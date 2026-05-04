import argparse
import sys
from typing import Optional

from flask import Flask, Response, request
from rdflib import Graph, Literal, RDF

from AgentZon.agents.logging_utils import configure_pretty_logging
from AgentZon.config import AGENTZON
from AgentZon.protocols.centre_logistic import (
    build_resposta_oferta_transport_action,
    get_resposta_oferta_transport_subject,
    read_peticio_transport,
    sumar_dies_iso,
)
from AgentZon.protocols.directory import build_register_action
from AgentZon.protocols.fipa_acl import build_message, build_not_understood, get_message_properties, parse_message
from AgentZon.protocols.fipa_acl import send_message as http_send_message


class AgentTransportista:
    """Agent extern de transport que respon ofertes per lots logístics."""

    def __init__(self, transportista_id: str, cost_base: float, dies_extra: int, address: str):
        self.transportista_id = transportista_id
        self.cost_base = cost_base
        self.dies_extra = dies_extra
        self.address = address
        self.uri = AGENTZON[f"agent_{transportista_id}"]
        self.estat = Graph()
        self.estat.bind("az", AGENTZON)
        self.estat.add((self.uri, RDF.type, AGENTZON.Transportista))
        self.estat.add((self.uri, AGENTZON.Id, Literal(self.transportista_id)))

    def preparar_oferta(self, peticio: dict) -> dict:
        return {
            "id_lot": "",
            "transportista_id": self.transportista_id,
            "cost": round(self.cost_base + float(peticio["pes"]), 2),
            "data_enviament": sumar_dies_iso(peticio["data_enviament"], self.dies_extra),
        }

    def registrar_al_directori(self, directory_address: str, message_sender=http_send_message) -> dict:
        content = build_register_action(
            name=self.transportista_id,
            uri=self.uri,
            address=self.address,
            agent_type="AgentTransportista",
        )
        message = build_message("request", self.uri, AGENTZON.directory_agent, content, msgcnt=1)
        response = message_sender(directory_address, message)
        return get_message_properties(response)


def create_app(transportista: Optional[AgentTransportista] = None) -> Flask:
    transportista = transportista or AgentTransportista(
        transportista_id="transport-a",
        cost_base=5.0,
        dies_extra=0,
        address="http://127.0.0.1:9011/comm",
    )
    app = Flask(__name__)

    @app.route("/comm", methods=["GET"])
    def comm():
        try:
            incoming = parse_message(request.args.get("content", ""))
            props = get_message_properties(incoming)
            if not props or props.get("performative") != "request" or props.get("content") is None:
                response = build_not_understood(transportista.uri, AGENTZON.unknown_agent, msgcnt=1)
            elif (props["content"], RDF.type, AGENTZON.PeticioTransport) in incoming:
                peticio_subj = props["content"]
                peticio = read_peticio_transport(incoming, peticio_subj)
                transportista.estat.add((transportista.uri, AGENTZON.RepUna, peticio_subj))
                for triple in incoming.triples((peticio_subj, None, None)):
                    transportista.estat.add(triple)

                oferta = transportista.preparar_oferta(peticio)
                oferta_graph = build_resposta_oferta_transport_action(oferta)
                oferta_subj = get_resposta_oferta_transport_subject(oferta_graph)

                transportista.estat.add((transportista.uri, AGENTZON.Genera, oferta_subj))
                for triple in oferta_graph:
                    transportista.estat.add(triple)

                oferta_graph.add((transportista.uri, AGENTZON.RepUna, peticio_subj))
                oferta_graph.add((transportista.uri, AGENTZON.Genera, oferta_subj))
                response = build_message(
                    "inform",
                    transportista.uri,
                    props.get("sender", AGENTZON.unknown_agent),
                    oferta_graph,
                    msgcnt=1,
                )
            else:
                response = build_not_understood(
                    transportista.uri,
                    props.get("sender", AGENTZON.unknown_agent),
                    msgcnt=1,
                )
        except Exception:
            response = build_not_understood(transportista.uri, AGENTZON.unknown_agent, msgcnt=1)

        return Response(response.serialize(format="xml"), mimetype="application/rdf+xml")

    @app.route("/Info", methods=["GET"])
    def info():
        return Response(transportista.estat.serialize(format="turtle"), mimetype="text/turtle")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentZon Agent Transportista")
    parser.add_argument("--id", default="transport-a")
    parser.add_argument("--cost-base", type=float, default=5.0)
    parser.add_argument("--dies-extra", type=int, default=0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9011)
    parser.add_argument("--directory", default="http://127.0.0.1:9000/Register")
    parser.add_argument("--address", default=None)
    args = parser.parse_args()

    configure_pretty_logging()
    advertised_address = args.address or f"http://127.0.0.1:{args.port}/comm"
    agent = AgentTransportista(
        transportista_id=args.id,
        cost_base=args.cost_base,
        dies_extra=args.dies_extra,
        address=advertised_address,
    )
    try:
        agent.registrar_al_directori(args.directory)
    except Exception as exc:
        print(f"Avís: no s'ha pogut registrar el transportista al directori: {exc}", file=sys.stderr)

    create_app(agent).run(host=args.host, port=args.port, debug=True)
