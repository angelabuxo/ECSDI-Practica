from typing import List, Optional

# definició de producte per als missatges. hem d defnit
class ProducteModel:
    def __init__(self, id: str, nom: str, preu: float, descr: str):
        self.id = id                # identificador únic
        self.nom = nom              # nom comercial
        self.preu = preu            # valor numèric
        self.descr = descr          # descripció genèrica

# definició del missatge de Cerca
class MostrarCerca:
    def __init__(self, llista_productes: List[ProducteModel], id: str):
        self.llista_productes = llista_productes # llista de ProductModel
        self.id = id                 # identificador únic
        self.total = len(llista_productes)       # comptador de resultats de la cerca