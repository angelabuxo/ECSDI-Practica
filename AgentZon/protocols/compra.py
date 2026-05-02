from typing import List
from .cerca import ProducteModel
from datetime import datetime, timedelta

# definició del model comanda.
class ComandaModel:
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
        self.id = id_comanda                                            # id de comanda autogenerat
        self.userid = userid                                            # id de l'usuari
        self.llista_productes = llista_productes                        # productes a comprar
        self.adreça = adreça                                            # adreça d'enviament
        self.ciutat = ciutat                                            # ciutat d'enviament
        self.prioritat = prioritat                                      # prioritat d'enviament
        self.metodepagament = metodepagament                            # mètode de pagament
        self.estat = "PENDENT"                                          # estat (PENDENT, PAGADA, ENVIADA)
        self.import_total = self._calcular_total()                      # import total
        self.data_entrega_estimada = self._calcular_data_entrega()      # data estimada

    # func per calcular el preu total de la comanda
    def _calcular_total(self) -> float:
        return sum(p.preu for p in self.llista_productes)

    # func per calcular la data d'entrega estimada
    def _calcular_data_entrega(self) -> str:
        # si prioritat és 1 - 24h, si és 2 72h
        if self.prioritat not in [1, 2]:
            raise ValueError("Prioritat ha de ser 1 (Express) o 2 (Normal)")
        dies = 1 if self.prioritat == 1 else 3
        data = datetime.now().replace(microsecond=0) + timedelta(days=dies)
        return data.date().isoformat()

# ------------------------------------------------------------------

# definició de l'accio PeticioCompra
class PeticioCompra:
    def __init__(self, userid: str, llista_productes: List[ProducteModel]):
        self.userid = userid                                            # id de l'usuari
        self.llista_productes = llista_productes                        # productes a comprar

# definició de l'accio PeticioInfoUsuari
class PeticioInfoUsuari:
    def __init__(self, userid: str, camps_requerits: List[str] = None):
        self.userid = userid
        self.camps_requerits = camps_requerits or ["adreça", "ciutat", "prioritat", "metodepagament"]

# definició de la resposta
class InformacioUsuari:
    def __init__(self, userid: str, adreça: str, ciutat: str, prioritat: int, metodepagament: str):
        self.userid = userid                                            # id de l'usuari
        self.adreça = adreça                                            # adreça d'enviament
        self.ciutat = ciutat                                            # ciutat d'enviament
        self.prioritat = prioritat                                      # prioritat d'enviament
        self.metodepagament = metodepagament                            # mètode de pagament

# ------------------------------------------------------------------

# Protocol Agent Compra -> Agent Opinador. Permet registrar una compra per
# futurs feedbacks o recomanacions.
class PeticioRegistreCompra:
    def __init__(self, id_comanda: str, userid: str, llista_productes: List[ProducteModel], data_hora_compra: str):
        self.id_comanda = id_comanda
        self.userid = userid
        self.llista_productes = llista_productes
        self.data_hora_compra = data_hora_compra


# Protocol Agent Compra -> Agent Venedor Extern.
class PeticioEnviamentVenedorExtern:
    def __init__(self, producte: ProducteModel, venedor: str, adreça: str, ciutat: str, data_limit: str):
        self.producte = producte
        self.venedor = venedor
        self.adreça = adreça
        self.ciutat = ciutat
        self.data_limit = data_limit


# Protocol Agent Compra -> Agent Centre Logístic.
class PeticioEnviamentCentreLogistic:
    def __init__(self, producte: ProducteModel, centre_logistic: str, adreça: str, ciutat: str, data_limit: str):
        self.producte = producte
        self.centre_logistic = centre_logistic
        self.adreça = adreça
        self.ciutat = ciutat
        self.data_limit = data_limit


def crear_peticio_registre_compra(comanda: ComandaModel) -> PeticioRegistreCompra:
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
    return PeticioEnviamentCentreLogistic(
        producte=producte,
        centre_logistic=centre_logistic,
        adreça=adreça,
        ciutat=ciutat,
        data_limit=data_limit,
    )

# ------------------------------------------------------------------

# amb la petició de compra i la resposta d'informació de l'usuari creem el model
def processar_peticio_final(compra: PeticioCompra, resposta_info: InformacioUsuari, id_comanda: str) -> ComandaModel:
    return ComandaModel(
        id_comanda=id_comanda,
        userid=compra.userid,
        llista_productes=compra.llista_productes,
        adreça=resposta_info.adreça,
        ciutat=resposta_info.ciutat,
        prioritat=resposta_info.prioritat,
        metodepagament=resposta_info.metodepagament
    )

# validar que la comanda sigui correcte
def validar_comanda(comanda: ComandaModel) -> bool:
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
