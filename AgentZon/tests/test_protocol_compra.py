import sys
import unittest
from pathlib import Path

from rdflib import Graph, RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.config import AGENTZON, PRODUCTES_PATH
from AgentZon.protocols.cerca import productes_per_ids
from AgentZon.protocols.compra import (
    build_comanda,
    build_info_usuari,
    build_peticio_enviament_centre_logistic,
    build_peticio_info_usuari,
    build_peticio_registre_compra,
    get_comanda_subject,
    read_comanda,
    read_info_usuari,
    read_peticio_enviament,
    read_peticio_info_usuari,
    read_peticio_registre_compra,
    validar_comanda,
)


class ProtocolCompraTest(unittest.TestCase):
    def setUp(self):
        self.catalog_graph = Graph()
        self.catalog_graph.parse(PRODUCTES_PATH, format="turtle")
        self.productes = productes_per_ids(self.catalog_graph, ["p001"])

    def test_builds_and_reads_info_usuari_as_rdf(self):
        graph = build_info_usuari("u001", "Carrer Test 1", "Barcelona", 1, "targeta")
        subject = next(graph.subjects(RDF.type, AGENTZON.InfoUsuari))
        info = read_info_usuari(graph, subject)

        self.assertEqual(info["userid"], "u001")
        self.assertEqual(info["adreca"], "Carrer Test 1")
        self.assertEqual(info["ciutat"], "Barcelona")
        self.assertEqual(info["prioritat"], 1)
        self.assertEqual(info["metodepagament"], "targeta")

    def test_builds_and_reads_comanda_as_rdf(self):
        info_graph = build_info_usuari("u001", "Carrer Test 1", "Barcelona", 2, "targeta")
        info_subject = next(info_graph.subjects(RDF.type, AGENTZON.InfoUsuari))
        info = read_info_usuari(info_graph, info_subject)

        comanda_graph = build_comanda(self.catalog_graph, "0000", self.productes, info)
        comanda_subject = get_comanda_subject(comanda_graph)
        comanda = read_comanda(self.catalog_graph + comanda_graph, comanda_subject)

        self.assertTrue(validar_comanda(self.catalog_graph + comanda_graph, comanda_subject))
        self.assertEqual(comanda["id"], "0000")
        self.assertEqual(comanda["userid"], "u001")
        self.assertEqual(comanda["import_total"], 699.99)
        self.assertEqual(comanda["llista_productes"][0]["id"], "p001")
        self.assertEqual(comanda["estat"], "PENDENT")

    def test_builds_purchase_related_messages_as_rdf(self):
        info_graph = build_info_usuari("u001", "Carrer Test 1", "Barcelona", 1, "targeta")
        info_subject = next(info_graph.subjects(RDF.type, AGENTZON.InfoUsuari))
        info = read_info_usuari(info_graph, info_subject)
        comanda_graph = build_comanda(self.catalog_graph, "0001", self.productes, info)
        comanda_subject = get_comanda_subject(comanda_graph)
        comanda = read_comanda(self.catalog_graph + comanda_graph, comanda_subject)

        peticio_info_graph = build_peticio_info_usuari("u001")
        peticio_info_subject = next(peticio_info_graph.subjects(RDF.type, AGENTZON.PeticioInfoUsuari))
        peticio_info = read_peticio_info_usuari(peticio_info_graph, peticio_info_subject)
        self.assertEqual(peticio_info["userid"], "u001")

        registre_graph = build_peticio_registre_compra(self.catalog_graph + comanda_graph, comanda_subject)
        registre_subject = next(registre_graph.subjects(RDF.type, AGENTZON.PeticioRegistreCompra))
        registre = read_peticio_registre_compra(self.catalog_graph + comanda_graph + registre_graph, registre_subject)
        self.assertEqual(registre["id_comanda"], "0001")
        self.assertEqual(registre["userid"], "u001")
        self.assertEqual([producte["id"] for producte in registre["llista_productes"]], ["p001"])

        enviament_graph = build_peticio_enviament_centre_logistic(
            producte=self.productes[0],
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
        self.assertEqual(enviament["centre_logistic"], "magatzem-bcn")
        self.assertEqual(enviament["id_producte"], "p001")
        self.assertEqual(enviament["userid"], "u001")


if __name__ == "__main__":
    unittest.main()
