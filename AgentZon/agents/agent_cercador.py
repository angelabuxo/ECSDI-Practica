import json
import sys
from pathlib import Path
from typing import List

from flask import Flask, render_template, request
from rdflib import Graph
from rdflib.exceptions import ParserError

# Aquest mòdul s'ha d'executar com a part del paquet, per exemple amb:
# `python -m AgentZon.agents.agent_cercador`
from AgentZon.config import AGENTZON, ONTOLOGY_PATH, PRODUCTES_PATH, WEB_DIR
from AgentZon.protocols.cerca import PeticioCerca, ProducteModel, ResultatCerca, cercar_en_base_de_dades
class AgentCercador:
    """
    Implementa els plans definits a Prometheus per a l'Agent Cercador:
    processar peticions de cerca i presentar resultats.
    """

    def __init__(self, ontology_path: Path = ONTOLOGY_PATH, productes_path: Path = PRODUCTES_PATH):
        self.ontology_path = ontology_path
        self.productes_path = productes_path
        self._inventari_cache: List[ProducteModel] = []

        # El graf RDF és la "base de coneixement" local de l'agent. Hi carreguem
        # l'ontologia; el catàleg de productes actual és en JSON.
        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self._carregar_ontologia()
        self._carregar_productes()

    def _carregar_ontologia(self) -> None:
        """Carrega l'ontologia RDF/XML per tenir disponibles classes i propietats."""
        if self.ontology_path.exists():
            try:
                self.graph.parse(self.ontology_path, format="xml")
            except ParserError as exc:
                # Si algun dia es torna a exportar en OWL/XML, el Cercador pot
                # seguir funcionant amb el namespace i el catàleg Turtle.
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _carregar_productes(self) -> None:
        """Carrega el catàleg JSON i construeix l'inventari en memòria."""
        if not self.productes_path.exists():
            raise FileNotFoundError(f"No s'ha trobat el catàleg de productes: {self.productes_path}")

        with self.productes_path.open("r", encoding="utf-8") as f:
            dades = json.load(f)

        self._inventari_cache = []
        for producte_id, info in dades.items():
            self._inventari_cache.append(
                ProducteModel(
                    id=producte_id,
                    nom=str(info.get("nom", "")),
                    preu=float(info.get("preu", 0.0)),
                    descr=str(info.get("descripcio", "")),
                    categ=str(info.get("categoria", "")),
                    marca=str(info.get("marca", "")),
                    pes=int(float(info.get("pes", 0))),
                )
            )

    def inventari(self) -> List[ProducteModel]:
        """Retorna l'inventari de productes carregat des del catàleg JSON."""
        return self._inventari_cache

    def processar_cerca(self, peticio: PeticioCerca) -> ResultatCerca:
        """Executa el pla de cerca: obté l'inventari i aplica els filtres."""
        return cercar_en_base_de_dades(peticio, self.inventari())


def _float_opcional(valor: str):
    """Converteix un camp del formulari a float o None si està buit."""
    valor = valor.strip()
    return float(valor) if valor else None


def create_app() -> Flask:
    """Crea la interfície HTML que pertany a l'Agent Cercador."""
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    cercador = AgentCercador()

    @app.route("/", methods=["GET", "POST"])
    def index():
        resultat = None
        error = None
        valors = {
            "text": "",
            "categ": "",
            "marca": "",
            "preu_min": "",
            "preu_max": "",
        }

        if request.method == "POST":
            valors = {
                "text": request.form.get("text", ""),
                "categ": request.form.get("categ", ""),
                "marca": request.form.get("marca", ""),
                "preu_min": request.form.get("preu_min", ""),
                "preu_max": request.form.get("preu_max", ""),
            }

            try:
                peticio = PeticioCerca(
                    text=valors["text"],
                    categ=valors["categ"] or None,
                    marca=valors["marca"] or None,
                    preu_min=_float_opcional(valors["preu_min"]),
                    preu_max=_float_opcional(valors["preu_max"]),
                )
                resultat = cercador.processar_cerca(peticio)
            except ValueError as exc:
                error = str(exc)

        return render_template("cercador.html", resultat=resultat, error=error, valors=valors)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=9001, debug=True)
