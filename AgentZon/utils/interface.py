from protocols.cerca import MostrarCerca, PeticioCerca
from protocols.compra import PeticioInfoUsuari, InformacioUsuari, PeticioCompra
from typing import Optional
import uuid

# ------------- cerca -----------------------------------------

def demanar_cerca_usuari() -> PeticioCerca:
    print("\n--- Cercador de productes ---")
    text = input("Què busques? (nom/descripció): ")
    categ = input("Categoria (opcional): ")
    marca = input("Marca (opcional): ")
    
    p_min = input("Preu mínim (opcional): ")
    p_max = input("Preu màxim (opcional): ")
    
    p_min = float(p_min) if p_min else None
    p_max = float(p_max) if p_max else None
    
    return PeticioCerca(
        id=str(uuid.uuid4()), 
        text=text, 
        categ=categ if categ else None, 
        marca=marca if marca else None,
        preu_min=p_min,
        preu_max=p_max
    )

def mostrar_resultats_cerca(answ: MostrarCerca):
    print(f"\n Resultats de la cerca ID: {answ.id}")
    print(f"S'han trobat {answ.total} productes:")

    if answ.total == 0:
        print("No s'han trobat productes")
    else:
        for p in answ.llista_productes:
            print(f"[{p.id}] {p.nom.upper()}")
            print(f"Preu: {p.preu}€")
            print(f"Descripció: {p.descr}")

# ------------- compra -----------------------------------------
def demanar_seleccio_compra(userid: str, llista_mostrada: list) -> Optional[PeticioCompra]:

    print("\n--- Finalitzar compra ---")
    ids_input = input("Escriu els IDs dels productes que vols comprar (separats per coma): ")
    llista_ids = [i.strip() for i in ids_input.split(",")]
    
    seleccionats = [p for p in llista_mostrada if p.id in llista_ids]
    
    if not seleccionats:
        print("No has seleccionat cap producte vàlid.")
        return None
        
    return PeticioCompra(userid=userid, llista_productes=seleccionats)

def demanar_dades_enviament(peticio: PeticioInfoUsuari) -> Optional[InformacioUsuari]:

    print(f"\n--- Formulari de compra per a l'usuari: {peticio.userid} ---")
    print(f"L'agent necessita: {', '.join(peticio.camps_requerits)}")
    
    adreça = input("Introdueix l'adreça d'enviament: ").strip()
    if not adreça:
        print("L'adreça d'enviament no pot ser buida.")
        return None
    
    try:
        prioritat = int(input("Prioritat (1:Express, 2:Normal): "))
        if prioritat not in [1, 2]:
            print("La prioritat ha de ser 1 (Express) o 2 (Normal).")
            return None
    except ValueError:
        print("La prioritat ha de ser un número.")
        return None
    
    metodepagament = input("Mètode de pagament: ").strip()
    if not metodepagament:
        print("El mètode de pagament no pot ser buit.")
        return None
    
    return InformacioUsuari(peticio.userid, adreça, prioritat, metodepagament)
