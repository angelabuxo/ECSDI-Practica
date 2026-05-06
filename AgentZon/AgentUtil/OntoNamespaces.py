"""Ontology namespace bindings shared by AgentZon graphs.

@author: javier
"""

__author__ = "javier"

from rdflib import Namespace, URIRef


AZON_ONTOLOGY = URIRef("http://www.semanticweb.org/agentzon")
DSO_ONTOLOGY = URIRef("http://www.semanticweb.org/directory-service-ontology#")
AZON = Namespace(f"{AZON_ONTOLOGY}#")
AGN = Namespace("http://www.agentes.org#")


def bind_namespaces(graph):
    graph.bind("azon", AZON)
    graph.bind("agn", AGN)
    graph.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    graph.bind("foaf", "http://xmlns.com/foaf/0.1/")
    return graph
