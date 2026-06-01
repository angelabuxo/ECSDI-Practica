"""Agent opinador: feedback, suggeriments i devolucions basats en històric."""

import argparse
import threading
from pathlib import Path

from flask import Flask, render_template, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI
from config import (
    DEFAULT_PORTS,
    TEMPLATE_DIR,
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_runtime_hostname,
    serve_agent,
)
from protocols.compra import build_confirmacio_registre_compra, parse_peticio_registre_compra
from protocols.opinador import build_resolucio_devolucio, parse_peticio_devolucio, parse_resposta_feedback
from services.history_service import (
    get_latest_purchase_for_user,
    load_feedback_records,
    load_purchase_records,
    record_feedback,
    record_purchase,
)
from services.opinador_service import evaluate_return_request, generate_recommendations, get_feedback_context


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = None
DATA_DIR = None
CATALOG_PATH = None
PURCHASE_HISTORY_PATH = None
SEARCH_HISTORY_PATH = None
FEEDBACK_PATH = None
COUNTER = 0
_MSGCNT_LOCK = threading.Lock()


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=None):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, DATA_DIR
    global CATALOG_PATH, PURCHASE_HISTORY_PATH, SEARCH_HISTORY_PATH, FEEDBACK_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender or settings.get("message_sender") or _default_message_sender
    DATA_DIR = Path(settings["data_dir"])
    CATALOG_PATH = DATA_DIR / "productes.ttl"
    PURCHASE_HISTORY_PATH = DATA_DIR / "historial_compres.ttl"
    SEARCH_HISTORY_PATH = DATA_DIR / "historial_cerques.ttl"
    FEEDBACK_PATH = DATA_DIR / "feedback.ttl"
    COUNTER = 0


def _default_message_sender(message, address):
    from AgentUtil.ACLMessages import send_message

    return send_message(message, address)


def next_counter():
    global COUNTER
    with _MSGCNT_LOCK:
        current = COUNTER
        COUNTER += 1
        return current


def _parse_product_ids(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def _latest_feedback_context(user_id=None):
    context = get_feedback_context(PURCHASE_HISTORY_PATH, user_id=user_id)
    if context is None:
        return None
    return {
        "feedback_id": f"FB-{context['order_id']}",
        **context,
    }


def _resolve_recommendation_user_id(user_id):
    if user_id:
        return user_id
    purchases = load_purchase_records(PURCHASE_HISTORY_PATH)
    return purchases[-1]["user_id"] if purchases else None


def _load_dashboard_stats(recommendations):
    return {
        "feedback_count": len(load_feedback_records(FEEDBACK_PATH)),
        "purchase_count": len(load_purchase_records(PURCHASE_HISTORY_PATH)),
        "recommendation_count": len(recommendations),
    }


# Agent logic ----------------------------------------------------------------------
def pla_registre_de_compra(request_data):
    order = {
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "user_name": request_data.get("user_name", "history-user"),
        "products": request_data["products"],
        "shipping_data": request_data.get(
            "shipping_data",
            {
                "user_id": request_data["user_id"],
                "user_name": request_data.get("user_name", "history-user"),
                "street_address": "",
                "city": "",
                "priority": "",
                "payment_method": "",
            },
        ),
    }
    logger.info("Registrant historial de compra per a la comanda %s", order["order_id"])
    record_purchase(PURCHASE_HISTORY_PATH, order)
    return order


def pla_registrar_feedback(feedback_data):
    logger.info("Registrant feedback %s per a la comanda %s", feedback_data["feedback_id"], feedback_data["order_id"])
    record_feedback(FEEDBACK_PATH, feedback_data)
    return feedback_data


def pla_crear_suggeriments(user_id=None, limit=5):
    resolved_user_id = _resolve_recommendation_user_id(user_id)
    return generate_recommendations(CATALOG_PATH, SEARCH_HISTORY_PATH, PURCHASE_HISTORY_PATH, user_id=resolved_user_id, limit=limit)


def pla_consulta_criteris_devolucio(request_data):
    return evaluate_return_request(CATALOG_PATH, PURCHASE_HISTORY_PATH, request_data)


def _build_feedback_request_context(user_id=None):
    context = _latest_feedback_context(user_id=user_id)
    if context is not None:
        return context
    purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id)
    if purchases:
        purchase = purchases[-1]
        return {
            "feedback_id": f"FB-{purchase['order_id']}",
            "user_id": purchase["user_id"],
            "order_id": purchase["order_id"],
            "product_ids": purchase["product_ids"],
        }
    return None


def _build_feedback_confirmation(feedback_data):
    return f"Feedback {feedback_data['feedback_id']} registrat correctament per a la comanda {feedback_data['order_id']}."


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties or properties.get("performative") != ACL.request:
        logger.warning("Rebut missatge no-request o malformat a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    content = properties["content"]
    content_type = message_graph.value(content, RDF.type)

    if content_type == AZON.PeticioRegistreCompra:
        request_data = parse_peticio_registre_compra(message_graph, content)
        pla_registre_de_compra(request_data)
        response = build_confirmacio_registre_compra(
            request_data["order_id"],
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            request_content=content,
            msgcnt=next_counter(),
        )
        return response.serialize(format="xml")

    if content_type == AZON.PeticioDevolucio:
        request_data = parse_peticio_devolucio(message_graph, content)
        decision = pla_consulta_criteris_devolucio(request_data)
        response = build_resolucio_devolucio(
            decision,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            request_content=content,
            msgcnt=next_counter(),
        )
        return response.serialize(format="xml")

    if content_type == AZON.RespostaFeedback:
        feedback_data = parse_resposta_feedback(message_graph, content)
        pla_registrar_feedback(feedback_data)
        response_graph = Graph()
        response = build_message(
            response_graph,
            ACL.inform,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            content=content,
            ontology=ONTOLOGY_URI,
            msgcnt=next_counter(),
        )
        return response.serialize(format="xml")

    logger.warning("Rebut acció no suportada a /comm: %s", content_type)
    return build_message(
        Graph(),
        ACL["not-understood"],
        sender=AGENT.uri,
        msgcnt=next_counter(),
    ).serialize(format="xml")


# Web interface -------------------------------------------------------------------
@app.route("/iface", methods=["GET", "POST"])
def iface():
    confirmation = request.args.get("confirmation", "")
    interface_user_id = request.values.get("user_id", "").strip()
    recommendation_limit = int(request.values.get("limit", 5) or 5)

    if request.method == "POST" and request.form.get("action") == "feedback":
        feedback_data = {
            "feedback_id": request.form["feedback_id"].strip(),
            "user_id": request.form["user_id"].strip(),
            "order_id": request.form["order_id"].strip(),
            "rating": int(request.form["rating"]),
            "comment": request.form.get("comment", "").strip(),
            "product_ids": _parse_product_ids(request.form.get("product_ids", "")),
        }
        pla_registrar_feedback(feedback_data)
        confirmation = _build_feedback_confirmation(feedback_data)
        interface_user_id = feedback_data["user_id"]

    feedback_context = _build_feedback_request_context(interface_user_id or None)
    recommendation_user_id = _resolve_recommendation_user_id(interface_user_id or (feedback_context or {}).get("user_id"))
    recommendations = pla_crear_suggeriments(recommendation_user_id, limit=recommendation_limit)
    recent_purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=interface_user_id or None)
    if not recent_purchases:
        recent_purchases = load_purchase_records(PURCHASE_HISTORY_PATH)[-5:]

    stats = _load_dashboard_stats(recommendations)

    return render_template(
        "opinador.html",
        iface_path="/iface",
        confirmation=confirmation,
        feedback_context=feedback_context,
        recommendation_context={"user_id": recommendation_user_id} if recommendation_user_id else None,
        recommendation_limit=recommendation_limit,
        recommendations=recommendations,
        recent_purchases=recent_purchases[-5:],
        stats=stats,
    )


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["opinador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("OpinadorAgent", "Opinador", args.port, host=hostname),
            "data_dir": Path(args.data_dir),
        }
    )
    directory = build_directory_agent(args.directory_host, args.directory_port)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, directory, DSO.OpinadorAgent, 0),
    )


if __name__ == "__main__":
    main()
