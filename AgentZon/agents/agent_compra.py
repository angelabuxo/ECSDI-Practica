"""Agent de compra: orquestra comandes, centres logístics, pagament i resum web."""

import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from flask import Flask, redirect, render_template, request
from rdflib import Graph, RDF, URIRef

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
    serve_agent,
)
from protocols.compra import (
    build_peticio_compra,
    build_peticio_registre_compra,
    build_resultat_compra,
    extract_registration_confirmation,
    parse_peticio_compra,
)
from protocols.centre_logistic import extract_shipping_details_list
from protocols.venedor_extern import (
    build_peticio_enviament_extern,
    extract_external_shipments_from_reply,
)
from protocols.pagament import (
    SENTIT_PAGAMENT,
    build_peticio_pagament,
    build_peticio_registre_dades_usuari,
    extract_invoice_from_content,
    extract_confirmacio_pagament,
    extract_confirmacio_registre_dades,
)
from services.agent_common_service import (
    get_client_ip_from_request,
    replace_url_path,
    resolve_agent_via_directory,
    resolve_agents_via_directory,
)
from services.catalog_service import get_products_by_ids
from services.external_vendor_service import load_shipping_responsibility_by_product
from services.payment_service import has_user_bank_data
from services.logistics_routing_service import (
    group_order_products_by_logistics_centre,
    load_product_location_candidates,
)
from services.order_service import (
    build_order,
    load_order,
    save_order,
    save_user_shipping_data,
    update_order_final_delivery_date,
)
from services.shipping_service import (
    build_invoice_summary,
    collect_warehouse_reservations,
    group_shipments_for_display,
)
from services.shipping_tracking_service import (
    aggregate_official_delivery_date,
    apply_shipping_update,
    load_tracking_for_order,
    lookup_order_for_localized_product,
    save_localization_confirmations,
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
TRACKING_PATH = None
USER_BANK_PATH = None
SHIPPING_RESPONSIBILITY_PATH = None
COUNTER = 0
_MSGCNT_LOCK = threading.Lock()
NO_PRODUCTS_ERROR = "Has de seleccionar almenys un producte abans de continuar la compra."
VENDOR_EXTERN_AGENT_TYPE = URIRef("http://www.semanticweb.org/directory-service-ontology#VenedorExternAgent")


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    """Inicialitza estat global, paths de dades i dependències de missatgeria."""
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH, ORDERS_PATH, SHIPPING_PATH, LOCATIONS_PATH, TRACKING_PATH, USER_BANK_PATH, SHIPPING_RESPONSIBILITY_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    ORDERS_PATH = data_dir / "comandes.ttl"
    SHIPPING_PATH = data_dir / "dades_enviament_usuari.ttl"
    LOCATIONS_PATH = data_dir / "ubicacions_productes.ttl"
    TRACKING_PATH = data_dir / "seguiment_enviaments.ttl"
    USER_BANK_PATH = data_dir / "dades_bancaries_usuari.ttl"
    SHIPPING_RESPONSIBILITY_PATH = data_dir / "responsable_enviament_productes.ttl"
    COUNTER = 0


def next_counter():
    """Retorna un `msgcnt` incremental segur per concurrència."""
    global COUNTER
    with _MSGCNT_LOCK:
        current = COUNTER
        COUNTER += 1
        return current


# Directory helpers ----------------------------------------------------------------
def resolve_agents(agent_type):
    """Resol tots els agents d'un tipus via directori."""
    return resolve_agents_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, agent_type)


def resolve_agent(agent_type):
    """Resol un únic agent d'un tipus via directori."""
    return resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, agent_type)


def resolve_cercador_iface_url():
    """Construeix l'URL de retorn a la interfície del Cercador."""
    cercador_agent = resolve_agent(DSO.CercadorAgent)
    return replace_url_path(cercador_agent.address, "/iface")


def redirect_to_cercador_with_error():
    """Redirigeix al Cercador amb el missatge d'error de compra."""
    query = urlencode({"purchase_error": NO_PRODUCTS_ERROR})
    return redirect(f"{resolve_cercador_iface_url()}?{query}")


def normalize_selected_product_ids(product_ids):
    """Neteja valors buits del selector de productes."""
    return [product_id for product_id in product_ids if product_id]


def get_client_ip():
    """Adreça IP del client HTTP (proxy-aware) com a identificador d'usuari."""
    return get_client_ip_from_request(request)


# Plans ----------------------------------------------------------------------------
def pla_demanar_informacio_usuari(selected_product_ids, client_ip):
    """Pla inicial: demanar dades d'usuari abans de confirmar compra."""
    product_ids = normalize_selected_product_ids(selected_product_ids)
    if not product_ids:
        return redirect_to_cercador_with_error()
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    if not products:
        return redirect_to_cercador_with_error()
    return render_template(
        "compra.html",
        products=products,
        iface_path="/iface",
        client_ip=client_ip,
    )


def split_order_products(order):
    """Separa productes interns, externs amb logística de plataforma i externs delegats."""
    responsibility = load_shipping_responsibility_by_product(SHIPPING_RESPONSIBILITY_PATH)
    external_logistics_by_seller = {}
    platform_shipped = []
    internal = []

    for product in order["products"]:
        product_id = product["product_id"]
        info = responsibility.get(product_id)
        if info and info.get("requires_external_logistics"):
            seller_id = info["seller_id"]
            external_logistics_by_seller.setdefault(seller_id, []).append(product)
        elif info:
            platform_shipped.append(product)
        else:
            internal.append(product)

    external_groups = [
        {"seller_id": seller_id, "products": products}
        for seller_id, products in external_logistics_by_seller.items()
    ]
    return external_groups, platform_shipped, internal


def pla_enviament_extern(order, external_groups):
    """Pla d'enviament delegat a venedors externs i cobrament associat."""
    if not external_groups:
        return []

    try:
        venedor_agent = resolve_agent(VENDOR_EXTERN_AGENT_TYPE)
    except Exception:
        logger.warning("No s'ha pogut resoldre l'Agent Venedor Extern; s'omet l'enviament extern")
        return []

    shipments = []
    for group in external_groups:
        subset_order = {**order, "products": group["products"]}
        message = build_peticio_enviament_extern(
            subset_order,
            group["seller_id"],
            sender=AGENT.uri,
            receiver=venedor_agent.uri,
            msgcnt=next_counter(),
        )
        reply = MESSAGE_SENDER(message, venedor_agent.address)
        shipments.extend(extract_external_shipments_from_reply(reply))
        pla_cobrament_extern(subset_order, group["seller_id"])
    return shipments


def pla_producte_als_nostres_magatzems(order):
    """Pla de localització i reserva de productes als centres logístics."""
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
    return collect_warehouse_reservations(
        order,
        centre_groups,
        AGENT.uri,
        MESSAGE_SENDER,
        next_counter,
    )


def pla_informar_usuari_sobre_l_enviament(order, shipments):
    """Pla de presentació del resum d'enviament per a l'usuari."""
    final_delivery_date = max(
        [shipment["delivery_date"] for shipment in shipments if shipment.get("delivery_date")],
        default=order.get("final_delivery_date") or order["delivery_date"],
    )
    return render_template(
        "shipping_summary.html",
        order=order,
        shipment_groups=group_shipments_for_display(shipments),
        final_delivery_date=final_delivery_date,
        invoice=build_invoice_summary(order, shipments),
        order_status_url=f"/orders/{order['order_id']}",
    )


def pla_delegar_registre_compra(order):
    """Pla que delega a Opinador el registre d'historial de compra."""
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
    """Pla que registra dades bancàries d'usuari al Cobrador, si cal."""
    if has_user_bank_data(USER_BANK_PATH, order["user_id"]):
        logger.info(
            "Ometent registre de dades bancaries: l'usuari %s ja en té registrades",
            order["user_id"],
        )
        return None
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


def pla_cobrament_extern(order, seller_id):
    """Inicia el cobrament/transferència externa cap a venedor."""
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
        "sentit": SENTIT_PAGAMENT,
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


def carregar_comanda(order_id):
    """Carrega una comanda amb el seu seguiment d'enviament."""
    stored_order = load_order(ORDERS_PATH, order_id)
    if stored_order is None:
        return None
    products = get_products_by_ids(CATALOG_PATH, stored_order["product_ids"])
    return {
        "order_id": stored_order["order_id"],
        "user_id": stored_order["user_id"],
        "user_name": stored_order["user_name"],
        "products": products,
        "shipping_data": stored_order["shipping_data"],
        "delivery_date": stored_order["delivery_date"],
        "final_delivery_date": stored_order.get("final_delivery_date"),
    }


def _build_acknowledgement(receiver):
    return build_message(
        Graph(),
        ACL.inform,
        sender=AGENT.uri,
        receiver=receiver,
        msgcnt=next_counter(),
    )


def process_shipping_update(message_graph, content, sender):
    """Processa actualitzacions logístiques rebudes dels centres."""
    invoice = extract_invoice_from_content(message_graph, content)
    shipped = (content, RDF.type, AZON.ConfirmacioEnviament) in message_graph
    touched_orders = set()

    for shipment in extract_shipping_details_list(message_graph):
        localized_product_id = shipment.get("localized_product_id")
        if not localized_product_id:
            continue
        order_id = lookup_order_for_localized_product(TRACKING_PATH, localized_product_id)
        if order_id is None:
            logger.warning(
                "No s'ha trobat la comanda per al producte localitzat %s",
                localized_product_id,
            )
            continue
        shipment = {**shipment, "order_id": order_id}
        apply_shipping_update(
            TRACKING_PATH,
            shipment,
            shipped=shipped,
            invoice=invoice,
        )
        touched_orders.add(order_id)

    for order_id in touched_orders:
        entries = load_tracking_for_order(TRACKING_PATH, order_id)
        final_delivery_date = aggregate_official_delivery_date(entries)
        if final_delivery_date is not None:
            update_order_final_delivery_date(ORDERS_PATH, order_id, final_delivery_date)

    return _build_acknowledgement(sender)


def process_purchase_request(request_data, acl_sender=None, request_content=None):
    """Orquestra el flux complet de compra des d'una petició ACL."""
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
    external_groups, platform_shipped, internal_products = split_order_products(order)
    warehouse_order = {**order, "products": internal_products + platform_shipped}
    shipping_details = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        bank_future = executor.submit(pla_registrar_dades_d_usuari_al_cobrador, order)
        history_future = executor.submit(pla_delegar_registre_compra, order)
        warehouse_future = (
            executor.submit(pla_producte_als_nostres_magatzems, warehouse_order)
            if warehouse_order["products"]
            else None
        )
        external_future = (
            executor.submit(pla_enviament_extern, order, external_groups)
            if external_groups
            else None
        )
        if warehouse_future is not None:
            shipping_details.extend(warehouse_future.result())
        if external_future is not None:
            shipping_details.extend(external_future.result())
        bank_future.result()
        history_future.result()
    save_localization_confirmations(TRACKING_PATH, shipping_details)
    response = build_resultat_compra(
        order,
        shipping_details,
        sender=AGENT.uri,
        receiver=acl_sender,
        request_content=request_content,
        msgcnt=next_counter(),
    )
    return response, order, shipping_details


def build_purchase_request_from_form(form_data, user_id):
    """Construeix una `PeticioCompra` a partir del formulari web."""
    request_graph = build_peticio_compra(
        f"iface-purchase-{next_counter()}",
        user_id=user_id,
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
    """Interfície web de Compra: captura dades i mostra resum."""
    if request.method == "GET":
        return redirect(resolve_cercador_iface_url())

    selected_product_ids = normalize_selected_product_ids(request.form.getlist("selected_product_ids"))
    if not selected_product_ids:
        logger.warning("Compra interrompuda: cap producte seleccionat")
        return redirect_to_cercador_with_error()

    client_ip = get_client_ip()
    if "user_name" not in request.form:
        return pla_demanar_informacio_usuari(selected_product_ids, client_ip)

    request_graph, content = build_purchase_request_from_form(request.form, client_ip)
    request_data = parse_peticio_compra(request_graph, content)
    _, order, shipping_details = process_purchase_request(
        request_data,
        acl_sender=AGENT.uri,
        request_content=content,
    )
    return pla_informar_usuari_sobre_l_enviament(order, shipping_details)


@app.route("/orders/<order_id>")
def order_status(order_id):
    """Endpoint de consulta de l'estat d'una comanda."""
    order = carregar_comanda(order_id)
    if order is None:
        return ("Comanda no trobada", 404)
    shipments = load_tracking_for_order(TRACKING_PATH, order_id)
    return pla_informar_usuari_sobre_l_enviament(order, shipments)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    """Entrada ACL de Compra: compra nova i actualitzacions d'enviament."""
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties:
        logger.warning("CompraAgent ha rebut un missatge malformat a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")
    content = properties["content"]
    performative = properties.get("performative")
    message_type = message_graph.value(content, RDF.type)

    if performative == ACL.inform and message_type in {AZON.DadesEnviament, AZON.ConfirmacioEnviament}:
        return process_shipping_update(message_graph, content, properties.get("sender")).serialize(format="xml")

    if performative != ACL.request or message_type != AZON.PeticioCompra:
        logger.warning("CompraAgent ha rebut una accio no suportada a /comm")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            receiver=properties.get("sender"),
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
    """Atura el servidor Flask de l'agent."""
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    """Punt d'entrada executable de l'Agent Compra."""
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
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CompraAgent, 0),
    )


if __name__ == "__main__":
    main()
