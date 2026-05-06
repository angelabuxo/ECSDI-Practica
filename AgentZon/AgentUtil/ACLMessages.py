"""Helpers for building, sending, and parsing FIPA-ACL messages.

@author: javier
"""

__author__ = "javier"

import requests
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, OWL, RDF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.Agent import Agent
from AgentZon.AgentUtil.DSO import DSO


AGN = Namespace("http://www.agentes.org#")


# Message creation -----------------------------------------------------------------
def build_message(gmess, perf, sender=None, receiver=None, content=None, msgcnt=0):
    mssid = f"message-{hash(sender)}-{msgcnt:04d}"
    ms = URIRef(mssid)
    gmess.bind("acl", ACL)
    gmess.add((ms, RDF.type, OWL.NamedIndividual))
    gmess.add((ms, RDF.type, ACL.FipaAclMessage))
    gmess.add((ms, ACL.performative, perf))
    if sender is not None:
        gmess.add((ms, ACL.sender, sender))
    if receiver is not None:
        gmess.add((ms, ACL.receiver, receiver))
    if content is not None:
        gmess.add((ms, ACL.content, content))
    return gmess


def send_message(gmess, address, timeout=10):
    payload = gmess.serialize(format="xml")
    response = requests.get(address, params={"content": payload}, timeout=timeout)
    response.raise_for_status()
    graph = Graph()
    graph.parse(data=response.text, format="xml")
    return graph


# Message parsing ------------------------------------------------------------------
def get_message_properties(msg):
    props = {
        "performative": ACL.performative,
        "sender": ACL.sender,
        "receiver": ACL.receiver,
        "ontology": ACL.ontology,
        "conversation-id": ACL["conversation-id"],
        "in-reply-to": ACL["in-reply-to"],
        "content": ACL.content,
    }

    message = msg.value(predicate=RDF.type, object=ACL.FipaAclMessage)
    if message is None:
        return {}

    data = {}
    for key, predicate in props.items():
        value = msg.value(subject=message, predicate=predicate)
        if value is not None:
            data[key] = value
    return data


# Directory-service helpers --------------------------------------------------------
def get_agent_info(agent_type, directory_agent, sender, msgcnt):
    gmess = Graph()
    gmess.bind("foaf", FOAF)
    gmess.bind("dso", DSO)
    ask_obj = AGN[f"{sender.name}-Search"]

    gmess.add((ask_obj, RDF.type, DSO.Search))
    gmess.add((ask_obj, DSO.AgentType, agent_type))
    response = send_message(
        build_message(
            gmess,
            perf=ACL.request,
            sender=sender.uri,
            receiver=directory_agent.uri,
            msgcnt=msgcnt,
            content=ask_obj,
        ),
        directory_agent.address,
    )
    properties = get_message_properties(response)
    content = properties["content"]

    return Agent(
        str(response.value(subject=content, predicate=FOAF.name)),
        response.value(subject=content, predicate=DSO.Uri),
        str(response.value(subject=content, predicate=DSO.Address)),
        "",
    )


def register_agent(origin_agent, directory_agent, agent_type, msgcnt):
    gmess = Graph()
    gmess.bind("foaf", FOAF)
    gmess.bind("dso", DSO)
    reg_obj = AGN[f"{origin_agent.name}-Register"]
    gmess.add((reg_obj, RDF.type, DSO.Register))
    gmess.add((reg_obj, DSO.Uri, origin_agent.uri))
    gmess.add((reg_obj, FOAF.name, Literal(origin_agent.name)))
    gmess.add((reg_obj, DSO.Address, Literal(origin_agent.address)))
    gmess.add((reg_obj, DSO.AgentType, agent_type))
    return send_message(
        build_message(
            gmess,
            perf=ACL.request,
            sender=origin_agent.uri,
            receiver=directory_agent.uri,
            content=reg_obj,
            msgcnt=msgcnt,
        ),
        directory_agent.address,
    )
