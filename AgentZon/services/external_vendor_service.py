"""Persistència de responsabilitat d'enviament i ubicacions de productes externs."""

from rdflib import Literal, RDF, XSD

from AgentUtil.OntoNamespaces import AZON
from services.rdf_store import load_graph, save_graph


CENTRE_RESOURCE_BY_ID = {
    "CL-BCN": "centre-BCN",
    "CL-GI": "centre-GI",
    "CL-TGN": "centre-TGN",
}


def save_shipping_responsibility(path, product_id, seller_id, requires_external_logistics):
    graph = load_graph(path)
    node = AZON[f"product-{product_id}"]
    graph.set((node, AZON.IdProducte, Literal(product_id)))
    graph.set((node, AZON.IdVenedorExtern, Literal(seller_id)))
    graph.set(
        (
            node,
            AZON.RequereixLogisticaExterna,
            Literal(bool(requires_external_logistics), datatype=XSD.boolean),
        )
    )
    save_graph(path, graph)


def load_shipping_responsibility_by_product(path):
    graph = load_graph(path)
    responsibility = {}
    for subject in graph.subjects(predicate=AZON.IdVenedorExtern, object=None):
        product_id = str(graph.value(subject, AZON.IdProducte))
        seller_id = graph.value(subject, AZON.IdVenedorExtern)
        external_flag = graph.value(subject, AZON.RequereixLogisticaExterna)
        responsibility[product_id] = {
            "seller_id": str(seller_id) if seller_id is not None else "",
            "requires_external_logistics": str(external_flag).lower() == "true" if external_flag is not None else False,
        }
    return responsibility


def save_external_product_location(locations_path, product_id, centre_id):
    centre_resource = CENTRE_RESOURCE_BY_ID.get(centre_id)
    if centre_resource is None:
        raise ValueError(f"Centre logistic desconegut: {centre_id}")

    graph = load_graph(locations_path)
    product_node = AZON[f"product-{product_id}"]
    centre_node = AZON[centre_resource]
    graph.set((product_node, AZON.UbicatACentre, centre_node))
    save_graph(locations_path, graph)


def is_external_product(catalog_path, product_id):
    graph = load_graph(catalog_path)
    product_node = AZON[f"product-{product_id}"]
    return (product_node, RDF.type, AZON.ProducteExtern) in graph
