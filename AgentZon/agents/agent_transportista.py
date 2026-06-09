# -*- coding: utf-8 -*-
"""
filename: agent_transportista

Agent transportista extern AgentZon (ofertes i negociacio de transport).

/comm entrada ACL (cfp, propose, accept-proposal, reject-proposal)
/iface vista tecnica
/Stop para l'agent
"""

import argparse
from datetime import date, timedelta

from flask import Flask, request
from rdflib import Graph

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from config import (
    DEFAULT_PORTS,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_agent_hosts,
    serve_agent,
)
from protocols.centre_logistic import (
    build_resposta_oferta_transport,
    extract_transport_offer,
    parse_peticio_transport,
)

logger = config_logger(level=1)
app = Flask(__name__)

mss_cnt = 0
AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
TRANSPORT_ID = "fast"
PRICE_PER_KG = 8.0
DELIVERY_DAYS = 1
LAST_OFFERS = {}
MIN_ACCEPTABLE_RATIO = 0.75


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, TRANSPORT_ID, PRICE_PER_KG, DELIVERY_DAYS, mss_cnt, LAST_OFFERS
    AGENT = settings["agent"]
    DirectoryAgent = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    TRANSPORT_ID = settings["transport_id"]
    PRICE_PER_KG = settings["price_per_kg"]
    DELIVERY_DAYS = settings["delivery_days"]
    mss_cnt = 0
    LAST_OFFERS = {}


def generar_oferta_transport(request_data):
    offer = {
        "lot_id": request_data["lot_id"],
        "order_id": request_data["order_id"],
        "transport_id": TRANSPORT_ID,
        "transport_name": AGENT.name,
        "city": request_data["city"],
        "delivery_date": (date.today() + timedelta(days=DELIVERY_DAYS)).isoformat(),
        "price": round(request_data["total_weight"] * PRICE_PER_KG, 2),
    }
    logger.info(
        "Generant oferta %s pel lot %s (%.2f EUR/kg, pes=%.2f, total=%.2f EUR, entrega=%s)",
        TRANSPORT_ID,
        offer["lot_id"],
        PRICE_PER_KG,
        request_data["total_weight"],
        offer["price"],
        offer["delivery_date"],
    )
    return offer


def register_transport_agent(directory_agent=None, msgcnt=0):
    target_directory = directory_agent or DirectoryAgent
    if target_directory is None:
        return False
    return register_with_directory(
        AGENT,
        target_directory,
        DSO.TransportistaAgent,
        msgcnt=msgcnt,
        metadata={AZON.IdTransportista: TRANSPORT_ID},
    )


def respondre_contraoferta(counter_offer, receiver=None):
    previous_offer = LAST_OFFERS.get(counter_offer["lot_id"])
    if previous_offer is None:
        logger.warning(
            "Contraoferta rebut per lot %s sense oferta previa (transport_id=%s)",
            counter_offer.get("lot_id"),
            TRANSPORT_ID,
        )
        return build_message(Graph(), ACL.refuse, sender=AGENT.uri, receiver=receiver, msgcnt=mss_cnt)

    min_acceptable = round(previous_offer["price"] * MIN_ACCEPTABLE_RATIO, 2)
    accept = counter_offer["price"] >= min_acceptable
    logger.info(
        "Contraoferta pel lot %s (%s): proposta %.2f EUR, original %.2f EUR, minim acceptable %.2f EUR -> %s",
        counter_offer["lot_id"],
        TRANSPORT_ID,
        counter_offer["price"],
        previous_offer["price"],
        min_acceptable,
        "accepta" if accept else "rebutja",
    )
    if accept:
        LAST_OFFERS[counter_offer["lot_id"]] = {**previous_offer, "price": counter_offer["price"]}
        return build_message(Graph(), ACL.agree, sender=AGENT.uri, receiver=receiver, msgcnt=mss_cnt)

    return build_message(Graph(), ACL.refuse, sender=AGENT.uri, receiver=receiver, msgcnt=mss_cnt)


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio del transportista.
    """
    global mss_cnt

    logger.debug("Peticio rebuda a /comm (transport_id=%s)", TRANSPORT_ID)

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")
    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        logger.warning("Missatge rebut no es FIPA ACL (transport_id=%s)", TRANSPORT_ID)
    else:
        perf = msgdic["performative"]
        sender = msgdic.get("sender")
        logger.debug("Performativa rebuda: %s (transport_id=%s)", str(perf).rsplit("#", 1)[-1], TRANSPORT_ID)
        if perf == ACL["accept-proposal"]:
            selected_offer = extract_transport_offer(gm)
            LAST_OFFERS.pop(selected_offer["lot_id"], None)
            logger.info(
                "Acceptacio rebuda pel lot %s (%s) - oferta eliminada",
                selected_offer["lot_id"],
                TRANSPORT_ID,
            )
            gr = build_message(Graph(), ACL.inform, sender=AGENT.uri, receiver=sender, msgcnt=mss_cnt)
        elif perf == ACL["reject-proposal"]:
            rejected_offer = extract_transport_offer(gm)
            LAST_OFFERS.pop(rejected_offer["lot_id"], None)
            logger.info(
                "Rebuig rebut pel lot %s (%s) - oferta eliminada",
                rejected_offer["lot_id"],
                TRANSPORT_ID,
            )
            gr = build_message(Graph(), ACL.inform, sender=AGENT.uri, receiver=sender, msgcnt=mss_cnt)
        elif perf == ACL.propose:
            counter_offer = extract_transport_offer(gm)
            logger.info(
                "Contraoferta rebuda pel lot %s (%s): preu proposat %.2f EUR",
                counter_offer.get("lot_id"),
                TRANSPORT_ID,
                counter_offer.get("price", 0),
            )
            gr = respondre_contraoferta(counter_offer, receiver=sender)
        elif perf != ACL.cfp:
            gr = build_message(
                Graph(),
                ACL["not-understood"],
                sender=AGENT.uri,
                receiver=sender,
                msgcnt=mss_cnt,
            )
            logger.warning("Performativa no suportada: %s (transport_id=%s)", str(perf), TRANSPORT_ID)
        else:
            content = msgdic["content"]
            request_data = parse_peticio_transport(gm, content)
            logger.info(
                "CFP rebut pel lot %s (pes=%.2f, desti=%s, entrega=%s)",
                request_data["lot_id"],
                request_data["total_weight"],
                request_data["city"],
                request_data["delivery_date"],
            )
            offer = generar_oferta_transport(request_data)
            LAST_OFFERS[offer["lot_id"]] = dict(offer)
            logger.info(
                "Oferta transport %s comanda %s (%.2f EUR)",
                TRANSPORT_ID,
                offer["order_id"],
                offer["price"],
            )
            gr = build_resposta_oferta_transport(
                offer,
                sender=AGENT.uri,
                receiver=sender,
                request_content=content,
                msgcnt=mss_cnt,
            )

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/iface")
def browser_iface():
    graph = Graph()
    bind_namespaces(graph)
    return graph.serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["transport_fast"])
    add_directory_arguments(parser)
    parser.add_argument("--transport-id", default="fast")
    parser.add_argument("--price-per-kg", type=float, default=8.0)
    parser.add_argument("--delivery-days", type=int, default=1)
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent(
                "Transportista-%s" % args.transport_id,
                "Transport%s" % args.transport_id.title(),
                args.port,
                host=publish_host,
            ),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "transport_id": args.transport_id,
            "price_per_kg": args.price_per_kg,
            "delivery_days": args.delivery_days,
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: register_transport_agent(0),
    )
