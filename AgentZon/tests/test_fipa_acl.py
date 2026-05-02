import sys
import unittest
from pathlib import Path

from rdflib import Graph, Literal, RDF, URIRef


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.config import AGENTZON
from AgentZon.protocols.fipa_acl import ACL, build_message, get_message_properties, parse_message


class FipaAclTest(unittest.TestCase):
    def test_builds_and_reads_acl_message_with_rdf_content(self):
        content = Graph()
        action = AGENTZON.test_action_1
        content.add((action, RDF.type, AGENTZON.PeticioTransport))
        content.add((action, AGENTZON.Id, Literal("lot-1")))

        message = build_message(
            performative="request",
            sender=URIRef(f"{AGENTZON}agent_compra"),
            receiver=URIRef(f"{AGENTZON}agent_centre_logistic_bcn"),
            content=content,
            msgcnt=7,
        )

        parsed = parse_message(message.serialize(format="xml"))
        props = get_message_properties(parsed)

        self.assertEqual(props["performative"], "request")
        self.assertEqual(props["sender"], URIRef(f"{AGENTZON}agent_compra"))
        self.assertEqual(props["receiver"], URIRef(f"{AGENTZON}agent_centre_logistic_bcn"))
        self.assertEqual(props["content"], action)
        self.assertIn((props["message"], ACL.performative, Literal("request")), parsed)
        self.assertIn((action, RDF.type, AGENTZON.PeticioTransport), parsed)

    def test_returns_empty_properties_for_invalid_message(self):
        props = get_message_properties(Graph())

        self.assertEqual(props, {})


if __name__ == "__main__":
    unittest.main()
