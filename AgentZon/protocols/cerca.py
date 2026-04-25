from typing import List, Optional
import uuid

# Aquest fitxer defineix els objectes que viatgen dins del protocol de cerca.

# Representa un producte tal com el Cercador el rep del catàleg i el retorna a
# la interfície o a altres agents.
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

# Resposta de l'Agent Cercador. Agrupa tots els productes trobats i manté l'id
# de la petició original per poder relacionar petició i resposta.
class ResultatCerca:
    def __init__(self, llista_productes: List[ProducteModel], id: str):

        self.llista_productes = llista_productes    # llista de ProductModel
        self.id = id                                # identificador únic
        self.total = len(llista_productes)          # comptador de resultats de la cerca

# nom que fa servir la interfície per mostrar resultats
MostrarCerca = ResultatCerca

# Petició de cerca per part de l'usuari. Tots els filtres són opcionals: si un
# camp ve buit, no limita la cerca.
# definició de la petició de cerca per part de l'usuari (no tinc clar si mirar q algo no sigui buit o nomes passar-vos les coses plenes)
class PeticioCerca:
    def __init__( self, id: Optional[str] = None, text: Optional[str] = "", categ: Optional[str] = None, marca: Optional[str] = None,
    preu_min: Optional[float] = None, preu_max: Optional[float] = None):

        self.id = id or str(uuid.uuid4()) # identificador de la peticio

        # Normalitzem text, categoria i marca a minúscules perquè les cerques no
        # depenguin de si l'usuari escriu "Sony", "sony" o "SONY".
        self.text = (text or "").strip().lower()   # text lliure (nom/descripcio)
        self.categ = categ.strip().lower() if categ else None
        self.marca = marca.strip().lower() if marca else None
        self.preu_min = preu_min          # preu minim
        self.preu_max = preu_max          # preu maxim

        # Invariant del protocol: un rang de preu no pot estar invertit.
        if self.preu_min is not None and self.preu_max is not None and self.preu_min > self.preu_max:
            raise ValueError("El preu mínim no pot ser més gran que el màxim.")
        
    def producte_compleix_filtres(self, p: ProducteModel) -> bool:
        """Comprova si un producte compleix tots els filtres de la petició."""
        # Text lliure: busquem coincidència parcial al nom o a la descripció.
        if self.text and not (self.text in p.nom.lower() or self.text in p.descr.lower()):
            return False
        
        # Filtres exactes per categoria i marca, ja normalitzats a minúscules.
        if self.categ and p.categ.lower() != self.categ:
            return False
            
        if self.marca and p.marca.lower() != self.marca:
            return False
            
        # Rang de preu opcional. Si només hi ha mínim o màxim, s'aplica només
        # aquell límit.
        if self.preu_min is not None and p.preu < self.preu_min:
            return False
        
        if self.preu_max is not None and p.preu > self.preu_max:
            return False
            
        return True
    
# -----------------------------------------------------------------

# funció que retorna els productes que compleixen les condicions
def cercar_en_base_de_dades(peticio: PeticioCerca, inventari_complet: List[ProducteModel]) -> ResultatCerca:
    resultats = [p for p in inventari_complet if peticio.producte_compleix_filtres(p)]
    return ResultatCerca(resultats, peticio.id)
