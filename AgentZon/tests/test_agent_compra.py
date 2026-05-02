import sys
import unittest
import json
import tempfile
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_compra import AgentCompra, create_app
from AgentZon.agents.agent_directory import AgentDirectory
from AgentZon.agents.agent_centre_logistic import AgentCentreLogistic
from AgentZon.agents.agent_centre_logistic import create_app as create_centre_logistic_app
from AgentZon.config import AGENTZON
from AgentZon.protocols.centre_logistic import DadesEnviamentProducte, build_dades_enviament_action
from AgentZon.protocols.fipa_acl import build_message, get_message_properties, parse_message
from AgentZon.protocols.compra import (
    InformacioUsuari,
    PeticioEnviamentCentreLogistic,
    PeticioEnviamentVenedorExtern,
    PeticioRegistreCompra,
    crear_peticio_enviament_centre_logistic,
    crear_peticio_enviament_venedor_extern,
    crear_peticio_registre_compra,
)


class AgentCompraTest(unittest.TestCase):
    def _metadata_paths(self, tmpdir):
        dades_enviament_path = Path(tmpdir) / "dades_enviament_usuari.json"
        ubicacions_path = Path(tmpdir) / "ubicacions_productes.json"
        responsables_path = Path(tmpdir) / "responsable_enviament_productes.json"

        ubicacions_path.write_text(
            json.dumps(
                {
                    "p001": {"magatzem": "magatzem-bcn", "ciutat": "Barcelona"},
                    "p002": {"magatzem": "magatzem-bcn", "ciutat": "Barcelona"},
                }
            ),
            encoding="utf-8",
        )
        responsables_path.write_text(
            json.dumps(
                {
                    "p001": {"responsable": "agentzon"},
                    "p002": {"responsable": "extern", "venedor": "Sony Store"},
                }
            ),
            encoding="utf-8",
        )
        return dades_enviament_path, ubicacions_path, responsables_path

    def _agent_with_temp_metadata(self, tmpdir):
        dades_path, ubicacions_path, responsables_path = self._metadata_paths(tmpdir)
        return AgentCompra(
            dades_enviament_path=dades_path,
            ubicacions_path=ubicacions_path,
            responsables_path=responsables_path,
        )

    def test_get_shows_catalog_products(self):
        app = create_app()

        response = app.test_client().get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Portatil Lenovo IdeaPad", response.data)
        self.assertIn(b"Auriculars Sony WH-CH520", response.data)

    def test_rejects_purchase_without_products(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self._agent_with_temp_metadata(tmpdir))

            response = app.test_client().post(
                "/",
                data={
                    "userid": "u001",
                    "adreca": "Carrer Test 1",
                    "prioritat": "1",
                    "metodepagament": "targeta",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cal seleccionar almenys un producte.", response.data)

    def test_rejects_invalid_priority(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self._agent_with_temp_metadata(tmpdir))

            response = app.test_client().post(
                "/",
                data={
                    "productes": ["p001"],
                    "userid": "u001",
                    "adreca": "Carrer Test 1",
                    "prioritat": "9",
                    "metodepagament": "targeta",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Prioritat ha de ser 1 (Express) o 2 (Normal)", response.data)

    def test_valid_purchase_returns_paid_order_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self._agent_with_temp_metadata(tmpdir))

            response = app.test_client().post(
                "/",
                data={
                    "productes": ["p001", "p002"],
                    "userid": "u001",
                    "adreca": "Carrer Test 1",
                    "prioritat": "1",
                    "metodepagament": "targeta",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Compra confirmada", response.data)
        self.assertIn(b"FACTURA", response.data)
        self.assertIn(b"749.89", response.data)
        self.assertIn(b"ENVIAT PER", response.data)
        self.assertNotIn(b"Entrega estimada", response.data)
        self.assertIn(b"AgentZon", response.data)
        self.assertIn(b"Sony Store", response.data)
        self.assertIn(b"Portatil Lenovo IdeaPad", response.data)
        self.assertIn(b"Auriculars Sony WH-CH520", response.data)

    def test_purchase_page_shows_definitive_delivery_data_when_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Definitiu 1", 1, "targeta")
            comanda = agent.gestionar_compra(compra, info)
            agent.processar_dades_enviament(
                DadesEnviamentProducte(
                    id_lot="lot-1",
                    id_comanda=comanda.id,
                    userid="u001",
                    id_producte="p001",
                    transportista_id="transport-1",
                    data_entrega_definitiva="2026-05-03",
                )
            )
            app = create_app(agent)

            with app.test_request_context("/"):
                html = app.jinja_env.get_template("compra.html").render(
                    productes=agent.inventari(),
                    resultat={"comanda": comanda, "enviament": agent.enviaments[comanda.id]},
                    error=None,
                    valors={"userid": "", "adreca": "", "prioritat": "2", "metodepagament": "", "productes": []},
                )

        self.assertIn("TRANSPORTISTA ESCOLLIT", html)
        self.assertIn("transport-1", html)
        self.assertIn("2026-05-03", html)

    def test_capacity_methods_create_and_pay_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            agent.demanar_informacio_usuari("u001")
            info = InformacioUsuari("u001", "Carrer Test 1", 2, "targeta")
            comanda = agent.gestionar_compra(compra, info)

        self.assertEqual(comanda.estat, "PENDENT")
        self.assertEqual(comanda.import_total, 699.99)
        self.assertIn(comanda.id, agent.enviaments)

    def test_order_delivery_date_uses_iso_format_for_rdf_datetime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer ISO 1", 2, "targeta")
            comanda = agent.gestionar_compra(compra, info)

        datetime.fromisoformat(comanda.data_entrega_estimada)

    def test_purchase_persists_and_reads_shipping_data_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dades_path, ubicacions_path, responsables_path = self._metadata_paths(tmpdir)
            agent = AgentCompra(
                dades_enviament_path=dades_path,
                ubicacions_path=ubicacions_path,
                responsables_path=responsables_path,
            )

            productes = agent.productes_per_ids(["p001", "p002"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Persistencia 1", 2, "targeta")
            comanda = agent.gestionar_compra(compra, info)
            enviament = agent.enviaments[comanda.id]

            dades_persistides = json.loads(dades_path.read_text(encoding="utf-8"))
            self.assertEqual(dades_persistides["u001"]["adreca"], "Carrer Persistencia 1")
            self.assertEqual(dades_persistides["u001"]["prioritat"], 2)
            self.assertEqual(enviament["responsables"]["p001"], "AgentZon")
            self.assertEqual(enviament["responsables"]["p002"], "Sony Store")
            self.assertNotIn("productes", enviament)

    def test_purchase_emits_debug_logs_for_order_and_shipping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Logs 1", 1, "targeta")

            with self.assertLogs("AgentZon.agents.agent_compra", level="DEBUG") as logs:
                comanda = agent.gestionar_compra(compra, info)

        log_text = "\n".join(logs.output)
        self.assertIn("gestionant compra", log_text)
        self.assertIn(comanda.id, log_text)
        self.assertIn("localitzant productes", log_text)
        self.assertIn("producte intern", log_text)
        self.assertIn("producte pendent d'agent", log_text)

    def test_does_not_expose_local_logistic_center_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)

        self.assertFalse(hasattr(agent, "registrar_centre_logistic"))
        self.assertFalse(hasattr(agent, "centres_logistics"))
        self.assertFalse(hasattr(agent, "peticions_enviament_centre_logistic"))

    def test_discovers_logistic_center_through_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dades_path, ubicacions_path, responsables_path = self._metadata_paths(tmpdir)
            directory = AgentDirectory()
            directory.register_agent(
                name="magatzem-bcn",
                uri=AGENTZON.agent_centre_logistic_bcn,
                address="memory://magatzem-bcn/comm",
                agent_type="AgentCentreLogistic",
            )
            centre_logistic = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
            centre_app = create_centre_logistic_app(centre_logistic)

            def send_in_memory(address, graph):
                if address == "memory://directory/Register":
                    return directory.process_message(graph)
                response = centre_app.test_client().get(
                    "/comm",
                    query_string={"content": graph.serialize(format="xml")},
                )
                return parse_message(response.data.decode("utf-8"))

            agent = AgentCompra(
                dades_enviament_path=dades_path,
                ubicacions_path=ubicacions_path,
                responsables_path=responsables_path,
                directory_address="memory://directory/Register",
                message_sender=send_in_memory,
            )

            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Directory 1", 1, "targeta")
            comanda = agent.gestionar_compra(compra, info)

            lot = next(iter(centre_logistic.lots_pendents.values()))
            enviament_centre = agent.enviaments[comanda.id]["centres_logistics"]["p001"]

            self.assertEqual(centre_logistic.lots_pendents[lot.id].productes[0].id_producte, "p001")
            self.assertEqual(enviament_centre["centre_logistic"], "magatzem-bcn")
            self.assertEqual(enviament_centre["id_lot"], lot.id)

    def test_processes_logistic_center_delivery_data_for_user_notification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Definitiu 1", 1, "targeta")
            comanda = agent.gestionar_compra(compra, info)

            notificacio = agent.processar_dades_enviament(
                DadesEnviamentProducte(
                    id_lot="lot-1",
                    id_comanda=comanda.id,
                    userid="u001",
                    id_producte="p001",
                    transportista_id="transport-1",
                    data_entrega_definitiva="2026-05-03",
                )
            )

            dades_definitives = agent.enviaments[comanda.id]["dades_definitives"]["p001"]
            self.assertEqual(dades_definitives["transportista_id"], "transport-1")
            self.assertEqual(dades_definitives["data_entrega_definitiva"], "2026-05-03")
            self.assertEqual(notificacio["userid"], "u001")
            self.assertEqual(notificacio["id_producte"], "p001")
            self.assertEqual(notificacio["transportista_id"], "transport-1")
            self.assertEqual(notificacio["data_entrega_definitiva"], "2026-05-03")

    def test_comm_processes_delivery_data_from_logistic_center(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Comm 1", 1, "targeta")
            comanda = agent.gestionar_compra(compra, info)
            app = create_app(agent)
            dades = DadesEnviamentProducte(
                id_lot="lot-comm",
                id_comanda=comanda.id,
                userid="u001",
                id_producte="p001",
                transportista_id="transport-a",
                data_entrega_definitiva="2026-05-03T10:00:00",
            )
            message = build_message(
                "request",
                AGENTZON.agent_centre_logistic_bcn,
                AGENTZON.agent_compra,
                build_dades_enviament_action(dades),
                msgcnt=1,
            )

            response = app.test_client().get("/comm", query_string={"content": message.serialize(format="xml")})
            response_graph = parse_message(response.data.decode("utf-8"))
            props = get_message_properties(response_graph)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(props["performative"], "confirm")
            self.assertEqual(
                agent.enviaments[comanda.id]["dades_definitives"]["p001"]["transportista_id"],
                "transport-a",
            )

    def test_rejects_delivery_data_for_unknown_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)

            with self.assertRaisesRegex(ValueError, "Comanda desconeguda"):
                agent.processar_dades_enviament(
                    DadesEnviamentProducte(
                        id_lot="lot-1",
                        id_comanda="comanda-inexistent",
                        userid="u001",
                        id_producte="p001",
                        transportista_id="transport-1",
                        data_entrega_definitiva="2026-05-03",
                    )
                )

    def test_local_product_without_location_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dades_path = Path(tmpdir) / "dades_enviament_usuari.json"
            ubicacions_path = Path(tmpdir) / "ubicacions_productes.json"
            responsables_path = Path(tmpdir) / "responsable_enviament_productes.json"
            ubicacions_path.write_text("{}", encoding="utf-8")
            responsables_path.write_text(json.dumps({"p001": {"responsable": "agentzon"}}), encoding="utf-8")
            agent = AgentCompra(
                dades_enviament_path=dades_path,
                ubicacions_path=ubicacions_path,
                responsables_path=responsables_path,
            )

            with self.assertRaisesRegex(ValueError, "No hi ha ubicació persistent"):
                productes = agent.productes_per_ids(["p001"])
                compra = agent.processar_peticio_compra("u001", productes)
                info = InformacioUsuari("u001", "Carrer Persistencia 1", 2, "targeta")
                agent.gestionar_compra(compra, info)

    def test_purchase_protocol_helpers_create_expected_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001", "p002"])
            compra = agent.processar_peticio_compra("u001", productes)
            info = InformacioUsuari("u001", "Carrer Protocol 1", 1, "targeta")
            comanda = agent.gestionar_compra(compra, info)

        registre = crear_peticio_registre_compra(comanda)
        enviament_extern = crear_peticio_enviament_venedor_extern(
            productes[1],
            "Sony Store",
            comanda.adreça,
            comanda.data_entrega_estimada,
        )
        enviament_centre = crear_peticio_enviament_centre_logistic(
            productes[0],
            "magatzem-bcn",
            comanda.adreça,
            comanda.data_entrega_estimada,
        )

        self.assertIsInstance(registre, PeticioRegistreCompra)
        self.assertEqual(registre.id_comanda, comanda.id)
        self.assertEqual(registre.userid, "u001")
        self.assertEqual(registre.llista_productes, productes)
        self.assertTrue(registre.data_hora_compra)
        self.assertIsInstance(enviament_extern, PeticioEnviamentVenedorExtern)
        self.assertEqual(enviament_extern.venedor, "Sony Store")
        self.assertEqual(enviament_extern.producte, productes[1])
        self.assertEqual(enviament_extern.adreça, "Carrer Protocol 1")
        self.assertEqual(enviament_extern.data_limit, comanda.data_entrega_estimada)
        self.assertIsInstance(enviament_centre, PeticioEnviamentCentreLogistic)
        self.assertEqual(enviament_centre.centre_logistic, "magatzem-bcn")
        self.assertEqual(enviament_centre.producte, productes[0])
        self.assertEqual(enviament_centre.adreça, "Carrer Protocol 1")
        self.assertEqual(enviament_centre.data_limit, comanda.data_entrega_estimada)


if __name__ == "__main__":
    unittest.main()
