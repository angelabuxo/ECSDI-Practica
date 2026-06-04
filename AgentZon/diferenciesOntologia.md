# Diferències entre el codi d'AgentZon i l'ontologia

**Referència:** `ontologia/AgentZonOntology.rdf` (espai de noms `http://www.semanticweb.org/agentzon#`, prefix `AZON` al codi).

**Abast analitzat:** `agents/`, `protocols/`, `services/`, `data/*.ttl`, `tests/` (només on aporta context).

**Data:** 4 de juny de 2026.

---

## 1. Resum executiu

| Categoria | Resultat |
|-----------|----------|
| Termes **inventats al codi** (fora de l'OWL) | **Cap** a `agents/`, `protocols/`, `services/` ni `data/` en ús de producció |
| Termes **només als tests** (legacy / comprovacions negatives) | 7 (`AgentIntern`, `AgentCercador`, `AgentCompra`, `emissor`, `receptor`, `teProducte`, `Compra` com a URI d'agent) |
| Termes **definits a l'ontologia però no usats** al codi de producció | 9 classes/propietats (vegeu §4) |
| **Violacions de domini** (propietat en classe no acotada a l'OWL) | Diverses a persistència i alguns missatges ACL (vegeu §5) |
| **Alineació general** | Les comunicacions ACL i la majoria de protocols fan servir classes i propietats de l'ontologia; les divergències principals són persistència local (`.ttl`) i alguns camps «de conveniència» no declarats a l'OWL |

El projecte **no penalitza** per usar JSON en ACL: el contingut és RDF amb vocabulari `AZON`. Les diferències rellevants són sobretot **dominis incomplets** a l'ontologia respecte al que ja escriu el codi, i **termes d'emmagatzematge** que reutilitzen propietats sense `rdf:type` de classe d'historial.

---

## 2. Metodologia

1. Càrrega de `AgentZonOntology.rdf` amb **rdflib** (classes `owl:Class`, propietats objecte i de dades, dominis `rdfs:domain`).
2. Extracció de referències `AZON.*` (Python) i `azon:*` (Turtle, només predicats amb inicial majúscula).
3. Comparació conjunts *ontologia* ↔ *codi + dades*.
4. Validació automàtica de dominis sobre els grafos de `data/*.ttl` i revisió manual de `protocols/` i `services/`.
5. Correlació amb `tests/test_ontology_alignment.py`, que ja documenta termes legacy i d'emmagatzematge intencionalment **fora** de l'OWL.

**Nota sobre subclasses:** en OWL, una instància de `ProducteExtern` (subclasse de `Producte`) **sí** pot portar propietats amb domini `Producte` (`Nom`, `Preu`, etc.). Les violacions de domini per `ProducteExtern` en aquest informe es limiten a propietats amb domini **només** `VenedorExtern` (p. ex. `IdVenedorExtern`).

---

## 3. Conceptes al codi que NO existeixen a l'ontologia

### 3.1 Codi de producció (`agents`, `protocols`, `services`, `data`)

**No s'ha detectat cap classe, propietat objecte ni propietat de dades nova** del namespace `agentzon#` en aquests directoris. Tot el vocabulari RDF de producció ve de l'ontologia compartida.

### 3.2 Tests i identificadors auxiliars

| Terme | On apareix | Interpretació |
|-------|------------|---------------|
| `AgentIntern`, `AgentCercador`, `AgentCompra` | `tests/test_ontology_alignment.py` | Termes **eliminats** de l'ontologia; el test comprova que no hi siguin |
| `emissor`, `receptor`, `teProducte` | Mateix test | Legacy eliminat |
| `DadesBancaries`, `DadesEnviamentUsuari`, `HistorialCerca`, `HistorialCompra`, `UbicacioProducte` | Mateix test (`test_storage_sources_are_not_ontology_classes`) | **No són classes OWL**; el codi reutilitza altres propietats sense tipar nodes d'historial (vegeu §6) |
| `Compra` | `tests/test_order_graphs.py` (`sender=AZON.Compra`) | URI d'**identitat d'agent** al missatge ACL, **no** definida com a classe a l'OWL (equivalent informal a un nom d'agent, no a un concepte de domini) |

### 3.3 Prefixos d'instància (no són conceptes de l'ontologia)

Els fitxers Turtle fan servir URIs com `azon:product-P1001`, `azon:order-ORDER-…`, `azon:centre-BCN`. El segment després del prefix és un **identificador d'instància**, no un terme nou de l'ontologia.

---

## 4. Conceptes a l'ontologia NO (o poc) usats al codi

### 4.1 Classes i propietats sense referència en producció

| Terme | Tipus | Comentari |
|-------|-------|-----------|
| `Actor` | Classe | Superclasse de `Usuari`, `Banc`, `Transportista`, `VenedorExtern`; no s'instancia directament |
| `Banc` | Classe | Modelat a l'OWL; el Cobrador no tipa nodes com a `Banc` |
| `Comunicacio` | Classe | Superclasse d'`Accio` / `Resposta`; no s'usa com a `rdf:type` |
| `Accio` | Classe | Superclasse de peticions; només jeràrquia OWL |
| `Resposta` | Classe | Superclasse de respostes; només jeràrquia OWL |
| `ProducteIntern` | Classe | Definida com a subclasse de `Producte`; el catàleg fa servir `Producte` o `ProducteExtern` (SPARQL inclou `ProducteIntern` però **0 instàncies** a `data/`) |
| `Retorna` | Propietat objecte | Domini `PeticioCerca`, rang `ResultatCerca`; el codi enllaça cerca amb **`EsRespostaA`** (`protocols/cerca.py`), no amb `Retorna` |
| `CostBaseKg` | Propietat de dades | Domini `Transportista`; els transportistes no persisteixen aquest valor (preus hardcoded als agents) |
| `IdBanc` | Propietat de dades | Domini `Banc`; sense ús al codi |

### 4.2 Classes d'acció/resposta usades als protocols però no al mapa `AZON.*:` dels agents

Això **no és una divergència semàntica**: són missatges **rebuts** o **construïts** als `protocols/`, mentre el dispatch per `rdf:type` només llista **peticions entrants** per agent. Exemples només a protocols/respostes: `ConfirmacioAltaProducteExtern`, `ConfirmacioLocalitzacio`, `ConfirmacioPagament`, `DadesEnviament`, `ResultatCerca`, `ResultatCompra`, `RespostaOfertaTransport`, `ResolucioDevolucio`, etc.

---

## 5. Propietats usades en classes (o nodes) fora del domini OWL

Aquí el codi **sí fa servir propietats de l'ontologia**, però en **tipus de subjecte** que l'OWL no té al `rdfs:domain`. Són les divergències més importants per alinear ontologia ↔ implementació.

### 5.1 Missatges ACL / protocols

| Subjecte (classe) | Propietat | Fitxers | Domini a l'OWL |
|-------------------|-----------|---------|----------------|
| `DadesEnviament` | `Estat` | `protocols/venedor_extern.py` | No inclou `DadesEnviament` (sí `Comanda`, `Lot`, `ResultatCompra`, …) |
| `PeticioEnviamentExtern` | `IdVenedorExtern` | `protocols/venedor_extern.py` | Només `VenedorExtern` |
| `PeticioEnviamentExtern` | `Carrer` | `protocols/venedor_extern.py` | Només `Comanda` |
| `ConfirmacioLocalitzacio` (dins `build_resultat_compra`) | `TeProducte` | `protocols/compra.py` | `Comanda`, `Lot`, `PeticioDevolucio`, `PeticioFeedback`, `ProducteLocalitzat` — **no** `ConfirmacioLocalitzacio` |

El test `test_shipping_details_response_is_modeled_as_a_response` confirma expressament que **`Estat` no ha de ser domini de `DadesEnviament`**; el codi del venedor extern el posa igualment (`Estat` = `DELEGAT`).

### 5.2 Persistència (`services/` + `data/`)

| Subjecte | Propietat | Fitxers | Domini a l'OWL |
|----------|-----------|---------|----------------|
| `Feedback` | `DataCompra`, `IdComanda`, `IdUsuari` | `services/history_service.py`, `data/feedback.ttl` | `DataCompra` → `Comanda`; `IdComanda` / `IdUsuari` → no inclouen `Feedback` |
| `Devolucio` | `IdComanda`, `IdUsuari`, `ImportPagament` | `services/payment_service.py` (`record_refund`), `data/devolucions.ttl` | Cap domini inclou `Devolucio` per aquestes propietats |
| `Devolucio` | `IdVenedorExtern` | `payment_service.py` (opcional) | Només `VenedorExtern` |
| `Pagament` | `IdUsuari` | `payment_service.py` | `IdUsuari` no té domini `Pagament` |
| `Pagament` | `IdVenedorExtern` | `payment_service.py` | Només `VenedorExtern` |
| `Usuari` (dades bancàries) | `MetodePagament` | `payment_service.py` (`save_user_bank_data`) | Domini: `Comanda`, `Pagament`, `PeticioCompra`, `PeticioPagament` — **no** `Usuari` |
| `ProducteExtern` | `IdVenedorExtern` | `catalog_service.py`, catàleg | Només `VenedorExtern` (no `Producte` / `ProducteExtern`) |

### 5.3 Historial de cerques/compres (nodes sense `rdf:type`)

`services/history_service.py` escriu a `historial_cerques.ttl` i `historial_compres.ttl` nodes **sense classe OWL** (p. ex. `azon:search-0`), però amb propietats de l'ontologia:

| Ús al graf d'historial | Propietats | Problema de domini |
|------------------------|------------|-------------------|
| Registre de cerca | `TextConsulta`, `CategoriaConsulta`, `MarcaConsulta`, `PreuMinim`, `PreuMaxim`, `IdUsuari`, `TotalResultats`, `MostraProducte` | Barreja camps de **`PeticioCerca`** i **`ResultatCerca`**; `IdUsuari` no és domini de `PeticioCerca`; `MostraProducte` / `TotalResultats` només per `ResultatCerca` |
| Registre de compra | `IdComanda`, `IdUsuari`, `DataCompra`, `SobreComanda`, `SobreProducte` | Sense tipus; dominis dispersos (molts pensats per `Comanda` o missatges, no per un node «historial») |

Això coincideix amb la decisió documentada als tests: **`HistorialCerca` / `HistorialCompra` no són classes** a l'OWL; el codi reutilitza propietats existents amb un model de persistència més lliure.

### 5.4 Nodes auxiliars sense tipus

| Fitxer / servei | Patró |
|-----------------|--------|
| `responsable_enviament_productes.ttl` / `external_vendor_service.py` | Nodes `azon:resp-{productId}` amb `IdProducte`, `IdVenedorExtern`, `RequereixLogisticaExterna` sense `rdf:type` |
| `ubicacions_productes.ttl` | Triples `Producte` → `UbicatACentre` (correcte); centres com a `azon:centre-BCN` sovint **sense** `rdf:type` `CentreLogistic` |

---

## 6. Relacions i atributs: ús coherent vs alternatives

| Ontologia | Ús al codi |
|-----------|------------|
| `EsRespostaA` | Enllaç genèric entre resposta i petició (`cerca`, `compra`, `pagament`, `centre_logistic`, `opinador`, …) |
| `Retorna` | Definida (`PeticioCerca` → `ResultatCerca`) però **no usada**; substituïda per `EsRespostaA` |
| `GeneraRecomanacio` | Usada a `protocols/opinador.py` (`RespostaRecomanacio` → node `Recomanacio`) — correcte; la propietat no té `rdfs:domain` declarat a l'OWL |
| `SentitPagament` | Usada a `protocols/pagament.py` i `payment_service.py` (`COBRAMENT` / `PAGAMENT`) — alineada amb el feedback del professor |
| `AssignatATransportista` | `logistics_service.py`, `centre_logistic.py` — alineada |
| `SobreLot` / `ProducteLocalitzat` | Test d'alineació i flux logístic — alineats |

---

## 7. Resum per capes

### 7.1 `protocols/` (missatges ACL)

- Vocabulari **100 % AZON** per a tipus de missatge i camps.
- Divergències principals: **`DadesEnviament.Estat`**, **`PeticioEnviamentExtern`** amb `IdVenedorExtern` / `Carrer`, i **`ConfirmacioLocalitzacio.TeProducte`** dins el resultat de compra.

### 7.2 `services/` (persistència `.ttl`)

- Reutilitza propietats OWL sense crear-ne de noves.
- Divergències: **`Feedback`**, **`Devolucio`**, **`Pagament`**, **`Usuari`** (banc), historials sense tipus, **`IdVenedorExtern`** en productes externs.

### 7.3 `agents/`

- Dispatch per `rdf:type` amb classes d'**acció** definides a l'ontologia (`PeticioCerca`, `PeticioCompra`, `PeticioTransport`, …).
- No introdueixen conceptes fora de l'OWL.

### 7.4 `data/`

- Catàleg i comandes en general **coherents** (`Producte`, `Comanda`, `Lot`, …).
- **`feedback.ttl`** i **`devolucions.ttl`** concentren les violacions de domini del §5.2.

---

## 8. Termes eliminats de l'ontologia (referència històrica)

El codi **no hauria de reintroduir** (i els tests ho prohibeixen):

- Classes d'agent intern: `AgentIntern`, `AgentCercador`, `AgentCompra`
- `emissor`, `receptor`, `teProducte` (substituït per `TeProducte` amb domini acotat)
- Classes d'emmagatzematge mai afegides a l'OWL: `HistorialCerca`, `HistorialCompra`, `DadesBancaries`, `DadesEnviamentUsuari`, `UbicacioProducte`

---

## 9. Recomanacions (si es vol alinear més l'ontologia i el codi)

1. **Ampliar dominis a l'OWL** (sense `rdfs:comment`) per als usos ja implementats:
   - `Feedback`: `IdComanda`, `IdUsuari`, `DataCompra` (o bé modelar enllaç `SobreComanda` i treure literals duplicats).
   - `Devolucio`: `IdComanda`, `IdUsuari`, `ImportPagament`, opcionalment `IdVenedorExtern`.
   - `Pagament`: `IdUsuari`; valorar si `IdVenedorExtern` ha de ser domini de `Pagament` o només enllaç a `VenedorExtern`.
   - `PeticioEnviamentExtern`: `IdVenedorExtern`, `Carrer` (o referència a `Comanda` embeguda).
   - `DadesEnviament`: decidir si cal `Estat` al codi; si sí, afegir domini; si no, treure `Estat` de `venedor_extern.py`.
   - `ProducteExtern`: domini de `IdVenedorExtern` (feedback professor: evitar subclasses amb un sol fill inútil; aquí és un cas d'atribut de producte extern).
2. **Historial:** o bé classes `HistorialCerca` / `HistorialCompra` amb dominis propis, o bé documentar explícitament (com ara) que la persistència és «reutilització de propietats» i no exigir alineació estricta en aquests fitxers.
3. **`Retorna` vs `EsRespostaA`:** unificar criteri (només un enllaç de resposta) a l'ontologia i al codi.
4. **`CostBaseKg` / `Banc`:** implementar o eliminar de l'OWL si no formen part de la quarta fase.
5. Després de canvis a l'OWL: `cd AgentZon && .venv/bin/python -m unittest discover -s tests -p 'test_*.py'`.

---

## 10. Inventari de l'ontologia (referència ràpida)

- **46** classes (incloses `Producte`, `ProducteExtern`, `ProducteIntern`, flux de compra, logística, pagaments, devolucions, recomanacions, …).
- **10** propietats objecte (`SobreComanda`, `SobreLot`, `SobreProducte`, `TeProducte`, `MostraProducte`, `UbicatACentre`, `AssignatATransportista`, `GeneraRecomanacio`, `EsRespostaA`, `Retorna`).
- **47** propietats de dades (identificadors, dates, preus, `SentitPagament`, etc.).

El codi de producció referencia **la gran majoria** d'aquest vocabulari; les llacunes i violacions estan detallades als apartats §4 i §5.

---

*Document generat per comparació automàtica i revisió del repositori AgentZon. Per asserts estructurals oficials, vegeu `tests/test_ontology_alignment.py`.*
