"""Logistics center agent that groups products into lots and negotiates transport."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, request
from rdflib import Graph

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, register_agent, send_message
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
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
from protocols.centre_logistic import (
    build_eleccio_transportista,
    build_peticio_transport,
    build_shipping_details_response,
    extract_transport_offer,
    parse_productes_localitzats,
)
from services.logistics_service import choose_best_offer, create_lot
from services.rdf_store import load_graph


app = Flask(__name__)
logger = config_logger(level=1)

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
    logger.info(
        "Assignant comanda %s a lot (ciutat=%s, data_entrega=%s, productes=%d)",
        request_data["order_id"],
        request_data["city"],
        request_data["delivery_date"],
        len(request_data["products"]),
    )
    lot = create_lot(
        LOTS_PATH,
        request_data["order_id"],
        request_data["city"],
        request_data["delivery_date"],
        request_data["products"],
    )
    if lot["created_new_lot"]:
        logger.info(
            "Creat lot nou %s per a la comanda %s (ciutat=%s, data_entrega=%s, pes_total=%.2f)",
            lot["lot_id"],
            request_data["order_id"],
            request_data["city"],
            request_data["delivery_date"],
            lot["total_weight"],
        )
    else:
        logger.info(
            "Reutilitzat lot existent %s per a la comanda %s (coincideix ciutat=%s, data_entrega=%s, pes_total=%.2f)",
            lot["lot_id"],
            request_data["order_id"],
            request_data["city"],
            request_data["delivery_date"],
            lot["total_weight"],
        )
    return lot


def pla_cerca_de_transportista(lot):
    def query_transport(transport_agent):
        message, _ = build_peticio_transport(
            lot,
            sender=AGENT.uri,
            receiver=transport_agent.uri,
            msgcnt=next_counter(),
        )
        return extract_transport_offer(MESSAGE_SENDER(message, transport_agent.address))

    with ThreadPoolExecutor(max_workers=len(TRANSPORT_AGENTS)) as executor:
        futures = [executor.submit(query_transport, agent) for agent in TRANSPORT_AGENTS]
        offers = [future.result() for future in futures]
        logger.info("Rebudes %d ofertes de transport per al lot %s", len(offers), lot["lot_id"])
        return offers


def pla_de_transportista_escollit(lot, offers, receiver, request_content=None):
    selected = choose_best_offer(offers)
    selected_transport = next(
        agent
        for agent in TRANSPORT_AGENTS
        if agent.name.endswith(selected["transport_id"]) or selected["transport_id"] in agent.name.lower()
    )
    selection_message = build_eleccio_transportista(
        lot,
        selected,
        sender=AGENT.uri,
        receiver=selected_transport.uri,
        request_content=request_content,
        msgcnt=next_counter(),
    )
    MESSAGE_SENDER(selection_message, selected_transport.address)
    return build_shipping_details_response(
        lot["order_id"],
        lot["city"],
        selected,
        sender=AGENT.uri,
        receiver=receiver,
        request_content=request_content,
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
        logger.warning("Rebut missatge no-request o malformat a /comm")
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
    response = pla_de_transportista_escollit(lot, offers, properties.get("sender"), request_content=content)
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
    logger.info("Registrant %s al directori %s", AGENT.name, directory.address)
    register_with_directory(AGENT, directory, DSO.CentreLogisticAgent, 0)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
