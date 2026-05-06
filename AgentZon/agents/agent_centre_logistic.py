"""Logistics center agent that groups products into lots and negotiates transport."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, request
from rdflib import Graph

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties, register_agent, send_message
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
from AgentZon.protocols.centre_logistic import (
    build_peticio_transport,
    build_shipping_details_response,
    extract_transport_offer,
    parse_productes_localitzats,
)
from AgentZon.services.logistics_service import choose_best_offer, create_lot
from AgentZon.services.rdf_store import load_graph


app = Flask(__name__)

# Agent attributes -----------------------------------------------------------------
AGENT = None
MESSAGE_SENDER = send_message
TRANSPORT_AGENTS = []
LOTS_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    global AGENT, MESSAGE_SENDER, TRANSPORT_AGENTS, LOTS_PATH, COUNTER
    AGENT = settings["agent"]
    MESSAGE_SENDER = message_sender
    TRANSPORT_AGENTS = settings["transport_agents"]
    LOTS_PATH = Path(settings["data_dir"]) / "lots.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def pla_assignar_producte_a_lot(request_data):
    return create_lot(
        LOTS_PATH,
        request_data["order_id"],
        request_data["city"],
        request_data["priority"],
        request_data["products"],
    )


def pla_cerca_de_transportista(lot):
    def query_transport(transport_agent):
        message, _ = build_peticio_transport(
            lot["lot_id"],
            lot["order_id"],
            lot["city"],
            lot["priority"],
            lot["total_weight"],
            sender=AGENT.uri,
            receiver=transport_agent.uri,
            msgcnt=next_counter(),
        )
        return extract_transport_offer(MESSAGE_SENDER(message, transport_agent.address))

    with ThreadPoolExecutor(max_workers=len(TRANSPORT_AGENTS)) as executor:
        futures = [executor.submit(query_transport, agent) for agent in TRANSPORT_AGENTS]
        return [future.result() for future in futures]


def pla_de_transportista_escollit(lot, offers, receiver):
    selected = choose_best_offer(offers)
    return build_shipping_details_response(
        lot["order_id"],
        lot["city"],
        selected,
        sender=AGENT.uri,
        receiver=receiver,
        msgcnt=next_counter(),
    )


def pla_producte_sha_enviat():
    return None


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
    request_data = parse_productes_localitzats(message_graph, content)
    lot = pla_assignar_producte_a_lot(request_data)
    offers = pla_cerca_de_transportista(lot)
    response = pla_de_transportista_escollit(lot, offers, properties.get("sender"))
    return response.serialize(format="xml")


@app.route("/info")
def info():
    return load_graph(LOTS_PATH).serialize(format="turtle")


@app.route("/stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["centre_logistic"])
    add_directory_arguments(parser)
    parser.add_argument("--transport-fast-host", default="127.0.0.1")
    parser.add_argument("--transport-fast-port", type=int, default=DEFAULT_PORTS["transport_fast"])
    parser.add_argument("--transport-economy-host", default="127.0.0.1")
    parser.add_argument("--transport-economy-port", type=int, default=DEFAULT_PORTS["transport_economy"])
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("CentreLogisticAgent", "CentreLogistic", args.port, host=hostname),
            "data_dir": Path(args.data_dir),
            "transport_agents": [
                build_agent(
                    "Transportista-fast",
                    "TransportFast",
                    args.transport_fast_port,
                    host=args.transport_fast_host,
                ),
                build_agent(
                    "Transportista-economy",
                    "TransportEconomy",
                    args.transport_economy_port,
                    host=args.transport_economy_host,
                ),
            ],
        }
    )
    directory = build_directory_agent(args.directory_host, args.directory_port)
    register_with_directory(AGENT, directory, DSO.CentreLogisticAgent, 0)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
