# -*- coding: utf-8 -*-
"""
filename: agent_cobrador

Agent cobrador AgentZon (pagaments, dades bancaries i devolucions).

/comm entrada ACL
/iface mostra pagaments en turtle
/Stop para l'agent
"""

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
    resolve_agent_hosts,
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
    save_seller_bank_data,
    save_user_bank_data,
)
from services.rdf_store import load_graph


logger = config_logger(level=1)
app = Flask(__name__)

OK_PAYMENT_STATUS = "PAGAT"
OK_REFUND_STATUS = "RETORNAT"
mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
USER_BANK_PATH = None
SELLER_BANK_PATH = None
PAYMENTS_PATH = None


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, CATALOG_PATH
    global USER_BANK_PATH, SELLER_BANK_PATH, PAYMENTS_PATH, mss_cnt
    AGENT = settings["agent"]
    DirectoryAgent = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    USER_BANK_PATH = data_dir / "dades_bancaries_usuari.ttl"
    SELLER_BANK_PATH = data_dir / "dades_bancaries_venedors_externs.ttl"
    PAYMENTS_PATH = data_dir / "pagaments.ttl"
    mss_cnt = 0


def _payment_date():
    return date.today().isoformat()


def calcular_import(product_ids):
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    return round(sum(product.get("price", 0.0) for product in products), 2)


def _confirm_payment(payment, sender, request_content):
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
        msgcnt=mss_cnt,
    )


def pla_registrar_dades_usuari(gm, content, sender):
    request_data = parse_peticio_registre_dades_usuari(gm, content)
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
        msgcnt=mss_cnt,
    )


def pla_registrar_dades_venedor(gm, content, sender):
    request_data = parse_peticio_registre_dades_venedor(gm, content)
    logger.info("Registrant dades bancaries del venedor extern %s", request_data["seller_id"])
    save_seller_bank_data(
        SELLER_BANK_PATH,
        request_data["seller_id"],
        request_data["bank_data"],
        request_data.get("seller_name") or None,
    )
    return build_confirmacio_registre_dades(
        request_data["seller_id"],
        is_external=True,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def pla_cobrament_intern(gm, content, sender):
    shipment = parse_peticio_cobrament_intern(gm, content)
    product = shipment.get("product") or {}
    product_id = product.get("product_id")
    product_ids = [product_id] if product_id else []
    logger.info(
        "Processant cobrament intern comanda %s lot %s ploc %s (%d producte(s))",
        shipment.get("order_id"),
        shipment["lot_id"],
        shipment.get("localized_product_id"),
        len(product_ids),
    )
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    products_subtotal = calcular_import(product_ids)
    amount = round(products_subtotal + shipment["transport_cost"], 2)
    payment = {
        "payment_id": f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": shipment.get("order_id") or shipment.get("localized_product_id") or shipment["lot_id"],
        "amount": amount,
        "method": "targeta",
        "sentit": SENTIT_COBRAMENT,
        "user_id": shipment["user_id"],
        "product_ids": product_ids,
        "products": products,
        "transport_cost": shipment["transport_cost"],
        "products_subtotal": products_subtotal,
        "status": OK_PAYMENT_STATUS,
        "date": _payment_date(),
    }
    return _confirm_payment(payment, sender, content)


def pla_cobrament_extern(gm, content, sender):
    request_data = parse_peticio_pagament(gm, content)
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


def pla_retornar_diners(gm, content, sender):
    request_data = parse_peticio_retorn_diners(gm, content)
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
        msgcnt=mss_cnt,
    )


PLANS = {
    AZON.PeticioRegistreDadesBancariesUsuari: pla_registrar_dades_usuari,
    AZON.PeticioRegistreDadesBancariesVenedor: pla_registrar_dades_venedor,
    AZON.ConfirmacioEnviament: pla_cobrament_intern,
    AZON.PeticioPagament: pla_cobrament_extern,
    AZON.PeticioRetornDiners: pla_retornar_diners,
}


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio de l'agent cobrador.
    """
    global mss_cnt

    print("INFO AgenteCobrador => Peticio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")
    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO AgenteCobrador => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        if perf != ACL.request:
            gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
            print("INFO AgenteCobrador => No es una request FIPA ACL")
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
                print("INFO AgenteCobrador => Accio no suportada: %s" % accion)
            else:
                gr = plan(gm, content, msgdic.get("sender"))

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/iface")
def browser_iface():
    return load_graph(PAYMENTS_PATH).serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["cobrador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent("CobradorAgent", "Cobrador", args.port, host=publish_host),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DirectoryAgent, DSO.CobradorAgent, 0),
    )
