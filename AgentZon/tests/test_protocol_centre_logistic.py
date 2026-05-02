import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rdflib import RDF

from AgentZon.config import AGENTZON

from AgentZon.protocols.centre_logistic import (
    DadesEnviamentProducte,
    EleccioTransportista,
    PeticioCobramentProducte,
    PeticioTransport,
    ProducteLocalitzat,
    RespostaOfertaTransport,
    build_lot_assignat_response,
    build_producte_localitzat_action,
    build_resposta_oferta_transport_action,
    read_lot_assignat_response,
    read_resposta_oferta_transport,
)


class ProtocolCentreLogisticTest(unittest.TestCase):
    def test_producte_localitzat_keeps_shipping_data_for_lot_assignment(self):
        missatge = ProducteLocalitzat(
            id_producte="p001",
            id_comanda="c001",
            userid="u001",
            adreca="Carrer Test 1",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-03",
            pes=2.5,
            import_producte=99.95,
        )

        self.assertEqual(missatge.id_producte, "p001")
        self.assertEqual(missatge.id_comanda, "c001")
        self.assertEqual(missatge.userid, "u001")
        self.assertEqual(missatge.adreca, "Carrer Test 1")
        self.assertEqual(missatge.ciutat, "Barcelona")
        self.assertEqual(missatge.prioritat, 1)
        self.assertEqual(missatge.data_limit, "2026-05-03")
        self.assertEqual(missatge.pes, 2.5)
        self.assertEqual(missatge.import_producte, 99.95)

    def test_transport_protocol_messages_keep_negotiation_data(self):
        peticio = PeticioTransport(
            centre_logistic_id="magatzem-bcn",
            ciutat_desti="Barcelona",
            data_enviament="2026-05-03",
            pes=3.5,
        )
        resposta = RespostaOfertaTransport(
            id_lot="lot-1",
            transportista_id="transport-1",
            cost=8.5,
            data_enviament="2026-05-02",
        )
        eleccio = EleccioTransportista(
            id_lot="lot-1",
            transportista_id="transport-1",
            cost=8.5,
            data_enviament="2026-05-02",
        )

        self.assertEqual(peticio.pes, 3.5)
        self.assertEqual(peticio.ciutat_desti, "Barcelona")
        self.assertEqual(peticio.data_enviament, "2026-05-03")
        self.assertEqual(resposta.transportista_id, "transport-1")
        self.assertEqual(eleccio.data_enviament, "2026-05-02")

    def test_dades_enviament_producte_keeps_delivery_data_for_compra(self):
        dades = DadesEnviamentProducte(
            id_lot="lot-1",
            id_comanda="c001",
            userid="u001",
            id_producte="p001",
            transportista_id="transport-1",
            data_entrega_definitiva="2026-05-02",
        )

        self.assertEqual(dades.id_lot, "lot-1")
        self.assertEqual(dades.id_comanda, "c001")
        self.assertEqual(dades.userid, "u001")
        self.assertEqual(dades.id_producte, "p001")
        self.assertEqual(dades.transportista_id, "transport-1")
        self.assertEqual(dades.data_entrega_definitiva, "2026-05-02")

    def test_cobrament_producte_keeps_user_product_and_amount(self):
        peticio = PeticioCobramentProducte(
            userid="u001",
            id_comanda="c001",
            id_producte="p001",
            import_cobrament=99.95,
        )

        self.assertEqual(peticio.userid, "u001")
        self.assertEqual(peticio.id_comanda, "c001")
        self.assertEqual(peticio.id_producte, "p001")
        self.assertEqual(peticio.import_cobrament, 99.95)

    def test_lot_confirm_links_catalog_product_with_teproducte(self):
        g = build_lot_assignat_response("bcn-0001", "p001")
        subj = next(g.subjects(RDF.type, AGENTZON.Lot))
        self.assertTrue((subj, AGENTZON.TeProducte, AGENTZON["p001"]) in g)
        self.assertEqual(read_lot_assignat_response(g, subj), {"id_lot": "bcn-0001", "id_producte": "p001"})

    def test_resposta_oferta_links_proposa_to_oferta_transport(self):
        oferta = RespostaOfertaTransport(
            id_lot="bcn-0001",
            transportista_id="transport-a",
            cost=12.5,
            data_enviament="2026-05-10",
        )
        g = build_resposta_oferta_transport_action(oferta)
        resposta = next(g.subjects(RDF.type, AGENTZON.RespostaOfertaTransport))
        nucli = g.value(resposta, AGENTZON.Proposa)
        self.assertIsNotNone(nucli)
        self.assertIn((nucli, RDF.type, AGENTZON.OfertaTransport), g)
        self.assertIn((resposta, AGENTZON.Proposa, nucli), g)
        self.assertEqual(float(g.value(nucli, AGENTZON.CostBase)), 12.5)
        llegit = read_resposta_oferta_transport(g, resposta)
        self.assertEqual(llegit.id_lot, "bcn-0001")
        self.assertEqual(llegit.transportista_id, "transport-a")
        self.assertEqual(llegit.cost, 12.5)
        self.assertEqual(llegit.data_enviament, "2026-05-10")

    def test_producte_localitzat_refs_catalog_product_with_localitza(self):
        missatge = ProducteLocalitzat(
            id_producte="p002",
            id_comanda="c01",
            userid="u01",
            adreca="Carrer 1",
            ciutat="Barcelona",
            prioritat=1,
            data_limit="2026-05-04",
            pes=1.0,
            import_producte=10.0,
        )
        g = build_producte_localitzat_action(missatge)
        subj = next(g.subjects(RDF.type, AGENTZON.ProducteLocalitzat))
        self.assertTrue((subj, AGENTZON.Localitza, AGENTZON["p002"]) in g)


if __name__ == "__main__":
    unittest.main()
