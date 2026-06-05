# Historial Comanda Unificat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistir l'snapshot de cada `Comanda` només a `historial_compres.ttl`, mantenir `seguiment_enviaments.ttl` a `Ag. Compra`, i llegir els detalls de comanda des d'`Ag. Opinador` quan es consulta `/orders/<id>`.

**Architecture:** `Ag. Compra` continuarà orquestrant compra i seguiment logístic, però deixarà d'escriure `comandes.ttl`. `Ag. Opinador` guardarà nodes `Comanda` complets dins `historial_compres.ttl` i exposarà una consulta ACL per recuperar-los. La pàgina `/orders/<id>` combinarà el snapshot retornat per `Opinador` amb el seguiment local.

**Tech Stack:** Flask, rdflib, RDF/OWL AZON, FIPA-ACL sobre HTTP, unittest

---

### Task 1: Fixar el nou contracte amb tests

**Files:**
- Modify: `tests/test_order_graphs.py`
- Modify: `tests/test_opinador_flow.py`
- Modify: `tests/test_purchase_flow.py`

- [ ] Verificar que `historial_compres.ttl` desa només nodes `Comanda`.
- [ ] Afegir test de consulta ACL de comanda a `Ag. Opinador`.
- [ ] Adaptar el test de `/orders/<id>` perquè no depengui de `comandes.ttl`.

### Task 2: Persistència de Comanda a historial_compres.ttl

**Files:**
- Modify: `services/history_service.py`
- Modify: `services/order_service.py`
- Modify: `protocols/compra.py`
- Modify: `agents/agent_opinador.py`

- [ ] Fer que `record_purchase` persisteixi el snapshot complet de `Comanda`.
- [ ] Fer que `parse_peticio_registre_compra` conservi tots els atributs necessaris.
- [ ] Mantenir els consumidors d'historial (feedback, recomanacions, devolucions) compatibles amb el nou format.

### Task 3: Consulta remota de comanda des de Compra

**Files:**
- Modify: `ontologia/AgentZonOntology.rdf`
- Modify: `protocols/opinador.py`
- Modify: `agents/agent_opinador.py`
- Modify: `agents/agent_compra.py`

- [ ] Afegir una acció AZON per demanar una comanda per `order_id`.
- [ ] Implementar builder/parser del missatge ACL.
- [ ] Fer que `Ag. Compra` consulti `Ag. Opinador` per construir `/orders/<id>`.

### Task 4: Neteja runtime i documentació

**Files:**
- Modify: `services/bootstrap.py`
- Modify: `docs/Justificacions/GUIA_NOU_INTEGRANT.md`
- Modify: `AgentZon-Documentació.md`
- Modify: `docs/AgentZon/AgentZon-Documentació.md`

- [ ] Treure `comandes.ttl` del bootstrap/runtime documentat.
- [ ] Reflectir que el snapshot de `Comanda` viu a `historial_compres.ttl`.
- [ ] Reflectir que el seguiment viu continua a `seguiment_enviaments.ttl`.

### Task 5: Verificació

**Files:**
- Test: `tests/test_*.py`

- [ ] Executar proves enfocades durant el cicle TDD.
- [ ] Executar `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`.
- [ ] Revisar els fitxers editats i confirmar que no queda cap ús runtime de `comandes.ttl`.
