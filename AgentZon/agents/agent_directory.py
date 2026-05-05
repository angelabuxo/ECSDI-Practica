import argparse
from threading import Lock

from flask import Flask, request
from rdflib import Graph, Literal, RDF
from rdflib.namespace import FOAF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.AgentUtil.OntoNamespaces import bind_namespaces
from AgentZon.config import DEFAULT_PORTS, build_agent


class DirectoryAgentService:
    def __init__(self, agent):
        self.agent = agent
        self.graph = Graph()
        bind_namespaces(self.graph)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("dso", DSO)
        self._counter = 0
        self._lock = Lock()

    def next_counter(self):
        with self._lock:
            current = self._counter
            self._counter += 1
            return current

    def process_register(self, gm, content):
        address = gm.value(content, DSO.Address)
        name = gm.value(content, FOAF.name)
        uri = gm.value(content, DSO.Uri)
        agent_type = gm.value(content, DSO.AgentType)

        self.graph.add((uri, RDF.type, FOAF.Agent))
        self.graph.add((uri, FOAF.name, name))
        self.graph.add((uri, DSO.Address, address))
        self.graph.add((uri, DSO.AgentType, agent_type))

        return build_message(
            Graph(),
            ACL.confirm,
            sender=self.agent.uri,
            receiver=uri,
            msgcnt=self.next_counter(),
        )

    def process_search(self, gm, content):
        agent_type = gm.value(content, DSO.AgentType)
        for uri, _, _ in self.graph.triples((None, DSO.AgentType, agent_type)):
            address = self.graph.value(uri, DSO.Address)
            name = self.graph.value(uri, FOAF.name)
            reply = Graph()
            bind_namespaces(reply)
            reply.bind("foaf", FOAF)
            reply.bind("dso", DSO)
            payload = self.agent.uri + "#directory-response"
            reply.add((payload, DSO.Address, address))
            reply.add((payload, DSO.Uri, uri))
            reply.add((payload, FOAF.name, name))
            return build_message(
                reply,
                ACL.inform,
                sender=self.agent.uri,
                receiver=uri,
                content=payload,
                msgcnt=self.next_counter(),
            )

        return build_message(
            Graph(),
            ACL.inform,
            sender=self.agent.uri,
            msgcnt=self.next_counter(),
        )


def create_app(settings):
    agent = settings["agent"]
    service = DirectoryAgentService(agent)
    app = Flask(__name__)

    @app.route("/Register")
    def register():
        gm = Graph()
        gm.parse(data=request.args["content"], format="xml")
        props = get_message_properties(gm)
        if not props or props.get("performative") != ACL.request:
            return build_message(Graph(), ACL["not-understood"], sender=agent.uri, msgcnt=service.next_counter()).serialize(format="xml")
        content = props["content"]
        action = gm.value(content, RDF.type)
        if action == DSO.Register:
            response = service.process_register(gm, content)
        elif action == DSO.Search:
            response = service.process_search(gm, content)
        else:
            response = build_message(Graph(), ACL["not-understood"], sender=agent.uri, msgcnt=service.next_counter())
        return response.serialize(format="xml")

    @app.route("/info")
    def info():
        return service.graph.serialize(format="turtle")

    @app.route("/stop")
    def stop():
        shutdown_server()
        return "Stopping"

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORTS["directory"])
    args = parser.parse_args()

    agent = build_agent("DirectoryAgent", "Directory", args.port, host=args.host, endpoint="/Register")
    app = create_app({"agent": agent})
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
