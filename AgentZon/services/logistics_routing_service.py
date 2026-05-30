"""Selecció de centre logístic per producte i agrupació d'enviaments per centre."""

import unicodedata
from difflib import SequenceMatcher

from AgentUtil.OntoNamespaces import AZON
from services.rdf_store import load_graph


def normalize_city_name(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    compact = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(compact.split())


def choose_logistics_centre_for_product(user_city, candidate_centres):
    if not candidate_centres:
        raise ValueError("No logistics centres are available for the requested product")

    normalized_user_city = normalize_city_name(user_city)

    def score(candidate):
        candidate_city = normalize_city_name(candidate.get("centre_city", ""))
        exact_match = candidate_city == normalized_user_city
        similarity = SequenceMatcher(None, normalized_user_city, candidate_city).ratio()
        return (
            0 if exact_match else 1,
            -similarity,
            candidate.get("centre_id", ""),
        )

    return min(candidate_centres, key=score)


def load_product_location_candidates(locations_path, product_ids):
    graph = load_graph(locations_path)
    candidates_by_product = {}
    for product_id in product_ids:
        product_node = AZON[f"product-{product_id}"]
        candidates = []
        for centre_node in graph.objects(product_node, AZON.UbicatACentre):
            centre_id = graph.value(centre_node, AZON.IdCentreLogistic)
            if centre_id is None:
                continue
            candidates.append(
                {
                    "centre_id": str(centre_id),
                    "centre_city": str(graph.value(centre_node, AZON.Ciutat) or ""),
                }
            )
        candidates_by_product[product_id] = sorted(candidates, key=lambda candidate: candidate["centre_id"])
    return candidates_by_product


def match_candidate_centres(candidate_centres, registered_centres):
    registered_by_id = {centre["centre_id"]: centre for centre in registered_centres if centre.get("centre_id")}
    matched = []
    for candidate in candidate_centres:
        registered = registered_by_id.get(candidate["centre_id"])
        if registered is None:
            continue
        matched.append(
            {
                **registered,
                "centre_id": candidate["centre_id"],
                "centre_city": candidate.get("centre_city") or registered.get("centre_city", ""),
            }
        )
    if not matched and len(registered_centres) == 1:
        registered = registered_centres[0]
        return [
            {
                **registered,
                "centre_id": candidate["centre_id"],
                "centre_city": candidate.get("centre_city") or registered.get("centre_city", ""),
            }
            for candidate in candidate_centres
        ]
    return matched


def resolve_logistics_centre_for_product(order, product, registered_centres, candidate_centres_by_product):
    candidate_centres = match_candidate_centres(
        candidate_centres_by_product.get(product["product_id"], []),
        registered_centres,
    )
    selected_centre = choose_logistics_centre_for_product(order["shipping_data"]["city"], candidate_centres)
    return selected_centre


def group_order_products_by_logistics_centre(order, registered_centres, candidate_centres_by_product):
    groups = {}
    for product in order["products"]:
        selected_centre = resolve_logistics_centre_for_product(
            order,
            product,
            registered_centres,
            candidate_centres_by_product,
        )
        centre_key = selected_centre.get("centre_id") or selected_centre.get("address")
        if centre_key not in groups:
            groups[centre_key] = {"centre": selected_centre, "products": []}
        groups[centre_key]["products"].append(product)
    return list(groups.values())
