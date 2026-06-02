"""Agent cercador: cerca de productes per ACL (/comm) i interfície web (/iface)."""

import argparse
from pathlib import Path

from flask import Flask, render_template, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
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
    serve_agent,
)
from protocols.cerca import build_peticio_cerca, build_resultat_cerca, parse_peticio_cerca
from protocols.venedor_extern import (
    build_confirmacio_alta_producte_extern,
    parse_alta_producte_extern,
)
from services.agent_common_service import (
    get_client_ip_from_request,
    replace_url_path,
    resolve_agent_via_directory,
)
from services.catalog_service import add_external_product, search_products
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
    """Inicialitza dependències i rutes de dades del Cercador."""
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, CATALOG_PATH, SEARCH_HISTORY_PATH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    SEARCH_HISTORY_PATH = data_dir / "historial_cerques.ttl"
    COUNTER = 0


def next_counter():
    """Retorna un identificador incremental per als missatges ACL."""
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


# Agent logic ----------------------------------------------------------------------
def default_criteria():
    """Retorna criteris de cerca per defecte."""
    return {"text": "", "category": "", "brand": "", "min_price": None, "max_price": None}


def resolve_compra_agent():
    """Resol l'Agent Compra via servei de directori."""
    return resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, DSO.CompraAgent)


def resolve_opinador_agent():
    """Resol l'Agent Opinador via servei de directori."""
    return resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, DSO.OpinadorAgent)


def resolve_retornador_agent():
    """Resol l'Agent Retornador via servei de directori."""
    return resolve_agent_via_directory(AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, next_counter, DSO.RetornadorAgent)


def resolve_retornador_iface_url():
    """URL de la interfície del Retornador (directori o port per defecte)."""
    try:
        retornador_agent = resolve_retornador_agent()
        return replace_url_path(retornador_agent.address, "/iface")
    except Exception:
        host = request.host.split(":")[0] if request.host else "127.0.0.1"
        fallback = f"http://{host}:{DEFAULT_PORTS['retornador']}/iface"
        logger.warning(
            "No s'ha pogut resoldre l'agent Retornador via directori; s'utilitza %s",
            fallback,
        )
        return fallback


def pla_afegir_info_producte_extern_a_la_bd(message_graph, content, sender):
    """Pla d'emmagatzematge d'un producte extern al catàleg."""
    request_data = parse_alta_producte_extern(message_graph, content)
    product_id = add_external_product(CATALOG_PATH, request_data["product"])
    logger.info("Producte extern %s registrat al catàleg", product_id)
    return build_confirmacio_alta_producte_extern(
        product_id,
        request_data["product"].get("sku_extern", ""),
        data_alta=request_data["product"].get("data_alta"),
        sender=AGENT.uri,
        receiver=sender,
        msgcnt=next_counter(),
    )


def pla_de_cerca(criteria):
    """Executa el pla de cerca sobre el catàleg."""
    logger.info("Executant cerca amb criteris: %s", criteria)
    products = search_products(CATALOG_PATH, criteria)
    logger.info("La cerca ha retornat %d productes", len(products))
    return products


def purchase_error_message():
    """Recupera missatges d'error de compra passats per query string."""
    return request.args.get("purchase_error", "")


def get_client_ip():
    """Adreca IP del client HTTP (proxy-aware) com a identificador d'usuari."""
    return get_client_ip_from_request(request)


def pla_de_presentacio(criteria, products, purchase_error=""):
    """Construeix la vista de resultats de cerca amb enllaços d'accions."""
    compra_agent = resolve_compra_agent()
    compra_url = replace_url_path(compra_agent.address, "/iface")
    opinador_url = ""
    retornador_url = resolve_retornador_iface_url()
    try:
        opinador_agent = resolve_opinador_agent()
        opinador_url = replace_url_path(opinador_agent.address, "/iface")
    except Exception:
        logger.warning("No s'ha pogut resoldre l'agent Opinador per a la interfície")
    return render_template(
        "cercador.html",
        criteria=criteria,
        products=products,
        compra_url=compra_url,
        opinador_url=opinador_url,
        retornador_url=retornador_url,
        search_path="/iface",
        purchase_error=purchase_error,
    )


# Web interface --------------------------------------------------------------------
@app.route("/iface", methods=["GET", "POST"])
def iface():
    """Interfície web del Cercador: formulari i resultats."""
    if request.method == "GET":
        opinador_url = ""
        retornador_url = resolve_retornador_iface_url()
        try:
            opinador_agent = resolve_opinador_agent()
            opinador_url = replace_url_path(opinador_agent.address, "/iface")
        except Exception:
            logger.warning("No s'ha pogut resoldre l'agent Opinador per a la interfície")
        return render_template(
            "cercador.html",
            criteria=default_criteria(),
            products=[],
            compra_url="",
            opinador_url=opinador_url,
            retornador_url=retornador_url,
            search_path="/iface",
            purchase_error=purchase_error_message(),
        )
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
    record_search(SEARCH_HISTORY_PATH, criteria, products, user_id=get_client_ip())
    return pla_de_presentacio(criteria, products)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    """Entrada ACL del Cercador (`PeticioCerca` -> `ResultatCerca`)."""
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
    message_type = message_graph.value(content, RDF.type)
    if message_type == AZON.AltaProducteExtern:
        logger.info("Rebuda peticio ACL d'alta de producte extern")
        response = pla_afegir_info_producte_extern_a_la_bd(message_graph, content, properties.get("sender"))
        return response.serialize(format="xml")

    if message_type != AZON.PeticioCerca:
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
    """Atura el servidor Flask de l'agent."""
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    """Punt d'entrada executable del Cercador."""
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
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DIRECTORY_AGENT, DSO.CercadorAgent, 0),
    )


if __name__ == "__main__":
    main()
