"""Agent Retornador: validació de devolucions i gestió de reemborsaments.

Aquest fitxer es limita a:
- exposar rutes Flask (`/iface`, `/comm`, `/Stop`)
- orquestrar plans de negoci
- delegar càlculs i transformacions a `services/retornador_service.py`
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
from protocols.opinador import (
    build_peticio_devolucio,
    build_resolucio_devolucio,
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
    build_purchased_products_for_user,
    build_refund_batches,
    build_return_request_from_selection,
)


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
REFUNDS_PATH = None
PURCHASE_HISTORY_PATH = None
CATALOG_PATH = None
SHIPPING_RESPONSIBILITY_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    """Inicialitza globals de runtime per a execució i tests."""
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, REFUNDS_PATH, PURCHASE_HISTORY_PATH, CATALOG_PATH
    global SHIPPING_RESPONSIBILITY_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    REFUNDS_PATH = data_dir / "devolucions.ttl"
    PURCHASE_HISTORY_PATH = data_dir / "historial_compres.ttl"
    CATALOG_PATH = data_dir / "productes.ttl"
    SHIPPING_RESPONSIBILITY_PATH = data_dir / "responsable_enviament_productes.ttl"
    COUNTER = 0


def next_counter():
    """Retorna un id incremental per `msgcnt` ACL."""
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


def get_client_ip():
    """Obté la IP real del client HTTP (compatible amb proxy)."""
    return get_client_ip_from_request(request)


def replace_path(address, new_path):
    """Canvia només el path d'una URL mantenint host i esquema."""
    return replace_url_path(address, new_path)


def resolve_agent(agent_type):
    """Resol una adreça d'agent via directori DSO."""
    logger.info("Resolent agent de tipus %s via directori", agent_type)
    resolved = resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, agent_type)
    logger.info("Agent resolt: %s (%s)", resolved.name, resolved.address)
    return resolved


# Plans ----------------------------------------------------------------------------
def _normalize_return_request(return_request):
    """Unifica peticions UI (multi-comanda) i ACL (una comanda)."""
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
    """Demana a l'Opinador la validació de cada comanda per separat."""
    opinador = resolve_agent(DSO.OpinadorAgent)
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
            msgcnt=next_counter(),
        )
        decision_graph = MESSAGE_SENDER(opinion_message, opinador.address)
        decision = parse_resolucio_devolucio(decision_graph)
        decision["requested_product_ids"] = product_ids
        if decision.get("accepted"):
            decision["accepted_product_ids"] = decision.get("product_ids", [])
        else:
            decision["accepted_product_ids"] = []
        order_decisions[order_id] = decision
        logger.info(
            "Comanda %s: %d producte(s) acceptat(s) de %d",
            order_id,
            len(decision["accepted_product_ids"]),
            len(product_ids),
        )
    return order_decisions


def pla_compliment_de_devolucio(return_request):
    """Valida devolució amb Opinador (per comanda) i reemborsa productes acceptats."""
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
        sub_decision = {
            "return_id": parent_return_id,
            "order_id": order_id,
            "user_id": normalized["user_id"],
            "reason": normalized.get("reason", ""),
            "product_ids": accepted_ids,
            "seller_id": None,
        }
        for batch in build_refund_batches(sub_decision, SHIPPING_RESPONSIBILITY_PATH, CATALOG_PATH):
            batch_index += 1
            batch_decision = {
                **sub_decision,
                "return_id": (
                    parent_return_id
                    if batch_index == 1 and len(normalized["order_groups"]) == 1
                    else f"{parent_return_id}-{batch_index}"
                ),
                "seller_id": batch["seller_id"],
                "product_ids": batch["product_ids"],
                "amount": batch["amount"],
            }
            refund_confirmations.append(pla_retorn(batch_decision))

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
    logger.info(
        "Devolucio %s completada (%d productes acceptats, %.2f EUR)",
        parent_return_id,
        len(aggregate.get("accepted_items", [])),
        total_refund_amount,
    )
    return aggregate, {"amount": total_refund_amount, "status": global_status}


def pla_retorn(decision):
    """Demana al Cobrador que executi un reemborsament concret."""
    logger.info(
        "Iniciant retorn de diners per devolucio %s (%.2f EUR)",
        decision.get("return_id", ""),
        decision.get("amount", 0.0),
    )
    cobrador = resolve_agent(DSO.CobradorAgent)
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
        msgcnt=next_counter(),
    )
    response_graph = MESSAGE_SENDER(refund_message, cobrador.address)
    confirmation = extract_confirmacio_retorn_diners(response_graph)
    logger.info(
        "Confirmacio retorn rebuda per %s: estat=%s, import=%.2f",
        confirmation.get("return_id", ""),
        confirmation.get("status", ""),
        confirmation.get("amount", 0.0),
    )
    return confirmation


# Web interface --------------------------------------------------------------------
@app.route("/iface", methods=["GET", "POST"])
def iface():
    """Interfície humana del Retornador."""
    compra_url = ""
    try:
        compra_agent = resolve_agent(DSO.CompraAgent)
        compra_url = replace_path(compra_agent.address, "/iface")
    except Exception:
        logger.warning("No s'ha pogut resoldre l'agent Compra per a la interfície")

    interface_user_id = get_client_ip()
    purchased_products = build_purchased_products_for_user(
        PURCHASE_HISTORY_PATH,
        CATALOG_PATH,
        interface_user_id,
        logger=logger,
    )

    if request.method == "GET":
        logger.info("Retornador /iface GET per usuari %s", interface_user_id)
        return render_template(
            "retornador.html",
            iface_path="/iface",
            compra_url=compra_url,
            interface_user_id=interface_user_id,
            purchased_products=purchased_products,
            selected_products=[],
            reason="",
            return_reason_options=RETURN_REASON_OPTIONS,
            decision=None,
            error="",
        )

    selected_products = request.form.getlist("selected_products")
    reason = request.form.get("reason", "").strip()
    logger.info(
        "Retornador /iface POST per usuari %s amb %d productes seleccionats",
        interface_user_id,
        len(selected_products),
    )
    return_request, build_error = build_return_request_from_selection(
        selected_products,
        reason,
        interface_user_id,
        logger=logger,
    )
    if return_request is None:
        logger.warning("Peticio de devolucio invalida per %s: %s", interface_user_id, build_error)
        return render_template(
            "retornador.html",
            iface_path="/iface",
            compra_url=compra_url,
            interface_user_id=interface_user_id,
            purchased_products=purchased_products,
            selected_products=selected_products,
            reason=reason,
            return_reason_options=RETURN_REASON_OPTIONS,
            decision=None,
            error=build_error,
        )

    try:
        decision, _ = pla_compliment_de_devolucio(return_request)
        logger.info(
            "Resposta final /iface devolucio %s: %s",
            decision.get("return_id", ""),
            "ACCEPTADA" if decision.get("accepted") else "DENEGADA",
        )
        return render_template(
            "retornador.html",
            iface_path="/iface",
            compra_url=compra_url,
            interface_user_id=interface_user_id,
            purchased_products=purchased_products,
            selected_products=selected_products,
            reason=reason,
            return_reason_options=RETURN_REASON_OPTIONS,
            decision=decision,
            error="",
        )
    except Exception:
        logger.exception("Error processant la devolució des de la interfície")
        return render_template(
            "retornador.html",
            iface_path="/iface",
            compra_url=compra_url,
            interface_user_id=interface_user_id,
            purchased_products=purchased_products,
            selected_products=selected_products,
            reason=reason,
            return_reason_options=RETURN_REASON_OPTIONS,
            decision=None,
            error="No s'ha pogut processar la devolució ara mateix.",
        )


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    """Entrada ACL: accepta `PeticioDevolucio` i retorna `ResolucioDevolucio`."""
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
    if message_graph.value(content, RDF.type) != AZON.PeticioDevolucio:
        logger.warning("Rebut accio no suportada a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    request_data = parse_peticio_devolucio(message_graph, content)
    logger.info(
        "Retornador /comm rebuda PeticioDevolucio %s (comanda %s)",
        request_data.get("return_id", ""),
        request_data.get("order_id", ""),
    )
    decision, _ = pla_compliment_de_devolucio(request_data)
    logger.info(
        "Retornador /comm resposta devolucio %s: %s",
        decision.get("return_id", ""),
        "ACCEPTADA" if decision.get("accepted") else "DENEGADA",
    )
    response = build_resolucio_devolucio(
        decision,
        sender=AGENT.uri,
        receiver=properties.get("sender"),
        request_content=content,
        msgcnt=next_counter(),
    )
    return response.serialize(format="xml")


@app.route("/Stop")
def stop():
    """Atura el servidor Flask de l'agent."""
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    """Punt d'entrada executable de l'agent."""
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS.get("retornador", 9012))
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("RetornadorAgent", "Retornador", args.port, host=hostname),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DIRECTORY_AGENT, DSO.RetornadorAgent, 0),
    )


if __name__ == "__main__":
    main()