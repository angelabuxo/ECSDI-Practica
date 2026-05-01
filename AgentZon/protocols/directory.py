from typing import Optional

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from AgentZon.config import AGENTZON


DSO = Namespace("http://www.agents.org/ontology/directory-service#")


def build_register_action(name: str, uri: URIRef, address: str, agent_type: str) -> Graph:
    graph = Graph()
    graph.bind("dso", DSO)
    graph.bind("az", AGENTZON)
    action = URIRef(f"{AGENTZON}register_{name}")
    graph.add((action, RDF.type, DSO.Register))
    graph.add((action, DSO.Name, Literal(name)))
    graph.add((action, DSO.Uri, uri))
    graph.add((action, DSO.Address, Literal(address)))
    graph.add((action, DSO.AgentType, Literal(agent_type)))
    return graph


def build_search_action(agent_type: str, name: Optional[str] = None) -> Graph:
    graph = Graph()
    graph.bind("dso", DSO)
    graph.bind("az", AGENTZON)
    safe_name = name or "any"
    action = URIRef(f"{AGENTZON}search_{agent_type}_{safe_name}")
    graph.add((action, RDF.type, DSO.Search))
    graph.add((action, DSO.AgentType, Literal(agent_type)))
    if name is not None:
        graph.add((action, DSO.Name, Literal(name)))
    return graph


def build_directory_response(name: str, uri: URIRef, address: str, agent_type: str) -> Graph:
    graph = Graph()
    graph.bind("dso", DSO)
    graph.bind("az", AGENTZON)
    response = URIRef(f"{AGENTZON}directory_response_{name}")
    graph.add((response, RDF.type, DSO.DirectoryResponse))
    graph.add((response, DSO.Name, Literal(name)))
    graph.add((response, DSO.Uri, uri))
    graph.add((response, DSO.Address, Literal(address)))
    graph.add((response, DSO.AgentType, Literal(agent_type)))
    return graph


def build_directory_responses(entries: list[dict]) -> Graph:
    graph = Graph()
    graph.bind("dso", DSO)
    graph.bind("az", AGENTZON)
    for entry in entries:
        response_graph = build_directory_response(
            name=entry["name"],
            uri=entry["uri"],
            address=entry["address"],
            agent_type=entry["agent_type"],
        )
        for triple in response_graph:
            graph.add(triple)
    return graph


def read_directory_response(graph: Graph, subject: URIRef) -> dict:
    return {
        "name": str(graph.value(subject, DSO.Name)),
        "uri": graph.value(subject, DSO.Uri),
        "address": str(graph.value(subject, DSO.Address)),
        "agent_type": str(graph.value(subject, DSO.AgentType)),
    }


def read_directory_responses(graph: Graph) -> list[dict]:
    return [
        read_directory_response(graph, subject)
        for subject in graph.subjects(RDF.type, DSO.DirectoryResponse)
    ]
