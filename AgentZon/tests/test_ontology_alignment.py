"""Structural assertions about the refined AgentZon ontology vocabulary."""

import ast
import unittest
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, OWL, RDF
from rdflib.namespace import RDFS

from AgentUtil.OntoNamespaces import AZON


ONTOLOGY_PATH = Path(__file__).resolve().parents[1] / "ontologia" / "AgentZonOntology.rdf"
RUNTIME_RDF_ROOTS = (
    Path(__file__).resolve().parents[1] / "protocols",
    Path(__file__).resolve().parents[1] / "services",
)


class OntologyAlignmentTests(unittest.TestCase):
    def object_property_domains(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")
        return {
            (str(prop), str(domain))
            for prop, domain in graph.subject_objects(RDFS.domain)
            if (prop, RDF.type, OWL.ObjectProperty) in graph
        }

    def datatype_property_domains(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")
        return {
            (str(prop), str(domain))
            for prop, domain in graph.subject_objects(RDFS.domain)
            if (prop, RDF.type, OWL.DatatypeProperty) in graph
        }

    def _collect_runtime_property_usage(self):
        helper_relations = {
            "link_sobre_comanda": "SobreComanda",
            "link_sobre_lot": "SobreLot",
            "link_assignat_transportista": "AssignatATransportista",
        }
        usage = defaultdict(set)

        for root in RUNTIME_RDF_ROOTS:
            for path in root.glob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for function_node in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
                    typed_subjects = {}
                    for stmt in ast.walk(function_node):
                        if not isinstance(stmt, ast.Call):
                            continue
                        if not isinstance(stmt.func, ast.Attribute) or stmt.func.attr not in {"add", "set"} or not stmt.args:
                            continue
                        triple = stmt.args[0]
                        if not isinstance(triple, ast.Tuple) or len(triple.elts) < 3:
                            continue
                        subject, predicate, obj = triple.elts[:3]
                        if (
                            isinstance(subject, ast.Name)
                            and isinstance(predicate, ast.Attribute)
                            and isinstance(predicate.value, ast.Name)
                            and predicate.value.id == "RDF"
                            and predicate.attr == "type"
                            and isinstance(obj, ast.Attribute)
                            and isinstance(obj.value, ast.Name)
                            and obj.value.id == "AZON"
                        ):
                            typed_subjects[subject.id] = obj.attr

                    for stmt in ast.walk(function_node):
                        if not isinstance(stmt, ast.Call):
                            continue
                        if isinstance(stmt.func, ast.Attribute) and stmt.func.attr in {"add", "set"} and stmt.args:
                            triple = stmt.args[0]
                            if not isinstance(triple, ast.Tuple) or len(triple.elts) < 3:
                                continue
                            subject, predicate, _ = triple.elts[:3]
                            if (
                                isinstance(subject, ast.Name)
                                and subject.id in typed_subjects
                                and isinstance(predicate, ast.Attribute)
                                and isinstance(predicate.value, ast.Name)
                                and predicate.value.id == "AZON"
                            ):
                                usage[typed_subjects[subject.id]].add(predicate.attr)

                        if not isinstance(stmt.func, ast.Name) or len(stmt.args) < 2:
                            continue
                        subject = stmt.args[1]
                        if not isinstance(subject, ast.Name) or subject.id not in typed_subjects:
                            continue

                        class_name = typed_subjects[subject.id]
                        helper_name = stmt.func.id
                        if helper_name in helper_relations:
                            usage[class_name].add(helper_relations[helper_name])
                        elif helper_name == "link_product":
                            relation = "TeProducte"
                            for keyword in stmt.keywords:
                                if keyword.arg == "product_kind" and isinstance(keyword.value, ast.Constant):
                                    if keyword.value.value == "extern":
                                        relation = "TeProducteExtern"
                                    elif keyword.value.value == "intern":
                                        relation = "TeProducteIntern"
                            usage[class_name].add(relation)
                        elif helper_name == "_add_snapshot_product" and len(stmt.args) >= 4:
                            predicate = stmt.args[3]
                            if (
                                isinstance(predicate, ast.Attribute)
                                and isinstance(predicate.value, ast.Name)
                                and predicate.value.id == "AZON"
                            ):
                                usage[class_name].add(predicate.attr)

        return usage

    def _class_ancestors(self, graph, class_name):
        pending = [AZON[class_name]]
        ancestors = set()
        while pending:
            current = pending.pop()
            for parent in graph.objects(current, RDFS.subClassOf):
                if parent not in ancestors and str(parent).startswith(str(AZON)):
                    ancestors.add(parent)
                    pending.append(parent)
        return ancestors

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
        self.assertIn((AZON.TeProducteExtern, RDF.type, OWL.ObjectProperty), graph)
        self.assertIn((AZON.TeProducteIntern, RDF.type, OWL.ObjectProperty), graph)
        self.assertIn((AZON.PesTotal, RDF.type, OWL.DatatypeProperty), graph)
        self.assertNotIn((AZON.AgentIntern, None, None), graph)
        self.assertNotIn((AZON.AgentCercador, None, None), graph)
        self.assertNotIn((AZON.AgentCompra, None, None), graph)
        self.assertNotIn((AZON.emissor, None, None), graph)
        self.assertNotIn((AZON.receptor, None, None), graph)
        self.assertNotIn((AZON.teProducte, None, None), graph)

    def test_product_relations_are_typed(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertIn((AZON.TeProducteExtern, RDFS.range, AZON.ProducteExtern), graph)
        self.assertIn((AZON.TeProducteIntern, RDFS.range, AZON.ProducteIntern), graph)
        self.assertIn((AZON.TeProducteExtern, RDFS.domain, AZON.AltaProducteExtern), graph)
        self.assertNotIn((AZON.TeProducteExtern, RDFS.domain, AZON.Comanda), graph)
        self.assertIn((AZON.TeProducte, RDFS.domain, AZON.Comanda), graph)

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

    def test_identifiers_live_on_entities_not_on_logistics_messages(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        id_comanda_domains = {
            domain
            for prop, domain in graph.subject_objects(RDFS.domain)
            if prop == AZON.IdComanda
        }
        id_lot_domains = {
            domain
            for prop, domain in graph.subject_objects(RDFS.domain)
            if prop == AZON.IdLot
        }
        id_transport_domains = {
            domain
            for prop, domain in graph.subject_objects(RDFS.domain)
            if prop == AZON.IdTransportista
        }

        self.assertIn(AZON.Comanda, id_comanda_domains)
        self.assertNotIn(AZON.PeticioTransport, id_comanda_domains)
        self.assertNotIn(AZON.EleccioTransportista, id_comanda_domains)
        self.assertNotIn(AZON.ResultatCompra, id_comanda_domains)
        self.assertNotIn(AZON.PeticioPagament, id_comanda_domains)
        self.assertNotIn(AZON.PeticioFeedback, id_comanda_domains)
        self.assertNotIn(AZON.PeticioDevolucio, id_comanda_domains)
        self.assertNotIn(AZON.PeticioRetornDiners, id_comanda_domains)
        self.assertIn(AZON.Feedback, id_comanda_domains)
        self.assertIn(AZON.Devolucio, id_comanda_domains)

        self.assertIn(AZON.Lot, id_lot_domains)
        self.assertNotIn(AZON.PeticioTransport, id_lot_domains)
        self.assertNotIn(AZON.ConfirmacioEnviament, id_lot_domains)

        self.assertIn(AZON.Transportista, id_transport_domains)
        self.assertNotIn(AZON.DadesEnviament, id_transport_domains)
        self.assertNotIn(AZON.EleccioTransportista, id_transport_domains)

    def test_shared_datatype_properties_keep_known_domains(self):
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
                AZON.ConfirmacioEnviament,
                AZON.ConfirmacioPagament,
                AZON.DadesEnviament,
                AZON.PeticioCobrament,
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
            AZON.PeticioCobrament,
            AZON.PeticioEnviamentExtern,
            AZON.EleccioTransportista,
            AZON.ConfirmacioEnviament,
        ):
            self.assertIn((cls, RDF.type, OWL.Class), graph)
            self.assertIn((cls, RDFS.subClassOf, AZON.Accio), graph)

        self.assertIn((AZON.PreuProducte, RDF.type, OWL.DatatypeProperty), graph)
        self.assertIn((AZON.PreuProducte, RDFS.domain, AZON.PeticioCobrament), graph)

    def test_shipping_details_response_is_modeled_as_a_response(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertIn((AZON.DadesEnviament, RDF.type, OWL.Class), graph)
        self.assertIn((AZON.DadesEnviament, RDFS.subClassOf, AZON.Resposta), graph)

        for relation in (AZON.SobreComanda, AZON.SobreLot, AZON.AssignatATransportista):
            self.assertIn((relation, RDFS.domain, AZON.DadesEnviament), graph)

        for prop in (
            AZON.NomTransportista,
            AZON.CostTransport,
            AZON.Ciutat,
            AZON.DataEntrega,
            AZON.DataEntregaDefinitiva,
            AZON.Estat,
        ):
            self.assertIn((prop, RDFS.domain, AZON.DadesEnviament), graph)

        self.assertNotIn((AZON.IdTransportista, RDFS.domain, AZON.DadesEnviament), graph)
        self.assertNotIn((AZON.IdComanda, RDFS.domain, AZON.DadesEnviament), graph)
        self.assertNotIn((AZON.IdLot, RDFS.domain, AZON.DadesEnviament), graph)

    def test_purchase_result_response_is_modeled_with_estimated_delivery_fields(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertIn((AZON.ResultatCompra, RDF.type, OWL.Class), graph)
        self.assertIn((AZON.ResultatCompra, RDFS.subClassOf, AZON.Resposta), graph)
        self.assertIn((AZON.SobreComanda, RDFS.domain, AZON.ResultatCompra), graph)

        self.assertIn((AZON.DataEntrega, RDFS.domain, AZON.ResultatCompra), graph)

        self.assertNotIn((AZON.SobreLot, RDFS.domain, AZON.ResultatCompra), graph)
        self.assertNotIn((AZON.DataEntregaDefinitiva, RDFS.domain, AZON.ResultatCompra), graph)
        self.assertNotIn((AZON.IdComanda, RDFS.domain, AZON.ResultatCompra), graph)

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
            (AZON.Estat, RDFS.domain, AZON.ConfirmacioLocalitzacio),
            (AZON.Estat, RDFS.domain, AZON.Lot),
            (AZON.DataEntrega, RDFS.domain, AZON.ResultatCompra),
            (AZON.DataEntrega, RDFS.domain, AZON.ConfirmacioLocalitzacio),
        ]:
            self.assertIn(triple, graph)

        self.assertNotIn((AZON.IdComanda, RDFS.domain, AZON.ConfirmacioLocalitzacio), graph)
        self.assertNotIn((AZON.IdLot, RDFS.domain, AZON.ConfirmacioLocalitzacio), graph)

    def test_code_aligned_domains_for_feedback_devolucio_and_pagament(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        for prop, domain in (
            (AZON.DataCompra, AZON.Feedback),
            (AZON.IdComanda, AZON.Feedback),
            (AZON.IdComanda, AZON.Devolucio),
            (AZON.IdComanda, AZON.Pagament),
            (AZON.SobreComanda, AZON.PeticioFeedback),
            (AZON.SobreComanda, AZON.PeticioDevolucio),
            (AZON.SobreComanda, AZON.PeticioRetornDiners),
            (AZON.ImportPagament, AZON.Devolucio),
            (AZON.Carrer, AZON.PeticioEnviamentExtern),
            (AZON.MetodePagament, AZON.Usuari),
            (AZON.PertanyAUsuari, AZON.PeticioCobrament),
            (AZON.TeProducteIntern, AZON.ConfirmacioLocalitzacio),
            (AZON.SobreComanda, AZON.PeticioPagament),
            (AZON.SobreComanda, AZON.ConfirmacioPagament),
            (AZON.GeneraRecomanacio, AZON.RespostaRecomanacio),
        ):
            self.assertIn((prop, RDFS.domain, domain), graph)

        self.assertNotIn((AZON.Retorna, RDF.type, OWL.ObjectProperty), graph)
        self.assertNotIn((AZON.CostBaseKg, RDF.type, OWL.DatatypeProperty), graph)
        self.assertNotIn((AZON.Banc, RDF.type, OWL.Class), graph)
        self.assertNotIn((AZON.IdBanc, RDF.type, OWL.DatatypeProperty), graph)

    def test_ontology_file_does_not_keep_ui_orange_annotations(self):
        ontology_text = ONTOLOGY_PATH.read_text(encoding="utf-8")
        self.assertNotIn("<rdfs:label", ontology_text)
        self.assertNotIn("<rdfs:comment", ontology_text)
        self.assertNotIn("xmlns:azon=", ontology_text)

    def test_ontology_does_not_redefine_owl_top_object_property(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")

        self.assertNotIn((OWL.topObjectProperty, RDFS.domain, None), graph)
        self.assertNotIn((OWL.topObjectProperty, RDFS.range, None), graph)

    def test_runtime_rdf_shapes_are_supported_by_ontology_domains(self):
        graph = Graph()
        graph.parse(ONTOLOGY_PATH, format="xml")
        missing = []

        for class_name, properties in self._collect_runtime_property_usage().items():
            accepted_domains = {AZON[class_name], *self._class_ancestors(graph, class_name)}
            for property_name in sorted(properties):
                property_domains = {
                    domain
                    for domain in graph.objects(AZON[property_name], RDFS.domain)
                    if str(domain).startswith(str(AZON))
                }
                if property_domains and property_domains & accepted_domains:
                    continue
                missing.append((class_name, property_name, sorted(str(domain) for domain in property_domains)))

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
