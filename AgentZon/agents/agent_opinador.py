# -*- coding: utf-8 -*-
"""
filename: agent_opinador

Agent opinador AgentZon (feedback, suggeriments i devolucions).

/comm entrada ACL
/iface dashboard web
/Stop para l'agent
"""

import argparse
import json
import os
import queue as queue_lib
import time
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
    OPINADOR_FEEDBACK_INTERVAL_SEC,
    OPINADOR_FEEDBACK_MIN_SECONDS,
    OPINADOR_FEEDBACK_POLICY_DAYS,
    OPINADOR_RECOMMENDATION_INTERVAL_SEC,
    TEMPLATE_DIR,
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_agent_hosts,
    serve_agent,
    _wait_for_shutdown_signal,
    _wait_until_server_ready_for_registration,
)
from protocols.compra import build_confirmacio_registre_compra, parse_peticio_registre_compra
from protocols.cerca import build_peticio_cerca, extract_result_products
from protocols.opinador import (
    build_confirmacio_registre_cerca,
    build_resultat_consulta_compres_usuari,
    build_resultat_consulta_comanda,
    build_resolucio_devolucio,
    parse_peticio_consulta_compres_usuari,
    parse_peticio_consulta_comanda,
    parse_peticio_registre_cerca,
    parse_peticio_devolucio,
    parse_resposta_feedback,
)
from services.agent_common_service import (
    get_client_ip_from_request,
    replace_url_path,
    resolve_agent_via_directory,
)
from services.history_service import (
    load_feedback_records,
    load_purchase_records,
    load_search_records,
    record_feedback,
    record_purchase,
    record_search,
)
from services.order_service import load_order
from services.opinador_service import (
    build_feedback_requests_for_user,
    evaluate_return_request,
    generate_recommendations_from_records,
    get_purchases_pending_feedback,
    is_feedback_eligible,
    list_known_user_ids,
)


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
FEEDBACK_POLICY_DAYS = OPINADOR_FEEDBACK_POLICY_DAYS
FEEDBACK_MIN_SECONDS = OPINADOR_FEEDBACK_MIN_SECONDS
RECOMMENDATION_INTERVAL_SEC = OPINADOR_RECOMMENDATION_INTERVAL_SEC
FEEDBACK_INTERVAL_SEC = OPINADOR_FEEDBACK_INTERVAL_SEC
PROACTIVE_ENABLED = True
PROACTIVE_RECOMMENDATION_LIMIT = 5
PROACTIVE_STATE_PATH = None


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, CATALOG_PATH
    global PURCHASE_HISTORY_PATH, SEARCH_HISTORY_PATH, FEEDBACK_PATH, mss_cnt
    global FEEDBACK_POLICY_DAYS, FEEDBACK_MIN_SECONDS, RECOMMENDATION_INTERVAL_SEC, FEEDBACK_INTERVAL_SEC
    global PROACTIVE_ENABLED, PROACTIVE_RECOMMENDATION_LIMIT, PROACTIVE_STATE_PATH
    AGENT = settings["agent"]
    DirectoryAgent = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = None
    PURCHASE_HISTORY_PATH = data_dir / "historial_compres.ttl"
    SEARCH_HISTORY_PATH = data_dir / "historial_cerques.ttl"
    FEEDBACK_PATH = data_dir / "feedback.ttl"
    PROACTIVE_STATE_PATH = data_dir / "proactive_state.json"
    FEEDBACK_POLICY_DAYS = settings.get("feedback_policy_days", OPINADOR_FEEDBACK_POLICY_DAYS)
    if "feedback_min_seconds" in settings:
        FEEDBACK_MIN_SECONDS = settings["feedback_min_seconds"]
    else:
        FEEDBACK_MIN_SECONDS = OPINADOR_FEEDBACK_MIN_SECONDS
    RECOMMENDATION_INTERVAL_SEC = settings.get(
        "recommendation_interval_sec",
        OPINADOR_RECOMMENDATION_INTERVAL_SEC,
    )
    FEEDBACK_INTERVAL_SEC = settings.get("feedback_interval_sec", OPINADOR_FEEDBACK_INTERVAL_SEC)
    PROACTIVE_ENABLED = settings.get("proactive_enabled", True)
    PROACTIVE_RECOMMENDATION_LIMIT = settings.get("proactive_recommendation_limit", 5)
    mss_cnt = 0
    _reset_proactive_state()


def _msgcnt():
    global mss_cnt
    current = mss_cnt
    mss_cnt += 1
    return current


def get_client_ip():
    return get_client_ip_from_request(request)


def _feedback_eligibility_kwargs():
    if FEEDBACK_MIN_SECONDS is not None:
        return {"min_seconds": FEEDBACK_MIN_SECONDS, "min_days": 0}
    return {"min_days": FEEDBACK_POLICY_DAYS, "min_seconds": None}


def _parse_recommendation_limit(raw_value):
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return PROACTIVE_RECOMMENDATION_LIMIT
    return max(1, min(10, parsed))


def resolve_cercador_iface_url():
    try:
        cercador_agent = resolve_cercador_agent()
        return replace_url_path(cercador_agent.address, "/iface")
    except Exception as exc:
        logger.warning("No s'ha pogut resoldre Cercador per a la interficie: %s", exc)
        return ""


def resolve_cercador_agent():
    return resolve_agent_via_directory(
        AGENT,
        DirectoryAgent,
        MESSAGE_SENDER,
        _msgcnt,
        DSO.CercadorAgent,
    )


def _empty_proactive_state():
    return {
        "recommendations": {},
        "feedback_requests": {},
        "last_recommendation_run": None,
        "last_feedback_run": None,
    }


def _read_proactive_state():
    if PROACTIVE_STATE_PATH is None or not PROACTIVE_STATE_PATH.exists():
        return _empty_proactive_state()
    try:
        return json.loads(PROACTIVE_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("No s'ha pogut llegir l'estat proactiu: %s", exc)
        return _empty_proactive_state()


def _write_proactive_state(state):
    if PROACTIVE_STATE_PATH is None:
        return
    temp_path = PROACTIVE_STATE_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(PROACTIVE_STATE_PATH)


def _reset_proactive_state():
    if PROACTIVE_STATE_PATH is not None and PROACTIVE_STATE_PATH.exists():
        PROACTIVE_STATE_PATH.unlink(missing_ok=True)
    tmp_path = PROACTIVE_STATE_PATH.with_suffix(".json.tmp") if PROACTIVE_STATE_PATH else None
    if tmp_path is not None:
        tmp_path.unlink(missing_ok=True)


def _get_pending_products(user_id):
    pending = get_purchases_pending_feedback(
        PURCHASE_HISTORY_PATH,
        FEEDBACK_PATH,
        CATALOG_PATH,
        user_id,
        **_feedback_eligibility_kwargs(),
    )
    return pending["eligible_products"]


def _get_proactive_recommendations(user_id, limit):
    cached = _read_proactive_state()["recommendations"].get(user_id, [])
    if cached:
        return cached[:limit]
    return pla_de_creacio_de_suggeriments(user_id, limit=limit)


def _get_proactive_feedback_requests(user_id):
    return list(_read_proactive_state()["feedback_requests"].get(user_id, []))


def _build_iface_context(interface_user_id, confirmation="", recommendation_limit=None):
    limit = recommendation_limit or PROACTIVE_RECOMMENDATION_LIMIT
    recommendations = _get_proactive_recommendations(interface_user_id, limit)
    recent_purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=interface_user_id)
    pending_state = get_purchases_pending_feedback(
        PURCHASE_HISTORY_PATH,
        FEEDBACK_PATH,
        CATALOG_PATH,
        interface_user_id,
        **_feedback_eligibility_kwargs(),
    )
    pending_products = pending_state["eligible_products"]
    waiting_products = pending_state["waiting_products"]
    feedback_requests = _get_proactive_feedback_requests(interface_user_id)
    logger.info(
        "Interficie Opinador per %s: %d suggeriments, %d compres recents, "
        "%d productes valorables, %d encara en espera",
        interface_user_id,
        len(recommendations),
        len(recent_purchases),
        len(pending_products),
        len(waiting_products),
    )
    return {
        "iface_path": "/iface",
        "cercador_url": resolve_cercador_iface_url(),
        "confirmation": confirmation,
        "recommendations": recommendations,
        "recommendation_limit": limit,
        "pending_products": pending_products,
        "waiting_products": waiting_products,
        "feedback_requests": feedback_requests,
        "feedback_policy_days": FEEDBACK_POLICY_DAYS,
        "feedback_min_seconds": FEEDBACK_MIN_SECONDS,
        "feedback_demo_mode": FEEDBACK_MIN_SECONDS is not None,
        "recent_purchases": recent_purchases[-5:],
        "stats": {
            "feedback_count": len(load_feedback_records(FEEDBACK_PATH, user_id=interface_user_id)),
            "purchase_count": len(recent_purchases),
            "recommendation_count": len(recommendations),
        },
        "proactive_last_recommendation_run": _read_proactive_state()["last_recommendation_run"],
        "proactive_last_feedback_run": _read_proactive_state()["last_feedback_run"],
        "recommendation_interval": RECOMMENDATION_INTERVAL_SEC,
        "feedback_interval": FEEDBACK_INTERVAL_SEC,
    }


def pla_de_registre_de_compra(request_data):
    order = {
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "user_name": request_data.get("user_name", "history-user"),
        "purchase_date": request_data.get("purchase_date"),
        "delivery_date": request_data.get("delivery_date", ""),
        "final_delivery_date": request_data.get("final_delivery_date"),
        "status": request_data.get("status", ""),
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


def pla_registre_cerca_acl(gm, content, sender):
    request_data = parse_peticio_registre_cerca(gm)
    record_search(
        SEARCH_HISTORY_PATH,
        request_data["criteria"],
        request_data["products"],
        user_id=request_data["user_id"],
    )
    return build_confirmacio_registre_cerca(
        request_data["user_id"],
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def pla_consulta_compres_usuari_acl(gm, content, sender):
    user_id = parse_peticio_consulta_compres_usuari(gm)
    purchases = load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id)
    return build_resultat_consulta_compres_usuari(
        user_id,
        purchases,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def _fetch_catalog_products():
    try:
        cercador = resolve_cercador_agent()
    except Exception as exc:
        logger.warning("No s'ha pogut resoldre Cercador per obtenir el cataleg: %s", exc)
        return []
    request_graph, request_content = build_peticio_cerca(f"opinador-catalog-{_msgcnt()}")
    message = build_message(
        request_graph,
        ACL.request,
        sender=AGENT.uri,
        receiver=cercador.uri,
        content=request_content,
        ontology=ONTOLOGY_URI,
        msgcnt=_msgcnt(),
    )
    try:
        reply = MESSAGE_SENDER(message, cercador.address)
    except Exception as exc:
        logger.warning("No s'ha pogut recuperar el cataleg remot: %s", exc)
        return []
    return extract_result_products(reply)


def pla_de_creacio_de_suggeriments(user_id=None, limit=5):
    recommendations = generate_recommendations_from_records(
        _fetch_catalog_products(),
        load_search_records(SEARCH_HISTORY_PATH, user_id=user_id),
        load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id),
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


def pla_de_demanar_feedback(user_id=None):
    if not user_id:
        return []

    feedback_requests = build_feedback_requests_for_user(
        PURCHASE_HISTORY_PATH,
        FEEDBACK_PATH,
        CATALOG_PATH,
        user_id,
        **_feedback_eligibility_kwargs(),
    )
    logger.info(
        "Pla demanar feedback: %d sol·licituds generades per l'usuari %s",
        len(feedback_requests),
        user_id,
    )

    return feedback_requests


def _run_proactive_recommendation_cycle():
    user_ids = list_known_user_ids(PURCHASE_HISTORY_PATH, SEARCH_HISTORY_PATH)
    generated = {}
    for user_id in user_ids:
        generated[user_id] = pla_de_creacio_de_suggeriments(
            user_id,
            limit=PROACTIVE_RECOMMENDATION_LIMIT,
        )
    state = _read_proactive_state()
    state["recommendations"] = generated
    state["last_recommendation_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_proactive_state(state)
    logger.info(
        "Cicle proactiu de recomanacions completat per a %d usuaris",
        len(generated),
    )


def _run_proactive_feedback_cycle():
    user_ids = list_known_user_ids(PURCHASE_HISTORY_PATH, SEARCH_HISTORY_PATH)
    feedback_by_user = {}
    for user_id in user_ids:
        feedback_by_user[user_id] = pla_de_demanar_feedback(user_id)
    state = _read_proactive_state()
    state["feedback_requests"] = feedback_by_user
    state["last_feedback_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_proactive_state(state)
    logger.info(
        "Cicle proactiu de feedback completat per a %d usuaris",
        len(user_ids),
    )


def _run_proactive_scheduler_loop(queue):
    """Bucle proactiu dins del Process concurrent (patro SimplePersonalAgent + cua d'aturada)."""
    try:
        _run_proactive_recommendation_cycle()
        _run_proactive_feedback_cycle()
    except Exception as exc:
        logger.exception("Error al primer cicle proactiu de l'Opinador: %s", exc)

    next_recommendation = time.monotonic() + RECOMMENDATION_INTERVAL_SEC
    next_feedback = time.monotonic() + FEEDBACK_INTERVAL_SEC
    while True:
        try:
            if queue.get(timeout=1.0) == 0:
                return
        except queue_lib.Empty:
            if os.getppid() == 1:
                return

        now = time.monotonic()
        if now >= next_recommendation:
            try:
                _run_proactive_recommendation_cycle()
            except Exception as exc:
                logger.exception("Error al cicle proactiu de recomanacions: %s", exc)
            next_recommendation = now + RECOMMENDATION_INTERVAL_SEC
        if now >= next_feedback:
            try:
                _run_proactive_feedback_cycle()
            except Exception as exc:
                logger.exception("Error al cicle proactiu de feedback: %s", exc)
            next_feedback = now + FEEDBACK_INTERVAL_SEC


def _opinador_agent_behaviour(queue, register_fn, ready_host=None, ready_port=None):
    """Comportament concurrent: registre al directori + plans proactius periòdics."""
    if register_fn is not None:
        if ready_host is not None and ready_port is not None:
            if not _wait_until_server_ready_for_registration(queue, ready_host, ready_port):
                return
        register_fn()
    if not PROACTIVE_ENABLED:
        _wait_for_shutdown_signal(queue)
        return
    _run_proactive_scheduler_loop(queue)


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
    if not is_feedback_eligible(
        associated_order.get("purchase_date", ""),
        **_feedback_eligibility_kwargs(),
    ):
        pending = get_purchases_pending_feedback(
            PURCHASE_HISTORY_PATH,
            FEEDBACK_PATH,
            CATALOG_PATH,
            user_id,
            **_feedback_eligibility_kwargs(),
        )
        waiting = next(
            (item for item in pending["waiting_products"] if item["product_id"] == requested_product_id),
            None,
        )
        if FEEDBACK_MIN_SECONDS is not None:
            seconds_until = waiting["seconds_until_eligible"] if waiting else FEEDBACK_MIN_SECONDS
            return (
                None,
                f"Encara no pots valorar aquest producte. Cal esperar {seconds_until} segon(s) més "
                f"(mode prova: {FEEDBACK_MIN_SECONDS}s; en producció: {FEEDBACK_POLICY_DAYS} dies).",
            )
        days_until = waiting["days_until_eligible"] if waiting else FEEDBACK_POLICY_DAYS
        return (
            None,
            f"Encara no pots valorar aquest producte. Cal esperar {days_until} dia(es) més "
            f"(mínim {FEEDBACK_POLICY_DAYS} dies des de la compra).",
        )

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


def pla_consulta_comanda_acl(gm, content, sender):
    order_id = parse_peticio_consulta_comanda(gm, content)
    order = load_order(PURCHASE_HISTORY_PATH, order_id)
    if order is None:
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            receiver=sender,
            msgcnt=mss_cnt,
        )
    products_by_id = {}
    for record in load_purchase_records(PURCHASE_HISTORY_PATH, user_id=order["user_id"]):
        if record["order_id"] != order_id:
            continue
        for product in record.get("products", []):
            products_by_id[product["product_id"]] = product
        break
    detailed_products = [products_by_id.get(product_id, {"product_id": product_id}) for product_id in order["product_ids"]]
    return build_resultat_consulta_comanda(
        {**order, "products": detailed_products},
        sender=AGENT.uri,
        receiver=sender,
        msgcnt=mss_cnt,
    )


PLANS = {
    AZON.PeticioRegistreCerca: pla_registre_cerca_acl,
    AZON.PeticioRegistreCompra: pla_registre_compra_acl,
    AZON.PeticioConsultaCompresUsuari: pla_consulta_compres_usuari_acl,
    AZON.PeticioConsultaComanda: pla_consulta_comanda_acl,
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
    confirmation = request.args.get("confirmation", "")
    interface_user_id = get_client_ip()
    recommendation_limit = _parse_recommendation_limit(request.values.get("limit"))

    if request.method == "POST" and request.form.get("action") == "feedback":
        print("INFO AgenteOpinador => POST feedback de %s" % interface_user_id)
        feedback_data, error = _build_feedback_submission(request.form, interface_user_id)
        if feedback_data is not None:
            pla_de_registre_de_feedback(feedback_data)
            confirmation = "Feedback registrat correctament per al producte seleccionat!"
        elif error:
            confirmation = error

    return render_template(
        "opinador.html",
        **_build_iface_context(interface_user_id, confirmation, recommendation_limit),
    )


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["opinador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    parser.add_argument(
        "--feedback-policy-days",
        type=int,
        default=OPINADOR_FEEDBACK_POLICY_DAYS,
        help="Dies de la política real (es mostra a la interficie).",
    )
    parser.add_argument(
        "--feedback-min-seconds",
        type=int,
        default=OPINADOR_FEEDBACK_MIN_SECONDS,
        help="Segons mínims abans de permetre valorar (mode prova; 0 = desactivat, usa dies).",
    )
    parser.add_argument(
        "--recommendation-interval",
        type=int,
        default=OPINADOR_RECOMMENDATION_INTERVAL_SEC,
        help="Segons entre cicles proactius de recomanació.",
    )
    parser.add_argument(
        "--feedback-interval",
        type=int,
        default=OPINADOR_FEEDBACK_INTERVAL_SEC,
        help="Segons entre cicles proactius de sol·licitud de feedback.",
    )
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent("OpinadorAgent", "Opinador", args.port, host=publish_host),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
            "feedback_policy_days": args.feedback_policy_days,
            "feedback_min_seconds": args.feedback_min_seconds or None,
            "recommendation_interval_sec": args.recommendation_interval,
            "feedback_interval_sec": args.feedback_interval,
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: (
            register_with_directory(AGENT, DirectoryAgent, DSO.OpinadorAgent, 0)
            if DirectoryAgent is not None
            else False
        ),
        behaviour_fn=_opinador_agent_behaviour,
    )
