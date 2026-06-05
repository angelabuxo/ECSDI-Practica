"""Missatges de pagament, cobrament, registre bancari i devolucions."""

from uuid import uuid4

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces
from protocols.rdf_refs import (
    _seller_id_from_iri,
    _user_id_from_iri,
    ensure_order_node,
    link_sobre_comanda,
    order_id_from_node,
)


# Sentit del moviment de diners (vegeu azon:SentitPagament a l'ontologia).
# COBRAMENT = entrant (la botiga cobra l'usuari); PAGAMENT = sortint (la botiga
# paga un venedor extern o retorna diners a l'usuari).
SENTIT_COBRAMENT = "COBRAMENT"
SENTIT_PAGAMENT = "PAGAMENT"


# Bank-data registration -----------------------------------------------------------
def build_peticio_registre_dades_usuari(
    user_id,
    bank_data,
    payment_method,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"bank-user-request-{user_id}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreDadesBancariesUsuari))
    graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(user_id)]))
    graph.add((content, AZON.DadesBancariesUsuari, Literal(bank_data)))
    graph.add((content, AZON.MetodePagament, Literal(payment_method)))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_registre_dades_usuari(graph, content):
    return {
        "user_id": _user_id_from_iri(graph.value(content, AZON.PertanyAUsuari)),
        "bank_data": str(graph.value(content, AZON.DadesBancariesUsuari)),
        "payment_method": str(graph.value(content, AZON.MetodePagament)),
    }


def build_peticio_registre_dades_venedor(
    seller_id,
    bank_data,
    seller_name=None,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"bank-seller-request-{seller_id}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreDadesBancariesVenedor))
    graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(seller_id)]))
    graph.add((content, AZON.DadesBancariesVenedorExtern, Literal(bank_data)))
    if seller_name:
        graph.add((content, AZON.Nom, Literal(seller_name)))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_registre_dades_venedor(graph, content):
    seller_name = graph.value(content, AZON.Nom)
    return {
        "seller_id": _seller_id_from_iri(graph.value(content, AZON.PertanyAVenedorExtern)),
        "bank_data": str(graph.value(content, AZON.DadesBancariesVenedorExtern)),
        "seller_name": str(seller_name) if seller_name is not None else "",
    }


def build_peticio_consulta_dades_venedor(seller_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"seller-profile-request-{seller_id}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaDadesBancariesVenedor))
    graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(seller_id)]))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_consulta_dades_venedor(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return _seller_id_from_iri(graph.value(content, AZON.PertanyAVenedorExtern))


def build_resultat_consulta_dades_venedor(
    profile,
    sender=None,
    receiver=None,
    request_content=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"seller-profile-response-{profile['seller_id']}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.ResultatConsultaDadesBancariesVenedor))
    graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(profile["seller_id"])]))
    graph.add((content, AZON.DadesBancariesVenedorExtern, Literal(profile.get("bank_data", ""))))
    graph.add((content, AZON.Nom, Literal(profile.get("seller_name", ""))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_resultat_consulta_dades_venedor(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "seller_id": _seller_id_from_iri(graph.value(content, AZON.PertanyAVenedorExtern)),
        "bank_data": str(graph.value(content, AZON.DadesBancariesVenedorExtern) or ""),
        "seller_name": str(graph.value(content, AZON.Nom) or ""),
    }


def build_confirmacio_registre_dades(
    subject_id,
    is_external=False,
    sender=None,
    receiver=None,
    request_content=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"bank-confirmation-{subject_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreDadesBancaries))
    if is_external:
        graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(subject_id)]))
    else:
        graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(subject_id)]))
    graph.add((content, AZON.Estat, Literal("REGISTRAT")))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_confirmacio_registre_dades(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return str(graph.value(content, AZON.Estat))


# Payment action (Cobrador <-> Proveidor, Compra -> Cobrador) -----------------------
def build_peticio_pagament(payment, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"payment-request-{payment['payment_id']}"]
    graph.add((content, RDF.type, AZON.PeticioPagament))
    graph.add((content, AZON.IdPagament, Literal(payment["payment_id"])))
    link_sobre_comanda(graph, content, payment["order_id"])
    graph.add((content, AZON.ImportPagament, Literal(payment["amount"], datatype=XSD.float)))
    graph.add((content, AZON.MetodePagament, Literal(payment["method"])))
    if payment.get("sentit"):
        graph.add((content, AZON.SentitPagament, Literal(payment["sentit"])))
    if payment.get("user_id"):
        graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(payment["user_id"])]))
    if payment.get("seller_id"):
        graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(payment["seller_id"])]))
    for product_id in payment.get("product_ids", []):
        product_node = AZON[f"product-{product_id}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_pagament(graph, content):
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))
    user_id = _user_id_from_iri(graph.value(content, AZON.PertanyAUsuari))
    seller_id_iri = graph.value(content, AZON.PertanyAVenedorExtern)
    seller_id = _seller_id_from_iri(seller_id_iri)
    sentit = graph.value(content, AZON.SentitPagament)
    return {
        "payment_id": str(graph.value(content, AZON.IdPagament)),
        "order_id": order_id_from_node(graph, content),
        "amount": float(graph.value(content, AZON.ImportPagament)),
        "method": str(graph.value(content, AZON.MetodePagament)),
        "sentit": str(sentit) if sentit is not None else None,
        "user_id": str(user_id) if user_id is not None else None,
        "seller_id": str(seller_id) if seller_id is not None else None,
        "product_ids": sorted(product_ids),
    }


def _add_invoice_product_lines(graph, subject, products):
    for product in products:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((subject, AZON.SobreProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
        graph.add((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))


def _parse_invoice_lines(graph, content):
    lines = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        price_value = graph.value(product_node, AZON.Preu)
        name = graph.value(product_node, AZON.Nom)
        lines.append(
            {
                "product_id": str(product_id),
                "name": str(name) if name is not None else str(product_id),
                "price": float(price_value) if price_value is not None else 0.0,
            }
        )
    transport_cost = graph.value(content, AZON.CostTransport)
    products_subtotal = round(sum(line["price"] for line in lines), 2)
    return {
        "lines": sorted(lines, key=lambda line: line["product_id"]),
        "transport_cost": float(transport_cost) if transport_cost is not None else 0.0,
        "products_subtotal": products_subtotal,
    }


def extract_invoice_from_content(graph, content):
    payment_id = graph.value(content, AZON.IdPagament)
    if payment_id is None:
        return None
    amount = graph.value(content, AZON.ImportPagament)
    line_data = _parse_invoice_lines(graph, content)
    amount_value = float(amount) if amount is not None else line_data["products_subtotal"] + line_data["transport_cost"]
    if not line_data["products_subtotal"] and amount_value:
        line_data["products_subtotal"] = round(max(amount_value - line_data["transport_cost"], 0.0), 2)
    return {
        "payment_id": str(payment_id),
        "order_id": order_id_from_node(graph, content),
        "amount": amount_value,
        "method": str(graph.value(content, AZON.MetodePagament) or ""),
        "sentit": str(graph.value(content, AZON.SentitPagament) or ""),
        "status": str(graph.value(content, AZON.Estat) or ""),
        "date": str(graph.value(content, AZON.DataPagament) or ""),
        **line_data,
    }


def embed_invoice_in_content(graph, content, invoice):
    graph.add((content, AZON.IdPagament, Literal(invoice["payment_id"])))
    graph.add((content, AZON.ImportPagament, Literal(invoice["amount"], datatype=XSD.float)))
    graph.add((content, AZON.MetodePagament, Literal(invoice["method"])))
    if invoice.get("sentit"):
        graph.add((content, AZON.SentitPagament, Literal(invoice["sentit"])))
    graph.add((content, AZON.Estat, Literal(invoice.get("status", "PAGAT"))))
    graph.add((content, AZON.DataPagament, Literal(invoice["date"])))
    graph.add((content, AZON.CostTransport, Literal(invoice["transport_cost"], datatype=XSD.float)))
    for line in invoice.get("lines", []):
        _add_invoice_product_lines(graph, content, [line])


def build_confirmacio_pagament(payment, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"payment-confirmation-{payment['payment_id']}"]
    graph.add((content, RDF.type, AZON.ConfirmacioPagament))
    graph.add((content, AZON.IdPagament, Literal(payment["payment_id"])))
    if payment.get("order_id"):
        link_sobre_comanda(graph, content, payment["order_id"])
    graph.add((content, AZON.ImportPagament, Literal(payment["amount"], datatype=XSD.float)))
    graph.add((content, AZON.MetodePagament, Literal(payment["method"])))
    if payment.get("sentit"):
        graph.add((content, AZON.SentitPagament, Literal(payment["sentit"])))
    graph.add((content, AZON.Estat, Literal(payment.get("status", "PAGAT"))))
    graph.add((content, AZON.DataPagament, Literal(payment["date"])))
    if payment.get("transport_cost") is not None:
        graph.add((content, AZON.CostTransport, Literal(payment["transport_cost"], datatype=XSD.float)))
    if payment.get("products"):
        _add_invoice_product_lines(graph, content, payment["products"])
    else:
        for product_id in payment.get("product_ids", []):
            graph.add((content, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_confirmacio_pagament(graph):
    props = get_message_properties(graph)
    content = props["content"]
    invoice = extract_invoice_from_content(graph, content)
    if invoice is None:
        return {}
    return invoice


# Charge request (Centre Logistic / Compra -> Cobrador) ----------------------------
def build_peticio_cobrament(charge, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"charge-request-{charge.get('user_id', uuid4().hex[:8])}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioCobrament))
    graph.add((content, AZON.PreuProducte, Literal(charge["preu_producte"], datatype=XSD.float)))
    # CostTransport=0 quan l'enviament el fa el venedor extern, no per l'AgentZon
    graph.add((content, AZON.CostTransport, Literal(charge["cost_transport"], datatype=XSD.float)))
    graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(charge["user_id"])]))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_cobrament(graph, content):
    preu_producte_value = graph.value(content, AZON.PreuProducte)
    cost_transport_value = graph.value(content, AZON.CostTransport)
    return {
        "user_id": _user_id_from_iri(graph.value(content, AZON.PertanyAUsuari)),
        "preu_producte": float(preu_producte_value) if preu_producte_value is not None else 0.0,
        "cost_transport": float(cost_transport_value) if cost_transport_value is not None else 0.0,
    }


# Refund request (Retornador -> Cobrador) ------------------------------------------
def build_peticio_retorn_diners(refund, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"refund-request-{refund['return_id']}"]
    graph.add((content, RDF.type, AZON.PeticioRetornDiners))
    graph.add((content, AZON.IdDevolucio, Literal(refund["return_id"])))
    link_sobre_comanda(graph, content, refund["order_id"])
    graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(refund["user_id"])]))
    graph.add((content, AZON.ImportPagament, Literal(refund["amount"], datatype=XSD.float)))
    graph.add((content, AZON.MotiuDevolucio, Literal(refund.get("reason", ""))))
    if refund.get("seller_id"):
        graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(refund["seller_id"])]))
    for product_id in refund.get("product_ids", []):
        product_node = AZON[f"product-{product_id}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_retorn_diners(graph, content):
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))
    seller_id_iri = graph.value(content, AZON.PertanyAVenedorExtern)
    seller_id = _seller_id_from_iri(seller_id_iri)
    return {
        "return_id": str(graph.value(content, AZON.IdDevolucio)),
        "order_id": order_id_from_node(graph, content),
        "user_id": _user_id_from_iri(graph.value(content, AZON.PertanyAUsuari)),
        "amount": float(graph.value(content, AZON.ImportPagament)),
        "reason": str(graph.value(content, AZON.MotiuDevolucio)),
        "seller_id": str(seller_id) if seller_id is not None else None,
        "product_ids": sorted(product_ids),
    }


def build_confirmacio_retorn_diners(refund, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"refund-confirmation-{refund['return_id']}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRetornDiners))
    graph.add((content, AZON.IdDevolucio, Literal(refund["return_id"])))
    link_sobre_comanda(graph, content, refund["order_id"])
    graph.add((content, AZON.ImportPagament, Literal(refund["amount"], datatype=XSD.float)))
    graph.add((content, AZON.Estat, Literal(refund.get("status", "RETORNAT"))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_confirmacio_retorn_diners(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "return_id": str(graph.value(content, AZON.IdDevolucio)),
        "order_id": order_id_from_node(graph, content),
        "amount": float(graph.value(content, AZON.ImportPagament)),
        "status": str(graph.value(content, AZON.Estat)),
    }
