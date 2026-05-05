import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, request
from rdflib import Graph, RDF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.config import DATA_DIR, DEFAULT_PORTS, build_agent
from AgentZon.protocols.centre_logistic import (
    build_peticio_transport,
    build_shipping_details_response,
    extract_transport_offer,
    parse_productes_localitzats,
)
from AgentZon.protocols.directory import build_register_message
from AgentZon.services.logistics_service import LogisticsService


class CentreLogisticAgent:
    def __init__(self, agent, data_dir, transport_agents, message_sender=send_message):
        self.agent = agent
        self.transport_agents = transport_agents
        self.message_sender = message_sender
        self.logistics_service = LogisticsService(Path(data_dir) / "lots.ttl")
        self.counter = 0

    def next_counter(self):
        current = self.counter
        self.counter += 1
        return current

    def pla_assignar_producte_a_lot(self, request_data):
        return self.logistics_service.create_lot(
            request_data["order_id"],
            request_data["city"],
            request_data["priority"],
            request_data["products"],
        )

    def pla_cerca_de_transportista(self, lot):
        def query_transport(transport_agent):
            message, _ = build_peticio_transport(
                lot["lot_id"],
                lot["order_id"],
                lot["city"],
                lot["priority"],
                lot["total_weight"],
                sender=self.agent.uri,
                receiver=transport_agent.uri,
                msgcnt=self.next_counter(),
            )
            return extract_transport_offer(self.message_sender(message, transport_agent.address))

        with ThreadPoolExecutor(max_workers=len(self.transport_agents)) as executor:
            futures = [executor.submit(query_transport, agent) for agent in self.transport_agents]
            return [future.result() for future in futures]

    def pla_de_transportista_escollit(self, lot, offers, receiver):
        selected = self.logistics_service.choose_best_offer(offers)
        return build_shipping_details_response(
            lot["order_id"],
            lot["city"],
            selected,
            sender=self.agent.uri,
            receiver=receiver,
            msgcnt=self.next_counter(),
        )

    def pla_producte_sha_enviat(self):
        return None


def create_app(settings, message_sender=send_message):
    service = CentreLogisticAgent(
        settings["agent"],
        settings["data_dir"],
        settings["transport_agents"],
        message_sender=message_sender,
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
        request_data = parse_productes_localitzats(gm, content)
        lot = service.pla_assignar_producte_a_lot(request_data)
        offers = service.pla_cerca_de_transportista(lot)
        response = service.pla_de_transportista_escollit(lot, offers, props.get("sender"))
        return response.serialize(format="xml")

    @app.route("/info")
    def info():
        return service.logistics_service.store.load_graph().serialize(format="turtle")

    @app.route("/stop")
    def stop():
        shutdown_server()
        return "Stopping"

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORTS["centre_logistic"])
    parser.add_argument("--directory-host", default="127.0.0.1")
    parser.add_argument("--directory-port", type=int, default=DEFAULT_PORTS["directory"])
    parser.add_argument("--transport-fast-host", default="127.0.0.1")
    parser.add_argument("--transport-fast-port", type=int, default=DEFAULT_PORTS["transport_fast"])
    parser.add_argument("--transport-economy-host", default="127.0.0.1")
    parser.add_argument("--transport-economy-port", type=int, default=DEFAULT_PORTS["transport_economy"])
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()

    agent = build_agent("CentreLogisticAgent", "CentreLogistic", args.port, host=args.host)
    directory = build_agent("DirectoryAgent", "Directory", args.directory_port, host=args.directory_host, endpoint="/Register")
    fast = build_agent("Transportista-fast", "TransportFast", args.transport_fast_port, host=args.transport_fast_host)
    economy = build_agent("Transportista-economy", "TransportEconomy", args.transport_economy_port, host=args.transport_economy_host)
    app = create_app(
        {
            "agent": agent,
            "data_dir": Path(args.data_dir),
            "transport_agents": [fast, economy],
        }
    )
    try:
        send_message(build_register_message(agent, DSO.CentreLogisticAgent, directory, msgcnt=0), directory.address)
    except Exception:
        pass
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
