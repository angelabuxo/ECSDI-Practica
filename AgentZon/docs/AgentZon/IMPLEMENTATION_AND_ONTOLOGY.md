# AgentZon Implementation and Ontology Notes

## Scope

The current codebase implements the Phase 2 core: product search, purchase capture for internally managed products, logistics negotiation through explicit transport agents, and purchase-history registration. The ontology has been expanded beyond that slice so the shared vocabulary also covers payments, returns, feedback, recommendations, and external sellers.

## Ontology Design

### Main hierarchies

- `Actor`
- `Usuari`, `VenedorExtern`, `Transportista`, `Banc`
- `Comunicacio`
- `Accio` and `Resposta`

`Actor` keeps only external entities. AgentZon's runtime agents (`AgentCercador`, `AgentCompra`, `AgentCentreLogistic`, `AgentOpinador`, etc.) are deployment artifacts, not ontology classes — they communicate using `acl:sender` and `acl:receiver` on the FIPA-ACL envelope.

### Implemented communication concepts

- `PeticioCerca` and `ResultatCerca`
- `PeticioRegistreCompra` and `ConfirmacioRegistreCompra`
- `ProducteLocalitzat`
- `PeticioTransport` and `RespostaOfertaTransport`

### Future-ready communication concepts

- `PeticioPagament` and `ConfirmacioPagament`
- `PeticioDevolucio` and `ResolucioDevolucio`
- `PeticioFeedback` and `RespostaFeedback`
- `PeticioRecomanacio` and `RespostaRecomanacio`
- `AltaProducteExtern` and `ConfirmacioAltaProducteExtern`

### Core domain concepts

- `Producte`, `ProducteExtern`
- `Comanda`
- `Lot`
- `CentreLogistic`
- `Pagament`, `Devolucio`, `Feedback`, `Recomanacio`

`DadesEnviamentUsuari`, `DadesBancaries`, `HistorialCompra`, `HistorialCerca`, and `UbicacionsProductes` are persisted data sources, not ontology classes.

### Key object properties

- `MostraProducte`: links a search result to the returned products
- `TeProducte`: reused by `Comanda`, `Lot`, `PeticioRegistreCompra`, and `ProducteLocalitzat`
- `SobreComanda`, `SobreLot`, `SobreProducte`: keep messages tied to the domain entities they affect
- `EsRespostaA`: ties a `Resposta` to the originating `Accio`
- `UbicatACentre`, `AssignatATransportista`, `TeFeedback`, `GeneraRecomanacio`: model logistics and post-sale processes

`acl:sender` and `acl:receiver` belong to the FIPA-ACL envelope and are not AgentZon ontology relations. `TeProducte`, `SobreComanda`, `SobreLot`, and `UbicatACentre` are the canonical runtime relations. `PesTotal` belongs to `Lot` and `PeticioTransport`; `Pes` stays on `Producte`.

### Key datatype properties

- Product attributes: `IdProducte`, `Nom`, `Descripcio`, `Categoria`, `Marca`, `Preu`, `Pes`, `SkuExtern`
- Order and logistics attributes: `IdComanda`, `IdLot`, `IdCentreLogistic`, `Prioritat`, `Ciutat`, `Carrer`, `DataEntrega`, `CostTransport`, `NomTransportista`, `PesTotal`
- Search attributes: `TextConsulta`, `CategoriaConsulta`, `MarcaConsulta`, `PreuMinim`, `PreuMaxim`, `TotalResultats`
- Future process attributes: `IdPagament`, `IdDevolucio`, `ImportPagament`, `Estat`, `MotiuDevolucio`, `Puntuacio`, `Comentari`, `Acceptada`, `RequereixLogisticaExterna`

## Implemented Agents

### 1. Directory Agent

The directory agent stores registrations and resolves agent types to addresses. It is the coordination entrypoint used by the other runtime agents before any domain message exchange happens.

### 2. Agent Cercador

The search agent receives browser searches and RDF `PeticioCerca` messages. It queries the local RDF catalog, records search history, and returns `ResultatCerca` resources with full product descriptions.

### 3. Agent Compra

The purchase agent receives the user’s selected products, collects shipping data, persists the order, asks the opinion agent to register the purchase, and delegates shipping preparation to the logistics center.

### 4. Agent Centre Logístic

The logistics agent converts a purchase into a `Lot`, asks both transport agents in parallel for offers, chooses the best offer, and answers with the selected shipping details.

### 5. Agent Opinador

The opinion agent currently implements the minimal Phase 2 responsibility: it receives `PeticioRegistreCompra` and persists purchase history. The ontology leaves room for its future feedback and recommendation responsibilities.

### 6. Agent Transportista

The transport agent is instantiated twice, once for the `fast` profile and once for the `economy` profile. Each instance receives `PeticioTransport` and replies with `RespostaOfertaTransport` using different cost and delivery parameters.

## Communication Between Agents

### Search flow

1. The user submits a browser form to `Agent Cercador`.
2. `Agent Cercador` converts the filters into a `PeticioCerca`-shaped internal record.
3. The catalog service returns matching `Producte` resources.
4. The result page is rendered and linked to `Agent Compra`, resolved through the directory service.

### Purchase and history flow

1. The user confirms a product selection with `Agent Compra`.
2. `Agent Compra` stores shipping data and creates a `Comanda`.
3. `Agent Compra` resolves `Agent Opinador` through the directory agent.
4. A `PeticioRegistreCompra` message is sent to `Agent Opinador`.
5. `Agent Opinador` writes a purchase-history record and returns `ConfirmacioRegistreCompra`.

### Logistics negotiation flow

1. `Agent Compra` sends `ProducteLocalitzat` to `Agent Centre Logístic`.
2. `Agent Centre Logístic` materializes a `Lot`.
3. It sends one `PeticioTransport` to each transport agent.
4. Both `RespostaOfertaTransport` replies are collected concurrently.
5. The logistics agent selects the cheapest valid offer and returns the final shipping summary to `Agent Compra`.

### Interaction with external actors

- `Transportista` is the only external actor implemented in code during this phase, and it remains explicit and distributed as required by the statement.
- `Usuari`, `VenedorExtern`, and `Banc` are fully modeled in the ontology even where the executable flow is still pending.
- The ontology also reserves the communication structure required for future external-seller onboarding, payment authorization, return management, and feedback/recommendation loops.

## Code/Ontology Mapping

- `AgentZon/protocols/cerca.py` maps to `PeticioCerca`, `ResultatCerca`, and `Producte`
- `AgentZon/protocols/compra.py` maps to `PeticioRegistreCompra` and `ConfirmacioRegistreCompra`
- `AgentZon/protocols/centre_logistic.py` maps to `ProducteLocalitzat`, `PeticioTransport`, and `RespostaOfertaTransport`
- `AgentZon/services/order_service.py` maps to `Comanda` and persisted shipping data
- `AgentZon/services/logistics_service.py` maps to `Lot`
- `AgentZon/services/history_service.py` maps purchase-history and search-history persistence to the message/domain vocabulary

## Refactor Notes

- The agent entrypoints now share centralized runtime helpers for host resolution, directory-agent creation, and registration.
- The `agent_*.py` modules already follow a function-based structure, so no redundant per-agent classes were reintroduced.
- All Python modules under `AgentZon/` now contain explicit file headers, and `AgentUtil` keeps the original `@author: javier` annotation.
