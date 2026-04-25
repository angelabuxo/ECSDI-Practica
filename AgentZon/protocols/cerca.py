from typing import List, Optional

# definició de producte per als missatges
class ProducteModel:
    def __init__(self, id: str, nom: str, preu: float, descr: str, categ: str, marca: str, pes: int):

        self.id = id                # identificador únic
        self.nom = nom              # nom comercial
        self.preu = preu            # valor numèric
        self.descr = descr          # descripció genèrica
        self.categ = categ          # categoria per filtrar
        self.marca = marca          # marca del producte
        self.pes = pes              # pes del producte
    
# ---------------------------------------------------------------------------------------

# definició del missatge de Cerca
class ResultatCerca:
    def __init__(self, llista_productes: List[ProducteModel], id: str):

        self.llista_productes = llista_productes    # llista de ProductModel
        self.id = id                                # identificador únic
        self.total = len(llista_productes)          # comptador de resultats de la cerca

# definició de la petició de cerca per part de l'usuari (no tinc clar si mirar q algo no sigui buit o nomes passar-vos les coses plenes)
class PeticioCerca:
    def __init__( self, id: Optional[str], text: Optional[str] = "", categ: Optional[str] = None, marca: Optional[str] = None,
    preu_min: Optional[float] = None, preu_max: Optional[float] = None):

        self.id = id                      # identificador de la peticio
        self.text = text.strip()          # text lliure (nom/descripcio)
        self.categ = categ                # filtre per categoria
        self.marca = marca                # filtre per marca
        self.preu_min = preu_min          # preu minim
        self.preu_max = preu_max          # preu maxim

        if self.preu_min and self.preu_max and self.preu_min > self.preu_max:
            raise ValueError("El preu mínim no pot ser més gran que el màxim.")
        
    # comprova que un producte compleixi les condicions de la cerca de l'usuari
    def producte_compleix_filtres(self, p: ProducteModel) -> bool:
        if self.text and not (self.text in p.nom.lower() or self.text in p.descr.lower()):
            return False
        
        if self.categ and p.categ != self.categ:
            return False
            
        if self.marca and p.marca != self.marca:
            return False
            
        if self.preu_min is not None and p.preu < self.preu_min:
            return False
        
        if self.preu_max is not None and p.preu > self.preu_max:
            return False
            
        return True
    
# -----------------------------------------------------------------

# func que retorna els productes que compleixen es condicions
def cercar_en_base_de_dades(peticio: PeticioCerca, inventari_complet: List[ProducteModel]) -> ResultatCerca:
    resultats = [p for p in inventari_complet if peticio.producte_compleix_filtres(p)]
    return ResultatCerca(resultats, peticio.id)
        if (
            self.preu_min is not None
            and self.preu_max is not None
            and self.preu_min > self.preu_max
        ):
            raise ValueError("El preu mínim no pot ser mes gran que el preu màxim.")
