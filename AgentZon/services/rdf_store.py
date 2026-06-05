"""Utilitats de lectura i escriptura de grafos RDF en fitxers Turtle."""

import tempfile
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
    serialized = graph.serialize(format=rdf_format)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as tmp_file:
        tmp_file.write(serialized)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)

def _user_id_from_iri(user_iri):
    """Extreu l'identificador d'usuari a partir de l'IRI de PertanyAUsuari."""
    if user_iri is None:
        return ""
    return str(user_iri).split("#")[-1].replace("usuari-", "")


def _seller_id_from_iri(seller_iri):
    """Extreu l'identificador de venedor a partir de l'IRI de PertanyAVenedorExtern."""
    if seller_iri is None:
        return ""
    return str(seller_iri).split("#")[-1].replace("venedor-", "")

def _centre_id_from_iri(centre_iri):
    """Extreu l'identificador de centre a partir de l'IRI de UbicatACentre."""
    if centre_iri is None:
        return ""
    return str(centre_iri).split("#")[-1].replace("centre-", "")
