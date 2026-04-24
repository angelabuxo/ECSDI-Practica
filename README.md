# AgentZon

> Plataforma distribuïda multiagent per a la gestió de processos de comerç electrònic.

AgentZon és el prototip desenvolupat per a la pràctica de l'assignatura **ECSDI** (Enginyeria del Coneixement i Sistemes Distribuïts Intel·ligents) del Grau en Enginyeria Informàtica de la **UPC - FIB**, curs 2025/2026 Q2.

El sistema modela una empresa global de comerç electrònic (tipus Amazon) com un conjunt d'agents autònoms que col·laboren mitjançant una ontologia compartida i protocols de comunicació basats en missatges, seguint la metodologia **Prometheus**.

## Context de la pràctica

L'objectiu global és que un **agent assistent virtual** sigui capaç de fer compres en nom d'un usuari a partir d'un conjunt de restriccions (marca, rang de preu, termini d'entrega, valoració, venedor, etc.). L'assistent raona sobre els productes disponibles, presenta opcions a l'usuari, confirma la tria i, a partir d'aquí, gestiona tota la compra de manera automatitzada.

## Estructura del projecte

```
AgentZon/
├── main.py                     # Punt d'entrada del sistema
├── ontologia/
│   ├── AgentZonOntology.owl    # Ontologia principal (OWL)
│   └── documentation/          # Documentació autogenerada
│       ├── index.html          # Documentació W3C (pyLODE)
│       └── grafo.png           # Graf visual (owl2plot)
├── protocols/
│   ├── cerca.py                # Missatges del protocol de cerca
│   └── compra.py               # Missatges del protocol de compra
├── agents/
│   ├── agent_cercador.py       # Agent responsable de la cerca
│   └── agent_compra.py         # Agent responsable de la compra
└── utils/
    └── interface.py            # Utilitats d'interacció amb l'usuari
```

### Descripció dels mòduls

**`main.py`** — Punt d'entrada del sistema. Inicialitza l'entorn d'agents (el contenidor), crea les instàncies de cada agent (Cercador, Compra) i manté el sistema en execució.

**`ontologia/`** — El nucli del coneixement.
- `AgentZonOntology.owl`: jerarquia de classes (`Producte`, `Categoria`), propietats (`téPreu`, `téMarca`) i individus (els productes reals). És un model iteratiu que creix amb el sistema.
- `documentation/`: documentació tècnica autogenerada.
  - `index.html`: documentació en format W3C generada amb **pyLODE**.
  - `grafo.png`: representació visual de l'ontologia generada amb **owl2plot**.

**`protocols/`** — Defineix l'"idioma" i els "formularis" que fan servir els agents per parlar entre ells.
- `cerca.py`: estructura dels missatges de cerca. Inclou la classe `MostrarCerca`, que dicta quins camps rep l'usuari quan l'Agent Cercador retorna resultats.
- `compra.py`: estructura per a les transaccions. Inclou la classe `ConfirmarCompra`, que assegura que els missatges d'èxit o error de la comanda segueixin un format estàndard.

**`agents/`** — La lògica de comportament (els "cervells" del sistema).
- `agent_cercador.py`: implementa el *pla de cerca*. La seva responsabilitat és rebre peticions, fer consultes SPARQL o filtrats sobre l'ontologia i tornar els resultats.
- `agent_compra.py`: implementa la lògica de comanda. Verifica la disponibilitat del producte a l'ontologia i gestiona la confirmació de la comanda simple.

**`utils/`** — Funcions de suport.
- `interface.py`: utilitats per a la interacció amb l'usuari. Centralitza la manera d'imprimir les taules de productes i de demanar dades per consola, assegurant una estètica coherent a tots els agents.

## Requisits

- **Python 3.10+**
- Llibreries principals:
  - `rdflib` — manipulació de grafs RDF i consultes SPARQL.
  - `owlready2` — càrrega i raonament sobre ontologies OWL.
  - `pyLODE` — generació de documentació W3C de l'ontologia.
  - `owl2else` — generació del graf visual de l'ontologia.

## Instal·lació

```bash
git clone <url-del-repositori>
cd ECSDI-Practica/AgentZon

python3 -m venv .venv
source .venv/bin/activate
```

De moment el repositori encara no té un `requirements.txt`. Les dependències s'instal·len manualment segons el que necessiti cada mòdul, per exemple:

```bash
pip install rdflib owlready2 pylode
```

## Execució

Des de l'arrel de `AgentZon/`:

```bash
python main.py
```

Això inicialitza el contenidor d'agents i engega els agents Cercador i Compra, que queden a l'espera de peticions per part de l'usuari.

### Regenerar la documentació de l'ontologia

```bash
pylode ontologia/AgentZonOntology.owl -o ontologia/documentation/index.html
owl2plot ontologia/AgentZonOntology.owl -o ontologia/documentation/grafo.png
```

## Tecnologies

- **Python 3** com a llenguatge d'implementació.
- **OWL / RDF / SPARQL** per a la representació i consulta del coneixement.
- **Prometheus Design Tool (PDT)** per al disseny del sistema multiagent.
- **Protégé** per a l'edició de l'ontologia.
- **pyLODE** i **owl2plot** per a la documentació de l'ontologia.
