# AGENTS.md — Guia per a la IA al projecte AgentZon

Aquest fitxer recull el **context i les normes que la IA ha de tenir en compte a CADA prompt**
d'aquest projecte. Llegeix-lo sencer abans de proposar o fer canvis. Si una petició entra en
conflicte amb aquestes normes, avisa-ho abans de tocar res.

---

## 0. Què és aquest projecte

AgentZon és un **sistema multiagent distribuït** (pràctica d'ECSDI) que simula una botiga tipus
Amazon: cerca de productes, comandes, logística multicentre, transport, opinions i pagaments. Cada
agent és un **servidor Flask independent** que es comunica amb els altres via **FIPA-ACL sobre
HTTP**, amb el contingut dels missatges representat en **RDF/OWL** segons una **ontologia
compartida**. Tot ha de seguir les eines i els patrons del professor (carpeta `REFERENCE/`).

---

## 1. Llegeix sempre aquests fitxers segons la tasca

- `@Enunciat.pdf` — seccions "3.3 Tareas básicas", "3.4 Niveles de desarrollo", "4.3 Tercera Fase",
  "4.4 Cuarta Fase". És el que defineix l'abast.
- `@REFERENCE/` — referència del professor. **És obligatori fer servir les mateixes eines i de la
  mateixa manera** que els seus exemples. Dins hi ha `ecsdiLab.md` / `ECSDILab.pdf` (el mateix
  document en dos formats) que expliquen com s'han d'utilitzar; segueix-lo.
- `@AgentZon/ontologia/AgentZonOntology.rdf` i `@AgentZon/data/*` — ontologia i dades.
- `@Entrega-3/Entrega3.md` — implementació escrita del sistema.
- `@AgentZon/Entrega-2/Diagrames-Entrega-2.pdf` — diagrames Prometheus de cada agent (plans i
  capacitats). **Els "plans" del codi (`pla_...`) mapegen 1:1 amb aquests diagrames.**
- `@AgentZon/docs/Justificacions/JUSTIFICACIO_EINES.md` i `@AgentZon/docs/Justificacions/GUIA_NOU_ESTUDIANT.md` — guia d'onboarding i
  justificació de cada eina amb referències al laboratori. Mantén-los coherents si canvies coses.

---

## 2. Arquitectura i capes (respecta la separació)

```
AgentZon/
├── agents/        # Un fitxer per agent. Servidor Flask + dispatch de plans. NO lògica de negoci pesada.
├── protocols/     # build_*/parse_*/extract_* : converteixen dades <-> grafs RDF (contingut dels missatges).
├── services/      # Lògica de negoci i persistència (.ttl). Sense saber res d'HTTP ni d'ACL.
├── AgentUtil/     # Infraestructura del professor (ACL, ACLMessages, DSO, Agent, FlaskServer...). NO tocar.
├── ontologia/     # AgentZonOntology.rdf (vocabulari AZON compartit).
├── data/          # Fitxers Turtle (.ttl) amb les dades.
├── web/templates/ # HTML de les interfícies /iface.
├── config.py      # Configuració compartida, ports, build_agent, register_with_directory, serve_agent.
└── tests/         # unittest. S'han de mantenir verds.
```

**Regla d'or:** mantén separades les tres capes — **agents** (comunicació + tria de pla),
**protocols** (serialització RDF dels missatges) i **services** (negoci + dades). Les interfícies
HTML van a `web/templates/`. No barregis lògica de negoci dins d'un `@app.route`.

### Anatomia d'un agent (tots segueixen la mateixa plantilla)
1. Imports → `app = Flask(__name__)` + logger.
2. Globals (`AGENT`, `DirectoryAgent`, rutes de dades, `mss_cnt` com als exemples del professor).
3. `configure_runtime(settings, message_sender=send_message)` — omple les globals. **Existeix
   separat de `if __name__` perquè els tests puguin muntar l'agent sense xarxa real. No ho trenquis.**
4. Plans (`pla_...`) — la lògica, un per capacitat del diagrama Prometheus.
5. `@app.route("/comm")` + `comunicacion()` — patró SimpleInfoAgent: `gm`/`msgdic`/`gr`, `print INFO`,
   `mss_cnt += 1` al final; tria el pla segons `RDF.type`.
6. `@app.route("/iface")` → `browser_iface()` (només alguns) i `@app.route("/Stop")`.
7. `if __name__ == "__main__":` → `serve_agent(...)` (vegeu §5, concurrència).

---

## 3. Com es comuniquen els agents (no et desviïs d'això)

- **Embolcall FIPA-ACL** construït amb `AgentUtil.ACLMessages.build_message` i llegit amb
  `get_message_properties`. `ACL` s'importa com a `ClosedNamespace`.
- **Enviament**: `send_message(graf, adreça)` serialitza a RDF/XML i fa `requests.get(adreça,
  params={"content": ...})`; la resposta es torna a convertir en graf. **No facis crides HTTP
  "directes" amb JSON ni inventis un protocol propi.**
- **Contingut**: sempre amb conceptes de l'ontologia (`AZON`), no strings/JSON arbitraris.
- **Descoberta**: via l'**agent Directory** (l'únic punt fix). Registre/cerca amb `DSO.Register` /
  `DSO.Search` i `FOAF.Agent`/`FOAF.name`. Cap agent ha de tenir "cablejada" l'adreça d'un altre
  (excepte la del Directory, i els transportistes que el centre rep per arguments).
- **Protocol**: `request` → si no s'entén `not-understood`; registre → `confirm`; resultat →
  `inform`. Respecta-ho.

---

## 4. Eines: només les del laboratori, i com toca

| Sí (i com) | Capítol `ecsdiLab.md` |
|---|---|
| **Flask** amb `@app.route` i `app.run(host, port)` | 3.2 |
| **requests** amb `requests.get(url, params=...)` | 3.3 |
| **rdflib**: `Graph`, `Namespace`, `add`, `value`, `parse`, `serialize` | 4.2 |
| **SPARQL local** amb `graph.query("""PREFIX… SELECT…""")` | 4.2.4 |
| **FIPA-ACL** com a `ClosedNamespace` (`build_message`/`get_message_properties`) | 6.1 |
| **DSO + FOAF** per al Directory | 6.1 |
| **multiprocessing** (`Process` + `Queue` + `join`) via `serve_agent` | 2 i 6 |
| **ThreadPoolExecutor** per al paral·lelisme intern d'un agent | 2.1 |

**NO facis servir** (i per què): cap framework web alternatiu; cap llibreria HTTP que no sigui
`requests`; **SPARQLWrapper** només seria per a *endpoints* SPARQL remots (no en tenim, treballem
amb `.ttl` locals); **flask-restful** és opcional i els exemples no el fan servir. No afegeixis
dependències noves sense justificar-ho amb el laboratori.

---

## 5. Concurrència i distribució

- Cada agent arrenca amb `config.serve_agent(app, hostname, port, register_fn=...)`, que replica el
  patró dels exemples: llança un `multiprocessing.Process` (l'`agentbehavior1` del professor) que
  fa el **registre al Directory** i espera en una `Queue`, mentre `app.run` corre en paral·lel; en
  aturar diposita un `0` a la cua i fa `join`.
- Aprofita el sistema distribuït: **evita solucions seqüencials quan es pot paral·lelitzar**
  (p. ex. l'Agent Compra envia en paral·lel logística/banc/historial amb `ThreadPoolExecutor`).

---

## 6. Ontologia (`AgentZonOntology.rdf`) — regles dures

- Espai de noms `AZON` (`http://www.semanticweb.org/agentzon#`). Si cal un concepte nou, afegeix-hi
  la **classe/propietat/relació** corresponent (no inventis termes només al codi).
- **NO afegeixis `rdfs:comment`** a l'ontologia: hi ha un test (`test_ontology_alignment.py`) que
  ho prohibeix. Documenta a `Entrega3.md` o als fitxers de guia, no dins de l'OWL.
- Propietats han d'estar **ben acotades** al seu domini. No facis classes que es especialitzin en
  una sola subclasse (feedback del professor sobre `Producte`).
- Els **pagaments tenen sentit/direcció** (`SentitPagament`: COBRAMENT vs PAGAMENT) — mantén-ho.
- Després de tocar l'ontologia, executa els tests d'alineació.

---

## 7. Idioma i noms (consistència)

- **Català**: domini, noms de plans (`pla_...`), interfícies HTML i comentaris nous.
- **Anglès**: identificadors tècnics, funcions de serveis, noms de fitxers (`catalog_service`,
  `shipping_service`...).
- **Codi de `AgentUtil/` (del professor)**: deixa'l com està (castellà/anglès), no el reescriguis.
- Noms de fitxers d'agent clars i orientats al rol: `agent_cercador.py`, `agent_compra.py`, etc.
- **No reanomenis els plans** a noms genèrics: el professor compara el codi amb els diagrames
  Prometheus.

---

## 8. Penalitzacions (NO incórrer-hi mai)

> La práctica se puede implementar de muchas maneras, incluyendo soluciones no distribuidas (o
> apenas), comunicación directa mediante llamadas API o sin usar la ontología en las
> comunicaciones o internamente, por lo tanto las siguientes implementaciones penalizarán en la
> nota:
> - No implementar agentes externos para los agentes de transporte, haciendo que los agentes
>   logísticos hagan las labores de los transportistas.
> - Implementar los agentes como una simple API REST, sin usar los conceptos definidos en la
>   ontología para las acciones que los agentes realizan o los conceptos que intercambian.
> - No aprovechar que se trabaja con un sistema distribuido y hacer soluciones secuenciales cuando
>   se puede trabajar en paralelo.
> - El día de la demostración, no ejecutarla de manera realmente distribuida (todo en un único PC).

---

## 9. Feedback del professor (2a entrega) i estat

> **Ontologia:** "No hagáis clases que se especialicen solo en una clase como habéis hecho en
> producto." → tenir-ho en compte en qualsevol canvi a l'ontologia.
> **Recomanacions:** n'hi ha prou amb un avís de recepció del missatge.
> **Pagaments:** "los pagos van en dos direcciones, a veces se cobra y a veces se paga, no sé si
> los podéis distinguir." → resolt amb `SentitPagament` (COBRAMENT / PAGAMENT). Mantén-ho coherent.
> **Implementació:** correcta; Asumo que las entradas extra de la API rest que teneis en alguno de los agentes es para hacer pruebas y poder ver que hacen los agentes.

---

## 10. Flux de treball per a cada canvi

1. **No facis refactors grans si no són necessaris.** Prioritza simplicitat, coherència amb
   l'ontologia i alineació amb la Tercera/Quarta Fase.
2. Si un canvi **trenca el disseny Prometheus o el flux documentat**, avisa ABANS de tocar codi.
3. Si proposes usar Flask/RDF/Turtle/SPARQL/FIPA-ACL/multiprocessing, **explica per què aporta
   valor** en aquesta fase (i lliga-ho al laboratori).
4. **Tests**: després de qualsevol canvi de codi, executa la suite sencera des de `AgentZon/`:
   ```bash
   .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
   ```
   Han de passar **tots** (actualment 32). Si n'afegeixes lògica nova, afegeix-hi tests si escau.
   Nota: la ruta del projecte té accents (`Pràctica`); fes servir sempre `cd "..."` amb cometes.
5. **Lints**: revisa els fitxers editats abans d'acabar.
6. Mantén `GUIA_NOU_INTEGRANT.md` i `JUSTIFICACIO_EINES.md` coherents amb els canvis que facis.
7. **Git**: NO facis commit ni push si l'usuari no ho demana explícitament. `.cursor/` és estat
   local de l'editor; no el versionis si no t'ho demanen.

---

## 11. Checklist abans de donar una tasca per acabada

- [ ] El canvi fa servir conceptes de l'ontologia a les comunicacions (no JSON/strings arbitraris).
- [ ] No s'ha introduït cap eina/llibreria fora del que permet el laboratori.
- [ ] Es respecta la separació agents / protocols / services / templates.
- [ ] Si he tocat l'ontologia: cap `rdfs:comment`, propietats acotades, tests d'alineació verds.
- [ ] Els transportistes segueixen sent agents externs; res ha esdevingut una "simple API REST".
- [ ] La suite de tests passa sencera i he revisat els lints.
- [ ] He avisat de qualsevol cosa que trenqui el disseny documentat o els diagrames Prometheus.
