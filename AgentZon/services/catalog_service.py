"""Catalog query helpers backed by the AgentZon RDF product store."""

from rdflib import Graph

from AgentZon.AgentUtil.OntoNamespaces import AZON
from AgentZon.services.rdf_store import load_graph


# Search operations ----------------------------------------------------------------
def search_products(catalog_path, criteria):
    graph = load_graph(catalog_path)
    query = """
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
    rows = graph.query(query)
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
