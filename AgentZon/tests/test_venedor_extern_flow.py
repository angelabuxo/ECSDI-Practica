"""Tests for external vendor registration and purchase branching."""

import shutil
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from AgentUtil.OntoNamespaces import AZON
from services.rdf_store import load_graph
from tests.support import LocalMessageRouter, load_catalog_products


VENDOR_EXTERN_AGENT_TYPE = URIRef("http://www.semanticweb.org/directory-service-ontology#VenedorExternAgent")


def _sample_product(product_id="P1030", requires_external_logistics=True, centre_id="CL-BCN"):
    return {
        "product_id": product_id,
        "name": "External Headphones",
        "description": "Wireless headphones from external vendor",
        "category": "audio",
        "brand": "ExtBrand",
        "price": 79.99,
        "weight": 0.4,
        "sku_extern": "EXT-HP-001",
        "data_alta": "2026-06-02",
        "requires_external_logistics": requires_external_logistics,
        "centre_id": centre_id,
    }


def _sample_seller():
    return {"seller_id": "VE-TECH", "bank_data": "ES12 2100 1234 5678 9012"}


class VenedorExternFlowTests(unittest.TestCase):
    def test_vendor_registration_writes_shipping_metadata_via_compra(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_cercador, agent_cobrador, agent_compra, agent_directory, agent_venedor_extern
        from protocols.compra import parse_peticio_registre_producte_extern_compra
        from protocols.directory import build_register_message
        from protocols.venedor_extern import build_alta_producte_extern
        from services.bootstrap import bootstrap_phase2_data

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
        venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")
        router = LocalMessageRouter()
        compra_messages = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_cercador.configure_runtime({"agent": cercador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cercador.address, agent_cercador.app)
            agent_cobrador.configure_runtime({"agent": cobrador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cobrador.address, agent_cobrador.app)
            agent_compra.configure_runtime({"agent": compra, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(compra.address, agent_compra.app)

            def venedor_sender(message, address):
                if address == compra.address:
                    compra_messages.append(parse_peticio_registre_producte_extern_compra(message))
                if address in {directory.address, compra.address, cercador.address, cobrador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_venedor_extern.configure_runtime(
                {"agent": venedor, "directory_agent": directory, "data_dir": data_dir},
                message_sender=venedor_sender,
            )
            router.register_app(venedor.address, agent_venedor_extern.app)

            for msgcnt, agent, agent_type in [
                (1, compra, DSO.CompraAgent),
                (2, cercador, DSO.CercadorAgent),
                (3, cobrador, DSO.CobradorAgent),
                (4, venedor, VENDOR_EXTERN_AGENT_TYPE),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt)
                router.send_message(register_graph, directory.address)

            alta = build_alta_producte_extern(_sample_product(product_id="P1030"), _sample_seller(), request_id="alta-compra", msgcnt=10)
            router.send_message(alta, venedor.address)

            self.assertEqual(compra_messages[0]["product_id"], "P1030")
            self.assertTrue(compra_messages[0]["requires_external_logistics"])

    def test_vendor_iface_reads_profile_via_cobrador_query(self):
        from AgentUtil.Agent import Agent
        from agents import agent_venedor_extern
        from protocols.pagament import build_resultat_consulta_dades_venedor

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
        venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            agent_venedor_extern.configure_runtime(
                {"agent": venedor, "directory_agent": directory, "data_dir": data_dir}
            )

            previous_sender = agent_venedor_extern.MESSAGE_SENDER
            previous_resolver = agent_venedor_extern.resolve_cobrador_agent
            try:
                agent_venedor_extern.MESSAGE_SENDER = lambda message, address: build_resultat_consulta_dades_venedor(
                    {
                        "seller_id": "10.0.0.1",
                        "bank_data": "ES12 2100 1234 5678 9012",
                        "seller_name": "Vendor",
                    },
                    sender=cobrador.uri,
                    receiver=venedor.uri,
                    msgcnt=2,
                )
                agent_venedor_extern.resolve_cobrador_agent = lambda: cobrador
                with agent_venedor_extern.app.test_request_context("/iface"):
                    html = agent_venedor_extern.render_iface_page("10.0.0.1")
            finally:
                agent_venedor_extern.MESSAGE_SENDER = previous_sender
                agent_venedor_extern.resolve_cobrador_agent = previous_resolver

            self.assertIn("Vendor", html)

    def test_protocol_roundtrip(self):
        from protocols.venedor_extern import (
            build_alta_producte_extern,
            build_confirmacio_alta_producte_extern,
            build_peticio_enviament_extern,
            parse_alta_producte_extern,
            parse_confirmacio_alta_producte_extern,
            parse_peticio_enviament_extern,
        )

        product = _sample_product()
        seller = _sample_seller()
        alta = build_alta_producte_extern(product, seller, request_id="alta-test-1", msgcnt=1)
        parsed = parse_alta_producte_extern(alta, alta.value(predicate=RDF.type, object=AZON.AltaProducteExtern))
        self.assertEqual(parsed["product"]["product_id"], "P1030")
        self.assertEqual(parsed["seller"]["seller_id"], "VE-TECH")

        confirm = build_confirmacio_alta_producte_extern("P1030", "EXT-HP-001", msgcnt=2)
        confirm_parsed = parse_confirmacio_alta_producte_extern(confirm)
        self.assertEqual(confirm_parsed["product_id"], "P1030")

        order = {
            "order_id": "ORD-EXT-1",
            "shipping_data": {
                "city": "Barcelona",
                "street_address": "Gran Via 1",
                "priority": "5 dies",
            },
            "products": [product],
        }
        shipping_request = build_peticio_enviament_extern(order, seller["seller_id"], msgcnt=3)
        shipping_parsed = parse_peticio_enviament_extern(
            shipping_request,
            shipping_request.value(predicate=RDF.type, object=AZON.PeticioEnviamentExtern),
        )
        self.assertEqual(shipping_parsed["order_id"], "ORD-EXT-1")
        self.assertEqual(len(shipping_parsed["products"]), 1)

    def test_registration_integration(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_cercador, agent_cobrador, agent_compra, agent_directory, agent_venedor_extern
        from protocols.directory import build_register_message
        from protocols.venedor_extern import build_alta_producte_extern, parse_confirmacio_alta_producte_extern
        from services.bootstrap import bootstrap_phase2_data
        from services.catalog_service import search_products
        from services.external_vendor_service import load_shipping_responsibility_by_product

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")

        router = LocalMessageRouter()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            shutil.copy(data_dir / "ubicacions_productes.ttl", data_dir / "ubicacions_backup.ttl")

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_cercador.configure_runtime(
                {"agent": cercador, "directory_agent": directory, "data_dir": data_dir}
            )
            router.register_app(cercador.address, agent_cercador.app)
            agent_cobrador.configure_runtime(
                {"agent": cobrador, "directory_agent": directory, "data_dir": data_dir}
            )
            router.register_app(cobrador.address, agent_cobrador.app)
            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir}
            )
            router.register_app(compra.address, agent_compra.app)

            def venedor_sender(message, address):
                if address in {directory.address, compra.address, cercador.address, cobrador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_venedor_extern.configure_runtime(
                {"agent": venedor, "directory_agent": directory, "data_dir": data_dir},
                message_sender=venedor_sender,
            )
            router.register_app(venedor.address, agent_venedor_extern.app)

            for msgcnt, agent, agent_type in [
                (1, compra, DSO.CompraAgent),
                (2, cercador, DSO.CercadorAgent),
                (3, cobrador, DSO.CobradorAgent),
                (4, venedor, VENDOR_EXTERN_AGENT_TYPE),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt)
                router.send_message(register_graph, directory.address)

            product = _sample_product(product_id="P1030", requires_external_logistics=True)
            alta = build_alta_producte_extern(product, _sample_seller(), request_id="alta-integration", msgcnt=10)
            reply = router.send_message(alta, venedor.address)
            confirmation = parse_confirmacio_alta_producte_extern(reply)
            self.assertEqual(confirmation["product_id"], "P1030")

            catalog_hits = search_products(data_dir / "productes.ttl", {"text": "External Headphones"})
            self.assertEqual(len(catalog_hits), 1)
            responsibility = load_shipping_responsibility_by_product(data_dir / "ubicacions_productes.ttl")
            self.assertTrue(responsibility["P1030"]["requires_external_logistics"])

            seller_graph = load_graph(data_dir / "dades_bancaries_venedors_externs.ttl")
            bank_values = list(seller_graph.objects(predicate=AZON.DadesBancariesVenedorExtern))
            self.assertTrue(bank_values)

    def test_vendor_shipped_purchase(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_cobrador, agent_compra, agent_directory, agent_cercador, agent_opinador, agent_venedor_extern
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from protocols.venedor_extern import build_alta_producte_extern, parse_confirmacio_alta_producte_extern
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import load_graph as load_ttl

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")

        router = LocalMessageRouter()
        external_requests = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_cercador.configure_runtime({"agent": cercador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cercador.address, agent_cercador.app)
            agent_cobrador.configure_runtime({"agent": cobrador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cobrador.address, agent_cobrador.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def venedor_sender(message, address):
                if address in {directory.address, compra.address, cercador.address, cobrador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_venedor_extern.configure_runtime(
                {"agent": venedor, "directory_agent": directory, "data_dir": data_dir},
                message_sender=venedor_sender,
            )
            router.register_app(venedor.address, agent_venedor_extern.app)

            def compra_sender(message, address):
                if address == venedor.address:
                    external_requests.append(address)
                if address in {directory.address, cercador.address, opinador.address, cobrador.address, venedor.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=compra_sender,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type in [
                (1, compra, DSO.CompraAgent),
                (2, cercador, DSO.CercadorAgent),
                (3, cobrador, DSO.CobradorAgent),
                (4, opinador, DSO.OpinadorAgent),
                (5, venedor, VENDOR_EXTERN_AGENT_TYPE),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt)
                router.send_message(register_graph, directory.address)

            product = _sample_product(product_id="P1030", requires_external_logistics=True)
            alta = build_alta_producte_extern(product, _sample_seller(), request_id="alta-purchase", msgcnt=20)
            router.send_message(alta, venedor.address)

            purchase_message = build_peticio_compra(
                "purchase-external-vendor",
                user_id="USER-EXT",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "7 dies",
                },
                product_ids=["P1030"],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=30,
            )
            response = router.send_message(purchase_message, compra.address)
            parsed = extract_resultat_compra(response)

            self.assertEqual(external_requests, [venedor.address])
            self.assertEqual(len(parsed["lots"]), 1)
            self.assertEqual(parsed["lots"][0]["lot_id"], "EXTERN")

            payments = load_ttl(data_dir / "pagaments.ttl")
            sentit_values = {str(value) for value in payments.objects(None, AZON.SentitPagament)}
            self.assertIn("PAGAMENT", sentit_values)

    def test_platform_shipped_external_purchase(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_centre_logistic, agent_compra, agent_directory, agent_cercador, agent_cobrador, agent_opinador, agent_venedor_extern
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from protocols.venedor_extern import build_alta_producte_extern
        from services.bootstrap import bootstrap_phase2_data

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        centre = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")

        router = LocalMessageRouter()
        external_requests = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_cercador.configure_runtime({"agent": cercador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cercador.address, agent_cercador.app)
            agent_cobrador.configure_runtime({"agent": cobrador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cobrador.address, agent_cobrador.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def venedor_sender(message, address):
                if address in {directory.address, compra.address, cercador.address, cobrador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_venedor_extern.configure_runtime(
                {"agent": venedor, "directory_agent": directory, "data_dir": data_dir},
                message_sender=venedor_sender,
            )
            router.register_app(venedor.address, agent_venedor_extern.app)

            def centre_sender(message, address):
                if address in {directory.address, compra.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_centre_logistic.configure_runtime(
                {
                    "agent": centre,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                    "transport_agents": [],
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
                message_sender=centre_sender,
            )
            router.register_app(centre.address, agent_centre_logistic.app)

            def compra_sender(message, address):
                if address == venedor.address:
                    external_requests.append(address)
                if address in {directory.address, cercador.address, opinador.address, centre.address, cobrador.address, venedor.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=compra_sender,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, compra, DSO.CompraAgent, None),
                (2, centre, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: Literal("CL-BCN"), AZON.Ciutat: Literal("Barcelona")}),
                (3, cercador, DSO.CercadorAgent, None),
                (4, cobrador, DSO.CobradorAgent, None),
                (5, opinador, DSO.OpinadorAgent, None),
                (6, venedor, VENDOR_EXTERN_AGENT_TYPE, None),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt, metadata=metadata)
                router.send_message(register_graph, directory.address)

            product = _sample_product(product_id="P1030", requires_external_logistics=False, centre_id="CL-BCN")
            alta = build_alta_producte_extern(product, _sample_seller(), request_id="alta-platform", msgcnt=20)
            router.send_message(alta, venedor.address)

            purchase_message = build_peticio_compra(
                "purchase-platform-external",
                user_id="USER-PLAT",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "7 dies",
                },
                product_ids=["P1030"],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=30,
            )
            response = router.send_message(purchase_message, compra.address)
            parsed = extract_resultat_compra(response)

            self.assertEqual(external_requests, [])
            warehouse_lots = [lot for lot in parsed["lots"] if lot.get("lot_id") != "EXTERN"]
            self.assertEqual(len(warehouse_lots), 1)
            self.assertEqual(warehouse_lots[0]["centre_id"], "CL-BCN")

    def test_mixed_order_splits_internal_and_external_paths(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_centre_logistic, agent_compra, agent_directory, agent_cercador, agent_cobrador, agent_opinador, agent_venedor_extern
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from protocols.venedor_extern import build_alta_producte_extern
        from services.bootstrap import bootstrap_phase2_data

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        centre = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")

        router = LocalMessageRouter()
        external_requests = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            internal_product = load_catalog_products(data_dir / "productes.ttl")[0]

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_cercador.configure_runtime({"agent": cercador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cercador.address, agent_cercador.app)
            agent_cobrador.configure_runtime({"agent": cobrador, "directory_agent": directory, "data_dir": data_dir})
            router.register_app(cobrador.address, agent_cobrador.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def venedor_sender(message, address):
                if address in {directory.address, compra.address, cercador.address, cobrador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_venedor_extern.configure_runtime(
                {"agent": venedor, "directory_agent": directory, "data_dir": data_dir},
                message_sender=venedor_sender,
            )
            router.register_app(venedor.address, agent_venedor_extern.app)

            def centre_sender(message, address):
                if address in {directory.address, compra.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_centre_logistic.configure_runtime(
                {
                    "agent": centre,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                    "transport_agents": [],
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
                message_sender=centre_sender,
            )
            router.register_app(centre.address, agent_centre_logistic.app)

            def compra_sender(message, address):
                if address == venedor.address:
                    external_requests.append(address)
                if address in {directory.address, cercador.address, opinador.address, centre.address, cobrador.address, venedor.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=compra_sender,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, compra, DSO.CompraAgent, None),
                (2, centre, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: Literal("CL-BCN"), AZON.Ciutat: Literal("Barcelona")}),
                (3, cercador, DSO.CercadorAgent, None),
                (4, cobrador, DSO.CobradorAgent, None),
                (5, opinador, DSO.OpinadorAgent, None),
                (6, venedor, VENDOR_EXTERN_AGENT_TYPE, None),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt, metadata=metadata)
                router.send_message(register_graph, directory.address)

            external_product = _sample_product(product_id="P1030", requires_external_logistics=True)
            alta = build_alta_producte_extern(external_product, _sample_seller(), request_id="alta-mixed", msgcnt=20)
            router.send_message(alta, venedor.address)

            purchase_message = build_peticio_compra(
                "purchase-mixed",
                user_id="USER-MIX",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "7 dies",
                },
                product_ids=[internal_product["product_id"], "P1030"],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=30,
            )
            response = router.send_message(purchase_message, compra.address)
            parsed = extract_resultat_compra(response)

            self.assertEqual(external_requests, [venedor.address])
            warehouse_lots = [lot for lot in parsed["lots"] if lot.get("lot_id") != "EXTERN"]
            self.assertEqual(len(warehouse_lots), 1)
            self.assertEqual(warehouse_lots[0]["product"]["product_id"], internal_product["product_id"])
            lot_ids = {lot["lot_id"] for lot in parsed["lots"]}
            self.assertIn("EXTERN", lot_ids)


if __name__ == "__main__":
    unittest.main()
