import argparse
from pathlib import Path

from flask import Flask, request
from rdflib import Graph, RDF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.config import DATA_DIR, DEFAULT_PORTS, build_agent
from AgentZon.domain import OrderRecord, ProductRecord, UserShippingData
from AgentZon.protocols.compra import (
    build_confirmacio_registre_compra,
    parse_peticio_registre_compra,
)
from AgentZon.protocols.directory import build_register_message
from AgentZon.services.history_service import PurchaseHistoryService


class OpinadorAgent:
    def __init__(self, agent, data_dir):
        self.agent = agent
        self.history_service = PurchaseHistoryService(data_dir / "historial_compres.ttl")
        self.counter = 0

    def next_counter(self):
        current = self.counter
        self.counter += 1
        return current

    def pla_registre_de_compra(self, request_data):
        order = OrderRecord(
            order_id=request_data["order_id"],
            user_id=request_data["user_id"],
            user_name="history-user",
            products=[
                ProductRecord(
                    product_id=product_id,
                    name=product_id,
                    description="history-placeholder",
                    category="history",
                    brand="history",
                    price=0.0,
                    weight=0.0,
                )
                for product_id in request_data["product_ids"]
            ],
            shipping_data=UserShippingData(
                user_id=request_data["user_id"],
                user_name="history-user",
                street_address="",
                city="",
                priority="",
                payment_method="",
            ),
        )
        self.history_service.record_purchase(order)


def create_app(settings):
    service = OpinadorAgent(settings["agent"], settings["data_dir"])
    app = Flask(__name__)

    @app.route("/comm")
    def comm():
        gm = Graph()
        gm.parse(data=request.args["content"], format="xml")
        props = get_message_properties(gm)
        if not props or props.get("performative") != ACL.request:
            return build_message(Graph(), ACL["not-understood"], sender=service.agent.uri, msgcnt=service.next_counter()).serialize(format="xml")
        content = props["content"]
        request_data = parse_peticio_registre_compra(gm, content)
        service.pla_registre_de_compra(request_data)
        response = build_confirmacio_registre_compra(
            request_data["order_id"],
            sender=service.agent.uri,
            receiver=props.get("sender"),
            msgcnt=service.next_counter(),
        )
        return response.serialize(format="xml")

    @app.route("/info")
    def info():
        return service.history_service.store.load_graph().serialize(format="turtle")

    @app.route("/stop")
    def stop():
        shutdown_server()
        return "Stopping"

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORTS["opinador"])
    parser.add_argument("--directory-host", default="127.0.0.1")
    parser.add_argument("--directory-port", type=int, default=DEFAULT_PORTS["directory"])
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()

    agent = build_agent("OpinadorAgent", "Opinador", args.port, host=args.host)
    app = create_app({"agent": agent, "data_dir": Path(args.data_dir)})
    directory = build_agent("DirectoryAgent", "Directory", args.directory_port, host=args.directory_host, endpoint="/Register")
    register = build_register_message(agent, DSO.OpinadorAgent, directory, msgcnt=0)
    try:
        from AgentZon.AgentUtil.ACLMessages import send_message

        send_message(register, directory.address)
    except Exception:
        pass
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
