"""End-to-end smoke test that launches the core AgentZon agents as processes."""

import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import requests


class DistributedSmokeTests(unittest.TestCase):
    def test_agents_run_as_separate_processes_and_complete_one_order(self):
        from services.bootstrap import bootstrap_phase2_data

        base_cmd = ["./.venv/bin/python", "-m"]
        host = "127.0.0.1"
        ports = {
            "directory": 9200,
            "cercador": 9201,
            "compra": 9202,
            "centre": 9203,
            "opinador": 9204,
            "fast": 9210,
            "economy": 9211,
        }

        processes = []
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)

            commands = [
                base_cmd + ["agents.agent_directory", "--host", host, "--port", str(ports["directory"])],
                base_cmd
                + [
                    "agents.agent_opinador",
                    "--host",
                    host,
                    "--port",
                    str(ports["opinador"]),
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
                    "--data-dir",
                    str(data_dir),
                ],
                base_cmd
                + [
                    "agents.agent_transportista",
                    "--host",
                    host,
                    "--port",
                    str(ports["fast"]),
                    "--transport-id",
                    "fast",
                    "--price-per-kg",
                    "8.0",
                    "--delivery-days",
                    "1",
                ],
                base_cmd
                + [
                    "agents.agent_transportista",
                    "--host",
                    host,
                    "--port",
                    str(ports["economy"]),
                    "--transport-id",
                    "economy",
                    "--price-per-kg",
                    "4.0",
                    "--delivery-days",
                    "3",
                ],
                base_cmd
                + [
                    "agents.agent_centre_logistic",
                    "--host",
                    host,
                    "--port",
                    str(ports["centre"]),
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
                    "--transport-fast-host",
                    host,
                    "--transport-fast-port",
                    str(ports["fast"]),
                    "--transport-economy-host",
                    host,
                    "--transport-economy-port",
                    str(ports["economy"]),
                    "--data-dir",
                    str(data_dir),
                ],
                base_cmd
                + [
                    "agents.agent_compra",
                    "--host",
                    host,
                    "--port",
                    str(ports["compra"]),
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
                    "--data-dir",
                    str(data_dir),
                ],
                base_cmd
                + [
                    "agents.agent_cercador",
                    "--host",
                    host,
                    "--port",
                    str(ports["cercador"]),
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
                    "--data-dir",
                    str(data_dir),
                ],
            ]

            try:
                for command in commands:
                    processes.append(
                        subprocess.Popen(
                            command,
                            cwd="/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon",
                        )
                    )
                    time.sleep(0.4)

                for port in ports.values():
                    self._wait_for_port(host, port)

                search_response = requests.post(
                    f"http://{host}:{ports['cercador']}/iface",
                    data={
                        "text": "wireless",
                        "category": "audio",
                        "brand": "AuralMax",
                        "min_price": "20",
                        "max_price": "150",
                    },
                    timeout=10,
                )
                self.assertIn("Wireless Headphones", search_response.text)

                purchase_page = requests.post(
                    f"http://{host}:{ports['compra']}/iface",
                    data={"selected_product_ids": ["P1001"]},
                    timeout=10,
                )
                self.assertIn("Confirm purchase", purchase_page.text)

                confirmation = requests.post(
                    f"http://{host}:{ports['compra']}/iface",
                    data={
                        "selected_product_ids": ["P1001"],
                        "user_id": "USER-DIST",
                        "user_name": "Distributed Demo",
                        "street_address": "Gran Via 100",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "placeholder-visa",
                    },
                    timeout=10,
                )
                self.assertIn("economy", confirmation.text)
                self.assertIn("ORDER-", confirmation.text)
            finally:
                for name, port in [
                    ("cercador", ports["cercador"]),
                    ("compra", ports["compra"]),
                    ("centre", ports["centre"]),
                    ("opinador", ports["opinador"]),
                    ("fast", ports["fast"]),
                    ("economy", ports["economy"]),
                    ("directory", ports["directory"]),
                ]:
                    try:
                        path = "/Stop"
                        requests.get(f"http://{host}:{port}{path}", timeout=2)
                    except Exception:
                        pass
                for process in processes:
                    process.terminate()
                    process.wait(timeout=5)

    def _wait_for_port(self, host, port, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex((host, port)) == 0:
                    return
            time.sleep(0.2)
        self.fail(f"Port {port} did not become reachable")


if __name__ == "__main__":
    unittest.main()
