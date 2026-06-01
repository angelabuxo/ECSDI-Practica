"""Agent transportista extern: ofertes de transport per lots (preu i data d'entrega)."""

import argparse
from datetime import date, timedelta

from flask import Flask, request
from rdflib import Graph

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
from protocols.centre_logistic import (
    build_resposta_oferta_transport,
    extract_transport_offer,
    parse_peticio_transport,
)


app = Flask(__name__)
logger = config_logger(level=1)
TRANSPORTISTA_AGENT_TYPE = DSO.TransportistaAgent

# Agent attributes -----------------------------------------------------------------
AGENT = None
TRANSPORT_ID = "fast"
PRICE_PER_KG = 8.0
DELIVERY_DAYS = 1
COUNTER = 0
LAST_OFFERS = {}


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings):
    global AGENT, TRANSPORT_ID, PRICE_PER_KG, DELIVERY_DAYS, COUNTER, LAST_OFFERS
    AGENT = settings["agent"]
    TRANSPORT_ID = settings["transport_id"]
    PRICE_PER_KG = settings["price_per_kg"]
    DELIVERY_DAYS = settings["delivery_days"]
    COUNTER = 0
    LAST_OFFERS = {}


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def generar_oferta_transport(request_data):
    return {
        "lot_id": request_data["lot_id"],
        "order_id": request_data["order_id"],
        "transport_id": TRANSPORT_ID,
        "transport_name": AGENT.name,
        "city": request_data["city"],
        "delivery_date": (date.today() + timedelta(days=DELIVERY_DAYS)).isoformat(),
        "price": round(request_data["total_weight"] * PRICE_PER_KG, 2),
    }


def register_transport_agent(directory_agent, msgcnt=0):
    return register_with_directory(
        AGENT,
        directory_agent,
        TRANSPORTISTA_AGENT_TYPE,
        msgcnt=msgcnt,
        metadata={AZON.IdTransportista: TRANSPORT_ID},
    )


def _build_inform_reply(receiver):
    return build_message(
        Graph(),
        ACL.inform,
        sender=AGENT.uri,
        receiver=receiver,
        msgcnt=next_counter(),
    )


def _build_refuse_reply(receiver):
    return build_message(
        Graph(),
        ACL.refuse,
        sender=AGENT.uri,
        receiver=receiver,
        msgcnt=next_counter(),
    )


def respondre_contraoferta(counter_offer, receiver=None):
    previous_offer = LAST_OFFERS.get(counter_offer["lot_id"])
    if previous_offer is None:
        return _build_refuse_reply(receiver)

    initial_price = previous_offer["price"]
    counter_price = counter_offer["price"]
    minimum_price = round(initial_price * 0.85, 2)

    if counter_price >= minimum_price:
        LAST_OFFERS[counter_offer["lot_id"]] = {**previous_offer, "price": counter_price}
        return build_message(
            Graph(),
            ACL.agree,
            sender=AGENT.uri,
            receiver=receiver,
            msgcnt=next_counter(),
        )

    proposed_price = max(round((initial_price + counter_price) / 2, 2), minimum_price)
    if counter_price < proposed_price < initial_price:
        proposed_offer = {**previous_offer, "price": proposed_price}
        LAST_OFFERS[counter_offer["lot_id"]] = proposed_offer
        return build_resposta_oferta_transport(
            proposed_offer,
            sender=AGENT.uri,
            receiver=receiver,
            msgcnt=next_counter(),
        )

    return _build_refuse_reply(receiver)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties:
        logger.warning("Rebut missatge malformat a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    performative = properties.get("performative")
    sender = properties.get("sender")
    if performative == ACL["accept-proposal"]:
        selected_offer = extract_transport_offer(message_graph)
        LAST_OFFERS.pop(selected_offer["lot_id"], None)
        return _build_inform_reply(sender).serialize(format="xml")
    if performative == ACL["reject-proposal"]:
        rejected_offer = extract_transport_offer(message_graph)
        LAST_OFFERS.pop(rejected_offer["lot_id"], None)
        return _build_inform_reply(sender).serialize(format="xml")
    if performative == ACL.propose:
        counter_offer = extract_transport_offer(message_graph)
        return respondre_contraoferta(counter_offer, receiver=sender).serialize(format="xml")
    if performative != ACL.cfp:
        logger.warning("Rebut missatge amb performativa no suportada a /comm: %s", performative)
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            receiver=sender,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    content = properties["content"]
    request_data = parse_peticio_transport(message_graph, content)
    offer = generar_oferta_transport(request_data)
    LAST_OFFERS[offer["lot_id"]] = dict(offer)
    logger.info(
        "Generada oferta de transport %s per a la comanda %s (%.2f EUR)",
        TRANSPORT_ID,
        offer["order_id"],
        offer["price"],
    )
    response = build_resposta_oferta_transport(
        offer,
        sender=AGENT.uri,
        receiver=sender,
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
    add_runtime_arguments(parser, DEFAULT_PORTS["transport_fast"])
    add_directory_arguments(parser)
    parser.add_argument("--transport-id", default="fast")
    parser.add_argument("--price-per-kg", type=float, default=8.0)
    parser.add_argument("--delivery-days", type=int, default=1)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent(
                f"Transportista-{args.transport_id}",
                f"Transport{args.transport_id.title()}",
                args.port,
                host=hostname,
            ),
            "transport_id": args.transport_id,
            "price_per_kg": args.price_per_kg,
            "delivery_days": args.delivery_days,
        }
    )
    directory = build_directory_agent(args.directory_host, args.directory_port)
    logger.info("Registrant %s al directori %s", AGENT.name, directory.address)
    register_transport_agent(directory)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(app, hostname, args.port)


if __name__ == "__main__":
    main()
