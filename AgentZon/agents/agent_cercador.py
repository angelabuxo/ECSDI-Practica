"""Search agent exposing ACL search on /comm and a thin browser wrapper on /iface."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, render_template, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, register_agent, send_message
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI
from config import (
    DEFAULT_PORTS,
    TEMPLATE_DIR,
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_runtime_hostname,
)
from protocols.cerca import build_peticio_cerca, build_resultat_cerca, parse_peticio_cerca
from protocols.directory import build_search_message, parse_directory_response
from services.catalog_service import search_products
from services.history_service import record_search


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
SEARCH_HISTORY_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH, SEARCH_HISTORY_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    SEARCH_HISTORY_PATH = data_dir / "historial_cerques.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def default_criteria():
    return {"text": "", "category": "", "brand": "", "min_price": None, "max_price": None}


def resolve_compra_agent():
    message = build_search_message(AGENT, DSO.CompraAgent, DIRECTORY_AGENT, msgcnt=next_counter())
    response = MESSAGE_SENDER(message, DIRECTORY_AGENT.address)
    return parse_directory_response(response)


def pla_de_cerca(criteria):
    logger.info("Executant cerca amb criteris: %s", criteria)
    products = search_products(CATALOG_PATH, criteria)
    record_search(SEARCH_HISTORY_PATH, criteria, products)
    logger.info("La cerca ha retornat %d productes", len(products))
    return products


def pla_de_presentacio(criteria, products):
    compra_agent = resolve_compra_agent()
    compra_url = replace_path(compra_agent.address, "/iface")
    return render_template("cercador.html", criteria=criteria, products=products, compra_url=compra_url, search_path="/iface")


def replace_path(address, new_path):
    parsed = urlsplit(address)
    return urlunsplit((parsed.scheme, parsed.netloc, new_path, "", ""))


# Web interface --------------------------------------------------------------------
@app.route("/iface", methods=["GET", "POST"])
def iface():
    if request.method == "GET":
        return render_template("cercador.html", criteria=default_criteria(), products=[], compra_url="", search_path="/iface")
    request_graph, content = build_peticio_cerca(
        f"iface-search-{next_counter()}",
        text=request.form.get("text", ""),
        category=request.form.get("category", ""),
        brand=request.form.get("brand", ""),
        min_price=float(request.form["min_price"]) if request.form.get("min_price") else None,
        max_price=float(request.form["max_price"]) if request.form.get("max_price") else None,
    )
    criteria = parse_peticio_cerca(request_graph, content)
    products = pla_de_cerca(criteria)
    return pla_de_presentacio(criteria, products)


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
    if message_graph.value(content, RDF.type) != AZON.PeticioCerca:
        logger.warning("Rebut accio no suportada a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    criteria = parse_peticio_cerca(message_graph, content)
    logger.info("Rebuda peticio ACL de cerca")
    products = pla_de_cerca(criteria)
    response_graph, response_content = build_resultat_cerca(
        f"result-{next_counter()}",
        products,
        request_content=content,
    )
    response = build_message(
        response_graph,
        ACL.inform,
        sender=AGENT.uri,
        receiver=properties.get("sender"),
        content=response_content,
        ontology=ONTOLOGY_URI,
        msgcnt=next_counter(),
    )
    return response.serialize(format="xml")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["cercador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("CercadorAgent", "Cercador", args.port, host=hostname),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Registrant %s al directori %s", AGENT.name, DIRECTORY_AGENT.address)
    register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CercadorAgent, 0)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
