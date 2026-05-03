"""
Servei de persistencia de mapes clau-valor per AgentZon.

Aquest fitxer encapsula la lectura i escriptura de dades estructurades en
format JSON o Turtle (TTL), mantenint una API unica (`load_map`/`save_map`)
per no duplicar lògica de serialitzacio dins dels agents.

Actualment l'utilitza `AgentCompra` per gestionar:
- dades d'enviament d'usuari,
- ubicacions de productes,
- responsables d'enviament.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from rdflib import Graph, Literal, RDF, URIRef, XSD


class MapDataStore:
    """Persistencia de mapes en format JSON o Turtle."""

    def __init__(self, namespace: str):
        self.namespace = namespace

    def _az(self, term: str) -> URIRef:
        return URIRef(f"{self.namespace}{term}")

    def _load_json(self, path: Path, default: Optional[Dict] = None) -> Dict:
        if not path.exists():
            return default or {}

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_json(self, path: Path, data: Dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def _load_indexed_ttl(
        self,
        path: Path,
        subject_type: str,
        id_predicate: str,
        field_predicates: Dict[str, str],
    ) -> Dict:
        if not path.exists():
            return {}

        graph = Graph()
        graph.parse(path, format="turtle")
        result = {}

        for subject in graph.subjects(RDF.type, self._az(subject_type)):
            entity_id = graph.value(subject, self._az(id_predicate))
            if entity_id is None:
                continue

            key = str(entity_id.toPython())
            row = {}
            for field, predicate in field_predicates.items():
                value = graph.value(subject, self._az(predicate))
                if value is not None:
                    row[field] = value.toPython()
            result[key] = row

        return result

    def _save_indexed_ttl(
        self,
        path: Path,
        data: Dict[str, Dict[str, object]],
        subject_type: str,
        id_predicate: str,
        field_predicates: Dict[str, str],
        subject_prefix: str,
    ) -> None:
        graph = Graph()
        graph.bind("az", self.namespace)

        for key, row in data.items():
            subject = self._az(f"{subject_prefix}_{key}")
            graph.add((subject, RDF.type, self._az(subject_type)))
            graph.add((subject, self._az(id_predicate), Literal(str(key))))

            for field, predicate in field_predicates.items():
                if field not in row:
                    continue

                value = row[field]
                if field == "prioritat":
                    graph.add((subject, self._az(predicate), Literal(int(value), datatype=XSD.integer)))
                else:
                    graph.add((subject, self._az(predicate), Literal(value)))

        path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=path, format="turtle")

    def load_map(self, path: Path, map_type: str) -> Dict:
        if path.suffix.lower() == ".ttl":
            if map_type == "dades_enviament":
                return self._load_indexed_ttl(
                    path,
                    subject_type="DadesEnviamentUsuari",
                    id_predicate="IdUsuari",
                    field_predicates={"adreca": "Adreça", "ciutat": "Ciutat", "prioritat": "Prioritat"},
                )
            if map_type == "ubicacions":
                return self._load_indexed_ttl(
                    path,
                    subject_type="UbicacioProducte",
                    id_predicate="IdProducte",
                    field_predicates={"magatzem": "Magatzem", "ciutat": "Ciutat"},
                )
            if map_type == "responsables":
                return self._load_indexed_ttl(
                    path,
                    subject_type="ResponsableEnviamentProducte",
                    id_predicate="IdProducte",
                    field_predicates={"responsable": "Responsable", "venedor": "Venedor"},
                )
            raise ValueError(f"Tipus de mapa desconegut: {map_type}")

        return self._load_json(path)

    def save_map(self, path: Path, data: Dict, map_type: str) -> None:
        if path.suffix.lower() == ".ttl":
            if map_type == "dades_enviament":
                self._save_indexed_ttl(
                    path,
                    data,
                    subject_type="DadesEnviamentUsuari",
                    id_predicate="IdUsuari",
                    field_predicates={"adreca": "Adreça", "ciutat": "Ciutat", "prioritat": "Prioritat"},
                    subject_prefix="dades_enviament_usuari",
                )
                return
            if map_type == "ubicacions":
                self._save_indexed_ttl(
                    path,
                    data,
                    subject_type="UbicacioProducte",
                    id_predicate="IdProducte",
                    field_predicates={"magatzem": "Magatzem", "ciutat": "Ciutat"},
                    subject_prefix="ubicacio_producte",
                )
                return
            if map_type == "responsables":
                self._save_indexed_ttl(
                    path,
                    data,
                    subject_type="ResponsableEnviamentProducte",
                    id_predicate="IdProducte",
                    field_predicates={"responsable": "Responsable", "venedor": "Venedor"},
                    subject_prefix="responsable_enviament_producte",
                )
                return
            raise ValueError(f"Tipus de mapa desconegut: {map_type}")

        self._save_json(path, data)
