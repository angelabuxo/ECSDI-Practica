"""Tests for shared AgentZon runtime configuration helpers."""

import types
import unittest
from unittest.mock import patch


class ConfigTests(unittest.TestCase):
    def test_resolve_runtime_hostname_falls_back_to_open_bind_address(self):
        from config import resolve_runtime_hostname

        args = types.SimpleNamespace(host=None, open=None)

        self.assertEqual(resolve_runtime_hostname(args), "0.0.0.0")

    def test_resolve_runtime_hostname_uses_machine_hostname_when_open_flag_is_set(self):
        from config import resolve_runtime_hostname

        args = types.SimpleNamespace(host=None, open=True)

        with patch("AgentZon.config.gethostname", return_value="agentzon-host"):
            self.assertEqual(resolve_runtime_hostname(args), "agentzon-host")

    def test_build_directory_agent_uses_register_endpoint(self):
        from config import build_directory_agent

        directory = build_directory_agent("directory.test", 9000)

        self.assertEqual(directory.name, "DirectoryAgent")
        self.assertEqual(str(directory.uri).split("#")[-1], "Directory")
        self.assertEqual(directory.address, "http://directory.test:9000/Register")


if __name__ == "__main__":
    unittest.main()
