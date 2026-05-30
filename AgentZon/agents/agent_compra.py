"""Purchase agent coordinating ACL purchase requests and browser wrappers."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import unicodedata
from difflib import SequenceMatcher
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
from protocols.centre_logistic import build_productes_localitzats, extract_shipping_details
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
from services.order_service import (
    build_order,
    save_order,
    save_user_shipping_data,
    update_order_final_delivery_date,
)
from services.rdf_store import load_graph


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
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
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


def normalize_city_name(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    compact = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(compact.split())


def choose_logistics_centre_for_product(user_city, candidate_centres):
    if not candidate_centres:
        raise ValueError("No logistics centres are available for the requested product")

    normalized_user_city = normalize_city_name(user_city)

    def score(candidate):
        candidate_city = normalize_city_name(candidate.get("centre_city", ""))
        exact_match = candidate_city == normalized_user_city
        similarity = SequenceMatcher(None, normalized_user_city, candidate_city).ratio()
        return (
            0 if exact_match else 1,
            -similarity,
            candidate.get("centre_id", ""),
        )

    return min(candidate_centres, key=score)


def load_product_location_candidates(product_ids):
    graph = load_graph(LOCATIONS_PATH)
    candidates_by_product = {}
    for product_id in product_ids:
        product_node = AZON[f"product-{product_id}"]
        candidates = []
        for centre_node in graph.objects(product_node, AZON.UbicatACentre):
            centre_id = graph.value(centre_node, AZON.IdCentreLogistic)
            if centre_id is None:
                continue
            candidates.append(
                {
                    "centre_id": str(centre_id),
                    "centre_city": str(graph.value(centre_node, AZON.Ciutat) or ""),
                }
            )
        candidates_by_product[product_id] = sorted(candidates, key=lambda candidate: candidate["centre_id"])
    return candidates_by_product


def resolve_centre_agents():
    return resolve_agents(DSO.CentreLogisticAgent)


def match_candidate_centres(candidate_centres, registered_centres):
    registered_by_id = {centre["centre_id"]: centre for centre in registered_centres if centre.get("centre_id")}
    matched = []
    for candidate in candidate_centres:
        registered = registered_by_id.get(candidate["centre_id"])
        if registered is None:
            continue
        matched.append(
            {
                **registered,
                "centre_id": candidate["centre_id"],
                "centre_city": candidate.get("centre_city") or registered.get("centre_city", ""),
            }
        )
    if not matched and len(registered_centres) == 1:
        registered = registered_centres[0]
        return [
            {
                **registered,
                "centre_id": candidate["centre_id"],
                "centre_city": candidate.get("centre_city") or registered.get("centre_city", ""),
            }
            for candidate in candidate_centres
        ]
    return matched


def enrich_shipment_details(order, product, selected_centre, shipping_details):
    details = {
        **shipping_details,
        "product_id": shipping_details.get("product_id") or product["product_id"],
        "product_name": product.get("name"),
        "centre_id": shipping_details.get("centre_id") or selected_centre.get("centre_id"),
        "centre_city": shipping_details.get("centre_city") or selected_centre.get("centre_city"),
        "delivery_city": order["shipping_data"]["city"],
    }
    if shipping_details.get("invoice") is not None:
        details["invoice"] = shipping_details["invoice"]
    return details


def build_invoice_summary(order, shipments):
    lines = sorted(
        [
            {"product_id": product["product_id"], "name": product["name"], "price": product["price"]}
            for product in order["products"]
        ],
        key=lambda line: line["product_id"],
    )
    shipment_invoices = [shipment["invoice"] for shipment in shipments if shipment.get("invoice")]
    fallback_products_subtotal = round(sum(line["price"] for line in lines), 2)
    fallback_transport_cost = round(sum(shipment["price"] for shipment in shipments), 2)

    if not shipment_invoices:
        return {
            "payment_id": "PENDENT",
            "order_id": order["order_id"],
            "amount": round(fallback_products_subtotal + fallback_transport_cost, 2),
            "method": order["shipping_data"]["payment_method"],
            "status": "PENDENT",
            "date": "",
            "lines": lines,
            "transport_cost": fallback_transport_cost,
            "products_subtotal": fallback_products_subtotal,
        }

    payment_ids = sorted({invoice["payment_id"] for invoice in shipment_invoices if invoice.get("payment_id")})
    statuses = sorted({invoice["status"] for invoice in shipment_invoices if invoice.get("status")})
    methods = sorted({invoice["method"] for invoice in shipment_invoices if invoice.get("method")})
    dates = sorted({invoice["date"] for invoice in shipment_invoices if invoice.get("date")})
    products_subtotal = round(sum(invoice.get("products_subtotal", 0.0) for invoice in shipment_invoices), 2)
    transport_cost = round(sum(invoice.get("transport_cost", 0.0) for invoice in shipment_invoices), 2)
    amount = round(sum(invoice.get("amount", 0.0) for invoice in shipment_invoices), 2)

    if not products_subtotal:
        products_subtotal = fallback_products_subtotal
    if not transport_cost:
        transport_cost = fallback_transport_cost
    if not amount:
        amount = round(products_subtotal + transport_cost, 2)

    return {
        "payment_id": ", ".join(payment_ids) if payment_ids else "PENDENT",
        "order_id": order["order_id"],
        "amount": amount,
        "method": methods[0] if len(methods) == 1 else order["shipping_data"]["payment_method"],
        "status": ", ".join(statuses) if statuses else "PENDENT",
        "date": ", ".join(dates),
        "lines": lines,
        "transport_cost": transport_cost,
        "products_subtotal": products_subtotal,
    }


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
    registered_centres = resolve_centre_agents()
    candidate_centres_by_product = load_product_location_candidates([product["product_id"] for product in order["products"]])
    shipments = []

    for product in order["products"]:
        candidate_centres = match_candidate_centres(
            candidate_centres_by_product.get(product["product_id"], []),
            registered_centres,
        )
        selected_centre = choose_logistics_centre_for_product(order["shipping_data"]["city"], candidate_centres)
        normalized_delivery_city = normalize_city_name(order["shipping_data"]["city"])
        scored_candidates = []
        for candidate in candidate_centres:
            candidate_city = normalize_city_name(candidate.get("centre_city", ""))
            exact_match = candidate_city == normalized_delivery_city
            similarity = SequenceMatcher(None, normalized_delivery_city, candidate_city).ratio()
            scored_candidates.append(
                {
                    "centre": candidate,
                    "exact_match": exact_match,
                    "similarity": similarity,
                    "score": (
                        0 if exact_match else 1,
                        -similarity,
                        candidate.get("centre_id", ""),
                    ),
                }
            )
        selected_candidate = next(
            candidate
            for candidate in scored_candidates
            if candidate["centre"].get("centre_id") == selected_centre.get("centre_id")
        )
        tied_candidates = [
            candidate for candidate in scored_candidates if candidate["score"][:2] == selected_candidate["score"][:2]
        ]
        reason = "coincideix exactament amb la ciutat de lliurament"
        if not selected_candidate["exact_match"]:
            reason = (
                "te la millor semblanca amb la ciutat de lliurament "
                f"({selected_candidate['similarity']:.3f})"
            )
        if len(tied_candidates) > 1:
            reason += " i s'ha desfet l'empat per centre_id"
        options = ", ".join(
            f"{candidate['centre'].get('centre_id')} ({candidate['centre'].get('centre_city', '-')})"
            for candidate in scored_candidates
        )
        logger.info(
            "Opcions de centre logistic per al producte %s de la comanda %s: %s",
            product["product_id"],
            order["order_id"],
            options,
        )
        logger.info(
            "Escollit el centre %s (%s) per al producte %s de la comanda %s perque %s",
            selected_centre["centre_id"],
            selected_centre.get("centre_city", ""),
            product["product_id"],
            order["order_id"],
            reason,
        )
        message, _ = build_productes_localitzats(
            order,
            products=[product],
            centre=selected_centre,
            sender=AGENT.uri,
            receiver=selected_centre["uri"],
            msgcnt=next_counter(),
        )
        reply = MESSAGE_SENDER(message, selected_centre["address"])
        shipments.append(enrich_shipment_details(order, product, selected_centre, extract_shipping_details(reply)))

    return shipments


def pla_informar_usuari_sobre_l_enviament(order, shipments):
    return render_template(
        "shipping_summary.html",
        order=order,
        shipments=shipments,
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
    # Delega al Cobrador el registre de les dades bancaries de l'usuari (cap. Guardar dades bancaries).
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
    # External-shipping integration point for marketplace products.
    return build_peticio_enviament_extern(
        order,
        sender=AGENT.uri,
        receiver=external_logistics_agent.uri,
        msgcnt=next_counter(),
    )


def pla_cobrament_extern(order, seller_id):
    # Pla de cobrament extern: demana al Cobrador que cobri els productes d'enviament extern.
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
