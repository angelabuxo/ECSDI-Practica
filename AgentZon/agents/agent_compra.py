"""Purchase agent coordinating ACL purchase requests and browser wrappers."""

import argparse
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from flask import Flask, redirect, render_template, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON
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
from protocols.centre_logistic import build_productes_localitzats, extract_shipping_details
from protocols.compra import (
    build_confirmacio_enviament,
    build_peticio_compra,
    build_peticio_enviament_extern,
    build_peticio_registre_compra,
    extract_registration_confirmation,
    parse_peticio_compra,
)
from protocols.directory import build_search_message, parse_directory_response
from services.catalog_service import get_products_by_ids
from services.order_service import (
    build_order,
    save_order,
    save_user_shipping_data,
    update_order_final_delivery_date,
)


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
ORDERS_PATH = None
SHIPPING_PATH = None
COUNTER = 0
NO_PRODUCTS_ERROR = "Has de seleccionar almenys un producte abans de continuar la compra."


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


def resolve_cercador_iface_url():
    cercador_agent = resolve_agent(DSO.CercadorAgent)
    parsed = urlsplit(cercador_agent.address)
    return urlunsplit((parsed.scheme, parsed.netloc, "/iface", "", ""))


def redirect_to_cercador_with_error():
    query = urlencode({"purchase_error": NO_PRODUCTS_ERROR})
    return redirect(f"{resolve_cercador_iface_url()}?{query}")


def normalize_selected_product_ids(product_ids):
    return [product_id for product_id in product_ids if product_id]


def pla_demanar_informacio_usuari(selected_product_ids):
    product_ids = normalize_selected_product_ids(selected_product_ids)
    if not product_ids:
        return redirect_to_cercador_with_error()
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    if not products:
        return redirect_to_cercador_with_error()
    return render_template("compra.html", products=products, iface_path="/iface")


def pla_registrar_dades_d_usuari(selected_product_ids, form_data):
    shipping = {
        "user_id": form_data["user_id"],
        "user_name": form_data["user_name"],
        "street_address": form_data["street_address"],
        "city": form_data["city"],
        "priority": form_data["priority"],
        "payment_method": form_data["payment_method"],
    }
    products = get_products_by_ids(CATALOG_PATH, selected_product_ids)
    order = build_order(shipping, products)
    logger.info("Persistint comanda %s amb %d productes", order["order_id"], len(products))
    save_user_shipping_data(SHIPPING_PATH, order)
    save_order(ORDERS_PATH, order)
    return order


def pla_producte_als_nostres_magatzems(order):
    centre_agent = resolve_agent(DSO.CentreLogisticAgent)
    logger.info("Delegant l'orquestracio de l'enviament a %s", centre_agent.name)
    message, _ = build_productes_localitzats(
        order,
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


def pla_enviament_extern(order, external_logistics_agent):
    # External-shipping integration point for marketplace products.
    return build_peticio_enviament_extern(
        order,
        sender=AGENT.uri,
        receiver=external_logistics_agent.uri,
        msgcnt=next_counter(),
    )


def process_purchase_request(request_data, acl_sender=None, request_content=None):
    if not request_data.get("product_ids"):
        raise ValueError(NO_PRODUCTS_ERROR)
    shipping = {
        "user_id": request_data["user_id"],
        "user_name": request_data["shipping_data"]["user_name"],
        "street_address": request_data["shipping_data"]["street_address"],
        "city": request_data["shipping_data"]["city"],
        "priority": request_data["shipping_data"]["priority"],
        "payment_method": request_data["payment_method"],
    }
    products = get_products_by_ids(CATALOG_PATH, request_data["product_ids"])
    order = build_order(shipping, products)
    logger.info("Persistint comanda %s amb %d productes", order["order_id"], len(products))
    save_user_shipping_data(SHIPPING_PATH, order)
    save_order(ORDERS_PATH, order)
    pla_delegar_registre_compra(order)
    shipping_details = pla_producte_als_nostres_magatzems(order)
    update_order_final_delivery_date(ORDERS_PATH, order["order_id"], shipping_details["delivery_date"])
    response = build_confirmacio_enviament(
        order,
        shipping_details,
        sender=AGENT.uri,
        receiver=acl_sender,
        request_content=request_content,
        msgcnt=next_counter(),
    )
    return response, order, shipping_details


def build_purchase_request_from_form(form_data):
    request_graph = build_peticio_compra(
        f"iface-purchase-{next_counter()}",
        user_id=form_data["user_id"],
        payment_method=form_data["payment_method"],
        shipping_data={
            "user_name": form_data["user_name"],
            "street_address": form_data["street_address"],
            "city": form_data["city"],
            "priority": form_data["priority"],
        },
        product_ids=form_data.getlist("selected_product_ids"),
        sender=AGENT.uri,
        receiver=AGENT.uri,
        msgcnt=next_counter(),
    )
    content = request_graph.value(predicate=RDF.type, object=AZON.PeticioCompra)
    return request_graph, content


# Web interface --------------------------------------------------------------------
@app.route("/iface", methods=["GET", "POST"])
def iface():
    if request.method == "GET":
        return redirect(resolve_cercador_iface_url())

    selected_product_ids = normalize_selected_product_ids(request.form.getlist("selected_product_ids"))
    if not selected_product_ids:
        logger.warning("Compra interrompuda: cap producte seleccionat")
        return redirect_to_cercador_with_error()

    if "user_id" not in request.form:
        return pla_demanar_informacio_usuari(selected_product_ids)

    request_graph, content = build_purchase_request_from_form(request.form)
    request_data = parse_peticio_compra(request_graph, content)
    _, order, shipping_details = process_purchase_request(
        request_data,
        acl_sender=AGENT.uri,
        request_content=content,
    )
    return pla_informar_usuari_sobre_l_enviament(order, shipping_details)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties or properties.get("performative") != ACL.request:
        logger.warning("CompraAgent ha rebut un missatge no-request o malformat a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    content = properties["content"]
    if message_graph.value(content, RDF.type) != AZON.PeticioCompra:
        logger.warning("CompraAgent ha rebut una accio no suportada a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    request_data = parse_peticio_compra(message_graph, content)
    if not request_data.get("product_ids"):
        logger.warning("Compra ACL rebutjada: cap producte a la peticio")
        return build_message(
            Graph(),
            ACL.failure,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            msgcnt=next_counter(),
        ).serialize(format="xml")
    response, _, _ = process_purchase_request(
        request_data,
        acl_sender=properties.get("sender"),
        request_content=content,
    )
    return response.serialize(format="xml")


@app.route("/Stop")
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
    logger.info("Registrant %s al directori %s", AGENT.name, DIRECTORY_AGENT.address)
    register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CompraAgent, 0)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
