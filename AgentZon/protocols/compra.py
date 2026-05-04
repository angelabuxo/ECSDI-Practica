"""
Protocol de domini "comanda / compra" — **objectes Python normals**, no RDF directe aquí.

Això va a part de FIPA-ACL: els agents acaben convertint aquests models a tripletes
amb l'ontologia AgentZon, però aquest fitxer és el lloc on es defineixen les estructures
de dades i les funcions petites (validació, factories) que la lògica de negoci entén
sense parlar de "performatives".

Resum del flux típic:
1) L'usuari vol comprar → `PeticioCompra` (qui és + quins productes).
2) Cal omplir dades d'enviament/pagament → `PeticioInfoUsuari` / `InformacioUsuari`.
3) Es compacta tot a `ComandaModel` i es valida amb `validar_comanda`.
4) Es generen peticions cap a altres agents (registre, enviament venedor extern, centre logístic).
"""

from typing import List
from .cerca import ProducteModel
from datetime import datetime, timedelta

# --- Model intern de comanda (estat que portes al teu agent abans/durant el pipeline) ---


class ComandaModel:
    """
    Comanda "completa" un cop tens usuari + carretó + adreça + prioritat + mètode de pagament.
    L'estat comença en PENDENT; la pràctica sovint exclou el pagament real però el camp hi és.
    """

    def __init__(
        self,
        userid: str,
        llista_productes: List[ProducteModel],
        adreça: str,
        ciutat: str,
        prioritat: int,
        metodepagament: str,
        id_comanda: str,
    ):
        self.id = id_comanda  # identificador únic
        self.userid = userid  # qui compra
        self.llista_productes = llista_productes  # llista de ProducteModel (ve de cerca.py)
        self.adreça = adreça  # línia d'adreça per l'enviament
        self.ciutat = ciutat
        self.prioritat = prioritat  # 1 = express, 2 = normal (veure _calcular_data_entrega)
        self.metodepagament = metodepagament  # string lliure per la demo (targeta, contra reemborsament, etc.)
        self.estat = "PENDENT"  # PENDENT / PAGADA / ENVIADA — el que facis servir al teu flux
        self.import_total = self._calcular_total()  # suma preus dels productes del carretó
        self.data_entrega_estimada = self._calcular_data_entrega()  # string data ISO (YYYY-MM-DD)

    def _calcular_total(self) -> float:
        """Suma simple: cada ProducteModel ha de tenir `.preu`."""
        return sum(p.preu for p in self.llista_productes)

    def _calcular_data_entrega(self) -> str:
        """
        Regla de negoci ràpida: prioritat 1 → l'endemà; prioritat 2 → +3 dies.
        Es treu la part de microsegons per tenir dates netes; es retorna només la data (sense hora).
        """
        if self.prioritat not in [1, 2]:
            raise ValueError("Prioritat ha de ser 1 (Express) o 2 (Normal)")
        dies = 1 if self.prioritat == 1 else 3
        data = datetime.now().replace(microsecond=0) + timedelta(days=dies)
        return data.date().isoformat()


# ------------------------------------------------------------------
# Passes del diàleg amb l'usuari (abans de tenir ComandaModel tancat)
# ------------------------------------------------------------------


class PeticioCompra:
    """Primera peça: "vull comprar aquests productes" encara sense adreça ni prioritat."""

    def __init__(self, userid: str, llista_productes: List[ProducteModel]):
        self.userid = userid
        self.llista_productes = llista_productes


class PeticioInfoUsuari:
    """
    Demana a l'usuari (o a un servei) que ompli camps. `camps_requerits` és una llista de noms
    de camp per si vols ser explícit què falta; per defecte els quatre clàssics del flux AgentZon.
    """

    def __init__(self, userid: str, camps_requerits: List[str] = None):
        self.userid = userid
        self.camps_requerits = camps_requerits or ["adreça", "ciutat", "prioritat", "metodepagament"]


class InformacioUsuari:
    """Resposta que omple el forat de dades: ja pots construir `ComandaModel`."""

    def __init__(self, userid: str, adreça: str, ciutat: str, prioritat: int, metodepagament: str):
        self.userid = userid
        self.adreça = adreça
        self.ciutat = ciutat
        self.prioritat = prioritat
        self.metodepagament = metodepagament


# ------------------------------------------------------------------
# Missatges cap a altres agents (encapsulen payload per quan el tradueixis a RDF)
# ------------------------------------------------------------------


class PeticioRegistreCompra:
    """
    Cap a un agent tipus "opinador / recomanador": deixar constància de la compra per feedback futur.
    No és obligatori que existixi a tots els desplegaments, però el model ja està definit.
    """

    def __init__(self, id_comanda: str, userid: str, llista_productes: List[ProducteModel], data_hora_compra: str):
        self.id_comanda = id_comanda
        self.userid = userid
        self.llista_productes = llista_productes
        self.data_hora_compra = data_hora_compra  # ISO string, moment de tancar la compra


class PeticioEnviamentVenedorExtern:
    """Enviament quan el producte ve d'un venedor extern (no del magatzem intern)."""

    def __init__(self, producte: ProducteModel, venedor: str, adreça: str, ciutat: str, data_limit: str):
        self.producte = producte
        self.venedor = venedor  # identificador del venedor (string o URI segons com ho lliguis)
        self.adreça = adreça
        self.ciutat = ciutat
        self.data_limit = data_limit  # fins quan ha d'arribar (coherent amb prioritat / promeses)


class PeticioEnviamentCentreLogistic:
    """Mateixa idea que l'anterior però el que coordina és el centre logístic (stock propi)."""

    def __init__(self, producte: ProducteModel, centre_logistic: str, adreça: str, ciutat: str, data_limit: str):
        self.producte = producte
        self.centre_logistic = centre_logistic
        self.adreça = adreça
        self.ciutat = ciutat
        self.data_limit = data_limit


def crear_peticio_registre_compra(comanda: ComandaModel) -> PeticioRegistreCompra:
    """Factory: de una comanda tancada surt el objecte per notificar el registre (amb timestamp ara)."""
    return PeticioRegistreCompra(
        id_comanda=comanda.id,
        userid=comanda.userid,
        llista_productes=comanda.llista_productes,
        data_hora_compra=datetime.now().isoformat(),
    )


def crear_peticio_enviament_venedor_extern(
    producte: ProducteModel,
    venedor: str,
    adreça: str,
    ciutat: str,
    data_limit: str,
) -> PeticioEnviamentVenedorExtern:
    """Només empaqueta arguments a la classe — per tenir constructor consistent i llegible als agents."""
    return PeticioEnviamentVenedorExtern(
        producte=producte,
        venedor=venedor,
        adreça=adreça,
        ciutat=ciutat,
        data_limit=data_limit,
    )


def crear_peticio_enviament_centre_logistic(
    producte: ProducteModel,
    centre_logistic: str,
    adreça: str,
    ciutat: str,
    data_limit: str,
) -> PeticioEnviamentCentreLogistic:
    """Igual que l'anterior però per la petició al centre logístic."""
    return PeticioEnviamentCentreLogistic(
        producte=producte,
        centre_logistic=centre_logistic,
        adreça=adreça,
        ciutat=ciutat,
        data_limit=data_limit,
    )


# ------------------------------------------------------------------


def processar_peticio_final(compra: PeticioCompra, resposta_info: InformacioUsuari, id_comanda: str) -> ComandaModel:
    """
    Uneix la intenció de compra (`PeticioCompra`) amb les dades d'usuari (`InformacioUsuari`)
    i un id de comanda que ja hagis generat (UUID, comptador, el que sigui).
    """
    return ComandaModel(
        id_comanda=id_comanda,
        userid=compra.userid,
        llista_productes=compra.llista_productes,
        adreça=resposta_info.adreça,
        ciutat=resposta_info.ciutat,
        prioritat=resposta_info.prioritat,
        metodepagament=resposta_info.metodepagament,
    )


def validar_comanda(comanda: ComandaModel) -> bool:
    """
    Comprovacions mínimes abans d'acceptar la comanda al pipeline (carretó buit, camps buits, prioritat vàlida).
    Retorna False si alguna cosa falla; True si passa totes les regles d'aquí.
    """
    if not comanda.llista_productes:
        return False
    if not comanda.adreça or not comanda.adreça.strip():
        return False
    if not comanda.ciutat or not comanda.ciutat.strip():
        return False
    if comanda.prioritat not in [1, 2]:
        return False
    if not comanda.metodepagament or not comanda.metodepagament.strip():
        return False
    return True
