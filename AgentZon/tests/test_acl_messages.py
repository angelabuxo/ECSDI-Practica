"""Regression tests for RDF/FIPA-ACL message construction."""

import unittest

from rdflib import Literal, Namespace


class ACLMessageTests(unittest.TestCase):
    def test_build_message_wraps_search_content_and_round_trips_properties(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI
        from protocols.cerca import build_peticio_cerca, parse_peticio_cerca

        agn = Namespace("http://www.agentes.org#")
        sender = agn.Cercador
        receiver = agn.Compra

        content_graph, content = build_peticio_cerca(
            request_id="search-1",
            text="headphones",
            category="audio",
            brand="Acme",
            min_price=20.0,
            max_price=100.0,
        )

        message_graph = build_message(
            content_graph,
            ACL.request,
            sender=sender,
            receiver=receiver,
            content=content,
            ontology=ONTOLOGY_URI,
            msgcnt=1,
        )

        properties = get_message_properties(message_graph)
        self.assertEqual(properties["performative"], ACL.request)
        self.assertEqual(properties["sender"], sender)
        self.assertEqual(properties["receiver"], receiver)
        self.assertEqual(properties["content"], content)
        self.assertEqual(properties["ontology"], ONTOLOGY_URI)

        self.assertEqual(message_graph.value(content, AZON.TextConsulta), Literal("headphones"))
        self.assertEqual(message_graph.value(content, AZON.CategoriaConsulta), Literal("audio"))
        self.assertEqual(message_graph.value(content, AZON.MarcaConsulta), Literal("Acme"))

        parsed = parse_peticio_cerca(message_graph, content)
        self.assertEqual(parsed["text"], "headphones")
        self.assertEqual(parsed["category"], "audio")
        self.assertEqual(parsed["brand"], "Acme")
        self.assertEqual(parsed["min_price"], 20.0)
        self.assertEqual(parsed["max_price"], 100.0)


if __name__ == "__main__":
    unittest.main()
