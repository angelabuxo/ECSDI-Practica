# Aquest fitxer defineix els objectes que viatgen dins dels protocols de
# l'Agent Centre Logístic. El contingut dels missatges es serialitza en RDF
# tipat amb concepts de l'ontologia AgentZon; la capçalera FIPA-ACL es construeix
# amb build_message (veure protocols.fipa_acl).
from datetime import datetime, timedelta

from rdflib import Graph, Literal, RDF, URIRef, XSD

from AgentZon.config import AGENTZON


class ProducteLocalitzat:
    """Missatge de l'Agent Compra al Centre Logístic per enviar un producte."""

    def __init__(
        self,
        id_producte: str,
        id_comanda: str,
        userid: str,
        adreca: str,
        ciutat: str,
        prioritat: int,
        data_limit: str,
        pes: float,
        import_producte: float,
    ):
        self.id_producte = id_producte
        self.id_comanda = id_comanda
        self.userid = userid
        self.adreca = adreca
        self.ciutat = ciutat
        self.prioritat = prioritat
        self.data_limit = data_limit
        self.pes = pes
        self.import_producte = import_producte


class PeticioTransport:
    """Petició de cotització per transport basada en destinació i pes."""

    def __init__(self, centre_logistic_id: str, ciutat_desti: str, data_enviament: str, pes: float):
        self.centre_logistic_id = centre_logistic_id
        self.ciutat_desti = ciutat_desti
        self.data_enviament = data_enviament
        self.pes = pes


class RespostaOfertaTransport:
    """Oferta rebuda d'un transportista extern per a un lot."""

    def __init__(self, id_lot: str, transportista_id: str, cost: float, data_enviament: str):
        self.id_lot = id_lot
        self.transportista_id = transportista_id
        self.cost = cost
        self.data_enviament = data_enviament


class EleccioTransportista:
    """Resultat de la selecció del transportista per part del Centre Logístic."""

    def __init__(self, id_lot: str, transportista_id: str, cost: float, data_enviament: str):
        self.id_lot = id_lot
        self.transportista_id = transportista_id
        self.cost = cost
        self.data_enviament = data_enviament


class DadesEnviamentProducte:
    """Missatge del Centre Logístic a l'Agent Compra amb les dades definitives d'enviament."""

    def __init__(
        self,
        id_lot: str,
        id_comanda: str,
        userid: str,
        id_producte: str,
        transportista_id: str,
        data_entrega_definitiva: str,
    ):
        self.id_lot = id_lot
        self.id_comanda = id_comanda
        self.userid = userid
        self.id_producte = id_producte
        self.transportista_id = transportista_id
        self.data_entrega_definitiva = data_entrega_definitiva


class PeticioCobramentProducte:
    """Petició del Centre Logístic a l'Agent Cobrador quan un producte s'ha enviat."""

    def __init__(self, userid: str, id_comanda: str, id_producte: str, import_cobrament: float):
        self.userid = userid
        self.id_comanda = id_comanda
        self.id_producte = id_producte
        self.import_cobrament = import_cobrament


def build_producte_localitzat_action(producte: ProducteLocalitzat) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = URIRef(f"{AGENTZON}producte_localitzat_{producte.id_comanda}_{producte.id_producte}")
    graph.add((subject, RDF.type, AGENTZON.ProducteLocalitzat))
    graph.add((subject, AGENTZON.IdProducte, Literal(producte.id_producte)))
    graph.add((subject, AGENTZON.IdComanda, Literal(producte.id_comanda)))
    graph.add((subject, AGENTZON.IdUsuari, Literal(producte.userid)))
    graph.add((subject, AGENTZON.Adreça, Literal(producte.adreca)))
    graph.add((subject, AGENTZON.Ciutat, Literal(producte.ciutat)))
    graph.add((subject, AGENTZON.Prioritat, Literal(producte.prioritat, datatype=XSD.integer)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(producte.data_limit, datatype=XSD.date)))
    graph.add((subject, AGENTZON.Pes, Literal(producte.pes, datatype=XSD.float)))
    graph.add((subject, AGENTZON.Preu, Literal(producte.import_producte, datatype=XSD.float)))
    return graph


def read_producte_localitzat(graph: Graph, subject: URIRef) -> ProducteLocalitzat:
    ciutat = graph.value(subject, AGENTZON.Ciutat)
    return ProducteLocalitzat(
        id_producte=str(graph.value(subject, AGENTZON.IdProducte)),
        id_comanda=str(graph.value(subject, AGENTZON.IdComanda)),
        userid=str(graph.value(subject, AGENTZON.IdUsuari)),
        adreca=str(graph.value(subject, AGENTZON.Adreça)),
        ciutat=str(ciutat if ciutat is not None else graph.value(subject, AGENTZON.Adreça)),
        prioritat=int(graph.value(subject, AGENTZON.Prioritat).toPython()),
        data_limit=str(graph.value(subject, AGENTZON.DataEnviament)),
        pes=float(graph.value(subject, AGENTZON.Pes).toPython()),
        import_producte=float(graph.value(subject, AGENTZON.Preu).toPython()),
    )


def build_lot_assignat_response(id_lot: str, id_producte: str) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = URIRef(f"{AGENTZON}lot_assignat_{id_lot}_{id_producte}")
    graph.add((subject, RDF.type, AGENTZON.Lot))
    graph.add((subject, AGENTZON.IdLot, Literal(id_lot)))
    graph.add((subject, AGENTZON.IdProducte, Literal(id_producte)))
    return graph


def read_lot_assignat_response(graph: Graph, subject: URIRef) -> dict:
    return {
        "id_lot": str(graph.value(subject, AGENTZON.IdLot)),
        "id_producte": str(graph.value(subject, AGENTZON.IdProducte)),
    }


def build_peticio_transport_action(peticio: PeticioTransport) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    token = f"{peticio.centre_logistic_id}_{peticio.ciutat_desti}_{peticio.data_enviament}_{peticio.pes}".replace(" ", "_")
    subject = URIRef(f"{AGENTZON}peticio_transport_{token}")
    graph.add((subject, RDF.type, AGENTZON.PeticioTransport))
    graph.add((subject, AGENTZON.IdCentreLogistic, Literal(peticio.centre_logistic_id)))
    graph.add((subject, AGENTZON.Ciutat, Literal(peticio.ciutat_desti)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(peticio.data_enviament, datatype=XSD.date)))
    graph.add((subject, AGENTZON.Pes, Literal(peticio.pes, datatype=XSD.float)))
    return graph


def read_peticio_transport(graph: Graph, subject: URIRef) -> PeticioTransport:
    return PeticioTransport(
        centre_logistic_id=str(graph.value(subject, AGENTZON.IdCentreLogistic)),
        ciutat_desti=str(graph.value(subject, AGENTZON.Ciutat)),
        data_enviament=str(graph.value(subject, AGENTZON.DataEnviament)),
        pes=float(graph.value(subject, AGENTZON.Pes).toPython()),
    )


def build_resposta_oferta_transport_action(oferta: RespostaOfertaTransport) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    id_oferta = oferta.id_lot if oferta.id_lot else "sense_lot"
    subject = URIRef(f"{AGENTZON}resposta_oferta_transport_{id_oferta}_{oferta.transportista_id}")
    graph.add((subject, RDF.type, AGENTZON.RespostaOfertaTransport))
    if oferta.id_lot:
        graph.add((subject, AGENTZON.IdLot, Literal(oferta.id_lot)))
    graph.add((subject, AGENTZON.IdTransportista, Literal(oferta.transportista_id)))
    graph.add((subject, AGENTZON.CostBase, Literal(oferta.cost, datatype=XSD.float)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(oferta.data_enviament, datatype=XSD.date)))
    return graph


def read_resposta_oferta_transport(graph: Graph, subject: URIRef) -> RespostaOfertaTransport:
    id_lot = graph.value(subject, AGENTZON.IdLot)
    return RespostaOfertaTransport(
        id_lot=str(id_lot) if id_lot is not None else "",
        transportista_id=str(graph.value(subject, AGENTZON.IdTransportista)),
        cost=float(graph.value(subject, AGENTZON.CostBase).toPython()),
        data_enviament=str(graph.value(subject, AGENTZON.DataEnviament)),
    )


def build_dades_enviament_action(dades: DadesEnviamentProducte) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = URIRef(f"{AGENTZON}dades_enviament_{dades.id_comanda}_{dades.id_producte}")
    graph.add((subject, RDF.type, AGENTZON.DadesEnviamentProducte))
    graph.add((subject, AGENTZON.IdLot, Literal(dades.id_lot)))
    graph.add((subject, AGENTZON.IdComanda, Literal(dades.id_comanda)))
    graph.add((subject, AGENTZON.IdUsuari, Literal(dades.userid)))
    graph.add((subject, AGENTZON.IdProducte, Literal(dades.id_producte)))
    graph.add((subject, AGENTZON.IdTransportista, Literal(dades.transportista_id)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(dades.data_entrega_definitiva, datatype=XSD.date)))
    return graph


def read_dades_enviament(graph: Graph, subject: URIRef) -> DadesEnviamentProducte:
    return DadesEnviamentProducte(
        id_lot=str(graph.value(subject, AGENTZON.IdLot)),
        id_comanda=str(graph.value(subject, AGENTZON.IdComanda)),
        userid=str(graph.value(subject, AGENTZON.IdUsuari)),
        id_producte=str(graph.value(subject, AGENTZON.IdProducte)),
        transportista_id=str(graph.value(subject, AGENTZON.IdTransportista)),
        data_entrega_definitiva=str(graph.value(subject, AGENTZON.DataEnviament)),
    )


def sumar_dies_iso(data_iso: str, dies: int) -> str:
    data = datetime.fromisoformat(data_iso)
    resultat = data + timedelta(days=dies)
    return resultat.date().isoformat()
