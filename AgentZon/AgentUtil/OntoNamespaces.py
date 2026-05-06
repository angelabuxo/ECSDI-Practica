"""Ontology namespace bindings shared by AgentZon graphs.

@author: javier
"""

__author__ = "javier"

from rdflib import Namespace, URIRef


ONTOLOGY_URI = URIRef("http://www.semanticweb.org/agentzon")
AZON = Namespace(f"{ONTOLOGY_URI}#")
AGN = Namespace("http://www.agentes.org#")


def bind_namespaces(graph):
    graph.bind("azon", AZON)
    graph.bind("agn", AGN)
    graph.bind("acl", "http://www.nuin.org/ontology/fipa/acl#")
    graph.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    graph.bind("owl", "http://www.w3.org/2002/07/owl#")
    graph.bind("foaf", "http://xmlns.com/foaf/0.1/")
    return graph
