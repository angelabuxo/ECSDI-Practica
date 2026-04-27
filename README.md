# AgentZon

AgentZon és el prototip de la pràctica d'ECSDI: una plataforma distribuïda multiagent per gestionar processos d'una empresa de comerç electrònic. El projecte parteix del disseny Prometheus i implementa agents que es comuniquen amb missatges i comparteixen una ontologia comuna.

Ara mateix la implementació està centrada en l'Agent Cercador, que permet buscar productes dins d'un catàleg RDF/Turtle.

## Estructura

```text
ECSDI-Practica/
├── README.md
├── requirements.txt
├── Entrega-1/
├── Entrega-2/
├── Entrega-3/
└── AgentZon/
    ├── config.py                    # Rutes i namespace compartits
    ├── agents/
    │   └── agent_cercador.py        # Agent Cercador i interfície web
    ├── protocols/
    │   ├── cerca.py                 # Missatges/model del protocol de cerca
    │   └── compra.py                # Models del protocol de compra
    ├── data/
    │   └── productes.ttl            # Catàleg de productes en Turtle
    ├── ontologia/
    │   ├── AgentZonOntology.rdf     # Ontologia compartida en RDF/XML
    │   └── docs/                    # Sortides generades (HTML/graf), ignorades a git
    └── web/
        ├── templates/
        │   └── cercador.html        # Interfície web de l'Agent Cercador
        └── static/
            └── style.css            # Estils de la interfície
```

## Requisits

- Python 3.10 o superior (recomanat Python 3.11 o 3.12 per compatibilitat amb eines d'ontologies).
- Dependències base de `requirements.txt`:
  - `Flask`
  - `rdflib`

Per generar la documentació i el graf de l'ontologia també cal:

- `pylode` (documentació HTML de l'ontologia).
- Graphviz del sistema (`dot`, `unflatten`) per renderitzar el graf.

## Instal·lació

### 1) Entorn virtual i dependències base

Des de l'arrel del repositori:

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

#### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### 2) Eines d'ontologia (HTML + graf)

Amb l'entorn virtual actiu:

```bash
python -m pip install "pylode==3.3.4"
```

> Nota: en alguns entorns `pylode` modern pot fallar. La versió `3.3.4` s'ha validat en aquest projecte.

### 3) Instal·lar Graphviz (binaris de sistema)

#### macOS (Homebrew)

```bash
brew install graphviz
```

Si Homebrew dona error de permisos a `/opt/homebrew`, cal reparar permisos i tornar a provar:

```bash
sudo chown -R $(whoami) /opt/homebrew /opt/homebrew/*
chmod u+w /opt/homebrew /opt/homebrew/*
brew install graphviz
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y graphviz
```

#### Fedora/RHEL

```bash
sudo dnf install -y graphviz
```

#### Windows

Instal·leu Graphviz des de la web oficial i afegiu el directori `bin` al `PATH`:

- [https://graphviz.org/download/](https://graphviz.org/download/)

Verificació:

```bash
dot -V
unflatten -V
```

Si no surten versions, Graphviz no està al `PATH`.

## Executar la interfície web de cerca

Des de l'arrel del repositori:

```bash
python3 AgentZon/agents/agent_cercador.py
```

Després obriu el navegador a:

```text
http://127.0.0.1:9001
```

La pàgina HTML mostra un formulari simple. Quan l'usuari envia la cerca, el mateix Agent Cercador rep els camps del formulari, crea una `PeticioCerca`, executa la cerca i torna a renderitzar la mateixa pàgina amb els resultats. No s'utilitza JSON ni una API REST separada.

## Provar només la lògica

També es pot provar la lògica directament:

```bash
python3 -c "from AgentZon.agents.agent_cercador import AgentCercador; from AgentZon.protocols.cerca import PeticioCerca; r = AgentCercador().processar_cerca(PeticioCerca(text='portatil')); print(r.total)"
```

## Ontologia i dades

`AgentZon/ontologia/AgentZonOntology.rdf` defineix el vocabulari compartit pels agents: classes, accions, respostes i propietats.

`AgentZon/data/productes.ttl` conté les dades concretes del catàleg. Està en format Turtle perquè és més llegible i fàcil de versionar que RDF/XML.

### Generar documentació HTML de l'ontologia

Des de l'arrel del repositori, amb l'entorn virtual actiu:

#### macOS/Linux

```bash
mkdir -p AgentZon/ontologia/docs
pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html
```

#### Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force AgentZon/ontologia/docs | Out-Null
pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html
```

Obrir resultat:

- macOS: `open AgentZon/ontologia/docs/ontology.html`
- Linux: `xdg-open AgentZon/ontologia/docs/ontology.html`
- Windows: `start AgentZon/ontologia/docs/ontology.html`

### Generar graf de l'ontologia

Des de l'arrel del repositori, amb l'entorn virtual actiu:

#### macOS/Linux

```bash
python -m rdflib.tools.rdf2dot AgentZon/ontologia/AgentZonOntology.rdf > AgentZon/ontologia/docs/ontology_graph.dot
dot -Tpng AgentZon/ontologia/docs/ontology_graph.dot -o AgentZon/ontologia/docs/ontology_graph.png
```

#### Windows (PowerShell)

```powershell
python -m rdflib.tools.rdf2dot AgentZon/ontologia/AgentZonOntology.rdf > AgentZon/ontologia/docs/ontology_graph.dot
dot -Tpng AgentZon/ontologia/docs/ontology_graph.dot -o AgentZon/ontologia/docs/ontology_graph.png
```

### Generar-ho tot en una sola comanda (HTML + graf)

Des de l'arrel del repositori, amb l'entorn virtual actiu:

#### macOS/Linux

```bash
mkdir -p AgentZon/ontologia/docs && pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html && python -m rdflib.tools.rdf2dot AgentZon/ontologia/AgentZonOntology.rdf > AgentZon/ontologia/docs/ontology_graph.dot && dot -Tpng AgentZon/ontologia/docs/ontology_graph.dot -o AgentZon/ontologia/docs/ontology_graph.png
```

#### Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force AgentZon/ontologia/docs | Out-Null; pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html; python -m rdflib.tools.rdf2dot AgentZon/ontologia/AgentZonOntology.rdf > AgentZon/ontologia/docs/ontology_graph.dot; dot -Tpng AgentZon/ontologia/docs/ontology_graph.dot -o AgentZon/ontologia/docs/ontology_graph.png
```

Obrir resultat:

- macOS: `open AgentZon/ontologia/docs/ontology_graph.png`
- Linux: `xdg-open AgentZon/ontologia/docs/ontology_graph.png`
- Windows: `start AgentZon/ontologia/docs/ontology_graph.png`

### Problemes freqüents

- `bad interpreter .../Mobile: no such file or directory`: hi ha espais al path; executeu els scripts amb `python <ruta-script>` tal com es mostra al README.
- `ExecutableNotFound: unflatten`: falta Graphviz de sistema o no està al `PATH`.
- `owl2plot: command not found` o `No matching distribution found for owl2plot`: useu el flux `rdflib.tools.rdf2dot` + `dot` d'aquest README (no `owl2plot`).
- `pylode` falla en importar (`pyproject.toml`): reinstal·leu amb `python -m pip install --force-reinstall "pylode==3.3.4"`.
