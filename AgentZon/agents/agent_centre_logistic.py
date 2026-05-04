import argparse
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, Response, request
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.exceptions import ParserError

from AgentZon.agents.logging_utils import configure_pretty_logging
from AgentZon.config import AGENTZON, ONTOLOGY_PATH
from AgentZon.protocols.centre_logistic import (
    LOG,
    build_dades_enviament_action,
    build_eleccio_transportista_action,
    build_lot_assignat_response,
    build_peticio_cobrament_action,
    build_peticio_transport_action,
    build_producte_localitzat_action,
    build_resposta_oferta_transport_action,
    get_dades_enviament_subject,
    get_eleccio_transportista_subject,
    get_peticio_cobrament_subject,
    get_peticio_transport_subject,
    get_producte_localitzat_subject,
    get_resposta_oferta_transport_subject,
    read_dades_enviament,
    read_eleccio_transportista,
    read_lot_assignat_response,
    read_peticio_cobrament,
    read_producte_localitzat,
    read_resposta_oferta_transport,
)
from AgentZon.protocols.directory import build_register_action, build_search_action, read_directory_responses
from AgentZon.protocols.fipa_acl import (
    build_message,
    build_not_understood,
    get_message_properties,
    parse_message,
    send_message,
)


logger = logging.getLogger(__name__)
STATE = Namespace("urn:agentzon:logistics:state:")


class AgentCentreLogistic:
    """
    Implementa els plans definits a Prometheus per a l'Agent Centre Logístic
    amb el graf RDF com a únic estat de treball.
    """

    def __init__(
        self,
        centre_logistic_id: str,
        ubicacio: str,
        ontology_path: Path = ONTOLOGY_PATH,
        directory_address: str = "http://127.0.0.1:9000/Register",
        message_sender=send_message,
    ):
        self.centre_logistic_id = centre_logistic_id
        self.ubicacio = ubicacio
        self.ontology_path = ontology_path
        self.directory_address = directory_address
        self.message_sender = message_sender

        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self.graph.bind("log", LOG)
        self.graph.bind("state", STATE)
        self._carregar_ontologia()
        self._registrar_instancia_centre_logistic()

    @property
    def capacitats(self) -> Dict[str, List[object]]:
        return {
            "Gestionar magatzem": [self.pla_assignar_producte_a_lot],
            "Negociar transport": [self.pla_cerca_transportista, self.pla_transportista_escollit],
            "Gestionar post-enviament": [self.pla_producte_sha_enviat],
        }

    @property
    def uri(self) -> URIRef:
        return AGENTZON[f"agent_centre_logistic_{self.centre_logistic_id}"]

    def registrar_al_directori(self, address: str) -> dict:
        logger.debug(
            "registrant centre logistic al directori centre_logistic=%s address=%s directory=%s",
            self.centre_logistic_id,
            address,
            self.directory_address,
        )
        content = build_register_action(
            name=self.centre_logistic_id,
            uri=self.uri,
            address=address,
            agent_type="AgentCentreLogistic",
        )
        message = build_message("request", self.uri, AGENTZON.directory_agent, content, msgcnt=1)
        response = self.message_sender(self.directory_address, message)
        props = get_message_properties(response)
        logger.debug("resposta registre centre logistic performative=%s", props.get("performative") if props else None)
        return props

    def _carregar_ontologia(self) -> None:
        if self.ontology_path.exists():
            try:
                self.graph.parse(self.ontology_path, format="xml")
            except ParserError as exc:
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _registrar_instancia_centre_logistic(self) -> None:
        subject = self._centre_subject()
        self.graph.add((subject, RDF.type, AGENTZON.CentreLogistic))
        self.graph.set((subject, AGENTZON.Id, Literal(self.centre_logistic_id)))
        self.graph.set((subject, AGENTZON.Ubicacio, Literal(self.ubicacio)))

    def _centre_subject(self) -> URIRef:
        return AGENTZON[f"centre_logistic_{self.centre_logistic_id}"]

    def _lot_subject(self, id_lot: str) -> URIRef:
        return AGENTZON[f"lot_{id_lot}"]

    def _literal(self, subject: URIRef, predicate: URIRef, default=None):
        value = self.graph.value(subject, predicate)
        return value.toPython() if value is not None else default

    def _merge_graph(self, fragment: Graph) -> None:
        for subject in set(fragment.subjects()):
            self.graph.remove((subject, None, None))
        for triple in fragment:
            self.graph.add(triple)

    def _set_lot_state(self, lot_subject: URIRef, estat: str) -> None:
        self.graph.set((lot_subject, LOG.estat, Literal(estat)))

    def _data_lot(self, data_enviament: str) -> str:
        return date.fromisoformat(data_enviament.split("T")[0]).isoformat()

    def _iter_lot_subjects(self):
        centre_subject = self._centre_subject()
        for lot_subject in self.graph.objects(centre_subject, AGENTZON.Distribueix):
            if (lot_subject, RDF.type, AGENTZON.Lot) in self.graph:
                yield lot_subject

    def _read_lot(self, lot_subject: URIRef) -> dict:
        productes = [
            read_producte_localitzat(self.graph, subject)
            for subject in sorted(self.graph.objects(lot_subject, LOG.producte_localitzat), key=str)
        ]
        return {
            "subject": lot_subject,
            "id": str(self._literal(lot_subject, AGENTZON.Id, "")),
            "centre_logistic_id": self.centre_logistic_id,
            "ciutat": str(self._literal(lot_subject, AGENTZON.Ciutat, "")),
            "data_enviament": str(self._literal(lot_subject, AGENTZON.DataEnviament, "")),
            "estat": str(self._literal(lot_subject, LOG.estat, "PENDENT")),
            "productes": productes,
            "pes_total": sum(float(producte["pes"]) for producte in productes),
        }

    def _obtenir_lot_subject(self, id_lot: str) -> URIRef:
        lot_subject = self._lot_subject(id_lot)
        if (lot_subject, RDF.type, AGENTZON.Lot) not in self.graph:
            raise ValueError(f"Lot desconegut: {id_lot}")
        if (self._centre_subject(), AGENTZON.Distribueix, lot_subject) not in self.graph:
            raise ValueError(f"Lot desconegut: {id_lot}")
        return lot_subject

    def _obtenir_lot(self, id_lot: str) -> dict:
        return self._read_lot(self._obtenir_lot_subject(id_lot))

    def _cercar_lot_compatible(self, ciutat: str, data_enviament: str) -> Optional[URIRef]:
        for lot_subject in self._iter_lot_subjects():
            lot = self._read_lot(lot_subject)
            if lot["estat"] == "PENDENT" and lot["ciutat"] == ciutat and lot["data_enviament"] == data_enviament:
                return lot_subject
        return None

    def _prefix_lot(self) -> str:
        prefix = self.centre_logistic_id.strip().lower().split("-")[-1]
        prefix = "".join(char for char in prefix if char.isalnum())
        return prefix or "lot"

    def _nou_id_lot(self) -> str:
        pattern = re.compile(rf"^{re.escape(self._prefix_lot())}-(\d{{4}})$")
        maxim = 0
        for lot_subject in self._iter_lot_subjects():
            lot_id = str(self._literal(lot_subject, AGENTZON.Id, ""))
            match = pattern.match(lot_id)
            if match:
                maxim = max(maxim, int(match.group(1)))
        if maxim >= 9999:
            raise ValueError("S'ha esgotat el rang d'identificadors de lot (0001-9999).")
        return f"{self._prefix_lot()}-{maxim + 1:04d}"

    def _crear_lot(self, ciutat: str, data_enviament: str) -> URIRef:
        id_lot = self._nou_id_lot()
        lot_subject = self._lot_subject(id_lot)
        self.graph.add((lot_subject, RDF.type, AGENTZON.Lot))
        self.graph.set((lot_subject, AGENTZON.Id, Literal(id_lot)))
        self.graph.set((lot_subject, AGENTZON.Ciutat, Literal(ciutat)))
        self.graph.set((lot_subject, AGENTZON.DataEnviament, Literal(data_enviament, datatype=XSD.date)))
        self._set_lot_state(lot_subject, "PENDENT")
        self.graph.add((self._centre_subject(), AGENTZON.Distribueix, lot_subject))
        return lot_subject

    def _afegir_producte_localitzat(self, lot_subject: URIRef, producte_localitzat: dict) -> None:
        fragment = build_producte_localitzat_action(producte_localitzat)
        producte_subject = get_producte_localitzat_subject(fragment)
        for existent in list(self.graph.subjects(LOG.producte_localitzat, producte_subject)):
            self.graph.remove((existent, LOG.producte_localitzat, producte_subject))
        self._merge_graph(fragment)
        self.graph.add((lot_subject, LOG.producte_localitzat, producte_subject))
        self.graph.add((lot_subject, AGENTZON.TeProducte, AGENTZON[producte_localitzat["id_producte"]]))
        self.graph.add((self._centre_subject(), AGENTZON.RepAvis, producte_subject))

    def _read_ofertes(self, id_lot: str) -> list[dict]:
        ofertes = []
        for subject in self.graph.subjects(RDF.type, AGENTZON.RespostaOfertaTransport):
            if str(self._literal(subject, AGENTZON.IdLot, "")) != id_lot:
                continue
            ofertes.append(read_resposta_oferta_transport(self.graph, subject))
        return sorted(ofertes, key=lambda oferta: (float(oferta["cost"]), oferta["transportista_id"]))

    def _guardar_peticio_transport(self, peticio: dict) -> None:
        fragment = build_peticio_transport_action(peticio)
        peticio_subject = get_peticio_transport_subject(fragment)
        self._merge_graph(fragment)
        self.graph.add((self._centre_subject(), AGENTZON.Negocia, peticio_subject))

    def _guardar_oferta(self, oferta: dict) -> dict:
        fragment = build_resposta_oferta_transport_action(oferta)
        oferta_subject = get_resposta_oferta_transport_subject(fragment)
        self._merge_graph(fragment)
        self.graph.add((self._centre_subject(), AGENTZON.RepOferta, oferta_subject))
        return read_resposta_oferta_transport(self.graph, oferta_subject)

    def _guardar_eleccio(self, eleccio: dict) -> dict:
        fragment = build_eleccio_transportista_action(eleccio)
        eleccio_subject = get_eleccio_transportista_subject(fragment)
        self._merge_graph(fragment)
        transportista_subject = AGENTZON[f"agent_{eleccio['transportista_id']}"]
        self.graph.add((transportista_subject, RDF.type, AGENTZON.Transportista))
        self.graph.add((transportista_subject, AGENTZON.EsEscollit, eleccio_subject))
        return read_eleccio_transportista(self.graph, eleccio_subject)

    def _guardar_dades_enviament(self, dades: dict) -> dict:
        fragment = build_dades_enviament_action(dades)
        dades_subject = get_dades_enviament_subject(fragment)
        self._merge_graph(fragment)
        self.graph.add((self._centre_subject(), AGENTZON.Genera, dades_subject))
        return read_dades_enviament(self.graph, dades_subject)

    def _guardar_peticio_cobrament(self, peticio: dict) -> dict:
        fragment = build_peticio_cobrament_action(peticio)
        peticio_subject = get_peticio_cobrament_subject(fragment)
        self._merge_graph(fragment)
        self.graph.add((self._centre_subject(), LOG.peticio_cobrament, peticio_subject))
        return read_peticio_cobrament(self.graph, peticio_subject)

    def pla_assignar_producte_a_lot(self, producte_localitzat: dict) -> dict:
        ciutat = producte_localitzat["ciutat"].strip()
        data_enviament = self._data_lot(producte_localitzat["data_limit"])
        logger.debug(
            "assignant producte producte=%s comanda=%s centre_logistic=%s ciutat=%s",
            producte_localitzat["id_producte"],
            producte_localitzat["id_comanda"],
            self.centre_logistic_id,
            ciutat,
        )

        lot_subject = self._cercar_lot_compatible(ciutat, data_enviament)
        if lot_subject is None:
            lot_subject = self._crear_lot(ciutat, data_enviament)
            logger.debug(
                "lot creat lot=%s centre_logistic=%s ciutat=%s producte=%s data=%s",
                self._literal(lot_subject, AGENTZON.Id, ""),
                self.centre_logistic_id,
                ciutat,
                producte_localitzat["id_producte"],
                data_enviament,
            )

        self._afegir_producte_localitzat(lot_subject, {**producte_localitzat, "data_limit": data_enviament})
        lot = self._read_lot(lot_subject)
        logger.debug(
            "producte assignat a lot lot=%s producte=%s total_productes=%s",
            lot["id"],
            producte_localitzat["id_producte"],
            len(lot["productes"]),
        )
        return lot

    def pla_cerca_transportista(self, id_lot: str) -> dict:
        lot_subject = self._obtenir_lot_subject(id_lot)
        lot = self._read_lot(lot_subject)
        if not lot["productes"]:
            raise ValueError(f"El lot {id_lot} no té productes.")

        self._set_lot_state(lot_subject, "NEGOCIANT_TRANSPORT")
        peticio = {
            "centre_logistic_id": self.centre_logistic_id,
            "ciutat_desti": lot["ciutat"],
            "data_enviament": lot["data_enviament"],
            "pes": lot["pes_total"],
        }
        self._guardar_peticio_transport(peticio)
        logger.debug(
            "peticio transport lot=%s ciutat=%s pes=%s data=%s",
            lot["id"],
            peticio["ciutat_desti"],
            peticio["pes"],
            peticio["data_enviament"],
        )
        return peticio

    def registrar_oferta_transport(self, resposta_oferta_transport: dict) -> dict:
        id_lot = resposta_oferta_transport["id_lot"]
        self._obtenir_lot_subject(id_lot)
        oferta = self._guardar_oferta(resposta_oferta_transport)
        logger.debug(
            "oferta transport rebuda lot=%s transportista=%s cost=%s data=%s",
            oferta["id_lot"],
            oferta["transportista_id"],
            oferta["cost"],
            oferta["data_enviament"],
        )
        return oferta

    def _crear_dades_enviament_productes(self, lot: dict, eleccio: dict) -> list[dict]:
        dades = []
        for producte in lot["productes"]:
            dades.append(
                self._guardar_dades_enviament(
                    {
                        "id_lot": lot["id"],
                        "id_comanda": producte["id_comanda"],
                        "userid": producte["userid"],
                        "id_producte": producte["id_producte"],
                        "transportista_id": eleccio["transportista_id"],
                        "data_entrega_definitiva": eleccio["data_enviament"],
                    }
                )
            )
        return dades

    def pla_transportista_escollit(self, id_lot: str) -> tuple[dict, list[dict]]:
        lot_subject = self._obtenir_lot_subject(id_lot)
        lot = self._read_lot(lot_subject)
        ofertes = self._read_ofertes(id_lot)
        logger.debug("avaluant ofertes transport lot=%s ofertes=%s", id_lot, len(ofertes))
        if not ofertes:
            raise ValueError(f"No hi ha ofertes de transport per al lot {id_lot}.")

        ofertes_dins_termini = [
            oferta for oferta in ofertes if self._data_lot(oferta["data_enviament"]) <= lot["data_enviament"]
        ]
        if not ofertes_dins_termini:
            raise ValueError(f"No hi ha ofertes de transport dins del termini per al lot {id_lot}.")

        millor_oferta = min(ofertes_dins_termini, key=lambda oferta: float(oferta["cost"]))
        eleccio = self._guardar_eleccio(
            {
                "id_lot": id_lot,
                "transportista_id": millor_oferta["transportista_id"],
                "cost": millor_oferta["cost"],
                "data_enviament": millor_oferta["data_enviament"],
            }
        )
        self._set_lot_state(lot_subject, "TRANSPORTISTA_ESCOLLIT")
        logger.debug(
            "transportista escollit lot=%s transportista=%s cost=%s data=%s",
            eleccio["id_lot"],
            eleccio["transportista_id"],
            eleccio["cost"],
            eleccio["data_enviament"],
        )
        return eleccio, self._crear_dades_enviament_productes(self._read_lot(lot_subject), eleccio)

    def pla_producte_sha_enviat(self, today: Optional[str] = None) -> list[dict]:
        today = today or date.today().isoformat()
        peticions_cobrament = []

        for lot_subject in self._iter_lot_subjects():
            lot = self._read_lot(lot_subject)
            if self._data_lot(lot["data_enviament"]) == self._data_lot(today) and lot["estat"] != "ENVIAT":
                self._set_lot_state(lot_subject, "ENVIAT")
                logger.debug("lot enviat lot=%s productes=%s data=%s", lot["id"], len(lot["productes"]), today)
                for producte in lot["productes"]:
                    peticions_cobrament.append(
                        self._guardar_peticio_cobrament(
                            {
                                "userid": producte["userid"],
                                "id_comanda": producte["id_comanda"],
                                "id_producte": producte["id_producte"],
                                "import_cobrament": producte["import_producte"],
                            }
                        )
                    )

        return peticions_cobrament

    def cercar_transportistes(self) -> List[Dict[str, object]]:
        logger.debug("cercant transportistes al directori centre_logistic=%s", self.centre_logistic_id)
        content = build_search_action(agent_type="AgentTransportista")
        request = build_message("request", self.uri, AGENTZON.directory_agent, content, msgcnt=1)
        response = self.message_sender(self.directory_address, request)
        props = get_message_properties(response)
        if not props or props.get("performative") != "inform":
            logger.debug("resposta cerca transportistes no inform performative=%s", props.get("performative") if props else None)
            return []
        transportistes = read_directory_responses(response)
        logger.debug("transportistes trobats count=%s", len(transportistes))
        return transportistes

    def negociar_transport_amb_transportistes(self, id_lot: str) -> tuple[dict, list[dict]]:
        peticio = self.pla_cerca_transportista(id_lot)
        transportistes = self.cercar_transportistes()
        if not transportistes:
            raise ValueError("No s'ha trobat cap AgentTransportista al DirectoryAgent.")

        def _demanar_oferta(transportista: Dict[str, object]) -> Optional[dict]:
            logger.debug(
                "enviant peticio transport lot=%s transportista=%s address=%s",
                id_lot,
                transportista["name"],
                transportista["address"],
            )
            request = build_message(
                "request",
                self.uri,
                transportista["uri"],
                build_peticio_transport_action(peticio),
                msgcnt=1,
            )
            response = self.message_sender(transportista["address"], request)
            props = get_message_properties(response)
            if props and props.get("performative") == "inform" and props.get("content") is not None:
                oferta_rebuda = read_resposta_oferta_transport(response, props["content"])
                oferta_rebuda["id_lot"] = id_lot
                return oferta_rebuda
            logger.debug(
                "transportista sense oferta valida lot=%s transportista=%s performative=%s",
                id_lot,
                transportista["name"],
                props.get("performative") if props else None,
            )
            return None

        with ThreadPoolExecutor(max_workers=max(1, len(transportistes))) as executor:
            futures = [executor.submit(_demanar_oferta, transportista) for transportista in transportistes]
            for future in as_completed(futures):
                oferta = future.result()
                if oferta is not None:
                    self.registrar_oferta_transport(oferta)

        return self.pla_transportista_escollit(id_lot)


def create_app(centre_logistic: Optional[AgentCentreLogistic] = None) -> Flask:
    centre_logistic = centre_logistic or AgentCentreLogistic("magatzem-bcn", "Barcelona")
    app = Flask(__name__)

    @app.route("/comm", methods=["GET"])
    def comm():
        try:
            incoming = parse_message(request.args.get("content", ""))
            props = get_message_properties(incoming)
            if not props or props.get("performative") != "request" or props.get("content") is None:
                response = build_not_understood(
                    AGENTZON[f"agent_centre_logistic_{centre_logistic.centre_logistic_id}"],
                    props.get("sender", AGENTZON.unknown_agent) if props else AGENTZON.unknown_agent,
                    msgcnt=1,
                )
            elif (props["content"], RDF.type, AGENTZON.ProducteLocalitzat) in incoming:
                producte = read_producte_localitzat(incoming, props["content"])
                lot = centre_logistic.pla_assignar_producte_a_lot(producte)
                content = build_lot_assignat_response(lot["id"], producte["id_producte"])
                response = build_message(
                    "confirm",
                    AGENTZON[f"agent_centre_logistic_{centre_logistic.centre_logistic_id}"],
                    props.get("sender", AGENTZON.unknown_agent),
                    content,
                    msgcnt=1,
                )
            else:
                response = build_not_understood(
                    AGENTZON[f"agent_centre_logistic_{centre_logistic.centre_logistic_id}"],
                    props.get("sender", AGENTZON.unknown_agent),
                    msgcnt=1,
                )
        except Exception:
            response = build_not_understood(
                AGENTZON[f"agent_centre_logistic_{centre_logistic.centre_logistic_id}"],
                AGENTZON.unknown_agent,
                msgcnt=1,
            )

        return Response(response.serialize(format="xml"), mimetype="application/rdf+xml")

    @app.route("/Info", methods=["GET"])
    def info():
        return Response(centre_logistic.graph.serialize(format="turtle"), mimetype="text/turtle")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentZon Agent Centre Logístic")
    parser.add_argument("--id", default="magatzem-bcn")
    parser.add_argument("--ubicacio", default="Barcelona")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9003)
    parser.add_argument("--directory", default="http://127.0.0.1:9000/Register")
    parser.add_argument("--address", default=None)
    args = parser.parse_args()

    configure_pretty_logging()
    agent = AgentCentreLogistic(
        centre_logistic_id=args.id,
        ubicacio=args.ubicacio,
        directory_address=args.directory,
    )
    advertised_address = args.address or f"http://127.0.0.1:{args.port}/comm"
    try:
        agent.registrar_al_directori(advertised_address)
    except Exception as exc:
        print(f"Avís: no s'ha pogut registrar el centre logístic al directori: {exc}", file=sys.stderr)

    create_app(agent).run(host=args.host, port=args.port, debug=True)
