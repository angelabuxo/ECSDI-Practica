from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.domain import OrderRecord, SearchCriteria
from AgentZon.services.rdf_store import RDFFileStore


class SearchHistoryService:
    def __init__(self, path):
        self.store = RDFFileStore(path)

    def record_search(self, criteria: SearchCriteria, products):
        graph = self.store.load_graph()
        bind_namespaces(graph)
        record = AZON[f"search-{len(graph)}"]
        graph.add((record, RDF.type, AZON.PeticioCerca))
        graph.add((record, AZON.teText, Literal(criteria.text)))
        graph.add((record, AZON.teCategoria, Literal(criteria.category)))
        graph.add((record, AZON.teMarca, Literal(criteria.brand)))
        graph.add((record, AZON.totalResultats, Literal(len(products))))
        for product in products:
            graph.add((record, AZON.mostraProducte, AZON[f"product-{product.product_id}"]))
        self.store.save_graph(graph)


class PurchaseHistoryService:
    def __init__(self, path):
        self.store = RDFFileStore(path)

    def record_purchase(self, order: OrderRecord):
        graph = self.store.load_graph()
        bind_namespaces(graph)
        record = AZON[f"purchase-{order.order_id}"]
        graph.add((record, RDF.type, AZON.HistorialCompra))
        graph.add((record, AZON.idComanda, Literal(order.order_id)))
        graph.add((record, AZON.idUsuari, Literal(order.user_id)))
        for product in order.products:
            graph.add((record, AZON.idProducte, Literal(product.product_id)))
        self.store.save_graph(graph)
