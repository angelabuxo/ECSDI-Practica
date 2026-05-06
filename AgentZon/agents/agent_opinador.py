"""Opinion agent that records completed purchases into persistent history."""

import argparse
from pathlib import Path

from flask import Flask, request
from rdflib import Graph

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.config import (
    DEFAULT_PORTS,
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_runtime_hostname,
)
from AgentZon.protocols.compra import (
    build_confirmacio_registre_compra,
    parse_peticio_registre_compra,
)
from AgentZon.services.history_service import record_purchase
from AgentZon.services.rdf_store import load_graph


app = Flask(__name__)

# Agent attributes -----------------------------------------------------------------
AGENT = None
HISTORY_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings):
    global AGENT, HISTORY_PATH, COUNTER
    AGENT = settings["agent"]
    HISTORY_PATH = Path(settings["data_dir"]) / "historial_compres.ttl"
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
    }
    record_purchase(HISTORY_PATH, order)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties or properties.get("performative") != ACL.request:
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    content = properties["content"]
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


@app.route("/info")
def info():
    return load_graph(HISTORY_PATH).serialize(format="turtle")


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
    register_with_directory(AGENT, directory, DSO.OpinadorAgent, 0)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
