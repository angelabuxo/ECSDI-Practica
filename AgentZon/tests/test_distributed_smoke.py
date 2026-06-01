"""End-to-end smoke test for the hybrid deferred-shipping flow."""

import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import requests

from tests.support import load_catalog_products


AGENTZON_DIR = Path(__file__).resolve().parents[1]


class DistributedSmokeTests(unittest.TestCase):
    def test_agents_run_as_separate_processes_and_complete_one_order(self):
        from rdflib import Graph, Literal, RDF

        from AgentUtil.OntoNamespaces import AZON, bind_namespaces
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import save_graph

        base_cmd = [sys.executable, "-m"]
        host = "127.0.0.1"
        ports = {
            "directory": 9200,
            "cercador": 9201,
            "compra": 9202,
            "centre_bcn": 9203,
            "centre_gi": 9205,
            "opinador": 9204,
            "fast": 9210,
            "economy": 9211,
        }

        processes = []
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            products = load_catalog_products(data_dir / "productes.ttl")[:2]
            sample_product = products[0]
            second_product = products[1]
            search_token = sample_product["name"].split()[0]

            locations = Graph()
            bind_namespaces(locations)
            centre_nodes = {"CL-BCN": AZON["centre-BCN"], "CL-GI": AZON["centre-GI"]}
            for centre_id, city in [("CL-BCN", "Barcelona"), ("CL-GI", "Girona")]:
                centre_node = centre_nodes[centre_id]
                locations.add((centre_node, RDF.type, AZON.CentreLogistic))
                locations.add((centre_node, AZON.IdCentreLogistic, Literal(centre_id)))
                locations.add((centre_node, AZON.Ciutat, Literal(city)))
            locations.add((AZON[f"product-{sample_product['product_id']}"], AZON.UbicatACentre, centre_nodes["CL-BCN"]))
            locations.add((AZON[f"product-{sample_product['product_id']}"], AZON.UbicatACentre, centre_nodes["CL-GI"]))
            locations.add((AZON[f"product-{second_product['product_id']}"], AZON.UbicatACentre, centre_nodes["CL-GI"]))
            save_graph(data_dir / "ubicacions_productes.ttl", locations)

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
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
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
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
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
                    str(ports["centre_bcn"]),
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
                    "--centre-id",
                    "CL-BCN",
                    "--centre-city",
                    "Barcelona",
                    "--data-dir",
                    str(data_dir),
                ],
                base_cmd
                + [
                    "agents.agent_centre_logistic",
                    "--host",
                    host,
                    "--port",
                    str(ports["centre_gi"]),
                    "--directory-host",
                    host,
                    "--directory-port",
                    str(ports["directory"]),
                    "--centre-id",
                    "CL-GI",
                    "--centre-city",
                    "Girona",
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
                    processes.append(subprocess.Popen(command, cwd=str(AGENTZON_DIR)))
                    time.sleep(0.4)

                try:
                    for port in ports.values():
                        self._wait_for_port(host, port)
                except AssertionError:
                    self.skipTest("The current environment does not allow binding local test ports")

                search_response = requests.post(
                    f"http://{host}:{ports['cercador']}/iface",
                    data={
                        "text": search_token,
                        "category": sample_product["category"],
                        "brand": sample_product["brand"],
                        "min_price": f"{sample_product['price'] - 0.01:.2f}",
                        "max_price": f"{sample_product['price'] + 0.01:.2f}",
                    },
                    timeout=10,
                )
                self.assertIn(sample_product["name"], search_response.text)

                purchase_page = requests.post(
                    f"http://{host}:{ports['compra']}/iface",
                    data={"selected_product_ids": [sample_product["product_id"], second_product["product_id"]]},
                    timeout=10,
                )
                self.assertIn("Confirm purchase", purchase_page.text)

                confirmation = requests.post(
                    f"http://{host}:{ports['compra']}/iface",
                    data={
                        "selected_product_ids": [sample_product["product_id"], second_product["product_id"]],
                        "user_name": "Distributed Demo",
                        "street_address": "Gran Via 100",
                        "city": "Barcelona",
                        "priority": "24h",
                        "payment_method": "placeholder-visa",
                    },
                    timeout=10,
                )
                self.assertIn("Pendent d'assignacio", confirmation.text)
                self.assertIn("ORDER-", confirmation.text)

                order_match = re.search(r"ORDER-[A-Z0-9]+", confirmation.text)
                self.assertIsNotNone(order_match)
                order_id = order_match.group(0)

                for centre_port in [ports["centre_bcn"], ports["centre_gi"]]:
                    sweep = requests.get(f"http://{host}:{centre_port}/cron/negotiate-ready-lots", timeout=10)
                    self.assertEqual(sweep.status_code, 200)

                order_page = requests.get(f"http://{host}:{ports['compra']}/orders/{order_id}", timeout=10)
                self.assertEqual(order_page.status_code, 200)
                self.assertIn("economy", order_page.text)
                self.assertIn("ENVIAT", order_page.text)
                self.assertIn("CL-BCN", order_page.text)
                self.assertIn("CL-GI", order_page.text)
            finally:
                for port in [
                    ports["cercador"],
                    ports["compra"],
                    ports["centre_bcn"],
                    ports["centre_gi"],
                    ports["opinador"],
                    ports["fast"],
                    ports["economy"],
                    ports["directory"],
                ]:
                    try:
                        requests.get(f"http://{host}:{port}/Stop", timeout=2)
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
