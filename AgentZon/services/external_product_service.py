"""Persistence helpers for external-seller products and bank details."""

from datetime import date

from rdflib import Literal, RDF, XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from services.rdf_store import load_graph, save_graph


def save_external_product(catalog_path, product):
    graph = load_graph(catalog_path)
    bind_namespaces(graph)
    node = AZON[f"product-{product['product_id']}"]

    graph.add((node, RDF.type, AZON.Producte))
    graph.add((node, RDF.type, AZON.ProducteExtern))
    graph.set((node, AZON.IdProducte, Literal(product["product_id"])))
    graph.set((node, AZON.Nom, Literal(product["name"])))
    graph.set((node, AZON.Descripcio, Literal(product["description"])))
    graph.set((node, AZON.Categoria, Literal(product["category"])))
    graph.set((node, AZON.Marca, Literal(product["brand"])))
    graph.set((node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
    graph.set((node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    graph.set((node, AZON.SkuExtern, Literal(product.get("sku_extern", product["product_id"]))))
    graph.set((node, AZON.RequereixLogisticaExterna, Literal(bool(product.get("requires_external_shipping", True)))))
    graph.set((node, AZON.DataAlta, Literal(product.get("data_alta", date.today().isoformat()), datatype=XSD.date)))
    save_graph(catalog_path, graph)


def save_shipping_responsibility(path, product):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"product-{product['product_id']}"]

    graph.add((node, RDF.type, AZON.ProducteExtern))
    graph.set((node, AZON.IdProducte, Literal(product["product_id"])))
    graph.set((node, AZON.SkuExtern, Literal(product.get("sku_extern", product["product_id"]))))
    graph.set((node, AZON.IdVenedorExtern, Literal(product["seller_id"])))
    graph.set((node, AZON.RequereixLogisticaExterna, Literal(bool(product.get("requires_external_shipping", True)))))
    save_graph(path, graph)


def save_product_location(path, product):
    graph = load_graph(path)
    bind_namespaces(graph)
    product_node = AZON[f"product-{product['product_id']}"]
    centre_node = AZON[f"centre-extern-{product['seller_id']}"]

    graph.add((centre_node, RDF.type, AZON.CentreLogistic))
    graph.set((centre_node, AZON.IdCentreLogistic, Literal(f"EXT-{product['seller_id']}")))
    graph.set((centre_node, AZON.Ciutat, Literal(product.get("warehouse_city", ""))))
    graph.set((product_node, AZON.UbicatACentre, centre_node))
    save_graph(path, graph)


def save_vendor_bank_data(path, vendor):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"vendor-{vendor['seller_id']}"]

    graph.add((node, RDF.type, AZON.VenedorExtern))
    graph.set((node, AZON.IdVenedorExtern, Literal(vendor["seller_id"])))
    graph.set((node, AZON.DadesBancariesVenedorExtern, Literal(vendor["bank_details"])))
    save_graph(path, graph)