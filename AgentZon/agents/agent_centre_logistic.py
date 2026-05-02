import argparse
import logging
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, Response, request
from rdflib import Graph, Literal, RDF, URIRef, XSD
from rdflib.exceptions import ParserError

# Aquest mòdul s'ha d'executar com a part del paquet, per exemple amb:
# `python -m AgentZon.agents.agent_centre_logistic`
from AgentZon.config import AGENTZON, ONTOLOGY_PATH
from AgentZon.protocols.directory import build_register_action, build_search_action, read_directory_responses
from AgentZon.protocols.centre_logistic import (
    DadesEnviamentProducte,
    EleccioTransportista,
    PeticioCobramentProducte,
    PeticioTransport,
    ProducteLocalitzat,
    RespostaOfertaTransport,
    build_lot_assignat_response,
    build_peticio_transport_action,
    read_resposta_oferta_transport,
    read_producte_localitzat,
)
from AgentZon.protocols.fipa_acl import (
    build_message,
    build_not_understood,
    get_message_properties,
    parse_message,
    send_message,
)
from AgentZon.agents.logging_utils import configure_pretty_logging


logger = logging.getLogger(__name__)


class LotLogistic:
    """Estat intern d'un Lot gestionat per l'Agent Centre Logístic."""

    def __init__(
        self,
        id: str,
        centre_logistic_id: str,
        adreca: str,
        prioritat: int,
        data_enviament: str,
        productes: Optional[List[ProducteLocalitzat]] = None,
        estat: str = "PENDENT",
    ):
        self.id = id
        self.centre_logistic_id = centre_logistic_id
        self.adreca = adreca
        self.prioritat = prioritat
        self.data_enviament = data_enviament
        self.productes = productes or []
        self.estat = estat

    @property
    def pes_total(self) -> float:
        return sum(float(getattr(producte, "pes", 0.0) or 0.0) for producte in self.productes)

    def es_compatible(self, adreca: str, prioritat: int, data_enviament: str) -> bool:
        return (
            self.estat == "PENDENT"
            and self.adreca == adreca # nomes els que coincideixen en adreca
            and self.prioritat == prioritat
            and self.data_enviament == data_enviament
        )


class AgentCentreLogistic:
    """
    Implementa els plans definits a Prometheus per a l'Agent Centre Logístic:
    gestionar magatzem, negociar transport i gestionar el post-enviament.

    Els protocols reals encara no estan implementats. Per això els plans reben
    objectes amb els atributs esperats dels futurs missatges.
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

        self.lots_pendents: Dict[str, LotLogistic] = {}
        self.ofertes_rebudes: Dict[str, List[RespostaOfertaTransport]] = {}
        self.eleccions_transportista: Dict[str, EleccioTransportista] = {}

        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self._carregar_ontologia()
        self._registrar_instancia_centre_logistic()

        self.capacitats = {
            "Gestionar magatzem": [
                self.pla_assignar_producte_a_lot,
            ],
            "Negociar transport": [
                self.pla_cerca_transportista,
                self.pla_transportista_escollit,
            ],
            "Gestionar post-enviament": [
                self.pla_producte_sha_enviat,
            ],
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
        """Carrega l'ontologia RDF/XML compartida pels agents."""
        if self.ontology_path.exists():
            try:
                self.graph.parse(self.ontology_path, format="xml")
            except ParserError as exc:
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _registrar_instancia_centre_logistic(self) -> None:
        """Afegeix la instància local del centre logístic al graf de treball."""
        subject = self._az(f"centre_logistic_{self.centre_logistic_id}")
        self.graph.add((subject, RDF.type, AGENTZON.CentreLogístic))
        self.graph.add((subject, AGENTZON.Id, Literal(self.centre_logistic_id)))
        self.graph.add((subject, AGENTZON.Ubicació, Literal(self.ubicacio)))

    def _az(self, term: str) -> URIRef:
        """Construeix un URIRef dins del namespace de l'ontologia AgentZon."""
        return URIRef(f"{AGENTZON}{term}")

    def pla_assignar_producte_a_lot(self, producte_localitzat: ProducteLocalitzat) -> LotLogistic:
        """
        Pla assignar producte a lot.

        Rep un ProducteLocalitzat de l'Agent Compra i l'agrupa en un Lot
        compatible per adreça de destí, prioritat i data d'enviament.
        """
        adreca = producte_localitzat.adreca.strip()
        prioritat = producte_localitzat.prioritat
        data_enviament = producte_localitzat.data_limit
        logger.debug(
            "assignant producte producte=%s comanda=%s centre_logistic=%s",
            producte_localitzat.id_producte,
            producte_localitzat.id_comanda,
            self.centre_logistic_id,
        )

        for lot in self.lots_pendents.values():
            if lot.es_compatible(adreca, prioritat, data_enviament):
                lot.productes.append(producte_localitzat)
                self._afegir_producte_localitzat_al_graf(producte_localitzat, lot)
                logger.debug(
                    "producte afegit a lot existent lot=%s producte=%s total_productes=%s",
                    lot.id,
                    producte_localitzat.id_producte,
                    len(lot.productes),
                )
                return lot

        lot = LotLogistic(
            id=str(uuid.uuid4()),
            centre_logistic_id=self.centre_logistic_id,
            adreca=adreca,
            prioritat=prioritat,
            data_enviament=data_enviament,
            productes=[producte_localitzat],
        )
        self.lots_pendents[lot.id] = lot
        self.ofertes_rebudes[lot.id] = []
        self._afegir_lot_al_graf(lot)
        self._afegir_producte_localitzat_al_graf(producte_localitzat, lot)
        logger.debug(
            "lot creat lot=%s centre_logistic=%s producte=%s adreca=%s prioritat=%s data=%s",
            lot.id,
            self.centre_logistic_id,
            producte_localitzat.id_producte,
            adreca,
            prioritat,
            data_enviament,
        )
        return lot

    def pla_cerca_transportista(self, id_lot: str) -> PeticioTransport:
        """
        Pla cerca de transportista.

        Prepara la PeticióTransport associada a un Lot pendent. No contacta
        transportistes; aquesta comunicació pertany al protocol futur.
        """
        lot = self._obtenir_lot(id_lot)
        if not lot.productes:
            raise ValueError(f"El lot {id_lot} no té productes.")

        lot.estat = "NEGOCIANT_TRANSPORT"
        peticio = PeticioTransport(
            id_lot=lot.id,
            centre_logistic_id=self.centre_logistic_id,
            adreca=lot.adreca,
            data_enviament=lot.data_enviament,
            pes=lot.pes_total,
            prioritat=lot.prioritat,
        )
        self._afegir_peticio_transport_al_graf(peticio)
        logger.debug(
            "peticio transport lot=%s pes=%s prioritat=%s data=%s",
            peticio.id_lot,
            peticio.pes,
            peticio.prioritat,
            peticio.data_enviament,
        )
        return peticio

    def registrar_oferta_transport(self, resposta_oferta_transport: RespostaOfertaTransport) -> RespostaOfertaTransport:
        """
        Registra una RespostaOfertaTransport rebuda pel centre logístic.

        Aquest mètode representa la recepció via RepOferta, però no implementa
        cap agent transportista.
        """
        id_lot = resposta_oferta_transport.id_lot
        self._obtenir_lot(id_lot)

        self.ofertes_rebudes.setdefault(id_lot, []).append(resposta_oferta_transport)
        self._afegir_oferta_al_graf(resposta_oferta_transport)
        logger.debug(
            "oferta transport rebuda lot=%s transportista=%s cost=%s data=%s",
            resposta_oferta_transport.id_lot,
            resposta_oferta_transport.transportista_id,
            resposta_oferta_transport.cost,
            resposta_oferta_transport.data_enviament,
        )
        return resposta_oferta_transport

    def pla_transportista_escollit(self, id_lot: str) -> tuple[EleccioTransportista, List[DadesEnviamentProducte]]:
        """
        Pla transportista escollit.

        Selecciona l'oferta més barata rebuda per al Lot i registra una
        EleccióTransportista. El centre logístic no fa la feina del transportista.
        """
        lot = self._obtenir_lot(id_lot)
        ofertes = self.ofertes_rebudes.get(id_lot, [])
        logger.debug("avaluant ofertes transport lot=%s ofertes=%s", id_lot, len(ofertes))
        if not ofertes:
            raise ValueError(f"No hi ha ofertes de transport per al lot {id_lot}.")

        ofertes_dins_termini = [
            oferta for oferta in ofertes if oferta.data_enviament <= lot.data_enviament
        ]
        if not ofertes_dins_termini:
            raise ValueError(f"No hi ha ofertes de transport dins del termini per al lot {id_lot}.")

        millor_oferta = min(ofertes_dins_termini, key=lambda oferta: oferta.cost)
        eleccio = EleccioTransportista(
            id_lot=id_lot,
            transportista_id=millor_oferta.transportista_id,
            cost=millor_oferta.cost,
            data_enviament=millor_oferta.data_enviament,
        )
        self.eleccions_transportista[id_lot] = eleccio
        lot.estat = "TRANSPORTISTA_ESCOLLIT"
        self._afegir_eleccio_al_graf(eleccio)
        logger.debug(
            "transportista escollit lot=%s transportista=%s cost=%s data=%s",
            eleccio.id_lot,
            eleccio.transportista_id,
            eleccio.cost,
            eleccio.data_enviament,
        )
        return eleccio, self._crear_dades_enviament_productes(lot, eleccio)

    def pla_producte_sha_enviat(self, today: Optional[str] = None) -> List[PeticioCobramentProducte]:
        """
        Pla producte s'ha enviat.

        Identifica els lots amb data d'enviament igual a avui i els marca com
        enviats. Retorna les peticions que cal enviar a l'Agent Cobrador perquè
        cobri cada producte enviat al seu usuari.
        """
        today = today or date.today().isoformat()
        peticions_cobrament = []

        for lot in self.lots_pendents.values():
            if lot.data_enviament == today and lot.estat != "ENVIAT":
                lot.estat = "ENVIAT"
                logger.debug("lot enviat lot=%s productes=%s data=%s", lot.id, len(lot.productes), today)
                for producte in lot.productes:
                    peticions_cobrament.append(
                        PeticioCobramentProducte(
                            userid=producte.userid,
                            id_comanda=producte.id_comanda,
                            id_producte=producte.id_producte,
                            import_cobrament=producte.import_producte,
                        )
                    )

        return peticions_cobrament

    def cercar_transportistes(self) -> List[Dict[str, object]]:
        logger.debug("cercant transportistes al directori centre_logistic=%s", self.centre_logistic_id)
        content = build_search_action(agent_type="AgentTransportista")
        request = build_message(
            "request",
            self.uri,
            AGENTZON.directory_agent,
            content,
            msgcnt=1,
        )
        response = self.message_sender(self.directory_address, request)
        props = get_message_properties(response)
        if not props or props.get("performative") != "inform":
            logger.debug("resposta cerca transportistes no inform performative=%s", props.get("performative") if props else None)
            return []
        transportistes = read_directory_responses(response)
        logger.debug("transportistes trobats count=%s", len(transportistes))
        return transportistes

    def negociar_transport_amb_transportistes(self, id_lot: str) -> tuple[EleccioTransportista, List[DadesEnviamentProducte]]:
        peticio = self.pla_cerca_transportista(id_lot)
        transportistes = self.cercar_transportistes()
        if not transportistes:
            raise ValueError("No s'ha trobat cap AgentTransportista al DirectoryAgent.")

        for transportista in transportistes:
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
                oferta = read_resposta_oferta_transport(response, props["content"])
                self.registrar_oferta_transport(oferta)
            else:
                logger.debug(
                    "transportista sense oferta valida lot=%s transportista=%s performative=%s",
                    id_lot,
                    transportista["name"],
                    props.get("performative") if props else None,
                )

        return self.pla_transportista_escollit(id_lot)

    def _obtenir_lot(self, id_lot: str) -> LotLogistic:
        if id_lot not in self.lots_pendents:
            raise ValueError(f"Lot desconegut: {id_lot}")
        return self.lots_pendents[id_lot]

    def _crear_dades_enviament_productes(
        self,
        lot: LotLogistic,
        eleccio: EleccioTransportista,
    ) -> List[DadesEnviamentProducte]:
        return [
            DadesEnviamentProducte(
                id_lot=lot.id,
                id_comanda=producte.id_comanda,
                userid=producte.userid,
                id_producte=producte.id_producte,
                transportista_id=eleccio.transportista_id,
                data_entrega_definitiva=eleccio.data_enviament,
            )
            for producte in lot.productes
        ]

    def _afegir_lot_al_graf(self, lot: LotLogistic) -> None:
        lot_subject = self._az(f"lot_{lot.id}")
        centre_subject = self._az(f"centre_logistic_{self.centre_logistic_id}")
        self.graph.add((lot_subject, RDF.type, AGENTZON.Lot))
        self.graph.add((lot_subject, AGENTZON.Id, Literal(lot.id)))
        self.graph.add((lot_subject, AGENTZON.DataEnviament, Literal(lot.data_enviament, datatype=XSD.dateTime)))
        self.graph.add((centre_subject, AGENTZON.Distribueix, lot_subject))

    def _afegir_producte_localitzat_al_graf(self, producte_localitzat: ProducteLocalitzat, lot: LotLogistic) -> None:
        producte_id = getattr(producte_localitzat, "id_producte", "")
        if not producte_id:
            return

        producte_subject = self._az(f"producte_localitzat_{lot.id}_{producte_id}")
        centre_subject = self._az(f"centre_logistic_{self.centre_logistic_id}")
        self.graph.add((producte_subject, RDF.type, AGENTZON.ProducteLocalitzat))
        self.graph.add((producte_subject, AGENTZON.Adreça, Literal(lot.adreca)))
        self.graph.add((producte_subject, AGENTZON.DataEnviament, Literal(lot.data_enviament, datatype=XSD.dateTime)))
        self.graph.add((centre_subject, AGENTZON.RepAvís, producte_subject))

    def _afegir_peticio_transport_al_graf(self, peticio: PeticioTransport) -> None:
        peticio_subject = self._az(f"peticio_transport_{peticio.id_lot}")
        centre_subject = self._az(f"centre_logistic_{self.centre_logistic_id}")
        self.graph.add((peticio_subject, RDF.type, AGENTZON.PeticióTransport))
        self.graph.add((peticio_subject, AGENTZON.Pes, Literal(peticio.pes, datatype=XSD.float)))
        self.graph.add(
            (peticio_subject, AGENTZON.DataEnviament, Literal(peticio.data_enviament, datatype=XSD.dateTime))
        )
        self.graph.add((centre_subject, AGENTZON.Negocia, peticio_subject))

    def _afegir_oferta_al_graf(self, oferta: RespostaOfertaTransport) -> None:
        oferta_subject = self._az(f"resposta_oferta_transport_{oferta.id_lot}_{oferta.transportista_id}")
        centre_subject = self._az(f"centre_logistic_{self.centre_logistic_id}")
        self.graph.add((oferta_subject, RDF.type, AGENTZON.RespostaOfertaTransport))
        self.graph.add((centre_subject, AGENTZON.RepOferta, oferta_subject))

    def _afegir_eleccio_al_graf(self, eleccio: EleccioTransportista) -> None:
        eleccio_subject = self._az(f"eleccio_transportista_{eleccio.id_lot}")
        transportista_subject = self._az(f"transportista_{eleccio.transportista_id}")
        self.graph.add((eleccio_subject, RDF.type, AGENTZON.EleccióTransportista))
        self.graph.add((transportista_subject, RDF.type, AGENTZON.Transportista))
        self.graph.add((transportista_subject, AGENTZON.ÉsEscollit, eleccio_subject))


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
                content = build_lot_assignat_response(lot.id, producte.id_producte)
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
