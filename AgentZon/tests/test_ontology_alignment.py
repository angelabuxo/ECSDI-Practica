"""Structural assertions about the refined AgentZon ontology vocabulary."""

import unittest
from pathlib import Path

from rdflib import Graph, OWL, RDF
from rdflib.namespace import RDFS

from AgentUtil.OntoNamespaces import AZON


ONTOLOGY_PATH = Path(__file__).resolve().parents[1] / "ontologia" / "AgentZonOntology.rdf"


class OntologyAlignmentTests(unittest.TestCase):
    def object_property_domains(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")
        return {
            (str(prop), str(domain))
            for prop, domain in graph.subject_objects(RDFS.domain)
            if (prop, RDF.type, OWL.ObjectProperty) in graph
        }

    def test_sobre_lot_accepts_producte_localitzat(self):
        self.assertIn(
            (
                "http://www.semanticweb.org/agentzon#SobreLot",
                "http://www.semanticweb.org/agentzon#ProducteLocalitzat",
            ),
            self.object_property_domains(),
        )

    def test_refined_ontology_removes_internal_agent_branch_and_legacy_terms(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertIn((AZON.SobreProducte, RDF.type, OWL.ObjectProperty), graph)
        self.assertIn((AZON.PesTotal, RDF.type, OWL.DatatypeProperty), graph)
        self.assertNotIn((AZON.AgentIntern, None, None), graph)
        self.assertNotIn((AZON.AgentCercador, None, None), graph)
        self.assertNotIn((AZON.AgentCompra, None, None), graph)
        self.assertNotIn((AZON.emissor, None, None), graph)
        self.assertNotIn((AZON.receptor, None, None), graph)
        self.assertNotIn((AZON.teProducte, None, None), graph)

    def test_storage_sources_are_not_ontology_classes(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        storage_only_terms = (
            AZON.DadesBancaries,
            AZON.DadesEnviamentUsuari,
            AZON.HistorialCerca,
            AZON.HistorialCompra,
            AZON.UbicacioProducte,
        )

        for term in storage_only_terms:
            self.assertNotIn((term, RDF.type, OWL.Class), graph)

    def test_product_catalog_properties_are_scoped_to_producte(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        product_properties = (
            AZON.IdProducte,
            AZON.Nom,
            AZON.Descripcio,
            AZON.Categoria,
            AZON.Marca,
            AZON.Preu,
            AZON.Pes,
        )

        for prop in product_properties:
            self.assertIn((prop, RDF.type, OWL.DatatypeProperty), graph)
            self.assertIn((prop, RDFS.domain, AZON.Producte), graph)

    def test_shared_datatype_properties_keep_all_known_domains(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        expected_domains = {
            AZON.Ciutat: {
                AZON.CentreLogistic,
                AZON.Comanda,
                AZON.DadesEnviament,
                AZON.ConfirmacioLocalitzacio,
                AZON.Lot,
                AZON.PeticioTransport,
                AZON.ProducteLocalitzat,
                AZON.RespostaOfertaTransport,
            },
            AZON.IdComanda: {
                AZON.Comanda,
                AZON.DadesEnviament,
                AZON.ConfirmacioLocalitzacio,
                AZON.ConfirmacioRegistreCompra,
                AZON.PeticioRegistreCompra,
                AZON.PeticioTransport,
                AZON.ProducteLocalitzat,
                AZON.RespostaOfertaTransport,
            },
            AZON.IdLot: {
                AZON.DadesEnviament,
                AZON.ConfirmacioLocalitzacio,
                AZON.Lot,
                AZON.PeticioTransport,
                AZON.RespostaOfertaTransport,
            },
            AZON.Prioritat: {
                AZON.Comanda,
                AZON.PeticioEnviamentExtern,
            },
            AZON.TextConsulta: {
                AZON.PeticioCerca,
            },
            AZON.TotalResultats: {
                AZON.ResultatCerca,
            },
            AZON.CostTransport: {
                AZON.DadesEnviament,
                AZON.RespostaOfertaTransport,
            },
            AZON.DataEntrega: {
                AZON.Comanda,
                AZON.ConfirmacioLocalitzacio,
                AZON.Lot,
                AZON.PeticioTransport,
                AZON.ProducteLocalitzat,
                AZON.ResultatCompra,
            },
            AZON.DataEntregaDefinitiva: {
                AZON.Comanda,
                AZON.DadesEnviament,
                AZON.RespostaOfertaTransport,
                AZON.EleccioTransportista,
                AZON.ConfirmacioEnviament,
            },
        }

        for prop, domains in expected_domains.items():
            for domain in domains:
                self.assertIn((prop, RDFS.domain, domain), graph)

    def test_transport_flow_actions_include_selection_and_shipping_confirmation(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        for cls in (
            AZON.PeticioEnviamentExtern,
            AZON.EleccioTransportista,
            AZON.ConfirmacioEnviament,
        ):
            self.assertIn((cls, RDF.type, OWL.Class), graph)
            self.assertIn((cls, RDFS.subClassOf, AZON.Accio), graph)

    def test_shipping_details_response_is_modeled_as_a_response(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertIn((AZON.DadesEnviament, RDF.type, OWL.Class), graph)
        self.assertIn((AZON.DadesEnviament, RDFS.subClassOf, AZON.Resposta), graph)

        for relation in (AZON.SobreComanda, AZON.SobreLot):
            self.assertIn((relation, RDFS.domain, AZON.DadesEnviament), graph)

        for prop in (
            AZON.IdTransportista,
            AZON.NomTransportista,
            AZON.CostTransport,
            AZON.Ciutat,
            AZON.DataEntregaDefinitiva,
        ):
            self.assertIn((prop, RDFS.domain, AZON.DadesEnviament), graph)

        self.assertNotIn((AZON.Estat, RDFS.domain, AZON.DadesEnviament), graph)

    def test_purchase_result_response_is_modeled_with_estimated_delivery_fields(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertIn((AZON.ResultatCompra, RDF.type, OWL.Class), graph)
        self.assertIn((AZON.ResultatCompra, RDFS.subClassOf, AZON.Resposta), graph)
        self.assertIn((AZON.SobreComanda, RDFS.domain, AZON.ResultatCompra), graph)

        for prop in (
            AZON.IdComanda,
            AZON.Estat,
            AZON.DataEntrega,
        ):
            self.assertIn((prop, RDFS.domain, AZON.ResultatCompra), graph)

        self.assertNotIn((AZON.SobreLot, RDFS.domain, AZON.ResultatCompra), graph)
        self.assertNotIn((AZON.DataEntregaDefinitiva, RDFS.domain, AZON.ResultatCompra), graph)

    def test_deferred_purchase_classes_exist_in_the_ontology(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        for cls in (AZON.ResultatCompra, AZON.ConfirmacioLocalitzacio):
            self.assertIn((cls, RDF.type, OWL.Class), graph)
            self.assertIn((cls, RDFS.subClassOf, AZON.Resposta), graph)

        for triple in [
            (AZON.SobreComanda, RDFS.domain, AZON.ResultatCompra),
            (AZON.SobreComanda, RDFS.domain, AZON.ConfirmacioLocalitzacio),
            (AZON.SobreLot, RDFS.domain, AZON.ConfirmacioLocalitzacio),
            (AZON.Estat, RDFS.domain, AZON.ResultatCompra),
            (AZON.Estat, RDFS.domain, AZON.ConfirmacioLocalitzacio),
            (AZON.Estat, RDFS.domain, AZON.Lot),
            (AZON.IdComanda, RDFS.domain, AZON.ResultatCompra),
            (AZON.IdComanda, RDFS.domain, AZON.ConfirmacioLocalitzacio),
            (AZON.IdLot, RDFS.domain, AZON.ConfirmacioLocalitzacio),
            (AZON.DataEntrega, RDFS.domain, AZON.ResultatCompra),
            (AZON.DataEntrega, RDFS.domain, AZON.ConfirmacioLocalitzacio),
        ]:
            self.assertIn(triple, graph)

    def test_ontology_file_does_not_keep_ui_orange_annotations(self):
        ontology_text = ONTOLOGY_PATH.read_text(encoding="utf-8")
        self.assertNotIn("<rdfs:label", ontology_text)
        self.assertNotIn("<rdfs:comment", ontology_text)
        self.assertNotIn("xmlns:azon=", ontology_text)


if __name__ == "__main__":
    unittest.main()
