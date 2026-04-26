import sys
import unittest
import json
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_compra import AgentCompra, create_app
from AgentZon.protocols.compra import (
    InformacioUsuari,
    PeticioCobramentUsuari,
    PeticioEnviamentCentreLogistic,
    PeticioEnviamentVenedorExtern,
    PeticioRegistreCompra,
    crear_peticio_cobrament_usuari,
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

        cobrament = crear_peticio_cobrament_usuari(info)
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

        self.assertIsInstance(cobrament, PeticioCobramentUsuari)
        self.assertEqual(cobrament.userid, "u001")
        self.assertEqual(cobrament.metodepagament, "targeta")
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
