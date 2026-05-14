"""Ontology-backed messages for the Opinador agent capabilities."""

from rdflib import Graph, Literal, RDF, XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces


# Feedback ------------------------------------------------------------------------
def build_peticio_feedback(feedback_id, order_id, user_id, products, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"feedback-request-{feedback_id}"]
    graph.add((content, RDF.type, AZON.PeticioFeedback))
    graph.add((content, AZON.IdFeedback, Literal(feedback_id)))
    graph.add((content, AZON.IdComanda, Literal(order_id)))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    for product_id in products:
        graph.add((content, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_feedback(graph, content):
    return {
        "feedback_id": str(graph.value(content, AZON.IdFeedback)),
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "products": _extract_product_ids(graph, content),
    }


def build_resposta_feedback(feedback_id, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"feedback-confirmation-{feedback_id}"]
    graph.add((content, RDF.type, AZON.RespostaFeedback))
    graph.add((content, AZON.IdFeedback, Literal(feedback_id)))
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


def build_feedback_entry(feedback):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"feedback-{feedback['feedback_id']}"]
    graph.add((content, RDF.type, AZON.Feedback))
    graph.add((content, AZON.IdFeedback, Literal(feedback["feedback_id"])))
    graph.add((content, AZON.IdComanda, Literal(feedback["order_id"])))
    graph.add((content, AZON.IdUsuari, Literal(feedback["user_id"])))
    graph.add((content, AZON.Puntuacio, Literal(feedback["score"], datatype=XSD.integer)))
    graph.add((content, AZON.Comentari, Literal(feedback["comment"])))
    for product_id in feedback["products"]:
        graph.add((content, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    return graph, content


def parse_feedback_entry(graph, content):
    return {
        "feedback_id": str(graph.value(content, AZON.IdFeedback)),
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "score": int(graph.value(content, AZON.Puntuacio)),
        "comment": str(graph.value(content, AZON.Comentari, default=Literal(""))),
        "products": _extract_product_ids(graph, content),
    }


# Recommendations -----------------------------------------------------------------
def build_resposta_recomanacio(request_id, products, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"recommendation-response-{request_id}"]
    graph.add((content, RDF.type, AZON.RespostaRecomanacio))
    graph.add((content, AZON.IdFeedback, Literal(request_id)))
    for product in products:
        subject = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.GeneraRecomanacio, AZON[f"recommendation-{product['product_id']}"]))
        graph.add((content, AZON.SobreProducte, subject))
        graph.add((subject, RDF.type, AZON.Producte))
        graph.add((subject, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((subject, AZON.Nom, Literal(product["name"])))
        graph.add((subject, AZON.Descripcio, Literal(product["description"])))
        graph.add((subject, AZON.Categoria, Literal(product["category"])))
        graph.add((subject, AZON.Marca, Literal(product["brand"])))
        graph.add((subject, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
        graph.add((subject, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
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


def extract_recommendation_products(graph, content=None):
    if content is None:
        content = graph.value(predicate=RDF.type, object=AZON.RespostaRecomanacio)
    return [
        {
            "product_id": str(graph.value(subject, AZON.IdProducte)),
            "name": str(graph.value(subject, AZON.Nom)),
            "description": str(graph.value(subject, AZON.Descripcio)),
            "category": str(graph.value(subject, AZON.Categoria)),
            "brand": str(graph.value(subject, AZON.Marca)),
            "price": float(graph.value(subject, AZON.Preu)),
            "weight": float(graph.value(subject, AZON.Pes)),
        }
        for subject in graph.objects(content, AZON.SobreProducte)
    ]


# Returns -------------------------------------------------------------------------
def build_peticio_consulta_devolucio(request_id, order_id, user_id, product_ids, reason, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"return-request-{request_id}"]
    graph.add((content, RDF.type, AZON.PeticioDevolucio))
    graph.add((content, AZON.IdDevolucio, Literal(request_id)))
    graph.add((content, AZON.IdComanda, Literal(order_id)))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    graph.add((content, AZON.MotiuDevolucio, Literal(reason)))
    for product_id in product_ids:
        graph.add((content, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_consulta_devolucio(graph, content):
    return {
        "request_id": str(graph.value(content, AZON.IdDevolucio)),
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "reason": str(graph.value(content, AZON.MotiuDevolucio, default=Literal(""))),
        "products": _extract_product_ids(graph, content),
    }


def build_resolucio_devolucio(request_id, accepted, reason, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"return-resolution-{request_id}"]
    graph.add((content, RDF.type, AZON.ResolucioDevolucio))
    graph.add((content, AZON.IdDevolucio, Literal(request_id)))
    graph.add((content, AZON.Acceptada, Literal(bool(accepted))))
    graph.add((content, AZON.Estat, Literal("acceptada" if accepted else "denegada")))
    graph.add((content, AZON.MotiuDevolucio, Literal(reason)))
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


# Helpers -------------------------------------------------------------------------
def _extract_product_ids(graph, content):
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = str(product_node).rsplit("product-", 1)[-1]
        product_ids.append(str(product_id))
    return product_ids
