from pathlib import Path

from rdflib import Graph

from AgentZon.AgentUtil.OntoNamespaces import bind_namespaces


class RDFFileStore:
    def __init__(self, path, rdf_format="turtle"):
        self.path = Path(path)
        self.rdf_format = rdf_format

    def load_graph(self):
        graph = Graph()
        bind_namespaces(graph)
        if self.path.exists() and self.path.read_text(encoding="utf-8").strip():
            graph.parse(self.path, format=self.rdf_format)
        return graph

    def save_graph(self, graph):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(graph.serialize(format=self.rdf_format), encoding="utf-8")
