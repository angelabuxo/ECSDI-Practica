import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, Response, render_template, request
from rdflib import Graph, Literal, RDF, URIRef, XSD
from rdflib.exceptions import ParserError

# Aquest mòdul s'ha d'executar com a part del paquet, per exemple amb:
# `python -m AgentZon.agents.agent_compra`
from AgentZon.config import (
    AGENTZON,
    DADES_ENVIAMENT_USUARI_PATH,
    ONTOLOGY_PATH,
    PRODUCTES_PATH,
    RESPONSABLE_ENVIAMENT_PRODUCTES_PATH,
    UBICACIONS_PRODUCTES_PATH,
    WEB_DIR,
)
from AgentZon.protocols.directory import build_register_action, build_search_action, read_directory_responses
from AgentZon.protocols.cerca import ProducteModel
from AgentZon.protocols.centre_logistic import (
    DadesEnviamentProducte,
    ProducteLocalitzat,
    build_producte_localitzat_action,
    read_dades_enviament,
    read_lot_assignat_response,
)
from AgentZon.protocols.compra import (
    ComandaModel,
    InformacioUsuari,
    PeticioCompra,
    PeticioInfoUsuari,
    processar_peticio_final,
    validar_comanda,
)
from AgentZon.protocols.fipa_acl import (
    build_message,
    build_not_understood,
    get_message_properties,
    parse_message,
    send_message,
)
from AgentZon.agents.logging_utils import configure_pretty_logging


logger = logging.getLogger(__name__)


class AgentCompra:
    """
    Implementa els plans definits a Prometheus per a l'Agent Compra:
    processar la compra, registrar les dades de l'usuari, confirmar la comanda,
    localitzar els productes i simular el cobrament.
    """

    def __init__(
        self,
        ontology_path: Path = ONTOLOGY_PATH,
        productes_path: Path = PRODUCTES_PATH,
        dades_enviament_path: Path = DADES_ENVIAMENT_USUARI_PATH,
        ubicacions_path: Path = UBICACIONS_PRODUCTES_PATH,
        responsables_path: Path = RESPONSABLE_ENVIAMENT_PRODUCTES_PATH,
        directory_address: Optional[str] = None,
        message_sender=send_message,
    ):
        self.ontology_path = ontology_path
        self.productes_path = productes_path
        self.dades_enviament_path = Path(dades_enviament_path)
        self.ubicacions_path = Path(ubicacions_path)
        self.responsables_path = Path(responsables_path)
        self.directory_address = directory_address
        self.message_sender = message_sender
        self.enviaments: Dict[str, Dict[str, object]] = {}
        self._seguent_id_comanda = 0

        self.graph = Graph()
        self.graph.bind("az", AGENTZON)
        self._carregar_ontologia()
        self._carregar_productes()

    def _carregar_ontologia(self) -> None:
        """Carrega l'ontologia RDF/XML per tenir disponibles classes i propietats."""
        if self.ontology_path.exists():
            try:
                self.graph.parse(self.ontology_path, format="xml")
            except ParserError as exc:
                print(
                    f"Avís: no s'ha pogut carregar l'ontologia '{self.ontology_path}': {exc}",
                    file=sys.stderr,
                )

    def _carregar_productes(self) -> None:
        """Carrega el catàleg Turtle que actua com a font de dades de productes."""
        if not self.productes_path.exists():
            raise FileNotFoundError(f"No s'ha trobat el catàleg de productes: {self.productes_path}")

        self.graph.parse(self.productes_path, format="turtle")

    def _az(self, term: str) -> URIRef:
        """Construeix un URIRef dins del namespace de l'ontologia AgentZon."""
        return URIRef(f"{AGENTZON}{term}")

    def _carregar_json(self, path: Path, default: Optional[Dict] = None) -> Dict:
        """Carrega una font de dades JSON persistent."""
        if not path.exists():
            return default or {}

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _guardar_json(self, path: Path, dades: Dict) -> None:
        """Guarda una font de dades JSON persistent."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(dades, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def _carregar_ttl_indexat(self, path: Path, subject_type: str, id_predicate: str, camp_predicates: Dict[str, str]) -> Dict:
        """
        Carrega una font Turtle com a diccionari indexat per id.
        Exemple de sortida: {"p001": {"responsable": "agentzon", "venedor": "X"}}.
        """
        if not path.exists():
            return {}

        graph = Graph()
        graph.parse(path, format="turtle")
        resultat = {}

        for subject in graph.subjects(RDF.type, self._az(subject_type)):
            entity_id = graph.value(subject, self._az(id_predicate))
            if entity_id is None:
                continue

            key = str(entity_id.toPython())
            row = {}
            for camp, predicate in camp_predicates.items():
                value = graph.value(subject, self._az(predicate))
                if value is not None:
                    row[camp] = value.toPython()

            resultat[key] = row

        return resultat

    def _guardar_ttl_indexat(
        self,
        path: Path,
        dades: Dict[str, Dict[str, object]],
        subject_type: str,
        id_predicate: str,
        camp_predicates: Dict[str, str],
        subject_prefix: str,
    ) -> None:
        """Guarda un diccionari indexat per id en format Turtle."""
        graph = Graph()
        graph.bind("az", AGENTZON)

        for key, row in dades.items():
            subject = self._az(f"{subject_prefix}_{key}")
            graph.add((subject, RDF.type, self._az(subject_type)))
            graph.add((subject, self._az(id_predicate), Literal(str(key))))

            for camp, predicate in camp_predicates.items():
                if camp not in row:
                    continue

                value = row[camp]
                if camp == "prioritat":
                    graph.add((subject, self._az(predicate), Literal(int(value), datatype=XSD.integer)))
                else:
                    graph.add((subject, self._az(predicate), Literal(value)))

        path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=path, format="turtle")

    def _carregar_mapa(self, path: Path, tipus: str) -> Dict:
        """Carrega dades persistides des de JSON o Turtle, segons extensió."""
        if path.suffix.lower() == ".ttl":
            if tipus == "dades_enviament":
                return self._carregar_ttl_indexat(
                    path,
                    subject_type="DadesEnviamentUsuari",
                    id_predicate="IdUsuari",
                    camp_predicates={"adreca": "Adreça", "ciutat": "Ciutat", "prioritat": "Prioritat"},
                )
            if tipus == "ubicacions":
                return self._carregar_ttl_indexat(
                    path,
                    subject_type="UbicacioProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"magatzem": "Magatzem", "ciutat": "Ciutat"},
                )
            if tipus == "responsables":
                return self._carregar_ttl_indexat(
                    path,
                    subject_type="ResponsableEnviamentProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"responsable": "Responsable", "venedor": "Venedor"},
                )
            raise ValueError(f"Tipus de mapa desconegut: {tipus}")

        return self._carregar_json(path)

    def _guardar_mapa(self, path: Path, dades: Dict, tipus: str) -> None:
        """Guarda dades persistides en JSON o Turtle, segons extensió."""
        if path.suffix.lower() == ".ttl":
            if tipus == "dades_enviament":
                self._guardar_ttl_indexat(
                    path,
                    dades,
                    subject_type="DadesEnviamentUsuari",
                    id_predicate="IdUsuari",
                    camp_predicates={"adreca": "Adreça", "ciutat": "Ciutat", "prioritat": "Prioritat"},
                    subject_prefix="dades_enviament_usuari",
                )
                return
            if tipus == "ubicacions":
                self._guardar_ttl_indexat(
                    path,
                    dades,
                    subject_type="UbicacioProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"magatzem": "Magatzem", "ciutat": "Ciutat"},
                    subject_prefix="ubicacio_producte",
                )
                return
            if tipus == "responsables":
                self._guardar_ttl_indexat(
                    path,
                    dades,
                    subject_type="ResponsableEnviamentProducte",
                    id_predicate="IdProducte",
                    camp_predicates={"responsable": "Responsable", "venedor": "Venedor"},
                    subject_prefix="responsable_enviament_producte",
                )
                return
            raise ValueError(f"Tipus de mapa desconegut: {tipus}")

        self._guardar_json(path, dades)

    def inventari(self) -> List[ProducteModel]:
        """Converteix totes les instàncies RDF de Producte a models Python."""
        return [self._producte_des_de_graf(subject) for subject in self.graph.subjects(RDF.type, AGENTZON.Producte)]

    def _literal(self, subject: URIRef, predicate: URIRef, default=None):
        """Llegeix un literal RDF i retorna un valor Python normal."""
        value = self.graph.value(subject, predicate)
        return value.toPython() if value is not None else default
    
    def _literal_de_predicats(self, subject: URIRef, predicates: List[URIRef], default=None):
        """
        Cerca un valor literal provant diversos predicats.
        Serveix per mantenir compatibilitat entre versions de l'ontologia.
        """
        for predicate in predicates:
            value = self.graph.value(subject, predicate)
            if value is not None:
                return value.toPython()
        return default

    def _producte_des_de_graf(self, subject: URIRef) -> ProducteModel:
        """Reconstrueix un ProducteModel a partir de les seves propietats RDF."""
        return ProducteModel(
            # Nova ontologia: Id, Nom, Preu, Descripcio, Categoria, Marca, Pes.
            # Mantenim fallback als noms antics (*Producte) per no trencar dades heretades.
            id=str(self._literal_de_predicats(subject, [AGENTZON.Id], subject.split("/")[-1])),
            nom=str(self._literal_de_predicats(subject, [AGENTZON.Nom], "")),
            preu=float(self._literal_de_predicats(subject, [AGENTZON.Preu], 0.0)),
            descr=str(self._literal_de_predicats(subject, [AGENTZON.Descripcio], "")),
            categ=str(self._literal_de_predicats(subject, [AGENTZON.Categoria], "")),
            marca=str(self._literal_de_predicats(subject, [AGENTZON.Marca], "")),
            pes=int(float(self._literal_de_predicats(subject, [AGENTZON.Pes], 0))),
        )

    def productes_per_ids(self, ids_productes: List[str]) -> List[ProducteModel]:
        """Localitza els productes seleccionats dins del catàleg RDF."""
        productes_per_id = {producte.id: producte for producte in self.inventari()}
        productes = []

        for producte_id in ids_productes:
            if producte_id not in productes_per_id:
                raise ValueError(f"Producte desconegut: {producte_id}")
            productes.append(productes_per_id[producte_id])

        return productes

    def processar_peticio_compra(self, userid: str, productes: List[ProducteModel]) -> PeticioCompra:
        """Cp. Processar petició compra: rep la selecció inicial de productes."""
        userid = userid.strip()
        if not userid:
            raise ValueError("Cal indicar l'id de l'usuari.")
        if not productes:
            raise ValueError("Cal seleccionar almenys un producte.")

        return PeticioCompra(userid=userid, llista_productes=productes)

    def demanar_informacio_usuari(self, userid: str) -> PeticioInfoUsuari:
        """Pla demanar informació usuari: demana adreça, prioritat i pagament."""
        return PeticioInfoUsuari(userid=userid)

    def registrar_dades_usuari(self, info: InformacioUsuari) -> InformacioUsuari:
        """Pla registrar dades d'usuari: desa la resposta de l'usuari al protocol."""
        self._persistir_dades_enviament(info)
        return info

    def _persistir_dades_enviament(self, info: InformacioUsuari) -> None:
        """Escriu la font persistent Dades d'enviament Usuari."""
        dades = self._carregar_mapa(self.dades_enviament_path, "dades_enviament")
        dades[info.userid] = {
            "adreca": info.adreça,
            "ciutat": info.ciutat,
            "prioritat": info.prioritat,
        }
        self._guardar_mapa(self.dades_enviament_path, dades, "dades_enviament")

    def gestionar_compra(self, compra: PeticioCompra, info_usuari: InformacioUsuari) -> ComandaModel:
        """Cp. Gestionar compra: crea, valida i registra la comanda."""
        logger.debug(
            "gestionant compra userid=%s productes=%s",
            compra.userid,
            [producte.id for producte in compra.llista_productes],
        )
        info_persistida = self.registrar_dades_usuari(info_usuari)
        comanda = processar_peticio_final(compra, info_persistida, self._nou_id_comanda())
        logger.debug(
            "comanda creada id=%s userid=%s total=%s estat=%s entrega_estimada=%s",
            comanda.id,
            comanda.userid,
            comanda.import_total,
            comanda.estat,
            comanda.data_entrega_estimada,
        )
        if not validar_comanda(comanda):
            raise ValueError("La comanda no és vàlida.")

        logger.debug("comanda validada id=%s", comanda.id)
        # TODO: Protocol per avisar a l'Ag. Cobrador sobre les dades bancàries de l'usuari.
        # TODO: Protocol per avisar a Ag. Opinador per registrar la comanda a BD.
        self.localitzar_productes(comanda)
        return comanda

    def _nou_id_comanda(self) -> str:
        if self._seguent_id_comanda > 9999:
            raise ValueError("S'ha esgotat el rang d'identificadors de comanda (0000-9999).")

        id_comanda = f"{self._seguent_id_comanda:04d}"
        self._seguent_id_comanda += 1
        return id_comanda

    def registrar_al_directori(self, address: str) -> dict:
        if not self.directory_address:
            raise ValueError("Cal configurar directory_address per registrar l'Agent Compra.")
        logger.debug("registrant agent compra al directori address=%s directory=%s", address, self.directory_address)
        content = build_register_action(
            name="agent-compra",
            uri=AGENTZON.agent_compra,
            address=address,
            agent_type="AgentCompra",
        )
        message = build_message("request", AGENTZON.agent_compra, AGENTZON.directory_agent, content, msgcnt=1)
        response = self.message_sender(self.directory_address, message)
        props = get_message_properties(response)
        logger.debug("resposta registre directori performative=%s", props.get("performative") if props else None)
        return props

    def _cercar_centre_logistic_al_directori(self, centre_logistic_id: str) -> Optional[Dict[str, object]]:
        if not self.directory_address:
            logger.debug("directori no configurat per centre_logistic=%s", centre_logistic_id)
            return None

        logger.debug("cercant centre logistic al directori centre_logistic=%s", centre_logistic_id)
        search = build_search_action(agent_type="AgentCentreLogistic", name=centre_logistic_id)
        request_graph = build_message(
            "request",
            AGENTZON.agent_compra,
            AGENTZON.directory_agent,
            search,
            msgcnt=1,
        )
        response = self.message_sender(self.directory_address, request_graph)
        props = get_message_properties(response)
        if not props or props.get("performative") != "inform":
            logger.debug(
                "resposta cerca centre logistic no inform centre_logistic=%s performative=%s",
                centre_logistic_id,
                props.get("performative") if props else None,
            )
            return None

        results = read_directory_responses(response)
        logger.debug("resultats directori centre_logistic=%s count=%s", centre_logistic_id, len(results))
        return results[0] if results else None

    def _enviar_producte_a_centre_logistic(
        self,
        centre_logistic_id: str,
        producte_localitzat: ProducteLocalitzat,
    ) -> Dict[str, object]:
        directory_entry = self._cercar_centre_logistic_al_directori(centre_logistic_id)
        if directory_entry is not None:
            logger.debug(
                "enviant producte a centre logistic centre_logistic=%s producte=%s address=%s",
                centre_logistic_id,
                producte_localitzat.id_producte,
                directory_entry["address"],
            )
            request_graph = build_message(
                "request",
                AGENTZON.agent_compra,
                directory_entry["uri"],
                build_producte_localitzat_action(producte_localitzat),
                msgcnt=1,
            )
            response = self.message_sender(directory_entry["address"], request_graph)
            props = get_message_properties(response)
            if props and props.get("performative") == "confirm" and props.get("content") is not None:
                lot_assignat = read_lot_assignat_response(response, props["content"])
                logger.debug(
                    "centre logistic confirma lot centre_logistic=%s producte=%s lot=%s",
                    centre_logistic_id,
                    producte_localitzat.id_producte,
                    lot_assignat["id_lot"],
                )
                return {
                    "centre_logistic": centre_logistic_id,
                    "id_lot": lot_assignat["id_lot"],
                    "estat": "PENDENT",
                }

            logger.debug(
                "centre logistic no confirma producte centre_logistic=%s producte=%s performative=%s",
                centre_logistic_id,
                producte_localitzat.id_producte,
                props.get("performative") if props else None,
            )

        logger.debug(
            "producte pendent d'agent centre_logistic=%s producte=%s",
            centre_logistic_id,
            producte_localitzat.id_producte,
        )
        return {
            "centre_logistic": centre_logistic_id,
            "estat": "PENDENT_AGENT",
        }

    def localitzar_productes(self, comanda: ComandaModel) -> Dict[str, object]:
        """
        Cp. Localitzar productes: verifica disponibilitat al catàleg i prepara
        una resposta local d'enviament per a aquesta entrega.
        """
        ids_comanda = [producte.id for producte in comanda.llista_productes]
        productes_per_id = {producte.id: producte for producte in comanda.llista_productes}
        logger.debug("localitzant productes comanda=%s productes=%s", comanda.id, ids_comanda)

        dades_usuari = self._carregar_mapa(self.dades_enviament_path, "dades_enviament")
        ubicacions = self._carregar_mapa(self.ubicacions_path, "ubicacions")
        responsables = self._carregar_mapa(self.responsables_path, "responsables")
        responsables_enviament = {}
        centres_logistics_enviament = {}

        for producte_id in ids_comanda:
            responsable = responsables.get(producte_id, {"responsable": "agentzon"})
            responsable_tipus = responsable.get("responsable", "agentzon")

            if responsable_tipus == "extern":
                responsables_enviament[producte_id] = responsable.get("venedor", "Venedor extern")
                logger.debug(
                    "producte extern producte=%s venedor=%s comanda=%s",
                    producte_id,
                    responsables_enviament[producte_id],
                    comanda.id,
                )
                # TODO: Protocol per avisar al venedor extern de que producte X s'ha d'enviar a Y abans de Z.
            else:
                if producte_id not in ubicacions:
                    raise ValueError(f"No hi ha ubicació persistent per al producte {producte_id}.")
                responsables_enviament[producte_id] = "AgentZon"
                ubicacio = ubicacions[producte_id]
                centre_logistic_id = ubicacio.get("magatzem")
                if not centre_logistic_id:
                    raise ValueError(f"No hi ha centre logístic persistent per al producte {producte_id}.")

                logger.debug(
                    "producte intern producte=%s centre_logistic=%s comanda=%s",
                    producte_id,
                    centre_logistic_id,
                    comanda.id,
                )
                # De moment assumim que cada producte només està en un centre logístic.
                # En el futur caldrà resoldre productes disponibles en diversos centres.
                producte_localitzat = ProducteLocalitzat(
                    id_producte=producte_id,
                    id_comanda=comanda.id,
                    userid=comanda.userid,
                    adreca=dades_usuari[comanda.userid]["adreca"],
                    ciutat=dades_usuari[comanda.userid].get("ciutat", dades_usuari[comanda.userid]["adreca"]),
                    prioritat=dades_usuari[comanda.userid]["prioritat"],
                    data_limit=comanda.data_entrega_estimada,
                    pes=productes_per_id[producte_id].pes,
                    import_producte=productes_per_id[producte_id].preu,
                )
                centres_logistics_enviament[producte_id] = self._enviar_producte_a_centre_logistic(
                    centre_logistic_id,
                    producte_localitzat,
                )

        enviament = {
            "data_entrega_estimada": comanda.data_entrega_estimada,
            "adreca": dades_usuari[comanda.userid]["adreca"],
            "ciutat": dades_usuari[comanda.userid].get("ciutat", dades_usuari[comanda.userid]["adreca"]),
            "prioritat": dades_usuari[comanda.userid]["prioritat"],
            "responsables": responsables_enviament,
            "centres_logistics": centres_logistics_enviament,
        }
        self.enviaments[comanda.id] = enviament
        logger.debug(
            "enviament preparat comanda=%s responsables=%s centres=%s",
            comanda.id,
            responsables_enviament,
            centres_logistics_enviament,
        )
        return enviament

    def processar_dades_enviament(self, dades: DadesEnviamentProducte) -> Dict[str, object]:
        """
        Pla informar usuari sobre l'enviament: processa el protocol Dades
        Enviament rebut de l'Agent Centre Logístic i prepara la notificació.
        """
        if dades.id_comanda not in self.enviaments:
            raise ValueError(f"Comanda desconeguda: {dades.id_comanda}")

        logger.debug(
            "processant dades enviament comanda=%s producte=%s lot=%s transportista=%s data=%s",
            dades.id_comanda,
            dades.id_producte,
            dades.id_lot,
            dades.transportista_id,
            dades.data_entrega_definitiva,
        )
        enviament = self.enviaments[dades.id_comanda]
        responsables = enviament.get("responsables", {})
        if dades.id_producte not in responsables:
            raise ValueError(f"Producte desconegut per a la comanda {dades.id_comanda}: {dades.id_producte}")

        dades_definitives = enviament.setdefault("dades_definitives", {})
        dades_definitives[dades.id_producte] = {
            "id_lot": dades.id_lot,
            "transportista_id": dades.transportista_id,
            "data_entrega_definitiva": dades.data_entrega_definitiva,
        }
        logger.debug(
            "dades definitives guardades comanda=%s producte=%s",
            dades.id_comanda,
            dades.id_producte,
        )

        return {
            "userid": dades.userid,
            "id_comanda": dades.id_comanda,
            "id_producte": dades.id_producte,
            "transportista_id": dades.transportista_id,
            "data_entrega_definitiva": dades.data_entrega_definitiva,
        }

def _int_obligatori(valor: str, missatge: str) -> int:
    """Converteix un camp obligatori del formulari a enter."""
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(missatge) from exc


def create_app(compra_agent: Optional[AgentCompra] = None) -> Flask:
    """Crea la interfície HTML que pertany a l'Agent Compra."""
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    compra_agent = compra_agent or AgentCompra()

    @app.route("/comm", methods=["GET"])
    def comm():
        try:
            incoming = parse_message(request.args.get("content", ""))
            props = get_message_properties(incoming)
            if not props or props.get("performative") != "request" or props.get("content") is None:
                response = build_not_understood(AGENTZON.agent_compra, AGENTZON.unknown_agent, msgcnt=1)
            elif (props["content"], RDF.type, AGENTZON.DadesEnviamentProducte) in incoming:
                dades = read_dades_enviament(incoming, props["content"])
                compra_agent.processar_dades_enviament(dades)
                response = build_message(
                    "confirm",
                    AGENTZON.agent_compra,
                    props.get("sender", AGENTZON.unknown_agent),
                    None,
                    msgcnt=1,
                )
            else:
                response = build_not_understood(
                    AGENTZON.agent_compra,
                    props.get("sender", AGENTZON.unknown_agent),
                    msgcnt=1,
                )
        except Exception:
            response = build_not_understood(AGENTZON.agent_compra, AGENTZON.unknown_agent, msgcnt=1)

        return Response(response.serialize(format="xml"), mimetype="application/rdf+xml")

    @app.route("/", methods=["GET", "POST"])
    def index():
        resultat = None
        error = None
        productes = compra_agent.inventari()
        valors = {
            "userid": "",
            "adreca": "",
            "ciutat": "",
            "prioritat": "2",
            "metodepagament": "",
            "productes": [],
        }

        if request.method == "POST":
            valors = {
                "userid": request.form.get("userid", ""),
                "adreca": request.form.get("adreca", ""),
                "ciutat": request.form.get("ciutat", ""),
                "prioritat": request.form.get("prioritat", "2"),
                "metodepagament": request.form.get("metodepagament", ""),
                "productes": request.form.getlist("productes"),
            }

            try:
                productes_seleccionats = compra_agent.productes_per_ids(valors["productes"])
                compra = compra_agent.processar_peticio_compra(valors["userid"], productes_seleccionats)
                compra_agent.demanar_informacio_usuari(compra.userid)
                info_usuari = InformacioUsuari(
                    userid=compra.userid,
                    adreça=valors["adreca"],
                    ciutat=valors["ciutat"],
                    prioritat=_int_obligatori(valors["prioritat"], "La prioritat ha de ser numèrica."),
                    metodepagament=valors["metodepagament"],
                )
                comanda = compra_agent.gestionar_compra(compra, info_usuari)
                resultat = {
                    "comanda": comanda,
                    "enviament": compra_agent.enviaments[comanda.id],
                }
            except ValueError as exc:
                error = str(exc)

        return render_template("compra.html", productes=productes, resultat=resultat, error=error, valors=valors)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentZon Agent Compra")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9002)
    parser.add_argument("--directory", default="http://127.0.0.1:9000/Register")
    parser.add_argument("--address", default=None)
    args = parser.parse_args()

    configure_pretty_logging()
    agent = AgentCompra(directory_address=args.directory)
    advertised_address = args.address or f"http://127.0.0.1:{args.port}/comm"
    try:
        agent.registrar_al_directori(advertised_address)
    except Exception as exc:
        print(f"Avís: no s'ha pogut registrar l'Agent Compra al directori: {exc}", file=sys.stderr)

    create_app(agent).run(host=args.host, port=args.port, debug=True)
