"""Agent cobrador: cobraments, transferències a venedors i devolucions."""

import argparse
from pathlib import Path
from uuid import uuid4

from flask import Flask, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
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
from protocols.directory import build_search_message, parse_directory_response
from protocols.pagament import (
    build_confirmacio_pagament,
    build_confirmacio_registre_dades,
    build_confirmacio_retorn_diners,
    build_peticio_pagament,
    extract_confirmacio_pagament,
    parse_peticio_cobrament_intern,
    parse_peticio_pagament,
    parse_peticio_registre_dades_usuari,
    parse_peticio_registre_dades_venedor,
    parse_peticio_retorn_diners,
)
from services.catalog_service import get_products_by_ids
from services.payment_service import (
    read_seller_bank_data,
    read_user_bank_data,
    record_payment,
    record_refund,
    save_seller_bank_data,
    save_user_bank_data,
)
from services.rdf_store import load_graph


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
USER_BANK_PATH = None
SELLER_BANK_PATH = None
PAYMENTS_PATH = None
REFUNDS_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH
    global USER_BANK_PATH, SELLER_BANK_PATH, PAYMENTS_PATH, REFUNDS_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    USER_BANK_PATH = data_dir / "dades_bancaries_usuari.ttl"
    SELLER_BANK_PATH = data_dir / "dades_bancaries_venedors_externs.ttl"
    PAYMENTS_PATH = data_dir / "pagaments.ttl"
    REFUNDS_PATH = data_dir / "devolucions.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def resolve_agent(agent_type):
    message = build_search_message(AGENT, agent_type, DIRECTORY_AGENT, msgcnt=next_counter())
    response = MESSAGE_SENDER(message, DIRECTORY_AGENT.address)
    return parse_directory_response(response)


def calcular_import(product_ids):
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    return round(sum(product.get("price", 0.0) for product in products), 2)


def pagar_via_proveidor(payment):
    proveidor = resolve_agent(DSO.ProveidorPagamentAgent)
    logger.info(
        "Enviant l'accio de cobrar %s (%.2f EUR) al proveidor de pagament %s",
        payment["payment_id"],
        payment["amount"],
        proveidor.name,
    )
    message = build_peticio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=proveidor.uri,
        msgcnt=next_counter(),
    )
    return extract_confirmacio_pagament(MESSAGE_SENDER(message, proveidor.address))


# Capacitat: Guardar dades bancaries -----------------------------------------------
def pla_registrar_dades_usuari(message_graph, content, sender):
    request_data = parse_peticio_registre_dades_usuari(message_graph, content)
    logger.info("Registrant dades bancaries de l'usuari %s", request_data["user_id"])
    save_user_bank_data(
        USER_BANK_PATH,
        request_data["user_id"],
        request_data["bank_data"],
        request_data["payment_method"],
    )
    return build_confirmacio_registre_dades(
        request_data["user_id"],
        is_external=False,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=next_counter(),
    )


def pla_registrar_dades_venedor(message_graph, content, sender):
    request_data = parse_peticio_registre_dades_venedor(message_graph, content)
    logger.info("Registrant dades bancaries del venedor extern %s", request_data["seller_id"])
    save_seller_bank_data(SELLER_BANK_PATH, request_data["seller_id"], request_data["bank_data"])
    return build_confirmacio_registre_dades(
        request_data["seller_id"],
        is_external=True,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=next_counter(),
    )


# Capacitat: Cobrar compra ---------------------------------------------------------
def pla_cobrament_intern(message_graph, content, sender):
    shipment = parse_peticio_cobrament_intern(message_graph, content)
    bank = read_user_bank_data(USER_BANK_PATH, shipment["user_id"])
    payment_method = bank["payment_method"] if bank and bank["payment_method"] else "targeta"
    products = get_products_by_ids(CATALOG_PATH, shipment["product_ids"])
    products_subtotal = calcular_import(shipment["product_ids"])
    amount = round(products_subtotal + shipment["transport_cost"], 2)
    payment = {
        "payment_id": f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": shipment["order_id"],
        "amount": amount,
        "method": payment_method,
        "user_id": shipment["user_id"],
        "product_ids": shipment["product_ids"],
        "products": products,
        "transport_cost": shipment["transport_cost"],
        "products_subtotal": products_subtotal,
    }
    logger.info(
        "Cobrament intern de la comanda %s a l'usuari %s (%.2f EUR)",
        payment["order_id"],
        payment["user_id"],
        payment["amount"],
    )
    confirmation = pagar_via_proveidor(payment)
    payment["status"] = confirmation["status"]
    payment["date"] = confirmation["date"]
    record_payment(PAYMENTS_PATH, payment)
    logger.info(
        "Factura emesa a l'usuari %s per la comanda %s (pagament %s, %.2f EUR)",
        payment["user_id"],
        payment["order_id"],
        payment["payment_id"],
        payment["amount"],
    )
    return build_confirmacio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=next_counter(),
    )


def pla_cobrament_extern(message_graph, content, sender):
    request_data = parse_peticio_pagament(message_graph, content)
    payment = {
        "payment_id": request_data["payment_id"] or f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": request_data["order_id"],
        "amount": request_data["amount"],
        "method": request_data["method"] or "transferencia",
        "user_id": request_data.get("user_id"),
        "seller_id": request_data.get("seller_id"),
        "product_ids": request_data.get("product_ids", []),
    }
    logger.info(
        "Cobrament extern de la comanda %s, transferint %.2f EUR al venedor %s",
        payment["order_id"],
        payment["amount"],
        payment["seller_id"],
    )
    confirmation = pagar_via_proveidor(payment)
    payment["status"] = confirmation["status"]
    payment["date"] = confirmation["date"]
    record_payment(PAYMENTS_PATH, payment)
    return build_confirmacio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=next_counter(),
    )


# Capacitat: Gestionar Devolucions -------------------------------------------------
def pla_retornar_diners(message_graph, content, sender):
    request_data = parse_peticio_retorn_diners(message_graph, content)
    is_external = bool(request_data.get("seller_id"))
    if is_external:
        bank = read_seller_bank_data(SELLER_BANK_PATH, request_data["seller_id"])
        logger.info(
            "Devolucio %s d'un producte extern: llegint dades del venedor %s",
            request_data["return_id"],
            request_data["seller_id"],
        )
    else:
        bank = read_user_bank_data(USER_BANK_PATH, request_data["user_id"])
        logger.info(
            "Devolucio %s: llegint dades bancaries de l'usuari %s",
            request_data["return_id"],
            request_data["user_id"],
        )
    if bank is None:
        logger.warning("No s'han trobat dades bancaries per a la devolucio %s", request_data["return_id"])
    payment = {
        "payment_id": f"REFUND-{request_data['return_id']}",
        "order_id": request_data["order_id"],
        "amount": request_data["amount"],
        "method": "transferencia",
        "user_id": request_data["user_id"],
        "seller_id": request_data.get("seller_id"),
        "product_ids": request_data.get("product_ids", []),
    }
    pagar_via_proveidor(payment)
    refund = {
        "return_id": request_data["return_id"],
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "amount": request_data["amount"],
        "reason": request_data.get("reason", ""),
        "seller_id": request_data.get("seller_id"),
        "product_ids": request_data.get("product_ids", []),
        "status": "RETORNAT",
    }
    record_refund(REFUNDS_PATH, refund)
    logger.info("Devolucio %s completada (%.2f EUR retornats)", refund["return_id"], refund["amount"])
    return build_confirmacio_retorn_diners(
        refund,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=next_counter(),
    )


# Communication handling -----------------------------------------------------------
PLANS = {
    AZON.PeticioRegistreDadesBancariesUsuari: pla_registrar_dades_usuari,
    AZON.PeticioRegistreDadesBancariesVenedor: pla_registrar_dades_venedor,
    AZON.ConfirmacioEnviament: pla_cobrament_intern,
    AZON.PeticioPagament: pla_cobrament_extern,
    AZON.PeticioRetornDiners: pla_retornar_diners,
}


@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties or properties.get("performative") != ACL.request:
        logger.warning("CobradorAgent ha rebut un missatge no-request o malformat a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    content = properties["content"]
    action = message_graph.value(content, RDF.type)
    plan = PLANS.get(action)
    if plan is None:
        logger.warning("CobradorAgent ha rebut una accio no suportada a /comm: %s", action)
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            msgcnt=next_counter(),
        ).serialize(format="xml")
    response = plan(message_graph, content, properties.get("sender"))
    return response.serialize(format="xml")


@app.route("/iface")
def iface():
    return load_graph(PAYMENTS_PATH).serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["cobrador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("CobradorAgent", "Cobrador", args.port, host=hostname),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Registrant %s al directori %s", AGENT.name, DIRECTORY_AGENT.address)
    register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CobradorAgent, 0)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
