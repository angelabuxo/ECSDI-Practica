import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request
from rdflib import Graph, Literal, RDF, URIRef, XSD
from rdflib.exceptions import ParserError

# Aquest mòdul s'ha d'executar com a part del paquet, per exemple amb:
# `python -m AgentZon.agents.agent_compra`
from AgentZon.config import (
    AGENTZON,
    DADES_ENVIAMENT_USUARI_PATH,
    ONTOLOGY_PATH,
    PRODUCTES_PATH,
    RESPONSABLE_ENVIAMENT_PRODUCTES_PATH,
    UBICACIONS_PRODUCTES_PATH,
    WEB_DIR,
)
from AgentZon.protocols.cerca import ProducteModel
from AgentZon.protocols.compra import (
    ComandaModel,
    InformacioUsuari,
    PeticioCompra,
    PeticioInfoUsuari,
    processar_peticio_final,
    validar_comanda,
)


class AgentCompra:
    """
    Implementa els plans definits a Prometheus per a l'Agent Compra:
    processar la compra, registrar les dades de l'usuari, confirmar la comanda,
    localitzar els productes i simular el cobrament.
    """

    def __init__(
        self,
        ontology_path: Path = ONTOLOGY_PATH,
        productes_path: Path = PRODUCTES_PATH,
        dades_enviament_path: Path = DADES_ENVIAMENT_USUARI_PATH,
        ubicacions_path: Path = UBICACIONS_PRODUCTES_PATH,
        responsables_path: Path = RESPONSABLE_ENVIAMENT_PRODUCTES_PATH,
    ):
        self.ontology_path = ontology_path
        self.productes_path = productes_path
        self.dades_enviament_path = Path(dades_enviament_path)
        self.ubicacions_path = Path(ubicacions_path)
        self.responsables_path = Path(responsables_path)
        self.enviaments: Dict[str, Dict[str, object]] = {}

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
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _carregar_productes(self) -> None:
        """Carrega el catàleg Turtle que actua com a font de dades de productes."""
        if not self.productes_path.exists():
            raise FileNotFoundError(f"No s'ha trobat el catàleg de productes: {self.productes_path}")

        self.graph.parse(self.productes_path, format="turtle")

    def _az(self, term: str) -> URIRef:
        """Construeix un URIRef dins del namespace de l'ontologia AgentZon."""
        return URIRef(f"{AGENTZON}{term}")

    def _carregar_json(self, path: Path, default: Optional[Dict] = None) -> Dict:
        """Carrega una font de dades JSON persistent."""
        if not path.exists():
            return default or {}

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _guardar_json(self, path: Path, dades: Dict) -> None:
        """Guarda una font de dades JSON persistent."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(dades, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def _carregar_ttl_indexat(self, path: Path, subject_type: str, id_predicate: str, camp_predicates: Dict[str, str]) -> Dict:
        """
        Carrega una font Turtle com a diccionari indexat per id.
        Exemple de sortida: {"p001": {"responsable": "agentzon", "venedor": "X"}}.
        """
        if not path.exists():
            return {}

        graph = Graph()
        graph.parse(path, format="turtle")
        resultat = {}

        for subject in graph.subjects(RDF.type, self._az(subject_type)):
            entity_id = graph.value(subject, self._az(id_predicate))
            if entity_id is None:
                continue

            key = str(entity_id.toPython())
            row = {}
            for camp, predicate in camp_predicates.items():
                value = graph.value(subject, self._az(predicate))
                if value is not None:
                    row[camp] = value.toPython()

            resultat[key] = row

        return resultat

    def _guardar_ttl_indexat(
        self,
        path: Path,
        dades: Dict[str, Dict[str, object]],
        subject_type: str,
        id_predicate: str,
        camp_predicates: Dict[str, str],
        subject_prefix: str,
    ) -> None:
        """Guarda un diccionari indexat per id en format Turtle."""
        graph = Graph()
        graph.bind("az", AGENTZON)

        for key, row in dades.items():
            subject = self._az(f"{subject_prefix}_{key}")
            graph.add((subject, RDF.type, self._az(subject_type)))
            graph.add((subject, self._az(id_predicate), Literal(str(key))))

            for camp, predicate in camp_predicates.items():
                if camp not in row:
                    continue

                value = row[camp]
                if camp == "prioritat":
                    graph.add((subject, self._az(predicate), Literal(int(value), datatype=XSD.integer)))
                else:
                    graph.add((subject, self._az(predicate), Literal(value)))

        path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=path, format="turtle")

    def _carregar_mapa(self, path: Path, tipus: str) -> Dict:
        """Carrega dades persistides des de JSON o Turtle, segons extensió."""
        if path.suffix.lower() == ".ttl":
            if tipus == "dades_enviament":
                return self._carregar_ttl_indexat(
                    path,
                    subject_type="DadesEnviamentUsuari",
                    id_predicate="IdUsuari",
                    camp_predicates={"adreca": "Adreça", "prioritat": "Prioritat"},
                )
            if tipus == "ubicacions":
                return self._carregar_ttl_indexat(
                    path,
                    subject_type="UbicacioProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"magatzem": "Magatzem", "ciutat": "Ciutat"},
                )
            if tipus == "responsables":
                return self._carregar_ttl_indexat(
                    path,
                    subject_type="ResponsableEnviamentProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"responsable": "Responsable", "venedor": "Venedor"},
                )
            raise ValueError(f"Tipus de mapa desconegut: {tipus}")

        return self._carregar_json(path)

    def _guardar_mapa(self, path: Path, dades: Dict, tipus: str) -> None:
        """Guarda dades persistides en JSON o Turtle, segons extensió."""
        if path.suffix.lower() == ".ttl":
            if tipus == "dades_enviament":
                self._guardar_ttl_indexat(
                    path,
                    dades,
                    subject_type="DadesEnviamentUsuari",
                    id_predicate="IdUsuari",
                    camp_predicates={"adreca": "Adreça", "prioritat": "Prioritat"},
                    subject_prefix="dades_enviament_usuari",
                )
                return
            if tipus == "ubicacions":
                self._guardar_ttl_indexat(
                    path,
                    dades,
                    subject_type="UbicacioProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"magatzem": "Magatzem", "ciutat": "Ciutat"},
                    subject_prefix="ubicacio_producte",
                )
                return
            if tipus == "responsables":
                self._guardar_ttl_indexat(
                    path,
                    dades,
                    subject_type="ResponsableEnviamentProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"responsable": "Responsable", "venedor": "Venedor"},
                    subject_prefix="responsable_enviament_producte",
                )
                return
            raise ValueError(f"Tipus de mapa desconegut: {tipus}")

        self._guardar_json(path, dades)

    def inventari(self) -> List[ProducteModel]:
        """Converteix totes les instàncies RDF de Producte a models Python."""
        return [self._producte_des_de_graf(subject) for subject in self.graph.subjects(RDF.type, AGENTZON.Producte)]

    def _literal(self, subject: URIRef, predicate: URIRef, default=None):
        """Llegeix un literal RDF i retorna un valor Python normal."""
        value = self.graph.value(subject, predicate)
        return value.toPython() if value is not None else default
    
    def _literal_de_predicats(self, subject: URIRef, predicates: List[URIRef], default=None):
        """
        Cerca un valor literal provant diversos predicats.
        Serveix per mantenir compatibilitat entre versions de l'ontologia.
        """
        for predicate in predicates:
            value = self.graph.value(subject, predicate)
            if value is not None:
                return value.toPython()
        return default

    def _producte_des_de_graf(self, subject: URIRef) -> ProducteModel:
        """Reconstrueix un ProducteModel a partir de les seves propietats RDF."""
        return ProducteModel(
            # Nova ontologia: Id, Nom, Preu, Descripció, Categoria, Marca, Pes.
            # Mantenim fallback als noms antics (*Producte) per no trencar dades heretades.
            id=str(self._literal_de_predicats(subject, [AGENTZON.Id], subject.split("/")[-1])),
            nom=str(self._literal_de_predicats(subject, [AGENTZON.Nom], "")),
            preu=float(self._literal_de_predicats(subject, [AGENTZON.Preu], 0.0)),
            descr=str(self._literal_de_predicats(subject, [AGENTZON.Descripció], "")),
            categ=str(self._literal_de_predicats(subject, [AGENTZON.Categoria], "")),
            marca=str(self._literal_de_predicats(subject, [AGENTZON.Marca], "")),
            pes=int(float(self._literal_de_predicats(subject, [AGENTZON.Pes], 0))),
        )

    def productes_per_ids(self, ids_productes: List[str]) -> List[ProducteModel]:
        """Localitza els productes seleccionats dins del catàleg RDF."""
        productes_per_id = {producte.id: producte for producte in self.inventari()}
        productes = []

        for producte_id in ids_productes:
            if producte_id not in productes_per_id:
                raise ValueError(f"Producte desconegut: {producte_id}")
            productes.append(productes_per_id[producte_id])

        return productes

    def processar_peticio_compra(self, userid: str, productes: List[ProducteModel]) -> PeticioCompra:
        """Cp. Processar petició compra: rep la selecció inicial de productes."""
        userid = userid.strip()
        if not userid:
            raise ValueError("Cal indicar l'id de l'usuari.")
        if not productes:
            raise ValueError("Cal seleccionar almenys un producte.")

        return PeticioCompra(userid=userid, llista_productes=productes)

    def demanar_informacio_usuari(self, userid: str) -> PeticioInfoUsuari:
        """Pla demanar informació usuari: demana adreça, prioritat i pagament."""
        return PeticioInfoUsuari(userid=userid)

    def registrar_dades_usuari(self, info: InformacioUsuari) -> InformacioUsuari:
        """Pla registrar dades d'usuari: desa la resposta de l'usuari al protocol."""
        self._persistir_dades_enviament(info)
        return info

    def _persistir_dades_enviament(self, info: InformacioUsuari) -> None:
        """Escriu la font persistent Dades d'enviament Usuari."""
        dades = self._carregar_mapa(self.dades_enviament_path, "dades_enviament")
        dades[info.userid] = {
            "adreca": info.adreça,
            "prioritat": info.prioritat,
        }
        self._guardar_mapa(self.dades_enviament_path, dades, "dades_enviament")

    def gestionar_compra(self, compra: PeticioCompra, info_usuari: InformacioUsuari) -> ComandaModel:
        """Cp. Gestionar compra: crea, valida i registra la comanda."""
        info_persistida = self.registrar_dades_usuari(info_usuari)
        comanda = processar_peticio_final(compra, info_persistida)
        if not validar_comanda(comanda):
            raise ValueError("La comanda no és vàlida.")

        # TODO: Protocol per avisar a l'Ag. Cobrador sobre les dades bancàries de l'usuari.
        # TODO: Protocol per avisar a Ag. Opinador per registrar la comanda a BD.
        self.localitzar_productes(comanda)
        return comanda

    def localitzar_productes(self, comanda: ComandaModel) -> Dict[str, object]:
        """
        Cp. Localitzar productes: verifica disponibilitat al catàleg i prepara
        una resposta local d'enviament per a aquesta entrega.
        """
        ids_comanda = [producte.id for producte in comanda.llista_productes]


        dades_usuari = self._carregar_mapa(self.dades_enviament_path, "dades_enviament")
        ubicacions = self._carregar_mapa(self.ubicacions_path, "ubicacions")
        responsables = self._carregar_mapa(self.responsables_path, "responsables")
        responsables_enviament = {}

        for producte_id in ids_comanda:
            responsable = responsables.get(producte_id, {"responsable": "agentzon"})
            responsable_tipus = responsable.get("responsable", "agentzon")

            if responsable_tipus == "extern":
                responsables_enviament[producte_id] = responsable.get("venedor", "Venedor extern")
                # TODO: Protocol per avisar al venedor extern de que producte X s'ha d'enviar a Y abans de Z.
            else:
                if producte_id not in ubicacions:
                    raise ValueError(f"No hi ha ubicació persistent per al producte {producte_id}.")
                responsables_enviament[producte_id] = "AgentZon"
                # TODO: Protocol per avisar al centre logístic de que producte X s'ha denviar a Y abans de Z.

        enviament = {
            "data_entrega_estimada": comanda.data_entrega_estimada,
            "adreca": dades_usuari[comanda.userid]["adreca"],
            "prioritat": dades_usuari[comanda.userid]["prioritat"],
            "responsables": responsables_enviament,
        }
        self.enviaments[comanda.id] = enviament
        return enviament

def _int_obligatori(valor: str, missatge: str) -> int:
    """Converteix un camp obligatori del formulari a enter."""
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(missatge) from exc


def create_app(compra_agent: Optional[AgentCompra] = None) -> Flask:
    """Crea la interfície HTML que pertany a l'Agent Compra."""
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    compra_agent = compra_agent or AgentCompra()

    @app.route("/", methods=["GET", "POST"])
    def index():
        resultat = None
        error = None
        productes = compra_agent.inventari()
        valors = {
            "userid": "",
            "adreca": "",
            "prioritat": "2",
            "metodepagament": "",
            "productes": [],
        }

        if request.method == "POST":
            valors = {
                "userid": request.form.get("userid", ""),
                "adreca": request.form.get("adreca", ""),
                "prioritat": request.form.get("prioritat", "2"),
                "metodepagament": request.form.get("metodepagament", ""),
                "productes": request.form.getlist("productes"),
            }

            try:
                productes_seleccionats = compra_agent.productes_per_ids(valors["productes"])
                compra = compra_agent.processar_peticio_compra(valors["userid"], productes_seleccionats)
                compra_agent.demanar_informacio_usuari(compra.userid)
                info_usuari = InformacioUsuari(
                    userid=compra.userid,
                    adreça=valors["adreca"],
                    prioritat=_int_obligatori(valors["prioritat"], "La prioritat ha de ser numèrica."),
                    metodepagament=valors["metodepagament"],
                )
                comanda = compra_agent.gestionar_compra(compra, info_usuari)
                resultat = {
                    "comanda": comanda,
                    "enviament": compra_agent.enviaments[comanda.id],
                }
            except ValueError as exc:
                error = str(exc)

        return render_template("compra.html", productes=productes, resultat=resultat, error=error, valors=valors)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=9002, debug=True)
