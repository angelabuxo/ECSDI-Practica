# Aquest fitxer defineix els objectes que viatgen dins dels protocols de
# l'Agent Centre Logístic. La comunicació FIPA-ACL es podrà afegir més endavant;
# aquí només representem el contingut dels missatges segons l'ontologia.
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
        prioritat: int,
        data_limit: str,
        pes: float,
        import_producte: float,
    ):
        self.id_producte = id_producte
        self.id_comanda = id_comanda
        self.userid = userid
        self.adreca = adreca
        self.prioritat = prioritat
        self.data_limit = data_limit
        self.pes = pes
        self.import_producte = import_producte


class PeticioTransport:
    """Petició que el Centre Logístic prepara per negociar el transport d'un lot."""

    def __init__(self, id_lot: str, centre_logistic_id: str, adreca: str, data_enviament: str, pes: float, prioritat: int):
        self.id_lot = id_lot
        self.centre_logistic_id = centre_logistic_id
        self.adreca = adreca
        self.data_enviament = data_enviament
        self.pes = pes
        self.prioritat = prioritat


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
    graph.add((subject, AGENTZON.Prioritat, Literal(producte.prioritat, datatype=XSD.integer)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(producte.data_limit, datatype=XSD.dateTime)))
    graph.add((subject, AGENTZON.Pes, Literal(producte.pes, datatype=XSD.float)))
    graph.add((subject, AGENTZON.Preu, Literal(producte.import_producte, datatype=XSD.float)))
    return graph


def read_producte_localitzat(graph: Graph, subject: URIRef) -> ProducteLocalitzat:
    return ProducteLocalitzat(
        id_producte=str(graph.value(subject, AGENTZON.IdProducte)),
        id_comanda=str(graph.value(subject, AGENTZON.IdComanda)),
        userid=str(graph.value(subject, AGENTZON.IdUsuari)),
        adreca=str(graph.value(subject, AGENTZON.Adreça)),
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
    subject = URIRef(f"{AGENTZON}peticio_transport_{peticio.id_lot}")
    graph.add((subject, RDF.type, AGENTZON.PeticióTransport))
    graph.add((subject, AGENTZON.IdLot, Literal(peticio.id_lot)))
    graph.add((subject, AGENTZON.IdCentreLogistic, Literal(peticio.centre_logistic_id)))
    graph.add((subject, AGENTZON.Adreça, Literal(peticio.adreca)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(peticio.data_enviament, datatype=XSD.dateTime)))
    graph.add((subject, AGENTZON.Pes, Literal(peticio.pes, datatype=XSD.float)))
    graph.add((subject, AGENTZON.Prioritat, Literal(peticio.prioritat, datatype=XSD.integer)))
    return graph


def read_peticio_transport(graph: Graph, subject: URIRef) -> PeticioTransport:
    return PeticioTransport(
        id_lot=str(graph.value(subject, AGENTZON.IdLot)),
        centre_logistic_id=str(graph.value(subject, AGENTZON.IdCentreLogistic)),
        adreca=str(graph.value(subject, AGENTZON.Adreça)),
        data_enviament=str(graph.value(subject, AGENTZON.DataEnviament)),
        pes=float(graph.value(subject, AGENTZON.Pes).toPython()),
        prioritat=int(graph.value(subject, AGENTZON.Prioritat).toPython()),
    )


def build_resposta_oferta_transport_action(oferta: RespostaOfertaTransport) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = URIRef(f"{AGENTZON}resposta_oferta_transport_{oferta.id_lot}_{oferta.transportista_id}")
    graph.add((subject, RDF.type, AGENTZON.RespostaOfertaTransport))
    graph.add((subject, AGENTZON.IdLot, Literal(oferta.id_lot)))
    graph.add((subject, AGENTZON.IdTransportista, Literal(oferta.transportista_id)))
    graph.add((subject, AGENTZON.CostBase, Literal(oferta.cost, datatype=XSD.float)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(oferta.data_enviament, datatype=XSD.dateTime)))
    return graph


def read_resposta_oferta_transport(graph: Graph, subject: URIRef) -> RespostaOfertaTransport:
    return RespostaOfertaTransport(
        id_lot=str(graph.value(subject, AGENTZON.IdLot)),
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
    graph.add((subject, AGENTZON.DataEnviament, Literal(dades.data_entrega_definitiva, datatype=XSD.dateTime)))
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
    return (data + timedelta(days=dies)).isoformat()
