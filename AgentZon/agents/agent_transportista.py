import argparse
from datetime import date, timedelta

from flask import Flask, request
from rdflib import Graph, RDF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.AgentUtil.OntoNamespaces import bind_namespaces
from AgentZon.config import DEFAULT_PORTS, build_agent
from AgentZon.domain import TransportOffer
from AgentZon.protocols.centre_logistic import (
    build_resposta_oferta_transport,
    parse_peticio_transport,
)


class TransportistaAgent:
    def __init__(self, agent, transport_id, price_per_kg, delivery_days):
        self.agent = agent
        self.transport_id = transport_id
        self.price_per_kg = price_per_kg
        self.delivery_days = delivery_days
        self.counter = 0

    def next_counter(self):
        current = self.counter
        self.counter += 1
        return current

    def generar_oferta_transport(self, request_data):
        delivery_date = (date.today() + timedelta(days=self.delivery_days)).isoformat()
        return TransportOffer(
            lot_id=request_data["lot_id"],
            transport_id=self.transport_id,
            transport_name=self.agent.name,
            city=request_data["city"],
            delivery_date=delivery_date,
            price=round(request_data["weight"] * self.price_per_kg, 2),
        )


def create_app(settings):
    service = TransportistaAgent(
        settings["agent"],
        settings["transport_id"],
        settings["price_per_kg"],
        settings["delivery_days"],
    )
    app = Flask(__name__)

    @app.route("/comm")
    def comm():
        gm = Graph()
        gm.parse(data=request.args["content"], format="xml")
        props = get_message_properties(gm)
        if not props or props.get("performative") != ACL.request:
            return build_message(Graph(), ACL["not-understood"], sender=service.agent.uri, msgcnt=service.next_counter()).serialize(format="xml")
        content = props["content"]
        action = gm.value(content, RDF.type)
        if action is None:
            return build_message(Graph(), ACL["not-understood"], sender=service.agent.uri, msgcnt=service.next_counter()).serialize(format="xml")
        request_data = parse_peticio_transport(gm, content)
        offer = service.generar_oferta_transport(request_data)
        response = build_resposta_oferta_transport(
            offer,
            sender=service.agent.uri,
            receiver=props.get("sender"),
            msgcnt=service.next_counter(),
        )
        return response.serialize(format="xml")

    @app.route("/info")
    def info():
        graph = Graph()
        bind_namespaces(graph)
        return graph.serialize(format="turtle")

    @app.route("/stop")
    def stop():
        shutdown_server()
        return "Stopping"

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORTS["transport_fast"])
    parser.add_argument("--transport-id", default="fast")
    parser.add_argument("--price-per-kg", type=float, default=8.0)
    parser.add_argument("--delivery-days", type=int, default=1)
    args = parser.parse_args()

    agent = build_agent(f"Transportista-{args.transport_id}", f"Transport{args.transport_id.title()}", args.port, host=args.host)
    app = create_app(
        {
            "agent": agent,
            "transport_id": args.transport_id,
            "price_per_kg": args.price_per_kg,
            "delivery_days": args.delivery_days,
        }
    )
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
