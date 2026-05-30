"""Test support helpers for in-process AgentZon message routing."""

from urllib.parse import urlparse

from rdflib import Graph


class LocalMessageRouter:
    def __init__(self):
        self._clients = {}

    def register_app(self, address, app):
        self._clients[address] = app.test_client()

    def send_message(self, gmess, address):
        client = self._clients[address]
        path = urlparse(address).path or "/"
        response = client.get(path, query_string={"content": gmess.serialize(format="xml")})
        graph = Graph()
        graph.parse(data=response.get_data(as_text=True), format="xml")
        return graph


def load_catalog_products(catalog_path):
    from services.catalog_service import search_products

    products = search_products(
        catalog_path,
        {
            "text": "",
            "category": "",
            "brand": "",
            "min_price": None,
            "max_price": None,
        },
    )
    return sorted(products, key=lambda product: product["product_id"])
