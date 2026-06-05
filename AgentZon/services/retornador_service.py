"""Serveis de negoci del Retornador (UI i agrupació de devolucions).

Aquest mòdul centralitza la lògica que no ha d'estar al fitxer Flask de l'agent:
- obtenir productes comprats per usuari
- construir peticions de devolució des de la UI
- separar productes interns/externs per venedor
- calcular imports de reemborsament
"""

from uuid import uuid4

from rdflib import RDF
from rdflib import Literal

from AgentUtil.OntoNamespaces import AZON
from services.catalog_service import get_products_by_ids
from services.history_service import load_purchase_records
from services.rdf_store import load_graph

# Motius de devolució (UI) i política d'acceptació (Opinador)
RETURN_REASON_DEFECTUOUS = "Producte defectuós"
RETURN_REASON_NOT_AS_DESCRIBED = "Producte no compleix amb la descripció"
RETURN_REASON_TRANSPORT_DELAY = "El producte ha arribat més tard del previst"
RETURN_REASON_WRONG_PURCHASE = "M'he equivocat en comprar-lo"
RETURN_REASON_DISLIKED = "No m'ha agradat"
RETURN_REASON_DAMAGED_BY_USER = "El producte ha deixat de ser útil perquè l'he trencat sense voler"
RETURN_REASON_DESCRIPTION_UNREAD = "No vaig llegir bé la descripció del producte i ja no el vull"
RETURN_REASON_BETTER_OFFER = "He trobat un producte millor després de comprar-lo"
RETURN_REASON_OPINION_CHANGED = "He canviat d'opinió i ja no el vull"

RETURN_REASON_OPTIONS = [
    RETURN_REASON_DEFECTUOUS,
    RETURN_REASON_NOT_AS_DESCRIBED,
    RETURN_REASON_WRONG_PURCHASE,
    RETURN_REASON_DISLIKED,
    RETURN_REASON_DAMAGED_BY_USER,
    RETURN_REASON_DESCRIPTION_UNREAD,
    RETURN_REASON_BETTER_OFFER,
    RETURN_REASON_OPINION_CHANGED,
    RETURN_REASON_TRANSPORT_DELAY,
]

RETURN_REASONS_ACCEPTED_BY_POLICY = {
    RETURN_REASON_DEFECTUOUS,
    RETURN_REASON_NOT_AS_DESCRIBED,
    RETURN_REASON_TRANSPORT_DELAY,
}

RETURN_REJECTION_MESSAGE = "Ho sentim, no es compleixen les condicions per retornar el producte."
MAX_RETURN_DAYS = 15


def build_purchased_products_from_orders(purchases, logger=None, user_id=None):
    """Converteix snapshots de compra en files simples per a la UI de devolucions."""
    purchased_products = []
    for purchase in purchases:
        order_id = purchase.get("order_id", "")
        for product in purchase.get("products", []):
            product_id = product.get("product_id", "")
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
            user_id or "",
        )
    return purchased_products


def build_purchased_products_for_user(purchase_history_path, catalog_path, user_id, logger=None):
    """Compatibilitat per a proves antigues que encara llegeixen historial local."""
    purchases = load_purchase_records(purchase_history_path, user_id=user_id)
    purchased_products = build_purchased_products_from_orders(purchases, user_id=user_id)
    missing_ids = sorted(
        {
            product["product_id"]
            for product in purchased_products
            if product.get("name") == product.get("product_id") or not product.get("brand")
        }
    )
    catalog_products = {}
    if catalog_path is not None and missing_ids:
        catalog_products = {
            product["product_id"]: product
            for product in get_products_by_ids(catalog_path, missing_ids)
        }
    for product in purchased_products:
        catalog_product = catalog_products.get(product["product_id"])
        if catalog_product is None:
            continue
        if product.get("name") == product.get("product_id"):
            product["name"] = catalog_product.get("name", product["product_id"])
        if not product.get("brand"):
            product["brand"] = catalog_product.get("brand", "")
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

    normalized_reason = (reason or "").strip()
    if normalized_reason not in RETURN_REASON_OPTIONS:
        return None, "Has de seleccionar un motiu de devolució."

    order_groups = {}
    for item in selections:
        order_groups.setdefault(item["order_id"], []).append(item["product_id"])
    for order_id in order_groups:
        order_groups[order_id] = sorted(set(order_groups[order_id]))

    request_payload = {
        "return_id": f"RET-{uuid4().hex[:8].upper()}",
        "user_id": user_id,
        "reason": normalized_reason,
        "order_groups": order_groups,
    }
    if logger is not None:
        logger.info(
            "Construida peticio de devolucio %s per usuari %s (%d comandes, %d productes)",
            request_payload["return_id"],
            user_id,
            len(order_groups),
            sum(len(product_ids) for product_ids in order_groups.values()),
        )
    return request_payload, ""


def build_aggregate_return_decision(parent_return_id, user_id, reason, order_decisions, catalog_path):
    """Agrupa les resolucions per comanda en una resposta per a la UI."""
    accepted_items = []
    rejected_items = []
    accepted_products = []

    for order_id, decision in sorted(order_decisions.items()):
        accepted_ids = set(decision.get("accepted_product_ids") or decision.get("product_ids") or [])
        requested_ids = set(decision.get("requested_product_ids") or accepted_ids)
        products_by_id = {
            product["product_id"]: product
            for product in decision.get("products", [])
            if product.get("product_id")
        }
        for product_id in sorted(requested_ids):
            product = products_by_id.get(product_id, {})
            item = {
                "order_id": order_id,
                "product_id": product_id,
                "name": product.get("name", product_id),
                "brand": product.get("brand", ""),
            }
            if product_id in accepted_ids:
                accepted_items.append(item)
                accepted_products.append(
                    product if product else {"product_id": product_id, "name": product_id, "brand": "", "price": 0.0}
                )
            else:
                rejected_items.append(item)

    total_amount = round(sum(_product_amount(product) for product in accepted_products), 2)
    if total_amount == 0.0 and accepted_items and catalog_path is not None:
        products = get_products_by_ids(catalog_path, sorted({item["product_id"] for item in accepted_items}))
        products_by_id = {product["product_id"]: product for product in products}
        total_amount = round(sum(products_by_id.get(item["product_id"], {}).get("price", 0.0) for item in accepted_items), 2)

    if not accepted_items:
        return {
            "return_id": parent_return_id,
            "order_id": ", ".join(sorted(order_decisions.keys())),
            "user_id": user_id,
            "amount": 0.0,
            "reason": RETURN_REJECTION_MESSAGE,
            "accepted": False,
            "product_ids": [],
            "accepted_items": [],
            "rejected_items": rejected_items,
            "partial": False,
        }

    partial = bool(rejected_items)
    if partial:
        detail = (
            f"S'han acceptat {len(accepted_items)} producte(s) "
            f"i n'han quedat {len(rejected_items)} fora de política."
        )
    else:
        detail = "Tots els productes sol·licitats compleixen la política de devolució."

    return {
        "return_id": parent_return_id,
        "order_id": ", ".join(sorted({item["order_id"] for item in accepted_items})),
        "user_id": user_id,
        "amount": total_amount,
        "reason": detail,
        "accepted": True,
        "product_ids": sorted({item["product_id"] for item in accepted_items}),
        "accepted_items": accepted_items,
        "rejected_items": rejected_items,
        "partial": partial,
    }


def _extract_product_id_from_node(graph, node):
    """Extreu l'IdProducte d'un node RDF amb fallback pel nom del recurs."""
    product_id = graph.value(node, AZON.IdProducte)
    if product_id is not None:
        return str(product_id)
    node_text = str(node)
    if "product-" in node_text:
        return node_text.rsplit("product-", 1)[-1]
    return node_text


def _product_amount(product):
    try:
        return float(product.get("price", 0.0))
    except (TypeError, ValueError):
        return 0.0


def build_refund_batches_from_products(products):
    """Agrupa snapshots acceptats en lots interns i externs per venedor."""
    internal_products = []
    external_by_seller = {}
    for product in products:
        seller_id = product.get("seller_id") or ""
        requires_external = bool(product.get("requires_external_logistics"))
        if seller_id and requires_external:
            external_by_seller.setdefault(seller_id, []).append(product)
        else:
            internal_products.append(product)

    batches = []
    if internal_products:
        batches.append(
            {
                "seller_id": None,
                "product_ids": sorted(product["product_id"] for product in internal_products),
                "amount": round(sum(_product_amount(product) for product in internal_products), 2),
            }
        )
    for seller_id, seller_products in sorted(external_by_seller.items()):
        batches.append(
            {
                "seller_id": seller_id,
                "product_ids": sorted(product["product_id"] for product in seller_products),
                "amount": round(sum(_product_amount(product) for product in seller_products), 2),
            }
        )
    return batches


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
    """Compatibilitat: usa snapshots si hi són; si no, recorre a les rutes antigues."""
    snapshot_products = [
        product
        for product in decision.get("products", [])
        if product.get("product_id") in set(decision.get("product_ids", []))
    ]
    snapshot_batches = build_refund_batches_from_products(snapshot_products)
    if snapshot_batches:
        return snapshot_batches

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
