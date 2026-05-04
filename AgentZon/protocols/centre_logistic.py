from __future__ import annotations

from datetime import datetime, timedelta

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef, XSD

from AgentZon.config import AGENTZON


LOG = Namespace("urn:agentzon:logistics:")


def _literal(graph: Graph, subject: URIRef | BNode, predicate: URIRef, default=None):
    value = graph.value(subject, predicate)
    return value.toPython() if value is not None else default


def _text(value: object) -> str:
    return str(value).strip()


def _float(value: object) -> float:
    return float(value)


def _int(value: object) -> int:
    return int(value)


def _single_subject(graph: Graph, rdf_type: URIRef, error_message: str) -> URIRef | BNode:
    subject = next(graph.subjects(RDF.type, rdf_type), None)
    if subject is None:
        raise ValueError(error_message)
    return subject


def build_producte_localitzat_action(
    producte: dict,
    subject: URIRef | BNode | None = None,
) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("log", LOG)
    subject = subject or URIRef(
        f"{AGENTZON}producte_localitzat_{producte['id_comanda']}_{producte['id_producte']}"
    )
    graph.add((subject, RDF.type, AGENTZON.ProducteLocalitzat))
    graph.add((subject, AGENTZON.IdProducte, Literal(_text(producte["id_producte"]))))
    graph.add((subject, AGENTZON.Localitza, AGENTZON[_text(producte["id_producte"])]))
    graph.add((subject, AGENTZON.IdComanda, Literal(_text(producte["id_comanda"]))))
    graph.add((subject, AGENTZON.IdUsuari, Literal(_text(producte["userid"]))))
    graph.add((subject, AGENTZON.Adreça, Literal(_text(producte["adreca"]))))
    graph.add((subject, AGENTZON.Ciutat, Literal(_text(producte["ciutat"]))))
    graph.add((subject, AGENTZON.Prioritat, Literal(_int(producte["prioritat"]), datatype=XSD.integer)))
    graph.add((subject, AGENTZON.DataEnviament, Literal(_text(producte["data_limit"]), datatype=XSD.date)))
    graph.add((subject, AGENTZON.Pes, Literal(_float(producte["pes"]), datatype=XSD.float)))
    graph.add((subject, AGENTZON.Preu, Literal(_float(producte["import_producte"]), datatype=XSD.float)))
    return graph


def get_producte_localitzat_subject(graph: Graph) -> URIRef | BNode:
    return _single_subject(graph, AGENTZON.ProducteLocalitzat, "No s'ha trobat cap ProducteLocalitzat al graf.")


def read_producte_localitzat(graph: Graph, subject: URIRef | BNode) -> dict:
    ciutat = _literal(graph, subject, AGENTZON.Ciutat, "")
    adreca = _literal(graph, subject, AGENTZON.Adreça, "")
    return {
        "subject": subject,
        "id_producte": _text(_literal(graph, subject, AGENTZON.IdProducte, "")),
        "id_comanda": _text(_literal(graph, subject, AGENTZON.IdComanda, "")),
        "userid": _text(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "adreca": _text(adreca),
        "ciutat": _text(ciutat or adreca),
        "prioritat": _int(_literal(graph, subject, AGENTZON.Prioritat, 0) or 0),
        "data_limit": _text(_literal(graph, subject, AGENTZON.DataEnviament, "")),
        "pes": _float(_literal(graph, subject, AGENTZON.Pes, 0.0) or 0.0),
        "import_producte": _float(_literal(graph, subject, AGENTZON.Preu, 0.0) or 0.0),
    }


def build_lot_assignat_response(id_lot: str, id_producte: str, subject: URIRef | BNode | None = None) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    subject = subject or URIRef(f"{AGENTZON}lot_{id_lot}")
    graph.add((subject, RDF.type, AGENTZON.Lot))
    graph.add((subject, AGENTZON.IdLot, Literal(_text(id_lot))))
    graph.add((subject, AGENTZON.TeProducte, AGENTZON[_text(id_producte)]))
    return graph


def read_lot_assignat_response(graph: Graph, subject: URIRef | BNode) -> dict:
    producte_uri = graph.value(subject, AGENTZON.TeProducte)
    fragment = ""
    if producte_uri is not None:
        producte_str = str(producte_uri)
        fragment = producte_str.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return {
        "subject": subject,
        "id_lot": _text(_literal(graph, subject, AGENTZON.IdLot, "")),
        "id_producte": fragment,
    }


def build_peticio_transport_action(peticio: dict, subject: URIRef | BNode | None = None) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("log", LOG)
    token = (
        f"{peticio['centre_logistic_id']}_{peticio['ciutat_desti']}_{peticio['data_enviament']}_{peticio['pes']}"
    ).replace(" ", "_")
    subject = subject or URIRef(f"{AGENTZON}peticio_transport_{token}")
    graph.add((subject, RDF.type, AGENTZON.PeticioTransport))
    graph.add((subject, AGENTZON.IdCentreLogistic, Literal(_text(peticio["centre_logistic_id"]))))
    graph.add((subject, AGENTZON.Ciutat, Literal(_text(peticio["ciutat_desti"]))))
    graph.add((subject, AGENTZON.DataEnviament, Literal(_text(peticio["data_enviament"]), datatype=XSD.date)))
    graph.add((subject, AGENTZON.Pes, Literal(_float(peticio["pes"]), datatype=XSD.float)))
    return graph


def get_peticio_transport_subject(graph: Graph) -> URIRef | BNode:
    return _single_subject(graph, AGENTZON.PeticioTransport, "No s'ha trobat cap PeticioTransport al graf.")


def read_peticio_transport(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "centre_logistic_id": _text(_literal(graph, subject, AGENTZON.IdCentreLogistic, "")),
        "ciutat_desti": _text(_literal(graph, subject, AGENTZON.Ciutat, "")),
        "data_enviament": _text(_literal(graph, subject, AGENTZON.DataEnviament, "")),
        "pes": _float(_literal(graph, subject, AGENTZON.Pes, 0.0) or 0.0),
    }


def build_resposta_oferta_transport_action(
    oferta: dict,
    subject: URIRef | BNode | None = None,
    oferta_subject: URIRef | BNode | None = None,
) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("log", LOG)
    id_lot = _text(oferta.get("id_lot", "")) or "sense_lot"
    transportista_id = _text(oferta["transportista_id"])
    token = f"{id_lot}_{transportista_id}_{oferta['data_enviament']}_{oferta['cost']}".replace(" ", "_")
    subject = subject or URIRef(f"{AGENTZON}resposta_oferta_transport_{token}")
    oferta_subject = oferta_subject or URIRef(f"{AGENTZON}oferta_transport_{token}")

    graph.add((subject, RDF.type, AGENTZON.RespostaOfertaTransport))
    graph.add((subject, AGENTZON.Proposa, oferta_subject))
    graph.add((subject, AGENTZON.IdTransportista, Literal(transportista_id)))

    graph.add((oferta_subject, RDF.type, AGENTZON.OfertaTransport))
    graph.add((oferta_subject, AGENTZON.CostBase, Literal(_float(oferta["cost"]), datatype=XSD.float)))
    graph.add(
        (oferta_subject, AGENTZON.DataEnviament, Literal(_text(oferta["data_enviament"]), datatype=XSD.date))
    )

    if _text(oferta.get("id_lot", "")):
        graph.add((subject, AGENTZON.IdLot, Literal(_text(oferta["id_lot"]))))
    return graph


def get_resposta_oferta_transport_subject(graph: Graph) -> URIRef | BNode:
    return _single_subject(
        graph,
        AGENTZON.RespostaOfertaTransport,
        "No s'ha trobat cap RespostaOfertaTransport al graf.",
    )


def read_resposta_oferta_transport(graph: Graph, subject: URIRef | BNode) -> dict:
    nucli = graph.value(subject, AGENTZON.Proposa)
    cost = _literal(graph, nucli, AGENTZON.CostBase) if nucli is not None else None
    data_enviament = _literal(graph, nucli, AGENTZON.DataEnviament) if nucli is not None else None
    if cost is None:
        cost = _literal(graph, subject, AGENTZON.CostBase, 0.0)
    if data_enviament is None:
        data_enviament = _literal(graph, subject, AGENTZON.DataEnviament, "")
    return {
        "subject": subject,
        "id_lot": _text(_literal(graph, subject, AGENTZON.IdLot, "")),
        "transportista_id": _text(_literal(graph, subject, AGENTZON.IdTransportista, "")),
        "cost": _float(cost or 0.0),
        "data_enviament": _text(data_enviament),
    }


def build_eleccio_transportista_action(
    eleccio: dict,
    subject: URIRef | BNode | None = None,
) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("log", LOG)
    subject = subject or URIRef(f"{AGENTZON}eleccio_transportista_{eleccio['id_lot']}")
    graph.add((subject, RDF.type, AGENTZON["EleccióTransportista"]))
    graph.add((subject, AGENTZON.IdLot, Literal(_text(eleccio["id_lot"]))))
    graph.add((subject, AGENTZON.IdTransportista, Literal(_text(eleccio["transportista_id"]))))
    graph.add((subject, AGENTZON.CostBase, Literal(_float(eleccio["cost"]), datatype=XSD.float)))
    graph.add(
        (subject, AGENTZON.DataEnviament, Literal(_text(eleccio["data_enviament"]), datatype=XSD.date))
    )
    return graph


def get_eleccio_transportista_subject(graph: Graph) -> URIRef | BNode:
    return _single_subject(
        graph,
        AGENTZON["EleccióTransportista"],
        "No s'ha trobat cap EleccióTransportista al graf.",
    )


def read_eleccio_transportista(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "id_lot": _text(_literal(graph, subject, AGENTZON.IdLot, "")),
        "transportista_id": _text(_literal(graph, subject, AGENTZON.IdTransportista, "")),
        "cost": _float(_literal(graph, subject, AGENTZON.CostBase, 0.0) or 0.0),
        "data_enviament": _text(_literal(graph, subject, AGENTZON.DataEnviament, "")),
    }


def build_dades_enviament_action(dades: dict, subject: URIRef | BNode | None = None) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("log", LOG)
    subject = subject or URIRef(f"{AGENTZON}dades_enviament_{dades['id_comanda']}_{dades['id_producte']}")
    graph.add((subject, RDF.type, AGENTZON.DadesEnviamentProducte))
    graph.add((subject, AGENTZON.IdLot, Literal(_text(dades["id_lot"]))))
    graph.add((subject, AGENTZON.IdComanda, Literal(_text(dades["id_comanda"]))))
    graph.add((subject, AGENTZON.IdUsuari, Literal(_text(dades["userid"]))))
    graph.add((subject, AGENTZON.IdProducte, Literal(_text(dades["id_producte"]))))
    graph.add((subject, AGENTZON.IdTransportista, Literal(_text(dades["transportista_id"]))))
    graph.add(
        (
            subject,
            AGENTZON.DataEntregaDefinitiva,
            Literal(_text(dades["data_entrega_definitiva"]), datatype=XSD.date),
        )
    )
    return graph


def get_dades_enviament_subject(graph: Graph) -> URIRef | BNode:
    return _single_subject(
        graph,
        AGENTZON.DadesEnviamentProducte,
        "No s'ha trobat cap DadesEnviamentProducte al graf.",
    )


def read_dades_enviament(graph: Graph, subject: URIRef | BNode) -> dict:
    data_definitiva = _literal(graph, subject, AGENTZON.DataEntregaDefinitiva)
    if data_definitiva is None:
        data_definitiva = _literal(graph, subject, AGENTZON.DataEnviament, "")
    return {
        "subject": subject,
        "id_lot": _text(_literal(graph, subject, AGENTZON.IdLot, "")),
        "id_comanda": _text(_literal(graph, subject, AGENTZON.IdComanda, "")),
        "userid": _text(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "id_producte": _text(_literal(graph, subject, AGENTZON.IdProducte, "")),
        "transportista_id": _text(_literal(graph, subject, AGENTZON.IdTransportista, "")),
        "data_entrega_definitiva": _text(data_definitiva),
    }


def build_peticio_cobrament_action(
    peticio: dict,
    subject: URIRef | BNode | None = None,
) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("log", LOG)
    subject = subject or URIRef(
        f"{AGENTZON}peticio_cobrament_{peticio['id_comanda']}_{peticio['id_producte']}"
    )
    graph.add((subject, RDF.type, AGENTZON.PeticioCobramentProducte))
    graph.add((subject, AGENTZON.IdUsuari, Literal(_text(peticio["userid"]))))
    graph.add((subject, AGENTZON.IdComanda, Literal(_text(peticio["id_comanda"]))))
    graph.add((subject, AGENTZON.IdProducte, Literal(_text(peticio["id_producte"]))))
    graph.add((subject, AGENTZON.Preu, Literal(_float(peticio["import_cobrament"]), datatype=XSD.float)))
    return graph


def get_peticio_cobrament_subject(graph: Graph) -> URIRef | BNode:
    return _single_subject(
        graph,
        AGENTZON.PeticioCobramentProducte,
        "No s'ha trobat cap PeticioCobramentProducte al graf.",
    )


def read_peticio_cobrament(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "userid": _text(_literal(graph, subject, AGENTZON.IdUsuari, "")),
        "id_comanda": _text(_literal(graph, subject, AGENTZON.IdComanda, "")),
        "id_producte": _text(_literal(graph, subject, AGENTZON.IdProducte, "")),
        "import_cobrament": _float(_literal(graph, subject, AGENTZON.Preu, 0.0) or 0.0),
    }


def sumar_dies_iso(data_iso: str, dies: int) -> str:
    data = datetime.fromisoformat(data_iso)
    resultat = data + timedelta(days=dies)
    return resultat.date().isoformat()
