from protocols.cerca import MostrarCerca

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