"""Feedback persistence and feedback scheduling helpers."""

from datetime import date, datetime, timedelta

from rdflib import Literal, RDF, XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from services.rdf_store import load_graph, save_graph


def record_feedback(path, feedback):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"feedback-{feedback['feedback_id']}"]
    graph.add((node, RDF.type, AZON.Feedback))
    graph.add((node, AZON.IdFeedback, Literal(feedback["feedback_id"])))
    graph.add((node, AZON.IdComanda, Literal(feedback["order_id"])))
    graph.add((node, AZON.IdUsuari, Literal(feedback["user_id"])))
    graph.add((node, AZON.Puntuacio, Literal(feedback["score"], datatype=XSD.integer)))
    graph.add((node, AZON.Comentari, Literal(feedback["comment"])))
    for product_id in feedback["products"]:
        graph.add((node, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    save_graph(path, graph)


def collect_due_feedback(purchase_history_path, days=14, today=None):
    graph = load_graph(purchase_history_path)
    today = today or date.today()
    due = []
    for purchase in graph.subjects(predicate=AZON.IdComanda):
        purchase_date = graph.value(purchase, AZON.DataCompra)
        if purchase_date is None:
            continue
        purchase_date = datetime.fromisoformat(str(purchase_date)).date()
        if today - purchase_date < timedelta(days=days):
            continue
        due.append(
            {
                "feedback_id": str(graph.value(purchase, AZON.IdComanda)),
                "order_id": str(graph.value(purchase, AZON.IdComanda)),
                "user_id": str(graph.value(purchase, AZON.IdUsuari)),
                "products": [str(product).rsplit("product-", 1)[-1] for product in graph.objects(purchase, AZON.SobreProducte)],
                "purchase_date": purchase_date.isoformat(),
            }
        )
    return due
