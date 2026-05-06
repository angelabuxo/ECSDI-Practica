"""Purchase agent coordinating order capture and internal shipping requests."""

import argparse
from pathlib import Path

from flask import Flask, render_template, request
from rdflib import Graph

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties, send_message
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
from AgentZon.protocols.centre_logistic import build_productes_localitzats, extract_shipping_details
from AgentZon.protocols.compra import build_peticio_registre_compra, extract_registration_confirmation
from AgentZon.protocols.directory import build_search_message, parse_directory_response
from AgentZon.services.catalog_service import get_products_by_ids
from AgentZon.services.order_service import create_order, save_user_shipping_data
from AgentZon.services.rdf_store import load_graph


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
ORDERS_PATH = None
SHIPPING_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH, ORDERS_PATH, SHIPPING_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    ORDERS_PATH = data_dir / "comandes.ttl"
    SHIPPING_PATH = data_dir / "dades_enviament_usuari.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def resolve_agent(agent_type):
    message = build_search_message(AGENT, agent_type, DIRECTORY_AGENT, msgcnt=next_counter())
    response = MESSAGE_SENDER(message, DIRECTORY_AGENT.address)
    return parse_directory_response(response)


def pla_demanar_informacio_usuari(selected_product_ids):
    products = get_products_by_ids(CATALOG_PATH, selected_product_ids)
    return render_template("compra.html", products=products)


def pla_registrar_dades_d_usuari(selected_product_ids, form_data):
    shipping = {
        "user_id": form_data["user_id"],
        "user_name": form_data["user_name"],
        "street_address": form_data["street_address"],
        "city": form_data["city"],
        "priority": form_data["priority"],
        "payment_method": form_data["payment_method"],
    }
    save_user_shipping_data(SHIPPING_PATH, shipping)
    products = get_products_by_ids(CATALOG_PATH, selected_product_ids)
    return create_order(ORDERS_PATH, shipping, products)


def pla_producte_als_nostres_magatzems(order):
    centre_agent = resolve_agent(DSO.CentreLogisticAgent)
    localized_products = [
        {
            "product_id": product["product_id"],
            "name": product["name"],
            "weight": product["weight"],
        }
        for product in order["products"]
    ]
    message, _ = build_productes_localitzats(
        order["order_id"],
        order["user_id"],
        order["shipping_data"]["city"],
        order["shipping_data"]["priority"],
        localized_products,
        sender=AGENT.uri,
        receiver=centre_agent.uri,
        msgcnt=next_counter(),
    )
    return extract_shipping_details(MESSAGE_SENDER(message, centre_agent.address))


def pla_informar_usuari_sobre_l_enviament(order, shipping_details):
    return render_template("shipping_summary.html", order=order, shipping_details=shipping_details)


def pla_delegar_registre_compra(order):
    opinador_agent = resolve_agent(DSO.OpinadorAgent)
    message = build_peticio_registre_compra(
        order,
        sender=AGENT.uri,
        receiver=opinador_agent.uri,
        msgcnt=next_counter(),
    )
    reply = MESSAGE_SENDER(message, opinador_agent.address)
    return extract_registration_confirmation(reply)


def pla_enviament_extern():
    return None


# Web interface --------------------------------------------------------------------
@app.route("/purchase", methods=["POST"])
def purchase():
    selected = request.form.getlist("selected_product_ids")
    return pla_demanar_informacio_usuari(selected)


@app.route("/confirm-purchase", methods=["POST"])
def confirm_purchase():
    selected = request.form.getlist("selected_product_ids")
    order = pla_registrar_dades_d_usuari(selected, request.form)
    pla_delegar_registre_compra(order)
    shipping_details = pla_producte_als_nostres_magatzems(order)
    return pla_informar_usuari_sobre_l_enviament(order, shipping_details)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    response = build_message(
        Graph(),
        ACL["not-understood"],
        sender=AGENT.uri,
        msgcnt=next_counter(),
        ontology=AZON_ONTOLOGY,
    )
    return response.serialize(format="xml")


@app.route("/info")
def info():
    return load_graph(ORDERS_PATH).serialize(format="turtle")


@app.route("/stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["compra"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent("CompraAgent", "Compra", args.port, host=hostname),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CompraAgent, 0)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
