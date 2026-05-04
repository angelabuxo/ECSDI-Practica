import sys
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_centre_logistic import AgentCentreLogistic, create_app as create_centre_logistic_app
from AgentZon.agents.agent_compra import AgentCompra, create_app
from AgentZon.agents.agent_directory import AgentDirectory
from AgentZon.config import AGENTZON, PRODUCTES_PATH, UBICACIONS_PRODUCTES_PATH
from AgentZon.protocols.centre_logistic import build_dades_enviament_action
from AgentZon.protocols.compra import (
    build_info_usuari,
    build_peticio_enviament_centre_logistic,
    build_peticio_registre_compra,
    get_comanda_subject,
    read_comanda,
    read_peticio_enviament,
    read_peticio_registre_compra,
)
from AgentZon.protocols.fipa_acl import build_message, get_message_properties, parse_message


class AgentCompraTest(unittest.TestCase):
    def _metadata_paths(self, tmpdir):
        dades_enviament_path = Path(tmpdir) / "dades_enviament_usuari.ttl"
        ubicacions_path = Path(tmpdir) / "ubicacions_productes.ttl"
        responsables_path = Path(tmpdir) / "responsable_enviament_productes.ttl"

        ubicacions_path.write_text(
            """@prefix az: <http://www.semanticweb.org/upc/ontologies/2026/3/untitled-ontology-15#> .

az:ubicacio_producte_p001 a az:UbicacioProducte ;
    az:IdProducte "p001" ;
    az:Magatzem "magatzem-bcn" ;
    az:Ciutat "Barcelona" .

az:ubicacio_producte_p002 a az:UbicacioProducte ;
    az:IdProducte "p002" ;
    az:Magatzem "magatzem-bcn" ;
    az:Ciutat "Barcelona" .
""",
            encoding="utf-8",
        )
        responsables_path.write_text(
            """@prefix az: <http://www.semanticweb.org/upc/ontologies/2026/3/untitled-ontology-15#> .

az:responsable_enviament_producte_p001 a az:ResponsableEnviamentProducte ;
    az:IdProducte "p001" ;
    az:Responsable "agentzon" .

az:responsable_enviament_producte_p002 a az:ResponsableEnviamentProducte ;
    az:IdProducte "p002" ;
    az:Responsable "extern" ;
    az:Venedor "Sony Store" .
""",
            encoding="utf-8",
        )
        return dades_enviament_path, ubicacions_path, responsables_path

    def _agent_with_temp_metadata(self, tmpdir, **kwargs):
        dades_path, ubicacions_path, responsables_path = self._metadata_paths(tmpdir)
        return AgentCompra(
            dades_enviament_path=dades_path,
            ubicacions_path=ubicacions_path,
            responsables_path=responsables_path,
            **kwargs,
        )

    def _compra_info_graph(self, userid, adreca, ciutat, prioritat, metodepagament):
        return build_info_usuari(userid, adreca, ciutat, prioritat, metodepagament)

    def test_get_shows_catalog_products(self):
        app = create_app()

        response = app.test_client().get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Portatil Lenovo IdeaPad", response.data)
        self.assertIn(b"Auriculars Sony WH-CH520", response.data)

    def test_info_endpoint_returns_turtle_graph(self):
        app = create_app()

        response = app.test_client().get("/Info")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"@prefix az:", response.data)
        self.assertIn(b"Portatil Lenovo IdeaPad", response.data)

    def test_rejects_purchase_without_products(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self._agent_with_temp_metadata(tmpdir))

            response = app.test_client().post(
                "/",
                data={
                    "userid": "u001",
                    "adreca": "Carrer Test 1",
                    "ciutat": "Barcelona",
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
                    "ciutat": "Barcelona",
                    "prioritat": "9",
                    "metodepagament": "targeta",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Prioritat ha de ser 1 (Express) o 2 (Normal)", response.data)

    def test_valid_purchase_returns_confirmation_and_rdf_backed_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            app = create_app(agent)

            response = app.test_client().post(
                "/",
                data={
                    "productes": ["p001", "p002"],
                    "userid": "u001",
                    "adreca": "Carrer Test 1",
                    "ciutat": "Barcelona",
                    "prioritat": "1",
                    "metodepagament": "targeta",
                },
            )

            comanda_subject = AGENTZON.comanda_0000
            comanda = read_comanda(agent.graph, comanda_subject)
            enviament = agent.render_enviament("0000")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Compra confirmada", response.data)
        self.assertIn(b"749.89", response.data)
        self.assertEqual(comanda["id"], "0000")
        self.assertEqual(comanda["estat"], "PENDENT")
        self.assertEqual(enviament["responsables"]["p001"], "AgentZon")
        self.assertEqual(enviament["responsables"]["p002"], "Sony Store")

    def test_persists_user_shipping_data_in_ttl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dades_path, ubicacions_path, responsables_path = self._metadata_paths(tmpdir)
            agent = AgentCompra(
                dades_enviament_path=dades_path,
                ubicacions_path=ubicacions_path,
                responsables_path=responsables_path,
            )
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            comanda = agent.gestionar_compra(
                compra,
                self._compra_info_graph("u001", "Carrer Persistencia 1", "Barcelona", 2, "targeta"),
            )

            persistit = Graph()
            persistit.parse(dades_path, format="turtle")
            subject = next(persistit.subjects(AGENTZON.IdUsuari, Literal("u001")))
            enviament = agent.render_enviament(comanda["id"])

        self.assertEqual(str(persistit.value(subject, AGENTZON.Adreça)), "Carrer Persistencia 1")
        self.assertEqual(str(persistit.value(subject, AGENTZON.Ciutat)), "Barcelona")
        self.assertEqual(int(persistit.value(subject, AGENTZON.Prioritat)), 2)
        self.assertEqual(enviament["responsables"]["p001"], "AgentZon")

    def test_processes_definitive_delivery_data_for_notification_and_render(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            comanda = agent.gestionar_compra(
                compra,
                self._compra_info_graph("u001", "Carrer Definitiu 1", "Barcelona", 1, "targeta"),
            )

            notificacio = agent.processar_dades_enviament(
                {
                    "id_lot": "lot-1",
                    "id_comanda": comanda["id"],
                    "userid": "u001",
                    "id_producte": "p001",
                    "transportista_id": "transport-1",
                    "data_entrega_definitiva": "2026-05-03",
                }
            )
            enviament = agent.render_enviament(comanda["id"])

        self.assertEqual(notificacio["transportista_id"], "transport-1")
        self.assertEqual(enviament["dades_definitives"]["p001"]["transportista_id"], "transport-1")
        self.assertEqual(enviament["dades_definitives"]["p001"]["data_entrega_definitiva"], "2026-05-03")

    def test_comm_processes_delivery_data_from_logistic_center(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            comanda = agent.gestionar_compra(
                compra,
                self._compra_info_graph("u001", "Carrer Comm 1", "Barcelona", 1, "targeta"),
            )
            app = create_app(agent)
            dades = {
                "id_lot": "lot-comm",
                "id_comanda": comanda["id"],
                "userid": "u001",
                "id_producte": "p001",
                "transportista_id": "transport-a",
                "data_entrega_definitiva": "2026-05-03",
            }
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
            enviament = agent.render_enviament(comanda["id"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(props["performative"], "confirm")
        self.assertEqual(enviament["dades_definitives"]["p001"]["transportista_id"], "transport-a")

    def test_rejects_delivery_data_for_unknown_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)

            with self.assertRaisesRegex(ValueError, "Comanda desconeguda"):
                agent.processar_dades_enviament(
                    {
                        "id_lot": "lot-1",
                        "id_comanda": "comanda-inexistent",
                        "userid": "u001",
                        "id_producte": "p001",
                        "transportista_id": "transport-1",
                        "data_entrega_definitiva": "2026-05-03",
                    }
                )

    def test_discovers_logistic_center_through_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
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

            agent = self._agent_with_temp_metadata(
                tmpdir,
                directory_address="memory://directory/Register",
                message_sender=send_in_memory,
            )
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            comanda = agent.gestionar_compra(
                compra,
                self._compra_info_graph("u001", "Carrer Directory 1", "Barcelona", 1, "targeta"),
            )
            lot_subject = next(centre_logistic.graph.subjects(RDF.type, AGENTZON.Lot))
            lot_id = str(centre_logistic.graph.value(lot_subject, AGENTZON.Id))
            enviament = agent.render_enviament(comanda["id"])

        self.assertIn((lot_subject, AGENTZON.TeProducte, AGENTZON["p001"]), centre_logistic.graph)
        self.assertEqual(enviament["centres_logistics"]["p001"]["centre_logistic"], "magatzem-bcn")
        self.assertEqual(enviament["centres_logistics"]["p001"]["id_lot"], lot_id)

    def test_protocol_helpers_generate_rdf_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._agent_with_temp_metadata(tmpdir)
            productes = agent.productes_per_ids(["p001"])
            compra = agent.processar_peticio_compra("u001", productes)
            comanda = agent.gestionar_compra(
                compra,
                self._compra_info_graph("u001", "Carrer Protocol 1", "Barcelona", 1, "targeta"),
            )

        registre_graph = build_peticio_registre_compra(agent.graph, AGENTZON[f"comanda_{comanda['id']}"])
        registre_subject = next(registre_graph.subjects(RDF.type, AGENTZON.PeticioRegistreCompra))
        registre = read_peticio_registre_compra(agent.graph + registre_graph, registre_subject)

        enviament_graph = build_peticio_enviament_centre_logistic(
            producte=productes[0],
            centre_logistic="magatzem-bcn",
            adreca=comanda["adreca"],
            ciutat=comanda["ciutat"],
            data_limit=comanda["data_entrega_estimada"],
            userid=comanda["userid"],
            id_comanda=comanda["id"],
            prioritat=comanda["prioritat"],
        )
        enviament_subject = next(enviament_graph.subjects(RDF.type, AGENTZON.PeticioEnviamentCentreLogistic))
        enviament = read_peticio_enviament(enviament_graph, enviament_subject)

        self.assertEqual(registre["id_comanda"], comanda["id"])
        self.assertEqual(registre["userid"], "u001")
        self.assertEqual([producte["id"] for producte in registre["llista_productes"]], ["p001"])
        self.assertEqual(enviament["centre_logistic"], "magatzem-bcn")
        self.assertEqual(enviament["id_producte"], "p001")

    def test_shared_catalog_has_location_for_each_product(self):
        productes_graph = Graph()
        productes_graph.parse(PRODUCTES_PATH, format="turtle")
        ubicacions_graph = Graph()
        ubicacions_graph.parse(UBICACIONS_PRODUCTES_PATH, format="turtle")

        product_ids = {
            str(productes_graph.value(subject, AGENTZON.Id))
            for subject in productes_graph.subjects(RDF.type, AGENTZON.Producte)
        }
        ubicacio_ids = {
            str(ubicacions_graph.value(subject, AGENTZON.IdProducte))
            for subject in ubicacions_graph.subjects(RDF.type, AGENTZON.UbicacioProducte)
        }

        self.assertEqual(product_ids, ubicacio_ids)


if __name__ == "__main__":
    unittest.main()
