"""Business rules for feedback, recommendations, and return checks."""

from collections import Counter
from datetime import date

from services.catalog_service import get_products_by_ids, search_products
from services.history_service import (
    get_latest_purchase_for_user,
    load_purchase_records,
    load_search_records,
)


def generate_recommendations(catalog_path, search_history_path, purchase_history_path, user_id=None, limit=5):
    catalog_products = search_products(catalog_path, _empty_criteria())
    purchase_records = load_purchase_records(purchase_history_path, user_id=user_id)
    purchased_ids = {product_id for record in purchase_records for product_id in record["product_ids"]}

    purchased_products = get_products_by_ids(catalog_path, list(purchased_ids)) if purchased_ids else []
    category_counter = Counter(product["category"] for product in purchased_products if product.get("category"))
    brand_counter = Counter(product["brand"] for product in purchased_products if product.get("brand"))

    search_records = load_search_records(search_history_path)
    searched_categories = Counter(
        record["criteria"]["category"] for record in search_records if record["criteria"]["category"]
    )
    searched_brands = Counter(record["criteria"]["brand"] for record in search_records if record["criteria"]["brand"])
    searched_products = Counter(product_id for record in search_records for product_id in record["product_ids"])

    ranked_products = []
    for product in catalog_products:
        if product["product_id"] in purchased_ids:
            continue
        score = (
            category_counter[product["category"]] * 3
            + brand_counter[product["brand"]] * 2
            + searched_categories[product["category"]]
            + searched_brands[product["brand"]]
            + searched_products[product["product_id"]]
        )
        if score == 0:
            continue
        ranked_products.append((score, product["price"], product["name"], product))

    if not ranked_products:
        ranked_products = [
            (0, product["price"], product["name"], product)
            for product in catalog_products
            if product["product_id"] not in purchased_ids
        ]

    ranked_products.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in ranked_products[:limit]]


def evaluate_return_request(catalog_path, purchase_history_path, request_data):
    order_id = request_data["order_id"]
    user_id = request_data.get("user_id")
    requested_product_ids = set(request_data.get("product_ids", []))

    matching_records = [record for record in load_purchase_records(purchase_history_path, user_id=user_id) if record["order_id"] == order_id]
    if not matching_records:
        return _build_return_decision(request_data, accepted=False, reason="La comanda no consta a l'historial de compres.")

    purchase_record = matching_records[-1]
    purchased_product_ids = set(purchase_record["product_ids"])
    if requested_product_ids and not requested_product_ids.issubset(purchased_product_ids):
        return _build_return_decision(
            request_data,
            accepted=False,
            reason="Els productes demanats no coincideixen amb els productes registrats a la compra.",
        )

    purchase_date = _parse_date(purchase_record.get("purchase_date"))
    if purchase_date is not None:
        age_days = (date.today() - purchase_date).days
        if age_days > 30:
            return _build_return_decision(
                request_data,
                accepted=False,
                reason="La compra supera el termini de devolució de 30 dies.",
            )

    purchased_products = get_products_by_ids(catalog_path, list(purchased_product_ids))
    amount = request_data.get("amount")
    if amount is None:
        amount = round(sum(product.get("price", 0.0) for product in purchased_products), 2)

    return _build_return_decision(
        {
            **request_data,
            "amount": amount,
            "product_ids": sorted(requested_product_ids or purchased_product_ids),
        },
        accepted=True,
        reason="La comanda compleix els criteris de devolució disponibles a l'historial.",
    )


def get_feedback_context(purchase_history_path, user_id=None):
    if user_id:
        purchase = get_latest_purchase_for_user(purchase_history_path, user_id)
        if purchase is not None:
            return purchase
    purchases = load_purchase_records(purchase_history_path)
    return purchases[-1] if purchases else None


def _build_return_decision(request_data, accepted, reason):
    return {
        "return_id": request_data["return_id"],
        "order_id": request_data["order_id"],
        "user_id": request_data.get("user_id", ""),
        "amount": request_data.get("amount", 0.0),
        "reason": reason,
        "accepted": accepted,
        "product_ids": sorted(request_data.get("product_ids", [])),
        "seller_id": request_data.get("seller_id"),
    }


def _empty_criteria():
    return {"text": "", "category": "", "brand": "", "min_price": None, "max_price": None}


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None