"""Recommendation helpers based on purchase and search histories."""

from collections import Counter

from services.catalog_service import search_products
from services.rdf_store import load_graph
from AgentUtil.OntoNamespaces import AZON


def generate_recommendations(search_history_path, purchase_history_path, catalog_path, user_id=None, limit=5):
    search_graph = load_graph(search_history_path)
    purchase_graph = load_graph(purchase_history_path)

    product_counter = Counter()
    for search in search_graph.subjects(predicate=AZON.TotalResultats):
        for product_node in search_graph.objects(search, AZON.MostraProducte):
            product_id = search_graph.value(product_node, AZON.IdProducte)
            if product_id is not None:
                product_counter[str(product_id)] += 1

    for purchase in purchase_graph.subjects(predicate=AZON.IdComanda):
        if user_id is not None and str(purchase_graph.value(purchase, AZON.IdUsuari)) != user_id:
            continue
        for product_node in purchase_graph.objects(purchase, AZON.SobreProducte):
            product_counter[str(product_node).rsplit("product-", 1)[-1]] += 2

    if not product_counter:
        return []

    ranked_product_ids = [product_id for product_id, _ in product_counter.most_common(limit)]
    catalog = search_products(catalog_path, {"text": "", "category": "", "brand": "", "min_price": None, "max_price": None})
    catalog_by_id = {product["product_id"]: product for product in catalog}
    return [catalog_by_id[product_id] for product_id in ranked_product_ids if product_id in catalog_by_id]
