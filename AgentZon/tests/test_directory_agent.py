"""Tests for directory-agent registration and lookup behaviour."""

import unittest

from rdflib import Namespace


class DirectoryAgentTests(unittest.TestCase):
    def test_directory_registers_and_resolves_core_agents(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_directory
        from protocols.directory import (
            build_register_message,
            build_search_message,
            parse_directory_response,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/Stop",
        )

        agent_directory.configure_runtime({"agent": directory})
        router = LocalMessageRouter()
        router.register_app(directory.address, agent_directory.app)

        register_message = build_register_message(
            compra,
            DSO.CompraAgent,
            directory,
            msgcnt=1,
        )
        register_reply = router.send_message(register_message, directory.address)
        self.assertIsNotNone(register_reply)

        search_message = build_search_message(
            cercador,
            DSO.CompraAgent,
            directory,
            msgcnt=2,
        )
        search_reply = router.send_message(search_message, directory.address)
        found = parse_directory_response(search_reply)

        self.assertEqual(found.name, compra.name)
        self.assertEqual(found.address, compra.address)

    def test_directory_returns_all_logistics_centres_with_registered_metadata(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_directory
        from protocols.directory import (
            build_register_message,
            build_search_message,
            parse_directory_responses,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        centre_bcn = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre-bcn.test/comm",
            "http://centre-bcn.test/Stop",
        )
        centre_gi = Agent(
            "CentreLogisticAgent-CL-GI",
            agn.CentreLogisticCLGI,
            "http://centre-gi.test/comm",
            "http://centre-gi.test/Stop",
        )

        agent_directory.configure_runtime({"agent": directory})
        router = LocalMessageRouter()
        router.register_app(directory.address, agent_directory.app)

        for msgcnt, (agent, centre_id, centre_city) in enumerate(
            [
                (centre_bcn, "CL-BCN", "Barcelona"),
                (centre_gi, "CL-GI", "Girona"),
            ],
            start=1,
        ):
            register_message = build_register_message(
                agent,
                DSO.CentreLogisticAgent,
                directory,
                msgcnt=msgcnt,
                metadata={
                    AZON.IdCentreLogistic: centre_id,
                    AZON.Ciutat: centre_city,
                },
            )
            router.send_message(register_message, directory.address)

        search_message = build_search_message(
            compra,
            DSO.CentreLogisticAgent,
            directory,
            msgcnt=10,
        )
        search_reply = router.send_message(search_message, directory.address)
        found = parse_directory_responses(search_reply)

        self.assertEqual(
            [(entry["centre_id"], entry["centre_city"]) for entry in found],
            [("CL-BCN", "Barcelona"), ("CL-GI", "Girona")],
        )
        self.assertEqual(
            [entry["address"] for entry in found],
            [centre_bcn.address, centre_gi.address],
        )

    def test_directory_returns_registered_transport_agents_with_transport_id(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_directory
        from protocols.directory import (
            build_register_message,
            build_search_message,
            parse_directory_responses,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        fast = Agent(
            "Transportista-fast",
            agn.TransportFast,
            "http://fast.test/comm",
            "http://fast.test/Stop",
        )
        economy = Agent(
            "Transportista-economy",
            agn.TransportEconomy,
            "http://economy.test/comm",
            "http://economy.test/Stop",
        )

        agent_directory.configure_runtime({"agent": directory})
        router = LocalMessageRouter()
        router.register_app(directory.address, agent_directory.app)

        for msgcnt, (agent, transport_id) in enumerate(
            [(fast, "fast"), (economy, "economy")],
            start=1,
        ):
            register_message = build_register_message(
                agent,
                DSO.TransportistaAgent,
                directory,
                msgcnt=msgcnt,
                metadata={AZON.IdTransportista: transport_id},
            )
            router.send_message(register_message, directory.address)

        search_message = build_search_message(
            compra,
            DSO.TransportistaAgent,
            directory,
            msgcnt=10,
        )
        search_reply = router.send_message(search_message, directory.address)
        found = parse_directory_responses(search_reply)

        self.assertEqual(
            [(entry["transport_id"], entry["address"]) for entry in found],
            [("economy", economy.address), ("fast", fast.address)],
        )

    def test_directory_replaces_address_when_agent_re_registers(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import agent_directory
        from protocols.directory import (
            build_register_message,
            build_search_message,
            parse_directory_response,
        )
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/Stop",
        )
        retornador_local = Agent(
            "RetornadorAgent",
            agn.Retornador,
            "http://127.0.0.1:9009/comm",
            "http://127.0.0.1:9009/Stop",
        )
        retornador_remote = Agent(
            "RetornadorAgent",
            agn.Retornador,
            "http://10.10.43.4:9009/comm",
            "http://10.10.43.4:9009/Stop",
        )

        agent_directory.configure_runtime({"agent": directory})
        router = LocalMessageRouter()
        router.register_app(directory.address, agent_directory.app)

        for msgcnt, retornador in enumerate([retornador_local, retornador_remote], start=1):
            register_message = build_register_message(
                retornador,
                DSO.RetornadorAgent,
                directory,
                msgcnt=msgcnt,
            )
            router.send_message(register_message, directory.address)

        search_message = build_search_message(
            cercador,
            DSO.RetornadorAgent,
            directory,
            msgcnt=3,
        )
        search_reply = router.send_message(search_message, directory.address)
        found = parse_directory_response(search_reply)

        self.assertEqual(found.address, retornador_remote.address)


if __name__ == "__main__":
    unittest.main()
