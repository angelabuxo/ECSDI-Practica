import unittest
from unittest.mock import Mock, patch

import config


class ServeAgentStartupTests(unittest.TestCase):
    def test_serve_agent_checks_port_before_starting_behaviour(self):
        app = Mock()
        context = Mock()
        context.Queue.return_value = Mock()

        with patch("config._ensure_port_available", side_effect=OSError("busy"), create=True) as ensure_port:
            with patch("config.multiprocessing.get_context", return_value=context):
                with self.assertRaises(OSError):
                    config.serve_agent(app, "127.0.0.1", 9010, register_fn=Mock())

        ensure_port.assert_called_once_with("127.0.0.1", 9010)
        context.Process.assert_not_called()
        app.run.assert_not_called()

    def test_agent_behaviour_skips_registration_until_server_is_ready(self):
        queue = Mock()
        register_fn = Mock()

        with patch(
            "config._wait_until_server_ready_for_registration",
            return_value=False,
            create=True,
        ) as wait_ready:
            with patch("config._wait_for_shutdown_signal") as wait_for_shutdown:
                config._agent_behaviour(queue, register_fn, "127.0.0.1", 9010)

        wait_ready.assert_called_once_with(queue, "127.0.0.1", 9010)
        register_fn.assert_not_called()
        wait_for_shutdown.assert_not_called()


if __name__ == "__main__":
    unittest.main()
