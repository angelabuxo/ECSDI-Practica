"""Agent proveïdor de pagament (banc extern): confirma o rebutja operacions de pagament."""

import argparse
from datetime import date

from flask import Flask, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from config import (
    DEFAULT_PORTS,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_runtime_hostname,
    serve_agent,
)
from protocols.pagament import build_confirmacio_pagament, parse_peticio_pagament


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
BANK_ID = "bank-main"
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings):
    global AGENT, BANK_ID, COUNTER
    AGENT = settings["agent"]
    BANK_ID = settings["bank_id"]
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def processar_pagament(request_data):
    logger.info(
        "Banc %s processant pagament %s de la comanda %s (%.2f EUR, metode=%s)",
        BANK_ID,
        request_data["payment_id"],
        request_data["order_id"],
        request_data["amount"],
        request_data["method"],
    )
    return {
        "payment_id": request_data["payment_id"],
        "order_id": request_data["order_id"],
        "amount": request_data["amount"],
        "method": request_data["method"],
        "sentit": request_data.get("sentit"),
        "status": "PAGAT",
        "date": date.today().isoformat(),
        "product_ids": request_data.get("product_ids", []),
    }


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties or properties.get("performative") != ACL.request:
        logger.warning("ProveidorPagament ha rebut un missatge no-request o malformat a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    content = properties["content"]
    if message_graph.value(content, RDF.type) != AZON.PeticioPagament:
        logger.warning("ProveidorPagament ha rebut una accio no suportada a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            msgcnt=next_counter(),
        ).serialize(format="xml")
    request_data = parse_peticio_pagament(message_graph, content)
    payment = processar_pagament(request_data)
    response = build_confirmacio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=properties.get("sender"),
        request_content=content,
        msgcnt=next_counter(),
    )
    return response.serialize(format="xml")


@app.route("/iface")
def iface():
    graph = Graph()
    bind_namespaces(graph)
    return graph.serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["proveidor_pagament"])
    add_directory_arguments(parser)
    parser.add_argument("--bank-id", default="bank-main")
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("ProveidorPagamentAgent", "ProveidorPagament", args.port, host=hostname),
            "bank_id": args.bank_id,
        }
    )
    directory = build_directory_agent(args.directory_host, args.directory_port)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, directory, DSO.ProveidorPagamentAgent, 0),
    )


if __name__ == "__main__":
    main()
