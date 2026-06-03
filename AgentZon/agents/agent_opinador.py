# -*- coding: utf-8 -*-
"""
filename: agent_opinador

Agent opinador AgentZon (feedback, suggeriments i devolucions).

/comm entrada ACL
/iface dashboard web
/Stop para l'agent
"""

import argparse
from pathlib import Path

from flask import Flask, render_template, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
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
from services.agent_common_service import get_client_ip_from_request
from services.history_service import (
    load_feedback_records,
    load_purchase_records,
    record_feedback,
    record_purchase,
)
from services.catalog_service import get_products_by_ids
from services.opinador_service import evaluate_return_request, generate_recommendations


logger = config_logger(level=1)
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
PURCHASE_HISTORY_PATH = None
SEARCH_HISTORY_PATH = None
FEEDBACK_PATH = None


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, CATALOG_PATH
    global PURCHASE_HISTORY_PATH, SEARCH_HISTORY_PATH, FEEDBACK_PATH, mss_cnt
    AGENT = settings["agent"]
    DirectoryAgent = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    PURCHASE_HISTORY_PATH = data_dir / "historial_compres.ttl"
    SEARCH_HISTORY_PATH = data_dir / "historial_cerques.ttl"
    FEEDBACK_PATH = data_dir / "feedback.ttl"
    mss_cnt = 0


def _msgcnt():
    global mss_cnt
    current = mss_cnt
    mss_cnt += 1
    return current


def get_client_ip():
    return get_client_ip_from_request(request)


def _load_dashboard_stats(recommendations, user_id):
    return {
        "feedback_count": len(load_feedback_records(FEEDBACK_PATH, user_id=user_id)),
        "purchase_count": len(load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id)),
        "recommendation_count": len(recommendations),
    }


def _parse_recommendation_limit(raw_value):
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(10, parsed))


def _get_pending_products(user_id):
    purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id)
    feedbacks = load_feedback_records(FEEDBACK_PATH, user_id=user_id)
    reviewed_product_ids = {pid for fb in feedbacks for pid in fb.get("product_ids", [])}
    purchased_product_ids = {pid for p in purchases for pid in p.get("product_ids", [])}
    pending_ids = list(purchased_product_ids - reviewed_product_ids)
    if not pending_ids:
        return []
    return get_products_by_ids(CATALOG_PATH, pending_ids)


def _build_dashboard_context(interface_user_id, recommendation_limit, confirmation):
    recommendations = pla_de_creacio_de_suggeriments(interface_user_id, limit=recommendation_limit)
    recent_purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=interface_user_id)
    stats = _load_dashboard_stats(recommendations, interface_user_id)
    pending_products = _get_pending_products(interface_user_id)
    logger.info(
        "Dashboard Opinador per %s: %d recomanacions, %d compres recents, %d productes pendents",
        interface_user_id,
        len(recommendations),
        len(recent_purchases),
        len(pending_products),
    )
    return {
        "iface_path": "/iface",
        "interface_user_id": interface_user_id,
        "show_dashboard": True,
        "confirmation": confirmation,
        "pending_products": pending_products,
        "recommendation_context": {"user_id": interface_user_id} if interface_user_id else None,
        "recommendation_limit": recommendation_limit,
        "recommendations": recommendations,
        "recent_purchases": recent_purchases[-5:],
        "stats": stats,
    }


def pla_de_registre_de_compra(request_data):
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


def pla_de_registre_de_feedback(feedback_data):
    logger.info("Registrant feedback %s per a la comanda %s", feedback_data["feedback_id"], feedback_data["order_id"])
    record_feedback(FEEDBACK_PATH, feedback_data)
    return feedback_data


def pla_de_creacio_de_suggeriments(user_id=None, limit=5):
    recommendations = generate_recommendations(
        CATALOG_PATH,
        SEARCH_HISTORY_PATH,
        PURCHASE_HISTORY_PATH,
        user_id=user_id,
        limit=limit,
    )
    logger.info(
        "Generats %d suggeriments per a l'usuari %s (limit=%d)",
        len(recommendations),
        user_id or "global",
        limit,
    )
    return recommendations


def pla_de_consulta_de_criteris_devolucio(request_data):
    logger.info(
        "Validant devolucio %s de la comanda %s (%d productes)",
        request_data.get("return_id", ""),
        request_data.get("order_id", ""),
        len(request_data.get("product_ids", [])),
    )
    decision = evaluate_return_request(CATALOG_PATH, PURCHASE_HISTORY_PATH, request_data)
    logger.info(
        "Resolucio devolucio %s: %s",
        decision.get("return_id", ""),
        "ACCEPTADA" if decision.get("accepted") else "DENEGADA",
    )
    return decision


def _build_feedback_submission(form_data, user_id):
    requested_product_id = form_data.get("product_id", "").strip()
    if not requested_product_id:
        return None, "No s'ha pogut registrar el feedback: No s'ha seleccionat cap producte vàlid."

    purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id)
    matching_purchases = [p for p in purchases if requested_product_id in p.get("product_ids", [])]

    if not matching_purchases:
        return None, "No s'ha pogut verificar la compra d'aquest producte."

    associated_order = matching_purchases[-1]
    order_id = associated_order["order_id"]
    logger.info(
        "Feedback UI: producte %s associat a comanda %s per usuari %s",
        requested_product_id,
        order_id,
        user_id,
    )

    feedback_id = f"FB-{requested_product_id}-{order_id}"

    try:
        rating = int(form_data.get("rating", "0"))
    except ValueError:
        return None, "No s'ha pogut registrar el feedback: puntuació no vàlida."

    rating = max(1, min(5, rating))

    return {
        "feedback_id": feedback_id,
        "user_id": user_id,
        "order_id": order_id,
        "rating": rating,
        "comment": form_data.get("comment", "").strip(),
        "product_ids": [requested_product_id],
    }, ""


def pla_registre_compra_acl(gm, content, sender):
    request_data = parse_peticio_registre_compra(gm, content)
    pla_de_registre_de_compra(request_data)
    return build_confirmacio_registre_compra(
        request_data["order_id"],
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def pla_devolucio_acl(gm, content, sender):
    request_data = parse_peticio_devolucio(gm, content)
    decision = pla_de_consulta_de_criteris_devolucio(request_data)
    return build_resolucio_devolucio(
        decision,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def pla_feedback_acl(gm, content, sender):
    feedback_data = parse_resposta_feedback(gm, content)
    pla_de_registre_de_feedback(feedback_data)
    response_graph = Graph()
    return build_message(
        response_graph,
        ACL.inform,
        sender=AGENT.uri,
        receiver=sender,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=mss_cnt,
    )


PLANS = {
    AZON.PeticioRegistreCompra: pla_registre_compra_acl,
    AZON.PeticioDevolucio: pla_devolucio_acl,
    AZON.RespostaFeedback: pla_feedback_acl,
}


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio de l'agent opinador.
    """
    global mss_cnt

    print("INFO AgenteOpinador => Peticio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")

    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO AgenteOpinador => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        if perf != ACL.request:
            gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
            print("INFO AgenteOpinador => No es una request FIPA ACL")
        else:
            content = msgdic["content"]
            accion = gm.value(subject=content, predicate=RDF.type)
            plan = PLANS.get(accion)
            if plan is None:
                gr = build_message(
                    Graph(),
                    ACL["not-understood"],
                    sender=AGENT.uri,
                    receiver=msgdic.get("sender"),
                    msgcnt=mss_cnt,
                )
                print("INFO AgenteOpinador => Accio no suportada: %s" % accion)
            else:
                print("INFO AgenteOpinador => Accio %s" % accion)
                gr = plan(gm, content, msgdic.get("sender"))

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/iface", methods=["GET", "POST"])
def browser_iface():
    """
    Permet la comunicacio amb l'agent via un navegador.
    """
    view = request.values.get("view", "home").strip().lower()
    confirmation = request.args.get("confirmation", "")
    interface_user_id = get_client_ip()
    recommendation_limit = _parse_recommendation_limit(request.values.get("limit", 5))

    if request.method == "POST" and request.form.get("action") == "feedback":
        print("INFO AgenteOpinador => POST feedback de %s" % interface_user_id)
        feedback_data, error = _build_feedback_submission(request.form, interface_user_id)
        if feedback_data is not None:
            pla_de_registre_de_feedback(feedback_data)
            confirmation = "Feedback registrat correctament per al producte seleccionat!"
        elif error:
            confirmation = error
        view = "dashboard"

    if view != "dashboard":
        return render_template(
            "opinador.html",
            iface_path="/iface",
            interface_user_id=interface_user_id,
            show_dashboard=False,
            stats=_load_dashboard_stats([], interface_user_id),
        )

    return render_template("opinador.html", **_build_dashboard_context(interface_user_id, recommendation_limit, confirmation))


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["opinador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("OpinadorAgent", "Opinador", args.port, host=hostname),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: (
            register_with_directory(AGENT, DirectoryAgent, DSO.OpinadorAgent, 0)
            if DirectoryAgent is not None
            else False
        ),
    )
