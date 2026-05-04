import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from flask import Flask, Response, render_template, request
from rdflib import BNode, Graph, Literal, RDF, URIRef
from rdflib.exceptions import ParserError

from AgentZon.config import (
    AGENTZON,
    DADES_ENVIAMENT_USUARI_PATH,
    ONTOLOGY_PATH,
    PRODUCTES_PATH,
    RESPONSABLE_ENVIAMENT_PRODUCTES_PATH,
    UBICACIONS_PRODUCTES_PATH,
    WEB_DIR,
)
from AgentZon.protocols.cerca import iter_productes, productes_per_ids
from AgentZon.protocols.centre_logistic import (
    build_dades_enviament_action,
    build_producte_localitzat_action,
    read_dades_enviament,
    read_lot_assignat_response,
)
from AgentZon.protocols.compra import (
    BUY,
    build_comanda,
    build_dades_enviament_usuari,
    build_info_usuari,
    build_peticio_info_usuari,
    get_comanda_subject,
    read_comanda,
    read_info_usuari,
    read_dades_enviament_usuari,
    validar_comanda,
)
from AgentZon.protocols.directory import build_register_action, build_search_action, read_directory_responses
from AgentZon.protocols.fipa_acl import (
    build_message,
    build_not_understood,
    get_message_properties,
    parse_message,
    send_message,
)
from AgentZon.agents.logging_utils import configure_pretty_logging


logger = logging.getLogger(__name__)


class AgentCompra:
    """
    Implementa els plans definits a Prometheus per a l'Agent Compra:
    processar la compra, registrar les dades de l'usuari, confirmar la comanda
    i coordinar l'enviament sobre estat RDF.
    """

    def __init__(
        self,
        ontology_path: Path = ONTOLOGY_PATH,
        productes_path: Path = PRODUCTES_PATH,
        dades_enviament_path: Path = DADES_ENVIAMENT_USUARI_PATH,
        ubicacions_path: Path = UBICACIONS_PRODUCTES_PATH,
        responsables_path: Path = RESPONSABLE_ENVIAMENT_PRODUCTES_PATH,
        directory_address: Optional[str] = None,
        message_sender=send_message,
    ):
        self.ontology_path = ontology_path
        self.productes_path = productes_path
        self.dades_enviament_path = Path(dades_enviament_path)
        self.ubicacions_path = Path(ubicacions_path)
        self.responsables_path = Path(responsables_path)
        self.directory_address = directory_address
        self.message_sender = message_sender
        self._seguent_id_comanda = 0

        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self.graph.bind("buy", BUY)
        self._carregar_ontologia()
        self._carregar_dades_base()

    def _carregar_ontologia(self) -> None:
        if self.ontology_path.exists():
            try:
                self.graph.parse(self.ontology_path, format="xml")
            except ParserError as exc:
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _carregar_dades_base(self) -> None:
        self._parse_optional(self.productes_path, "turtle")
        self._parse_optional(self.dades_enviament_path, "turtle")
        self._parse_optional(self.ubicacions_path, "turtle")
        self._parse_optional(self.responsables_path, "turtle")

    def _parse_optional(self, path: Path, rdf_format: str) -> None:
        if path.exists() and path.stat().st_size:
            self.graph.parse(path, format=rdf_format)

    def _load_graph_from_path(self, path: Path) -> Graph:
        graph = Graph()
        graph.bind("az", AGENTZON)
        if path.exists() and path.stat().st_size:
            graph.parse(path, format="turtle")
        return graph

    def _persist_subject(self, path: Path, subject: URIRef | BNode, fragment: Graph) -> None:
        graph = self._load_graph_from_path(path)
        graph.remove((subject, None, None))
        for triple in fragment.triples((subject, None, None)):
            graph.add(triple)
        path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=path, format="turtle")

        self.graph.remove((subject, None, None))
        for triple in fragment.triples((subject, None, None)):
            self.graph.add(triple)

    def _literal(self, subject: URIRef | BNode, predicate: URIRef, default=None):
        value = self.graph.value(subject, predicate)
        return value.toPython() if value is not None else default

    def inventari(self) -> list[dict]:
        return iter_productes(self.graph)

    def productes_per_ids(self, ids_productes: list[str]) -> list[dict]:
        return productes_per_ids(self.graph, ids_productes)

    def processar_peticio_compra(self, userid: str, productes: list[dict]) -> dict:
        userid = userid.strip()
        if not userid:
            raise ValueError("Cal indicar l'id de l'usuari.")
        if not productes:
            raise ValueError("Cal seleccionar almenys un producte.")
        return {"userid": userid, "llista_productes": productes}

    def demanar_informacio_usuari(self, userid: str) -> Graph:
        return build_peticio_info_usuari(userid)

    def registrar_dades_usuari(self, info_usuari: dict) -> dict:
        fragment = build_dades_enviament_usuari(
            info_usuari["userid"],
            info_usuari["adreca"],
            info_usuari["ciutat"],
            int(info_usuari["prioritat"]),
        )
        subject = next(fragment.subjects(RDF.type, AGENTZON.DadesEnviamentUsuari))
        self._persist_subject(self.dades_enviament_path, subject, fragment)
        return read_dades_enviament_usuari(self.graph, subject)

    def _nou_id_comanda(self) -> str:
        if self._seguent_id_comanda > 9999:
            raise ValueError("S'ha esgotat el rang d'identificadors de comanda (0000-9999).")
        id_comanda = f"{self._seguent_id_comanda:04d}"
        self._seguent_id_comanda += 1
        return id_comanda

    def _read_info_usuari_input(self, info_usuari: dict | Graph) -> dict:
        if isinstance(info_usuari, Graph):
            subject = next(info_usuari.subjects(RDF.type, AGENTZON.InfoUsuari))
            return read_info_usuari(info_usuari, subject)
        return info_usuari

    def gestionar_compra(self, compra: dict, info_usuari: dict | Graph) -> dict:
        logger.debug(
            "gestionant compra userid=%s productes=%s",
            compra["userid"],
            [producte["id"] for producte in compra["llista_productes"]],
        )
        info = self._read_info_usuari_input(info_usuari)
        self.registrar_dades_usuari(info)
        comanda_graph = build_comanda(self.graph, self._nou_id_comanda(), compra["llista_productes"], info)
        comanda_subject = get_comanda_subject(comanda_graph)
        for triple in comanda_graph:
            self.graph.add(triple)
        comanda = read_comanda(self.graph, comanda_subject)
        logger.debug(
            "comanda creada id=%s userid=%s total=%s estat=%s entrega_estimada=%s",
            comanda["id"],
            comanda["userid"],
            comanda["import_total"],
            comanda["estat"],
            comanda["data_entrega_estimada"],
        )
        if not validar_comanda(self.graph, comanda_subject):
            raise ValueError("La comanda no és vàlida.")

        logger.debug("comanda validada id=%s", comanda["id"])
        self.localitzar_productes(comanda)
        return comanda

    def registrar_al_directori(self, address: str) -> dict:
        if not self.directory_address:
            raise ValueError("Cal configurar directory_address per registrar l'Agent Compra.")
        logger.debug("registrant agent compra al directori address=%s directory=%s", address, self.directory_address)
        content = build_register_action(
            name="agent-compra",
            uri=AGENTZON.agent_compra,
            address=address,
            agent_type="AgentCompra",
        )
        message = build_message("request", AGENTZON.agent_compra, AGENTZON.directory_agent, content, msgcnt=1)
        response = self.message_sender(self.directory_address, message)
        props = get_message_properties(response)
        logger.debug("resposta registre directori performative=%s", props.get("performative") if props else None)
        return props

    def _cercar_centre_logistic_al_directori(self, centre_logistic_id: str) -> Optional[dict]:
        if not self.directory_address:
            logger.debug("directori no configurat per centre_logistic=%s", centre_logistic_id)
            return None

        logger.debug("cercant centre logistic al directori centre_logistic=%s", centre_logistic_id)
        search = build_search_action(agent_type="AgentCentreLogistic", name=centre_logistic_id)
        request_graph = build_message(
            "request",
            AGENTZON.agent_compra,
            AGENTZON.directory_agent,
            search,
            msgcnt=1,
        )
        response = self.message_sender(self.directory_address, request_graph)
        props = get_message_properties(response)
        if not props or props.get("performative") != "inform":
            logger.debug(
                "resposta cerca centre logistic no inform centre_logistic=%s performative=%s",
                centre_logistic_id,
                props.get("performative") if props else None,
            )
            return None

        results = read_directory_responses(response)
        logger.debug("resultats directori centre_logistic=%s count=%s", centre_logistic_id, len(results))
        return results[0] if results else None

    def _find_subject_by_id(self, rdf_type: URIRef, predicate: URIRef, value: str) -> Optional[URIRef]:
        for subject in self.graph.subjects(predicate, Literal(value)):
            if (subject, RDF.type, rdf_type) in self.graph:
                return subject
        return None

    def _read_responsable(self, producte_id: str) -> dict:
        subject = self._find_subject_by_id(AGENTZON.ResponsableEnviamentProducte, AGENTZON.IdProducte, producte_id)
        if subject is None:
            return {"responsable": "agentzon", "venedor": None}
        return {
            "responsable": str(self._literal(subject, AGENTZON.Responsable, "agentzon")),
            "venedor": self._literal(subject, AGENTZON.Venedor),
        }

    def _read_ubicacio(self, producte_id: str) -> dict:
        subject = self._find_subject_by_id(AGENTZON.UbicacioProducte, AGENTZON.IdProducte, producte_id)
        if subject is None:
            raise ValueError(f"No hi ha ubicació persistent per al producte {producte_id}.")
        return {
            "magatzem": str(self._literal(subject, AGENTZON.Magatzem, "")),
            "ciutat": str(self._literal(subject, AGENTZON.Ciutat, "")),
        }

    def _read_dades_usuari(self, userid: str) -> dict:
        subject = self._find_subject_by_id(AGENTZON.DadesEnviamentUsuari, AGENTZON.IdUsuari, userid)
        if subject is None:
            raise ValueError(f"No hi ha dades d'enviament persistides per a l'usuari {userid}.")
        return read_dades_enviament_usuari(self.graph, subject)

    def _save_assignacio_centre_logistic(
        self,
        comanda_id: str,
        producte_id: str,
        centre_logistic: str,
        estat: str,
        id_lot: str | None = None,
    ) -> None:
        subject = AGENTZON[f"assignacio_centre_logistic_{comanda_id}_{producte_id}"]
        self.graph.remove((subject, None, None))
        self.graph.add((subject, RDF.type, BUY.AssignacioCentreLogistic))
        self.graph.add((subject, AGENTZON.IdComanda, Literal(comanda_id)))
        self.graph.add((subject, AGENTZON.IdProducte, Literal(producte_id)))
        self.graph.add((subject, BUY.centre_logistic, Literal(centre_logistic)))
        self.graph.add((subject, BUY.estat, Literal(estat)))
        if id_lot:
            self.graph.set((subject, AGENTZON.IdLot, Literal(id_lot)))

    def _read_assignacions_centre_logistic(self, comanda_id: str) -> dict:
        result = {}
        for subject in self.graph.subjects(RDF.type, BUY.AssignacioCentreLogistic):
            if str(self._literal(subject, AGENTZON.IdComanda, "")) != comanda_id:
                continue
            producte_id = str(self._literal(subject, AGENTZON.IdProducte, ""))
            result[producte_id] = {
                "centre_logistic": str(self._literal(subject, BUY.centre_logistic, "")),
                "estat": str(self._literal(subject, BUY.estat, "")),
            }
            id_lot = self._literal(subject, AGENTZON.IdLot)
            if id_lot is not None:
                result[producte_id]["id_lot"] = str(id_lot)
        return result

    def _read_dades_definitives(self, comanda_id: str) -> dict:
        result = {}
        for subject in self.graph.subjects(RDF.type, AGENTZON.DadesEnviamentProducte):
            if str(self._literal(subject, AGENTZON.IdComanda, "")) != comanda_id:
                continue
            producte_id = str(self._literal(subject, AGENTZON.IdProducte, ""))
            result[producte_id] = {
                "id_lot": str(self._literal(subject, AGENTZON.IdLot, "")),
                "transportista_id": str(self._literal(subject, AGENTZON.IdTransportista, "")),
                "data_entrega_definitiva": str(self._literal(subject, AGENTZON.DataEntregaDefinitiva, "")),
            }
        return result

    def _enviar_producte_a_centre_logistic(self, centre_logistic_id: str, producte_localitzat: dict) -> dict:
        directory_entry = self._cercar_centre_logistic_al_directori(centre_logistic_id)
        if directory_entry is not None:
            logger.debug(
                "enviant producte a centre logistic centre_logistic=%s producte=%s address=%s",
                centre_logistic_id,
                producte_localitzat["id_producte"],
                directory_entry["address"],
            )
            request_graph = build_message(
                "request",
                AGENTZON.agent_compra,
                directory_entry["uri"],
                build_producte_localitzat_action(producte_localitzat),
                msgcnt=1,
            )
            response = self.message_sender(directory_entry["address"], request_graph)
            props = get_message_properties(response)
            if props and props.get("performative") == "confirm" and props.get("content") is not None:
                lot_assignat = read_lot_assignat_response(response, props["content"])
                logger.debug(
                    "centre logistic confirma lot centre_logistic=%s producte=%s lot=%s",
                    centre_logistic_id,
                    producte_localitzat["id_producte"],
                    lot_assignat["id_lot"],
                )
                return {
                    "centre_logistic": centre_logistic_id,
                    "id_lot": lot_assignat["id_lot"],
                    "estat": "PENDENT",
                }

            logger.debug(
                "centre logistic no confirma producte centre_logistic=%s producte=%s performative=%s",
                centre_logistic_id,
                producte_localitzat["id_producte"],
                props.get("performative") if props else None,
            )

        logger.debug(
            "producte pendent d'agent centre_logistic=%s producte=%s",
            centre_logistic_id,
            producte_localitzat["id_producte"],
        )
        return {
            "centre_logistic": centre_logistic_id,
            "estat": "PENDENT_AGENT",
        }

    def localitzar_productes(self, comanda: dict) -> dict:
        ids_comanda = [producte["id"] for producte in comanda["llista_productes"]]
        productes_per_id = {producte["id"]: producte for producte in comanda["llista_productes"]}
        logger.debug("localitzant productes comanda=%s productes=%s", comanda["id"], ids_comanda)

        dades_usuari = self._read_dades_usuari(comanda["userid"])
        responsables_enviament = {}
        centres_logistics_enviament = {}

        for producte_id in ids_comanda:
            responsable = self._read_responsable(producte_id)
            responsable_tipus = responsable.get("responsable", "agentzon")

            if responsable_tipus == "extern":
                responsables_enviament[producte_id] = responsable.get("venedor") or "Venedor extern"
                logger.debug(
                    "producte extern producte=%s venedor=%s comanda=%s",
                    producte_id,
                    responsables_enviament[producte_id],
                    comanda["id"],
                )
            else:
                ubicacio = self._read_ubicacio(producte_id)
                centre_logistic_id = ubicacio.get("magatzem")
                if not centre_logistic_id:
                    raise ValueError(f"No hi ha centre logístic persistent per al producte {producte_id}.")

                responsables_enviament[producte_id] = "AgentZon"
                logger.debug(
                    "producte intern producte=%s centre_logistic=%s comanda=%s",
                    producte_id,
                    centre_logistic_id,
                    comanda["id"],
                )
                producte_localitzat = {
                    "id_producte": producte_id,
                    "id_comanda": comanda["id"],
                    "userid": comanda["userid"],
                    "adreca": dades_usuari["adreca"],
                    "ciutat": dades_usuari["ciutat"] or dades_usuari["adreca"],
                    "prioritat": dades_usuari["prioritat"],
                    "data_limit": comanda["data_entrega_estimada"],
                    "pes": productes_per_id[producte_id]["pes"],
                    "import_producte": productes_per_id[producte_id]["preu"],
                }
                centres_logistics_enviament[producte_id] = self._enviar_producte_a_centre_logistic(
                    centre_logistic_id,
                    producte_localitzat,
                )
                self._save_assignacio_centre_logistic(
                    comanda["id"],
                    producte_id,
                    centre_logistic_id,
                    centres_logistics_enviament[producte_id]["estat"],
                    centres_logistics_enviament[producte_id].get("id_lot"),
                )

        enviament = {
            "data_entrega_estimada": comanda["data_entrega_estimada"],
            "adreca": dades_usuari["adreca"],
            "ciutat": dades_usuari["ciutat"] or dades_usuari["adreca"],
            "prioritat": dades_usuari["prioritat"],
            "responsables": responsables_enviament,
            "centres_logistics": centres_logistics_enviament,
            "dades_definitives": self._read_dades_definitives(comanda["id"]),
        }
        logger.debug(
            "enviament preparat comanda=%s responsables=%s centres=%s",
            comanda["id"],
            responsables_enviament,
            centres_logistics_enviament,
        )
        return enviament

    def render_enviament(self, comanda_id: str) -> dict:
        comanda_subject = AGENTZON[f"comanda_{comanda_id}"]
        comanda = read_comanda(self.graph, comanda_subject)
        dades_usuari = self._read_dades_usuari(comanda["userid"])
        responsables = {}
        for producte in comanda["llista_productes"]:
            responsable = self._read_responsable(producte["id"])
            responsables[producte["id"]] = (
                responsable.get("venedor") if responsable.get("responsable") == "extern" else "AgentZon"
            ) or "AgentZon"

        return {
            "data_entrega_estimada": comanda["data_entrega_estimada"],
            "adreca": dades_usuari["adreca"],
            "ciutat": dades_usuari["ciutat"] or dades_usuari["adreca"],
            "prioritat": dades_usuari["prioritat"],
            "responsables": responsables,
            "centres_logistics": self._read_assignacions_centre_logistic(comanda_id),
            "dades_definitives": self._read_dades_definitives(comanda_id),
        }

    def processar_dades_enviament(self, dades) -> dict:
        id_comanda = dades["id_comanda"]
        if (AGENTZON[f"comanda_{id_comanda}"], RDF.type, AGENTZON.Comanda) not in self.graph:
            raise ValueError(f"Comanda desconeguda: {id_comanda}")

        logger.debug(
            "processant dades enviament comanda=%s producte=%s lot=%s transportista=%s data=%s",
            id_comanda,
            dades["id_producte"],
            dades["id_lot"],
            dades["transportista_id"],
            dades["data_entrega_definitiva"],
        )
        dades_graph = build_dades_enviament_action(dades)
        dades_subject = next(dades_graph.subjects(RDF.type, AGENTZON.DadesEnviamentProducte))
        self.graph.remove((dades_subject, None, None))
        for triple in dades_graph:
            self.graph.add(triple)
        logger.debug("dades definitives guardades comanda=%s producte=%s", id_comanda, dades["id_producte"])

        return {
            "userid": dades["userid"],
            "id_comanda": id_comanda,
            "id_producte": dades["id_producte"],
            "transportista_id": dades["transportista_id"],
            "data_entrega_definitiva": dades["data_entrega_definitiva"],
        }


def _int_obligatori(valor: str, missatge: str) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(missatge) from exc


def create_app(compra_agent: Optional[AgentCompra] = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    compra_agent = compra_agent or AgentCompra()

    @app.route("/comm", methods=["GET"])
    def comm():
        try:
            incoming = parse_message(request.args.get("content", ""))
            props = get_message_properties(incoming)
            if not props or props.get("performative") != "request" or props.get("content") is None:
                response = build_not_understood(AGENTZON.agent_compra, AGENTZON.unknown_agent, msgcnt=1)
            elif (props["content"], RDF.type, AGENTZON.DadesEnviamentProducte) in incoming:
                dades = read_dades_enviament(incoming, props["content"])
                compra_agent.processar_dades_enviament(dades)
                response = build_message(
                    "confirm",
                    AGENTZON.agent_compra,
                    props.get("sender", AGENTZON.unknown_agent),
                    None,
                    msgcnt=1,
                )
            else:
                response = build_not_understood(
                    AGENTZON.agent_compra,
                    props.get("sender", AGENTZON.unknown_agent),
                    msgcnt=1,
                )
        except Exception:
            response = build_not_understood(AGENTZON.agent_compra, AGENTZON.unknown_agent, msgcnt=1)

        return Response(response.serialize(format="xml"), mimetype="application/rdf+xml")

    @app.route("/", methods=["GET", "POST"])
    def index():
        resultat = None
        error = None
        productes = compra_agent.inventari()
        valors = {
            "userid": "",
            "adreca": "",
            "ciutat": "",
            "prioritat": "2",
            "metodepagament": "",
            "productes": [],
        }

        if request.method == "POST":
            valors = {
                "userid": request.form.get("userid", ""),
                "adreca": request.form.get("adreca", ""),
                "ciutat": request.form.get("ciutat", ""),
                "prioritat": request.form.get("prioritat", "2"),
                "metodepagament": request.form.get("metodepagament", ""),
                "productes": request.form.getlist("productes"),
            }

            try:
                productes_seleccionats = compra_agent.productes_per_ids(valors["productes"])
                compra = compra_agent.processar_peticio_compra(valors["userid"], productes_seleccionats)
                compra_agent.demanar_informacio_usuari(compra["userid"])
                info_graph = build_info_usuari(
                    userid=compra["userid"],
                    adreca=valors["adreca"],
                    ciutat=valors["ciutat"],
                    prioritat=_int_obligatori(valors["prioritat"], "La prioritat ha de ser numèrica."),
                    metodepagament=valors["metodepagament"],
                )
                comanda = compra_agent.gestionar_compra(compra, info_graph)
                resultat = {
                    "comanda": comanda,
                    "enviament": compra_agent.render_enviament(comanda["id"]),
                }
            except ValueError as exc:
                error = str(exc)

        return render_template("compra.html", productes=productes, resultat=resultat, error=error, valors=valors)

    @app.route("/Info", methods=["GET"])
    def info():
        return Response(compra_agent.graph.serialize(format="turtle"), mimetype="text/turtle")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentZon Agent Compra")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9002)
    parser.add_argument("--directory", default="http://127.0.0.1:9000/Register")
    parser.add_argument("--address", default=None)
    args = parser.parse_args()

    configure_pretty_logging()
    agent = AgentCompra(directory_address=args.directory)
    advertised_address = args.address or f"http://127.0.0.1:{args.port}/comm"
    try:
        agent.registrar_al_directori(advertised_address)
    except Exception as exc:
        print(f"Avís: no s'ha pogut registrar l'Agent Compra al directori: {exc}", file=sys.stderr)

    create_app(agent).run(host=args.host, port=args.port, debug=True)
