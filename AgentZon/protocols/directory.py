"""
Servei de directori en RDF (ontology "directory-service", prefix dso).

Idea ràpida: és com una guia telefònica per agents. Un agent vol saber "qui és el
transportista?" o "quin és l'endpoint del centre logístic?" — registres i cerques es
representen com a **accions** (Register, Search) i **respostes** (DirectoryResponse)
amb tripletes RDF, igual que la resta d'AgentZon. Això no és FIPA en si: després
s'embolla dins un missatge ACL (capa envelope) amb `fipa_acl.build_message`.

No cal saber RDF a fons: cada funció retorna un `Graph()` petit amb nodes i propietats
que el Directory Agent sap llegir i escriure.
"""

from typing import Optional

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from AgentZon.config import AGENTZON


# Vocabulari reutilitzat (URI base fixa — coincideix amb el que solen usar els exemples d'agents)
DSO = Namespace("http://www.agents.org/ontology/directory-service#")


def build_register_action(name: str, uri: URIRef, address: str, agent_type: str) -> Graph:
    """
    "Hola directori, vull donar-me d'alta": nom llegible, URI de l'agent, URL HTTP on
    escolta, i tipus (p.ex. quin rol té dins AgentZon). El graf resultant és el **contingut**
    que un agent envia dins del missatge ACL quan es registra.
    """
    graph = Graph()
    # Prefixos curts sortiran bé si es serialitza a XML/Turtle
    graph.bind("dso", DSO)
    graph.bind("az", AGENTZON)

    # Un node "acció" únic per aquest registre — el nom a l'URL és només identificador local
    action = URIRef(f"{AGENTZON}register_{name}")
    graph.add((action, RDF.type, DSO.Register))  # aquest node és una acció Register del vocabulari dso
    graph.add((action, DSO.Name, Literal(name)))  # string humà (p.ex. "transportista_1")
    graph.add((action, DSO.Uri, uri))  # URIRef de l'agent dins l'ontologia AgentZon
    graph.add((action, DSO.Address, Literal(address)))  # base URL tipus http://127.0.0.1:9003
    graph.add((action, DSO.AgentType, Literal(agent_type)))  # etiqueta de tipus per filtrar cerques
    return graph


def build_search_action(agent_type: str, name: Optional[str] = None) -> Graph:
    """
    "Hola directori, busco agents d'aquest tipus" i opcionalment un nom concret.
    Si `name` és None, només filtrem per tipus (el fragment de l'URI del node acció usarà "any").
    """
    graph = Graph()
    graph.bind("dso", DSO)
    graph.bind("az", AGENTZON)

    safe_name = name or "any"  # per no trencar l'URIRef si no hi ha nom; és dummy, no surt com a predicate
    action = URIRef(f"{AGENTZON}search_{agent_type}_{safe_name}")
    graph.add((action, RDF.type, DSO.Search))
    graph.add((action, DSO.AgentType, Literal(agent_type)))
    if name is not None:
        graph.add((action, DSO.Name, Literal(name)))  # cerca més específica per nom exacte

    return graph


def build_directory_response(name: str, uri: URIRef, address: str, agent_type: str) -> Graph:
    """
    Una entrada de resultat: el directori respon amb "aquest agent existeix i aquestes són les seves dades".
    Un graf pot tenir-ne diverses (veure `build_directory_responses`).
    """
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
    """
    Fusiona moltes respostes en un sol graf (útil quan la cerca retorna 0, 1 o N agents).
    Cada `entry` ha de tenir claus name, uri, address, agent_type — mateix contracte que `build_directory_response`.
    """
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
        # Copiem totes les tripletes del mini-graf dins el graf gran (patró típic rdflib)
        for triple in response_graph:
            graph.add(triple)

    return graph


def read_directory_response(graph: Graph, subject: URIRef) -> dict:
    """
    Desinversa: des d'un node que ja saps que és un DirectoryResponse, extreu dict Python.
    `graph.value` retorna el objecte de la tripleta (o None si falta); uri es deixa com URIRef.
    """
    return {
        "name": str(graph.value(subject, DSO.Name)),
        "uri": graph.value(subject, DSO.Uri),
        "address": str(graph.value(subject, DSO.Address)),
        "agent_type": str(graph.value(subject, DSO.AgentType)),
    }


def read_directory_responses(graph: Graph) -> list[dict]:
    """
    Escaneja **tot** el graf i agafa tots els subjectes que són rdf:type DirectoryResponse.
    Ordre no garantit (depèn de rdflib); si en cal un d'ordre explícit, el faries al cridador.
    """
    return [
        read_directory_response(graph, subject)
        for subject in graph.subjects(RDF.type, DSO.DirectoryResponse)
    ]
