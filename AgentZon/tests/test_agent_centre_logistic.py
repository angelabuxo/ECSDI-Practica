import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

from rdflib import RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.config import AGENTZON
from AgentZon.agents.agent_directory import AgentDirectory
from AgentZon.agents.agent_centre_logistic import AgentCentreLogistic, create_app
from AgentZon.agents.agent_transportista import AgentTransportista, create_app as create_transportista_app
from AgentZon.protocols.directory import build_register_action
from AgentZon.protocols.centre_logistic import (
    DadesEnviamentProducte,
    EleccioTransportista,
    PeticioCobramentProducte,
    PeticioTransport,
    ProducteLocalitzat,
    RespostaOfertaTransport,
    build_producte_localitzat_action,
    read_lot_assignat_response,
)
from AgentZon.protocols.fipa_acl import build_message, get_message_properties, parse_message


class AgentCentreLogisticTest(unittest.TestCase):
    def test_loads_ontology_with_logistic_center_class(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")

        self.assertIn((AGENTZON.CentreLogistic, RDF.type, None), agent.graph)

    def test_declares_prometheus_capabilities_and_plans(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")

        self.assertEqual(
            {
                "Gestionar magatzem": ["pla_assignar_producte_a_lot"],
                "Negociar transport": ["pla_cerca_transportista", "pla_transportista_escollit"],
                "Gestionar post-enviament": ["pla_producte_sha_enviat"],
            },
            {capacitat: [pla.__name__ for pla in plans] for capacitat, plans in agent.capacitats.items()},
        )

    def test_assigns_products_to_compatible_lot_by_shipping_day(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte_1 = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=2,
            data_limit="2026-05-03",
            pes=2.5,
            import_producte=99.95,
        )
        producte_2 = ProducteLocalitzat(
            id_producte="p002",
            id_comanda="c002",
            userid="u002",
            adreca="Carrer Diferent 8, Girona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=1.0,
            import_producte=49.95,
        )

        lot_1 = agent.pla_assignar_producte_a_lot(producte_1)
        lot_2 = agent.pla_assignar_producte_a_lot(producte_2)

        self.assertEqual(lot_1.id, lot_2.id)
        self.assertEqual(lot_1.id, "bcn-0001")
        self.assertIn((AGENTZON[f"lot_{lot_1.id}"], RDF.type, AGENTZON.Lot), agent.graph)
        self.assertEqual([p.id_producte for p in lot_1.productes], ["p001", "p002"])
        self.assertEqual(lot_1.pes_total, 3.5)
        self.assertEqual(lot_1.data_enviament, "2026-05-03")

    def test_creates_sequential_lot_ids_with_centre_suffix_prefix(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte_1 = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.5,
            import_producte=99.95,
        )
        producte_2 = ProducteLocalitzat(
            id_producte="p002",
            id_comanda="c002",
            userid="u002",
            adreca="Carrer Diferent 2, Barcelona",
            ciutat="Girona",
            prioritat=1,
            data_limit="2026-05-04",
            pes=1.0,
            import_producte=49.95,
        )

        lot_1 = agent.pla_assignar_producte_a_lot(producte_1)
        lot_2 = agent.pla_assignar_producte_a_lot(producte_2)

        self.assertEqual(lot_1.id, "bcn-0001")
        self.assertEqual(lot_2.id, "bcn-0002")

    def test_emits_debug_logs_for_lot_assignment_and_transport_selection(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.0,
            import_producte=99.95,
        )

        with self.assertLogs("AgentZon.agents.agent_centre_logistic", level="DEBUG") as logs:
            lot = agent.pla_assignar_producte_a_lot(producte)
            agent.pla_cerca_transportista(lot.id)
            agent.registrar_oferta_transport(
                RespostaOfertaTransport(
                    id_lot=lot.id,
                    transportista_id="transport-1",
                    cost=9.0,
                    data_enviament="2026-05-03",
                )
            )
            agent.pla_transportista_escollit(lot.id)

        log_text = "\n".join(logs.output)
        self.assertIn("assignant producte", log_text)
        self.assertIn(lot.id, log_text)
        self.assertIn("peticio transport", log_text)
        self.assertIn("oferta transport rebuda", log_text)
        self.assertIn("transportista escollit", log_text)

    def test_comm_assigns_producte_localitzat_to_lot(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        app = create_app(agent)
        producte = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.5,
            import_producte=99.95,
        )
        message = build_message(
            "request",
            AGENTZON.agent_compra,
            AGENTZON.agent_centre_logistic_bcn,
            build_producte_localitzat_action(producte),
            msgcnt=1,
        )

        response = app.test_client().get("/comm", query_string={"content": message.serialize(format="xml")})
        response_graph = parse_message(response.data.decode("utf-8"))
        props = get_message_properties(response_graph)
        lot_response = read_lot_assignat_response(response_graph, props["content"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(props["performative"], "confirm")
        self.assertEqual(lot_response["id_producte"], "p001")
        self.assertIn(lot_response["id_lot"], agent.lots_pendents)
        self.assertEqual(agent.lots_pendents[lot_response["id_lot"]].productes[0].id_producte, "p001")

    def test_prepares_transport_request_for_pending_lot(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=2,
            data_limit="2026-05-04",
            pes=2.0,
            import_producte=99.95,
        )
        lot = agent.pla_assignar_producte_a_lot(producte)

        peticio = agent.pla_cerca_transportista(lot.id)

        self.assertIsInstance(peticio, PeticioTransport)
        self.assertEqual(peticio.ciutat_desti, "Barcelona")
        self.assertEqual(peticio.pes, 2.0)
        self.assertEqual(peticio.data_enviament, "2026-05-04")
        self.assertEqual(lot.estat, "NEGOCIANT_TRANSPORT")

    def test_selects_cheapest_transport_offer_before_lot_deadline(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.0,
            import_producte=99.95,
        )
        lot = agent.pla_assignar_producte_a_lot(producte)
        agent.pla_cerca_transportista(lot.id)
        agent.registrar_oferta_transport(
            RespostaOfertaTransport(
                id_lot=lot.id,
                transportista_id="transport-1",
                cost=9.0,
                data_enviament="2026-05-03",
            )
        )
        agent.registrar_oferta_transport(
            RespostaOfertaTransport(
                id_lot=lot.id,
                transportista_id="transport-2",
                cost=6.5,
                data_enviament="2026-05-04",
            )
        )

        eleccio, missatges = agent.pla_transportista_escollit(lot.id)

        self.assertIsInstance(eleccio, EleccioTransportista)
        self.assertEqual(len(missatges), 1)
        self.assertEqual(eleccio.id_lot, lot.id)
        self.assertEqual(eleccio.transportista_id, "transport-1")
        self.assertEqual(eleccio.cost, 9.0)
        self.assertEqual(lot.estat, "TRANSPORTISTA_ESCOLLIT")

    def test_transport_selection_creates_delivery_messages_for_compra(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte_1 = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.0,
            import_producte=99.95,
        )
        producte_2 = ProducteLocalitzat(
            id_producte="p002",
            id_comanda="c002",
            userid="u002",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=1.0,
            import_producte=49.95,
        )
        lot = agent.pla_assignar_producte_a_lot(producte_1)
        agent.pla_assignar_producte_a_lot(producte_2)
        agent.pla_cerca_transportista(lot.id)
        agent.registrar_oferta_transport(
            RespostaOfertaTransport(
                id_lot=lot.id,
                transportista_id="transport-1",
                cost=9.0,
                data_enviament="2026-05-03",
            )
        )

        eleccio, missatges = agent.pla_transportista_escollit(lot.id)

        self.assertIsInstance(eleccio, EleccioTransportista)
        self.assertEqual(len(missatges), 2)
        self.assertTrue(all(isinstance(missatge, DadesEnviamentProducte) for missatge in missatges))
        self.assertEqual([missatge.id_producte for missatge in missatges], ["p001", "p002"])
        self.assertEqual([missatge.id_comanda for missatge in missatges], ["c001", "c002"])
        self.assertEqual([missatge.userid for missatge in missatges], ["u001", "u002"])
        self.assertEqual({missatge.transportista_id for missatge in missatges}, {"transport-1"})
        self.assertEqual({missatge.data_entrega_definitiva for missatge in missatges}, {"2026-05-03"})

    def test_discovers_transport_agents_and_selects_best_offer(self):
        directory = AgentDirectory()
        directory.register_agent(
            name="transport-a",
            uri=AGENTZON.agent_transportista_a,
            address="memory://transport-a/comm",
            agent_type="AgentTransportista",
        )
        directory.register_agent(
            name="transport-b",
            uri=AGENTZON.agent_transportista_b,
            address="memory://transport-b/comm",
            agent_type="AgentTransportista",
        )
        transport_a = create_transportista_app(
            AgentTransportista("transport-a", cost_base=8.0, dies_extra=0, address="memory://transport-a/comm")
        )
        transport_b = create_transportista_app(
            AgentTransportista("transport-b", cost_base=5.0, dies_extra=0, address="memory://transport-b/comm")
        )
        transport_apps = {
            "memory://transport-a/comm": transport_a,
            "memory://transport-b/comm": transport_b,
        }

        def send_in_memory(address, graph):
            if address == "memory://directory/Register":
                return directory.process_message(graph)
            response = transport_apps[address].test_client().get(
                "/comm",
                query_string={"content": graph.serialize(format="xml")},
            )
            return parse_message(response.data.decode("utf-8"))

        agent = AgentCentreLogistic(
            centre_logistic_id="magatzem-bcn",
            ubicacio="Barcelona",
            directory_address="memory://directory/Register",
            message_sender=send_in_memory,
        )
        producte = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.0,
            import_producte=99.95,
        )
        lot = agent.pla_assignar_producte_a_lot(producte)

        eleccio, missatges = agent.negociar_transport_amb_transportistes(lot.id)

        self.assertEqual(eleccio.transportista_id, "transport-b")
        self.assertEqual(eleccio.cost, 7.0)
        self.assertEqual(len(agent.ofertes_rebudes[lot.id]), 2)
        self.assertEqual(missatges[0].transportista_id, "transport-b")

    def test_rejects_transport_selection_when_no_offer_meets_deadline(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.0,
            import_producte=99.95,
        )
        lot = agent.pla_assignar_producte_a_lot(producte)
        agent.pla_cerca_transportista(lot.id)
        agent.registrar_oferta_transport(
            RespostaOfertaTransport(
                id_lot=lot.id,
                transportista_id="transport-1",
                cost=6.5,
                data_enviament="2026-05-04",
            )
        )

        with self.assertRaisesRegex(ValueError, "dins del termini"):
            agent.pla_transportista_escollit(lot.id)

    def test_shipping_today_creates_charging_requests_for_sent_products(self):
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        producte_avui = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit=today,
            pes=2.0,
            import_producte=99.95,
        )
        producte_dema = ProducteLocalitzat(
            id_producte="p002",
            id_comanda="c002",
            userid="u002",
            adreca="Carrer Test 2, Barcelona",
            ciutat="Barcelona",
            prioritat=1,
            data_limit=tomorrow,
            pes=1.0,
            import_producte=49.95,
        )
        lot_avui = agent.pla_assignar_producte_a_lot(producte_avui)
        agent.pla_assignar_producte_a_lot(producte_dema)

        peticions = agent.pla_producte_sha_enviat(today=today)

        self.assertEqual(len(peticions), 1)
        self.assertIsInstance(peticions[0], PeticioCobramentProducte)
        self.assertEqual(peticions[0].userid, "u001")
        self.assertEqual(peticions[0].id_comanda, "c001")
        self.assertEqual(peticions[0].id_producte, "p001")
        self.assertEqual(peticions[0].import_cobrament, 99.95)
        self.assertEqual(lot_avui.estat, "ENVIAT")


if __name__ == "__main__":
    unittest.main()
