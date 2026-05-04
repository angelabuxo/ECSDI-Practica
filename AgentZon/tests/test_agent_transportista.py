import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_transportista import AgentTransportista, create_app
from AgentZon.agents.agent_directory import AgentDirectory
from rdflib import RDF

from AgentZon.config import AGENTZON
from AgentZon.protocols.centre_logistic import (
    PeticioTransport,
    build_peticio_transport_action,
    read_resposta_oferta_transport,
)
from AgentZon.protocols.fipa_acl import build_message, get_message_properties, parse_message


class AgentTransportistaTest(unittest.TestCase):
    def test_registers_itself_in_directory(self):
        directory = AgentDirectory()

        def send_in_memory(address, graph):
            self.assertEqual(address, "memory://directory/Register")
            return directory.process_message(graph)

        transportista = AgentTransportista(
            transportista_id="transport-a",
            cost_base=5.0,
            dies_extra=0,
            address="memory://transport-a/comm",
        )

        props = transportista.registrar_al_directori("memory://directory/Register", send_in_memory)
        result = directory.search_agent("AgentTransportista", name="transport-a")

        self.assertEqual(props["performative"], "confirm")
        self.assertEqual(result["address"], "memory://transport-a/comm")

    def test_comm_returns_transport_offer_for_transport_request(self):
        transportista = AgentTransportista(
            transportista_id="transport-a",
            cost_base=5.0,
            dies_extra=0,
            address="http://127.0.0.1:9011/comm",
        )
        app = create_app(transportista)
        peticio = PeticioTransport(
            centre_logistic_id="magatzem-bcn",
            ciutat_desti="Barcelona",
            data_enviament="2026-05-03",
            pes=2.0,
        )
        peticio_graph = build_peticio_transport_action(peticio)
        message = build_message(
            "request",
            AGENTZON.agent_centre_logistic_bcn,
            AGENTZON.agent_transportista_a,
            peticio_graph,
            msgcnt=1,
        )
        req_props = get_message_properties(message)
        peticio_subj = req_props["content"]

        response = app.test_client().get("/comm", query_string={"content": message.serialize(format="xml")})
        response_graph = parse_message(response.data.decode("utf-8"))
        props = get_message_properties(response_graph)
        oferta = read_resposta_oferta_transport(response_graph, props["content"])
        resposta_subj = props["content"]
        nucli = response_graph.value(resposta_subj, AGENTZON.Proposa)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(props["performative"], "inform")
        self.assertEqual(oferta.id_lot, "")
        self.assertEqual(oferta.transportista_id, "transport-a")
        self.assertEqual(oferta.cost, 7.0)
        self.assertEqual(oferta.data_enviament, "2026-05-03")
        self.assertEqual(response_graph.value(resposta_subj, RDF.type), AGENTZON.RespostaOfertaTransport)
        self.assertIsNotNone(nucli)
        self.assertEqual(response_graph.value(nucli, RDF.type), AGENTZON.OfertaTransport)
        self.assertEqual(float(response_graph.value(nucli, AGENTZON.CostBase)), 7.0)
        self.assertIn((transportista.uri, AGENTZON.RepUna, peticio_subj), response_graph)
        self.assertIn((transportista.uri, AGENTZON.Genera, resposta_subj), response_graph)
        self.assertIn((transportista.uri, AGENTZON.RepUna, peticio_subj), transportista.estat)


if __name__ == "__main__":
    unittest.main()
