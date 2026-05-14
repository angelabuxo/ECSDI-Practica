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
            "http://directory.test/stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/stop",
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


if __name__ == "__main__":
    unittest.main()
