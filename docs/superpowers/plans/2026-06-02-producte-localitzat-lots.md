# ProducteLocalitzat Lot Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace reservation/order-centric lot storage with lot-centric `Lot` records that persist one `ProducteLocalitzat` per purchased product, while keeping `Ag Compra` able to reconcile shipping updates to orders and `Ag Cobrador` able to charge shipped products without `IdComanda` in the lot files.

**Architecture:** `Ag Compra` mints an opaque `ProducteLocalitzat` identifier per purchased product and keeps the local mapping from that item to the order in its own tracking store. `Agent Centre Logístic` persists those same `ProducteLocalitzat` nodes under `Lot` via `SobreLot`, emits `DadesEnviament` and `ConfirmacioEnviament` that reference the same item identities, and sends one internal charge request per shipped item with a prorated transport share based on product weight. `Ag Compra` aggregates item-level shipping updates back into order-level status and UI groups.

**Tech Stack:** Python, Flask, rdflib/OWL/Turtle, unittest, FIPA-ACL over HTTP

---

## Locked decisions

- No `IdComanda` in `AgentZon/data/lots-CL-*.ttl`.
- No direct `Lot -> TeProducte` manifest in the lot files.
- One `ProducteLocalitzat` node per purchased product instance in a lot.
- `Ag Compra` mints opaque localized-product ids. Do not encode the order id in the URI.
- `Centre -> Cobrador` sends one `PeticioCobramentIntern` per shipped `ProducteLocalitzat`.
- Transport cost sharing is per product: `product.weight / lot.total_weight`.
- `DadesEnviament` and `ConfirmacioEnviament` must carry the `ProducteLocalitzat` identity so `Ag Compra` can recover the owning order from its tracking store.
- `Ag Compra` remains the only agent that needs order-level correlation. The logistics side becomes order-agnostic.

## Target lot shape

```ttl
@prefix azon: <http://www.semanticweb.org/agentzon#> .

azon:lot-LOT-123 a azon:Lot ;
    azon:IdLot "LOT-123" ;
    azon:Estat "ASSIGNAT" ;
    azon:Ciutat "Girona" ;
    azon:DataEntrega "2026-06-06" ;
    azon:DataEntregaDefinitiva "2026-06-04" ;
    azon:PesTotal "4.50"^^xsd:float ;
    azon:IdCentreLogistic "CL-GI" ;
    azon:IdTransportista "economy" ;
    azon:NomTransportista "Transportista-economy" ;
    azon:CostTransport "18.40"^^xsd:float .

azon:ploc-9a13e6 a azon:ProducteLocalitzat ;
    azon:SobreLot azon:lot-LOT-123 ;
    azon:TeProducte azon:product-P1011 ;
    azon:IdUsuari "127.0.0.1" ;
    azon:Ciutat "Girona" ;
    azon:DataEntrega "2026-06-06" .

azon:ploc-7bc2aa a azon:ProducteLocalitzat ;
    azon:SobreLot azon:lot-LOT-123 ;
    azon:TeProducte azon:product-P1017 ;
    azon:IdUsuari "192.168.1.12" ;
    azon:Ciutat "Girona" ;
    azon:DataEntrega "2026-06-06" .
```

## File map

**Ontology and docs**

- Modify: `AgentZon/ontologia/AgentZonOntology.rdf`
- Modify: `Entrega-3/Entrega3.md`
- Modify: `AgentZon/docs/Justificacions/GUIA_NOU_INTEGRANT.md`
- Modify: `AgentZon/docs/Justificacions/JUSTIFICACIO_EINES.md`

**Compra <-> Centre protocols**

- Modify: `AgentZon/protocols/centre_logistic.py`
- Modify: `AgentZon/services/shipping_service.py`
- Modify: `AgentZon/protocols/compra.py`
- Modify: `AgentZon/agents/agent_compra.py`

**Lot persistence and centre behavior**

- Modify: `AgentZon/services/logistics_service.py`
- Modify: `AgentZon/agents/agent_centre_logistic.py`

**Tracking and payment**

- Modify: `AgentZon/services/shipping_tracking_service.py`
- Modify: `AgentZon/protocols/pagament.py`
- Modify: `AgentZon/agents/agent_cobrador.py`

**Tests**

- Modify: `AgentZon/tests/test_ontology_alignment.py`
- Modify: `AgentZon/tests/test_order_graphs.py`
- Modify: `AgentZon/tests/test_logistics_flow.py`
- Modify: `AgentZon/tests/test_purchase_flow.py`

## Task 1: Update ontology meaning and documentation

**Files:**
- Modify: `AgentZon/ontologia/AgentZonOntology.rdf`
- Modify: `Entrega-3/Entrega3.md`
- Modify: `AgentZon/docs/Justificacions/GUIA_NOU_INTEGRANT.md`
- Modify: `AgentZon/docs/Justificacions/JUSTIFICACIO_EINES.md`
- Test: `AgentZon/tests/test_ontology_alignment.py`

- [ ] **Step 1: Write the failing ontology test for `ProducteLocalitzat -> SobreLot`**

```python
def test_sobre_lot_accepts_producte_localitzat(self):
    self.assertIn(
        ("http://www.semanticweb.org/agentzon#SobreLot",
         "http://www.semanticweb.org/agentzon#ProducteLocalitzat"),
        self.object_property_domains()
    )
```

- [ ] **Step 2: Run the ontology test and confirm it fails**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_ontology_alignment -v
```

Expected: one failure asserting that `ProducteLocalitzat` is not yet a domain of `SobreLot`.

- [ ] **Step 3: Update the ontology and docs**

Add `ProducteLocalitzat` as a domain of `SobreLot` and revise the docs so `ProducteLocalitzat` is described as both:

- the action sent by `Ag Compra` to the centre, and
- the persistent per-product lot item reused across the shipping lifecycle

Keep the change minimal. Do not add `rdfs:comment`.

- [ ] **Step 4: Re-run the ontology test**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_ontology_alignment -v
```

Expected: PASS.

## Task 2: Make `Ag Compra` mint stable `ProducteLocalitzat` items

**Files:**
- Modify: `AgentZon/protocols/centre_logistic.py`
- Modify: `AgentZon/services/shipping_service.py`
- Modify: `AgentZon/protocols/compra.py`
- Modify: `AgentZon/agents/agent_compra.py`
- Test: `AgentZon/tests/test_order_graphs.py`

- [ ] **Step 1: Write the failing protocol test for item identity**

```python
def test_build_productes_localitzats_uses_opaque_localized_product_id(self):
    localized = {
        "localized_product_id": "ploc-9a13e6",
        "user_id": "127.0.0.1",
        "city": "Girona",
        "delivery_date": "2026-06-06",
        "product": {"product_id": "P1011", "name": "X", "weight": 1.5},
        "centre": {"centre_id": "CL-GI", "centre_city": "Girona"},
    }
    graph, parsed = build_and_parse_roundtrip(localized)
    assert parsed["localized_product_id"] == "ploc-9a13e6"
    assert parsed["user_id"] == "127.0.0.1"
    assert parsed["product"]["product_id"] == "P1011"
```

- [ ] **Step 2: Run the protocol test and confirm it fails**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_order_graphs -v
```

Expected: FAIL because the current protocol still assumes order-grouped localization data.

- [ ] **Step 3: Refactor the Compra-side localization flow**

Implement these changes:

- `Ag Compra` builds one opaque `localized_product_id` per purchased product.
- `collect_warehouse_reservations()` dispatches one `ProducteLocalitzat` request per product.
- `build_productes_localitzats()` and `parse_productes_localitzats()` carry:
  - `localized_product_id`
  - `IdUsuari`
  - `Ciutat`
  - `DataEntrega`
  - exactly one `TeProducte`
  - optional centre metadata
- remove the requirement that the centre protocol depends on `IdComanda`

Use an item dict shaped like this:

```python
{
    "localized_product_id": "ploc-9a13e6",
    "user_id": "127.0.0.1",
    "city": "Girona",
    "delivery_date": "2026-06-06",
    "product": {"product_id": "P1011", "name": "X", "weight": 1.5},
    "centre_id": "CL-GI",
    "centre_city": "Girona",
}
```

- [ ] **Step 4: Re-run the protocol test**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_order_graphs -v
```

Expected: PASS.

## Task 3: Replace reservation nodes with persisted `ProducteLocalitzat` lot items

**Files:**
- Modify: `AgentZon/services/logistics_service.py`
- Modify: `AgentZon/protocols/centre_logistic.py`
- Modify: `AgentZon/agents/agent_centre_logistic.py`
- Test: `AgentZon/tests/test_logistics_flow.py`

- [ ] **Step 1: Write the failing logistics test for the new TTL shape**

```python
def test_create_lot_persists_producte_localitzat_items_not_reservations(self):
    lot = create_lot(...one_localized_product...)
    graph = load_graph(self.lots_path)
    self.assertEqual(0, len(list(graph.subjects(RDF.type, AZON.ConfirmacioLocalitzacio))))
    items = list(graph.subjects(RDF.type, AZON.ProducteLocalitzat))
    self.assertEqual(1, len(items))
    self.assertEqual(AZON["lot-" + lot["lot_id"]], graph.value(items[0], AZON.SobreLot))
```

- [ ] **Step 2: Run the logistics test and confirm it fails**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_logistics_flow -v
```

Expected: FAIL because the current implementation still creates `ConfirmacioLocalitzacio` reservation nodes.

- [ ] **Step 3: Refactor lot persistence**

Implement these changes in `services/logistics_service.py`:

- `create_lot()` accepts one localized-product item instead of an `(order_id, products[])` reservation batch
- the lot file stores:
  - one `Lot`
  - one `ProducteLocalitzat` subject per purchased product
- remove `_reservation_node_for()`, `_reservation_nodes_for_lot()`, and reservation-centric extraction
- replace `reservations` with `items` in extracted lot dictionaries
- compute `lot["products"]` as a derived convenience list from `items`, not as persistent RDF edges from the lot

Each extracted item should look like:

```python
{
    "localized_product_id": "ploc-9a13e6",
    "user_id": "127.0.0.1",
    "product": {"product_id": "P1011", "name": "X", "weight": 1.5},
    "city": "Girona",
    "delivery_date": "2026-06-06",
}
```

- [ ] **Step 4: Re-run the logistics test**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_logistics_flow -v
```

Expected: PASS.

## Task 4: Make shipping updates item-centric and let `Ag Compra` map items back to orders

**Files:**
- Modify: `AgentZon/services/shipping_tracking_service.py`
- Modify: `AgentZon/protocols/centre_logistic.py`
- Modify: `AgentZon/protocols/compra.py`
- Modify: `AgentZon/agents/agent_compra.py`
- Test: `AgentZon/tests/test_purchase_flow.py`

- [ ] **Step 1: Write the failing purchase-flow test for item-based reconciliation**

```python
def test_process_shipping_update_resolves_order_from_localized_product_id(self):
    save_localization_confirmations(self.tracking_path, [{
        "localized_product_id": "ploc-9a13e6",
        "order_id": "ORDER-1234",
        "lot_id": "LOT-123",
        "user_id": "127.0.0.1",
        "product": {"product_id": "P1011", "name": "X", "weight": 1.5},
    }])
    process_shipping_update(message_graph_with_ploc_9a13e6, content, sender)
    order = load_order(self.orders_path, "ORDER-1234")
    self.assertEqual("ASSIGNAT", order["status"])
```

- [ ] **Step 2: Run the purchase-flow test and confirm it fails**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_purchase_flow -v
```

Expected: FAIL because shipping updates are still correlated through `IdComanda`.

- [ ] **Step 3: Refactor tracking and shipping messages**

Implement these changes:

- `save_localization_confirmations()` stores both:
  - the `localized_product_id`
  - the owning `order_id`
- tracking nodes are keyed by `localized_product_id`, not `(order_id, lot_id)`
- `DadesEnviament` and `ConfirmacioEnviament` include the `ProducteLocalitzat` nodes they refer to
- `extract_shipping_details_list()` returns item-centric entries with `localized_product_id`
- `process_shipping_update()` looks up the touched order ids from the tracking store instead of trusting centre-side `IdComanda`
- `group_shipments_for_display()` and `aggregate_order_status()` keep grouping by `(centre_id, lot_id)` for the UI even though storage is item-based

Use item-centric shipment payloads shaped like:

```python
{
    "localized_product_id": "ploc-9a13e6",
    "lot_id": "LOT-123",
    "status": "ASSIGNAT",
    "transport_id": "economy",
    "transport_name": "Transportista-economy",
    "city": "Girona",
    "delivery_date": "2026-06-04",
    "price": 6.13,
    "centre_id": "CL-GI",
    "centre_city": "Girona",
    "product": {"product_id": "P1011", "name": "X", "weight": 1.5},
}
```

- [ ] **Step 4: Re-run the purchase-flow test**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_purchase_flow -v
```

Expected: PASS.

## Task 5: Send one internal charge request per shipped item

**Files:**
- Modify: `AgentZon/services/logistics_service.py`
- Modify: `AgentZon/agents/agent_centre_logistic.py`
- Modify: `AgentZon/protocols/pagament.py`
- Modify: `AgentZon/agents/agent_cobrador.py`
- Test: `AgentZon/tests/test_logistics_flow.py`
- Test: `AgentZon/tests/test_purchase_flow.py`

- [ ] **Step 1: Write the failing test for per-item charging**

```python
def test_mark_shipped_triggers_one_charge_per_localized_product(self):
    lot = load_lot_by_id(self.lots_path, "LOT-123")
    confirmations = process_ready_lot("LOT-123")
    self.assertEqual(
        {"ploc-9a13e6", "ploc-7bc2aa"},
        {call["localized_product_id"] for call in self.sent_internal_charge_requests}
    )
```

- [ ] **Step 2: Run the affected tests and confirm they fail**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_logistics_flow tests.test_purchase_flow -v
```

Expected: FAIL because the current implementation still builds one shipment per reservation/user batch.

- [ ] **Step 3: Refactor charging to per-item requests**

Implement these changes:

- replace reservation-level shipment builders with item-level shipment builders
- compute item transport share with:

```python
item_transport_cost = round(
    lot_transport_price * item_weight / total_lot_weight,
    2,
)
```

- send one `PeticioCobramentIntern` per shipped item
- each payment request must include:
  - `localized_product_id`
  - `lot_id`
  - `user_id`
  - `product_id`
  - `transport_cost`
- `Ag Cobrador` keeps recording one payment per request and returns one invoice per shipped item
- `Agent Centre Logístic` forwards that invoice back to `Ag Compra` inside the matching `ConfirmacioEnviament`

Do not reintroduce `IdComanda` into the centre-side lot model.

- [ ] **Step 4: Re-run the charging tests**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest tests.test_logistics_flow tests.test_purchase_flow -v
```

Expected: PASS.

## Task 6: Regression pass, sample data verification, and docs sync

**Files:**
- Modify: `Entrega-3/Entrega3.md`
- Modify: `AgentZon/docs/Justificacions/GUIA_NOU_INTEGRANT.md`
- Modify: `AgentZon/docs/Justificacions/JUSTIFICACIO_EINES.md`
- Verify: `AgentZon/data/lots-CL-GI.ttl`
- Verify: `AgentZon/data/lots-CL-BCN.ttl`
- Verify: `AgentZon/data/lots-CL-TGN.ttl`

- [ ] **Step 1: Regenerate or rewrite fixture expectations**

Check that the sample lot files now show:

- one `Lot` subject per lot
- one `ProducteLocalitzat` subject per purchased product
- no `ConfirmacioLocalitzacio` reservation subjects persisted in the lot files
- no `IdComanda` in the lot files

- [ ] **Step 2: Run the full test suite**

Run:

```bash
cd "/Users/polmontanera/Desktop/Q6 2526/ECSDI/ECSDI-Practica/AgentZon" && .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Expected: all tests PASS.

- [ ] **Step 3: Review edited files for consistency**

Verify:

- `Entrega3.md` matches the item-centric lot design
- onboarding docs explain that `Ag Compra` owns the order mapping
- payment docs explain that internal charging is per `ProducteLocalitzat`
- no new libraries were introduced

- [ ] **Step 4: Do not commit unless the user explicitly asks**

Project rule:

```text
Git: NO facis commit ni push si l'usuari no ho demana explícitament.
```

## Self-review checklist

- The plan removes `IdComanda` only from logistics storage and centre-side coordination, not from Compra-owned order tracking.
- The plan keeps the system distributed and ontology-driven.
- The plan preserves the current separation: agents for ACL/dispatch, protocols for RDF messages, services for persistence/business logic.
- The plan keeps transportists as external agents.
- The plan selects the simpler charging option requested by the user: one internal charge per product.
- The plan includes the transport-cost propagation work instead of deferring it.
