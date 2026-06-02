"""Agent venedor extern: registre de productes externs i gestió d'enviaments delegats."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, render_template, request
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
from protocols.pagament import build_peticio_registre_dades_venedor, extract_confirmacio_registre_dades
from protocols.venedor_extern import (
    build_alta_producte_extern,
    build_confirmacio_alta_producte_extern,
    build_resposta_enviament_extern,
    parse_alta_producte_extern,
    parse_confirmacio_alta_producte_extern,
    parse_peticio_enviament_extern,
)
from services.agent_common_service import get_client_ip_from_request, resolve_agent_via_directory
from services.catalog_service import allocate_external_product_id
from services.external_vendor_service import save_external_product_location, save_shipping_responsibility
from services.payment_service import has_seller_bank_data, read_seller_bank_data, resolve_seller_display_name


app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
logger = config_logger(level=1)

VENDOR_EXTERN_AGENT_TYPE = URIRef("http://www.semanticweb.org/directory-service-ontology#VenedorExternAgent")

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
SHIPPING_RESPONSIBILITY_PATH = None
LOCATIONS_PATH = None
SELLER_BANK_PATH = None
COUNTER = 0


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    """Inicialitza dependències i rutes de dades del Venedor Extern."""
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH
    global SHIPPING_RESPONSIBILITY_PATH, LOCATIONS_PATH, SELLER_BANK_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    SHIPPING_RESPONSIBILITY_PATH = data_dir / "responsable_enviament_productes.ttl"
    LOCATIONS_PATH = data_dir / "ubicacions_productes.ttl"
    SELLER_BANK_PATH = data_dir / "dades_bancaries_venedors_externs.ttl"
    COUNTER = 0


def next_counter():
    """Retorna un identificador incremental per als missatges ACL."""
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


def resolve_cercador_agent():
    return resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, DSO.CercadorAgent)


def resolve_cobrador_agent():
    return resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, DSO.CobradorAgent)


# Plans ----------------------------------------------------------------------------
def pla_afegir_producte_extern_a_la_bd(request_data):
    """Desa responsabilitat d'enviament i ubicació del producte extern."""
    product = request_data["product"]
    seller = request_data["seller"]
    save_shipping_responsibility(
        SHIPPING_RESPONSIBILITY_PATH,
        product["product_id"],
        seller["seller_id"],
        product["requires_external_logistics"],
    )
    if not product["requires_external_logistics"] and product.get("centre_id"):
        save_external_product_location(LOCATIONS_PATH, product["product_id"], product["centre_id"])
    logger.info(
        "Producte extern %s registrat a responsable enviament (logistica externa=%s)",
        product["product_id"],
        product["requires_external_logistics"],
    )
    return product["product_id"]


def pla_delegar_afegir_info_producte_extern(message_graph, content):
    """Delega l'alta de catàleg a l'Agent Cercador."""
    cercador = resolve_cercador_agent()
    message = build_message(
        message_graph,
        ACL.request,
        sender=AGENT.uri,
        receiver=cercador.uri,
        content=content,
        msgcnt=next_counter(),
    )
    reply = MESSAGE_SENDER(message, cercador.address)
    return parse_confirmacio_alta_producte_extern(reply)


def pla_delegar_afegir_dades_bancaries_del_venedor_extern(seller):
    """Delega el registre bancari del venedor a l'Agent Cobrador."""
    if not seller.get("bank_data"):
        raise ValueError("Calen dades bancaries per registrar el venedor extern")
    cobrador = resolve_cobrador_agent()
    message = build_peticio_registre_dades_venedor(
        seller["seller_id"],
        seller["bank_data"],
        seller_name=seller.get("seller_name") or None,
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=next_counter(),
    )
    reply = MESSAGE_SENDER(message, cobrador.address)
    return extract_confirmacio_registre_dades(reply)


def ensure_seller_bank_registered(seller):
    """Registra dades bancàries del venedor només la primera vegada."""
    if has_seller_bank_data(SELLER_BANK_PATH, seller["seller_id"]):
        logger.info(
            "Ometent registre bancari: el venedor %s ja en té registrades",
            seller["seller_id"],
        )
        return None
    if not seller.get("bank_data"):
        logger.warning(
            "El venedor %s encara no té dades bancaries; cal completar el perfil a /iface",
            seller["seller_id"],
        )
        return None
    return pla_delegar_afegir_dades_bancaries_del_venedor_extern(seller)


def register_seller_profile(seller_id, seller_name, bank_data):
    """Registra el perfil inicial del venedor (nom + compte bancari)."""
    seller = {
        "seller_id": seller_id,
        "seller_name": seller_name.strip(),
        "bank_data": bank_data.strip(),
    }
    return pla_delegar_afegir_dades_bancaries_del_venedor_extern(seller)


def pla_comunicar_nou_producte_afegit(product_id, sku_extern, receiver=None):
    """Envia confirmació final de registre correcte."""
    return build_confirmacio_alta_producte_extern(
        product_id,
        sku_extern,
        sender=AGENT.uri,
        receiver=receiver,
        msgcnt=next_counter(),
    )


def process_alta_producte_extern(message_graph, content, receiver=None):
    """Orquestra el registre local i de catàleg en paral·lel i confirma el resultat."""
    request_data = parse_alta_producte_extern(message_graph, content)
    ensure_seller_bank_registered(request_data["seller"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        local_future = executor.submit(pla_afegir_producte_extern_a_la_bd, request_data)
        catalog_future = executor.submit(pla_delegar_afegir_info_producte_extern, message_graph, content)
        local_future.result()
        catalog_confirmation = catalog_future.result()
    return pla_comunicar_nou_producte_afegit(
        catalog_confirmation["product_id"],
        catalog_confirmation.get("sku_extern") or request_data["product"].get("sku_extern", ""),
        receiver=receiver,
    )


def process_peticio_enviament_extern(message_graph, content, sender):
    """Notifica la venda externa i retorna dades d'enviament estimades."""
    request_data = parse_peticio_enviament_extern(message_graph, content)
    delivery_date = (date.today() + timedelta(days=5)).isoformat()
    logger.info(
        "Rebuda peticio d'enviament extern per comanda %s (venedor %s, %d producte(s))",
        request_data["order_id"],
        request_data["seller_id"],
        len(request_data["products"]),
    )
    response = build_resposta_enviament_extern(
        request_data["order_id"],
        request_data["products"],
        request_data["seller_id"],
        delivery_date,
        request_data["city"],
        seller_display_name=resolve_seller_display_name(
            SELLER_BANK_PATH,
            request_data["seller_id"],
        ),
        sender=AGENT.uri,
        receiver=sender,
        msgcnt=next_counter(),
    )
    return response


def get_client_ip():
    """Retorna la IP del client com a identificador de venedor extern."""
    return get_client_ip_from_request(request)


def parse_products_from_form(form_data):
    """Extreu una llista de productes del formulari (pot incloure diverses files)."""
    names = form_data.getlist("name")
    descriptions = form_data.getlist("description")
    categories = form_data.getlist("category")
    brands = form_data.getlist("brand")
    prices = form_data.getlist("price")
    weights = form_data.getlist("weight")
    sku_externs = form_data.getlist("sku_extern")
    logistics_modes = form_data.getlist("logistics_mode")
    centre_ids = form_data.getlist("centre_id")

    products = []
    for index, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        requires_external_logistics = logistics_modes[index] == "vendor"
        products.append(
            {
                "name": name,
                "description": descriptions[index],
                "category": categories[index],
                "brand": brands[index],
                "price": float(prices[index]),
                "weight": float(weights[index]),
                "sku_extern": sku_externs[index],
                "requires_external_logistics": requires_external_logistics,
                "centre_id": centre_ids[index] if index < len(centre_ids) else "CL-BCN",
            }
        )
    return products


def build_product_payload(product_fields, seller_id):
    """Construeix el diccionari de producte amb identificador assignat."""
    product_id = allocate_external_product_id(CATALOG_PATH)
    return {
        "product_id": product_id,
        "name": product_fields["name"],
        "description": product_fields["description"],
        "category": product_fields["category"],
        "brand": product_fields["brand"],
        "price": product_fields["price"],
        "weight": product_fields["weight"],
        "sku_extern": product_fields["sku_extern"],
        "data_alta": date.today().isoformat(),
        "requires_external_logistics": product_fields["requires_external_logistics"],
        "centre_id": product_fields.get("centre_id", "CL-BCN"),
        "seller_id": seller_id,
    }


def build_seller_payload(seller_id):
    """Construeix el venedor a partir de la IP del client i el perfil persistit."""
    profile = read_seller_bank_data(SELLER_BANK_PATH, seller_id) or {}
    return {
        "seller_id": seller_id,
        "bank_data": profile.get("bank_data", ""),
        "seller_name": profile.get("seller_name", ""),
    }


def render_iface_page(client_ip, **context):
    """Renderitza la interfície amb l'estat del perfil del venedor."""
    seller_profile = read_seller_bank_data(SELLER_BANK_PATH, client_ip)
    defaults = {
        "iface_path": "/iface",
        "centres": ["CL-BCN", "CL-GI", "CL-TGN"],
        "client_ip": client_ip,
        "needs_vendor_setup": seller_profile is None,
        "seller_profile": seller_profile,
    }
    defaults.update(context)
    return render_template("venedor_extern.html", **defaults)


# Web interface --------------------------------------------------------------------
@app.route("/iface", methods=["GET", "POST"])
def iface():
    """Interfície del venedor extern per registrar nous productes."""
    client_ip = get_client_ip()
    if request.method == "GET":
        return render_iface_page(client_ip)

    form_type = request.form.get("form_type", "products")
    if form_type == "setup":
        seller_name = request.form.get("seller_name", "").strip()
        bank_data = request.form.get("bank_data", "").strip()
        if not seller_name or not bank_data:
            return render_iface_page(
                client_ip,
                error="Cal indicar el nom del venedor i les dades bancàries.",
            )
        if has_seller_bank_data(SELLER_BANK_PATH, client_ip):
            return render_iface_page(
                client_ip,
                setup_complete=True,
                message="El perfil del venedor ja estava registrat.",
            )
        register_seller_profile(client_ip, seller_name, bank_data)
        return render_iface_page(
            client_ip,
            setup_complete=True,
            message=f"Perfil registrat correctament com a {seller_name}.",
        )

    if not has_seller_bank_data(SELLER_BANK_PATH, client_ip):
        return render_iface_page(
            client_ip,
            error="Primer cal completar el perfil del venedor (nom i dades bancàries).",
        )

    seller = build_seller_payload(client_ip)
    product_fields_list = parse_products_from_form(request.form)
    if not product_fields_list:
        return render_iface_page(
            client_ip,
            error="Cal introduir almenys un producte.",
        )

    confirmations = []
    for product_fields in product_fields_list:
        product = build_product_payload(product_fields, seller["seller_id"])
        message = build_alta_producte_extern(
            product,
            seller,
            request_id=f"iface-alta-{next_counter()}",
            sender=AGENT.uri,
            receiver=AGENT.uri,
            msgcnt=next_counter(),
        )
        props = get_message_properties(message)
        content = props["content"]
        confirmation_message = process_alta_producte_extern(message, content, receiver=AGENT.uri)
        confirmation_data = parse_confirmacio_alta_producte_extern(confirmation_message)
        confirmations.append({"product": product, "confirmation": confirmation_data})

    return render_iface_page(client_ip, confirmations=confirmations)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    """Entrada ACL: alta de producte extern i peticions d'enviament."""
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties:
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    content = properties["content"]
    performative = properties.get("performative")
    message_type = message_graph.value(content, RDF.type)
    sender = properties.get("sender")

    if performative == ACL.request and message_type == AZON.AltaProducteExtern:
        response = process_alta_producte_extern(message_graph, content, receiver=sender)
        return response.serialize(format="xml")

    if performative == ACL.request and message_type == AZON.PeticioEnviamentExtern:
        response = process_peticio_enviament_extern(message_graph, content, sender)
        return response.serialize(format="xml")

    return build_message(
        Graph(),
        ACL["not-understood"],
        sender=AGENT.uri,
        receiver=sender,
        msgcnt=next_counter(),
    ).serialize(format="xml")


@app.route("/Stop")
def stop():
    """Atura el servidor Flask de l'agent."""
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    """Punt d'entrada executable de l'Agent Venedor Extern."""
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
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DIRECTORY_AGENT, VENDOR_EXTERN_AGENT_TYPE, 0),
    )


if __name__ == "__main__":
    main()
