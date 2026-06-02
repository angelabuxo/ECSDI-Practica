"""Tests de la política de devolucions (Opinador + motius UI)."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from services.history_service import record_purchase
from protocols.opinador import build_resolucio_devolucio, parse_resolucio_devolucio
from rdflib import Graph

from services.opinador_service import evaluate_multi_order_return, evaluate_return_request
from services.retornador_service import (
    RETURN_REASON_DEFECTUOUS,
    RETURN_REASON_DISLIKED,
    RETURN_REASON_NOT_AS_DESCRIBED,
    RETURN_REJECTION_MESSAGE,
    build_aggregate_return_decision,
    build_return_request_from_selection,
)


class ReturnPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        self.catalog_path = self.data_dir / "productes.ttl"
        self.history_path = self.data_dir / "historial_compres.ttl"
        self.catalog_path.write_text(
            """@prefix azon: <http://www.semanticweb.org/agentzon#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

azon:product-P1 a azon:Producte ;
  azon:IdProducte "P1" ;
  azon:Nom "Prova" ;
  azon:Preu "50.0"^^xsd:float .
""",
            encoding="utf-8",
        )
        record_purchase(
            self.history_path,
            {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "user_name": "Prova",
                "products": [{"product_id": "P1"}],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Prova",
                    "street_address": "Carrer 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            },
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_accepted_when_within_15_days_and_valid_reason(self):
        decision = evaluate_return_request(
            self.catalog_path,
            self.history_path,
            {
                "return_id": "RET-1",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "product_ids": ["P1"],
                "reason": RETURN_REASON_DEFECTUOUS,
            },
        )
        self.assertTrue(decision["accepted"])

    def test_rejected_when_reason_not_eligible(self):
        decision = evaluate_return_request(
            self.catalog_path,
            self.history_path,
            {
                "return_id": "RET-2",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "product_ids": ["P1"],
                "reason": RETURN_REASON_DISLIKED,
            },
        )
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], RETURN_REJECTION_MESSAGE)

    def test_rejected_when_purchase_older_than_15_days(self):
        old_date = (date.today() - timedelta(days=20)).isoformat()
        graph_path = self.history_path
        text = graph_path.read_text(encoding="utf-8")
        graph_path.write_text(text.replace(date.today().isoformat(), old_date), encoding="utf-8")

        decision = evaluate_return_request(
            self.catalog_path,
            self.history_path,
            {
                "return_id": "RET-3",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "product_ids": ["P1"],
                "reason": RETURN_REASON_NOT_AS_DESCRIBED,
            },
        )
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], RETURN_REJECTION_MESSAGE)

    def test_rejected_resolution_roundtrips_without_amount_error(self):
        message = build_resolucio_devolucio(
            {
                "return_id": "RET-X",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "amount": None,
                "accepted": False,
                "reason": RETURN_REJECTION_MESSAGE,
                "product_ids": [],
            }
        )
        graph = Graph()
        graph.parse(data=message.serialize(format="xml"), format="xml")
        decision = parse_resolucio_devolucio(graph)
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["amount"], 0.0)

    def test_ui_requires_radio_reason(self):
        payload, error = build_return_request_from_selection(
            ["ORDER-1::P1"],
            "",
            "USER-1",
        )
        self.assertIsNone(payload)
        self.assertIn("motiu", error.lower())

    def test_multi_order_selection_groups_by_order(self):
        record_purchase(
            self.history_path,
            {
                "order_id": "ORDER-2",
                "user_id": "USER-1",
                "user_name": "Prova",
                "products": [{"product_id": "P2"}],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Prova",
                    "street_address": "Carrer 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            },
        )
        payload, error = build_return_request_from_selection(
            ["ORDER-1::P1", "ORDER-2::P2"],
            RETURN_REASON_DEFECTUOUS,
            "USER-1",
        )
        self.assertEqual(error, "")
        self.assertEqual(payload["order_groups"], {"ORDER-1": ["P1"], "ORDER-2": ["P2"]})

    def test_multi_order_evaluates_each_order_separately(self):
        old_date = (date.today() - timedelta(days=20)).isoformat()
        text = self.history_path.read_text(encoding="utf-8")
        self.history_path.write_text(
            text.replace(date.today().isoformat(), old_date, 1),
            encoding="utf-8",
        )
        record_purchase(
            self.history_path,
            {
                "order_id": "ORDER-RECENT",
                "user_id": "USER-1",
                "user_name": "Prova",
                "products": [{"product_id": "P2"}],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Prova",
                    "street_address": "Carrer 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            },
        )

        return_request, _ = build_return_request_from_selection(
            ["ORDER-1::P1", "ORDER-RECENT::P2"],
            RETURN_REASON_DEFECTUOUS,
            "USER-1",
        )
        order_decisions = evaluate_multi_order_return(
            self.catalog_path,
            self.history_path,
            return_request,
        )
        aggregate = build_aggregate_return_decision(
            return_request["return_id"],
            "USER-1",
            return_request["reason"],
            order_decisions,
            self.catalog_path,
        )
        self.assertTrue(aggregate["accepted"])
        self.assertTrue(aggregate["partial"])
        self.assertEqual(len(aggregate["accepted_items"]), 1)
        self.assertEqual(aggregate["accepted_items"][0]["order_id"], "ORDER-RECENT")
        self.assertEqual(len(aggregate["rejected_items"]), 1)
        self.assertEqual(aggregate["rejected_items"][0]["order_id"], "ORDER-1")


if __name__ == "__main__":
    unittest.main()
