# -*- coding: utf-8 -*-
"""
filename: agent_directory

Agent de directori AgentZon (registre i cerca d'agents).

/Register es la entrada per rebre missatges ACL de registre o cerca
/Info retorna el graf de directori en turtle
/Stop para l'agent
"""

import argparse

from flask import Flask, request
from rdflib import Graph, RDF
from rdflib.namespace import FOAF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.DSO import DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger
from AgentUtil.OntoNamespaces import bind_namespaces
from config import (
    DEFAULT_PORTS,
    add_runtime_arguments,
    build_agent,
    resolve_agent_hosts,
    serve_agent,
)

logger = config_logger(level=1)
app = Flask(__name__)

mss_cnt = 0
AGENT = None
dsgraph = None


def configure_runtime(settings):
    global AGENT, dsgraph, mss_cnt
    AGENT = settings["agent"]
    dsgraph = Graph()
    bind_namespaces(dsgraph)
    dsgraph.bind("foaf", FOAF)
    dsgraph.bind("dso", DSO)
    mss_cnt = 0


def process_register():
    logger.info("Peticio de registre")

    agn_add = gm.value(subject=content, predicate=DSO.Address)
    agn_name = gm.value(subject=content, predicate=FOAF.name)
    agn_uri = gm.value(subject=content, predicate=DSO.Uri)
    agn_type = gm.value(subject=content, predicate=DSO.AgentType)

    dsgraph.add((agn_uri, RDF.type, FOAF.Agent))
    dsgraph.add((agn_uri, FOAF.name, agn_name))
    for _, _, old_address in list(dsgraph.triples((agn_uri, DSO.Address, None))):
        dsgraph.remove((agn_uri, DSO.Address, old_address))
    dsgraph.add((agn_uri, DSO.Address, agn_add))
    dsgraph.add((agn_uri, DSO.AgentType, agn_type))
    dsgraph.add((agn_uri, DSO.Uri, agn_uri))
    for predicate, obj in gm.predicate_objects(agn_uri):
        dsgraph.add((agn_uri, predicate, obj))

    return build_message(
        Graph(),
        ACL.confirm,
        sender=AGENT.uri,
        receiver=agn_uri,
        msgcnt=mss_cnt,
    )


def process_search():
    agent_type = gm.value(subject=content, predicate=DSO.AgentType)
    logger.info("Cerca al directori pel tipus %s", agent_type)

    reply = Graph()
    bind_namespaces(reply)
    reply.bind("foaf", FOAF)
    reply.bind("dso", DSO)
    payload = AGENT.uri + "#directory-response"
    for uri, _, _ in dsgraph.triples((None, DSO.AgentType, agent_type)):
        for predicate, obj in dsgraph.predicate_objects(uri):
            reply.add((uri, predicate, obj))

    return build_message(
        reply,
        ACL.inform,
        sender=AGENT.uri,
        receiver=msgdic["sender"],
        content=payload,
        msgcnt=mss_cnt,
    )


@app.route("/Register")
def register():
    """
    Entry point del agente que recibe los mensajes de registro.
    """
    global mss_cnt, gm, content, msgdic

    print("INFO DirectoryAgent => Peticio rebuda\n")

    message = request.args["content"]
    gm = Graph()
    gm.parse(data=message, format="xml")

    msgdic = get_message_properties(gm)

    if msgdic is None:
        gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        print("INFO DirectoryAgent => El missatge no era un FIPA ACL")
    else:
        perf = msgdic["performative"]
        if perf != ACL.request:
            gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)
        else:
            content = msgdic["content"]
            accion = gm.value(subject=content, predicate=RDF.type)
            if accion == DSO.Register:
                gr = process_register()
            elif accion == DSO.Search:
                gr = process_search()
            else:
                gr = build_message(Graph(), ACL["not-understood"], sender=AGENT.uri, msgcnt=mss_cnt)

    mss_cnt += 1
    return gr.serialize(format="xml")


@app.route("/Info")
def info():
    return dsgraph.serialize(format="turtle")


@app.route("/Stop")
def stop():
    shutdown_server()
    return "Parando Servidor"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser, DEFAULT_PORTS["directory"])
    args = parser.parse_args()
    bind_host, publish_host = resolve_agent_hosts(args)

    configure_runtime(
        {"agent": build_agent("DirectoryAgent", "Directory", args.port, host=publish_host, endpoint="/Register")}
    )
    logger.info("Iniciant %s a %s:%s (publicat com a %s)", AGENT.name, bind_host, args.port, publish_host)
    serve_agent(app, bind_host, args.port)
