"""Messages for external-seller product registration and confirmations."""

from rdflib import Graph, Literal, RDF, XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces


def build_alta_producte_extern(
    request_id,
    product_id,
    seller_id,
    bank_details,
    name,
    description,
    category,
    brand,
    price,
    weight,
    sku_extern=None,
    warehouse_city="",
    requires_external_shipping=True,
    data_alta=None,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[request_id]

    graph.add((content, RDF.type, AZON.AltaProducteExtern))
    graph.add((content, AZON.IdProducte, Literal(product_id)))
    graph.add((content, AZON.IdVenedorExtern, Literal(seller_id)))
    graph.add((content, AZON.DadesBancariesVenedorExtern, Literal(bank_details)))
    graph.add((content, AZON.Nom, Literal(name)))
    graph.add((content, AZON.Descripcio, Literal(description)))
    graph.add((content, AZON.Categoria, Literal(category)))
    graph.add((content, AZON.Marca, Literal(brand)))
    graph.add((content, AZON.Preu, Literal(price, datatype=XSD.float)))
    graph.add((content, AZON.Pes, Literal(weight, datatype=XSD.float)))
    graph.add((content, AZON.SkuExtern, Literal(sku_extern or product_id)))
    graph.add((content, AZON.RequereixLogisticaExterna, Literal(bool(requires_external_shipping))))
    graph.add((content, AZON.Ciutat, Literal(warehouse_city)))
    if data_alta is not None:
        graph.add((content, AZON.DataAlta, Literal(data_alta, datatype=XSD.date)))

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_alta_producte_extern(graph, content):
    return {
        "product_id": str(graph.value(content, AZON.IdProducte)),
        "seller_id": str(graph.value(content, AZON.IdVenedorExtern)),
        "bank_details": str(graph.value(content, AZON.DadesBancariesVenedorExtern)),
        "name": str(graph.value(content, AZON.Nom)),
        "description": str(graph.value(content, AZON.Descripcio)),
        "category": str(graph.value(content, AZON.Categoria)),
        "brand": str(graph.value(content, AZON.Marca)),
        "price": float(graph.value(content, AZON.Preu)),
        "weight": float(graph.value(content, AZON.Pes)),
        "sku_extern": _literal_to_string(graph.value(content, AZON.SkuExtern)),
        "warehouse_city": _literal_to_string(graph.value(content, AZON.Ciutat)),
        "requires_external_shipping": _literal_to_bool(graph.value(content, AZON.RequereixLogisticaExterna)),
        "data_alta": _literal_to_string(graph.value(content, AZON.DataAlta)),
    }


def build_confirmacio_alta_producte_extern(
    product_id,
    seller_id,
    sender=None,
    receiver=None,
    request_content=None,
    msgcnt=0,
    data_alta=None,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-product-confirmation-{product_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioAltaProducteExtern))
    graph.add((content, AZON.IdProducte, Literal(product_id)))
    graph.add((content, AZON.IdVenedorExtern, Literal(seller_id)))
    graph.add((content, AZON.SkuExtern, Literal(product_id)))
    if data_alta is not None:
        graph.add((content, AZON.DataAlta, Literal(data_alta, datatype=XSD.date)))
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


def _literal_to_bool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def _literal_to_string(value):
    return "" if value is None else str(value)