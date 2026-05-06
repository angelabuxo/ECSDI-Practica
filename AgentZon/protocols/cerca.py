"""Ontology-backed messages for product-search requests and responses."""

from rdflib import Graph, Literal, RDF, XSD

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces


# RDF builders --------------------------------------------------------------------
def build_peticio_cerca(request_id, text="", category="", brand="", min_price=None, max_price=None):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[request_id]
    graph.add((content, RDF.type, AZON.PeticioCerca))
    graph.add((content, AZON.teText, Literal(text)))
    graph.add((content, AZON.teCategoria, Literal(category)))
    graph.add((content, AZON.teMarca, Literal(brand)))
    if min_price is not None:
        graph.add((content, AZON.preuMinim, Literal(min_price, datatype=XSD.float)))
    if max_price is not None:
        graph.add((content, AZON.preuMaxim, Literal(max_price, datatype=XSD.float)))
    return graph, content


# RDF parsers ---------------------------------------------------------------------
def parse_peticio_cerca(graph, content):
    return {
        "text": str(graph.value(content, AZON.teText, default=Literal(""))),
        "category": str(graph.value(content, AZON.teCategoria, default=Literal(""))),
        "brand": str(graph.value(content, AZON.teMarca, default=Literal(""))),
        "min_price": _literal_to_float(graph.value(content, AZON.preuMinim)),
        "max_price": _literal_to_float(graph.value(content, AZON.preuMaxim)),
    }


def build_resultat_cerca(result_id, products):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[result_id]
    graph.add((content, RDF.type, AZON.ResultatCerca))
    graph.add((content, AZON.totalResultats, Literal(len(products))))
    for product in products:
        subject = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.mostraProducte, subject))
        graph.add((subject, RDF.type, AZON.Producte))
        graph.add((subject, AZON.idProducte, Literal(product["product_id"])))
        graph.add((subject, AZON.nom, Literal(product["name"])))
        graph.add((subject, AZON.descripcio, Literal(product["description"])))
        graph.add((subject, AZON.categoria, Literal(product["category"])))
        graph.add((subject, AZON.marca, Literal(product["brand"])))
        graph.add((subject, AZON.preu, Literal(product["price"])))
        graph.add((subject, AZON.pes, Literal(product["weight"])))
    return graph, content


def extract_result_products(graph, content=None):
    if content is None:
        content = graph.value(predicate=RDF.type, object=AZON.ResultatCerca)
    products = []
    for subject in graph.objects(content, AZON.mostraProducte):
        products.append(
            {
                "product_id": str(graph.value(subject, AZON.idProducte)),
                "name": str(graph.value(subject, AZON.nom)),
                "description": str(graph.value(subject, AZON.descripcio)),
                "category": str(graph.value(subject, AZON.categoria)),
                "brand": str(graph.value(subject, AZON.marca)),
                "price": float(graph.value(subject, AZON.preu)),
                "weight": float(graph.value(subject, AZON.pes)),
            }
        )
    return products


def _literal_to_float(value):
    return None if value is None else float(value)
