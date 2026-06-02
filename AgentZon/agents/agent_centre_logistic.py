"""Agent centre logístic: lots, negociació amb transportistes i cobrament intern."""

import argparse
from pathlib import Path
import threading

from flask import Flask, request
from rdflib import Graph

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
    add_data_dir_argument,
    add_directory_arguments,
    add_runtime_arguments,
    build_agent,
    build_directory_agent,
    register_with_directory,
    resolve_runtime_hostname,
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
from protocols.directory import parse_directory_response
from protocols.pagament import build_peticio_cobrament_intern, extract_confirmacio_pagament
from services.agent_common_service import resolve_agent_via_directory, resolve_agents_via_directory
from services.logistics_service import (
    assign_transport_to_lot,
    build_counter_offer_price,
    build_internal_shipment,
    choose_winning_offer,
    create_lot,
    format_centre_uri_name,
    list_ready_lots_for_negotiation,
    load_lot_by_id,
    mark_lot_negotiating,
    mark_lot_shipped,
    match_transport_agent,
    query_transport_offers,
)
from services.rdf_store import load_graph


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_AGENT = None
MESSAGE_SENDER = send_message
TRANSPORT_AGENTS = []
LOTS_PATH = None
CENTRE_ID = None
CENTRE_CITY = None
COUNTER = 0
AUTO_TRIGGER_READY_LOTS = True


# Runtime configuration ------------------------------------------------------------
def configure_runtime(settings, message_sender=send_message):
    """Inicialitza configuració de centre, paths i dependències."""
    global AGENT, DIRECTORY_AGENT, MESSAGE_SENDER, TRANSPORT_AGENTS, LOTS_PATH, CENTRE_ID, CENTRE_CITY, COUNTER, AUTO_TRIGGER_READY_LOTS
    AGENT = settings["agent"]
    DIRECTORY_AGENT = settings.get("directory_agent")
    MESSAGE_SENDER = message_sender
    TRANSPORT_AGENTS = settings["transport_agents"]
    CENTRE_ID = settings.get("centre_id")
    CENTRE_CITY = settings.get("centre_city")
    AUTO_TRIGGER_READY_LOTS = settings.get("auto_trigger_ready_lots", True)
    lots_filename = f"lots-{CENTRE_ID}.ttl" if CENTRE_ID else "lots.ttl"
    LOTS_PATH = Path(settings["data_dir"]) / lots_filename
    COUNTER = 0


def next_counter():
    """Retorna un identificador incremental per a `msgcnt`."""
    global COUNTER
    current = COUNTER
    COUNTER += 1
    return current


def _shipment_scope_texts(shipment):
    product_ids = shipment.get("product_ids", [])
    lot_id = shipment.get("lot_id")
    if len(product_ids) == 1:
        base = f"producte {product_ids[0]}"
        return (
            f"S'ha enviat el {base} del lot {lot_id}" if lot_id else f"S'ha enviat el {base}",
            f"al {base} del lot {lot_id}" if lot_id else f"al {base}",
        )
    elif product_ids:
        base = "productes {}".format(", ".join(product_ids))
        return (
            f"S'han enviat els {base} del lot {lot_id}" if lot_id else f"S'han enviat els {base}",
            f"als {base} del lot {lot_id}" if lot_id else f"als {base}",
        )
    else:
        if lot_id:
            return (f"S'ha enviat el lot {lot_id}", f"al lot {lot_id}")
        order_id = shipment["order_id"]
        return (f"S'ha enviat la comanda {order_id}", f"a la comanda {order_id}")


# Plans ----------------------------------------------------------------------------
def pla_assignar_producte_a_lot(request_data):
    """Pla de magatzem: assigna productes de comanda a un lot."""
    centre_id = request_data.get("centre_id") or CENTRE_ID
    logger.info(
        "Processant %d productes al centre %s (desti=%s, data=%s)",
        len(request_data["products"]),
        centre_id,
        request_data["city"],
        request_data["delivery_date"],
    )
    lot = create_lot(
        LOTS_PATH,
        request_data["order_id"],
        request_data["city"],
        request_data["delivery_date"],
        request_data["products"],
        centre_id=centre_id,
        centre_city=request_data.get("centre_city") or CENTRE_CITY,
        user_id=request_data.get("user_id"),
    )
    action = "Creat" if lot["created_new_lot"] else "Reutilitzat"
    logger.info(
        "%s lot %s al centre %s (pes_total=%.2f)",
        action,
        lot["lot_id"],
        centre_id,
        lot["total_weight"],
    )
    for product in request_data["products"]:
        logger.info(
            "Assignat producte %s al lot %s",
            product["product_id"],
            lot["lot_id"],
        )
    return lot


def resolve_transport_agents():
    """Resol transportistes disponibles (cache local o directori)."""
    if TRANSPORT_AGENTS:
        return TRANSPORT_AGENTS
    if DIRECTORY_AGENT is None:
        return []

    entries = resolve_agents_via_directory(
        AGENT,
        DIRECTORY_AGENT,
        MESSAGE_SENDER,
        next_counter,
        DSO.TransportistaAgent,
    )
    return [
        Agent(
            name=entry["name"],
            uri=entry["uri"],
            address=entry["address"],
            stop="",
        )
        for entry in entries
    ]


def pla_cerca_de_transportista(lot):
    """Pla de negociació: recull ofertes inicials dels transportistes."""
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
            message, _ = build_peticio_transport(
                lot,
                sender=AGENT.uri,
                receiver=transport_agent.uri,
                msgcnt=next_counter(),
            )
            return extract_transport_offer(MESSAGE_SENDER(message, transport_agent.address))
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
    """Pla de negociació: envia contraoferta i recull respostes."""
    counter_price = build_counter_offer_price(offers)
    logger.info(
        "Contraoferta comuna per al lot %s: %.2f EUR",
        lot["lot_id"],
        counter_price,
    )
    negotiated_offers = []
    for offer in offers:
        transport_agent = match_transport_agent(transport_agents, offer["transport_id"])
        message = build_contraoferta_transport(
            lot,
            offer,
            new_price=counter_price,
            sender=AGENT.uri,
            receiver=transport_agent.uri,
            msgcnt=next_counter(),
        )
        reply = MESSAGE_SENDER(message, transport_agent.address)
        performative = get_message_properties(reply).get("performative")
        if performative == ACL.agree:
            logger.info(
                "Resposta a la contraoferta del lot %s per %s: acceptada a %.2f EUR",
                lot["lot_id"],
                offer["transport_id"],
                counter_price,
            )
            negotiated_offers.append({**offer, "price": counter_price})
        elif performative == ACL.propose:
            negotiated_offer = extract_transport_offer(reply)
            logger.info(
                "Resposta a la contraoferta del lot %s per %s: nova proposta de %.2f EUR amb entrega %s",
                lot["lot_id"],
                offer["transport_id"],
                negotiated_offer["price"],
                negotiated_offer["delivery_date"],
            )
            negotiated_offers.append(negotiated_offer)
        else:
            logger.info(
                "Resposta a la contraoferta del lot %s per %s: rebutjada",
                lot["lot_id"],
                offer["transport_id"],
            )
    return negotiated_offers


def pla_de_transportista_escollit(lot, transport_agents, initial_offers, negotiated_offers, request_content=None):
    """Pla de selecció: tria guanyador i notifica acceptacions/rebuigs."""
    selected = choose_winning_offer(initial_offers, negotiated_offers)
    source = "negociada" if negotiated_offers else "inicial"
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
                msgcnt=next_counter(),
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
                msgcnt=next_counter(),
            )
            logger.info(
                "Notificant rebuig al transportista %s per al lot %s",
                transport_id,
                lot["lot_id"],
            )
        MESSAGE_SENDER(message, transport_agent.address)
    return selected


def pla_producte_sha_enviat(shipment):
    """Pla post-enviament: notifica cobrament intern al Cobrador."""
    if DIRECTORY_AGENT is None:
        return None
    try:
        cobrador = parse_directory_response(
            MESSAGE_SENDER(
                build_search_message(AGENT, DSO.CobradorAgent, DIRECTORY_AGENT, msgcnt=next_counter()),
                DIRECTORY_AGENT.address,
            )
        )
    except Exception:
        logger.warning("No s'ha pogut resoldre el Cobrador; s'omet el cobrament intern")
        return None
    sent_text, payment_target = _shipment_scope_texts(shipment)
    logger.info("%s; demanant cobrament intern al Cobrador", sent_text)
    message = build_peticio_cobrament_intern(
        shipment,
        sender=AGENT.uri,
        receiver=cobrador.uri,
        msgcnt=next_counter(),
    )
    try:
        confirmation = extract_confirmacio_pagament(MESSAGE_SENDER(message, cobrador.address))
    except Exception:
        logger.warning("El cobrament intern per %s no s'ha pogut completar", payment_target)
        return None
    if not confirmation.get("payment_id"):
        logger.warning("El Cobrador no ha retornat una factura per %s", payment_target)
        return None
    logger.info(
        "Cobrament intern confirmat per %s (pagament %s, %.2f EUR)",
        payment_target,
        confirmation["payment_id"],
        confirmation["amount"],
    )
    return confirmation


def resolve_compra_agent():
    if DIRECTORY_AGENT is None:
        return None
    try:
        return resolve_agent_via_directory(
            AGENT,
            DIRECTORY_AGENT,
            MESSAGE_SENDER,
            next_counter,
            DSO.CompraAgent,
        )
    except Exception:
        logger.warning("No s'ha pogut resoldre l'Agent Compra per enviar actualitzacions d'enviament")
        return None


def _build_order_request_data(lot, reservation):
    return {
        "order_id": reservation["order_id"],
        "user_id": reservation.get("user_id"),
        "city": reservation["city"],
        "delivery_date": reservation["delivery_date"],
        "products": reservation.get("products", []),
        "centre_id": lot.get("centre_id"),
        "centre_city": lot.get("centre_city"),
    }


def _build_reservation_offer(lot, reservation):
    return {
        "lot_id": lot["lot_id"],
        "order_id": reservation["order_id"],
        "transport_id": lot["transport_id"],
        "transport_name": lot["transport_name"],
        "city": reservation["city"],
        "delivery_date": lot["official_delivery_date"],
        "price": reservation.get("price", lot["price"]),
    }


def _notify_compra(message_builder, lot, reservation, compra_agent, invoice=None):
    if compra_agent is None:
        return
    request_data = _build_order_request_data(lot, reservation)
    offer = _build_reservation_offer(lot, reservation)
    if invoice is None:
        message = message_builder(
            request_data,
            offer,
            sender=AGENT.uri,
            receiver=compra_agent.uri,
            msgcnt=next_counter(),
        )
    else:
        message = message_builder(
            request_data,
            offer,
            sender=AGENT.uri,
            receiver=compra_agent.uri,
            invoice=invoice,
            msgcnt=next_counter(),
        )
    MESSAGE_SENDER(message, compra_agent.address)


def process_ready_lot(lot_id):
    """Executa el flux complet d'un lot preparat fins a enviament."""
    lot = mark_lot_negotiating(LOTS_PATH, lot_id)
    if lot is None:
        return None

    transport_agents, offers = pla_cerca_de_transportista(lot)
    negotiated_offers = pla_negociar_contraoferta(lot, transport_agents, offers)
    selected = pla_de_transportista_escollit(lot, transport_agents, offers, negotiated_offers)
    assigned_lot = assign_transport_to_lot(LOTS_PATH, lot_id, selected)
    compra_agent = resolve_compra_agent()

    for reservation in assigned_lot["reservations"]:
        _notify_compra(build_dades_enviament, assigned_lot, reservation, compra_agent)

    shipped_lot = mark_lot_shipped(LOTS_PATH, lot_id)
    for reservation in shipped_lot["reservations"]:
        shipment = build_internal_shipment(
            reservation,
            selected,
            total_lot_weight=shipped_lot["total_weight"],
        )
        invoice = pla_producte_sha_enviat(shipment)
        _notify_compra(build_confirmacio_enviament, shipped_lot, reservation, compra_agent, invoice=invoice)

    return load_lot_by_id(LOTS_PATH, lot_id)


def trigger_ready_lot_negotiation(lot_id, asynchronous=True):
    """Activa negociació de lot en segon pla o en mode síncron."""
    if asynchronous:
        thread = threading.Thread(target=process_ready_lot, args=(lot_id,), daemon=True)
        thread.start()
        return thread
    return process_ready_lot(lot_id)


# Communication handling -----------------------------------------------------------
@app.route("/comm")
def comm():
    """Entrada ACL del centre: rep productes localitzats i respon confirmació."""
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
    request_data = parse_productes_localitzats(message_graph, content)
    try:
        lot = pla_assignar_producte_a_lot(request_data)
        response = build_confirmacio_localitzacio(
            request_data,
            lot,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            request_content=content,
            msgcnt=next_counter(),
        )
        if lot.get("ready_for_negotiation") and AUTO_TRIGGER_READY_LOTS:
            trigger_ready_lot_negotiation(lot["lot_id"], asynchronous=True)
        return response.serialize(format="xml")
    except Exception as exc:
        logger.error("Error processant la comanda %s: %s", request_data.get("order_id"), exc)
        return build_message(
            Graph(),
            ACL.failure,
            sender=AGENT.uri,
            receiver=properties.get("sender"),
            msgcnt=next_counter(),
        ).serialize(format="xml")


@app.route("/iface")
def iface():
    """Vista tècnica del centre: exporta l'estat de lots en Turtle."""
    return load_graph(LOTS_PATH).serialize(format="turtle")


@app.route("/cron/negotiate-ready-lots")
def negotiate_ready_lots():
    """Cron manual per negociar lots preparats o imminents."""
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
    """Atura el servidor Flask de l'agent."""
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    """Punt d'entrada executable de l'Agent Centre Logístic."""
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["centre_logistic"])
    add_directory_arguments(parser)
    parser.add_argument("--centre-id", default="CL-BCN")
    parser.add_argument("--centre-city", default="Barcelona")
    add_data_dir_argument(parser)
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {
            "agent": build_agent(
                f"CentreLogisticAgent-{args.centre_id}",
                format_centre_uri_name(args.centre_id),
                args.port,
                host=hostname,
            ),
            "directory_agent": build_directory_agent(args.directory_host, args.directory_port),
            "data_dir": Path(args.data_dir),
            "centre_id": args.centre_id,
            "centre_city": args.centre_city,
            "transport_agents": [],
        }
    )
    directory = build_directory_agent(args.directory_host, args.directory_port)
    logger.info("Iniciant %s a %s:%s", AGENT.name, hostname, args.port)
    serve_agent(
        app,
        hostname,
        args.port,
        register_fn=lambda: register_with_directory(
            AGENT,
            directory,
            DSO.CentreLogisticAgent,
            0,
            metadata={
                AZON.IdCentreLogistic: args.centre_id,
                AZON.Ciutat: args.centre_city,
            },
        ),
    )


if __name__ == "__main__":
    main()
