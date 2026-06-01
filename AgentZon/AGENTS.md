Vull que revisis l'estat actual del projecte AgentZon com si fossis un assessor tècnic de la pràctica d'ECSDI. Abans de proposar o fer canvis, llegeix aquests fitxers:

- @Enunciat.pdf, especialment la secció "3.3 Tareas básicas" i "3.4 Niveles de desarrollo" i la part de "4.3 Tercera Fase" i "4.4 Cuarta Fase".
- @REFERENCE/ com a carpeta de referència del professor (estructura, exemples d'agents i patrons de comunicació). És important utilitzar les mateixes eines (Flask, requests, rdflib, RDF/OWL, Turtle, SPARQL, SPARQLWrapper i agents d'exemple amb FIPA-ACL/Directory Service). Trobaràs també els fitxers ECSDILab.pdf i ecsdiLab.md, son el mateix però en diferents formats i expliquen com has d'utilitzar aquestes eines, has de seguir el que es demana.
- @AgentZon/ontologia/AgentZonOntology.rdf i @AgentZon/data/* per veure ontologia i dades.
- @AgentZon/Entrega-3/Entrega3.md on s'explica la implementació per escrit del nostre sistema.
- @AgentZon/Entrega-2/Diagrames-Entrega-2.pd on pots consultar els diagrames de cada agent amb els seu splans i capacitats.

# Objectiu de la revisió:

## Comprova si el codi que estem desenvolupant continua alineat amb el que demana la Tercera i Cuarta Fase de l'enunciat:

1. Disseny i ús d'una ontologia compartida entre agents/serveis.
2. Representació de l'estat dels serveis, accions/comunicacions i contingut dels missatges.
3. Implementació dels serveis que permeten buscar productes segons restriccions.
4. Implementació progressiva dels serveis que permeten fer comandes de productes venuts directament per la botiga, des de la petició fins a l'enviament, excloent el pagament.
5. Documentació clara de l'ontologia i del disseny detallat del que s'ha implementat.
6. Comprova que, dins del que s'ha fet, no es viola cap de les coses que penalitzen (esmentades a continuació)

# Penaliztacions:

La práctica se puede implementar de muchas maneras, incluyendo soluciones no distribuidas (o apenas), comunicación directa mediante llamadas API o sin usar la ontología en las comunicaciones o internamente, por lo tanto las siguientes implementaciones penalizarán en la nota:
- No implementar agentes externos para los agentes de transporte, haciendo que los agentes logísticos hagan las labores de los transportistas
- Implementar los agentes como una simple API REST, sin usar los conceptos definidos en la ontología para las acciones que los agentes realizan o los conceptos que intercambian
- No aprovechar que se trabaja con un sistema distribuido y hacer soluciones secuenciales cuando se puede trabajar en paralelo
- El día de la demostración, no ejecutarla de manera realmente distribuida (todo en un único PC)



# Important:

- No facis refactors grans si no són necessaris.
- Prioritza simplicitat, coherència amb l'ontologia i alineació amb la Tercera Fase.
- Si proposes usar Flask, RDF, Turtle, SPARQL o FIPA-ACL, explica per què aporta valor en aquesta fase.
- Si detectes que un canvi trenca el disseny Prometheus o el flux documentat, avisa abans de tocar codi.
- Mantén separada la lògica dels agents, els protocols de missatge i les interfícies HTML.
- Revisa que els noms dels fitxers siguin clars pensant en futurs agents, per exemple Cercador i Compra.
- Si consideres que cal fer canvis a l'ontologia, no oblidis afegir-hi els conceptes, relacions i atributs necessaris.

### Tingues en compte també, el feedback que ens va donar el professor respecte al codi que li vam entregar fa unes setmanes i assegura't que el que va demanar corregir està aplicat:

Correcciones a la segunda entrega
---------------------------------

Ontologia
=========

La ontologia me parece bien.

No hagais clases que se especialicen solo en una clase como habeis hecho
en producto.

Las recomendaciones realmente no tienen una respuesta, depende de como 
implementeis el protocolo de recomendacion, pero simplemente con 
un aviso de recepcion de mensaje deberia ser suficiente.

No tengo claro como representais los pagos, fijaos que los pagos van en 
dos direcciones, a veces se cobra y a veces se paga, no se si los
podeis distinguir.

Implementacion
==============

Lo que llevais implementado me parece bien.

Asumo que las entradas extra de la API rest que teneis en alguno de los
agente es para hacer pruebas y poder ver que hacen los agentes.
