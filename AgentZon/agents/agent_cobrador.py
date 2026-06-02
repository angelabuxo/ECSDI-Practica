"""Agent cobrador: accepta peticions de pagament i devolució amb confirmació automàtica."""

import argparse
from datetime import date
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
    serve_agent,
)
from protocols.pagament import (
    SENTIT_COBRAMENT,
    SENTIT_PAGAMENT,
    build_confirmacio_pagament,
    build_confirmacio_registre_dades,
    build_confirmacio_retorn_diners,
    parse_peticio_cobrament_intern,
    parse_peticio_pagament,
    parse_peticio_registre_dades_usuari,
    parse_peticio_registre_dades_venedor,
    parse_peticio_retorn_diners,
)
from services.catalog_service import get_products_by_ids
from services.payment_service import (
    record_payment,
    record_refund,
    save_seller_bank_data,
    save_user_bank_data,
)
from services.rdf_store import load_graph


app = Flask(__name__)
logger = config_logger(level=1)

OK_PAYMENT_STATUS = "PAGAT"
OK_REFUND_STATUS = "RETORNAT"

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
    """Inicialitza rutes de dades i dependències del Cobrador."""
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
    """Retorna un identificador incremental per als missatges ACL."""
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


def _payment_date():
    """Data de confirmació per als missatges de pagament."""
    return date.today().isoformat()


def calcular_import(product_ids):
    """Calcula l'import total dels productes indicats."""
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    return round(sum(product.get("price", 0.0) for product in products), 2)


def _confirm_payment(payment, sender, request_content):
    """Registra el pagament i construeix la confirmació ACL."""
    record_payment(PAYMENTS_PATH, payment)
    logger.info(
        "Pagament acceptat automaticament %s (comanda %s, %.2f EUR)",
        payment["payment_id"],
        payment["order_id"],
        payment["amount"],
    )
    return build_confirmacio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=sender,
        request_content=request_content,
        msgcnt=next_counter(),
    )


# Capacitat: Guardar dades bancaries -----------------------------------------------
def pla_registrar_dades_usuari(message_graph, content, sender):
    """Pla de registre de dades bancàries d'usuari (confirmació automàtica)."""
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
    """Pla de registre de dades bancàries de venedor extern (confirmació automàtica)."""
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
    """Pla de cobrament intern: sempre confirma amb estat PAGAT."""
    shipment = parse_peticio_cobrament_intern(message_graph, content)
    logger.info(
        "Processant cobrament intern comanda %s lot %s (%d producte(s))",
        shipment["order_id"],
        shipment["lot_id"],
        len(shipment["product_ids"]),
    )
    products = get_products_by_ids(CATALOG_PATH, shipment["product_ids"])
    products_subtotal = calcular_import(shipment["product_ids"])
    amount = round(products_subtotal + shipment["transport_cost"], 2)
    payment = {
        "payment_id": f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": shipment["order_id"],
        "amount": amount,
        "method": "targeta",
        "sentit": SENTIT_COBRAMENT,
        "user_id": shipment["user_id"],
        "product_ids": shipment["product_ids"],
        "products": products,
        "transport_cost": shipment["transport_cost"],
        "products_subtotal": products_subtotal,
        "status": OK_PAYMENT_STATUS,
        "date": _payment_date(),
    }
    return _confirm_payment(payment, sender, content)


def pla_cobrament_extern(message_graph, content, sender):
    """Pla de cobrament/transferència externa: sempre confirma amb estat PAGAT."""
    request_data = parse_peticio_pagament(message_graph, content)
    payment = {
        "payment_id": request_data["payment_id"] or f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": request_data["order_id"],
        "amount": request_data["amount"],
        "method": request_data["method"] or "transferencia",
        "sentit": request_data.get("sentit") or SENTIT_PAGAMENT,
        "user_id": request_data.get("user_id"),
        "seller_id": request_data.get("seller_id"),
        "product_ids": request_data.get("product_ids", []),
        "status": OK_PAYMENT_STATUS,
        "date": _payment_date(),
    }
    logger.info(
        "Cobrament extern acceptat automaticament (comanda %s, %.2f EUR)",
        payment["order_id"],
        payment["amount"],
    )
    return _confirm_payment(payment, sender, content)


# Capacitat: Gestionar Devolucions -------------------------------------------------
def pla_retornar_diners(message_graph, content, sender):
    """Pla de reemborsament: sempre confirma amb estat RETORNAT."""
    request_data = parse_peticio_retorn_diners(message_graph, content)
    refund = {
        "return_id": request_data["return_id"],
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "amount": request_data["amount"],
        "reason": request_data.get("reason", ""),
        "seller_id": request_data.get("seller_id"),
        "product_ids": request_data.get("product_ids", []),
        "status": OK_REFUND_STATUS,
    }
    record_refund(REFUNDS_PATH, refund)
    logger.info(
        "Devolucio acceptada automaticament %s (%.2f EUR)",
        refund["return_id"],
        refund["amount"],
    )
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
    """Entrada ACL del Cobrador: dispatch de plans per tipus d'acció."""
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
    logger.info("Cobrador /comm rep peticio %s des de %s", action, properties.get("sender"))
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
    """Vista tècnica del Cobrador: estat de pagaments en Turtle."""
    return load_graph(PAYMENTS_PATH).serialize(format="turtle")


@app.route("/Stop")
def stop():
    """Atura el servidor Flask de l'agent."""
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    """Punt d'entrada executable de l'Agent Cobrador."""
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
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CobradorAgent, 0),
    )


if __name__ == "__main__":
    main()
