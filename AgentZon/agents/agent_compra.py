# -*- coding: utf-8 -*-
"""
filename: agent_compra

Agent compra AgentZon (orquestracio de comandes i enviaments).

/comm entrada ACL
/iface flux de compra web
/Stop para l'agent
"""

import argparse
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
    resolve_agent_hosts,
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


logger = config_logger(level=1)
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
ORDERS_PATH = None
SHIPPING_PATH = None
LOCATIONS_PATH = None
TRACKING_PATH = None
USER_BANK_PATH = None
SHIPPING_RESPONSIBILITY_PATH = None
NO_PRODUCTS_ERROR = "Has de seleccionar almenys un producte abans de continuar la compra."
VENDOR_EXTERN_AGENT_TYPE = URIRef("http://www.semanticweb.org/directory-service-ontology#VenedorExternAgent")


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, CATALOG_PATH, ORDERS_PATH, SHIPPING_PATH
    global LOCATIONS_PATH, TRACKING_PATH, USER_BANK_PATH, SHIPPING_RESPONSIBILITY_PATH, mss_cnt
    AGENT = settings["agent"]
    DirectoryAgent = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    ORDERS_PATH = data_dir / "comandes.ttl"
    SHIPPING_PATH = data_dir / "dades_enviament_usuari.ttl"
    LOCATIONS_PATH = data_dir / "ubicacions_productes.ttl"
    TRACKING_PATH = data_dir / "seguiment_enviaments.ttl"
    USER_BANK_PATH = data_dir / "dades_bancaries_usuari.ttl"
    SHIPPING_RESPONSIBILITY_PATH = data_dir / "responsable_enviament_productes.ttl"
    mss_cnt = 0


def _msgcnt():
    global mss_cnt
    current = mss_cnt
    mss_cnt += 1
    return current


def resolve_agents(agent_type):
    return resolve_agents_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, agent_type)


def resolve_agent(agent_type):
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, agent_type)


def resolve_cercador_iface_url():
    cercador_agent = resolve_agent(DSO.CercadorAgent)
    return replace_url_path(cercador_agent.address, "/iface")


def redirect_to_cercador_with_error():
    query = urlencode({"purchase_error": NO_PRODUCTS_ERROR})
    return redirect(f"{resolve_cercador_iface_url()}?{query}")


def normalize_selected_product_ids(product_ids):
    return [product_id for product_id in product_ids if product_id]


def get_client_ip():
    return get_client_ip_from_request(request)


def pla_demanar_informacio_usuari(selected_product_ids, client_ip):
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
    if not external_groups:
        return []

    try:
        venedor_agent = resolve_agent(VENDOR_EXTERN_AGENT_TYPE)
    except Exception:
        print("INFO AgenteCompra => No s'ha pogut resoldre Venedor Extern")
        return []

    shipments = []
    for group in external_groups:
        subset_order = {**order, "products": group["products"]}
        message = build_peticio_enviament_extern(
            subset_order,
            group["seller_id"],
            sender=AGENT.uri,
            receiver=venedor_agent.uri,
            msgcnt=_msgcnt(),
        )
        reply = MESSAGE_SENDER(message, venedor_agent.address)
        shipments.extend(extract_external_shipments_from_reply(reply))
        pla_cobrament_extern(subset_order, group["seller_id"])
    return shipments


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
    return collect_warehouse_reservations(
        order,
        centre_groups,
        AGENT.uri,
        MESSAGE_SENDER,
        _msgcnt,
    )


def pla_informar_usuari_sobre_l_enviament(order, shipments):
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
    opinador_agent = resolve_agent(DSO.OpinadorAgent)
    message = build_peticio_registre_compra(
        order,
        sender=AGENT.uri,
        receiver=opinador_agent.uri,
        msgcnt=_msgcnt(),
    )
    reply = MESSAGE_SENDER(message, opinador_agent.address)
    return extract_registration_confirmation(reply)


def pla_registrar_dades_d_usuari_al_cobrador(order):
    if has_user_bank_data(USER_BANK_PATH, order["user_id"]):
        return None
    try:
        cobrador = resolve_agent(DSO.CobradorAgent)
    except Exception:
        print("INFO AgenteCompra => No s'ha pogut resoldre Cobrador per registre bancari")
        return None
    shipping = order["shipping_data"]
    bank_data = f"card-****-{order['user_id']}"
    message = build_peticio_registre_dades_usuari(
        order["user_id"],
        bank_data,
        shipping["payment_method"],
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=_msgcnt(),
    )
    try:
        status = extract_confirmacio_registre_dades(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        return None
    logger.info("Dades bancaries de l'usuari %s registrades al Cobrador (%s)", order["user_id"], status)
    return status


def pla_cobrament_extern(order, seller_id):
    try:
        cobrador = resolve_agent(DSO.CobradorAgent)
    except Exception:
        print("INFO AgenteCompra => No s'ha pogut resoldre Cobrador per cobrament extern")
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
        msgcnt=_msgcnt(),
    )
    try:
        confirmation = extract_confirmacio_pagament(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        return None
    logger.info(
        "Cobrament extern confirmat per la comanda %s (pagament %s, venedor %s)",
        order["order_id"],
        confirmation["payment_id"],
        seller_id,
    )
    return confirmation


def carregar_comanda(order_id):
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
        msgcnt=mss_cnt,
    )


def process_shipping_update(gm, content, sender):
    invoice = extract_invoice_from_content(gm, content)
    shipped = (content, RDF.type, AZON.ConfirmacioEnviament) in gm
    touched_orders = set()

    for shipment in extract_shipping_details_list(gm):
        localized_product_id = shipment.get("localized_product_id")
        if not localized_product_id:
            continue
        order_id = lookup_order_for_localized_product(TRACKING_PATH, localized_product_id)
        if order_id is None:
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
        msgcnt=mss_cnt,
    )
    return response, order, shipping_details


def build_purchase_request_from_form(form_data, user_id):
    request_graph = build_peticio_compra(
        f"iface-purchase-{_msgcnt()}",
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
        msgcnt=_msgcnt(),
    )
    content = request_graph.value(predicate=RDF.type, object=AZON.PeticioCompra)
    return request_graph, content


@app.route("/iface", methods=["GET", "POST"])
def browser_iface():
    """
    Permet la comunicacio amb l'agent via un navegador.
    """
    if request.method == "GET":
        return redirect(resolve_cercador_iface_url())

    selected_product_ids = normalize_selected_product_ids(request.form.getlist("selected_product_ids"))
    if not selected_product_ids:
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
    order = carregar_comanda(order_id)
    if order is None:
        return ("Comanda no trobada", 404)
    shipments = load_tracking_for_order(TRACKING_PATH, order_id)
    return pla_informar_usuari_sobre_l_enviament(order, shipments)


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio de l'agent compra.
    """
    global mss_cnt

    print("INFO AgenteCompra => Peticio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")

    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO AgenteCompra => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        content = msgdic["content"]
        accion = gm.value(subject=content, predicate=RDF.type)

        if perf == ACL.inform and accion in {AZON.DadesEnviament, AZON.ConfirmacioEnviament}:
            print("INFO AgenteCompra => Actualitzacio enviament %s" % accion)
            gr = process_shipping_update(gm, content, msgdic.get("sender"))
        elif perf != ACL.request or accion != AZON.PeticioCompra:
            gr = build_message(
                Graph(),
                ACL["not-understood"],
                sender=AGENT.uri,
                receiver=msgdic.get("sender"),
                msgcnt=mss_cnt,
            )
            print("INFO AgenteCompra => Accio no suportada: %s" % accion)
        else:
            request_data = parse_peticio_compra(gm, content)
            if not request_data.get("product_ids"):
                gr = build_message(
                    Graph(),
                    ACL.failure,
                    sender=AGENT.uri,
                    receiver=msgdic.get("sender"),
                    msgcnt=mss_cnt,
                )
                print("INFO AgenteCompra => PeticioCompra sense productes")
            else:
                print("INFO AgenteCompra => PeticioCompra")
                gr, _, _ = process_purchase_request(
                    request_data,
                    acl_sender=msgdic.get("sender"),
                    request_content=content,
                )

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["compra"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent("CompraAgent", "Compra", args.port, host=publish_host),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DirectoryAgent, DSO.CompraAgent, 0),
    )
