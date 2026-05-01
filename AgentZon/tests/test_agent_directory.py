import sys
import unittest
from pathlib import Path

from rdflib import Graph, Literal, RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_directory import AgentDirectory, create_app
from AgentZon.config import AGENTZON
from AgentZon.protocols.fipa_acl import build_message, get_message_properties, parse_message
from AgentZon.protocols.directory import (
    DSO,
    build_register_action,
    build_search_action,
    read_directory_response,
)


class AgentDirectoryTest(unittest.TestCase):
    def test_registers_and_finds_agent_by_type_and_name(self):
        directory = AgentDirectory()
        register_graph = build_register_action(
            name="magatzem-bcn",
            uri=AGENTZON.agent_centre_logistic_bcn,
            address="http://127.0.0.1:9003/comm",
            agent_type="AgentCentreLogistic",
        )

        directory.process_message(
            build_message(
                "request",
                AGENTZON.agent_centre_logistic_bcn,
                AGENTZON.directory_agent,
                register_graph,
                msgcnt=1,
            )
        )
        response = directory.process_message(
            build_message(
                "request",
                AGENTZON.agent_compra,
                AGENTZON.directory_agent,
                build_search_action(agent_type="AgentCentreLogistic", name="magatzem-bcn"),
                msgcnt=2,
            )
        )

        response_props = get_message_properties(response)
        directory_response = read_directory_response(response, response_props["content"])

        self.assertEqual(response_props["performative"], "inform")
        self.assertEqual(directory_response["name"], "magatzem-bcn")
        self.assertEqual(directory_response["address"], "http://127.0.0.1:9003/comm")
        self.assertEqual(directory_response["agent_type"], "AgentCentreLogistic")

    def test_register_endpoint_rejects_invalid_acl_message(self):
        app = create_app(AgentDirectory())

        response = app.test_client().get("/Register", query_string={"content": Graph().serialize(format="xml")})
        graph = parse_message(response.data.decode("utf-8"))
        props = get_message_properties(graph)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(props["performative"], "not-understood")

    def test_info_endpoint_returns_directory_as_turtle(self):
        directory = AgentDirectory()
        directory.register_agent(
            name="transport-a",
            uri=AGENTZON.agent_transportista_a,
            address="http://127.0.0.1:9011/comm",
            agent_type="AgentTransportista",
        )
        app = create_app(directory)

        response = app.test_client().get("/Info")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"transport-a", response.data)
        self.assertIn(b"AgentTransportista", response.data)


if __name__ == "__main__":
    unittest.main()
