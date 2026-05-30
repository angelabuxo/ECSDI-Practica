"""Seed data generators for the AgentZon Phase 2 prototype."""

import argparse
import random
from pathlib import Path

from rdflib import Graph, Literal, RDF, XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from config import DATA_DIR
from services.rdf_store import save_graph


PRODUCT_ARCHETYPES = [
    {
        "category": "audio",
        "kind": "Headphones",
        "adjectives": ["Wireless", "Studio", "Noise-Cancelling", "Travel"],
        "details": [
            "with immersive stereo sound",
            "for long listening sessions",
            "with low-latency bluetooth connectivity",
        ],
        "brands": ["AuralMax", "SonicNest", "WaveCraft"],
        "price_range": (49.0, 249.0),
        "weight_range": (0.2, 1.4),
    },
    {
        "category": "audio",
        "kind": "Speaker",
        "adjectives": ["Portable", "Smart", "Compact", "Party"],
        "details": [
            "built for indoor and outdoor playback",
            "with punchy bass response",
            "for easy travel and quick pairing",
        ],
        "brands": ["AuralMax", "EchoBeat", "WaveCraft"],
        "price_range": (35.0, 199.0),
        "weight_range": (0.4, 2.5),
    },
    {
        "category": "peripherals",
        "kind": "Keyboard",
        "adjectives": ["Mechanical", "Compact", "Ergonomic", "RGB"],
        "details": [
            "with responsive tactile switches",
            "for productivity and gaming",
            "with durable premium keycaps",
        ],
        "brands": ["KeyForge", "TypeLab", "InputWorks"],
        "price_range": (59.0, 229.0),
        "weight_range": (0.6, 2.0),
    },
    {
        "category": "peripherals",
        "kind": "Mouse",
        "adjectives": ["Wireless", "Precision", "Ergonomic", "Ultra-Light"],
        "details": [
            "for precise cursor control",
            "with programmable buttons and fast tracking",
            "designed for all-day comfort",
        ],
        "brands": ["KeyForge", "PointerPro", "InputWorks"],
        "price_range": (24.0, 149.0),
        "weight_range": (0.08, 0.5),
    },
    {
        "category": "home",
        "kind": "Coffee Mug",
        "adjectives": ["Ceramic", "Insulated", "Minimalist", "Stoneware"],
        "details": [
            "for hot drinks throughout the day",
            "with a comfortable easy-grip handle",
            "that fits naturally into any kitchen",
        ],
        "brands": ["CasaNova", "Homely", "NordClay"],
        "price_range": (8.0, 35.0),
        "weight_range": (0.2, 0.9),
    },
    {
        "category": "home",
        "kind": "Desk Lamp",
        "adjectives": ["LED", "Adjustable", "Slim", "Ambient"],
        "details": [
            "for focused lighting on work surfaces",
            "with soft warm illumination",
            "that blends into modern study spaces",
        ],
        "brands": ["CasaNova", "LumaHome", "BrightNest"],
        "price_range": (18.0, 89.0),
        "weight_range": (0.5, 2.2),
    },
]

LOGISTIC_CENTRES = [
    {"resource": "centre-BCN", "id": "CL-BCN", "city": "Barcelona"},
    {"resource": "centre-GI", "id": "CL-GI", "city": "Girona"},
    {"resource": "centre-TGN", "id": "CL-TGN", "city": "Tarragona"},
]


def _build_rng(seed):
    return random.Random(seed)


def _round_float(value):
    return round(value, 2)


def _build_product_record(index, rng):
    archetype = rng.choice(PRODUCT_ARCHETYPES)
    adjective = rng.choice(archetype["adjectives"])
    brand = rng.choice(archetype["brands"])
    detail = rng.choice(archetype["details"])
    product_id = f"P{1001 + index}"
    name = f"{adjective} {archetype['kind']}"
    description = f"{name} {detail}"
    return {
        "id": product_id,
        "name": name,
        "description": description,
        "category": archetype["category"],
        "brand": brand,
        "price": _round_float(rng.uniform(*archetype["price_range"])),
        "weight": _round_float(rng.uniform(*archetype["weight_range"])),
    }


def _generate_random_products(product_count, rng):
    return [_build_product_record(index, rng) for index in range(product_count)]


def _build_products_graph(products):
    graph = Graph()
    bind_namespaces(graph)

    for item in products:
        subject = AZON[f"product-{item['id']}"]
        graph.add((subject, RDF.type, AZON.Producte))
        graph.add((subject, AZON.IdProducte, Literal(item["id"])))
        graph.add((subject, AZON.Nom, Literal(item["name"])))
        graph.add((subject, AZON.Descripcio, Literal(item["description"])))
        graph.add((subject, AZON.Categoria, Literal(item["category"])))
        graph.add((subject, AZON.Marca, Literal(item["brand"])))
        graph.add((subject, AZON.Preu, Literal(item["price"], datatype=XSD.float)))
        graph.add((subject, AZON.Pes, Literal(item["weight"], datatype=XSD.float)))
    return graph


def _build_locations_graph(products):
    graph = Graph()
    bind_namespaces(graph)

    for centre_data in LOGISTIC_CENTRES:
        centre = AZON[centre_data["resource"]]
        graph.add((centre, RDF.type, AZON.CentreLogistic))
        graph.add((centre, AZON.IdCentreLogistic, Literal(centre_data["id"])))
        graph.add((centre, AZON.Ciutat, Literal(centre_data["city"])))

    for index, item in enumerate(products):
        product = AZON[f"product-{item['id']}"]
        primary_centre = LOGISTIC_CENTRES[index % len(LOGISTIC_CENTRES)]
        graph.add((product, AZON.UbicatACentre, AZON[primary_centre["resource"]]))
        if len(LOGISTIC_CENTRES) > 1 and index % 3 == 0:
            secondary_centre = LOGISTIC_CENTRES[(index + 1) % len(LOGISTIC_CENTRES)]
            graph.add((product, AZON.UbicatACentre, AZON[secondary_centre["resource"]]))
    return graph


def _build_empty_graph():
    graph = Graph()
    bind_namespaces(graph)
    return graph


def bootstrap_phase2_data(data_dir, product_count=24, seed=None):
    if product_count <= 0:
        raise ValueError("product_count must be greater than 0")

    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    rng = _build_rng(seed)
    products = _generate_random_products(product_count, rng)

    files = {
        "productes.ttl": _build_products_graph(products),
        "ubicacions_productes.ttl": _build_locations_graph(products),
        "historial_cerques.ttl": _build_empty_graph(),
        "historial_compres.ttl": _build_empty_graph(),
        "comandes.ttl": _build_empty_graph(),
        "dades_enviament_usuari.ttl": _build_empty_graph(),
        "lots.ttl": _build_empty_graph(),
    }

    for filename, graph in files.items():
        save_graph(data_dir / filename, graph)


def main():
    parser = argparse.ArgumentParser(description="Generate random AgentZon RDF seed data.")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--product-count", type=int, default=24)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    bootstrap_phase2_data(args.data_dir, product_count=args.product_count, seed=args.seed)


if __name__ == "__main__":
    main()
