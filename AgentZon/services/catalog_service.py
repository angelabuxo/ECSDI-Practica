"""Consultes al catàleg de productes (productes.ttl) amb filtres per ID i criteris."""

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

from AgentUtil.OntoNamespaces import AZON
from services.rdf_store import load_graph


# La gramàtica SPARQL de rdflib (pyparsing) NO és thread-safe en temps de
# parseig. Sota Flask (threaded=True) diverses peticions concurrents que
# analitzin la mateixa cadena SPARQL corrompen l'estat compartit del parser i
# llancen errors com "Param.postParse2() missing 1 required positional argument".
# Preparem la consulta una sola vegada a la importació (single-thread) i
# reutilitzem l'objecte ja parsejat a cada crida, evitant el parseig concurrent.
_PRODUCTS_QUERY = prepareQuery(
    """
        PREFIX azon: <http://www.semanticweb.org/agentzon#>
        SELECT ?id ?name ?description ?category ?brand ?price ?weight
        WHERE {
            ?product a azon:Producte ;
                azon:IdProducte ?id ;
                azon:Nom ?name ;
                azon:Descripcio ?description ;
                azon:Categoria ?category ;
                azon:Marca ?brand ;
                azon:Preu ?price ;
                azon:Pes ?weight .
        }
    """
)


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
