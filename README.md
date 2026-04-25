# AgentZon

AgentZon és el prototip de la pràctica d'ECSDI: una plataforma distribuïda multiagent per gestionar processos d'una empresa de comerç electrònic. El projecte parteix del disseny Prometheus i implementa agents que es comuniquen amb missatges i comparteixen una ontologia comuna.

Ara mateix la implementació està centrada en l'Agent Cercador, que permet buscar productes dins d'un catàleg RDF/Turtle.

## Estructura

```text
AgentZon/
├── config.py                    # Rutes i namespace compartits pels agents
├── agents/
│   ├── agent_cercador.py        # Agent Cercador i interfície web
│   └── agent_compra.py          # Agent de compra, pendent d'implementar
├── data/
│   └── productes.ttl            # Catàleg de productes en Turtle
├── ontologia/
│   ├── AgentZonOntology.rdf     # Ontologia compartida en RDF/XML
│   └── documentation/           # Documentació generada de l'ontologia
├── protocols/
│   ├── cerca.py                 # Missatges del protocol de cerca
│   └── compra.py                # Missatges del protocol de compra
├── web/
│   ├── templates/
│   │   └── cercador.html        # Interfície web de l'Agent Cercador
│   └── static/
│       └── style.css            # Estils de la interfície
```

## Requisits

- Python 3.10 o superior.
- Dependències de `requirements.txt`:
  - `Flask`
  - `rdflib`

## Instal·lació

Des de l'arrel del repositori:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si no voleu crear entorn virtual, també es pot fer:

```bash
python3 -m pip install --user -r requirements.txt
```

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
