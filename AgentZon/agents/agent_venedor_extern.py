"""External-seller agent that coordinates product registration across agents."""

import argparse
from pathlib import Path

from flask import Flask, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.DSO import DSO
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
from protocols.directory import build_search_message, parse_directory_response
from protocols.venedor_extern import (
    build_alta_producte_extern,
    build_confirmacio_alta_producte_extern,
    parse_alta_producte_extern,
)
from services.external_product_service import save_product_location, save_shipping_responsibility, save_vendor_bank_data


app = Flask(__name__)
logger = config_logger(level=1)

AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
AGENT_RESOLVER = None
RESPONSIBILITY_PATH = None
LOCATION_PATH = None
BANK_PATH = None
COUNTER = 0


def configure_runtime(settings, message_sender=send_message, agent_resolver=None):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, AGENT_RESOLVER, RESPONSIBILITY_PATH, LOCATION_PATH, BANK_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    AGENT_RESOLVER = agent_resolver
    data_dir = Path(settings["data_dir"])
    RESPONSIBILITY_PATH = data_dir / "responsable_enviament_productes.ttl"
    LOCATION_PATH = data_dir / "ubicacions_productes.ttl"
    BANK_PATH = data_dir / "dades_bancaries_venedors_externs.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


def resolve_agent(agent_type):
    if AGENT_RESOLVER is not None:
        return AGENT_RESOLVER(agent_type)
    if DIRECTORY_AGENT is None:
        raise RuntimeError("No directory agent configured")
    message = build_search_message(AGENT, agent_type, DIRECTORY_AGENT, msgcnt=next_counter())
    response = MESSAGE_SENDER(message, DIRECTORY_AGENT.address)
    return parse_directory_response(response)


def pla_afegir_producte_extern_a_bd(request_data):
    logger.info("Registrant producte extern %s a les bases de dades locals", request_data["product_id"])
    save_shipping_responsibility(RESPONSIBILITY_PATH, request_data)
    save_product_location(LOCATION_PATH, request_data)
    save_vendor_bank_data(BANK_PATH, request_data)


def pla_delegar_afegir_info_producte_extern(request_data, request_content):
    cercador_agent = resolve_agent(DSO.CercadorAgent)
    message = build_alta_producte_extern(
        f"search-product-{request_data['product_id']}",
        product_id=request_data["product_id"],
        seller_id=request_data["seller_id"],
        bank_details=request_data["bank_details"],
        name=request_data["name"],
        description=request_data["description"],
        category=request_data["category"],
        brand=request_data["brand"],
        price=request_data["price"],
        weight=request_data["weight"],
        sku_extern=request_data["sku_extern"],
        warehouse_city=request_data["warehouse_city"],
        requires_external_shipping=request_data["requires_external_shipping"],
        data_alta=request_data.get("data_alta"),
        sender=AGENT.uri,
        receiver=cercador_agent.uri,
        msgcnt=next_counter(),
    )
    return MESSAGE_SENDER(message, cercador_agent.address)


def pla_comunicar_nou_producte_afegit(request_data, request_content):
    return build_confirmacio_alta_producte_extern(
        request_data["product_id"],
        request_data["seller_id"],
        sender=AGENT.uri,
        receiver=None,
        request_content=request_content,
        msgcnt=next_counter(),
        data_alta=request_data.get("data_alta"),
    )


def process_external_product_request(request_data, request_content=None):
    pla_afegir_producte_extern_a_bd(request_data)
    product_reply = pla_delegar_afegir_info_producte_extern(request_data, request_content)
    if not product_reply:
        raise RuntimeError("No s'ha pogut completar l'alta del producte extern")
    return pla_comunicar_nou_producte_afegit(request_data, request_content)


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
    if message_graph.value(content, RDF.type) != AZON.AltaProducteExtern:
        logger.warning("Rebut accio no suportada a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    request_data = parse_alta_producte_extern(message_graph, content)
    response = process_external_product_request(request_data, request_content=content)
    response_graph = Graph()
    response_graph += response
    return response_graph.serialize(format="xml")


@app.route("/iface")
def iface():
    return Graph().serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Stopping"


def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["venedor_extern"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("VenedorExternAgent", "VenedorExtern", args.port, host=hostname),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Registrant %s al directori %s", AGENT.name, DIRECTORY_AGENT.address)
    register_with_directory(AGENT, DIRECTORY_AGENT, DSO.VenedorExternAgent, 0)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()