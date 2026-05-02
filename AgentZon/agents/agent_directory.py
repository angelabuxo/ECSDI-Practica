import argparse
from typing import Dict, Optional

from flask import Flask, Response, request
from rdflib import Graph, Literal, RDF, URIRef

from AgentZon.agents.logging_utils import configure_pretty_logging
from AgentZon.config import AGENTZON
from AgentZon.protocols.directory import (
    DSO,
    build_directory_response,
    build_directory_responses,
    read_directory_response,
)
from AgentZon.protocols.fipa_acl import build_message, build_not_understood, get_message_properties, parse_message


class AgentDirectory:
    """Servei de registre i descobriment d'agents seguint el patró del LabDoc."""

    def __init__(self):
        self.uri = URIRef(f"{AGENTZON}directory_agent")
        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self.graph.bind("dso", DSO)

    def register_agent(self, name: str, uri: URIRef, address: str, agent_type: str) -> None:
        subject = URIRef(f"{AGENTZON}directory_entry_{name}")
        self.graph.remove((subject, None, None))
        self.graph.add((subject, RDF.type, DSO.RegisteredAgent))
        self.graph.add((subject, DSO.Name, Literal(name)))
        self.graph.add((subject, DSO.Uri, uri))
        self.graph.add((subject, DSO.Address, Literal(address)))
        self.graph.add((subject, DSO.AgentType, Literal(agent_type)))

    def search_agent(self, agent_type: str, name: Optional[str] = None) -> Optional[Dict[str, object]]:
        results = self.search_agents(agent_type=agent_type, name=name)
        return results[0] if results else None

    def search_agents(self, agent_type: str, name: Optional[str] = None) -> list[Dict[str, object]]:
        results = []
        for subject in self.graph.subjects(RDF.type, DSO.RegisteredAgent):
            current_type = self.graph.value(subject, DSO.AgentType)
            current_name = self.graph.value(subject, DSO.Name)
            if str(current_type) != agent_type:
                continue
            if name is not None and str(current_name) != name:
                continue
            results.append(
                {
                    "name": str(current_name),
                    "uri": self.graph.value(subject, DSO.Uri),
                    "address": str(self.graph.value(subject, DSO.Address)),
                    "agent_type": str(current_type),
                }
            )
        return results

    def process_message(self, message: Graph) -> Graph:
        props = get_message_properties(message)
        if not props or props.get("performative") != "request" or props.get("content") is None:
            return build_not_understood(self.uri, AGENTZON.unknown_agent, msgcnt=0)

        action = props["content"]
        sender = props.get("sender") or AGENTZON.unknown_agent

        if (action, RDF.type, DSO.Register) in message:
            data = read_directory_response(message, action)
            self.register_agent(
                name=data["name"],
                uri=data["uri"],
                address=data["address"],
                agent_type=data["agent_type"],
            )
            return build_message("confirm", self.uri, sender, None, msgcnt=1)

        if (action, RDF.type, DSO.Search) in message:
            agent_type = message.value(action, DSO.AgentType)
            name = message.value(action, DSO.Name)
            if agent_type is None:
                return build_not_understood(self.uri, sender, msgcnt=1)

            results = self.search_agents(agent_type=str(agent_type), name=str(name) if name is not None else None)
            if not results:
                return build_not_understood(self.uri, sender, msgcnt=1)

            content = build_directory_responses(results)
            return build_message("inform", self.uri, sender, content, msgcnt=1)

        return build_not_understood(self.uri, sender, msgcnt=1)


def create_app(directory_agent: Optional[AgentDirectory] = None) -> Flask:
    app = Flask(__name__)
    directory_agent = directory_agent or AgentDirectory()

    @app.route("/Register", methods=["GET"])
    def register():
        try:
            incoming = parse_message(request.args.get("content", ""))
            response = directory_agent.process_message(incoming)
        except Exception:
            response = build_not_understood(directory_agent.uri, AGENTZON.unknown_agent, msgcnt=0)
        return Response(response.serialize(format="xml"), mimetype="application/rdf+xml")

    @app.route("/Info", methods=["GET"])
    def info():
        return Response(directory_agent.graph.serialize(format="turtle"), mimetype="text/turtle")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentZon DirectoryAgent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    configure_pretty_logging()
    create_app().run(host=args.host, port=args.port, debug=True)
