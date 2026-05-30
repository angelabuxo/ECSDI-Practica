"""Messages exchanged with the local directory service agent."""

from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import FOAF
from rdflib.term import Identifier

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.Agent import Agent
from AgentUtil.DSO import DSO
from AgentUtil.OntoNamespaces import AGN, AZON, bind_namespaces


# Directory requests ---------------------------------------------------------------
def _coerce_metadata_value(value):
    if isinstance(value, Identifier):
        return value
    return Literal(value)


def build_register_message(agent, agent_type, directory_agent, msgcnt=0, metadata=None):
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
    if metadata:
        for predicate, value in metadata.items():
            values = value if isinstance(value, (list, tuple, set)) else [value]
            for item in values:
                graph.add((agent.uri, predicate, _coerce_metadata_value(item)))
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


# Directory responses --------------------------------------------------------------
def parse_directory_responses(graph):
    _ = get_message_properties(graph)
    entries = []
    for uri in set(graph.subjects(DSO.AgentType, None)):
        entry = {
            "name": str(graph.value(uri, FOAF.name, default=Literal("resolved-agent"))),
            "uri": graph.value(uri, DSO.Uri, default=uri),
            "address": str(graph.value(uri, DSO.Address)),
            "agent_type": graph.value(uri, DSO.AgentType),
        }
        centre_id = graph.value(uri, AZON.IdCentreLogistic)
        centre_city = graph.value(uri, AZON.Ciutat)
        if centre_id is not None:
            entry["centre_id"] = str(centre_id)
        if centre_city is not None:
            entry["centre_city"] = str(centre_city)
        entries.append(entry)

    return sorted(
        entries,
        key=lambda entry: (
            entry.get("centre_id", ""),
            entry["name"],
            entry["address"],
        ),
    )


def parse_directory_response(graph):
    responses = parse_directory_responses(graph)
    if not responses:
        raise ValueError("Directory response does not contain any agents")
    response = responses[0]
    return Agent(
        name=response["name"],
        uri=response["uri"],
        address=response["address"],
        stop="",
    )
