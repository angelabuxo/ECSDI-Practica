# AgentZon Implementation and Ontology Notes

## Scope

The current codebase implements the Phase 2 core: product search, purchase capture for internally managed products, logistics negotiation through explicit transport agents, and purchase-history registration. The ontology has been expanded beyond that slice so the shared vocabulary also covers payments, returns, feedback, recommendations, and external sellers.

## Ontology Design

### Main hierarchies

- `Actor`
- `Usuari`, `VenedorExtern`, `Transportista`, `ProveidorPagament`
- `Comunicacio`
- `Accio` and `Resposta`

The ontology no longer models internal agents as domain concepts. Agents are the consumers of the ontology, while sender/receiver/performative metadata is carried by the FIPA-ACL envelope.

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
- `DadesEnviamentUsuari`
- `DadesBancaries`
- `HistorialCompra`, `HistorialCerca`
- `UbicacioProducte`
- `Pagament`, `Devolucio`, `Feedback`, `Recomanacio`

### Key object properties

- `MostraProducte`: links a search result or search-history record to returned products
- `TeProducte`: reused by orders, lots, purchase-history messages, and logistics messages
- `TeDadesEnviament`: links an order to shipping data
- `SobreComanda`, `SobreLot`, `SobreProducte`: keep messages and records tied to the domain entities they affect
- `UbicatACentre`, `AssignatATransportista`, `TeFeedback`, `GeneraRecomanacio`: model logistics and post-sale processes
- FIPA-ACL `sender`, `receiver`, `performative`, `content`, and `ontology` are used for communicative acts instead of duplicating those roles in the local ontology

### Key datatype properties

- Product attributes: `IdProducte`, `Nom`, `Descripcio`, `Categoria`, `Marca`, `Preu`, `Pes`, `SkuExtern`
- Order and logistics attributes: `IdComanda`, `IdLot`, `IdCentreLogistic`, `Prioritat`, `Ciutat`, `Carrer`, `DataEntrega`, `CostTransport`, `NomTransportista`
- Search attributes: `TeText`, `TeCategoria`, `TeMarca`, `PreuMinim`, `PreuMaxim`, `TotalResultats`
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

The opinion agent currently implements the minimal Phase 2 responsibility: it receives `PeticioRegistreCompra` and persists `HistorialCompra`. The ontology leaves room for its future feedback and recommendation responsibilities.

### 6. Agent Transportista

The transport agent is instantiated twice, once for the `fast` profile and once for the `economy` profile. Each instance receives `PeticioTransport` and replies with `RespostaOfertaTransport` using different cost and delivery parameters.

## Communication Between Agents

### Search flow

1. The user submits a browser form to `Agent Cercador`.
2. `Agent Cercador` converts the filters into a `PeticioCerca`-shaped internal record.
3. The catalog service returns matching `Producte` resources.
4. The RDF response is wrapped in a FIPA-ACL `inform` message with explicit `acl:ontology`.
5. The result page is rendered and linked to `Agent Compra`, resolved through the directory service.

### Purchase and history flow

1. The user confirms a product selection with `Agent Compra`.
2. `Agent Compra` stores `DadesEnviamentUsuari` and creates a `Comanda` linked through `TeDadesEnviament` and `TeProducte`.
3. `Agent Compra` resolves `Agent Opinador` through the directory agent.
4. A `PeticioRegistreCompra` FIPA-ACL `request` message is sent to `Agent Opinador` and points to the `Comanda` via `SobreComanda`.
5. `Agent Opinador` writes a `HistorialCompra` record and returns `ConfirmacioRegistreCompra`.

### Logistics negotiation flow

1. `Agent Compra` sends `ProducteLocalitzat` to `Agent Centre Logístic`.
2. `Agent Centre Logístic` materializes a `Lot` linked to both `Comanda` and `Producte`.
3. It sends one `PeticioTransport` to each transport agent, with the lot referenced through `SobreLot`.
4. Both `RespostaOfertaTransport` replies are collected concurrently.
5. The logistics agent selects the cheapest valid offer and returns the final shipping summary to `Agent Compra`, preserving the `Transportista` relation through `AssignatATransportista`.

### Interaction with external actors

- `Transportista` is the only external actor implemented in code during this phase, and it remains explicit and distributed as required by the statement.
- `Usuari`, `VenedorExtern`, and `ProveidorPagament` are fully modeled in the ontology even where the executable flow is still pending.
- The ontology also reserves the communication structure required for future external-seller onboarding, payment authorization, return management, and feedback/recommendation loops.

## Code/Ontology Mapping

- `AgentZon/protocols/cerca.py` maps to `PeticioCerca`, `ResultatCerca`, and `Producte`
- `AgentZon/protocols/compra.py` maps to `PeticioRegistreCompra` and `ConfirmacioRegistreCompra`
- `AgentZon/protocols/centre_logistic.py` maps to `ProducteLocalitzat`, `PeticioTransport`, and `RespostaOfertaTransport`
- `AgentZon/services/order_service.py` maps to `Comanda` and `DadesEnviamentUsuari`
- `AgentZon/services/logistics_service.py` maps to `Lot`
- `AgentZon/services/history_service.py` maps to `HistorialCompra` and search-history persistence derived from `PeticioCerca`

## Refactor Notes

- The agent entrypoints now share centralized runtime helpers for host resolution, directory-agent creation, and registration.
- The `agent_*.py` modules already follow a function-based structure, so no redundant per-agent classes were reintroduced.
- All Python modules under `AgentZon/` now contain explicit file headers, and `AgentUtil` keeps the original `@author: javier` annotation.
