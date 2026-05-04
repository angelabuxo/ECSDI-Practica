import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rdflib import RDF

from AgentZon.config import AGENTZON
from AgentZon.protocols.centre_logistic import (
    build_dades_enviament_action,
    build_eleccio_transportista_action,
    build_lot_assignat_response,
    build_peticio_cobrament_action,
    build_peticio_transport_action,
    build_producte_localitzat_action,
    build_resposta_oferta_transport_action,
    get_dades_enviament_subject,
    get_eleccio_transportista_subject,
    get_peticio_cobrament_subject,
    get_peticio_transport_subject,
    get_producte_localitzat_subject,
    get_resposta_oferta_transport_subject,
    read_dades_enviament,
    read_eleccio_transportista,
    read_lot_assignat_response,
    read_peticio_cobrament,
    read_peticio_transport,
    read_producte_localitzat,
    read_resposta_oferta_transport,
)


class ProtocolCentreLogisticTest(unittest.TestCase):
    def test_producte_localitzat_roundtrip_keeps_shipping_data(self):
        missatge = {
            "id_producte": "p001",
            "id_comanda": "c001",
            "userid": "u001",
            "adreca": "Carrer Test 1",
            "ciutat": "Barcelona",
            "prioritat": 1,
            "data_limit": "2026-05-03",
            "pes": 2.5,
            "import_producte": 99.95,
        }

        g = build_producte_localitzat_action(missatge)
        subj = get_producte_localitzat_subject(g)
        llegit = read_producte_localitzat(g, subj)

        self.assertIn((subj, RDF.type, AGENTZON.ProducteLocalitzat), g)
        self.assertIn((subj, AGENTZON.Localitza, AGENTZON["p001"]), g)
        self.assertEqual(llegit["id_producte"], "p001")
        self.assertEqual(llegit["ciutat"], "Barcelona")
        self.assertEqual(llegit["pes"], 2.5)

    def test_lot_confirm_links_catalog_product_with_teproducte(self):
        g = build_lot_assignat_response("bcn-0001", "p001")
        subj = next(g.subjects(RDF.type, AGENTZON.Lot))

        self.assertTrue((subj, AGENTZON.TeProducte, AGENTZON["p001"]) in g)
        self.assertEqual(read_lot_assignat_response(g, subj)["id_lot"], "bcn-0001")

    def test_peticio_transport_roundtrip_keeps_negotiation_data(self):
        peticio = {
            "centre_logistic_id": "magatzem-bcn",
            "ciutat_desti": "Barcelona",
            "data_enviament": "2026-05-03",
            "pes": 3.5,
        }

        g = build_peticio_transport_action(peticio)
        subj = get_peticio_transport_subject(g)
        llegit = read_peticio_transport(g, subj)

        self.assertIn((subj, RDF.type, AGENTZON.PeticioTransport), g)
        self.assertEqual(llegit["ciutat_desti"], "Barcelona")
        self.assertEqual(llegit["pes"], 3.5)

    def test_resposta_oferta_links_proposa_to_oferta_transport(self):
        oferta = {
            "id_lot": "bcn-0001",
            "transportista_id": "transport-a",
            "cost": 12.5,
            "data_enviament": "2026-05-10",
        }

        g = build_resposta_oferta_transport_action(oferta)
        resposta = get_resposta_oferta_transport_subject(g)
        nucli = g.value(resposta, AGENTZON.Proposa)
        llegit = read_resposta_oferta_transport(g, resposta)

        self.assertIsNotNone(nucli)
        self.assertIn((nucli, RDF.type, AGENTZON.OfertaTransport), g)
        self.assertEqual(float(g.value(nucli, AGENTZON.CostBase)), 12.5)
        self.assertEqual(llegit["id_lot"], "bcn-0001")
        self.assertEqual(llegit["transportista_id"], "transport-a")

    def test_eleccio_transportista_roundtrip_keeps_selected_offer(self):
        eleccio = {
            "id_lot": "bcn-0001",
            "transportista_id": "transport-a",
            "cost": 8.0,
            "data_enviament": "2026-05-03",
        }

        g = build_eleccio_transportista_action(eleccio)
        subj = get_eleccio_transportista_subject(g)
        llegit = read_eleccio_transportista(g, subj)

        self.assertEqual(llegit["id_lot"], "bcn-0001")
        self.assertEqual(llegit["transportista_id"], "transport-a")
        self.assertEqual(llegit["cost"], 8.0)

    def test_dades_enviament_producte_roundtrip_keeps_delivery_data(self):
        dades = {
            "id_lot": "lot-1",
            "id_comanda": "c001",
            "userid": "u001",
            "id_producte": "p001",
            "transportista_id": "transport-1",
            "data_entrega_definitiva": "2026-05-02",
        }

        g = build_dades_enviament_action(dades)
        subj = get_dades_enviament_subject(g)
        llegit = read_dades_enviament(g, subj)

        self.assertIn((subj, RDF.type, AGENTZON.DadesEnviamentProducte), g)
        self.assertEqual(llegit["id_producte"], "p001")
        self.assertEqual(llegit["data_entrega_definitiva"], "2026-05-02")

    def test_cobrament_producte_roundtrip_keeps_user_product_and_amount(self):
        peticio = {
            "userid": "u001",
            "id_comanda": "c001",
            "id_producte": "p001",
            "import_cobrament": 99.95,
        }

        g = build_peticio_cobrament_action(peticio)
        subj = get_peticio_cobrament_subject(g)
        llegit = read_peticio_cobrament(g, subj)

        self.assertEqual(llegit["userid"], "u001")
        self.assertEqual(llegit["id_comanda"], "c001")
        self.assertEqual(llegit["import_cobrament"], 99.95)


if __name__ == "__main__":
    unittest.main()
