"""Tests del flux ACL de cobrament al Cobrador."""

import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AGN
from protocols.pagament import (
    build_peticio_cobrament,
    extract_confirmacio_pagament,
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

  def test_charge_request_returns_paid_confirmation(self):
    centre = Agent(
      "CentreLogisticAgent",
      AGN.CentreLogistic,
      "http://centre.test/comm",
      "http://centre.test/Stop",
    )
    message = build_peticio_cobrament(
      {
        "user_id": "USER-1",
        "preu_producte": 10.0,
        "cost_transport": 4.5,
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
    self.assertEqual(confirmation["products_subtotal"], 10.0)
    self.assertEqual(confirmation["transport_cost"], 4.5)
    self.assertEqual(confirmation["amount"], 14.5)
    self.assertTrue(confirmation["payment_id"])

  def test_charge_request_keeps_product_and_transport_subtotals(self):
    centre = Agent(
      "CentreLogisticAgent",
      AGN.CentreLogistic,
      "http://centre.test/comm",
      "http://centre.test/Stop",
    )
    message = build_peticio_cobrament(
      {
        "user_id": "USER-2",
        "preu_producte": 50.0,
        "cost_transport": 4.5,
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
    self.assertEqual(confirmation["transport_cost"], 4.5)
    self.assertEqual(confirmation["amount"], 54.5)

  def test_external_charge_request_uses_zero_transport_cost(self):
    compra = Agent("CompraAgent", AGN.Compra, "http://compra.test/comm", "http://compra.test/Stop")

    payment_message = build_peticio_cobrament(
      {
        "user_id": "USER-1",
        "preu_producte": 25.0,
        "cost_transport": 0.0,
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
    self.assertEqual(payment_confirmation["products_subtotal"], 25.0)
    self.assertEqual(payment_confirmation["transport_cost"], 0.0)
    self.assertEqual(payment_confirmation["amount"], 25.0)


if __name__ == "__main__":
  unittest.main()
