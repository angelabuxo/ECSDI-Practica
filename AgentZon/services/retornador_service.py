"""Serveis de negoci del Retornador (UI i agrupació de devolucions).

Aquest mòdul centralitza la lògica que no ha d'estar al fitxer Flask de l'agent:
- obtenir productes comprats per usuari
- construir peticions de devolució des de la UI
- separar productes interns/externs per venedor
- calcular imports de reemborsament
"""

from uuid import uuid4

from rdflib import RDF

from AgentUtil.OntoNamespaces import AZON
from services.catalog_service import get_products_by_ids
from services.history_service import load_purchase_records
from services.rdf_store import load_graph


def build_purchased_products_for_user(purchase_history_path, catalog_path, user_id, logger=None):
    """Retorna els productes comprats per un usuari (IP) amb dades de catàleg."""
    purchases = load_purchase_records(purchase_history_path, user_id=user_id)
    product_ids = sorted({pid for purchase in purchases for pid in purchase.get("product_ids", [])})
    catalog_products = {
        product["product_id"]: product
        for product in get_products_by_ids(catalog_path, product_ids)
    }
    purchased_products = []
    for purchase in purchases:
        order_id = purchase.get("order_id", "")
        for product_id in purchase.get("product_ids", []):
            product = catalog_products.get(product_id, {})
            purchased_products.append(
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "name": product.get("name", product_id),
                    "brand": product.get("brand", ""),
                }
            )
    if logger is not None:
        logger.info(
            "Retornador UI: %d productes comprats disponibles per a l'usuari %s",
            len(purchased_products),
            user_id,
        )
    return purchased_products


def build_return_request_from_selection(selected_values, reason, user_id, logger=None):
    """Construeix una petició de devolució a partir de la selecció de la UI.

    Les opcions de la UI venen com `order_id::product_id`.
    """
    selections = []
    for value in selected_values:
        if "::" not in value:
            continue
        order_id, product_id = value.split("::", 1)
        selections.append({"order_id": order_id.strip(), "product_id": product_id.strip()})
    if not selections:
        return None, "Has de seleccionar almenys un producte comprat."

    distinct_orders = {item["order_id"] for item in selections}
    if len(distinct_orders) != 1:
        return None, "Per ara només es poden retornar productes d'una mateixa comanda alhora."

    request_payload = {
        "return_id": f"RET-{uuid4().hex[:8].upper()}",
        "order_id": selections[0]["order_id"],
        "user_id": user_id,
        "amount": None,
        "reason": reason.strip(),
        "seller_id": None,
        "product_ids": sorted({item["product_id"] for item in selections}),
    }
    if logger is not None:
        logger.info(
            "Construida peticio de devolucio %s per usuari %s (comanda %s, %d productes)",
            request_payload["return_id"],
            user_id,
            request_payload["order_id"],
            len(request_payload["product_ids"]),
        )
    return request_payload, ""


def _extract_product_id_from_node(graph, node):
    """Extreu l'IdProducte d'un node RDF amb fallback pel nom del recurs."""
    product_id = graph.value(node, AZON.IdProducte)
    if product_id is not None:
        return str(product_id)
    node_text = str(node)
    if "product-" in node_text:
        return node_text.rsplit("product-", 1)[-1]
    return node_text


def load_external_seller_by_product(shipping_responsibility_path, catalog_path):
    """Mapeja `product_id -> seller_id` per als productes externs."""
    graph = load_graph(shipping_responsibility_path)
    seller_by_product = {}
    for subject in graph.subjects(predicate=AZON.IdProducte, object=None):
        product_id = str(graph.value(subject, AZON.IdProducte))
        seller_id = graph.value(subject, AZON.IdVenedorExtern)
        external_flag = graph.value(subject, AZON.RequereixLogisticaExterna)
        is_external = str(external_flag).lower() == "true" if external_flag is not None else False
        if seller_id is not None and is_external:
            seller_by_product[product_id] = str(seller_id)

    # Fallback: si hi ha productes externs definits al catàleg.
    catalog_graph = load_graph(catalog_path)
    for product_node in catalog_graph.subjects(RDF.type, AZON.ProducteExtern):
        product_id = _extract_product_id_from_node(catalog_graph, product_node)
        seller_id = catalog_graph.value(product_node, AZON.IdVenedorExtern)
        if seller_id is not None:
            seller_by_product[product_id] = str(seller_id)
    return seller_by_product


def calculate_amount_for_products(catalog_path, product_ids):
    """Calcula l'import total com a suma de preus dels productes indicats."""
    products = get_products_by_ids(catalog_path, product_ids)
    return round(sum(product.get("price", 0.0) for product in products), 2)


def build_refund_batches(decision, shipping_responsibility_path, catalog_path):
    """Separa una devolució en lots de reemborsament intern/extern per venedor."""
    product_ids = decision.get("product_ids", [])
    seller_by_product = load_external_seller_by_product(shipping_responsibility_path, catalog_path)
    internal_product_ids = []
    external_by_seller = {}
    for product_id in product_ids:
        seller_id = seller_by_product.get(product_id)
        if seller_id:
            external_by_seller.setdefault(seller_id, []).append(product_id)
        else:
            internal_product_ids.append(product_id)

    batches = []
    if internal_product_ids:
        batches.append(
            {
                "seller_id": None,
                "product_ids": sorted(internal_product_ids),
                "amount": calculate_amount_for_products(catalog_path, internal_product_ids),
            }
        )
    for seller_id, seller_product_ids in sorted(external_by_seller.items()):
        batches.append(
            {
                "seller_id": seller_id,
                "product_ids": sorted(seller_product_ids),
                "amount": calculate_amount_for_products(catalog_path, seller_product_ids),
            }
        )

    if not batches and product_ids:
        batches.append(
            {
                "seller_id": decision.get("seller_id"),
                "product_ids": sorted(product_ids),
                "amount": calculate_amount_for_products(catalog_path, product_ids),
            }
        )
    return batches
