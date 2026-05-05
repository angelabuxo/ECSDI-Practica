# AgentZon Phase 2 Prototype

This prototype implements the Phase 2 subset requested in the course statement:

- product search with restrictions
- simple internal orders
- one logistics center
- two explicit external transport agents
- no payment workflow
- no external-vendor fulfillment
- no returns
- no recommendation/feedback loop beyond minimal purchase-history registration

## Structure

- `AgentZon/AgentUtil/`: local reference-inspired utilities based on the professor examples
- `AgentZon/protocols/`: RDF/FIPA-ACL message builders and parsers
- `AgentZon/services/`: RDF-backed catalog, order, history, and logistics services
- `AgentZon/agents/`: Flask agents with one method per implemented Prometheus plan
- `AgentZon/data/`: seeded Turtle data and persisted runtime state
- `AgentZon/ontologia/AgentZonOntology.rdf`: minimal Phase 2 shared ontology

## Implemented plan methods

- `Agent Cercador`
  - `pla_de_cerca`
  - `pla_de_presentacio`

- `Agent Compra`
  - `pla_demanar_informacio_usuari`
  - `pla_registrar_dades_d_usuari`
  - `pla_producte_als_nostres_magatzems`
  - `pla_informar_usuari_sobre_l_enviament`
  - `pla_delegar_registre_compra`
  - `pla_enviament_extern` as dormant placeholder

- `Agent Centre Logístic`
  - `pla_assignar_producte_a_lot`
  - `pla_cerca_de_transportista`
  - `pla_de_transportista_escollit`
  - `pla_producte_sha_enviat` as dormant placeholder

- `Agent Opinador`
  - minimal `pla_registre_de_compra` for purchase-history persistence

## Ontology documentation commands

Generate W3C-style ontology HTML with `pylode`:

```bash
./AgentZon/.venv/bin/python -m pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html
```

Generate the ontology graph with `owl2plot` from `owl2else`:

```bash
owl2plot AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology_graph
```

These commands are documentation helpers only. The runtime does not depend on them.
