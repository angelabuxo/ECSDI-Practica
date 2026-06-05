# -*- coding: utf-8 -*-
"""
filename: agent_cercador

Agent cercador de productes AgentZon.

/comm es la entrada per rebre missatges ACL
/iface permet consultar el cataleg des d'un navegador
/Stop para l'agent
"""

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
    resolve_agent_hosts,
    serve_agent,
)
from protocols.cerca import (
    build_peticio_cerca,
    build_resultat_cerca,
    build_resultat_consulta_productes,
    parse_peticio_cerca,
    parse_peticio_consulta_productes,
)
from protocols.opinador import build_peticio_registre_cerca, parse_confirmacio_registre_cerca
from protocols.venedor_extern import (
    build_confirmacio_alta_producte_extern,
    parse_alta_producte_extern,
)
from services.agent_common_service import (
    get_client_ip_from_request,
    replace_url_path,
    resolve_agent_via_directory,
)
from services.catalog_service import add_external_product, get_products_by_ids, search_products

logger = config_logger(level=1)
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

# Contador de missatges (patro SimpleInfoAgent / PROYECTO)
mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
CATALOG_PATH = None
SEARCH_HISTORY_PATH = None


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, CATALOG_PATH, SEARCH_HISTORY_PATH, mss_cnt
    AGENT = settings["agent"]
    DirectoryAgent = settings["directory_agent"]
    MESSAGE_SENDER = message_sender
    data_dir = Path(settings["data_dir"])
    CATALOG_PATH = data_dir / "productes.ttl"
    SEARCH_HISTORY_PATH = None
    mss_cnt = 0


def default_criteria():
    return {"text": "", "category": "", "brand": "", "min_price": None, "max_price": None}


def resolve_compra_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CompraAgent)


def resolve_opinador_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.OpinadorAgent)


def resolve_retornador_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.RetornadorAgent)


def _msgcnt():
    global mss_cnt
    current = mss_cnt
    mss_cnt += 1
    return current


def resolve_retornador_iface_url():
    try:
        retornador_agent = resolve_retornador_agent()
        return replace_url_path(retornador_agent.address, "/iface")
    except Exception:
        print("INFO AgenteCercador => No s'ha trobat Retornador al directori")
        return ""


def pla_afegir_info_producte_extern_a_la_bd(gm, content, sender):
    request_data = parse_alta_producte_extern(gm, content)
    product_id = add_external_product(CATALOG_PATH, request_data["product"])
    logger.info("Producte extern %s registrat al cataleg", product_id)
    return build_confirmacio_alta_producte_extern(
        product_id,
        request_data["product"].get("sku_extern", ""),
        data_alta=request_data["product"].get("data_alta"),
        sender=AGENT.uri,
        receiver=sender,
        msgcnt=mss_cnt,
    )


def pla_de_cerca(criteria):
    logger.info("Executant cerca amb criteris: %s", criteria)
    products = search_products(CATALOG_PATH, criteria)
    logger.info("La cerca ha retornat %d productes", len(products))
    return products


def pla_consulta_productes_acl(gm, content, sender):
    product_ids = parse_peticio_consulta_productes(gm, content)
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    return build_resultat_consulta_productes(
        products,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def pla_registrar_cerca_a_opinador(criteria, products, user_id):
    if not user_id:
        return None
    try:
        opinador = resolve_opinador_agent()
    except Exception as exc:
        logger.warning("No s'ha pogut resoldre Opinador per registrar la cerca: %s", exc)
        return None
    message = build_peticio_registre_cerca(
        {"user_id": user_id, "criteria": criteria, "products": products},
        sender=AGENT.uri,
        receiver=opinador.uri,
        msgcnt=_msgcnt(),
    )
    try:
        reply = MESSAGE_SENDER(message, opinador.address)
    except Exception as exc:
        logger.warning("No s'ha pogut registrar la cerca a Opinador: %s", exc)
        return None
    return parse_confirmacio_registre_cerca(reply)


def pla_de_presentacio(criteria, products, purchase_error=""):
    compra_agent = resolve_compra_agent()
    compra_url = replace_url_path(compra_agent.address, "/iface")
    opinador_url = ""
    retornador_url = resolve_retornador_iface_url()
    try:
        opinador_agent = resolve_opinador_agent()
        opinador_url = replace_url_path(opinador_agent.address, "/iface")
    except Exception as exc:
        logger.warning("No s'ha pogut resoldre Opinador per a la interficie: %s", exc)
        print("INFO AgenteCercador => No s'ha pogut resoldre Opinador per a la interficie: %s" % exc)
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


@app.route("/iface", methods=["GET", "POST"])
def browser_iface():
    """
    Permet la comunicacio amb l'agent via un navegador.
    """
    if request.method == "GET":
        opinador_url = ""
        retornador_url = resolve_retornador_iface_url()
        try:
            opinador_agent = resolve_opinador_agent()
            opinador_url = replace_url_path(opinador_agent.address, "/iface")
        except Exception as exc:
            logger.warning("No s'ha pogut resoldre Opinador per a la interficie: %s", exc)
            print("INFO AgenteCercador => No s'ha pogut resoldre Opinador per a la interficie: %s" % exc)
        return render_template(
            "cercador.html",
            criteria=default_criteria(),
            products=[],
            compra_url="",
            opinador_url=opinador_url,
            retornador_url=retornador_url,
            search_path="/iface",
            purchase_error=request.args.get("purchase_error", ""),
        )
    request_graph, content = build_peticio_cerca(
        "iface-search-%d" % _msgcnt(),
        text=request.form.get("text", ""),
        category=request.form.get("category", ""),
        brand=request.form.get("brand", ""),
        min_price=float(request.form["min_price"]) if request.form.get("min_price") else None,
        max_price=float(request.form["max_price"]) if request.form.get("max_price") else None,
    )
    criteria = parse_peticio_cerca(request_graph, content)
    products = pla_de_cerca(criteria)
    pla_registrar_cerca_a_opinador(criteria, products, get_client_ip_from_request(request))
    return pla_de_presentacio(criteria, products)


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio de l'agent cercador.
    """
    global mss_cnt

    print("INFO AgenteCercador => Peticio d'informacio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")

    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO AgenteCercador => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        if perf != ACL.request:
            gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
            print("INFO AgenteCercador => No es una request FIPA ACL\n")
        else:
            content = msgdic["content"]
            accion = gm.value(subject=content, predicate=RDF.type)
            if accion == AZON.AltaProducteExtern:
                print("INFO AgenteCercador => Alta producte extern")
                gr = pla_afegir_info_producte_extern_a_la_bd(gm, content, msgdic.get("sender"))
            elif accion == AZON.PeticioConsultaProductes:
                print("INFO AgenteCercador => Consulta de productes")
                gr = pla_consulta_productes_acl(gm, content, msgdic.get("sender"))
            elif accion != AZON.PeticioCerca:
                gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
                print("INFO AgenteCercador => Accio no suportada")
            else:
                criteria = parse_peticio_cerca(gm, content)
                products = pla_de_cerca(criteria)
                grespuesta, res_obj = build_resultat_cerca(
                    "result-%d" % mss_cnt,
                    products,
                    request_content=content,
                )
                gr = build_message(
                    grespuesta,
                    ACL.inform,
                    sender=AGENT.uri,
                    receiver=msgdic.get("sender"),
                    content=res_obj,
                    ontology=ONTOLOGY_URI,
                    msgcnt=mss_cnt,
                )

    mss_cnt += 1
    print("INFO AgenteCercador => Responem a la peticio")
    return gr.serialize(format="xml")


@app.route("/Stop")
def stop():
    """
    Entrypoint que para l'agent.
    """
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["cercador"])
    add_directory_arguments(parser)
    add_data_dir_argument(parser)
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent("CercadorAgent", "Cercador", args.port, host=publish_host),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: register_with_directory(AGENT, DirectoryAgent, DSO.CercadorAgent, 0),
    )
