"""Tests del flux ACL de cobrament al Cobrador."""

import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AGN
from protocols.pagament import (
    build_peticio_cobrament_intern,
    build_peticio_pagament,
    build_peticio_retorn_diners,
    extract_confirmacio_pagament,
    extract_confirmacio_retorn_diners,
)

from agents import agent_cobrador


class CobradorFlowTests(unittest.TestCase):
  def setUp(self):
    self.tmpdir = tempfile.TemporaryDirectory()
    self.data_dir = Path(self.tmpdir.name)
    catalog = self.data_dir / "productes.ttl"
    catalog.write_text(
      """@prefix azon: <http://www.semanticweb.org/agentzon#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

azon:product-P1001 a azon:Producte ;
  azon:IdProducte "P1001" ;
  azon:Nom "Producte prova" ;
  azon:Preu "10.0"^^xsd:float .
""",
      encoding="utf-8",
    )
    agent_cobrador.configure_runtime(
      {
        "agent": Agent(
          "CobradorAgent",
          AGN.Cobrador,
          "http://127.0.0.1:9005/comm",
          "http://127.0.0.1:9005/Stop",
        ),
        "directory_agent": None,
        "data_dir": self.data_dir,
      }
    )
    self.client = agent_cobrador.app.test_client()

  def tearDown(self):
    self.tmpdir.cleanup()

  def _post_comm(self, message):
    content = quote(message.serialize(format="xml"))
    return self.client.get(f"/comm?content={content}")

  def test_internal_charge_returns_paid_confirmation(self):
    centre = Agent(
      "CentreLogisticAgent",
      AGN.CentreLogistic,
      "http://centre.test/comm",
      "http://centre.test/Stop",
    )
    message = build_peticio_cobrament_intern(
      {
        "localized_product_id": "ploc-test-1",
        "lot_id": "LOT-1",
        "order_id": "ORDER-1",
        "user_id": "USER-1",
        "city": "Barcelona",
        "delivery_date": "2026-06-02",
        "transport_cost": 4.5,
        "product": {"product_id": "P1001", "name": "Producte prova", "weight": 1.0},
      },
      sender=centre.uri,
      receiver=agent_cobrador.AGENT.uri,
      msgcnt=1,
    )
    response = self._post_comm(message)
    self.assertEqual(response.status_code, 200)
    response_graph = Graph()
    response_graph.parse(data=response.data, format="xml")
    confirmation = extract_confirmacio_pagament(response_graph)
    self.assertEqual(confirmation["status"], "PAGAT")
    self.assertEqual(confirmation["order_id"], "ORDER-1")
    self.assertGreater(confirmation["amount"], 0.0)
    self.assertTrue(confirmation["payment_id"])

  def test_internal_charge_uses_price_from_transport_message(self):
    centre = Agent(
      "CentreLogisticAgent",
      AGN.CentreLogistic,
      "http://centre.test/comm",
      "http://centre.test/Stop",
    )
    message = build_peticio_cobrament_intern(
      {
        "localized_product_id": "ploc-test-2",
        "lot_id": "LOT-2",
        "order_id": "ORDER-2",
        "user_id": "USER-2",
        "city": "Barcelona",
        "delivery_date": "2026-06-06",
        "transport_cost": 4.5,
        "product": {"product_id": "P1001", "name": "Teclat", "weight": 0.8, "price": 50.0},
      },
      sender=centre.uri,
      receiver=agent_cobrador.AGENT.uri,
      msgcnt=2,
    )
    response = self._post_comm(message)
    response_graph = Graph()
    response_graph.parse(data=response.data, format="xml")
    confirmation = extract_confirmacio_pagament(response_graph)
    self.assertEqual(confirmation["products_subtotal"], 50.0)
    self.assertEqual(confirmation["amount"], 54.5)

  def test_external_payment_and_refund_return_ok(self):
    compra = Agent("CompraAgent", AGN.Compra, "http://compra.test/comm", "http://compra.test/Stop")
    retornador = Agent(
      "RetornadorAgent",
      AGN.Retornador,
      "http://retornador.test/comm",
      "http://retornador.test/Stop",
    )

    payment_message = build_peticio_pagament(
      {
        "payment_id": "PAY-EXT-1",
        "order_id": "ORDER-EXT",
        "amount": 25.0,
        "method": "transferencia",
        "sentit": "PAGAMENT",
        "seller_id": "SELLER-1",
        "product_ids": ["P1001"],
      },
      sender=compra.uri,
      receiver=agent_cobrador.AGENT.uri,
      msgcnt=2,
    )
    payment_response = self._post_comm(payment_message)
    payment_graph = Graph()
    payment_graph.parse(data=payment_response.data, format="xml")
    payment_confirmation = extract_confirmacio_pagament(payment_graph)
    self.assertEqual(payment_confirmation["status"], "PAGAT")

    refund_message = build_peticio_retorn_diners(
      {
        "return_id": "RET-1",
        "order_id": "ORDER-EXT",
        "user_id": "USER-1",
        "amount": 25.0,
        "reason": "Prova",
        "product_ids": ["P1001"],
      },
      sender=retornador.uri,
      receiver=agent_cobrador.AGENT.uri,
      msgcnt=3,
    )
    refund_response = self._post_comm(refund_message)
    refund_graph = Graph()
    refund_graph.parse(data=refund_response.data, format="xml")
    refund_confirmation = extract_confirmacio_retorn_diners(refund_graph)
    self.assertEqual(refund_confirmation["status"], "RETORNAT")
    self.assertEqual(refund_confirmation["return_id"], "RET-1")


if __name__ == "__main__":
  unittest.main()
