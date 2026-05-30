"""Agent de compra: orquestra comandes, centres logístics, pagament i resum web."""

import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import uuid4

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
from protocols.compra import (
    build_confirmacio_enviament,
    build_peticio_compra,
    build_peticio_enviament_extern,
    build_peticio_registre_compra,
    extract_registration_confirmation,
    parse_peticio_compra,
)
from protocols.directory import build_search_message, parse_directory_response, parse_directory_responses
from protocols.pagament import (
    build_peticio_pagament,
    build_peticio_registre_dades_usuari,
    extract_confirmacio_pagament,
    extract_confirmacio_registre_dades,
)
from services.catalog_service import get_products_by_ids
from services.logistics_routing_service import (
    group_order_products_by_logistics_centre,
    load_product_location_candidates,
)
from services.order_service import (
    build_order,
    save_order,
    save_user_shipping_data,
    update_order_final_delivery_date,
)
from services.shipping_service import (
    build_invoice_summary,
    collect_warehouse_shipments,
    group_shipments_for_display,
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
LOCATIONS_PATH = None
COUNTER = 0
_MSGCNT_LOCK = threading.Lock()
NO_PRODUCTS_ERROR = "Has de seleccionar almenys un producte abans de continuar la compra."


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH, ORDERS_PATH, SHIPPING_PATH, LOCATIONS_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    ORDERS_PATH = data_dir / "comandes.ttl"
    SHIPPING_PATH = data_dir / "dades_enviament_usuari.ttl"
    LOCATIONS_PATH = data_dir / "ubicacions_productes.ttl"
    COUNTER = 0


def next_counter():
    global COUNTER
    with _MSGCNT_LOCK:
        current = COUNTER
        COUNTER += 1
        return current


# Directory helpers ----------------------------------------------------------------
def resolve_agents(agent_type):
    message = build_search_message(AGENT, agent_type, DIRECTORY_AGENT, msgcnt=next_counter())
    response = MESSAGE_SENDER(message, DIRECTORY_AGENT.address)
    return parse_directory_responses(response)


def resolve_agent(agent_type):
    return parse_directory_response(
        MESSAGE_SENDER(
            build_search_message(AGENT, agent_type, DIRECTORY_AGENT, msgcnt=next_counter()),
            DIRECTORY_AGENT.address,
        )
    )


def resolve_cercador_iface_url():
    cercador_agent = resolve_agent(DSO.CercadorAgent)
    parsed = urlsplit(cercador_agent.address)
    return urlunsplit((parsed.scheme, parsed.netloc, "/iface", "", ""))


def redirect_to_cercador_with_error():
    query = urlencode({"purchase_error": NO_PRODUCTS_ERROR})
    return redirect(f"{resolve_cercador_iface_url()}?{query}")


def normalize_selected_product_ids(product_ids):
    return [product_id for product_id in product_ids if product_id]


# Plans ----------------------------------------------------------------------------
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
    registered_centres = resolve_agents(DSO.CentreLogisticAgent)
    candidate_centres_by_product = load_product_location_candidates(
        LOCATIONS_PATH,
        [product["product_id"] for product in order["products"]],
    )
    centre_groups = group_order_products_by_logistics_centre(
        order,
        registered_centres,
        candidate_centres_by_product,
    )
    for group in centre_groups:
        logger.info(
            "Enviant %d producte(s) de la comanda %s al centre %s",
            len(group["products"]),
            order["order_id"],
            group["centre"]["centre_id"],
        )
    return collect_warehouse_shipments(
        order,
        centre_groups,
        AGENT.uri,
        MESSAGE_SENDER,
        next_counter,
    )


def pla_informar_usuari_sobre_l_enviament(order, shipments):
    return render_template(
        "shipping_summary.html",
        order=order,
        shipment_groups=group_shipments_for_display(shipments),
        final_delivery_date=max(shipment["delivery_date"] for shipment in shipments),
        invoice=build_invoice_summary(order, shipments),
    )


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


def pla_registrar_dades_d_usuari_al_cobrador(order):
    try:
        cobrador = resolve_agent(DSO.CobradorAgent)
    except Exception:
        logger.warning("No s'ha pogut resoldre el Cobrador; s'omet el registre de dades bancaries")
        return None
    shipping = order["shipping_data"]
    bank_data = f"card-****-{order['user_id']}"
    message = build_peticio_registre_dades_usuari(
        order["user_id"],
        bank_data,
        shipping["payment_method"],
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=next_counter(),
    )
    try:
        status = extract_confirmacio_registre_dades(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        logger.warning("El Cobrador no ha confirmat el registre de dades bancaries de l'usuari %s", order["user_id"])
        return None
    logger.info("Dades bancaries de l'usuari %s registrades al Cobrador (%s)", order["user_id"], status)
    return status


def pla_enviament_extern(order, external_logistics_agent):
    return build_peticio_enviament_extern(
        order,
        sender=AGENT.uri,
        receiver=external_logistics_agent.uri,
        msgcnt=next_counter(),
    )


def pla_cobrament_extern(order, seller_id):
    try:
        cobrador = resolve_agent(DSO.CobradorAgent)
    except Exception:
        logger.warning("No s'ha pogut resoldre el Cobrador; s'omet el cobrament extern")
        return None
    amount = round(sum(product.get("price", 0.0) for product in order["products"]), 2)
    payment = {
        "payment_id": f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": order["order_id"],
        "amount": amount,
        "method": "transferencia",
        "user_id": order["user_id"],
        "seller_id": seller_id,
        "product_ids": [product["product_id"] for product in order["products"]],
    }
    message = build_peticio_pagament(
        payment,
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=next_counter(),
    )
    try:
        confirmation = extract_confirmacio_pagament(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        logger.warning("El cobrament extern de la comanda %s no s'ha pogut completar", order["order_id"])
        return None
    logger.info(
        "Cobrament extern confirmat per la comanda %s (pagament %s, venedor %s)",
        order["order_id"],
        confirmation["payment_id"],
        seller_id,
    )
    return confirmation


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
    with ThreadPoolExecutor(max_workers=3) as executor:
        bank_future = executor.submit(pla_registrar_dades_d_usuari_al_cobrador, order)
        history_future = executor.submit(pla_delegar_registre_compra, order)
        shipping_future = executor.submit(pla_producte_als_nostres_magatzems, order)
        shipping_details = shipping_future.result()
        bank_future.result()
        history_future.result()
    final_delivery_date = max(shipment["delivery_date"] for shipment in shipping_details)
    update_order_final_delivery_date(ORDERS_PATH, order["order_id"], final_delivery_date)
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
