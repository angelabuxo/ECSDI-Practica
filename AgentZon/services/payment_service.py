"""Persistence helpers for bank data, payments, invoices and refunds."""

from rdflib import Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from services.rdf_store import load_graph, save_graph


# Bank data ------------------------------------------------------------------------
def save_user_bank_data(path, user_id, bank_data, payment_method):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"bank-user-{user_id}"]
    graph.add((node, RDF.type, AZON.Usuari))
    graph.set((node, AZON.IdUsuari, Literal(user_id)))
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


def save_seller_bank_data(path, seller_id, bank_data):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"bank-seller-{seller_id}"]
    graph.add((node, RDF.type, AZON.VenedorExtern))
    graph.set((node, AZON.IdVenedorExtern, Literal(seller_id)))
    graph.set((node, AZON.DadesBancariesVenedorExtern, Literal(bank_data)))
    save_graph(path, graph)


def read_seller_bank_data(path, seller_id):
    graph = load_graph(path)
    node = AZON[f"bank-seller-{seller_id}"]
    bank_data = graph.value(node, AZON.DadesBancariesVenedorExtern)
    if bank_data is None:
        return None
    return {"seller_id": seller_id, "bank_data": str(bank_data)}


# Payments / invoices --------------------------------------------------------------
def record_payment(path, payment):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"payment-{payment['payment_id']}"]
    order_node = AZON[f"order-{payment['order_id']}"]
    graph.add((node, RDF.type, AZON.Pagament))
    graph.add((node, AZON.IdPagament, Literal(payment["payment_id"])))
    graph.add((node, AZON.IdComanda, Literal(payment["order_id"])))
    graph.add((node, AZON.ImportPagament, Literal(payment["amount"], datatype=XSD.float)))
    graph.add((node, AZON.MetodePagament, Literal(payment["method"])))
    graph.add((node, AZON.Estat, Literal(payment.get("status", "PAGAT"))))
    graph.add((node, AZON.DataPagament, Literal(payment["date"])))
    graph.add((node, AZON.SobreComanda, order_node))
    if payment.get("user_id"):
        graph.add((node, AZON.IdUsuari, Literal(payment["user_id"])))
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
    graph.add((node, AZON.IdUsuari, Literal(refund["user_id"])))
    graph.add((node, AZON.ImportPagament, Literal(refund["amount"], datatype=XSD.float)))
    graph.add((node, AZON.MotiuDevolucio, Literal(refund.get("reason", ""))))
    graph.add((node, AZON.Estat, Literal(refund.get("status", "RETORNAT"))))
    if refund.get("seller_id"):
        graph.add((node, AZON.IdVenedorExtern, Literal(refund["seller_id"])))
    for product_id in refund.get("product_ids", []):
        graph.add((node, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    save_graph(path, graph)
