"""Persistència de dades bancàries, pagaments, factures i devolucions."""

from rdflib import Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from protocols.rdf_refs import ensure_order_node, link_sobre_comanda
from services.rdf_store import load_graph, save_graph


# Bank data ------------------------------------------------------------------------
def save_user_bank_data(path, user_id, bank_data, payment_method):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"bank-user-{user_id}"]
    graph.add((node, RDF.type, AZON.Usuari))
    graph.set((node, AZON.IdUsuari, Literal(user_id))))
    graph.set((node, AZON.DadesBancariesUsuari, Literal(bank_data)))
    graph.set((node, AZON.MetodePagament, Literal(payment_method)))
    save_graph(path, graph)


def read_user_bank_data(path, user_id):
    graph = load_graph(path)
    node = AZON[f"bank-user-{user_id}"]
    bank_data = graph.value(node, AZON.DadesBancariesUsuari)
    if bank_data is None:
        return None
    return {
        "user_id": user_id,
        "bank_data": str(bank_data),
        "payment_method": str(graph.value(node, AZON.MetodePagament) or ""),
    }


def has_user_bank_data(path, user_id):
    return read_user_bank_data(path, user_id) is not None


def save_seller_bank_data(path, seller_id, bank_data, seller_name=None):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"bank-seller-{seller_id}"]
    graph.add((node, RDF.type, AZON.VenedorExtern))
    graph.set((node, AZON.IdVenedorExtern, Literal(seller_id)))
    graph.set((node, AZON.DadesBancariesVenedorExtern, Literal(bank_data)))
    if seller_name:
        graph.set((node, AZON.Nom, Literal(seller_name)))
    save_graph(path, graph)


def read_seller_bank_data(path, seller_id):
    graph = load_graph(path)
    node = AZON[f"bank-seller-{seller_id}"]
    bank_data = graph.value(node, AZON.DadesBancariesVenedorExtern)
    if bank_data is None:
        return None
    seller_name = graph.value(node, AZON.Nom)
    return {
        "seller_id": seller_id,
        "bank_data": str(bank_data),
        "seller_name": str(seller_name) if seller_name is not None else "",
    }


def has_seller_bank_data(path, seller_id):
    return read_seller_bank_data(path, seller_id) is not None


def resolve_seller_display_name(path, seller_id):
    """Retorna el nom comercial del venedor o l'identificador si no n'hi ha."""
    profile = read_seller_bank_data(path, seller_id)
    if profile and profile.get("seller_name"):
        return profile["seller_name"]
    return seller_id


# Payments / invoices --------------------------------------------------------------
def record_payment(path, payment):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"payment-{payment['payment_id']}"]
    graph.add((node, RDF.type, AZON.Pagament))
    graph.add((node, AZON.IdPagament, Literal(payment["payment_id"])))
    graph.add((node, AZON.IdComanda, Literal(payment["order_id"])))
    link_sobre_comanda(graph, node, payment["order_id"])
    graph.add((node, AZON.ImportPagament, Literal(payment["amount"], datatype=XSD.float)))
    graph.add((node, AZON.MetodePagament, Literal(payment["method"])))
    if payment.get("sentit"):
        graph.add((node, AZON.SentitPagament, Literal(payment["sentit"])))
    graph.add((node, AZON.Estat, Literal(payment.get("status", "PAGAT"))))
    graph.add((node, AZON.DataPagament, Literal(payment["date"])))
    if payment.get("user_id"):
        graph.add((node, AZON.PertanyAUsuari, AZON["usuari-" + str(payment["user_id"])])))
    if payment.get("seller_id"):
        graph.add((node, AZON.IdVenedorExtern, Literal(payment["seller_id"])))
    for product_id in payment.get("product_ids", []):
        graph.add((node, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    save_graph(path, graph)


# Refunds --------------------------------------------------------------------------
def record_refund(path, refund):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"refund-{refund['return_id']}"]
    graph.add((node, RDF.type, AZON.Devolucio))
    graph.add((node, AZON.IdDevolucio, Literal(refund["return_id"])))
    graph.add((node, AZON.IdComanda, Literal(refund["order_id"])))
    ensure_order_node(graph, refund["order_id"])
    graph.add((node, AZON.PertanyAUsuari, AZON["usuari-" + str(refund["user_id"])])))
    graph.add((node, AZON.ImportPagament, Literal(refund["amount"], datatype=XSD.float)))
    graph.add((node, AZON.MotiuDevolucio, Literal(refund.get("reason", ""))))
    graph.add((node, AZON.Estat, Literal(refund.get("status", "RETORNAT"))))
    if refund.get("seller_id"):
        graph.add((node, AZON.IdVenedorExtern, Literal(refund["seller_id"])))
    for product_id in refund.get("product_ids", []):
        graph.add((node, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    save_graph(path, graph)
