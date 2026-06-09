# -*- coding: utf-8 -*-
"""
filename: agent_centre_logistic

Agent centre logistic AgentZon (lots, transport i cobrament intern).

/comm entrada ACL
/iface estat lots en turtle
/Stop para l'agent
"""

import argparse
import threading
from pathlib import Path

from flask import Flask, render_template, request
from rdflib import Graph, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentUtil.Agent import Agent
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import AZON
from config import (
    DEFAULT_PORTS,
    READY_DELIVERY_WINDOW_DAYS,
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
from protocols.centre_logistic import (
    build_accept_transport_offer,
    build_confirmacio_enviament,
    build_confirmacio_localitzacio,
    build_contraoferta_transport,
    build_dades_enviament,
    build_peticio_transport,
    build_reject_transport_offer,
    extract_transport_offer,
    parse_productes_localitzats,
)
from protocols.pagament import build_peticio_cobrament, extract_confirmacio_pagament
from services.agent_common_service import resolve_agent_via_directory, resolve_agents_via_directory
from services.logistics_service import (
    assign_transport_to_lot,
    build_internal_shipment,
    build_premium_counter_price,
    build_premium_price_cap,
    create_lot,
    format_centre_uri_name,
    list_all_lots,
    list_ready_lots_for_negotiation,
    load_lot_by_id,
    mark_lot_negotiating,
    mark_lot_shipped,
    match_transport_agent,
    query_transport_offers,
    select_best_offer,
    split_low_and_other_offers,
)


logger = config_logger(level=1)
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

mss_cnt = 0

AGENT = None
DirectoryAgent = None
MESSAGE_SENDER = send_message
TRANSPORT_AGENTS = []
LOTS_PATH = None
CENTRE_ID = None
CENTRE_CITY = None
AUTO_TRIGGER_READY_LOTS = True


def configure_runtime(settings, message_sender=send_message):
    global AGENT, DirectoryAgent, MESSAGE_SENDER, TRANSPORT_AGENTS, LOTS_PATH
    global CENTRE_ID, CENTRE_CITY, mss_cnt, AUTO_TRIGGER_READY_LOTS
    AGENT = settings["agent"]
    DirectoryAgent = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    TRANSPORT_AGENTS = settings["transport_agents"]
    CENTRE_ID = settings.get("centre_id")
    CENTRE_CITY = settings.get("centre_city")
    AUTO_TRIGGER_READY_LOTS = settings.get("auto_trigger_ready_lots", True)
    lots_filename = f"lots-{CENTRE_ID}.ttl" if CENTRE_ID else "lots.ttl"
    LOTS_PATH = Path(settings["data_dir"]) / lots_filename
    mss_cnt = 0


def _msgcnt():
    global mss_cnt
    current = mss_cnt
    mss_cnt += 1
    return current


def _shipment_scope_texts(shipment):
    product = shipment.get("product") or {}
    product_id = product.get("product_id")
    lot_id = shipment.get("lot_id")
    localized_product_id = shipment.get("localized_product_id")
    if product_id:
        base = f"producte {product_id}"
        suffix = f" ({localized_product_id})" if localized_product_id else ""
        return (
            f"S'ha enviat el {base}{suffix} del lot {lot_id}" if lot_id else f"S'ha enviat el {base}{suffix}",
            f"al {base}{suffix} del lot {lot_id}" if lot_id else f"al {base}{suffix}",
        )
    if lot_id:
        return (f"S'ha enviat el lot {lot_id}", f"al lot {lot_id}")
    return ("S'ha enviat un producte", "al producte enviat")


def pla_assignar_producte_a_lot(request_data):
    centre_id = request_data.get("centre_id") or CENTRE_ID
    product = request_data["product"]
    logger.info(
        "Processant producte %s al centre %s (desti=%s, data=%s)",
        product["product_id"],
        centre_id,
        request_data["city"],
        request_data["delivery_date"],
    )
    lot = create_lot(LOTS_PATH, request_data)
    if lot["created_new_lot"]:
        logger.info(
            "Creat lot %s al centre %s (pes_total=%.2f)",
            lot["lot_id"],
            centre_id,
            lot["total_weight"],
        )
    else:
        item_count = len(lot.get("items", []))
        logger.info(
            "Reutilitzat lot %s al centre %s: ara te %d producte(s), pes total %.2f kg",
            lot["lot_id"],
            centre_id,
            item_count,
            lot["total_weight"],
        )
    logger.info(
        "Assignat producte %s al lot %s",
        product["product_id"],
        lot["lot_id"],
    )
    return lot


def resolve_transport_agents():
    if TRANSPORT_AGENTS:
        logger.debug("Usant llista de transportistes preconfigurada (%d agents)", len(TRANSPORT_AGENTS))
        return TRANSPORT_AGENTS
    if DirectoryAgent is None:
        logger.warning("No hi ha agent de directori configurat; no es poden resoldre transportistes")
        return []

    entries = resolve_agents_via_directory(
        AGENT,
        DirectoryAgent,
        MESSAGE_SENDER,
        _msgcnt,
        DSO.TransportistaAgent,
    )
    agents = [
        Agent(
            name=entry["name"],
            uri=entry["uri"],
            address=entry["address"],
            stop="",
        )
        for entry in entries
    ]
    logger.info("Resolts %d transportistes via directori: %s", len(agents), [(a.name, a.address) for a in agents])
    return agents


def pla_cerca_de_transportista(lot):
    transport_agents = resolve_transport_agents()
    logger.info(
        "Iniciant negociacio del lot %s (%d transportistes, pes_total=%.2f, desti=%s, entrega_estimada=%s)",
        lot["lot_id"],
        len(transport_agents),
        lot["total_weight"],
        lot["city"],
        lot["delivery_date"],
    )

    def request_offer(transport_agent):
        try:
            logger.debug("Enviant CFP a %s (%s) per al lot %s", transport_agent.name, transport_agent.address, lot["lot_id"])
            message, _ = build_peticio_transport(
                lot,
                sender=AGENT.uri,
                receiver=transport_agent.uri,
                msgcnt=_msgcnt(),
            )
            reply = MESSAGE_SENDER(message, transport_agent.address)
            offer = extract_transport_offer(reply)
            logger.debug("Oferta rebuda de %s per al lot %s: %.2f EUR, entrega %s", transport_agent.name, lot["lot_id"], offer["price"], offer["delivery_date"])
            return offer
        except Exception as exc:
            logger.warning(
                "No s'ha pogut obtenir oferta de %s (%s): %s",
                transport_agent.name,
                transport_agent.address,
                exc,
            )
            return None

    offers = query_transport_offers(lot, transport_agents, request_offer)
    if not offers:
        raise RuntimeError("Cap transportista disponible per al lot {}".format(lot["lot_id"]))
    logger.info("Rebudes %d ofertes de transport per al lot %s", len(offers), lot["lot_id"])
    for offer in sorted(offers, key=lambda current: (current["price"], current["delivery_date"], current["transport_id"])):
        logger.info(
            "Oferta inicial rebuda per al lot %s: %s (%s) %.2f EUR, entrega %s",
            lot["lot_id"],
            offer["transport_id"],
            offer["transport_name"],
            offer["price"],
            offer["delivery_date"],
        )
    return transport_agents, offers


def pla_negociar_contraoferta(lot, transport_agents, offers):
    low_offer, other_offers = split_low_and_other_offers(offers)

    if not other_offers:
        logger.info(
            "Lot %s amb una sola oferta (%s); sense contraoferta",
            lot["lot_id"],
            low_offer["transport_id"] if low_offer else "cap",
        )
        return {"low_offer": low_offer, "counter_price": None, "cap_price": None, "negotiated_offers": []}

    counter_price = build_premium_counter_price(low_offer)
    cap_price = build_premium_price_cap(low_offer)
    logger.info(
        "Contraoferta per al lot %s: preu objectiu %.2f EUR (sostre %.2f EUR) basat en oferta baixa de %s (%.2f EUR)",
        lot["lot_id"],
        counter_price,
        cap_price,
        low_offer["transport_id"],
        low_offer["price"],
    )

    negotiated_offers = []
    for other_offer in other_offers:
        transport_agent = match_transport_agent(transport_agents, other_offer["transport_id"])
        logger.debug(
            "Enviant contraoferta a %s (%s) per al lot %s: %.2f EUR (original %.2f EUR)",
            other_offer["transport_id"],
            transport_agent.address,
            lot["lot_id"],
            counter_price,
            other_offer["price"],
        )
        message = build_contraoferta_transport(
            lot,
            other_offer,
            new_price=counter_price,
            sender=AGENT.uri,
            receiver=transport_agent.uri,
            msgcnt=_msgcnt(),
        )
        try:
            reply = MESSAGE_SENDER(message, transport_agent.address)
            performative = get_message_properties(reply).get("performative")
            logger.debug(
                "Resposta contraoferta de %s per al lot %s: %s",
                other_offer["transport_id"],
                lot["lot_id"],
                str(performative).rsplit("#", 1)[-1] if performative is not None else "None",
            )
            if performative == ACL.agree:
                logger.info(
                    "Contraoferta acceptada per %s al lot %s: %.2f EUR",
                    other_offer["transport_id"],
                    lot["lot_id"],
                    counter_price,
                )
                negotiated_offers.append({**other_offer, "price": counter_price})
            elif performative == ACL.propose:
                negotiated_offer = extract_transport_offer(reply)
                if negotiated_offer["price"] <= cap_price:
                    logger.info(
                        "Contraoferta rebuda de %s al lot %s: %.2f EUR (entrega %s)",
                        other_offer["transport_id"],
                        lot["lot_id"],
                        negotiated_offer["price"],
                        negotiated_offer["delivery_date"],
                    )
                    negotiated_offers.append(negotiated_offer)
                else:
                    logger.info(
                        "Contraoferta rebutjada de %s al lot %s: %.2f EUR > sostre %.2f EUR",
                        other_offer["transport_id"],
                        lot["lot_id"],
                        negotiated_offer["price"],
                        cap_price,
                    )
            else:
                logger.info(
                    "Contraoferta rebutjada per %s al lot %s",
                    other_offer["transport_id"],
                    lot["lot_id"],
                )
        except Exception as exc:
            logger.warning(
                "Error en contraoferta a %s pel lot %s: %s",
                other_offer["transport_id"],
                lot["lot_id"],
                exc,
            )

    logger.info(
        "Resum negociacio lot %s: %d concessio(ns) acceptada(es) de %d contraofertes (preu objectiu=%.2f EUR, sostre=%.2f EUR)",
        lot["lot_id"],
        len(negotiated_offers),
        len(other_offers),
        counter_price,
        cap_price,
    )
    return {
        "low_offer": low_offer,
        "counter_price": counter_price,
        "cap_price": cap_price,
        "negotiated_offers": negotiated_offers,
    }


def pla_de_transportista_escollit(lot, transport_agents, initial_offers, negotiation, request_content=None):
    selected = select_best_offer(
        negotiation["low_offer"],
        negotiation["negotiated_offers"],
    )
    negotiated_ids = {o["transport_id"] for o in negotiation.get("negotiated_offers", [])}
    if negotiated_ids and selected["transport_id"] in negotiated_ids:
        source = "negociada"
    elif negotiated_ids:
        source = "oferta baixa"
    else:
        source = "inicial"
    logger.info(
        "Transportista seleccionat per al lot %s: %s (%s) amb oferta %s de %.2f EUR i entrega %s",
        lot["lot_id"],
        selected["transport_id"],
        selected["transport_name"],
        source,
        selected["price"],
        selected["delivery_date"],
    )
    offered_transport_ids = {offer["transport_id"] for offer in initial_offers}
    for transport_id in offered_transport_ids:
        transport_agent = match_transport_agent(transport_agents, transport_id)
        base_offer = next(offer for offer in initial_offers if offer["transport_id"] == transport_id)
        if transport_id == selected["transport_id"]:
            message = build_accept_transport_offer(
                lot,
                selected,
                sender=AGENT.uri,
                receiver=transport_agent.uri,
                msgcnt=_msgcnt(),
            )
            logger.info(
                "Notificant acceptacio al transportista %s per al lot %s",
                transport_id,
                lot["lot_id"],
            )
        else:
            message = build_reject_transport_offer(
                lot,
                base_offer,
                sender=AGENT.uri,
                receiver=transport_agent.uri,
                msgcnt=_msgcnt(),
            )
            logger.info(
                "Notificant rebuig al transportista %s per al lot %s",
                transport_id,
                lot["lot_id"],
            )
        MESSAGE_SENDER(message, transport_agent.address)
    return selected


def pla_producte_sha_enviat(shipment):
    cobrador = resolve_cobrador_agent()
    if cobrador is None:
        return None
    sent_text, payment_target = _shipment_scope_texts(shipment)
    product = shipment.get("product") or {}
    charge = {
        "user_id": shipment["user_id"],
        "preu_producte": float(product.get("price") or 0.0),
        "cost_transport": float(shipment.get("transport_cost") or 0.0),
    }
    logger.info("%s; demanant cobrament al Cobrador", sent_text)
    message = build_peticio_cobrament(
        charge,
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=_msgcnt(),
    )
    try:
        confirmation = extract_confirmacio_pagament(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        logger.warning("El cobrament intern per %s no s'ha pogut completar", payment_target)
        return None
    if not confirmation.get("payment_id"):
        logger.warning("El Cobrador no ha retornat una factura per %s", payment_target)
        return None
    return confirmation


def resolve_compra_agent():
    if DirectoryAgent is None:
        return None
    try:
        return resolve_agent_via_directory(
            AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CompraAgent,
        )
    except Exception:
        print("INFO AgenteCentreLogistic => No s'ha pogut resoldre Compra")
        return None


def resolve_cobrador_agent():
    if DirectoryAgent is None:
        return None
    try:
        return resolve_agent_via_directory(
            AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CobradorAgent,
        )
    except Exception:
        print("INFO AgenteCentreLogistic => No s'ha pogut resoldre Cobrador")
        return None


def _build_item_offer(lot, item):
    item_weight = float(item["product"].get("weight", 0.0))
    total_weight = lot["total_weight"] or item_weight or 1.0
    if total_weight and item_weight:
        item_price = round(lot["price"] * item_weight / total_weight, 2)
    else:
        item_price = round(lot["price"], 2)
    return {
        "lot_id": lot["lot_id"],
        "transport_id": lot["transport_id"],
        "transport_name": lot["transport_name"],
        "delivery_date": lot["official_delivery_date"],
        "price": item_price,
        "lot_transport_price": lot["price"],
        "total_lot_weight": total_weight,
    }


def _notify_compra(message_builder, item, offer, compra_agent, invoice=None):
    if compra_agent is None:
        return
    if invoice is None:
        message = message_builder(
            item,
            offer,
            sender=AGENT.uri,
            receiver=compra_agent.uri,
            msgcnt=_msgcnt(),
        )
    else:
        message = message_builder(
            item,
            offer,
            sender=AGENT.uri,
            receiver=compra_agent.uri,
            invoice=invoice,
            msgcnt=_msgcnt(),
        )
    MESSAGE_SENDER(message, compra_agent.address)


def process_ready_lot(lot_id):
    lot = mark_lot_negotiating(LOTS_PATH, lot_id)
    if lot is None:
        return None

    transport_agents, offers = pla_cerca_de_transportista(lot)
    negotiation = pla_negociar_contraoferta(lot, transport_agents, offers)
    selected = pla_de_transportista_escollit(lot, transport_agents, offers, negotiation)
    assigned_lot = assign_transport_to_lot(LOTS_PATH, lot_id, selected)
    compra_agent = resolve_compra_agent()

    for item in assigned_lot["items"]:
        _notify_compra(build_dades_enviament, item, _build_item_offer(assigned_lot, item), compra_agent)

    shipped_lot = mark_lot_shipped(LOTS_PATH, lot_id)
    for item in shipped_lot["items"]:
        shipment = build_internal_shipment(
            item,
            selected,
            total_lot_weight=shipped_lot["total_weight"],
        )
        invoice = pla_producte_sha_enviat(shipment)
        _notify_compra(
            build_confirmacio_enviament,
            item,
            _build_item_offer(shipped_lot, item),
            compra_agent,
            invoice=invoice,
        )

    return load_lot_by_id(LOTS_PATH, lot_id)


def trigger_ready_lot_negotiation(lot_id, asynchronous=True):
    if asynchronous:
        thread = threading.Thread(target=process_ready_lot, args=(lot_id,), daemon=True)
        thread.start()
        return thread
    return process_ready_lot(lot_id)


def pla_localitzacio_acl(gm, content, sender):
    request_data = parse_productes_localitzats(gm, content)
    lot = pla_assignar_producte_a_lot(request_data)
    gr = build_confirmacio_localitzacio(
        request_data,
        lot,
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )
    if lot.get("ready_for_negotiation") and AUTO_TRIGGER_READY_LOTS:
        trigger_ready_lot_negotiation(lot["lot_id"], asynchronous=True)
    return gr


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacio del centre logistic.
    """
    global mss_cnt

    print("INFO AgenteCentreLogistic => Peticio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")

    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO AgenteCentreLogistic => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        if perf != ACL.request:
            gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
            print("INFO AgenteCentreLogistic => No es una request FIPA ACL")
        else:
            content = msgdic["content"]
            accion = gm.value(subject=content, predicate=RDF.type)
            print("INFO AgenteCentreLogistic => Accio %s" % accion)
            try:
                gr = pla_localitzacio_acl(gm, content, msgdic.get("sender"))
            except Exception as exc:
                logger.error("Error processant localitzacio: %s", exc)
                gr = build_message(
                    Graph(),
                    ACL.failure,
                    sender=AGENT.uri,
                    receiver=msgdic.get("sender"),
                    msgcnt=mss_cnt,
                )

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/iface")
def browser_iface():
    lots = list_all_lots(LOTS_PATH)
    return render_template(
        "centre_logistic.html",
        centre_id=CENTRE_ID,
        centre_city=CENTRE_CITY,
        lots=lots,
    )


@app.route("/cron/negotiate-ready-lots")
def negotiate_ready_lots():
    ready_lots = list_ready_lots_for_negotiation(
        LOTS_PATH,
        delivery_window_days=READY_DELIVERY_WINDOW_DAYS,
    )
    processed = 0
    for lot in ready_lots:
        if trigger_ready_lot_negotiation(lot["lot_id"], asynchronous=False) is not None:
            processed += 1
    return f"Processed {processed} ready lot(s)"


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["centre_logistic"])
    add_directory_arguments(parser)
    parser.add_argument("--centre-id", default="CL-BCN")
    parser.add_argument("--centre-city", default="Barcelona")
    add_data_dir_argument(parser)
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {
            "agent": build_agent(
                f"CentreLogisticAgent-{args.centre_id}",
                format_centre_uri_name(args.centre_id),
                args.port,
                host=publish_host,
            ),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
            "centre_id": args.centre_id,
            "centre_city": args.centre_city,
            "transport_agents": [],
        }
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(
        app,
        bind_host,
        args.port,
        register_fn=lambda: register_with_directory(
            AGENT,
            DirectoryAgent,
            DSO.CentreLogisticAgent,
            0,
            metadata={
                AZON.IdCentreLogistic: args.centre_id,
                AZON.Ciutat: args.centre_city,
            },
        ),
    )
