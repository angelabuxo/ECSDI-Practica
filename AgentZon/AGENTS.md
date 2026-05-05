Vull que revisis l'estat actual del projecte AgentZon com si fossis un assessor tècnic de la pràctica d'ECSDI. Abans de proposar o fer canvis, llegeix aquests fitxers:

- @Enunciat.pdf, especialment la secció "3.3 Tareas básicas" i la part de "Segunda Fase".
- @REFERENCE/ com a carpeta de referència del professor (estructura, exemples d'agents i patrons de comunicació). És important utilitzar les mateixes eines (Flask, requests, rdflib, RDF/OWL, Turtle, SPARQL, SPARQLWrapper i agents d'exemple amb FIPA-ACL/Directory Service)
- @AgentZon/ontologia/AgentZonOntology.rdf i @AgentZon/data/productes.ttl per veure ontologia i dades.
- @AgentZon/Entrega-3.md on s'explica la implementació per escrit del nostre sistema.

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



Important:

- No facis refactors grans si no són necessaris.
- Prioritza simplicitat, coherència amb l'ontologia i alineació amb la Segona Fase.
- Si proposes usar Flask, RDF, Turtle, SPARQL o FIPA-ACL, explica per què aporta valor en aquesta fase.
- Si detectes que un canvi trenca el disseny Prometheus o el flux documentat, avisa abans de tocar codi.
- Mantén separada la lògica dels agents, els protocols de missatge i les interfícies HTML.
- Revisa que els noms dels fitxers siguin clars pensant en futurs agents, per exemple Cercador i Compra.
