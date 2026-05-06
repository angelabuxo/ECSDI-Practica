"""Directory agent that registers and resolves AgentZon services."""

import argparse
from threading import Lock

from flask import Flask, request
from rdflib import Graph, RDF
from rdflib.namespace import FOAF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.AgentUtil.Logging import config_logger
from AgentZon.AgentUtil.OntoNamespaces import bind_namespaces
from AgentZon.config import (
    DEFAULT_PORTS,
    add_runtime_arguments,
    build_agent,
    resolve_runtime_hostname,
)


app = Flask(__name__)
logger = config_logger(level=1)

# Agent attributes -----------------------------------------------------------------
AGENT = None
DIRECTORY_GRAPH = None
COUNTER = 0
COUNTER_LOCK = Lock()


# Runtime configuration ------------------------------------------------------------
def _new_directory_graph():
    graph = Graph()
    bind_namespaces(graph)
    graph.bind("foaf", FOAF)
    graph.bind("dso", DSO)
    return graph


def configure_runtime(settings):
    global AGENT, DIRECTORY_GRAPH, COUNTER
    AGENT = settings["agent"]
    DIRECTORY_GRAPH = _new_directory_graph()
    COUNTER = 0


def next_counter():
    global COUNTER
    with COUNTER_LOCK:
        current = COUNTER
        COUNTER += 1
        return current


# Directory logic ------------------------------------------------------------------
def process_register(message_graph, content):
    address = message_graph.value(content, DSO.Address)
    name = message_graph.value(content, FOAF.name)
    uri = message_graph.value(content, DSO.Uri)
    agent_type = message_graph.value(content, DSO.AgentType)

    DIRECTORY_GRAPH.add((uri, RDF.type, FOAF.Agent))
    DIRECTORY_GRAPH.add((uri, FOAF.name, name))
    DIRECTORY_GRAPH.add((uri, DSO.Address, address))
    DIRECTORY_GRAPH.add((uri, DSO.AgentType, agent_type))
    logger.info("Registered agent %s (%s) at %s", name, agent_type, address)

    return build_message(
        Graph(),
        ACL.confirm,
        sender=AGENT.uri,
        receiver=uri,
        msgcnt=next_counter(),
    )


def process_search(message_graph, content, requester):
    agent_type = message_graph.value(content, DSO.AgentType)
    logger.info("Directory search requested for agent type %s", agent_type)
    for uri, _, _ in DIRECTORY_GRAPH.triples((None, DSO.AgentType, agent_type)):
        address = DIRECTORY_GRAPH.value(uri, DSO.Address)
        name = DIRECTORY_GRAPH.value(uri, FOAF.name)
        reply = Graph()
        bind_namespaces(reply)
        reply.bind("foaf", FOAF)
        reply.bind("dso", DSO)
        payload = AGENT.uri + "#directory-response"
        reply.add((payload, DSO.Address, address))
        reply.add((payload, DSO.Uri, uri))
        reply.add((payload, FOAF.name, name))
        return build_message(
            reply,
            ACL.inform,
            sender=AGENT.uri,
            receiver=requester,
            content=payload,
            msgcnt=next_counter(),
        )

    return build_message(
        Graph(),
        ACL.inform,
        sender=AGENT.uri,
        receiver=requester,
        msgcnt=next_counter(),
    )


# Communication handling -----------------------------------------------------------
@app.route("/Register")
def register():
    message_graph = Graph()
    message_graph.parse(data=request.args["content"], format="xml")
    properties = get_message_properties(message_graph)
    if not properties or properties.get("performative") != ACL.request:
        logger.warning("Received non-request or malformed message in /Register")
        return build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        ).serialize(format="xml")

    content = properties["content"]
    action = message_graph.value(content, RDF.type)
    if action == DSO.Register:
        response = process_register(message_graph, content)
    elif action == DSO.Search:
        response = process_search(message_graph, content, properties.get("sender"))
    else:
        response = build_message(
            Graph(),
            ACL["not-understood"],
            sender=AGENT.uri,
            msgcnt=next_counter(),
        )
    return response.serialize(format="xml")


# Inspection endpoints -------------------------------------------------------------
@app.route("/info")
def info():
    return DIRECTORY_GRAPH.serialize(format="turtle")


@app.route("/stop")
def stop():
    shutdown_server()
    return "Stopping"


# Bootstrap -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["directory"])
    args = parser.parse_args()
    hostname = resolve_runtime_hostname(args)

    configure_runtime(
        {"agent": build_agent("DirectoryAgent", "Directory", args.port, host=hostname, endpoint="/Register")}
    )
    logger.info("Starting %s on %s:%s", AGENT.name, hostname, args.port)
    app.run(host=hostname, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
