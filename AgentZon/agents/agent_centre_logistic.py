"""Logistics center agent that groups products into lots and negotiates transport."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, request
from rdflib import Graph

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
from protocols.centre_logistic import (
    build_eleccio_transportista,
    build_peticio_transport,
    build_shipping_details_response,
    extract_transport_offer,
    parse_productes_localitzats,
)
from protocols.directory import build_search_message, parse_directory_response
from protocols.pagament import build_peticio_cobrament_intern, extract_confirmacio_pagament
from services.logistics_service import choose_best_offer, create_lot
from services.rdf_store import load_graph


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
TRANSPORT_AGENTS = []
LOTS_PATH = None
CENTRE_ID = None
CENTRE_CITY = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, TRANSPORT_AGENTS, LOTS_PATH, CENTRE_ID, CENTRE_CITY, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    TRANSPORT_AGENTS = settings["transport_agents"]
    CENTRE_ID = settings.get("centre_id")
    CENTRE_CITY = settings.get("centre_city")
    lots_filename = f"lots-{CENTRE_ID}.ttl" if CENTRE_ID else "lots.ttl"
    LOTS_PATH = Path(settings["data_dir"]) / lots_filename
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def build_centre_uri_name(centre_id):
    return f"CentreLogistic{''.join(ch for ch in centre_id if ch.isalnum())}"


def pla_assignar_producte_a_lot(request_data):
    logger.info(
        "Assignant comanda %s a lot al centre %s (desti=%s, data_entrega=%s, productes=%d)",
        request_data["order_id"],
        request_data.get("centre_id") or CENTRE_ID,
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
        centre_id=request_data.get("centre_id") or CENTRE_ID,
        centre_city=request_data.get("centre_city") or CENTRE_CITY,
    )
    if lot["created_new_lot"]:
        logger.info(
            "Creat lot nou %s per a la comanda %s al centre %s (desti=%s, data_entrega=%s, pes_total=%.2f)",
            lot["lot_id"],
            request_data["order_id"],
            lot.get("centre_id") or CENTRE_ID,
            request_data["city"],
            request_data["delivery_date"],
            lot["total_weight"],
        )
    else:
        logger.info(
            "Reutilitzat lot existent %s per a la comanda %s al centre %s (coincideix desti=%s, data_entrega=%s, pes_total=%.2f)",
            lot["lot_id"],
            request_data["order_id"],
            lot.get("centre_id") or CENTRE_ID,
            request_data["city"],
            request_data["delivery_date"],
            lot["total_weight"],
        )
    return lot


def pla_cerca_de_transportista(lot):
    def query_transport(transport_agent):
        try:
            message, _ = build_peticio_transport(
                lot,
                sender=AGENT.uri,
                receiver=transport_agent.uri,
                msgcnt=next_counter(),
            )
            return extract_transport_offer(MESSAGE_SENDER(message, transport_agent.address))
        except Exception as exc:
            logger.warning(
                "No s'ha pogut obtenir oferta de %s (%s): %s",
                transport_agent.name,
                transport_agent.address,
                exc,
            )
            return None

    with ThreadPoolExecutor(max_workers=len(TRANSPORT_AGENTS)) as executor:
        futures = [executor.submit(query_transport, agent) for agent in TRANSPORT_AGENTS]
        offers = [offer for future in futures if (offer := future.result()) is not None]
    if not offers:
        raise RuntimeError("Cap transportista disponible per al lot {}".format(lot["lot_id"]))
    logger.info("Rebudes %d ofertes de transport per al lot %s", len(offers), lot["lot_id"])
    return offers


def pla_de_transportista_escollit(lot, offers, request_content=None):
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
    return selected


def resolve_agent(agent_type):
    message = build_search_message(AGENT, agent_type, DIRECTORY_AGENT, msgcnt=next_counter())
    response = MESSAGE_SENDER(message, DIRECTORY_AGENT.address)
    return parse_directory_response(response)


def pla_producte_sha_enviat(request_data, selected):
    if DIRECTORY_AGENT is None:
        return None
    try:
        cobrador = resolve_agent(DSO.CobradorAgent)
    except Exception:
        logger.warning("No s'ha pogut resoldre el Cobrador; s'omet el cobrament intern")
        return None
    shipment = {
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "city": request_data["city"],
        "delivery_date": selected["delivery_date"],
        "transport_cost": selected["price"],
        "product_ids": [product["product_id"] for product in request_data["products"]],
    }
    logger.info(
        "Productes de la comanda %s enviats; notificant el Cobrador perque cobri",
        shipment["order_id"],
    )
    message = build_peticio_cobrament_intern(
        shipment,
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=next_counter(),
    )
    try:
        confirmation = extract_confirmacio_pagament(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        logger.warning("El cobrament intern de la comanda %s no s'ha pogut completar", shipment["order_id"])
        return None
    if not confirmation.get("payment_id"):
        logger.warning("El Cobrador no ha retornat una factura per a la comanda %s", shipment["order_id"])
        return None
    logger.info(
        "Cobrament intern confirmat per la comanda %s (pagament %s, %.2f EUR)",
        shipment["order_id"],
        confirmation["payment_id"],
        confirmation["amount"],
    )
    return confirmation


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
    try:
        lot = pla_assignar_producte_a_lot(request_data)
        offers = pla_cerca_de_transportista(lot)
        selected = pla_de_transportista_escollit(lot, offers, request_content=content)
        invoice = pla_producte_sha_enviat(request_data, selected)
        response = build_shipping_details_response(
            request_data,
            selected,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            request_content=content,
            invoice=invoice,
            msgcnt=next_counter(),
        )
        return response.serialize(format="xml")
    except Exception as exc:
        logger.error("Error processant la comanda %s: %s", request_data.get("order_id"), exc)
        return build_message(
            Graph(),
            ACL.failure,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            msgcnt=next_counter(),
        ).serialize(format="xml")


@app.route("/iface")
def iface():
    return load_graph(LOTS_PATH).serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["centre_logistic"])
    add_directory_arguments(parser)
    parser.add_argument("--centre-id", default="CL-BCN")
    parser.add_argument("--centre-city", default="Barcelona")
    parser.add_argument("--transport-fast-host", default="127.0.0.1")
    parser.add_argument("--transport-fast-port", type=int, default=DEFAULT_PORTS["transport_fast"])
    parser.add_argument("--transport-economy-host", default="127.0.0.1")
    parser.add_argument("--transport-economy-port", type=int, default=DEFAULT_PORTS["transport_economy"])
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent(
                f"CentreLogisticAgent-{args.centre_id}",
                build_centre_uri_name(args.centre_id),
                args.port,
                host=hostname,
            ),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
            "centre_id": args.centre_id,
            "centre_city": args.centre_city,
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
    register_with_directory(
        AGENT,
        directory,
        DSO.CentreLogisticAgent,
        0,
        metadata={
            AZON.IdCentreLogistic: args.centre_id,
            AZON.Ciutat: args.centre_city,
        },
    )
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
