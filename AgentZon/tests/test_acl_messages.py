import unittest

from rdflib import Graph, Literal, Namespace, RDF


class ACLMessageTests(unittest.TestCase):
    def test_build_message_wraps_search_content_and_round_trips_properties(self):
        from AgentZon.AgentUtil.ACL import ACL
        from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentZon.protocols.cerca import build_peticio_cerca, parse_peticio_cerca

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
            msgcnt=1,
        )

        properties = get_message_properties(message_graph)
        self.assertEqual(properties["performative"], ACL.request)
        self.assertEqual(properties["sender"], sender)
        self.assertEqual(properties["receiver"], receiver)
        self.assertEqual(properties["content"], content)

        parsed = parse_peticio_cerca(message_graph, content)
        self.assertEqual(parsed["text"], "headphones")
        self.assertEqual(parsed["category"], "audio")
        self.assertEqual(parsed["brand"], "Acme")
        self.assertEqual(parsed["min_price"], 20.0)
        self.assertEqual(parsed["max_price"], 100.0)


if __name__ == "__main__":
    unittest.main()
