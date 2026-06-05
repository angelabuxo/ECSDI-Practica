import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AGN, AZON


class AgentDataOwnershipTests(unittest.TestCase):
    def test_runtime_only_assigns_owned_paths(self):
        from agents import (
            agent_cercador,
            agent_compra,
            agent_cobrador,
            agent_opinador,
            agent_retornador,
            agent_venedor_extern,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            directory_agent = Agent(
                "DirectoryAgent",
                AGN.Directory,
                "http://directory.test/Register",
                "http://directory.test/Stop",
            )

            agent_compra.configure_runtime(
                {
                    "agent": Agent("CompraAgent", AGN.Compra, "http://compra.test/comm", "http://compra.test/Stop"),
                    "directory_agent": directory_agent,
                    "data_dir": data_dir,
                }
            )
            self.assertIsNone(getattr(agent_compra, "CATALOG_PATH", None))
            self.assertIsNone(getattr(agent_compra, "USER_BANK_PATH", None))
            self.assertEqual(agent_compra.SHIPPING_PATH.name, "dades_enviament_usuari.ttl")
            self.assertEqual(agent_compra.LOCATIONS_PATH.name, "ubicacions_productes.ttl")
            self.assertEqual(
                agent_compra.SHIPPING_RESPONSIBILITY_PATH.name,
                "responsable_enviament_productes.ttl",
            )

            agent_opinador.configure_runtime(
                {
                    "agent": Agent(
                        "OpinadorAgent",
                        AGN.Opinador,
                        "http://opinador.test/comm",
                        "http://opinador.test/Stop",
                    ),
                    "directory_agent": directory_agent,
                    "data_dir": data_dir,
                    "proactive_enabled": False,
                }
            )
            self.assertIsNone(getattr(agent_opinador, "CATALOG_PATH", None))
            self.assertEqual(agent_opinador.SEARCH_HISTORY_PATH.name, "historial_cerques.ttl")
            self.assertEqual(agent_opinador.PURCHASE_HISTORY_PATH.name, "historial_compres.ttl")
            self.assertEqual(agent_opinador.FEEDBACK_PATH.name, "feedback.ttl")

            agent_retornador.configure_runtime(
                {
                    "agent": Agent(
                        "RetornadorAgent",
                        AGN.Retornador,
                        "http://retornador.test/comm",
                        "http://retornador.test/Stop",
                    ),
                    "directory_agent": directory_agent,
                    "data_dir": data_dir,
                }
            )
            self.assertIsNone(getattr(agent_retornador, "PURCHASE_HISTORY_PATH", None))
            self.assertIsNone(getattr(agent_retornador, "CATALOG_PATH", None))
            self.assertIsNone(getattr(agent_retornador, "SHIPPING_RESPONSIBILITY_PATH", None))
            self.assertEqual(agent_retornador.REFUNDS_PATH.name, "devolucions.ttl")

            agent_venedor_extern.configure_runtime(
                {
                    "agent": Agent(
                        "VenedorExternAgent",
                        AGN.VenedorExtern,
                        "http://venedor.test/comm",
                        "http://venedor.test/Stop",
                    ),
                    "directory_agent": directory_agent,
                    "data_dir": data_dir,
                }
            )
            self.assertIsNone(getattr(agent_venedor_extern, "SHIPPING_RESPONSIBILITY_PATH", None))
            self.assertIsNone(getattr(agent_venedor_extern, "LOCATIONS_PATH", None))
            self.assertIsNone(getattr(agent_venedor_extern, "SELLER_BANK_PATH", None))

            agent_cobrador.configure_runtime(
                {
                    "agent": Agent(
                        "CobradorAgent",
                        AGN.Cobrador,
                        "http://cobrador.test/comm",
                        "http://cobrador.test/Stop",
                    ),
                    "directory_agent": directory_agent,
                    "data_dir": data_dir,
                }
            )
            self.assertIsNone(getattr(agent_cobrador, "CATALOG_PATH", None))

            agent_cercador.configure_runtime(
                {
                    "agent": Agent(
                        "CercadorAgent",
                        AGN.Cercador,
                        "http://cercador.test/comm",
                        "http://cercador.test/Stop",
                    ),
                    "directory_agent": directory_agent,
                    "data_dir": data_dir,
                }
            )
            self.assertEqual(agent_cercador.CATALOG_PATH.name, "productes.ttl")
            self.assertIsNone(getattr(agent_cercador, "SEARCH_HISTORY_PATH", None))

    def test_owner_query_protocols_roundtrip(self):
        from protocols.cerca import (
            build_peticio_consulta_productes,
            extract_product_snapshots,
            parse_peticio_consulta_productes,
        )
        from protocols.compra import (
            build_confirmacio_registre_producte_extern_compra,
            build_peticio_registre_producte_extern_compra,
            parse_confirmacio_registre_producte_extern_compra,
            parse_peticio_registre_producte_extern_compra,
        )
        from protocols.opinador import (
            build_confirmacio_registre_cerca,
            build_peticio_consulta_compres_usuari,
            build_peticio_registre_cerca,
            build_resultat_consulta_compres_usuari,
            parse_confirmacio_registre_cerca,
            parse_peticio_consulta_compres_usuari,
            parse_peticio_registre_cerca,
            parse_resultat_consulta_compres_usuari,
        )
        from protocols.pagament import (
            build_peticio_consulta_dades_venedor,
            build_resultat_consulta_dades_venedor,
            parse_peticio_consulta_dades_venedor,
            parse_resultat_consulta_dades_venedor,
        )

        lookup = build_peticio_consulta_productes(["P1001", "P1002"], msgcnt=1)
        lookup_content = lookup.value(predicate=RDF.type, object=AZON.PeticioConsultaProductes)
        self.assertEqual(
            parse_peticio_consulta_productes(lookup, lookup_content),
            ["P1001", "P1002"],
        )

        search_registration = build_peticio_registre_cerca(
            {
                "user_id": "USER-1",
                "criteria": {
                    "text": "",
                    "category": "periferics",
                    "brand": "KeyCo",
                    "min_price": None,
                    "max_price": None,
                },
                "products": [
                    {
                        "product_id": "P1001",
                        "name": "Teclat",
                        "category": "periferics",
                        "brand": "KeyCo",
                        "price": 50.0,
                        "weight": 0.8,
                    }
                ],
            },
            msgcnt=2,
        )
        parsed_search_registration = parse_peticio_registre_cerca(search_registration)
        self.assertEqual(parsed_search_registration["user_id"], "USER-1")
        self.assertEqual(parsed_search_registration["products"][0]["product_id"], "P1001")
        search_confirmation = build_confirmacio_registre_cerca("USER-1", msgcnt=3)
        self.assertEqual(parse_confirmacio_registre_cerca(search_confirmation)["user_id"], "USER-1")

        register = build_peticio_registre_producte_extern_compra(
            {
                "product_id": "P1030",
                "seller_id": "SELLER-1",
                "requires_external_logistics": True,
                "centre_id": "CL-BCN",
            },
            msgcnt=4,
        )
        self.assertEqual(parse_peticio_registre_producte_extern_compra(register)["product_id"], "P1030")
        confirmation = build_confirmacio_registre_producte_extern_compra("P1030", msgcnt=5)
        self.assertEqual(parse_confirmacio_registre_producte_extern_compra(confirmation)["product_id"], "P1030")

        purchases = build_resultat_consulta_compres_usuari(
            "USER-1",
            [
                {
                    "order_id": "ORDER-1",
                    "products": [
                        {
                            "product_id": "P1001",
                            "name": "Teclat",
                            "price": 50.0,
                            "seller_id": "",
                            "requires_external_logistics": False,
                        }
                    ],
                    "shipping_data": {"city": "Barcelona"},
                }
            ],
            msgcnt=6,
        )
        self.assertEqual(parse_resultat_consulta_compres_usuari(purchases)[0]["order_id"], "ORDER-1")
        self.assertEqual(
            parse_peticio_consulta_compres_usuari(
                build_peticio_consulta_compres_usuari("USER-1", msgcnt=7)
            ),
            "USER-1",
        )

        profile_request = build_peticio_consulta_dades_venedor("SELLER-1", msgcnt=8)
        self.assertEqual(parse_peticio_consulta_dades_venedor(profile_request), "SELLER-1")
        profile_reply = build_resultat_consulta_dades_venedor(
            {
                "seller_id": "SELLER-1",
                "bank_data": "ES12 2100 1234 5678 9012",
                "seller_name": "Vendor",
            },
            msgcnt=9,
        )
        self.assertEqual(parse_resultat_consulta_dades_venedor(profile_reply)["seller_name"], "Vendor")

        self.assertEqual(extract_product_snapshots(build_peticio_consulta_productes([], msgcnt=10)), [])
