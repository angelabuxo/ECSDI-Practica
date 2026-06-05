"""Flow tests for the Opinador agent."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from rdflib import Graph, Namespace, RDF

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AZON
from protocols.compra import build_peticio_registre_compra
from protocols.opinador import (
    build_peticio_consulta_comanda,
    build_peticio_consulta_compres_usuari,
    build_peticio_devolucio,
    parse_resolucio_devolucio,
    parse_resultat_consulta_comanda,
    parse_resultat_consulta_compres_usuari,
)
from services.bootstrap import bootstrap_phase2_data
from services.history_service import load_feedback_records, load_purchase_records, record_purchase
from services.opinador_service import (
    MIN_DAYS_BEFORE_FEEDBACK,
    generate_recommendations,
    get_purchases_pending_feedback,
    is_feedback_eligible,
)
from services.retornador_service import RETURN_REASON_DEFECTUOUS, RETURN_REJECTION_MESSAGE


def _test_runtime_settings(agent, data_dir):
    return {
        "agent": agent,
        "data_dir": data_dir,
        "feedback_min_seconds": 0,
        "feedback_policy_days": 14,
        "proactive_enabled": False,
    }


class OpinadorFlowTests(unittest.TestCase):
    def test_search_history_registration_persists_in_opinador(self):
        from agents import agent_opinador
        from protocols.opinador import build_peticio_registre_cerca
        from services.history_service import load_search_records

        agn = Namespace("http://www.agentes.org#")

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            opinador = Agent(
                "OpinadorAgent",
                agn.Opinador,
                "http://opinador.test/comm",
                "http://opinador.test/Stop",
            )
            agent_opinador.configure_runtime(
                {
                    "agent": opinador,
                    "directory_agent": None,
                    "data_dir": data_dir,
                    "proactive_enabled": False,
                }
            )
            client = agent_opinador.app.test_client()

            message = build_peticio_registre_cerca(
                {
                    "user_id": "USER-1",
                    "criteria": {
                        "text": "",
                        "category": "periferics",
                        "brand": "KeyCo",
                        "min_price": None,
                        "max_price": None,
                    },
                    "products": [
                        {
                            "product_id": "P1002",
                            "name": "Ratoli",
                            "category": "periferics",
                            "brand": "KeyCo",
                            "price": 20.0,
                            "weight": 0.2,
                        }
                    ],
                },
                sender=agn.Cercador,
                receiver=opinador.uri,
                msgcnt=1,
            )
            client.get("/comm", query_string={"content": message.serialize(format="xml")})

            stored = load_search_records(data_dir / "historial_cerques.ttl", user_id="USER-1")
            self.assertEqual(stored[0]["criteria"]["brand"], "KeyCo")
            self.assertEqual(stored[0]["product_ids"], ["P1002"])

    def test_opinador_recommendations_use_owned_histories_and_remote_catalog(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message
        from AgentUtil.OntoNamespaces import ONTOLOGY_URI
        from agents import agent_opinador
        from protocols.cerca import build_resultat_cerca
        from services.history_service import record_search

        agn = Namespace("http://www.agentes.org#")
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )
        calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            agent_opinador.configure_runtime(
                {
                    "agent": opinador,
                    "data_dir": data_dir,
                    "feedback_min_seconds": 0,
                    "proactive_enabled": False,
                }
            )

            record_search(
                data_dir / "historial_cerques.ttl",
                {
                    "text": "",
                    "category": "periferics",
                    "brand": "KeyCo",
                    "min_price": None,
                    "max_price": None,
                },
                [{"product_id": "P1002"}],
                user_id="USER-1",
            )
            record_purchase(
                data_dir / "historial_compres.ttl",
                {
                    "order_id": "ORDER-1",
                    "user_id": "USER-1",
                    "user_name": "User",
                    "purchase_date": "2026-06-01",
                    "delivery_date": "2026-06-03",
                    "shipping_data": {
                        "user_id": "USER-1",
                        "user_name": "User",
                        "street_address": "Gran Via 1",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                    "products": [
                        {
                            "product_id": "P1001",
                            "name": "Teclat",
                            "category": "periferics",
                            "brand": "KeyCo",
                            "price": 50.0,
                            "weight": 0.8,
                        }
                    ],
                },
            )

            def fake_sender(message, address):
                calls.append(address)
                request_content = message.value(predicate=RDF.type, object=AZON.PeticioCerca)
                payload, response_content = build_resultat_cerca(
                    "catalog-result-1",
                    [
                        {
                            "product_id": "P1001",
                            "name": "Teclat",
                            "description": "",
                            "category": "periferics",
                            "brand": "KeyCo",
                            "price": 50.0,
                            "weight": 0.8,
                        },
                        {
                            "product_id": "P1002",
                            "name": "Ratoli",
                            "description": "",
                            "category": "periferics",
                            "brand": "KeyCo",
                            "price": 20.0,
                            "weight": 0.2,
                        },
                    ],
                    request_content=request_content,
                )
                return build_message(
                    payload,
                    ACL.inform,
                    sender=cercador.uri,
                    receiver=opinador.uri,
                    content=response_content,
                    ontology=ONTOLOGY_URI,
                    msgcnt=3,
                )

            previous_sender = agent_opinador.MESSAGE_SENDER
            previous_resolver = agent_opinador.resolve_cercador_agent
            try:
                agent_opinador.MESSAGE_SENDER = fake_sender
                agent_opinador.resolve_cercador_agent = lambda: cercador
                recommendations = agent_opinador.pla_de_creacio_de_suggeriments("USER-1", limit=5)
            finally:
                agent_opinador.MESSAGE_SENDER = previous_sender
                agent_opinador.resolve_cercador_agent = previous_resolver

            self.assertEqual(calls, [cercador.address])
            self.assertEqual(recommendations[0]["product_id"], "P1002")

    def test_return_resolution_roundtrip_keeps_accepted_product_details(self):
        from protocols.opinador import build_resolucio_devolucio, parse_resolucio_devolucio

        message = build_resolucio_devolucio(
            {
                "return_id": "RET-1",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "amount": 50.0,
                "accepted": True,
                "reason": "OK",
                "product_ids": ["P1001"],
                "products": [
                    {
                        "product_id": "P1001",
                        "name": "Teclat",
                        "price": 50.0,
                        "seller_id": "SELLER-1",
                        "requires_external_logistics": True,
                    }
                ],
            },
            msgcnt=1,
        )
        parsed = parse_resolucio_devolucio(message)
        self.assertEqual(parsed["products"][0]["price"], 50.0)
        self.assertEqual(parsed["products"][0]["seller_id"], "SELLER-1")

    def test_generate_recommendations_excludes_already_purchased_products(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"

            all_recommendations = generate_recommendations(
                catalog_path,
                data_dir / "historial_cerques.ttl",
                data_dir / "historial_compres.ttl",
                limit=8,
            )
            self.assertTrue(all_recommendations)

            first_product = all_recommendations[0]

            record_purchase(
                data_dir / "historial_compres.ttl",
                {
                    "order_id": "ORDER-1",
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "products": [{"product_id": first_product["product_id"]}],
                    "shipping_data": {
                        "user_id": "USER-1",
                        "user_name": "Pol",
                        "street_address": "Gran Via 1",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
            )

            filtered_recommendations = generate_recommendations(
                catalog_path,
                data_dir / "historial_cerques.ttl",
                data_dir / "historial_compres.ttl",
                user_id="USER-1",
                limit=8,
            )
            self.assertNotIn(first_product["product_id"], {product["product_id"] for product in filtered_recommendations})

    def test_opinador_registers_purchase_feedback_and_return_resolution(self):
        from agents import agent_opinador

        client_ip = "10.0.0.10"

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"
            products = generate_recommendations(catalog_path, data_dir / "historial_cerques.ttl", data_dir / "historial_compres.ttl", limit=8)
            purchased_product = products[0]

            agent_opinador.configure_runtime(_test_runtime_settings(opinador, data_dir))
            client = agent_opinador.app.test_client()

            purchase_order = {
                "order_id": "ORDER-1",
                "user_id": client_ip,
                "user_name": "Pol",
                "products": [
                    {"product_id": purchased_product["product_id"], "name": purchased_product["name"], "price": purchased_product["price"]},
                ],
                "shipping_data": {
                    "user_id": client_ip,
                    "user_name": "Pol",
                    "street_address": "Gran Via 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            }

            purchase_message = build_peticio_registre_compra(
                purchase_order,
                sender=opinador.uri,
                receiver=opinador.uri,
                msgcnt=1,
            )
            purchase_response = client.get("/comm", query_string={"content": purchase_message.serialize(format="xml")})
            parsed_response = Graph()
            parsed_response.parse(data=purchase_response.get_data(as_text=True), format="xml")
            self.assertIsNotNone(parsed_response.value(predicate=RDF.type, object=AZON.ConfirmacioRegistreCompra))

            purchases = load_purchase_records(data_dir / "historial_compres.ttl")
            self.assertEqual(len(purchases), 1)
            self.assertEqual(purchases[0]["order_id"], "ORDER-1")

            feedback_response = client.post(
                "/iface",
                data={
                    "action": "feedback",
                    "rating": "5",
                    "product_id": purchased_product["product_id"],
                    "comment": "Bon servei",
                },
                environ_base={"REMOTE_ADDR": client_ip},
            )
            html = feedback_response.get_data(as_text=True)
            self.assertIn("Feedback registrat correctament per al producte seleccionat!", html)

            feedback_records = load_feedback_records(data_dir / "feedback.ttl")
            self.assertEqual(len(feedback_records), 1)
            self.assertEqual(feedback_records[0]["rating"], 5)
            self.assertEqual(feedback_records[0]["user_id"], client_ip)

            return_message = build_peticio_devolucio(
                {
                    "return_id": "RET-1",
                    "order_id": "ORDER-1",
                    "user_id": client_ip,
                    "amount": purchased_product["price"],
                    "reason": RETURN_REASON_DEFECTUOUS,
                    "products": [{"product_id": purchased_product["product_id"]}],
                },
                sender=opinador.uri,
                receiver=opinador.uri,
                msgcnt=2,
            )
            return_response = client.get("/comm", query_string={"content": return_message.serialize(format="xml")})
            return_graph = Graph()
            return_graph.parse(data=return_response.get_data(as_text=True), format="xml")
            decision = parse_resolucio_devolucio(return_graph)
            self.assertTrue(decision["accepted"])
            self.assertEqual(decision["return_id"], "RET-1")

            rejected_message = build_peticio_devolucio(
                {
                    "return_id": "RET-2",
                    "order_id": "ORDER-1",
                    "user_id": client_ip,
                    "amount": purchased_product["price"],
                    "reason": "No m'ha agradat",
                    "products": [{"product_id": purchased_product["product_id"]}],
                },
                sender=opinador.uri,
                receiver=opinador.uri,
                msgcnt=3,
            )
            rejected_response = client.get(
                "/comm",
                query_string={"content": rejected_message.serialize(format="xml")},
            )
            rejected_graph = Graph()
            rejected_graph.parse(data=rejected_response.get_data(as_text=True), format="xml")
            rejected_decision = parse_resolucio_devolucio(rejected_graph)
            self.assertFalse(rejected_decision["accepted"])
            self.assertEqual(rejected_decision["reason"], RETURN_REJECTION_MESSAGE)

    def test_opinador_returns_full_order_snapshot_for_order_query(self):
        from agents import agent_opinador

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)

            agent_opinador.configure_runtime(_test_runtime_settings(opinador, data_dir))
            client = agent_opinador.app.test_client()

            purchase_order = {
                "order_id": "ORDER-Q1",
                "user_id": "10.0.0.10",
                "user_name": "Pol",
                "purchase_date": "2026-06-05",
                "delivery_date": "2026-06-08",
                "products": [{"product_id": "P1001", "name": "Teclat", "price": 50.0, "weight": 0.8}],
                "shipping_data": {
                    "user_id": "10.0.0.10",
                    "user_name": "Pol",
                    "street_address": "Gran Via 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            }

            purchase_message = build_peticio_registre_compra(
                purchase_order,
                sender=agn.Compra,
                receiver=opinador.uri,
                msgcnt=1,
            )
            client.get("/comm", query_string={"content": purchase_message.serialize(format="xml")})

            query_message = build_peticio_consulta_comanda(
                "ORDER-Q1",
                sender=agn.Compra,
                receiver=opinador.uri,
                msgcnt=2,
            )
            query_response = client.get("/comm", query_string={"content": query_message.serialize(format="xml")})
            response_graph = Graph()
            response_graph.parse(data=query_response.get_data(as_text=True), format="xml")
            parsed = parse_resultat_consulta_comanda(response_graph)

            self.assertEqual(parsed["order_id"], "ORDER-Q1")
            self.assertEqual(parsed["user_id"], "10.0.0.10")
            self.assertEqual(parsed["shipping_data"]["street_address"], "Gran Via 1")
            self.assertEqual(parsed["shipping_data"]["payment_method"], "visa")
            self.assertEqual(parsed["delivery_date"], "2026-06-08")
            self.assertEqual(parsed["purchase_date"], "2026-06-05")
            self.assertEqual(parsed["product_ids"], ["P1001"])

    def test_opinador_returns_user_purchases_for_retornador_queries(self):
        from agents import agent_opinador

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)

            agent_opinador.configure_runtime(_test_runtime_settings(opinador, data_dir))
            client = agent_opinador.app.test_client()

            purchase_message = build_peticio_registre_compra(
                {
                    "order_id": "ORDER-R1",
                    "user_id": "10.0.0.25",
                    "user_name": "Retorns",
                    "purchase_date": "2026-06-05",
                    "delivery_date": "2026-06-08",
                    "products": [
                        {
                            "product_id": "P1001",
                            "name": "Teclat",
                            "brand": "KeyCo",
                            "price": 50.0,
                            "seller_id": "SELLER-1",
                            "requires_external_logistics": True,
                        }
                    ],
                    "shipping_data": {
                        "user_id": "10.0.0.25",
                        "user_name": "Retorns",
                        "street_address": "Gran Via 1",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
                sender=agn.Compra,
                receiver=opinador.uri,
                msgcnt=1,
            )
            client.get("/comm", query_string={"content": purchase_message.serialize(format="xml")})

            query_message = build_peticio_consulta_compres_usuari(
                "10.0.0.25",
                sender=agn.Retornador,
                receiver=opinador.uri,
                msgcnt=2,
            )
            query_response = client.get("/comm", query_string={"content": query_message.serialize(format="xml")})
            response_graph = Graph()
            response_graph.parse(data=query_response.get_data(as_text=True), format="xml")
            purchases = parse_resultat_consulta_compres_usuari(response_graph)

            self.assertEqual(len(purchases), 1)
            self.assertEqual(purchases[0]["order_id"], "ORDER-R1")
            self.assertEqual(purchases[0]["products"][0]["seller_id"], "SELLER-1")
            self.assertTrue(purchases[0]["products"][0]["requires_external_logistics"])

    def test_opinador_dashboard_and_feedback_are_scoped_by_client_ip(self):
        from agents import agent_opinador

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"
            products = generate_recommendations(catalog_path, data_dir / "historial_cerques.ttl", data_dir / "historial_compres.ttl", limit=8)
            product_user_1 = products[0]
            product_user_2 = products[1]

            agent_opinador.configure_runtime(_test_runtime_settings(opinador, data_dir))
            client = agent_opinador.app.test_client()

            for order in (
                {
                    "order_id": "ORDER-IP1",
                    "user_id": "10.0.0.1",
                    "user_name": "User One",
                    "products": [{"product_id": product_user_1["product_id"], "name": product_user_1["name"], "price": product_user_1["price"]}],
                    "shipping_data": {
                        "user_id": "10.0.0.1",
                        "user_name": "User One",
                        "street_address": "Carrer A",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
                {
                    "order_id": "ORDER-IP2",
                    "user_id": "10.0.0.2",
                    "user_name": "User Two",
                    "products": [{"product_id": product_user_2["product_id"], "name": product_user_2["name"], "price": product_user_2["price"]}],
                    "shipping_data": {
                        "user_id": "10.0.0.2",
                        "user_name": "User Two",
                        "street_address": "Carrer B",
                        "city": "Girona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
            ):
                message = build_peticio_registre_compra(
                    order,
                    sender=opinador.uri,
                    receiver=opinador.uri,
                    msgcnt=1,
                )
                client.get("/comm", query_string={"content": message.serialize(format="xml")})

            dashboard_ip1 = client.get("/iface", environ_base={"REMOTE_ADDR": "10.0.0.1"})
            html_ip1 = dashboard_ip1.get_data(as_text=True)
            self.assertIn("ORDER-IP1", html_ip1)
            self.assertNotIn("ORDER-IP2", html_ip1)

            feedback_response = client.post(
                "/iface",
                data={
                    "action": "feedback",
                    "rating": "5",
                    "product_id": product_user_1["product_id"],
                    "comment": "Tot correcte",
                },
                environ_base={"REMOTE_ADDR": "10.0.0.1"},
            )
            self.assertIn("Feedback registrat correctament per al producte seleccionat!", feedback_response.get_data(as_text=True))

            feedback_records = load_feedback_records(data_dir / "feedback.ttl", user_id="10.0.0.1")
            self.assertEqual(len(feedback_records), 1)
            self.assertEqual(feedback_records[0]["order_id"], "ORDER-IP1")
            self.assertEqual(feedback_records[0]["product_ids"], [product_user_1["product_id"]])

    def test_feedback_requires_minimum_days_after_purchase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"
            products = generate_recommendations(
                catalog_path,
                data_dir / "historial_cerques.ttl",
                data_dir / "historial_compres.ttl",
                limit=8,
            )
            product = products[0]
            recent_date = date.today().isoformat()
            old_date = (date.today() - timedelta(days=MIN_DAYS_BEFORE_FEEDBACK)).isoformat()

            record_purchase(
                data_dir / "historial_compres.ttl",
                {
                    "order_id": "ORDER-RECENT",
                    "user_id": "USER-FEEDBACK",
                    "user_name": "Tester",
                    "purchase_date": recent_date,
                    "products": [{"product_id": product["product_id"]}],
                    "shipping_data": {
                        "user_id": "USER-FEEDBACK",
                        "user_name": "Tester",
                        "street_address": "Carrer 1",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
            )

            pending_recent = get_purchases_pending_feedback(
                data_dir / "historial_compres.ttl",
                data_dir / "feedback.ttl",
                catalog_path,
                "USER-FEEDBACK",
                min_days=MIN_DAYS_BEFORE_FEEDBACK,
            )
            self.assertEqual(pending_recent["eligible_products"], [])
            self.assertEqual(len(pending_recent["waiting_products"]), 1)
            self.assertFalse(is_feedback_eligible(recent_date))

            record_purchase(
                data_dir / "historial_compres.ttl",
                {
                    "order_id": "ORDER-OLD",
                    "user_id": "USER-FEEDBACK",
                    "user_name": "Tester",
                    "purchase_date": old_date,
                    "products": [{"product_id": products[1]["product_id"]}],
                    "shipping_data": {
                        "user_id": "USER-FEEDBACK",
                        "user_name": "Tester",
                        "street_address": "Carrer 1",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
            )

            pending_old = get_purchases_pending_feedback(
                data_dir / "historial_compres.ttl",
                data_dir / "feedback.ttl",
                catalog_path,
                "USER-FEEDBACK",
                min_days=MIN_DAYS_BEFORE_FEEDBACK,
            )
            self.assertEqual(len(pending_old["eligible_products"]), 1)
            self.assertTrue(is_feedback_eligible(old_date))

    def test_proactive_cycles_cache_recommendations_and_feedback_requests(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message
        from AgentUtil.OntoNamespaces import ONTOLOGY_URI
        from agents import agent_opinador
        from protocols.cerca import build_resultat_cerca

        agn = Namespace("http://www.agentes.org#")
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"
            products = generate_recommendations(
                catalog_path,
                data_dir / "historial_cerques.ttl",
                data_dir / "historial_compres.ttl",
                limit=8,
            )
            user_id = "10.0.0.99"
            old_date = (date.today() - timedelta(days=MIN_DAYS_BEFORE_FEEDBACK)).isoformat()
            record_purchase(
                data_dir / "historial_compres.ttl",
                {
                    "order_id": "ORDER-PROACTIVE",
                    "user_id": user_id,
                    "user_name": "Proactive User",
                    "purchase_date": old_date,
                    "products": [{"product_id": products[0]["product_id"]}],
                    "shipping_data": {
                        "user_id": user_id,
                        "user_name": "Proactive User",
                        "street_address": "Carrer Z",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
            )

            agent_opinador.configure_runtime(
                {
                    "agent": opinador,
                    "data_dir": data_dir,
                    "feedback_min_seconds": None,
                    "feedback_policy_days": MIN_DAYS_BEFORE_FEEDBACK,
                    "proactive_enabled": False,
                }
            )
            catalog_products = [
                {
                    "product_id": products[0]["product_id"],
                    "name": products[0]["name"],
                    "description": products[0].get("description", ""),
                    "category": products[0].get("category", ""),
                    "brand": products[0].get("brand", ""),
                    "price": products[0].get("price", 0.0),
                    "weight": products[0].get("weight", 0.0),
                },
                {
                    "product_id": products[1]["product_id"],
                    "name": products[1]["name"],
                    "description": products[1].get("description", ""),
                    "category": products[1].get("category", ""),
                    "brand": products[1].get("brand", ""),
                    "price": products[1].get("price", 0.0),
                    "weight": products[1].get("weight", 0.0),
                },
            ]

            def fake_sender(message, address):
                request_content = message.value(predicate=RDF.type, object=AZON.PeticioCerca)
                payload, response_content = build_resultat_cerca(
                    "catalog-result-proactive",
                    catalog_products,
                    request_content=request_content,
                )
                return build_message(
                    payload,
                    ACL.inform,
                    sender=cercador.uri,
                    receiver=opinador.uri,
                    content=response_content,
                    ontology=ONTOLOGY_URI,
                    msgcnt=3,
                )

            previous_sender = agent_opinador.MESSAGE_SENDER
            previous_resolver = agent_opinador.resolve_cercador_agent
            try:
                agent_opinador.MESSAGE_SENDER = fake_sender
                agent_opinador.resolve_cercador_agent = lambda: cercador
                agent_opinador._run_proactive_recommendation_cycle()
                agent_opinador._run_proactive_feedback_cycle()
                recommendations = agent_opinador._get_proactive_recommendations(user_id, limit=5)
            finally:
                agent_opinador.MESSAGE_SENDER = previous_sender
                agent_opinador.resolve_cercador_agent = previous_resolver

            self.assertTrue(recommendations)

            feedback_requests = agent_opinador._get_proactive_feedback_requests(user_id)
            self.assertEqual(len(feedback_requests), 1)
            self.assertEqual(feedback_requests[0]["order_id"], "ORDER-PROACTIVE")


if __name__ == "__main__":
    unittest.main()
