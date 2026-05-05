from rdflib import Graph

from AgentZon.AgentUtil.OntoNamespaces import AZON
from AgentZon.domain import ProductRecord, SearchCriteria
from AgentZon.services.rdf_store import RDFFileStore


class CatalogService:
    def __init__(self, catalog_path):
        self.store = RDFFileStore(catalog_path)

    def search_products(self, criteria: SearchCriteria):
        graph = self.store.load_graph()
        query = """
            PREFIX azon: <http://www.semanticweb.org/agentzon#>
            SELECT ?id ?name ?description ?category ?brand ?price ?weight
            WHERE {
                ?product a azon:Producte ;
                    azon:idProducte ?id ;
                    azon:nom ?name ;
                    azon:descripcio ?description ;
                    azon:categoria ?category ;
                    azon:marca ?brand ;
                    azon:preu ?price ;
                    azon:pes ?weight .
            }
        """
        rows = graph.query(query)
        results = []
        lowered_text = criteria.text.lower()
        for row in rows:
            product = ProductRecord(
                product_id=str(row.id),
                name=str(row.name),
                description=str(row.description),
                category=str(row.category),
                brand=str(row.brand),
                price=float(row.price),
                weight=float(row.weight),
            )
            haystack = f"{product.name} {product.description}".lower()
            if lowered_text and lowered_text not in haystack:
                continue
            if criteria.category and product.category != criteria.category:
                continue
            if criteria.brand and product.brand != criteria.brand:
                continue
            if criteria.min_price is not None and product.price < criteria.min_price:
                continue
            if criteria.max_price is not None and product.price > criteria.max_price:
                continue
            results.append(product)
        return results

    def get_products_by_ids(self, product_ids):
        wanted = set(product_ids)
        return [product for product in self.search_products(SearchCriteria()) if product.product_id in wanted]
