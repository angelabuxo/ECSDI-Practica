# -*- coding: utf-8 -*-
"""
filename: agent_retornador

Agent retornador AgentZon (devolucions i reemborsaments).

/comm entrada ACL
/iface formulari web
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
from AgentUtil.OntoNamespaces import AZON
from config import (
    DEFAULT_PORTS,
    TEMPLATE_DIR,
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_agent_hosts,
    serve_agent,
)
from protocols.opinador import (
    build_peticio_consulta_compres_usuari,
    build_peticio_devolucio,
    build_resolucio_devolucio,
    parse_resultat_consulta_compres_usuari,
    parse_peticio_devolucio,
    parse_resolucio_devolucio,
)
from protocols.pagament import (
    build_peticio_retorn_diners,
    extract_confirmacio_retorn_diners,
)
from services.agent_common_service import (
    get_client_ip_from_request,
    replace_url_path,
    resolve_agent_via_directory,
)
from services.payment_service import record_refund
from services.retornador_service import (
    RETURN_REASON_OPTIONS,
    build_aggregate_return_decision,
    build_purchased_products_from_orders,
    build_refund_batches_from_products,
    build_return_request_from_selection,
)


logger = config_logger(level=1)
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
REFUNDS_PATH = None
PURCHASE_HISTORY_PATH = None
CATALOG_PATH = None
SHIPPING_RESPONSIBILITY_PATH = None


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, REFUNDS_PATH, PURCHASE_HISTORY_PATH
    global CATALOG_PATH, SHIPPING_RESPONSIBILITY_PATH, mss_cnt
    AGENT = settings["agent"]
    DirectoryAgent = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    REFUNDS_PATH = data_dir / "devolucions.ttl"
    PURCHASE_HISTORY_PATH = None
    CATALOG_PATH = None
    SHIPPING_RESPONSIBILITY_PATH = None
    mss_cnt = 0


def _msgcnt():
    global mss_cnt
    current = mss_cnt
    mss_cnt += 1
    return current


def get_client_ip():
    return get_client_ip_from_request(request)


def resolve_opinador_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.OpinadorAgent)


def resolve_cobrador_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CobradorAgent)


def resolve_compra_iface_url():
    try:
        compra_agent = resolve_agent_via_directory(
            AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CompraAgent,
        )
        return replace_url_path(compra_agent.address, "/iface")
    except Exception:
        print("INFO AgenteRetornador => No s'ha pogut resoldre Compra per a la interficie")
        return ""


def _normalize_return_request(return_request):
    if return_request.get("order_groups"):
        return return_request
    return {
        "return_id": return_request["return_id"],
        "user_id": return_request["user_id"],
        "reason": return_request.get("reason", ""),
        "order_groups": {
            return_request["order_id"]: sorted(set(return_request.get("product_ids", []))),
        },
    }


def _consult_opinador_per_order(return_request):
    opinador = resolve_opinador_agent()
    order_decisions = {}
    for order_id, product_ids in return_request["order_groups"].items():
        logger.info(
            "Consultant Opinador per comanda %s (%d producte(s))",
            order_id,
            len(product_ids),
        )
        opinion_message = build_peticio_devolucio(
            {
                "return_id": f"{return_request['return_id']}-{order_id}",
                "order_id": order_id,
                "user_id": return_request["user_id"],
                "amount": None,
                "reason": return_request.get("reason", ""),
                "seller_id": None,
                "products": [{"product_id": product_id} for product_id in product_ids],
            },
            sender=AGENT.uri,
            receiver=opinador.uri,
            msgcnt=_msgcnt(),
        )
        decision_graph = MESSAGE_SENDER(opinion_message, opinador.address)
        decision = parse_resolucio_devolucio(decision_graph)
        decision["requested_product_ids"] = product_ids
        if decision.get("accepted"):
            decision["accepted_product_ids"] = decision.get("product_ids", [])
        else:
            decision["accepted_product_ids"] = []
        order_decisions[order_id] = decision
    return order_decisions


def _fetch_user_purchases_from_opinador(user_id):
    opinador = resolve_opinador_agent()
    purchase_message = build_peticio_consulta_compres_usuari(
        user_id,
        sender=AGENT.uri,
        receiver=opinador.uri,
        msgcnt=_msgcnt(),
    )
    response_graph = MESSAGE_SENDER(purchase_message, opinador.address)
    return parse_resultat_consulta_compres_usuari(response_graph)


def pla_compliment_de_devolucio(return_request):
    normalized = _normalize_return_request(return_request)
    parent_return_id = normalized["return_id"]
    logger.info(
        "Iniciant validacio devolucio %s (%d comandes)",
        parent_return_id,
        len(normalized["order_groups"]),
    )

    order_decisions = _consult_opinador_per_order(normalized)
    aggregate = build_aggregate_return_decision(
        parent_return_id,
        normalized["user_id"],
        normalized.get("reason", ""),
        order_decisions,
        CATALOG_PATH,
    )
    if not aggregate.get("accepted"):
        return aggregate, None

    refund_confirmations = []
    batch_index = 0
    for order_id in sorted(normalized["order_groups"]):
        accepted_ids = order_decisions[order_id].get("accepted_product_ids", [])
        if not accepted_ids:
            continue
        accepted_products = list(order_decisions[order_id].get("products", []))
        sub_decision = {
            "return_id": parent_return_id,
            "order_id": order_id,
            "user_id": normalized["user_id"],
            "reason": normalized.get("reason", ""),
            "product_ids": accepted_ids,
            "products": accepted_products,
            "seller_id": None,
        }
        for batch in build_refund_batches_from_products(accepted_products):
            batch_index += 1
            batch_product_ids = set(batch["product_ids"])
            batch_decision = {
                **sub_decision,
                "return_id": (
                    parent_return_id
                    if batch_index == 1 and len(normalized["order_groups"]) == 1
                    else f"{parent_return_id}-{batch_index}"
                ),
                "seller_id": batch["seller_id"],
                "product_ids": batch["product_ids"],
                "products": [product for product in accepted_products if product.get("product_id") in batch_product_ids],
                "amount": batch["amount"],
            }
            confirmation = pla_retorn(batch_decision)
            refund_confirmations.append(confirmation)
            record_refund(
                REFUNDS_PATH,
                {
                    "return_id": batch_decision["return_id"],
                    "order_id": batch_decision["order_id"],
                    "user_id": batch_decision["user_id"],
                    "amount": batch_decision["amount"],
                    "reason": batch_decision.get("reason", ""),
                    "seller_id": batch_decision.get("seller_id"),
                    "product_ids": batch_decision.get("product_ids", []),
                    "status": confirmation.get("status", "RETORNAT"),
                },
            )

    total_refund_amount = round(sum(refund["amount"] for refund in refund_confirmations), 2)
    global_status = "RETORNAT" if refund_confirmations and all(
        refund["status"] == "RETORNAT" for refund in refund_confirmations
    ) else "PARCIAL"
    record_refund(
        REFUNDS_PATH,
        {
            "return_id": parent_return_id,
            "order_id": aggregate.get("order_id", ""),
            "user_id": normalized["user_id"],
            "amount": total_refund_amount,
            "reason": normalized.get("reason", ""),
            "seller_id": None,
            "product_ids": aggregate.get("product_ids", []),
            "status": global_status,
        },
    )
    aggregate["amount"] = total_refund_amount
    if total_refund_amount > 0:
        aggregate["reason"] = (
            f"{aggregate['reason']} Reemborsament {global_status} de {total_refund_amount:.2f} EUR."
        ).strip()
    return aggregate, {"amount": total_refund_amount, "status": global_status}


def pla_retorn(decision):
    cobrador = resolve_cobrador_agent()
    refund_message = build_peticio_retorn_diners(
        {
            "return_id": decision["return_id"],
            "order_id": decision["order_id"],
            "user_id": decision["user_id"],
            "amount": decision["amount"],
            "reason": decision.get("reason", ""),
            "seller_id": decision.get("seller_id"),
            "product_ids": decision.get("product_ids", []),
        },
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=_msgcnt(),
    )
    response_graph = MESSAGE_SENDER(refund_message, cobrador.address)
    return extract_confirmacio_retorn_diners(response_graph)


def _load_purchased_products_for_iface(user_id):
    return build_purchased_products_from_orders(
        _fetch_user_purchases_from_opinador(user_id),
        logger=logger,
        user_id=user_id,
    )


def _render_retornador_iface(
    interface_user_id,
    purchased_products,
    *,
    compra_url="",
    selected_products=None,
    reason="",
    decision=None,
    error="",
):
    return render_template(
        "retornador.html",
        iface_path="/iface",
        compra_url=compra_url,
        interface_user_id=interface_user_id,
        purchased_products=purchased_products,
        selected_products=selected_products or [],
        reason=reason,
        return_reason_options=RETURN_REASON_OPTIONS,
        decision=decision,
        error=error,
    )


def pla_devolucio_acl(gm, content, sender):
    request_data = parse_peticio_devolucio(gm, content)
    decision, _ = pla_compliment_de_devolucio(request_data)
    return build_resolucio_devolucio(
        decision,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


@app.route("/iface", methods=["GET", "POST"])
def browser_iface():
    """
    Permet la comunicacio amb l'agent via un navegador.
    """
    compra_url = resolve_compra_iface_url()
    interface_user_id = get_client_ip()
    purchased_products = _load_purchased_products_for_iface(interface_user_id)

    if request.method == "GET":
        return _render_retornador_iface(
            interface_user_id,
            purchased_products,
            compra_url=compra_url,
        )

    selected_products = request.form.getlist("selected_products")
    reason = request.form.get("reason", "").strip()
    return_request, build_error = build_return_request_from_selection(
        selected_products,
        reason,
        interface_user_id,
        logger=logger,
    )
    if return_request is None:
        return _render_retornador_iface(
            interface_user_id,
            purchased_products,
            compra_url=compra_url,
            selected_products=selected_products,
            reason=reason,
            error=build_error,
        )

    try:
        decision, _ = pla_compliment_de_devolucio(return_request)
        return _render_retornador_iface(
            interface_user_id,
            purchased_products,
            compra_url=compra_url,
            selected_products=selected_products,
            reason=reason,
            decision=decision,
        )
    except Exception:
        logger.exception("Error processant la devolució des de la interfície")
        return _render_retornador_iface(
            interface_user_id,
            purchased_products,
            compra_url=compra_url,
            selected_products=selected_products,
            reason=reason,
            error="No s'ha pogut processar la devolució ara mateix.",
        )


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio de l'agent retornador.
    """
    global mss_cnt

    print("INFO AgenteRetornador => Peticio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")

    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO AgenteRetornador => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        if perf != ACL.request:
            gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
            print("INFO AgenteRetornador => No es una request FIPA ACL")
        else:
            content = msgdic["content"]
            accion = gm.value(subject=content, predicate=RDF.type)
            if accion != AZON.PeticioDevolucio:
                gr = build_message(
                    Graph(),
                    ACL["not-understood"],
                    sender=AGENT.uri,
                    receiver=msgdic.get("sender"),
                    msgcnt=mss_cnt,
                )
                print("INFO AgenteRetornador => Accio no suportada: %s" % accion)
            else:
                print("INFO AgenteRetornador => PeticioDevolucio")
                gr = pla_devolucio_acl(gm, content, msgdic.get("sender"))

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["retornador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent("RetornadorAgent", "Retornador", args.port, host=publish_host),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DirectoryAgent, DSO.RetornadorAgent, 0),
    )
