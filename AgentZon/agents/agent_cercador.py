"""Search agent responsible for product queries and search-history recording."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, render_template, request
from rdflib import Graph

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties, register_agent, send_message
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.AgentUtil.OntoNamespaces import AZON_ONTOLOGY
from AgentZon.config import (
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
from AgentZon.protocols.cerca import build_peticio_cerca, build_resultat_cerca, parse_peticio_cerca
from AgentZon.protocols.directory import build_search_message, parse_directory_response
from AgentZon.services.catalog_service import search_products
from AgentZon.services.history_service import record_search
from AgentZon.services.rdf_store import load_graph


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

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
    products = search_products(CATALOG_PATH, criteria)
    record_search(SEARCH_HISTORY_PATH, criteria, products)
    return products


def pla_de_presentacio(criteria, products):
    compra_agent = resolve_compra_agent()
    compra_url = replace_path(compra_agent.address, "/purchase")
    return render_template("cercador.html", criteria=criteria, products=products, compra_url=compra_url)


def replace_path(address, new_path):
    parsed = urlsplit(address)
    return urlunsplit((parsed.scheme, parsed.netloc, new_path, "", ""))


# Web interface --------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("cercador.html", criteria=default_criteria(), products=[], compra_url="")


@app.route("/search", methods=["POST"])
def search():
    criteria = {
        "text": request.form.get("text", ""),
        "category": request.form.get("category", ""),
        "brand": request.form.get("brand", ""),
        "min_price": float(request.form["min_price"]) if request.form.get("min_price") else None,
        "max_price": float(request.form["max_price"]) if request.form.get("max_price") else None,
    }
    products = pla_de_cerca(criteria)
    return pla_de_presentacio(criteria, products)


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
            ontology=AZON_ONTOLOGY,
        ).serialize(format="xml")
    content = properties["content"]
    criteria = parse_peticio_cerca(message_graph, content)
    products = pla_de_cerca(criteria)
    response_graph, response_content = build_resultat_cerca(f"result-{next_counter()}", products)
    response = build_message(
        response_graph,
        ACL.inform,
        sender=AGENT.uri,
        receiver=properties.get("sender"),
        content=response_content,
        msgcnt=next_counter(),
        ontology=AZON_ONTOLOGY,
    )
    return response.serialize(format="xml")


@app.route("/info")
def info():
    return load_graph(SEARCH_HISTORY_PATH).serialize(format="turtle")


@app.route("/stop")
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
    register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CercadorAgent, 0)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
