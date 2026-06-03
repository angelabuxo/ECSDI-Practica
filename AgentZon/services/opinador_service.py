"""Business rules for feedback, recommendations, and return checks."""

from collections import Counter
from datetime import date, datetime

from services.catalog_service import get_products_by_ids, search_products
from services.history_service import (
    get_latest_purchase_for_user,
    load_feedback_records,
    load_purchase_records,
    load_search_records,
)
from services.retornador_service import (
    MAX_RETURN_DAYS,
    RETURN_REASONS_ACCEPTED_BY_POLICY,
    RETURN_REJECTION_MESSAGE,
)

# Temps mínim des de la compra abans de demanar feedback.
MIN_DAYS_BEFORE_FEEDBACK = 14


def generate_recommendations(catalog_path, search_history_path, purchase_history_path, user_id=None, limit=5):
    catalog_products = search_products(catalog_path, _empty_criteria())
    purchase_records = load_purchase_records(purchase_history_path, user_id=user_id)
    purchased_ids = {product_id for record in purchase_records for product_id in record["product_ids"]}

    purchased_products = get_products_by_ids(catalog_path, list(purchased_ids)) if purchased_ids else []
    category_counter = Counter(product["category"] for product in purchased_products if product.get("category"))
    brand_counter = Counter(product["brand"] for product in purchased_products if product.get("brand"))

    search_records = load_search_records(search_history_path, user_id=user_id)
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


def _is_product_return_eligible(purchase_history_path, user_id, order_id, product_id, return_reason):
    """Comprova si un producte concret d'una comanda pot retornar-se."""
    if return_reason not in RETURN_REASONS_ACCEPTED_BY_POLICY:
        return False

    matching_records = [
        record
        for record in load_purchase_records(purchase_history_path, user_id=user_id)
        if record["order_id"] == order_id
    ]
    if not matching_records:
        return False

    purchase_record = matching_records[-1]
    if product_id not in set(purchase_record.get("product_ids", [])):
        return False

    purchase_date = _parse_date(purchase_record.get("purchase_date"))
    if purchase_date is None:
        return True

    return (date.today() - purchase_date).days <= MAX_RETURN_DAYS


def evaluate_return_request(catalog_path, purchase_history_path, request_data):
    order_id = request_data["order_id"]
    user_id = request_data.get("user_id")
    requested_product_ids = list(request_data.get("product_ids", []))
    return_reason = (request_data.get("reason") or "").strip()

    if return_reason not in RETURN_REASONS_ACCEPTED_BY_POLICY:
        return _build_return_decision(
            request_data,
            accepted=False,
            reason=RETURN_REJECTION_MESSAGE,
            accepted_product_ids=[],
            requested_product_ids=requested_product_ids,
        )

    matching_records = [
        record
        for record in load_purchase_records(purchase_history_path, user_id=user_id)
        if record["order_id"] == order_id
    ]
    if not matching_records:
        return _build_return_decision(
            request_data,
            accepted=False,
            reason=RETURN_REJECTION_MESSAGE,
            accepted_product_ids=[],
            requested_product_ids=requested_product_ids,
        )

    purchase_record = matching_records[-1]
    purchased_product_ids = sorted(set(purchase_record.get("product_ids", [])))
    if not requested_product_ids:
        requested_product_ids = purchased_product_ids

    accepted_product_ids = [
        product_id
        for product_id in requested_product_ids
        if _is_product_return_eligible(
            purchase_history_path,
            user_id,
            order_id,
            product_id,
            return_reason,
        )
    ]

    if not accepted_product_ids:
        return _build_return_decision(
            request_data,
            accepted=False,
            reason=RETURN_REJECTION_MESSAGE,
            accepted_product_ids=[],
            requested_product_ids=requested_product_ids,
        )

    target_products = get_products_by_ids(catalog_path, accepted_product_ids)
    amount = request_data.get("amount")
    if amount is None:
        amount = round(sum(product.get("price", 0.0) for product in target_products), 2)

    partial = len(accepted_product_ids) < len(requested_product_ids)
    if partial:
        resolution_reason = (
            f"Només {len(accepted_product_ids)} de {len(requested_product_ids)} productes "
            f"de la comanda compleixen la política."
        )
    else:
        resolution_reason = "La devolució compleix les condicions de la política de devolució."

    return _build_return_decision(
        {
            **request_data,
            "amount": amount,
            "product_ids": sorted(accepted_product_ids),
        },
        accepted=True,
        reason=resolution_reason,
        accepted_product_ids=sorted(accepted_product_ids),
        requested_product_ids=requested_product_ids,
    )


def evaluate_multi_order_return(catalog_path, purchase_history_path, return_request):
    """Avalua cada comanda de la selecció per separat (termini de 15 dies per comanda)."""
    order_decisions = {}
    for order_id, product_ids in return_request["order_groups"].items():
        decision = evaluate_return_request(
            catalog_path,
            purchase_history_path,
            {
                "return_id": f"{return_request['return_id']}-{order_id}",
                "order_id": order_id,
                "user_id": return_request["user_id"],
                "reason": return_request["reason"],
                "product_ids": product_ids,
            },
        )
        decision["requested_product_ids"] = product_ids
        order_decisions[order_id] = decision
    return order_decisions


def get_feedback_context(purchase_history_path, user_id=None):
    if not user_id:
        return None
    return get_latest_purchase_for_user(purchase_history_path, user_id)


def list_known_user_ids(purchase_history_path, search_history_path):
    user_ids = set()
    for record in load_purchase_records(purchase_history_path):
        if record.get("user_id"):
            user_ids.add(record["user_id"])
    for record in load_search_records(search_history_path):
        if record.get("user_id"):
            user_ids.add(record["user_id"])
    return sorted(user_ids)


def _parse_purchase_datetime(purchase_date):
    if not purchase_date:
        return None
    raw = str(purchase_date).strip()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        parsed_date = _parse_date(raw)
        if parsed_date is None:
            return None
        return datetime.combine(parsed_date, datetime.min.time())


def _reference_datetime(reference_date=None, reference_time=None):
    if reference_time is not None:
        return reference_time
    if reference_date is None:
        return datetime.now()
    if isinstance(reference_date, datetime):
        return reference_date
    return datetime.combine(reference_date, datetime.max.time())


def seconds_since_purchase(purchase_date, reference_time=None):
    parsed = _parse_purchase_datetime(purchase_date)
    if parsed is None:
        return 0
    now = _reference_datetime(reference_time=reference_time)
    return max(0, int((now - parsed).total_seconds()))


def days_since_purchase(purchase_date, reference_date=None):
    return seconds_since_purchase(purchase_date, reference_time=_reference_datetime(reference_date)) // 86400


def is_feedback_eligible(
    purchase_date,
    min_days=MIN_DAYS_BEFORE_FEEDBACK,
    min_seconds=None,
    reference_date=None,
    reference_time=None,
):
    if min_seconds is not None:
        return seconds_since_purchase(purchase_date, reference_time=reference_time) >= min_seconds
    return days_since_purchase(purchase_date, reference_date=reference_date) >= min_days


def get_purchases_pending_feedback(
    purchase_history_path,
    feedback_path,
    catalog_path,
    user_id,
    min_days=MIN_DAYS_BEFORE_FEEDBACK,
    min_seconds=None,
    reference_date=None,
    reference_time=None,
):
    """Productes comprats sense feedback, separats per elegibles i pendents de temps."""
    feedbacks = load_feedback_records(feedback_path, user_id=user_id)
    reviewed_product_ids = {pid for fb in feedbacks for pid in fb.get("product_ids", [])}
    purchases = load_purchase_records(purchase_history_path, user_id=user_id)

    eligible_entries = []
    waiting_entries = []
    seen_product_ids = set()

    for purchase in purchases:
        purchase_date = purchase.get("purchase_date", "")
        elapsed_seconds = seconds_since_purchase(purchase_date, reference_time=reference_time)
        days_elapsed = elapsed_seconds // 86400
        for product_id in purchase.get("product_ids", []):
            if product_id in reviewed_product_ids or product_id in seen_product_ids:
                continue
            seen_product_ids.add(product_id)
            if min_seconds is not None:
                until_eligible = max(0, min_seconds - elapsed_seconds)
            else:
                until_eligible = max(0, min_days - days_elapsed)
            entry = {
                "product_id": product_id,
                "order_id": purchase["order_id"],
                "purchase_date": purchase_date,
                "days_since_purchase": days_elapsed,
                "seconds_since_purchase": elapsed_seconds,
                "days_until_eligible": until_eligible if min_seconds is None else 0,
                "seconds_until_eligible": until_eligible if min_seconds is not None else 0,
            }
            if is_feedback_eligible(
                purchase_date,
                min_days=min_days,
                min_seconds=min_seconds,
                reference_date=reference_date,
                reference_time=reference_time,
            ):
                eligible_entries.append(entry)
            else:
                waiting_entries.append(entry)

    eligible_ids = [entry["product_id"] for entry in eligible_entries]
    products_by_id = {
        product["product_id"]: product
        for product in get_products_by_ids(catalog_path, eligible_ids)
    }

    eligible_products = []
    for entry in eligible_entries:
        product = products_by_id.get(entry["product_id"])
        if product is None:
            continue
        eligible_products.append({**product, **entry})

    waiting_products = []
    waiting_ids = [entry["product_id"] for entry in waiting_entries]
    waiting_by_id = {
        product["product_id"]: product
        for product in get_products_by_ids(catalog_path, waiting_ids)
    }
    for entry in waiting_entries:
        product = waiting_by_id.get(entry["product_id"])
        if product is None:
            continue
        waiting_products.append({**product, **entry})

    return {
        "eligible_products": eligible_products,
        "waiting_products": waiting_products,
    }


def build_feedback_requests_for_user(
    purchase_history_path,
    feedback_path,
    catalog_path,
    user_id,
    min_days=MIN_DAYS_BEFORE_FEEDBACK,
    min_seconds=None,
    reference_date=None,
    reference_time=None,
):
    pending = get_purchases_pending_feedback(
        purchase_history_path,
        feedback_path,
        catalog_path,
        user_id,
        min_days=min_days,
        min_seconds=min_seconds,
        reference_date=reference_date,
        reference_time=reference_time,
    )
    requests = []
    for product in pending["eligible_products"]:
        feedback_id = f"FB-REQ-{product['product_id']}-{product['order_id']}"
        requests.append(
            {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "order_id": product["order_id"],
                "prompt": (
                    f"Fa {product.get('seconds_since_purchase', product['days_since_purchase'])} "
                    f"{'segons' if min_seconds is not None else 'dies'} que vas comprar "
                    f"{product.get('name', product['product_id'])}. "
                    "Ens agradaria conèixer la teva opinió."
                ),
                "products": [product],
                "product_ids": [product["product_id"]],
            }
        )
    return requests


def _build_return_decision(
    request_data,
    accepted,
    reason,
    accepted_product_ids=None,
    requested_product_ids=None,
):
    product_ids = sorted(accepted_product_ids if accepted_product_ids is not None else request_data.get("product_ids", []))
    amount = request_data.get("amount")
    if amount is None:
        amount = 0.0
    return {
        "return_id": request_data["return_id"],
        "order_id": request_data["order_id"],
        "user_id": request_data.get("user_id", ""),
        "amount": amount,
        "reason": reason,
        "accepted": accepted,
        "product_ids": product_ids,
        "accepted_product_ids": product_ids,
        "requested_product_ids": sorted(
            requested_product_ids if requested_product_ids is not None else request_data.get("product_ids", [])
        ),
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