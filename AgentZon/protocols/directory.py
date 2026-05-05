from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import FOAF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.Agent import Agent
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.OntoNamespaces import AGN, bind_namespaces


def build_register_message(agent, agent_type, directory_agent, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    graph.bind("foaf", FOAF)
    graph.bind("dso", DSO)
    content = AGN[f"{agent.name}-register"]
    graph.add((content, RDF.type, DSO.Register))
    graph.add((content, DSO.Uri, agent.uri))
    graph.add((content, FOAF.name, Literal(agent.name)))
    graph.add((content, DSO.Address, Literal(agent.address)))
    graph.add((content, DSO.AgentType, agent_type))
    return build_message(
        graph,
        perf=ACL.request,
        sender=agent.uri,
        receiver=directory_agent.uri,
        content=content,
        msgcnt=msgcnt,
    )


def build_search_message(requester_agent, agent_type, directory_agent, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    graph.bind("dso", DSO)
    content = AGN[f"{requester_agent.name}-search"]
    graph.add((content, RDF.type, DSO.Search))
    graph.add((content, DSO.AgentType, agent_type))
    return build_message(
        graph,
        perf=ACL.request,
        sender=requester_agent.uri,
        receiver=directory_agent.uri,
        content=content,
        msgcnt=msgcnt,
    )


def parse_directory_response(graph):
    properties = get_message_properties(graph)
    content = properties.get("content")
    if content is None:
        raise ValueError("Directory response does not contain content")
    uri = graph.value(content, DSO.Uri)
    address = str(graph.value(content, DSO.Address))
    name = str(graph.value(content, FOAF.name, default=Literal("resolved-agent")))
    return Agent(name=name, uri=uri, address=address, stop="")
