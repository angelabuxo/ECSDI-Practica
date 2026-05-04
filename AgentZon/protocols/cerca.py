from __future__ import annotations

from typing import Iterable
import uuid

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef, XSD

from AgentZon.config import AGENTZON


SEARCH = Namespace("urn:agentzon:search:")


def _literal(graph: Graph, subject: URIRef, predicate: URIRef, default=None):
    value = graph.value(subject, predicate)
    return value.toPython() if value is not None else default


def _literal_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def build_peticio_cerca(
    text: str = "",
    categ: str | None = None,
    marca: str | None = None,
    preu_min: float | None = None,
    preu_max: float | None = None,
    subject: URIRef | BNode | None = None,
) -> Graph:
    if preu_min is not None and preu_max is not None and preu_min > preu_max:
        raise ValueError("El preu mínim no pot ser més gran que el màxim.")

    graph = Graph()
    graph.bind("az", AGENTZON)
    graph.bind("search", SEARCH)

    subject = subject or BNode()
    graph.add((subject, RDF.type, AGENTZON.PeticioCerca))

    normalized_text = (text or "").strip().lower()
    normalized_categ = categ.strip().lower() if categ else None
    normalized_marca = marca.strip().lower() if marca else None

    if normalized_text:
        graph.add((subject, SEARCH.text, Literal(normalized_text)))
    if normalized_categ:
        graph.add((subject, SEARCH.categ, Literal(normalized_categ)))
    if normalized_marca:
        graph.add((subject, SEARCH.marca, Literal(normalized_marca)))
    if preu_min is not None:
        graph.add((subject, SEARCH.preu_min, Literal(preu_min, datatype=XSD.float)))
    if preu_max is not None:
        graph.add((subject, SEARCH.preu_max, Literal(preu_max, datatype=XSD.float)))

    return graph


def get_peticio_cerca_subject(graph: Graph) -> URIRef | BNode:
    subject = next(graph.subjects(RDF.type, AGENTZON.PeticioCerca), None)
    if subject is None:
        raise ValueError("No s'ha trobat cap instància PeticioCerca al graf.")
    return subject


def read_peticio_cerca(graph: Graph, subject: URIRef | BNode) -> dict:
    return {
        "subject": subject,
        "text": str(_literal(graph, subject, SEARCH.text, "") or ""),
        "categ": _literal_text(_literal(graph, subject, SEARCH.categ)),
        "marca": _literal_text(_literal(graph, subject, SEARCH.marca)),
        "preu_min": _literal(graph, subject, SEARCH.preu_min),
        "preu_max": _literal(graph, subject, SEARCH.preu_max),
    }


def read_producte(graph: Graph, subject: URIRef) -> dict:
    producte_id = _literal(graph, subject, AGENTZON.Id, str(subject).rsplit("#", 1)[-1].rsplit("/", 1)[-1])
    return {
        "uri": subject,
        "id": str(producte_id),
        "nom": str(_literal(graph, subject, AGENTZON.Nom, "")),
        "preu": float(_literal(graph, subject, AGENTZON.Preu, 0.0) or 0.0),
        "descr": str(_literal(graph, subject, AGENTZON.Descripcio, "")),
        "categ": str(_literal(graph, subject, AGENTZON.Categoria, "")),
        "marca": str(_literal(graph, subject, AGENTZON.Marca, "")),
        "pes": int(float(_literal(graph, subject, AGENTZON.Pes, 0) or 0)),
    }


def iter_productes(graph: Graph) -> list[dict]:
    return [read_producte(graph, subject) for subject in graph.subjects(RDF.type, AGENTZON.Producte)]


def productes_per_ids(graph: Graph, ids_productes: Iterable[str]) -> list[dict]:
    productes_indexats = {producte["id"]: producte for producte in iter_productes(graph)}
    seleccionats = []

    for producte_id in ids_productes:
        if producte_id not in productes_indexats:
            raise ValueError(f"Producte desconegut: {producte_id}")
        seleccionats.append(productes_indexats[producte_id])

    return seleccionats


def cercar_productes(catalog_graph: Graph, peticio_graph: Graph, peticio_subject: URIRef | BNode) -> list[URIRef]:
    peticio = read_peticio_cerca(peticio_graph, peticio_subject)
    filters = []

    if peticio["text"]:
        text_literal = Literal(peticio["text"]).n3()
        filters.append(
            f"(CONTAINS(LCASE(STR(?nom)), LCASE(STR({text_literal}))) "
            f"|| CONTAINS(LCASE(STR(?descr)), LCASE(STR({text_literal}))))"
        )

    if peticio["categ"]:
        categ_literal = Literal(peticio["categ"]).n3()
        filters.append(f"LCASE(STR(?categoria)) = LCASE(STR({categ_literal}))")

    if peticio["marca"]:
        marca_literal = Literal(peticio["marca"]).n3()
        filters.append(f"LCASE(STR(?marca)) = LCASE(STR({marca_literal}))")

    if peticio["preu_min"] is not None:
        filters.append(f"?preu >= {Literal(float(peticio['preu_min']), datatype=XSD.float).n3()}")

    if peticio["preu_max"] is not None:
        filters.append(f"?preu <= {Literal(float(peticio['preu_max']), datatype=XSD.float).n3()}")

    where_filters = ""
    if filters:
        where_filters = "\nFILTER(" + " && ".join(filters) + ")"

    query = f"""
    SELECT DISTINCT ?producte
    WHERE {{
      ?producte rdf:type az:Producte ;
                az:Nom ?nom ;
                az:Descripcio ?descr ;
                az:Categoria ?categoria ;
                az:Marca ?marca ;
                az:Preu ?preu .
      {where_filters}
    }}
    ORDER BY ?producte
    """

    results = catalog_graph.query(query, initNs={"rdf": RDF, "az": AGENTZON})
    return [row.producte for row in results]


def build_resultat_cerca(
    catalog_graph: Graph,
    productes: Iterable[URIRef],
    peticio_subject: URIRef | BNode | None = None,
    result_subject: URIRef | BNode | None = None,
) -> Graph:
    graph = Graph()
    graph.bind("az", AGENTZON)
    result_subject = result_subject or URIRef(f"{AGENTZON}resultat_cerca_{uuid.uuid4()}")

    graph.add((result_subject, RDF.type, AGENTZON.ResultatCerca))
    if peticio_subject is not None:
        graph.add((AGENTZON.usuari_cercador, AGENTZON.Rep, result_subject))

    for producte in productes:
        if (producte, RDF.type, AGENTZON.Producte) not in catalog_graph:
            raise ValueError(f"El producte {producte} no existeix al catàleg.")
        graph.add((result_subject, AGENTZON.Mostra, producte))

    return graph


def get_resultat_cerca_subject(graph: Graph) -> URIRef | BNode:
    subject = next(graph.subjects(RDF.type, AGENTZON.ResultatCerca), None)
    if subject is None:
        raise ValueError("No s'ha trobat cap instància ResultatCerca al graf.")
    return subject


def read_resultat_cerca(graph: Graph, subject: URIRef | BNode) -> dict:
    productes = [read_producte(graph, producte) for producte in graph.objects(subject, AGENTZON.Mostra)]
    return {
        "subject": subject,
        "llista_productes": productes,
        "total": len(productes),
    }
