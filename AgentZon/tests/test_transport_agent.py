"""Focused tests for transport-agent negotiation and registration behaviour."""

import unittest
from unittest.mock import patch

from rdflib import Namespace


class TransportAgentTests(unittest.TestCase):
    def test_transport_agent_answers_cfp_with_a_proposal(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.Agent import Agent
        from agents import agent_transportista
        from protocols.centre_logistic import build_peticio_transport, extract_transport_offer
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        transport = Agent(
            "Transportista-fast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        centre = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )

        agent_transportista.configure_runtime(
            {
                "agent": transport,
                "transport_id": "fast",
                "price_per_kg": 8.0,
                "delivery_days": 1,
            }
        )
        router = LocalMessageRouter()
        router.register_app(transport.address, agent_transportista.app)

        lot = {
            "lot_id": "LOT-1",
            "order_id": "ORDER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-10",
            "total_weight": 2.0,
        }
        message, _ = build_peticio_transport(lot, sender=centre.uri, receiver=transport.uri, msgcnt=1)
        reply = router.send_message(message, transport.address)

        self.assertEqual(get_message_properties(reply)["performative"], ACL.propose)
        offer = extract_transport_offer(reply)
        self.assertEqual(offer["transport_id"], "fast")
        self.assertEqual(offer["price"], 16.0)

    def test_transport_agent_accepts_counter_offer_within_threshold(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.Agent import Agent
        from agents import agent_transportista
        from protocols.centre_logistic import (
            build_contraoferta_transport,
            build_peticio_transport,
            extract_transport_offer,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        transport = Agent(
            "Transportista-fast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        centre = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )

        agent_transportista.configure_runtime(
            {
                "agent": transport,
                "transport_id": "fast",
                "price_per_kg": 8.0,
                "delivery_days": 1,
            }
        )
        router = LocalMessageRouter()
        router.register_app(transport.address, agent_transportista.app)

        lot = {
            "lot_id": "LOT-THRESHOLD",
            "order_id": "ORDER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-10",
            "total_weight": 2.0,
        }
        cfp_message, cfp_content = build_peticio_transport(lot, sender=centre.uri, receiver=transport.uri, msgcnt=1)
        proposal_reply = router.send_message(cfp_message, transport.address)
        proposal = extract_transport_offer(proposal_reply)

        counter_price = 12.5
        counter_message = build_contraoferta_transport(
            lot,
            proposal,
            new_price=counter_price,
            sender=centre.uri,
            receiver=transport.uri,
            request_content=cfp_content,
            msgcnt=2,
        )
        counter_reply = router.send_message(counter_message, transport.address)
        self.assertEqual(get_message_properties(counter_reply)["performative"], ACL.agree)

    def test_transport_agent_rejects_counter_offer_below_threshold(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.Agent import Agent
        from agents import agent_transportista
        from protocols.centre_logistic import (
            build_contraoferta_transport,
            build_peticio_transport,
            extract_transport_offer,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        transport = Agent(
            "Transportista-fast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        centre = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )

        agent_transportista.configure_runtime(
            {
                "agent": transport,
                "transport_id": "fast",
                "price_per_kg": 8.0,
                "delivery_days": 1,
            }
        )
        router = LocalMessageRouter()
        router.register_app(transport.address, agent_transportista.app)

        lot = {
            "lot_id": "LOT-REJECT",
            "order_id": "ORDER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-10",
            "total_weight": 2.0,
        }
        cfp_message, cfp_content = build_peticio_transport(lot, sender=centre.uri, receiver=transport.uri, msgcnt=1)
        proposal_reply = router.send_message(cfp_message, transport.address)
        proposal = extract_transport_offer(proposal_reply)

        counter_price = 10.0
        counter_message = build_contraoferta_transport(
            lot,
            proposal,
            new_price=counter_price,
            sender=centre.uri,
            receiver=transport.uri,
            request_content=cfp_content,
            msgcnt=2,
        )
        counter_reply = router.send_message(counter_message, transport.address)
        self.assertEqual(get_message_properties(counter_reply)["performative"], ACL.refuse)

    def test_transport_agent_answers_counter_accept_reject_cycle(self):
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.Agent import Agent
        from agents import agent_transportista
        from protocols.centre_logistic import (
            build_accept_transport_offer,
            build_contraoferta_transport,
            build_peticio_transport,
            build_reject_transport_offer,
            extract_transport_offer,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        transport = Agent(
            "Transportista-fast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        centre = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )

        agent_transportista.configure_runtime(
            {
                "agent": transport,
                "transport_id": "fast",
                "price_per_kg": 8.0,
                "delivery_days": 1,
            }
        )
        router = LocalMessageRouter()
        router.register_app(transport.address, agent_transportista.app)

        lot = {
            "lot_id": "LOT-1",
            "order_id": "ORDER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-10",
            "total_weight": 2.0,
        }
        cfp_message, cfp_content = build_peticio_transport(lot, sender=centre.uri, receiver=transport.uri, msgcnt=1)
        proposal_reply = router.send_message(cfp_message, transport.address)
        proposal = extract_transport_offer(proposal_reply)

        counter_message = build_contraoferta_transport(
            lot,
            proposal,
            new_price=15.0,
            sender=centre.uri,
            receiver=transport.uri,
            request_content=cfp_content,
            msgcnt=2,
        )
        self.assertEqual(get_message_properties(counter_message)["performative"], ACL.propose)
        counter_reply = router.send_message(counter_message, transport.address)
        self.assertEqual(get_message_properties(counter_reply)["performative"], ACL.agree)

        accept_reply = router.send_message(
            build_accept_transport_offer(lot, proposal, sender=centre.uri, receiver=transport.uri, msgcnt=3),
            transport.address,
        )
        reject_reply = router.send_message(
            build_reject_transport_offer(lot, proposal, sender=centre.uri, receiver=transport.uri, msgcnt=4),
            transport.address,
        )
        self.assertEqual(get_message_properties(accept_reply)["performative"], ACL.inform)
        self.assertEqual(get_message_properties(reject_reply)["performative"], ACL.inform)

    def test_transport_agent_registers_with_directory_transport_metadata(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_transportista

        agn = Namespace("http://www.agentes.org#")
        transport = Agent(
            "Transportista-fast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )

        agent_transportista.configure_runtime(
            {
                "agent": transport,
                "transport_id": "fast",
                "price_per_kg": 8.0,
                "delivery_days": 1,
            }
        )

        with patch.object(agent_transportista, "register_with_directory", return_value=True) as register_mock:
            registered = agent_transportista.register_transport_agent(directory, msgcnt=7)

        self.assertTrue(registered)
        register_mock.assert_called_once()
        agent, directory_agent, agent_type = register_mock.call_args.args[:3]
        self.assertEqual(agent, transport)
        self.assertEqual(directory_agent, directory)
        self.assertEqual(str(agent_type), "http://www.semanticweb.org/directory-service-ontology#TransportistaAgent")
        self.assertEqual(register_mock.call_args.kwargs["metadata"], {AZON.IdTransportista: "fast"})


if __name__ == "__main__":
    unittest.main()
