"""Agent transportista extern: ofertes de transport per lots (preu i data d'entrega)."""

import argparse
from datetime import date, timedelta

from flask import Flask, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from config import (
    DEFAULT_PORTS,
    add_runtime_arguments,
    build_agent,
    resolve_runtime_hostname,
    serve_agent,
)
from protocols.centre_logistic import build_resposta_oferta_transport, parse_peticio_transport


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
TRANSPORT_ID = "fast"
PRICE_PER_KG = 8.0
DELIVERY_DAYS = 1
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings):
    global AGENT, TRANSPORT_ID, PRICE_PER_KG, DELIVERY_DAYS, COUNTER
    AGENT = settings["agent"]
    TRANSPORT_ID = settings["transport_id"]
    PRICE_PER_KG = settings["price_per_kg"]
    DELIVERY_DAYS = settings["delivery_days"]
    COUNTER = 0


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
    action = message_graph.value(content, RDF.type)
    if action is None:
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    if action == AZON.EleccioTransportista:
        return build_message(
            Graph(),
            ACL.inform,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            msgcnt=next_counter(),
        ).serialize(format="xml")
    request_data = parse_peticio_transport(message_graph, content)
    offer = generar_oferta_transport(request_data)
    logger.info(
        "Generada oferta de transport %s per a la comanda %s (%.2f EUR)",
        TRANSPORT_ID,
        offer["order_id"],
        offer["price"],
    )
    response = build_resposta_oferta_transport(
        offer,
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
    add_runtime_arguments(parser, DEFAULT_PORTS["transport_fast"])
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
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(app, hostname, args.port)


if __name__ == "__main__":
    main()
