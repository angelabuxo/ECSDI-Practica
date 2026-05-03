Vull que revisis l'estat actual del projecte AgentZon com si fossis un assessor tècnic de la pràctica d'ECSDI. Abans de proposar o fer canvis, llegeix aquests fitxers:

- @Enunciat.pdf, especialment la secció "3.3 Tareas básicas" i la part de "Segunda Fase".
- @LabDoc.pdf, especialment les seccions sobre Flask, requests, rdflib, RDF/OWL, Turtle, SPARQL, SPARQLWrapper i agents d'exemple amb FIPA-ACL/Directory Service.
- @README.md per entendre com s'executa el projecte ara mateix.
- @JavierBejar/ com a carpeta de referència del professor (estructura, exemples d'agents i patrons de comunicació).
- @AgentZon/ontologia/AgentZonOntology.rdf i @AgentZon/data/productes.ttl per veure ontologia i dades.
- Els agents i protocols actuals dins @AgentZon/agents/ i @AgentZon/protocols/.
- @AgentZon/DISTRIBUTED_RUN.md per validar el desplegament distribuït i l'ordre d'arrencada dels agents.
- @AgentZon/Entrega-2.md on s'explica què necessitem per aquesta entrega.

Objectiu de la revisió:

Comprova si el codi que estem desenvolupant continua alineat amb el que demana la Segona Fase de l'enunciat:

1. Disseny i ús d'una ontologia compartida entre agents/serveis.
2. Representació de l'estat dels serveis, accions/comunicacions i contingut dels missatges.
3. Implementació dels serveis que permeten buscar productes segons restriccions.
4. Implementació progressiva dels serveis que permeten fer comandes de productes venuts directament per la botiga, des de la petició fins a l'enviament, excloent el pagament.
5. Documentació clara de l'ontologia i del disseny detallat del que s'ha implementat.
6. Comprova que, dins del que s'ha fet, no es viola cap de les coses que penalitzen (esmentades a continuació)

Penaliztacions:

La práctica se puede implementar de muchas maneras, incluyendo soluciones no distribuidas (o apenas), comuni-
cación directa mediante llamadas API o sin usar la ontología en las comunicaciones o internamente, por lo tanto las siguientes implementaciones penalizarán en la nota:
- No implementar agentes externos para los agentes de transporte, haciendo que los agentes logísticos hagan las labores de los transportistas
- Implementar los agentes como una simple API REST, sin usar los conceptos definidos en la ontología para las
acciones que los agentes realizan o los conceptos que intercambian
- No aprovechar que se trabaja con un sistema distribuido y hacer soluciones secuenciales cuando se puede trabajar
en paralelo
- El día de la demostración, no ejecutarla de manera realmente distribuida (todo en un único PC)


Context actual del projecte:

- La carpeta @JavierBejar/ s'utilitza com a plantilla de referència per contrastar arquitectura, protocols i estil d'implementació.
- Volem refactoritzar @AgentZon/ perquè s'alineï amb les restriccions de la pràctica i la Segona Fase, mantenint simplicitat i coherència.
- L'Agent Cercador està a @AgentZon/agents/agent_cercador.py.
- La interfície web del Cercador és @AgentZon/web/templates/cercador.html i els estils són @AgentZon/web/static/style.css.
- La cerca carrega l'ontologia RDF/XML i el catàleg Turtle amb rdflib.
- Encara no hem implementat completament comunicació FIPA-ACL, DirectoryAgent ni agents separats per ports, però el LabDoc i FiberZone poden servir com a referència per quan calgui avançar cap a multiagent real.
- El següent agent important serà @AgentZon/agents/agent_compra.py, que haurà d'alinear-se amb @AgentZon/protocols/compra.py i amb el disseny Prometheus documentat.

Quan revisis el projecte, respon en català i estructura la resposta així:

1. "Estat actual": què està ben encaminat i quines peces ja compleixen l'enunciat.
2. "Riscos o desviacions": coses que poden penalitzar o allunyar-nos del que demanen.
3. "Canvis recomanats ara": només canvis concrets i prioritzats que tinguin sentit en aquest moment.
4. "No fer encara": coses que serien massa avançades o innecessàries ara mateix.
5. "Següent pas proposat": una acció clara per continuar.

Important:

- No facis refactors grans si no són necessaris.
- Prioritza simplicitat, coherència amb l'ontologia i alineació amb la Segona Fase.
- Si proposes usar Flask, RDF, Turtle, SPARQL o FIPA-ACL, explica per què aporta valor en aquesta fase.
- Si detectes que un canvi trenca el disseny Prometheus o el flux documentat, avisa abans de tocar codi.
- Mantén separada la lògica dels agents, els protocols de missatge i les interfícies HTML.
- Revisa que els noms dels fitxers siguin clars pensant en futurs agents, per exemple Cercador i Compra.
