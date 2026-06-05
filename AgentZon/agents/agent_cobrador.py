# -*- coding: utf-8 -*-
"""
filename: agent_cobrador

Agent cobrador AgentZon (calcul d'imports, dades bancaries i devolucions).

/comm entrada ACL
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
    build_confirmacio_pagament,
    build_confirmacio_registre_dades,
    build_resultat_consulta_dades_venedor,
    parse_peticio_cobrament,
    parse_peticio_consulta_dades_venedor,
    parse_peticio_registre_dades_usuari,
    parse_peticio_registre_dades_venedor,
)
from services.payment_service import (
    read_seller_bank_data,
    save_seller_bank_data,
    save_user_bank_data,
)


logger = config_logger(level=1)
app = Flask(__name__)

OK_PAYMENT_STATUS = "PAGAT"
mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
USER_BANK_PATH = None
SELLER_BANK_PATH = None


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER
    global USER_BANK_PATH, SELLER_BANK_PATH, mss_cnt
    AGENT = settings["agent"]
    DirectoryAgent = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    USER_BANK_PATH = data_dir / "dades_bancaries_usuari.ttl"
    SELLER_BANK_PATH = data_dir / "dades_bancaries_venedors_externs.ttl"
    mss_cnt = 0


def _payment_date():
    return date.today().isoformat()


def pla_calcular_import(gm, content, sender):
    charge = parse_peticio_cobrament(gm, content)
    preu_producte = charge["preu_producte"]
    cost_transport = charge["cost_transport"]
    amount = round(preu_producte + cost_transport, 2)
    user_id = charge["user_id"]
    logger.info(
        "Calculant cobrament per a l'usuari %s: %.2f (productes) + %.2f (transport) = %.2f",
        user_id,
        preu_producte,
        cost_transport,
        amount,
    )
    payment = {
        "payment_id": f"PAY-{uuid4().hex[:8].upper()}",
        "amount": amount,
        "method": "targeta",
        "sentit": SENTIT_COBRAMENT,
        "user_id": user_id,
        "transport_cost": cost_transport,
        "products_subtotal": preu_producte,
        "status": OK_PAYMENT_STATUS,
        "date": _payment_date(),
    }
    return build_confirmacio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
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


def pla_consulta_dades_venedor(gm, content, sender):
    seller_id = parse_peticio_consulta_dades_venedor(gm)
    profile = read_seller_bank_data(SELLER_BANK_PATH, seller_id) or {
        "seller_id": seller_id,
        "bank_data": "",
        "seller_name": "",
    }
    return build_resultat_consulta_dades_venedor(
        profile,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


# TODO: implementar devolucio de diners (PeticioRetornDiners)


PLANS = {
    AZON.PeticioCobrament: pla_calcular_import,
    AZON.PeticioRegistreDadesBancariesUsuari: pla_registrar_dades_usuari,
    AZON.PeticioRegistreDadesBancariesVenedor: pla_registrar_dades_venedor,
    AZON.PeticioConsultaDadesBancariesVenedor: pla_consulta_dades_venedor,
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
