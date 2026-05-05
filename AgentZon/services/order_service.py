from uuid import uuid4

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.domain import OrderRecord, ProductRecord, UserShippingData
from AgentZon.services.rdf_store import RDFFileStore


class OrderService:
    def __init__(self, orders_path, shipping_path):
        self.orders_store = RDFFileStore(orders_path)
        self.shipping_store = RDFFileStore(shipping_path)

    def save_user_shipping_data(self, shipping_data: UserShippingData):
        graph = self.shipping_store.load_graph()
        bind_namespaces(graph)
        node = AZON[f"shipping-{shipping_data.user_id}"]
        graph.add((node, RDF.type, AZON.DadesEnviamentUsuari))
        graph.add((node, AZON.idUsuari, Literal(shipping_data.user_id)))
        graph.add((node, AZON.nom, Literal(shipping_data.user_name)))
        graph.add((node, AZON.carrer, Literal(shipping_data.street_address)))
        graph.add((node, AZON.ciutat, Literal(shipping_data.city)))
        graph.add((node, AZON.prioritat, Literal(shipping_data.priority)))
        graph.add((node, AZON.metodePagament, Literal(shipping_data.payment_method)))
        self.shipping_store.save_graph(graph)

    def create_order(self, shipping_data: UserShippingData, products: list[ProductRecord]):
        order = OrderRecord(
            order_id=f"ORDER-{uuid4().hex[:8].upper()}",
            user_id=shipping_data.user_id,
            user_name=shipping_data.user_name,
            products=products,
            shipping_data=shipping_data,
        )
        graph = self.orders_store.load_graph()
        bind_namespaces(graph)
        node = AZON[f"order-{order.order_id}"]
        graph.add((node, RDF.type, AZON.Comanda))
        graph.add((node, AZON.idComanda, Literal(order.order_id)))
        graph.add((node, AZON.idUsuari, Literal(order.user_id)))
        graph.add((node, AZON.nom, Literal(order.user_name)))
        graph.add((node, AZON.carrer, Literal(order.shipping_data.street_address)))
        graph.add((node, AZON.ciutat, Literal(order.shipping_data.city)))
        graph.add((node, AZON.prioritat, Literal(order.shipping_data.priority)))
        for product in order.products:
            graph.add((node, AZON.teProducte, AZON[f"product-{product.product_id}"]))
        self.orders_store.save_graph(graph)
        return order
