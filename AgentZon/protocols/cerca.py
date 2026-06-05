# -*- coding: utf-8 -*-
"""Missatges RDF de cerca i consultes de catàleg propietari."""

from rdflib import Graph, Literal, RDF, XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces


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
        subject = AZON["product-%s" % product["product_id"]]
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


def build_peticio_consulta_productes(product_ids, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"product-lookup-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaProductes))
    for product_id in sorted(set(product_ids)):
        product_node = AZON[f"product-{product_id}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    return build_message(
        graph,
        ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_consulta_productes(graph, content=None):
    if content is None:
        props = get_message_properties(graph)
        content = props.get("content") or graph.value(predicate=RDF.type, object=AZON.PeticioConsultaProductes)
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is not None:
            product_ids.append(str(product_id))
    return sorted(product_ids)


def build_resultat_consulta_productes(products, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"product-lookup-result-{msgcnt}"]
    graph.add((content, RDF.type, AZON.ResultatConsultaProductes))
    for product in products:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((product_node, AZON.Nom, Literal(product.get("name", ""))))
        graph.add((product_node, AZON.Categoria, Literal(product.get("category", ""))))
        graph.add((product_node, AZON.Marca, Literal(product.get("brand", ""))))
        graph.add((product_node, AZON.Preu, Literal(product.get("price", 0.0), datatype=XSD.float)))
        graph.add((product_node, AZON.Pes, Literal(product.get("weight", 0.0), datatype=XSD.float)))
        if "description" in product:
            graph.add((product_node, AZON.Descripcio, Literal(product.get("description", ""))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_product_snapshots(graph, content=None):
    if content is None:
        props = get_message_properties(graph)
        content = props.get("content") or graph.value(predicate=RDF.type, object=AZON.ResultatConsultaProductes)
    products = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        price_value = graph.value(product_node, AZON.Preu)
        weight_value = graph.value(product_node, AZON.Pes)
        product = {
            "product_id": str(graph.value(product_node, AZON.IdProducte)),
            "name": str(graph.value(product_node, AZON.Nom) or ""),
            "category": str(graph.value(product_node, AZON.Categoria) or ""),
            "brand": str(graph.value(product_node, AZON.Marca) or ""),
            "price": float(price_value) if price_value is not None else 0.0,
            "weight": float(weight_value) if weight_value is not None else 0.0,
        }
        description = graph.value(product_node, AZON.Descripcio)
        if description is not None:
            product["description"] = str(description)
        products.append(product)
    return products
