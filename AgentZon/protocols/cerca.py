"""Ontology-backed messages for product-search requests and responses."""

from rdflib import Graph, Literal, RDF, XSD

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces


# RDF builders --------------------------------------------------------------------
def build_peticio_cerca(request_id, text="", category="", brand="", min_price=None, max_price=None):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[request_id]
    graph.add((content, RDF.type, AZON.PeticioCerca))
    graph.add((content, AZON.TextConsulta, Literal(text)))
    graph.add((content, AZON.CategoriaConsulta, Literal(category)))
    graph.add((content, AZON.MarcaConsulta, Literal(brand)))
    if min_price is not None:
        graph.add((content, AZON.PreuMinim, Literal(min_price, datatype=XSD.float)))
    if max_price is not None:
        graph.add((content, AZON.PreuMaxim, Literal(max_price, datatype=XSD.float)))
    return graph, content


# RDF parsers ---------------------------------------------------------------------
def parse_peticio_cerca(graph, content):
    return {
        "text": str(graph.value(content, AZON.TextConsulta, default=Literal(""))),
        "category": str(graph.value(content, AZON.CategoriaConsulta, default=Literal(""))),
        "brand": str(graph.value(content, AZON.MarcaConsulta, default=Literal(""))),
        "min_price": _literal_to_float(graph.value(content, AZON.PreuMinim)),
        "max_price": _literal_to_float(graph.value(content, AZON.PreuMaxim)),
    }


def build_resultat_cerca(result_id, products, request_content=None):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[result_id]
    graph.add((content, RDF.type, AZON.ResultatCerca))
    graph.add((content, AZON.TotalResultats, Literal(len(products))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    for product in products:
        subject = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.MostraProducte, subject))
        graph.add((subject, RDF.type, AZON.Producte))
        graph.add((subject, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((subject, AZON.Nom, Literal(product["name"])))
        graph.add((subject, AZON.Descripcio, Literal(product["description"])))
        graph.add((subject, AZON.Categoria, Literal(product["category"])))
        graph.add((subject, AZON.Marca, Literal(product["brand"])))
        graph.add((subject, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
        graph.add((subject, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    return graph, content


def extract_result_products(graph, content=None):
    if content is None:
        content = graph.value(predicate=RDF.type, object=AZON.ResultatCerca)
    products = []
    for subject in graph.objects(content, AZON.MostraProducte):
        products.append(
            {
                "product_id": str(graph.value(subject, AZON.IdProducte)),
                "name": str(graph.value(subject, AZON.Nom)),
                "description": str(graph.value(subject, AZON.Descripcio)),
                "category": str(graph.value(subject, AZON.Categoria)),
                "brand": str(graph.value(subject, AZON.Marca)),
                "price": float(graph.value(subject, AZON.Preu)),
                "weight": float(graph.value(subject, AZON.Pes)),
            }
        )
    return products


def _literal_to_float(value):
    return None if value is None else float(value)
