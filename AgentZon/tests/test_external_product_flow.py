"""Tests for the external-seller product registration flow."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, RDF


class ExternalProductFlowTests(unittest.TestCase):
    def test_alta_producte_extern_round_trip_keeps_key_fields(self):
        from AgentUtil.OntoNamespaces import AZON
        from protocols.venedor_extern import build_alta_producte_extern, parse_alta_producte_extern

        request_graph = build_alta_producte_extern(
            "external-product-1",
            product_id="PX-1",
            seller_id="SELLER-1",
            bank_details="IBAN-ES00-0000-0000-0000-0000-0000",
            name="Outdoor Speaker",
            description="Portable waterproof speaker",
            category="audio",
            brand="AuralMax",
            price=74.95,
            weight=1.2,
            sku_extern="SKU-EXT-1",
            warehouse_city="Barcelona",
            requires_external_shipping=True,
            data_alta="2026-05-21",
        )
        content = request_graph.value(predicate=RDF.type, object=AZON.AltaProducteExtern)
        parsed = parse_alta_producte_extern(request_graph, content)

        self.assertEqual(parsed["product_id"], "PX-1")
        self.assertEqual(parsed["seller_id"], "SELLER-1")
        self.assertEqual(parsed["bank_details"], "IBAN-ES00-0000-0000-0000-0000-0000")
        self.assertEqual(parsed["sku_extern"], "SKU-EXT-1")
        self.assertEqual(parsed["warehouse_city"], "Barcelona")
        self.assertTrue(parsed["requires_external_shipping"])

    def test_external_product_services_persist_expected_triples(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.external_product_service import (
            save_external_product,
            save_product_location,
            save_shipping_responsibility,
            save_vendor_bank_data,
        )
        from services.rdf_store import load_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            catalog_path = data_dir / "productes.ttl"
            responsibility_path = data_dir / "responsable_enviament_productes.ttl"
            location_path = data_dir / "ubicacions_productes.ttl"
            bank_path = data_dir / "dades_bancaries_venedors_externs.ttl"

            product = {
                "product_id": "PX-1",
                "seller_id": "SELLER-1",
                "bank_details": "IBAN-ES00-0000-0000-0000-0000-0000",
                "name": "Outdoor Speaker",
                "description": "Portable waterproof speaker",
                "category": "audio",
                "brand": "AuralMax",
                "price": 74.95,
                "weight": 1.2,
                "sku_extern": "SKU-EXT-1",
                "warehouse_city": "Barcelona",
                "requires_external_shipping": True,
            }

            save_external_product(catalog_path, product)
            save_shipping_responsibility(responsibility_path, product)
            save_product_location(location_path, product)
            save_vendor_bank_data(bank_path, product)

            catalog = load_graph(catalog_path)
            product_node = AZON["product-PX-1"]
            self.assertIn((product_node, RDF.type, AZON.ProducteExtern), catalog)
            self.assertIn((product_node, AZON.SkuExtern, None), catalog)

            responsibility = load_graph(responsibility_path)
            self.assertIn((product_node, AZON.RequereixLogisticaExterna, None), responsibility)

            locations = load_graph(location_path)
            centre = AZON["centre-extern-SELLER-1"]
            self.assertIn((product_node, AZON.UbicatACentre, centre), locations)

            bank_graph = load_graph(bank_path)
            seller_node = AZON["vendor-SELLER-1"]
            self.assertIn((seller_node, RDF.type, AZON.VenedorExtern), bank_graph)
            self.assertIn((seller_node, AZON.DadesBancariesVenedorExtern, None), bank_graph)

    def test_venedor_extern_coordinates_search_and_local_persistence(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_cercador, agent_venedor_extern
        from protocols.venedor_extern import build_alta_producte_extern
        from services.bootstrap import bootstrap_phase2_data
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")

        seller = Agent(
            "VenedorExternAgent",
            agn.VenedorExtern,
            "http://seller.test/comm",
            "http://seller.test/Stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://search.test/comm",
            "http://search.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)
            router = LocalMessageRouter()

            agent_cercador.configure_runtime(
                {
                    "agent": cercador,
                    "directory_agent": None,
                    "data_dir": data_dir,
                },
                message_sender=router.send_message,
            )
            agent_venedor_extern.configure_runtime(
                {
                    "agent": seller,
                    "directory_agent": None,
                    "data_dir": data_dir,
                },
                message_sender=router.send_message,
                agent_resolver={
                    AZON.CercadorAgent: cercador,
                }.__getitem__,
            )

            router.register_app(cercador.address, agent_cercador.app)
            router.register_app(seller.address, agent_venedor_extern.app)

            request_graph = build_alta_producte_extern(
                "external-product-1",
                product_id="PX-1",
                seller_id="SELLER-1",
                bank_details="IBAN-ES00-0000-0000-0000-0000-0000",
                name="Outdoor Speaker",
                description="Portable waterproof speaker",
                category="audio",
                brand="AuralMax",
                price=74.95,
                weight=1.2,
                sku_extern="SKU-EXT-1",
                warehouse_city="Barcelona",
                requires_external_shipping=True,
                data_alta="2026-05-21",
                sender=seller.uri,
                receiver=seller.uri,
                msgcnt=1,
            )

            response = router.send_message(request_graph, seller.address)
            properties = get_message_properties(response)
            content = properties["content"]

            self.assertEqual(response.value(content, RDF.type), AZON.ConfirmacioAltaProducteExtern)

            catalog_graph = Graph()
            catalog_graph.parse(data=(data_dir / "productes.ttl").read_text(encoding="utf-8"), format="turtle")
            self.assertIn((AZON["product-PX-1"], RDF.type, AZON.ProducteExtern), catalog_graph)

            responsibility_graph = Graph()
            responsibility_graph.parse(
                data=(data_dir / "responsable_enviament_productes.ttl").read_text(encoding="utf-8"),
                format="turtle",
            )
            self.assertIn((AZON["product-PX-1"], AZON.RequereixLogisticaExterna, None), responsibility_graph)

            bank_graph = Graph()
            bank_graph.parse(
                data=(data_dir / "dades_bancaries_venedors_externs.ttl").read_text(encoding="utf-8"),
                format="turtle",
            )
            self.assertIn((AZON["vendor-SELLER-1"], RDF.type, AZON.VenedorExtern), bank_graph)


if __name__ == "__main__":
    unittest.main()