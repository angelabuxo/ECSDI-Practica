from __future__ import annotations

from pathlib import Path

from rdflib import BNode, Graph, Namespace, URIRef

from AgentZon.config import AGENTZON


class MapDataStore:
    """
    Petit helper RDF per carregar, substituir i persistir fragments Turtle.

    El nom es manté per compatibilitat amb imports existents, però la
    implementació deixa enrere la semàntica de mapes JSON i treballa només amb
    grafs `rdflib`.
    """

    def __init__(self, namespace: str = str(AGENTZON)):
        self.namespace = namespace

    def load_graph(self, path: Path, rdf_format: str = "turtle") -> Graph:
        graph = Graph()
        graph.bind("az", Namespace(self.namespace))
        if path.exists() and path.stat().st_size:
            graph.parse(path, format=rdf_format)
        return graph

    def save_graph(self, path: Path, graph: Graph, rdf_format: str = "turtle") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=path, format=rdf_format)

    def replace_subject(
        self,
        path: Path,
        subject: URIRef | BNode,
        fragment: Graph,
        rdf_format: str = "turtle",
    ) -> Graph:
        graph = self.load_graph(path, rdf_format=rdf_format)
        graph.remove((subject, None, None))
        for triple in fragment.triples((subject, None, None)):
            graph.add(triple)
        self.save_graph(path, graph, rdf_format=rdf_format)
        return graph
