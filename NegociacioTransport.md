# Negociació de transport entre centre logístic i transportistes

Aquest document descriu la **política de negociació acordada** per a AgentZon (Quarta fase / apartat 7.2 de l’entrega). És la referència per implementar el codi, provar la demo i redactar l’informe. El text està en **català** i evita acoblar la lògica a noms concrets com `fast` o `economy`: s’identifiquen els papers per **preu i termini** de les ofertes inicials.

Documentació relacionada:

- [Transportistes.md](Transportistes.md) — visió general dels agents de transport i el flux de lots.
- [Entrega3.md](../../../Entrega-3/Entrega3.md) — apartat **7.2** (resum per a l’informe d’entrega).
- Codi previst: `services/logistics_service.py`, `agents/agent_centre_logistic.py`, `agents/agent_transportista.py`.

---

## 1. Objectiu de negociació

En cada lot `PREPARAT`, el centre logístic vol:

1. Obtenir ofertes de **tots** els transportistes registrats (descoberta via Directory).
2. Intentar contractar el servei **més ràpid** (oferta amb preu inicial més alt i, en general, data d’entrega més propera) **només si** el preu final no supera un sostre calculat a partir de l’oferta més barata.
3. Si no es pot tancar dins d’aquest sostre, assignar l’**oferta més barata** sense negociar-la (preu i data de la proposta inicial).

Això modela una botiga que prioritza la velocitat d’entrega però no paga un premium il·limitat: accepta pagar com a màxim un **15 %** per sobre del preu de l’opció econòmica per obtenir el servei premium.

---

## 2. Papers de les ofertes (sense `transport_id` fixos)

Després de la ronda de CFP (`PeticioTransport` → `RespostaOfertaTransport`), el centre classifica les ofertes vàlides:

| Paper | Criteri | Rol en la negociació |
|--------|---------|----------------------|
| **Oferta baixa** (`oferta_baixa`) | Menor `price` entre les inicials. En empat de preu, es desempata per `delivery_date` més propera i després per `transport_id` (ordre estable). | Pla de referència (cost mínim). **No rep contraoferta.** |
| **Oferta alta** (`oferta_alta`) | Major `price` entre les inicials (mateix criteri de desempat). | Únic candidat amb qui es negocia activament. |

Amb dos transportistes de demo (`economy` 4 €/kg / 3 dies, `fast` 8 €/kg / 1 dia), l’oferta baixa sol ser economy i l’alta fast. Si s’afegeixen més agents, la regla segueix sent la mateixa: es negocia només amb qui va llançar la **proposta inicial més cara**, no amb un nom hardcodejat.

**Requisit mínim:** cal almenys **dues** ofertes inicials per aplicar aquest protocol. Si només n’hi ha una, s’assigna directament sense contraoferta.

---

## 3. Paràmetres de la política

Tots els percentatges s’apliquen sobre el preu de l’**oferta baixa** (`P_baix`):

| Paràmetre | Valor | Significat |
|-----------|-------|------------|
| `FACTOR_CONTRAOFERTA` | **1,10** (110 %) | Preu que el centre proposa al transportista de l’oferta alta. |
| `FACTOR_SOSTRE` | **1,15** (115 %) | Preu màxim acceptable per acceptar l’oferta alta (negociada o proposada). |

Fórmules (preus en EUR, arrodonits a 2 decimals com al codi actual):

```
P_contra = round(P_baix × 1,10, 2)
P_sostre = round(P_baix × 1,15, 2)
```

**Interpretació:** el centre ofereix pagar un **10 %** per sobre del mínim del mercat; està disposat a pujar fins a un **15 %** per sobre del mínim per quedar-se amb el servei ràpid. Entre el 10 % i el 15 % hi ha un corredor on el transportista premium pot respondre amb `propose`.

---

## 4. Protocol per fases (centre logístic)

### Fase A — Recollida d’ofertes (`pla_cerca_de_transportista`)

1. Descobrir transportistes (Directory o llista cablejada en proves).
2. Enviar `PeticioTransport` **en paral·lel** a tots.
3. Emmagatzemar les `RespostaOfertaTransport` vàlides: `price`, `delivery_date`, `transport_id`, etc.

### Fase B — Contraoferta selectiva (`pla_negociar_contraoferta`)

1. Calcular `oferta_baixa` i `oferta_alta` (secció 2).
2. Calcular `P_contra` i `P_sostre`.
3. Enviar **una sola** contraoferta (`ContraofertaTransport`, performative ACL `propose`) **només** al transportista de `oferta_alta`, amb `new_price = P_contra`.
4. **No** enviar contraoferta a la resta (inclosa l’oferta baixa).

### Fase C — Decisió (`pla_de_transportista_escollit`)

Sigui `R` la resposta del transportista de l’oferta alta:

| Resposta ACL | Acció del centre |
|--------------|------------------|
| `agree` | Preu final = `P_contra`. Si `P_contra ≤ P_sostre` → guanyador = oferta alta amb aquest preu i la seva `delivery_date`. |
| `propose` (nova `RespostaOfertaTransport`) | Sigui `P_resposta` el preu extret. Si `P_resposta ≤ P_sostre` → guanyador = oferta alta actualitzada a `P_resposta`. Si `P_resposta > P_sostre` → guanyador = **oferta baixa** (preu i data inicials). |
| `refuse` o error / sense resposta | Guanyador = **oferta baixa** (oferta inicial, sense negociació). |

Després:

- `accept-proposal` al guanyador.
- `reject-proposal` a tots els altres que van participar en el CFP (inclosos els que no van rebre contraoferta).

**Important:** la selecció **no** és «el preu més baix de tot el pool negociat». És una regla explícita: *o bé premium dins del sostre, o bé econòmic a preu inicial*.

### Fase D — Assignació i notificacions

Igual que avui: `assign_transport_to_lot`, `DadesEnviament` a Compra, marcar `ENVIAT`, `ConfirmacioEnviament`, cobrament intern repartit per pes.

---

## 5. Comportament del transportista (oferta alta)

La regla antiga del transportista (acceptar si la contraoferta ≥ 85 % del **seu** preu inicial) **no** encaixa amb `P_contra = 1,10 × P_baix` quan el premium costa el doble que l’econòmic: la contraoferta queda molt per sota del 85 % del preu inicial i el centre acabaria sempre amb economy sense negociació real.

Cal **alinear** `agent_transportista.py` amb el corredor del centre. Proposta coherent:

1. El transportista recorda la seva oferta inicial `P_inicial` per al `lot_id`.
2. En rebre contraoferta amb `P_contra`:
   - Si `P_contra ≥ P_inicial` → `agree` (cas rar si les tarifes canvien).
   - Si `P_contra < P_inicial` i el centre ha proposat un preu raonable, el transportista pot:
     - **`agree`** si `P_contra` és acceptable (p. ex. `P_contra ≥ P_inicial × 0,90` o, millor, si el centre inclou al missatge RDF el sostre `P_sostre` i accepta quan `P_contra ≤ P_sostre` des del punt de vista del centre — veure nota al final).
     - **`propose`** amb `P_proposta = min(P_inicial, max(P_contra, P_sostre))` o un punt intermedi dins `[P_contra, P_sostre]` (p. ex. mitjana arrodonida) sempre que `P_proposta ≤ P_sostre`.
     - **`refuse`** si no hi ha marge (p. ex. `P_contra` massa baix respecte el seu cost).

Per a la **demo amb dos transportistes** i tarifes per defecte, una implementació simple i demostrable:

- Si `P_contra ≥ P_inicial × 0,90` → `agree` a `P_contra`.
- Sinó, si `P_contra < P_sostre` (el transportista ha de poder derivar `P_sostre` com `round(P_contra / 1,10 × 1,15, 2)` si el centre no l’envia explícitament) → `propose` amb `P_proposta = min(P_inicial, P_sostre)` o la mitjana `(P_contra + P_sostre) / 2` arrodonida.
- Sinó → `refuse`.

Això permet que, en un lot de 5 kg (20 € economy / 40 € fast), el centre contraoferti a 22 € i el fast respongui amb `propose` a 23 € o `agree` a 22 €, i el centre accepti el premium. Si fast proposa 30 €, el centre recau en economy a 20 €.

El transportista de l’**oferta baixa** no rep contraoferta; la seva lògica no canvia.

---

## 6. Exemple numèric (configuració per defecte)

Lot amb `total_weight = 5,0` kg, tarifes `economy` 4 €/kg (3 dies) i `fast` 8 €/kg (1 dia):

| Concepte | Càlcul | Valor |
|----------|--------|-------|
| `P_baix` | 5 × 4 | **20,00 €** |
| `P_alta` (inicial) | 5 × 8 | **40,00 €** |
| `P_contra` | 20 × 1,10 | **22,00 €** |
| `P_sostre` | 20 × 1,15 | **23,00 €** |

Escenaris:

1. **Fast accepta** (`agree`) a 22 € → assignació fast, 22 €, entrega en 1 dia. Estalvi de 18 € respecte la seva oferta inicial; premium de 2 € (10 %) respecte economy.
2. **Fast proposa** (`propose`) 23 € → 23 ≤ 23 → assignació fast a 23 € (15 % sobre economy).
3. **Fast proposa** 28 € o **refuse** → assignació economy a 20 € i 3 dies.
4. **Només fast respon** al CFP → es pot assignar fast sense negociació o es considera error segons política d’errors (recomanat: exigir almenys dues ofertes).

---

## 7. Comparació amb l’estratègia anterior

| Aspecte | Abans | Ara (acordat) |
|---------|--------|----------------|
| Contraoferta | Una de sola: `min(preus) − 0,01`, a **tots** | `P_baix × 1,10`, només a **oferta alta** |
| Objectiu | Empènyer tots cap al preu mínim | Intentar premium amb sostre; economy com a reserva |
| Guanyador | Preu més baix del pool negociat | Premium si `≤ P_sostre`; sinó oferta baixa inicial |
| Identificació | — | Per rang de preu, no per `transport_id` |
| Demo | Economy guanya gairebé sempre | Fast pot guanyar dins del 10–15 % |

Això segueix sent una **negociació complexa** en el sentit de l’enunciat (CFP, contraoferta, `agree` / `propose` / `refuse`, selecció condicionada), però amb una política de negoci més realista per a dos nivells de servei.

---

## 8. Casos límit i decisions de disseny

| Cas | Comportament recomanat |
|-----|-------------------------|
| Una sola oferta al CFP | Assignar-la directament; sense fase de contraoferta. |
| Dues ofertes amb el mateix preu | Desempat per `delivery_date`; la «alta» és la de termini més curt. Si tot coincideix, `transport_id` estable. |
| Tres o més transportistes | Negociar només amb la més cara; guanyador segons sostre; si es rebutja, `oferta_baixa` (no el segon més barat automàticament). |
| Cap resposta al CFP | Error / lot queda `NEGOCIANT` (com ara). |
| Oferta alta no respon a la contraoferta | `oferta_baixa` inicial. |
| `P_contra > P_sostre` per error de configuració | Tractar com a error de programació; en producció no hauria de passar amb factors 1,10 i 1,15. |

**Data d’entrega:** el criteri principal de la política és el **preu** dins del sostre; la data millor de l’oferta alta ve «gratis» si es respecta el sostre. No es compara data quan es recau en economy.

**Ontologia:** no cal afegir classes noves; `ContraofertaTransport`, `RespostaOfertaTransport` i preus RDF existents són suficients. Opcionalment es pot afegir al graf de contraoferta una propietat `PreuMaximAcceptable` = `P_sostre` perquè el transportista no calculi el sostre per inferència.

---

## 9. Mapatge al codi (implementació pendent)

| Component | Canvi previst |
|-----------|----------------|
| `logistics_service.build_counter_offer_price` | Substituir o complementar amb `build_premium_counter_offer(oferta_baixa)` → `P_contra`. |
| `logistics_service` | Nova funció `select_offer_after_premium_negotiation(oferta_baixa, oferta_alta, resposta_alta)`. |
| `agent_centre_logistic.pla_negociar_contraoferta` | Contraoferta només a `oferta_alta`; passar resultat a la nova selecció. |
| `agent_centre_logistic.pla_de_transportista_escollit` | Usar la nova selecció en lloc de `choose_winning_offer` per aquest flux. |
| `agent_transportista.respondre_contraoferta` | Regles alineades amb el corredor `[P_contra, P_sostre]`. |
| Tests | Actualitzar `test_logistics_flow`, `test_transport_agent`; afegir casos numèrics 20/22/23/40. |
| Logs | Registrar `P_baix`, `P_contra`, `P_sostre`, resposta ACL i motiu de recaure en economy. |

Els noms de plans Prometheus (`pla_cerca_de_transportista`, `pla_negociar_contraoferta`, `pla_de_transportista_escollit`) es mantenen; només canvia la lògica interna i la documentació.

---

## 10. Proves i demostració

**Tests unitaris** (sense xarxa):

- Classificació baixa/alta amb 2 i 3 ofertes.
- `P_contra` i `P_sostre` per a pes i tarifes conegudes.
- Selecció: `agree` a 22 € → fast; `propose` 24 € → economy; `refuse` → economy.

**Demo manual** (`run_agents.sh`):

1. Compra que ompli un lot (~5 kg).
2. Cron o dispar automàtic `negotiate-ready-lots`.
3. Logs del centre: contraoferta 22 € només a fast; economy sense `propose` de contraoferta.
4. Verificar `lots-CL-*.ttl`: `IdTransportista` i `CostTransport` coherents.

---

## 11. Resum en una frase

El centre demana pressupostos a tothom, ofereix al transportista més car un preu del **110 %** del més barat, i el contracta només si la resposta final no supera el **115 %** del més barat; en cas contrari, es queda l’oferta més barata sense negociar-la.
