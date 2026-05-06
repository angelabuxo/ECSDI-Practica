"""Ontology namespace bindings shared by AgentZon graphs.

@author: javier
"""

__author__ = "javier"

from rdflib import Namespace


AZON = Namespace("http://www.semanticweb.org/agentzon#")
AGN = Namespace("http://www.agentes.org#")


def bind_namespaces(graph):
    graph.bind("azon", AZON)
    graph.bind("agn", AGN)
    graph.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    graph.bind("foaf", "http://xmlns.com/foaf/0.1/")
    return graph
