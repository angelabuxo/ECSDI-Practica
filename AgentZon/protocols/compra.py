from typing import List
from .cerca import ProducteModel
from datetime import datetime, timedelta
import uuid

# definició del model comanda.
class ComandaModel:
    def __init__(self, userid: str, llista_productes: List[ProducteModel], adreça: str, prioritat: int, metodepagament: str):
        self.id = str(uuid.uuid4())                                     # id únic autogenerat
        self.userid = userid                                            # id de l'usuari
        self.llista_productes = llista_productes                        # productes a comprar
        self.adreça = adreça                                            # adreça d'enviament
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
        data = datetime.now() + timedelta(days=dies)
        return data.strftime("%d/%m/%Y")

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
        self.camps_requerits = camps_requerits or ["adreça", "prioritat", "metodepagament"]

# definició de la resposta
class InformacioUsuari:
    def __init__(self, userid: str, adreça: str, prioritat: int, metodepagament: str):
        self.userid = userid                                            # id de l'usuari
        self.adreça = adreça                                            # adreça d'enviament
        self.prioritat = prioritat                                      # prioritat d'enviament
        self.metodepagament = metodepagament                            # mètode de pagament

# ------------------------------------------------------------------

# amb la petició de compra i la resposta d'informació de l'usuari creem el model
def processar_peticio_final(compra: PeticioCompra, resposta_info: InformacioUsuari) -> ComandaModel:
    return ComandaModel(
        userid=compra.userid,
        llista_productes=compra.llista_productes,
        adreça=resposta_info.adreça,
        prioritat=resposta_info.prioritat,
        metodepagament=resposta_info.metodepagament
    )

# validar que la comanda sigui correcte
def validar_comanda(comanda: ComandaModel) -> bool:
    if not comanda.llista_productes:
        return False
    if not comanda.adreça or not comanda.adreça.strip():
        return False
    if comanda.prioritat not in [1, 2]:
        return False
    if not comanda.metodepagament or not comanda.metodepagament.strip():
        return False
    return True
