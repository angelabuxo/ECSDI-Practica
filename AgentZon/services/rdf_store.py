"""Utilitats de lectura i escriptura de grafos RDF en fitxers Turtle."""

from pathlib import Path

from rdflib import Graph

from AgentUtil.OntoNamespaces import bind_namespaces


# Graph IO -------------------------------------------------------------------------
def load_graph(path, rdf_format="turtle"):
    path = Path(path)
    graph = Graph()
    bind_namespaces(graph)
    if path.exists() and path.read_text(encoding="utf-8").strip():
        graph.parse(path, format=rdf_format)
    return graph


def save_graph(path, graph, rdf_format="turtle"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(graph.serialize(format=rdf_format), encoding="utf-8")
