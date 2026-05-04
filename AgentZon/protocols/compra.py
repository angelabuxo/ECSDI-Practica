from __future__ import annotations

from datetime import datetime, timedelta

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef, XSD

from AgentZon.config import AGENTZON
from AgentZon.protocols.cerca import read_producte


BUY = Namespace("urn:agentzon:buy:")


def _literal(graph: Graph, subject: URIRef | BNode, predicate: URIRef, default=None):
    value = graph.value(subject, predicate)
    return value.toPython() if value is not None else default


def _prioritat_valida(prioritat: int) -> int:
    if prioritat not in [1, 2]:
        raise ValueError("Prioritat ha de ser 1 (Express) o 2 (Normal)")
    return prioritat


def _calcular_data_entrega(created_at: str, prioritat: int) -> str:
    _prioritat_valida(prioritat)
    dies = 1 if prioritat == 1 else 3
    return (datetime.fromisoformat(created_at) + timedelta(days=dies)).date().isoformat()


def build_peticio_info_usuari(userid: str, subject: URIRef | BNode | None = None) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = subject or BNode()
    graph.add((subject, RDF.type, AGENTZON.PeticioInfoUsuari))
    graph.add((subject, AGENTZON.IdUsuari, Literal(userid)))
    return graph


def read_peticio_info_usuari(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "userid": str(_literal(graph, subject, AGENTZON.IdUsuari, "")),
    }


def build_info_usuari(
    userid: str,
    adreca: str,
    ciutat: str,
    prioritat: int,
    metodepagament: str,
    subject: URIRef | BNode | None = None,
) -> Graph:
    prioritat = _prioritat_valida(prioritat)
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = subject or BNode()
    graph.add((subject, RDF.type, AGENTZON.InfoUsuari))
    graph.add((subject, AGENTZON.IdUsuari, Literal(userid)))
    graph.add((subject, AGENTZON.Adreça, Literal(adreca)))
    graph.add((subject, AGENTZON.Ciutat, Literal(ciutat)))
    graph.add((subject, AGENTZON.Prioritat, Literal(prioritat, datatype=XSD.integer)))
    graph.add((subject, AGENTZON.MetodePagament, Literal(metodepagament)))
    return graph


def read_info_usuari(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "userid": str(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "adreca": str(_literal(graph, subject, AGENTZON.Adreça, "")),
        "ciutat": str(_literal(graph, subject, AGENTZON.Ciutat, "")),
        "prioritat": int(_literal(graph, subject, AGENTZON.Prioritat, 0) or 0),
        "metodepagament": str(_literal(graph, subject, AGENTZON.MetodePagament, "")),
    }


def build_dades_enviament_usuari(
    userid: str,
    adreca: str,
    ciutat: str,
    prioritat: int,
    subject: URIRef | BNode | None = None,
) -> Graph:
    prioritat = _prioritat_valida(prioritat)
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = subject or AGENTZON[f"dades_enviament_usuari_{userid}"]
    graph.add((subject, RDF.type, AGENTZON.DadesEnviamentUsuari))
    graph.add((subject, AGENTZON.IdUsuari, Literal(userid)))
    graph.add((subject, AGENTZON.Adreça, Literal(adreca)))
    graph.add((subject, AGENTZON.Ciutat, Literal(ciutat)))
    graph.add((subject, AGENTZON.Prioritat, Literal(prioritat, datatype=XSD.integer)))
    return graph


def read_dades_enviament_usuari(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "userid": str(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "adreca": str(_literal(graph, subject, AGENTZON.Adreça, "")),
        "ciutat": str(_literal(graph, subject, AGENTZON.Ciutat, "")),
        "prioritat": int(_literal(graph, subject, AGENTZON.Prioritat, 0) or 0),
    }


def build_comanda(
    catalog_graph: Graph,
    id_comanda: str,
    productes: list[dict],
    info_usuari: dict,
    subject: URIRef | BNode | None = None,
    created_at: str | None = None,
) -> Graph:
    prioritat = _prioritat_valida(int(info_usuari["prioritat"]))
    created_at = created_at or datetime.now().replace(microsecond=0).isoformat()

    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("buy", BUY)
    subject = subject or AGENTZON[f"comanda_{id_comanda}"]

    graph.add((subject, RDF.type, AGENTZON.Comanda))
    graph.add((subject, AGENTZON.Id, Literal(id_comanda)))
    graph.add((subject, AGENTZON.IdUsuari, Literal(info_usuari["userid"])))
    graph.add((subject, AGENTZON.Adreça, Literal(info_usuari["adreca"])))
    graph.add((subject, AGENTZON.Ciutat, Literal(info_usuari["ciutat"])))
    graph.add((subject, AGENTZON.Prioritat, Literal(prioritat, datatype=XSD.integer)))
    graph.add((subject, AGENTZON.MetodePagament, Literal(info_usuari["metodepagament"])))
    graph.add((subject, BUY.created_at, Literal(created_at, datatype=XSD.dateTime)))
    graph.add((subject, BUY.estat, Literal("PENDENT")))

    for producte in productes:
        producte_uri = producte["uri"]
        if (producte_uri, RDF.type, AGENTZON.Producte) not in catalog_graph:
            raise ValueError(f"El producte {producte_uri} no existeix al catàleg.")
        graph.add((subject, AGENTZON.Te, producte_uri))

    return graph


def get_comanda_subject(graph: Graph) -> URIRef | BNode:
    subject = next(graph.subjects(RDF.type, AGENTZON.Comanda), None)
    if subject is None:
        raise ValueError("No s'ha trobat cap instància Comanda al graf.")
    return subject


def read_comanda(graph: Graph, subject: URIRef | BNode) -> dict:
    created_at = str(_literal(graph, subject, BUY.created_at, datetime.now().replace(microsecond=0).isoformat()))
    prioritat = int(_literal(graph, subject, AGENTZON.Prioritat, 0) or 0)
    productes = [read_producte(graph, producte_uri) for producte_uri in graph.objects(subject, AGENTZON.Te)]

    return {
        "subject": subject,
        "id": str(_literal(graph, subject, AGENTZON.Id, "")),
        "userid": str(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "llista_productes": productes,
        "adreca": str(_literal(graph, subject, AGENTZON.Adreça, "")),
        "ciutat": str(_literal(graph, subject, AGENTZON.Ciutat, "")),
        "prioritat": prioritat,
        "metodepagament": str(_literal(graph, subject, AGENTZON.MetodePagament, "")),
        "estat": str(_literal(graph, subject, BUY.estat, "PENDENT")),
        "import_total": sum(float(producte["preu"]) for producte in productes),
        "data_entrega_estimada": _calcular_data_entrega(created_at, prioritat) if prioritat else "",
        "created_at": created_at,
    }


def validar_comanda(graph: Graph, subject: URIRef | BNode) -> bool:
    comanda = read_comanda(graph, subject)
    if not comanda["llista_productes"]:
        return False
    if not comanda["adreca"].strip():
        return False
    if not comanda["ciutat"].strip():
        return False
    if comanda["prioritat"] not in [1, 2]:
        return False
    if not comanda["metodepagament"].strip():
        return False
    return True


def build_peticio_registre_compra(
    graph: Graph,
    comanda_subject: URIRef | BNode,
    subject: URIRef | BNode | None = None,
) -> Graph:
    comanda = read_comanda(graph, comanda_subject)
    registre_graph = Graph()
    registre_graph.bind("az", AGENTZON)
    registre_graph.bind("buy", BUY)
    subject = subject or AGENTZON[f"registre_compra_{comanda['id']}"]
    registre_graph.add((subject, RDF.type, AGENTZON.PeticioRegistreCompra))
    registre_graph.add((subject, AGENTZON.IdComanda, Literal(comanda["id"])))
    registre_graph.add((subject, AGENTZON.IdUsuari, Literal(comanda["userid"])))
    registre_graph.add((subject, AGENTZON.Prioritat, Literal(comanda["prioritat"], datatype=XSD.integer)))
    registre_graph.add((subject, BUY.data_hora_compra, Literal(comanda["created_at"], datatype=XSD.dateTime)))
    for producte in comanda["llista_productes"]:
        registre_graph.add((subject, AGENTZON.Te, producte["uri"]))
    return registre_graph


def read_peticio_registre_compra(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "id_comanda": str(_literal(graph, subject, AGENTZON.IdComanda, "")),
        "userid": str(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "prioritat": int(_literal(graph, subject, AGENTZON.Prioritat, 0) or 0),
        "data_hora_compra": str(_literal(graph, subject, BUY.data_hora_compra, "")),
        "llista_productes": [read_producte(graph, producte_uri) for producte_uri in graph.objects(subject, AGENTZON.Te)],
    }


def build_peticio_enviament_centre_logistic(
    producte: dict,
    centre_logistic: str,
    adreca: str,
    ciutat: str,
    data_limit: str,
    userid: str,
    id_comanda: str,
    prioritat: int,
    subject: URIRef | BNode | None = None,
) -> Graph:
    prioritat = _prioritat_valida(prioritat)
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("buy", BUY)
    subject = subject or BNode()
    graph.add((subject, RDF.type, AGENTZON.PeticioEnviamentCentreLogistic))
    graph.add((subject, AGENTZON.IdProducte, Literal(producte["id"])))
    graph.add((subject, AGENTZON.IdComanda, Literal(id_comanda)))
    graph.add((subject, AGENTZON.IdUsuari, Literal(userid)))
    graph.add((subject, AGENTZON.Adreça, Literal(adreca)))
    graph.add((subject, AGENTZON.Ciutat, Literal(ciutat)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(data_limit, datatype=XSD.date)))
    graph.add((subject, AGENTZON.Prioritat, Literal(prioritat, datatype=XSD.integer)))
    graph.add((subject, BUY.centre_logistic, Literal(centre_logistic)))
    return graph


def build_peticio_enviament_venedor_extern(
    producte: dict,
    venedor: str,
    adreca: str,
    ciutat: str,
    data_limit: str,
    userid: str,
    id_comanda: str,
    prioritat: int,
    subject: URIRef | BNode | None = None,
) -> Graph:
    prioritat = _prioritat_valida(prioritat)
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("buy", BUY)
    subject = subject or BNode()
    graph.add((subject, RDF.type, AGENTZON.PeticioEnviamentVenedorExtern))
    graph.add((subject, AGENTZON.IdProducte, Literal(producte["id"])))
    graph.add((subject, AGENTZON.IdComanda, Literal(id_comanda)))
    graph.add((subject, AGENTZON.IdUsuari, Literal(userid)))
    graph.add((subject, AGENTZON.Adreça, Literal(adreca)))
    graph.add((subject, AGENTZON.Ciutat, Literal(ciutat)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(data_limit, datatype=XSD.date)))
    graph.add((subject, AGENTZON.Prioritat, Literal(prioritat, datatype=XSD.integer)))
    graph.add((subject, BUY.venedor, Literal(venedor)))
    return graph


def read_peticio_enviament(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "id_producte": str(_literal(graph, subject, AGENTZON.IdProducte, "")),
        "id_comanda": str(_literal(graph, subject, AGENTZON.IdComanda, "")),
        "userid": str(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "adreca": str(_literal(graph, subject, AGENTZON.Adreça, "")),
        "ciutat": str(_literal(graph, subject, AGENTZON.Ciutat, "")),
        "data_limit": str(_literal(graph, subject, AGENTZON.DataEnviament, "")),
        "prioritat": int(_literal(graph, subject, AGENTZON.Prioritat, 0) or 0),
        "centre_logistic": _literal(graph, subject, BUY.centre_logistic),
        "venedor": _literal(graph, subject, BUY.venedor),
    }
