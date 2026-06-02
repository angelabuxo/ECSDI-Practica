"""Consultes al catàleg de productes (productes.ttl) amb filtres per ID i criteris."""

from datetime import date

from rdflib import Literal, RDF, XSD
from rdflib.plugins.sparql import prepareQuery

from AgentUtil.OntoNamespaces import AZON
from services.rdf_store import load_graph, save_graph


# La gramàtica SPARQL de rdflib (pyparsing) NO és thread-safe en temps de
# parseig. Sota Flask (threaded=True) diverses peticions concurrents que
# analitzin la mateixa cadena SPARQL corrompen l'estat compartit del parser i
# llancen errors com "Param.postParse2() missing 1 required positional argument".
# Preparem la consulta una sola vegada a la importació (single-thread) i
# reutilitzem l'objecte ja parsejat a cada crida, evitant el parseig concurrent.
_PRODUCTS_QUERY = prepareQuery(
    """
        PREFIX azon: <http://www.semanticweb.org/agentzon#>
        SELECT ?id ?name ?description ?category ?brand ?price ?weight ?is_external
        WHERE {
            ?product a ?product_type ;
                azon:IdProducte ?id ;
                azon:Nom ?name ;
                azon:Descripcio ?description ;
                azon:Categoria ?category ;
                azon:Marca ?brand ;
                azon:Preu ?price ;
                azon:Pes ?weight .
            FILTER(?product_type IN (azon:Producte, azon:ProducteExtern, azon:ProducteIntern))
            OPTIONAL {
                ?product a azon:ProducteExtern .
                BIND(true AS ?is_external)
            }
        }
    """
)


def _next_product_id(graph):
    max_num = 1000
    for product_id in graph.objects(None, AZON.IdProducte):
        product_text = str(product_id)
        if product_text.startswith("P") and product_text[1:].isdigit():
            max_num = max(max_num, int(product_text[1:]))
    return f"P{max_num + 1}"


def allocate_external_product_id(catalog_path):
    graph = load_graph(catalog_path)
    return _next_product_id(graph)


# Search operations ----------------------------------------------------------------
def search_products(catalog_path, criteria):
    graph = load_graph(catalog_path)
    rows = graph.query(_PRODUCTS_QUERY)
    results = []
    lowered_text = criteria.get("text", "").lower()
    for row in rows:
        product = {
            "product_id": str(row.id),
            "name": str(row.name),
            "description": str(row.description),
            "category": str(row.category),
            "brand": str(row.brand),
            "price": float(row.price),
            "weight": float(row.weight),
            "is_external": bool(row.is_external),
        }
        haystack = f"{product['name']} {product['description']}".lower()
        if lowered_text and lowered_text not in haystack:
            continue
        if criteria.get("category") and product["category"] != criteria["category"]:
            continue
        if criteria.get("brand") and product["brand"] != criteria["brand"]:
            continue
        if criteria.get("min_price") is not None and product["price"] < criteria["min_price"]:
            continue
        if criteria.get("max_price") is not None and product["price"] > criteria["max_price"]:
            continue
        results.append(product)
    return results


def get_products_by_ids(catalog_path, product_ids):
    wanted = set(product_ids)
    return [
        product
        for product in search_products(catalog_path, {"text": "", "category": "", "brand": "", "min_price": None, "max_price": None})
        if product["product_id"] in wanted
    ]


def add_external_product(catalog_path, product):
    graph = load_graph(catalog_path)
    product_id = product.get("product_id") or _next_product_id(graph)
    node = AZON[f"product-{product_id}"]

    graph.add((node, RDF.type, AZON.ProducteExtern))
    graph.add((node, AZON.IdProducte, Literal(product_id)))
    graph.add((node, AZON.Nom, Literal(product.get("name", ""))))
    graph.add((node, AZON.Descripcio, Literal(product.get("description", ""))))
    graph.add((node, AZON.Categoria, Literal(product.get("category", ""))))
    graph.add((node, AZON.Marca, Literal(product.get("brand", ""))))
    graph.add((node, AZON.Preu, Literal(float(product.get("price", 0.0)), datatype=XSD.float)))
    graph.add((node, AZON.Pes, Literal(float(product.get("weight", 0.0)), datatype=XSD.float)))
    graph.add((node, AZON.SkuExtern, Literal(product.get("sku_extern", ""))))
    graph.add((node, AZON.DataAlta, Literal(product.get("data_alta", date.today().isoformat()), datatype=XSD.date)))
    graph.add(
        (
            node,
            AZON.RequereixLogisticaExterna,
            Literal(bool(product.get("requires_external_logistics", False)), datatype=XSD.boolean),
        )
    )
    if product.get("seller_id"):
        graph.add((node, AZON.IdVenedorExtern, Literal(product["seller_id"])))

    save_graph(catalog_path, graph)
    return product_id
