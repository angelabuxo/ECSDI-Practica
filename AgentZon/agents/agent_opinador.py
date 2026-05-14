"""Opinion agent that records purchases, feedback, suggestions, and return checks."""

import argparse
from pathlib import Path

from flask import Flask, jsonify, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON
from config import (
    DEFAULT_PORTS,
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_runtime_hostname,
)
from protocols.compra import build_confirmacio_registre_compra, parse_peticio_registre_compra
from protocols.opinador import build_resolucio_devolucio, build_resposta_feedback, parse_feedback_entry, parse_peticio_consulta_devolucio
from services.feedback_service import collect_due_feedback, record_feedback
from services.history_service import record_purchase
from services.rdf_store import load_graph
from services.recommendation_service import generate_recommendations
from services.return_service import evaluate_return_request


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
PURCHASE_HISTORY_PATH = None
SEARCH_HISTORY_PATH = None
FEEDBACK_PATH = None
CATALOG_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings):
    global AGENT, PURCHASE_HISTORY_PATH, SEARCH_HISTORY_PATH, FEEDBACK_PATH, CATALOG_PATH, COUNTER
    AGENT = settings["agent"]
    data_dir = Path(settings["data_dir"])
    PURCHASE_HISTORY_PATH = data_dir / "historial_compres.ttl"
    SEARCH_HISTORY_PATH = data_dir / "historial_cerques.ttl"
    FEEDBACK_PATH = data_dir / "feedback.ttl"
    CATALOG_PATH = data_dir / "productes.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def pla_registre_de_compra(request_data):
    order = {
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "user_name": "history-user",
        "products": request_data["products"],
        "shipping_data": request_data.get(
            "shipping_data",
            {
                "user_id": request_data["user_id"],
                "user_name": "history-user",
                "street_address": "",
                "city": "",
                "priority": "",
                "payment_method": "",
            },
        ),
        "delivery_date": request_data.get("delivery_date"),
    }
    logger.info("Registrant historial de compra per a la comanda %s", order["order_id"])
    record_purchase(PURCHASE_HISTORY_PATH, order)


def pla_registrar_feedback(feedback_data):
    logger.info("Registrant feedback %s per a la comanda %s", feedback_data["feedback_id"], feedback_data["order_id"])
    record_feedback(FEEDBACK_PATH, feedback_data)


def pla_crear_suggeriments(user_id=None, limit=5):
    recommendations = generate_recommendations(SEARCH_HISTORY_PATH, PURCHASE_HISTORY_PATH, CATALOG_PATH, user_id=user_id, limit=limit)
    logger.info("Generades %d recomanacions%s", len(recommendations), f" per a l'usuari {user_id}" if user_id else "")
    return recommendations


def pla_consulta_devolucio(request_data):
    logger.info("Consultant criteris de devolució per a la comanda %s", request_data["order_id"])
    return evaluate_return_request(PURCHASE_HISTORY_PATH, request_data)


def pla_demanar_feedback():
    return collect_due_feedback(PURCHASE_HISTORY_PATH)


def _parse_feedback_payload():
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict(flat=True)
        if not data:
            data = request.args.to_dict(flat=True)
    products = data.get("products") or data.get("product_ids") or []
    if isinstance(products, str):
        products = [item for item in products.split(",") if item]
    elif hasattr(products, "to_list"):
        products = products.to_list()
    return {
        "feedback_id": str(data.get("feedback_id") or data.get("order_id") or f"FB-{next_counter()}"),
        "order_id": str(data.get("order_id", "")),
        "user_id": str(data.get("user_id", "")),
        "score": int(data.get("score", data.get("puntuacio", 0))),
        "comment": str(data.get("comment", data.get("comentari", ""))),
        "products": [str(product_id) for product_id in products],
    }


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
        request_data = parse_peticio_consulta_devolucio(message_graph, content)
        result = pla_consulta_devolucio(request_data)
        response = build_resolucio_devolucio(
            request_data["request_id"],
            result["accepted"],
            result["reason"],
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            request_content=content,
            msgcnt=next_counter(),
        )
        return response.serialize(format="xml")

    if content_type in {AZON.Feedback, AZON.RespostaFeedback}:
        feedback_data = parse_feedback_entry(message_graph, content)
        pla_registrar_feedback(feedback_data)
        response = build_resposta_feedback(
            feedback_data["feedback_id"],
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            request_content=content,
            msgcnt=next_counter(),
        )
        return response.serialize(format="xml")

    logger.warning("OpinadorAgent ha rebut un tipus de missatge no suportat: %s", content_type)
    return build_message(
        Graph(),
        ACL["not-understood"],
        sender=AGENT.uri,
        msgcnt=next_counter(),
    ).serialize(format="xml")


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "GET":
        return jsonify(pla_demanar_feedback())

    feedback_data = _parse_feedback_payload()
    pla_registrar_feedback(feedback_data)
    return jsonify({"status": "ok", "feedback_id": feedback_data["feedback_id"]})


@app.route("/recommendations")
def recommendations():
    user_id = request.args.get("user_id") or None
    limit = int(request.args.get("limit", 5))
    return jsonify(pla_crear_suggeriments(user_id=user_id, limit=limit))


@app.route("/info")
def info():
    return load_graph(PURCHASE_HISTORY_PATH).serialize(format="turtle")


@app.route("/stop")
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

    configure_runtime({"agent": build_agent("OpinadorAgent", "Opinador", args.port, host=hostname), "data_dir": Path(args.data_dir)})
    directory = build_directory_agent(args.directory_host, args.directory_port)
    logger.info("Registrant %s al directori %s", AGENT.name, directory.address)
    register_with_directory(AGENT, directory, DSO.OpinadorAgent, 0)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
