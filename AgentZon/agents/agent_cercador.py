import sys
from pathlib import Path
from typing import Optional

from flask import Flask, Response, render_template, request
from rdflib import Graph
from rdflib.exceptions import ParserError

from AgentZon.config import AGENTZON, ONTOLOGY_PATH, PRODUCTES_PATH, WEB_DIR
from AgentZon.protocols.cerca import (
    build_peticio_cerca,
    build_resultat_cerca,
    cercar_productes,
    get_peticio_cerca_subject,
    get_resultat_cerca_subject,
    iter_productes,
    read_resultat_cerca,
)


class AgentCercador:
    """
    Implementa els plans definits a Prometheus per a l'Agent Cercador:
    processar peticions de cerca i presentar resultats.
    """

    def __init__(self, ontology_path: Path = ONTOLOGY_PATH, productes_path: Path = PRODUCTES_PATH):
        self.ontology_path = ontology_path
        self.productes_path = productes_path

        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self._carregar_ontologia()
        self._carregar_productes()

    def _carregar_ontologia(self) -> None:
        if self.ontology_path.exists():
            try:
                self.graph.parse(self.ontology_path, format="xml")
            except ParserError as exc:
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _carregar_productes(self) -> None:
        if not self.productes_path.exists():
            raise FileNotFoundError(f"No s'ha trobat el catàleg de productes: {self.productes_path}")
        self.graph.parse(self.productes_path, format="turtle")

    def inventari(self) -> list[dict]:
        return iter_productes(self.graph)

    def processar_cerca(self, peticio_graph: Graph) -> Graph:
        peticio_subject = get_peticio_cerca_subject(peticio_graph)
        productes = cercar_productes(self.graph, peticio_graph, peticio_subject)
        return build_resultat_cerca(self.graph, productes, peticio_subject=peticio_subject)

    def resultat_per_template(self, resultat_graph: Graph) -> dict:
        resultat_subject = get_resultat_cerca_subject(resultat_graph)
        return read_resultat_cerca(self.graph + resultat_graph, resultat_subject)


def _float_opcional(valor: str):
    valor = valor.strip()
    return float(valor) if valor else None


def create_app(cercador: Optional[AgentCercador] = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    cercador = cercador or AgentCercador()

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
                peticio_graph = build_peticio_cerca(
                    text=valors["text"],
                    categ=valors["categ"] or None,
                    marca=valors["marca"] or None,
                    preu_min=_float_opcional(valors["preu_min"]),
                    preu_max=_float_opcional(valors["preu_max"]),
                )
                resultat = cercador.resultat_per_template(cercador.processar_cerca(peticio_graph))
            except ValueError as exc:
                error = str(exc)

        return render_template("cercador.html", resultat=resultat, error=error, valors=valors)

    @app.route("/Info", methods=["GET"])
    def info():
        return Response(cercador.graph.serialize(format="turtle"), mimetype="text/turtle")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=9001, debug=True)
