# Jocs de Prova - AgentZon

**Versió:** 1.0  
**Data:** 5 de juny de 2026  
**Propòsit:** Demonstració del funcionament del sistema multiagent distribuït AgentZon

---

## Índex

1. [Cerca de productes](#1-cerca-de-productes)
2. [Compra d'un producte intern](#2-compra-dun-producte-intern)
3. [Compra de molts productes d'un sol centre logístic](#3-compra-de-molts-productes-dun-sol-centre-logístic)
4. [Compra de diversos productes en diferents centres logístics](#4-compra-de-diversos-productes-en-diferents-centres-logístics)
5. [Devolució que compleix els requisits](#5-devolució-que-compleix-els-requisits)
6. [Devolució que no compleix els requisits](#6-devolució-que-no-compleix-els-requisits)
7. [Suggeriments](#7-suggeriments)
8. [Donar feedback a producte](#8-donar-feedback-a-producte)
9. [Afegir producte extern](#9-afegir-producte-extern)
10. [Compra d'1 producte (extern amb enviament nostre)](#10-compra-d1-producte-extern-amb-enviament-nostre)
11. [Compra d'1 producte (extern amb enviament seu)](#11-compra-d1-producte-extern-amb-enviament-seu)

---

## 1. Cerca de productes

### Propòsit

Validar la funcionalitat de cerca amb múltiples criteris i la correcta visualització de resultats, incloent el registre a l'historial de cerques per futurs suggeriments.

### Entrada

- **Text de cerca:** "Coffee"
- **Marca:** (buit - totes les marques)
- **Categoria:** (totes les categories)
- **Rang preu:** 0€ - 50€

### Sortida

- **2 productes trobats:**
  - P1001 - Minimalist Coffee Mug (CasaNova) - 27.01€ - 0.75kg
  - P1009 - Insulated Coffee Mug (Homely) - 12.79€ - 0.33kg
- Cada producte mostra: IdProducte, Nom, Marca, Preu, Descripció, Pes
- Registre de la cerca a `historial_cerques.ttl` amb l'IP de l'usuari

### Flux

1. **Usuari** → omple formulari a `http://127.0.0.1:9001/iface` (Agent Cercador)
2. **Agent Cercador** → rep la petició HTTP del formulari
3. **Agent Cercador** → executa `pla_de_cerca` amb SPARQL sobre `productes.ttl`
4. **Agent Cercador** → envia `PeticioRegistreCerca` a Agent Opinador
5. **Agent Opinador** → registra la cerca a `historial_cerques.ttl`
6. **Agent Opinador** → confirma el registre
7. **Agent Cercador** → mostra resultats HTML amb els 2 productes

### Instruccions per l'execució

**Agents necessaris:**
- Directory (port 9000)
- Cercador (port 9001)
- Opinador (port 9004)

**Passos:**
1. Arrencar els agents: `./run_agents.sh` o manualment segons `README.md`
2. Obrir navegador: `http://127.0.0.1:9001/iface`
3. Introduir "Coffee" al camp de text
4. Deixar marca i categoria buides
5. Establir rang preu: mínim 0, màxim 50
6. Clicar "Cercar"
7. Verificar que apareixen exactament 2 productes amb "Coffee" al nom
8. Verificar a `data/historial_cerques.ttl` que s'ha registrat la cerca amb l'IP del client

**Dades de prova:**
```bash
# Verificar que els productes existeixen al catàleg
grep -A 5 "P1001\|P1009" data/productes.ttl
```

---

## 2. Compra d'un producte intern

### Propòsit

Validar el flux complet d'una compra simple amb pagament, enviament intern i coordinació entre múltiples agents, demostrant la naturalesa distribuïda del sistema.

### Entrada

- **Producte:** P1003 (Precision Mouse, InputWorks) - 30.38€ - 0.38kg
- **Ubicació:** Centre Logístic TGN
- **Dades usuari:**
  - Nom: "Test User 1"
  - Adreça: "Carrer Test 123, Barcelona"
  - Prioritat: "normal"
  - Mètode pagament: "targeta"

### Sortida

- **Comanda creada:** IdComanda únic (ex: `COM-20260605-XXXX`)
- **Data estimada entrega:** Avui + 3 dies laborables (prioritat normal)
- **Transportista assignat:** Segons negociació (ràpid o econòmic)
- **Factura:** 
  - Producte: 30.38€
  - Transport: ~5-15€ (segons oferta acceptada)
  - Total: variable
- **Registres:**
  - `historial_compres.ttl`: compra registrada amb IP usuari
  - `lots-CL-TGN.ttl`: producte assignat a lot
  - `pagaments.ttl**: pagament amb Sentit COBRAMENT
  - `seguiment_enviaments.ttl`: producte localitzat vinculat a comanda

### Flux

1. **Usuari** → selecciona P1003 des de resultats de cerca
2. **Usuari** → omple formulari compra a `http://127.0.0.1:9002/iface`
3. **Agent Compra** → rep confirmació → `pla_registrar_dades_d_usuari`
4. **Agent Compra** → crea Comanda amb IdComanda únic
5. **Agent Compra** → en paral·lel (ThreadPoolExecutor):
   - 5a. → Agent Cobrador: `PeticioRegistreDadesBancariesUsuari`
   - 5b. → Agent Opinador: `PeticioRegistreCompra`
   - 5c. → consulta `ubicacions_productes.ttl` → troba centre TGN
6. **Agent Cobrador** → registra dades bancàries a `dades_bancaries_usuari.ttl` → confirma
7. **Agent Opinador** → registra compra a `historial_compres.ttl` → confirma
8. **Agent Compra** → consulta `ubicacions_productes.ttl` → troba centre TGN per P1003
9. **Agent Compra** → crea `ProducteLocalitzat` amb id `ploc-XXXX`
10. **Agent Compra** → registra a `seguiment_enviaments.ttl`: `ploc-XXXX` ↔ IdComanda
11. **Agent Compra** → envia `ProducteLocalitzat` a Centre Logístic TGN
12. **Centre Logístic TGN** → `pla_assignar_producte_a_lot` → afegeix a lot nou/existent a `lots-CL-TGN.ttl`
13. **Centre Logístic TGN** → `pla_cerca_de_transportista` (periòdic cada 3h o immediat si activat)
14. **Centre Logístic TGN** → consulta Directory → troba Transportista ràpid i econòmic
15. **Centre Logístic TGN** → en paral·lel:
    - 15a. → Transportista ràpid (9010): `PeticioTransport` amb pes i destinació
    - 15b. → Transportista econòmic (9011): `PeticioTransport` amb pes i destinació
16. **Transportistes** → generen ofertes amb preu i data entrega
17. **Transportistes** → retornen `RespostaOfertaTransport`
18. **Centre Logístic TGN** → aplica política negociació:
    - Si millor oferta ≤ 115% de la més barata → tria la millor (més cara dins el sostre)
    - Sinó → tria la més econòmica
19. **Centre Logístic TGN** → envia `EleccioTransportista` al transportista escollit
20. **Centre Logístic TGN** → assigna data definitiva i transportista al lot
21. **Centre Logístic TGN** → `pla_producte_sha_enviat` (quan data enviament = avui)
22. **Centre Logístic TGN** → Agent Cobrador: `PeticioPagament` amb Sentit COBRAMENT + línia factura
23. **Agent Cobrador** → registra pagament a `pagaments.ttl` amb Sentit COBRAMENT
24. **Agent Cobrador** → retorna `ConfirmacioPagament` amb estat PAGAT
25. **Centre Logístic TGN** → Agent Compra: `ConfirmacioEnviament` amb factura i detalls
26. **Agent Compra** → mostra `shipping_summary.html` a usuari

### Instruccions per l'execució

**Agents necessaris (tots):**
- Directory (9000)
- Cercador (9001)
- Compra (9002)
- Centre Logístic BCN (9003)
- Opinador (9004)
- Cobrador (9005)
- Centre Logístic GI (9007)
- Centre Logístic TGN (9008)
- Transportista ràpid (9010)
- Transportista econòmic (9011)

**Passos:**
1. Verificar que P1003 està a TGN: `grep "P1003" data/ubicacions_productes.ttl`
2. Arrencar tots els agents
3. Realitzar una cerca prèvia (test 1) per trobar P1003
4. Des de resultats, clicar "Comprar" a P1003
5. Omplir formulari:
   - Nom: "Test User 1"
   - Adreça: "Carrer Test 123, Barcelona"
   - Prioritat: "normal"
   - Mètode pagament: "targeta"
6. Confirmar compra
7. Esperar resposta (pot trigar uns segons per la negociació de transport)
8. Verificar pàgina de resum amb:
   - IdComanda
   - Data entrega
   - Transportista
   - Factura detallada
9. Verificar fitxers:
   ```bash
   # Compra registrada
   grep "Test User 1" data/historial_compres.ttl
   
   # Lot creat a TGN
   cat data/lots-CL-TGN.ttl
   
   # Pagament registrat
   grep "COBRAMENT" data/pagaments.ttl
   ```

---

## 3. Compra de molts productes d'un sol centre logístic

### Propòsit

Validar l'assignació de múltiples productes a un mateix lot i l'optimització de l'enviament, demostrant que el sistema agrupa productes del mateix centre per minimitzar costos de transport.

### Entrada

- **Productes:** 
  - P1003 (Precision Mouse, InputWorks) - 30.38€ - 0.38kg - TGN
  - P1006 (Wireless Mouse, InputWorks) - 25.95€ - 0.38kg - TGN
  - P1009 (Insulated Coffee Mug, Homely) - 12.79€ - 0.33kg - TGN
  - P1012 (Ultra-Light Mouse, KeyForge) - 53.54€ - 0.30kg - TGN
- **Pes total:** ~1.39 kg
- **Preu total productes:** 122.66€
- **Dades usuari:**
  - Nom: "Test User Multi"
  - Adreça: "Carrer Gran 45, Tarragona"
  - Prioritat: "urgent"
  - Mètode pagament: "targeta"

### Sortida

- **Un sol lot creat** al Centre Logístic TGN (agrupació de 4 productes)
- **Data entrega:** Avui + 1 dia laborable (prioritat urgent)
- **Cost transport:** Optimitzat per pes total (no 4 enviaments separats)
- **Una factura** amb 4 línies de producte + 1 línia de transport
- **Registres:**
  - Un únic lot a `lots-CL-TGN.ttl` amb 4 `ProducteLocalitzat`
  - Un pagament a `pagaments.ttl` amb 4 productes
  - Una comanda a `historial_compres.ttl` amb 4 productes

### Flux

1-5. **Igual que test 2**, però amb 4 productes seleccionats
6. **Agent Compra** → consulta `ubicacions_productes.ttl` per als 4 productes → tots a TGN
7. **Agent Compra** → crea 4 `ProducteLocalitzat` (un per producte)
8. **Agent Compra** → registra els 4 a `seguiment_enviaments.ttl` vinculats a IdComanda
9. **Agent Compra** → envia els 4 `ProducteLocalitzat` a Centre Logístic TGN
10. **Centre Logístic TGN** → `pla_assignar_producte_a_lot` per a cada producte
11. **Centre Logístic TGN** → agrupa els 4 productes en un mateix lot (mateixa destinació + prioritat)
12. **Centre Logístic TGN** → registra lot únic a `lots-CL-TGN.ttl` amb 4 referències
13-26. **Resta igual que test 2**, però negociació per un sol lot amb pes total 1.39kg

### Instruccions per l'execució

**Agents necessaris:** Tots (igual que test 2)

**Passos:**
1. Verificar que els 4 productes estan a TGN:
   ```bash
   grep -E "P1003|P1006|P1009|P1012" data/ubicacions_productes.ttl
   ```
2. Realitzar cerques per trobar els 4 productes
3. Afegir els 4 productes a la comanda (segons la interfície disponible)
4. Omplir dades d'usuari amb prioritat "urgent"
5. Confirmar compra
6. Verificar que només s'ha creat **un lot**:
   ```bash
   # Comptar lots a TGN després de la compra
   grep -c "a azon:Lot" data/lots-CL-TGN.ttl
   ```
7. Verificar que el lot conté 4 productes:
   ```bash
   # Veure contingut del lot
   grep -A 20 "azon:Lot" data/lots-CL-TGN.ttl | grep "MostraProducte"
   ```
8. Verificar data entrega = avui + 1 dia
9. Verificar factura amb 4 línies de producte

---

## 4. Compra de diversos productes en diferents centres logístics

### Propòsit

Validar la coordinació distribuïda entre múltiples centres logístics i l'agregació de respostes, demostrant que el sistema pot gestionar enviaments paral·lels des de diferents ubicacions.

### Entrada

- **Productes:**
  - P1001 (Minimalist Coffee Mug, CasaNova) - 27.01€ - 0.75kg - BCN i GI
  - P1002 (Precision Mouse, KeyForge) - 94.76€ - 0.16kg - GI
  - P1003 (Precision Mouse, InputWorks) - 30.38€ - 0.38kg - TGN
  - P1005 (Adjustable Desk Lamp, CasaNova) - 82.66€ - 1.97kg - GI
- **Dades usuari:**
  - Nom: "Test User Distribuit"
  - Adreça: "Carrer Central 100, Lleida"
  - Prioritat: "normal"
  - Mètode pagament: "targeta"

### Sortida

- **3 lots creats** (un per centre logístic):
  - 1 lot a BCN amb 1 producte (P1001)
  - 1 lot a GI amb 2 productes (P1002, P1005)
  - 1 lot a TGN amb 1 producte (P1003)
- **3 negociacions paral·leles** amb transportistes (una per centre)
- **3 dates d'entrega** (possiblement diferents segons transportista assignat a cada centre)
- **Una factura agregada** amb:
  - Secció per cada centre logístic
  - Cost de transport per cada enviament
  - Total consolidat
- **Registres:**
  - 3 lots a `lots-CL-BCN.ttl`, `lots-CL-GI.ttl`, `lots-CL-TGN.ttl`
  - 3 pagaments separats a `pagaments.ttl` (un per centre quan enviïn)
  - 1 comanda a `historial_compres.ttl` amb 4 productes

### Flux

1-5. **Igual que test 2**, però amb 4 productes
6. **Agent Compra** → consulta `ubicacions_productes.ttl` per als 4 productes
   - P1001 → BCN o GI (tria BCN per proximitat a Lleida)
   - P1002 → GI
   - P1003 → TGN
   - P1005 → GI
7. **Agent Compra** → crea 4 `ProducteLocalitzat` i registra a `seguiment_enviaments.ttl`
8. **Agent Compra** → envia en paral·lel:
   - `ProducteLocalitzat` P1001 → Centre Logístic BCN
   - `ProducteLocalitzat` P1002 i P1005 → Centre Logístic GI
   - `ProducteLocalitzat` P1003 → Centre Logístic TGN
9. **Centres Logístics (BCN, GI, TGN)** → processen en paral·lel:
   - Cada un assigna els seus productes a un lot propi
   - Cada un negocia amb transportistes de manera independent
   - Cada un tria el seu transportista
10. **Centres Logístics** → quan enviïn (data enviament = avui):
    - Cada un envia `PeticioPagament` independent al Cobrador
    - Cobridor registra 3 pagaments separats amb Sentit COBRAMENT
11. **Centres Logístics** → cada un envia `ConfirmacioEnviament` a Agent Compra
12. **Agent Compra** → aggrega les 3 confirmacions
13. **Agent Compra** → mostra resum consolidat a usuari amb:
    - Detalls de cada enviament per separat
    - Factura total agregada

### Instruccions per l'execució

**Agents necessaris:** Tots (igual que test 2)

**Passos:**
1. Verificar ubicacions dels productes:
   ```bash
   grep -E "P1001|P1002|P1003|P1005" data/ubicacions_productes.ttl
   ```
2. Realitzar cerques per trobar els 4 productes
3. Afegir productes a la comanda
4. Omplir dades usuari (adreça Lleida per centralitat)
5. Confirmar compra
6. Esperar resposta (pot trigar més per coordinació de 3 centres)
7. Verificar resum amb 3 enviaments separats
8. Verificar fitxers:
   ```bash
   # Lots creats a cada centre
   grep "azon:Lot" data/lots-CL-BCN.ttl
   grep "azon:Lot" data/lots-CL-GI.ttl
   grep "azon:Lot" data/lots-CL-TGN.ttl
   
   # Pagaments múltiples
   grep -c "COBRAMENT" data/pagaments.ttl
   ```

---

## 5. Devolució que compleix els requisits

### Propòsit

Validar el flux de devolució quan es compleixen tots els criteris: motiu vàlid, dins del termini de 15 dies, i producte existent a l'historial de compres.

### Entrada

- **Comanda:** Una comanda prèvia de l'usuari (del test 2 o 3)
- **Productes a retornar:** Selecció d'1 o més productes de la comanda
- **Motiu:** "producte_defectuós" o "producte_incorrecte" (motius acceptats per política)
- **Usuari:** IP del client que va fer la compra

### Sortida

- **Resolució:** ACCEPTADA
- **Productes acceptats:** Llista de productes que compleixen criteris
- **Devolució registrada** a `devolucions.ttl` amb:
  - IdDevolució únic
  - IdComanda original
  - Productes retornats
  - Import a reemborsar
- **Pagament de retorn** a `pagaments.ttl` amb Sentit PAGAMENT
- **Lots de retorn** (si aplica) per organitzar la logística inversa
- **Confirmació** a l'usuari amb instruccions de retorn

### Flux

1. **Usuari** → accedeix a interfície de devolucions (`http://127.0.0.1:9006/iface` si existeix, o via API)
2. **Usuari** → introdueix IdComanda i selecciona productes a retornar
3. **Usuari** → indica motiu: "producte_defectuós"
4. **Agent Retornador** → rep `PeticioDevolucio`
5. **Agent Retornador** → `pla_de_compliment_de_devolucio`
6. **Agent Retornador** → consulta Agent Opinador amb `PeticioConsultaCompresUsuari`
7. **Agent Opinador** → consulta `historial_compres.ttl` amb IP usuari
8. **Agent Opinador** → retorna `ResultatConsultaCompresUsuari` amb les compres
9. **Agent Retornador** → avalia cada producte:
   - El producte pertany a la comanda? ✓
   - Data compra ≤ 15 dies? ✓
   - Motiu és "producte_defectuós" o "producte_incorrecte"? ✓
10. **Agent Retornador** → construeix `ResolucioDevolucio` amb ACCEPTADA
11. **Agent Retornador** → `pla_de_retorn`
12. **Agent Retornador** → envia `PeticioRetornDiners` a Agent Cobrador
13. **Agent Cobrador** → processa reemborsament
14. **Agent Cobrador** → registra a `pagaments.ttl` amb Sentit PAGAMENT
15. **Agent Cobrador** → retorna `ConfirmacioPagament` amb estat RETORNAT
16. **Agent Retornador** → registra devolució a `devolucions.ttl`
17. **Agent Retornador** → mostra confirmació a usuari amb instruccions

### Instruccions per l'execució

**Preparació prèvia:**
- Realitzar una compra (test 2) i anotar l'IdComanda
- Assegurar-se que la data de compra és ≤ 15 dies abans

**Agents necessaris:**
- Tots els agents (igual que test 2)
- Retornador (9006)

**Passos:**
1. Realitzar una compra simple (test 2)
2. Anotar l'IdComanda de la compra
3. Accedir a la interfície de devolucions
4. Introduir IdComanda
5. Seleccionar el producte comprat
6. Escollir motiu: "producte_defectuós"
7. Confirmar devolució
8. Verificar resposta ACCEPTADA
9. Verificar fitxers:
   ```bash
   # Devolució registrada
   cat data/devolucions.ttl
   
   # Pagament de retorn
   grep "PAGAMENT" data/pagaments.ttl
   ```

---

## 6. Devolució que no compleix els requisits

### Propòsit

Validar el rebuig correcte de devolucions que no compleixen els criteris de la política: fora de termini, motiu no vàlid, o producte inexistent.

### Entrada

- **Comanda:** Una comanda prèvia de l'usuari
- **Productes a retornar:** Productes de la comanda
- **Motiu:** "insatisfaccio_client" (només vàlid si compra ≤ 15 dies)
- **Escenari A (fora termini):** Compra realitzada fa més de 15 dies
- **Escenari B (motiu no vàlid):** Motiu buit o no reconegut

### Sortida

- **Resolució:** REBUTJADA
- **Motiu del rebuig:** Missatge explicatiu
  - Escenari A: "La devolució s'ha de sol·licitar dins dels 15 dies posteriors a la compra"
  - Escenari B: "El motiu de devolució no és vàlid segons la política de la botiga"
- **Productes acceptats:** Cap (llista buida)
- **Cap registre** a `devolucions.ttl`
- **Cap pagament** de retorn a `pagaments.ttl`

### Flux

1-8. **Igual que test 5**
9. **Agent Retornador** → avalia cada producte:
   - **Escenari A:** Data compra > 15 dies? ✗
   - **Escenari B:** Motiu no és "producte_defectuós" ni "producte_incorrecte"? ✗
10. **Agent Retornador** → construeix `ResolucioDevolucio` amb REBUTJADA
11. **Agent Retornador** → mostra missatge de rebuig a usuari
12. **NO** executa `pla_de_retorn` (no hi ha retorn de diners)

### Instruccions per l'execució

**Escenari A - Fora de termini:**

**Preparació prèvia:**
- Editar manualment `data/historial_compres.ttl` per canviar la data d'una compra anterior a >15 dies
- O utilitzar una compra molt antiga si existeix

**Passos:**
1. Accedir a interfície de devolucions
2. Introduir IdComanda antiga (>15 dies)
3. Seleccionar producte
4. Motiu: "insatisfaccio_client"
5. Confirmar
6. Verificar resposta REBUTJADA amb missatge de termini

**Escenari B - Motiu no vàlid:**

**Passos:**
1. Realitzar compra nova (test 2)
2. Accedir a devolucions immediatament
3. Introduir IdComanda
4. Seleccionar producte
5. Motiu: "altre_motiu_no_valid" o deixar buit
6. Confirmar
7. Verificar resposta REBUTJADA amb missatge de motiu invàlid
8. Verificar que NO hi ha registre a `devolucions.ttl`

---

## 7. Suggeriments

### Propòpit

Validar la generació de recomanacions personalitzades basades en l'historial de cerques i compres de l'usuari, demostrant el raonament proactiu del sistema.

### Entrada

- **Usuari:** IP d'un usuari amb historial de cerques i compres (del tests anteriors)
- **Historial de cerques:** Almenys 3 cerques prèvies registrades a `historial_cerques.ttl`
- **Historial de compres:** Almenys 1 compra prèvia registrada a `historial_compres.ttl`

### Sortida

- **Llista de 5 productes recomanats** amb:
  - IdProducte
  - Nom
  - Preu
  - Puntuació de rellevància (score)
- **Productes no comprats prèviament**
- **Ordenats per:**
  1. Coincidència amb categories comprades (pes 3)
  2. Coincidència amb marques comprades (pes 2)
  3. Coincidència amb categories cercades (pes 1)
  4. Coincidència amb marques cercades (pes 1)
  5. Productes que han aparegut en cerques (pes 1)
- **Si no hi ha puntuació:** Productes aleatoris no comprats

### Flux

1. **Agent Opinador** → s'activa periòdicament (cada `OPINADOR_RECOMMENDATION_INTERVAL_SEC`)
2. **Agent Opinador** → per a cada usuari conegut a l'historial:
   - Consulta `historial_cerques.ttl` per l'usuari
   - Consulta `historial_compres.ttl` per l'usuari
   - Carrega catàleg complet de `productes.ttl`
3. **Agent Opinador** → `pla_de_creacio_de_suggeriments`:
   - Compta categories i marques comprades
   - Compta categories i marques cercades
   - Compta productes que han aparegut en cerques
   - Calcula score per cada producte del catàleg
   - Exclou productes ja comprats
   - Ordena per score descendent
   - Selecciona top 5
4. **Agent Opinador** → comunica suggeriments a l'usuari (via interfície o notificació)

### Instruccions per l'execució

**Preparació prèvia:**
- Realitzar diverses cerques amb categories similars (ex: "peripherals")
- Comprar almenys 1 producte d'una categoria (ex: mouse)
- Assegurar-se que l'usuari té historial registrat

**Agents necessaris:**
- Directory (9000)
- Cercador (9001)
- Opinador (9004)

**Passos:**
1. Realitzar 3-4 cerques de productes "peripherals" (mouses, keyboards)
2. Comprar un mouse (test 2)
3. Accedir a la interfície de suggeriments (via Opinador o dashboard d'usuari)
4. Verificar que els suggeriments inclouen:
   - Altres productes "peripherals" (keyboards, altres mouses)
   - Productes de la mateixa marca (InputWorks, KeyForge)
   - Productes NO comprats prèviament
5. Verificar ordenació per rellevància
6. Comprovar que hi ha 5 productes (o menys si no n'hi ha suficients)

**Verificació manual:**
```bash
# Veure historial de l'usuari
grep "127.0.0.1" data/historial_cerques.ttl
grep "127.0.0.1" data/historial_compres.ttl

# Executar funció de recomanació
cd AgentZon
python -c "
from services.opinador_service import generate_recommendations
from pathlib import Path
recs = generate_recommendations(
    Path('data/productes.ttl'),
    Path('data/historial_cerques.ttl'),
    Path('data/historial_compres.ttl'),
    user_id='127.0.0.1',
    limit=5
)
for r in recs:
    print(f\"{r['product_id']}: {r['name']} - {r['price']}€\")
"
```

---

## 8. Donar feedback a producte

### Propòsit

Validar la recollida de valoracions d'usuaris sobre productes comprats, el registre del feedback, i la seva integració per millorar futurs suggeriments.

### Entrada

- **Usuari:** IP d'un usuari amb compres prèvies (del test 2 o 3)
- **Comanda:** IdComanda d'una compra completada
- **Productes:** Productes de la comanda
- **Valoració:**
  - Puntuació: 1-5 estrelles
  - Comentari: Text lliure (opcional)

### Sortida

- **Feedback registrat** a `feedback.ttl` amb:
  - IdFeedback únic
  - IdUsuari (IP)
  - IdComanda
  - IdProducte
  - Puntuació (1-5)
  - Comentari
  - Data feedback
- **Confirmació** a l'usuari que el feedback s'ha registrat
- **Sistema de suggeriments actualitzat** (el feedback influirà en futures recomanacions)

### Flux

1. **Agent Opinador** → s'activa periòdicament (cada `OPINADOR_FEEDBACK_INTERVAL_SEC`)
2. **Agent Opinador** → `pla_demanar_feedback`:
   - Consulta `historial_compres.ttl`
   - Identifica compres amb data ≥ 14 dies (MIN_DAYS_BEFORE_FEEDBACK)
   - Filtra les que ja tenen feedback a `feedback.ttl`
   - Per cada compra pendent de feedback:
3. **Agent Opinador** → envia sol·licitud de feedback a l'usuari (via interfície)
4. **Usuari** → omple formulari amb puntuació i comentari
5. **Agent Opinador** → rep `RespostaFeedback`
6. **Agent Opinador** → `pla_de_registre_de_feedback`:
   - Valida puntuació (1-5)
   - Genera IdFeedback únic
   - Data actual
7. **Agent Opinador** → registra a `feedback.ttl`
8. **Agent Opinador** → confirma registre a usuari
9. **Agent Opinador** → actualitza mètriques per suggeriments (feedback positiu augmenta score)

### Instruccions per l'execució

**Preparació prèvia:**
- Realitzar una compra (test 2) fa més de 14 dies
- O simular modificant la data a `historial_compres.ttl`
- O canviar temporalment `OPINADOR_FEEDBACK_MIN_SECONDS` a `config.py` per fer proves

**Agents necessaris:**
- Directory (9000)
- Opinador (9004)

**Passos:**
1. Verificar que hi ha una compra pendent de feedback:
   ```bash
   # Comprovar data de compra
   grep "IdComanda" data/historial_compres.ttl
   ```
2. Esperar activació periòdica de l'Opinador (o forçar via API interna)
3. Accedir a la interfície de feedback (via Opinador)
4. Veure sol·licitud de feedback per la compra
5. Introduir puntuació: 5 estrelles
6. Afegir comentari: "Excel·lent producte, molt content amb la compra"
7. Enviar feedback
8. Verificar confirmació
9. Verificar registre:
   ```bash
   cat data/feedback.ttl
   ```
10. Verificar que la propera generació de suggeriments considera aquest feedback

---

## 9. Afegir producte extern

### Propòsit

Validar la integració de productes de venedors externs al catàleg de la plataforma, incloent el registre de metadades, dades bancàries del venedor, i la delegació entre agents.

### Entrada

- **Venedor extern:**
  - IdVenedor: "VEN-001"
  - Nom: "TechGadgets SL"
  - Dades bancàries: "ES12 3456 7890 1234 5678 9012"
- **Producte extern:**
  - Nom: "Smart Fitness Tracker"
  - Descripció: "Advanced fitness tracker with heart rate monitoring"
  - Categoria: "wearables"
  - Marca: "FitPro"
  - Preu: 79.99€
  - Pes: 0.05kg
  - SkuExtern: "FIT-TRACK-001"
  - RequereixLogisticaExterna: false (enviament nostre)
  - CentreLogistic: "CL-BCN"

### Sortida

- **Producte registrat** a `productes.ttl` amb:
  - IdProducte únic (ex: EXT-XXXX)
  - Tipus: ProducteExtern
  - SkuExtern: FIT-TRACK-001
  - DataAlta: data actual
  - PertanyAVenedorExtern: venedor-VEN-001
  - UbicatACentre: centre-BCN
  - RequereixLogisticaExterna: false
- **Metadades logístiques** a `responsable_enviament_productes.ttl` (via Agent Compra):
  - IdProducte: EXT-XXXX
  - Responsable: "AgentZon" (no extern)
  - IdVenedor: VEN-001
- **Ubicació** a `ubicacions_productes.ttl` (via Agent Compra):
  - EXT-XXXX → centre-BCN
- **Dades bancàries venedor** a `dades_bancaries_venedors_externs.ttl` (via Cobrador):
  - IdVenedor: VEN-001
  - DadesBancaries: ES12...
- **Confirmació** al venedor que el producte s'ha afegit correctament

### Flux

1. **Venedor extern** → accedeix a `http://127.0.0.1:9012/iface` (Agent Venedor Extern)
2. **Venedor extern** → omple formulari amb dades del producte i venedor
3. **Agent Venedor Extern** → rep `AltaProducteExtern` (via interfície o ACL)
4. **Agent Venedor Extern** → `pla_afegir_producte_extern_a_la_bd`:
   - Processa les dades
   - Prepara les delegacions en paral·lel
5. **Agent Venedor Extern** → en paral·lel (ThreadPoolExecutor):
   - 5a. → Agent Cercador: `PeticioConsultaProductes` per afegir al catàleg
   - 5b. → Agent Compra: `PeticioRegistreProducteExternCompra` per metadades logístiques
   - 5c. → Agent Cobrador: `PeticioRegistreDadesBancariesVenedor` per dades bancàries
6. **Agent Cercador** → `pla_afegir_info_producte_extern_a_la_bd`:
   - Afegeix producte a `productes.ttl`
   - Retorna confirmació
7. **Agent Compra** → `pla_registrar_producte_extern_compra`:
   - Afegeix a `responsable_enviament_productes.ttl`
   - Afegeix a `ubicacions_productes.ttl`
   - Retorna confirmació
8. **Agent Cobrador** → `pla_registrar_dades_venedor`:
   - Afegeix a `dades_bancaries_venedors_externs.ttl`
   - Retorna confirmació
9. **Agent Venedor Extern** → espera les 3 confirmacions
10. **Agent Venedor Extern** → `pla_comunicar_nou_producte_afegit`:
    - Construeix `ConfirmacioAltaProducteExtern`
    - Envia confirmació al venedor extern
11. **Venedor extern** → rep confirmació amb IdProducte assignat

### Instruccions per l'execució

**Agents necessaris:**
- Directory (9000)
- Cercador (9001)
- Compra (9002)
- Cobrador (9005)
- Venedor Extern (9012)

**Passos:**
1. Arrencar tots els agents
2. Accedir a `http://127.0.0.1:9012/iface`
3. Omplir formulari:
   - Dades venedor:
     - Id: VEN-001
     - Nom: TechGadgets SL
     - IBAN: ES12 3456 7890 1234 5678 9012
   - Dades producte:
     - Nom: Smart Fitness Tracker
     - Descripció: Advanced fitness tracker with heart rate monitoring
     - Categoria: wearables
     - Marca: FitPro
     - Preu: 79.99
     - Pes: 0.05
     - SKU: FIT-TRACK-001
     - Logística: nostra (no externa)
     - Centre: BCN
4. Enviar formulari
5. Esperar confirmació
6. Verificar fitxers:
   ```bash
   # Producte al catàleg
   grep "FIT-TRACK-001" data/productes.ttl
   
   # Metadades logístiques
   grep "VEN-001" data/responsable_enviament_productes.ttl 2>/dev/null || echo "Fitxer gestionat per Compra"
   
   # Ubicació
   grep "EXT-" data/ubicacions_productes.ttl
   
   # Dades bancàries
   grep "VEN-001" data/dades_bancaries_venedors_externs.ttl
   ```
7. Verificar que el producte apareix a cerques posteriors

---

## 10. Compra d'1 producte (extern amb enviament nostre)

### Propòsit

Validar la compra d'un producte extern que utilitza la logística d'AgentZon, incloent el flux de pagament diferit (cobrament quan s'envia) i la transferència al venedor extern.

### Entrada

- **Producte:** Producte extern creat al test 9 (ex: EXT-XXXX, Smart Fitness Tracker)
- **Preu:** 79.99€
- **Venedor:** VEN-001 (TechGadgets SL)
- **Logística:** AgentZon (RequereixLogisticaExterna = false)
- **Ubicació:** Centre BCN
- **Dades usuari:**
  - Nom: "Test External 1"
  - Adreça: "Carrer Extern 50, Barcelona"
  - Prioritat: "normal"
  - Mètode pagament: "targeta"

### Sortida

- **Comanda creada** amb producte extern
- **Flux logístic:** Igual que producte intern (Centre BCN gestiona enviament)
- **Cobrament quan s'envia:**
  - Agent Compra NO cobra immediatament
  - Centre Logístic BCN dispara cobrament quan data enviament = avui
- **Dos pagaments:**
  1. Usuari paga a AgentZon: `pagaments.ttl` amb Sentit COBRAMENT (quan s'envia)
  2. AgentZon paga al venedor: `pagaments.ttl` amb Sentit PAGAMENT (quan s'envia)
- **Factura** mostrant:
  - Preu producte: 79.99€
  - Preu transport: variable
  - Total: variable
  - Nota: "Producte extern de TechGadgets SL"

### Flux

1-8. **Igual que test 2**, però amb producte extern
9. **Agent Compra** → consulta `responsable_enviament_productes.ttl`:
   - Producte és extern? ✓
   - Requereix logística externa? ✗ (és nostra)
10. **Agent Compra** → NO executa `pla_enviament_extern`
11. **Agent Compra** → consulta `ubicacions_productes.ttl` → centre BCN
12. **Agent Compra** → crea `ProducteLocalitzat` i registra
13. **Agent Compra** → envia a Centre Logístic BCN
14. **Centre Logístic BCN** → assigna a lot i gestiona enviament (igual que test 2)
15. **Centre Logístic BCN** → quan s'envia:
    - Envia `PeticioPagament` a Cobrador amb:
      - Sentit: COBRAMENT (usuari paga AgentZon)
      - IdVenedorExtern: VEN-001
      - Import venedor: 79.99€
16. **Agent Cobrador** → `pla_cobrament_extern`:
    - Cobra a usuari (COBRAMENT)
    - Paga a venedor (PAGAMENT)
    - Registra dos pagaments a `pagaments.ttl`
17. **Agent Cobrador** → retorna `ConfirmacioPagament` PAGAT
18. **Centre Logístic BCN** → envia `ConfirmacioEnviament` a Agent Compra
19. **Agent Compra** → mostra resum a usuari

### Instruccions per l'execució

**Preparació prèvia:**
- Realitzar test 9 per crear producte extern amb logística nostra
- Anotar IdProducte assignat (ex: EXT-XXXX)

**Agents necessaris:** Tots

**Passos:**
1. Verificar que el producte extern existeix:
   ```bash
   grep "EXT-" data/productes.ttl | grep "FitPro"
   ```
2. Realitzar cerca del producte extern (per nom "Smart Fitness Tracker")
3. Seleccionar producte
4. Omplir formulari compra
5. Confirmar
6. Esperar processament
7. Verificar resum amb indicació "Producte extern"
8. Verificar dos pagaments quan s'enviï:
   ```bash
   # Esperar fins que Centre Logístic enviï (data enviament)
   # O verificar després de la demo
   grep "VEN-001" data/pagaments.ttl
   grep "COBRAMENT" data/pagaments.ttl
   ```

---

## 11. Compra d'1 producte (extern amb enviament seu)

### Propòsit

Validar la compra d'un producte extern on el venedor gestiona l'enviament, demostrant la delegació de logística i el cobrament immediat (diferent dels productes interns).

### Entrada

- **Producte:** Nou producte extern amb logística externa
  - Nom: "Premium Wireless Headphones"
  - Marca: "AudioMax"
  - Preu: 149.99€
  - Pes: 0.35kg
  - SkuExtern: "AUD-WH-PRO-001"
  - RequereixLogisticaExterna: true (venedor envia)
  - Venedor: VEN-002 (AudioMax Corp)
  - Dades bancàries: "ES98 7654 3210 9876 5432 1098"
- **Dades usuari:**
  - Nom: "Test External 2"
  - Adreça: "Avinguda Audio 10, València"
  - Prioritat: "normal"
  - Mètode pagament: "targeta"

### Sortida

- **Comanda creada** amb producte extern
- **Cap flux logístic intern** (Centre Logístic NO intervé)
- **Cobrament immediat:**
  - Agent Compra cobra immediatament (no espera enviament)
  - Paga al venedor immediatament
- **Dos pagaments immediats:**
  1. Usuari paga a AgentZon: `pagaments.ttl` amb Sentit COBRAMENT
  2. AgentZon paga a venedor: `pagaments.ttl` amb Sentit PAGAMENT
- **Confirmació enviament extern:**
  - Venedor extern confirmarà data entrega (fora del nostre sistema)
  - O simplement confirmació que hem transferit la comanda al venedor
- **Resum a usuari:**
  - "Producte extern gestionat per AudioMax Corp"
  - "El venedor es posarà en contacte per coordinar l'enviament"
  - Preu total: 149.99€

### Flux

1-8. **Igual que test 2**, però amb producte extern
9. **Agent Compra** → consulta `responsable_enviament_productes.ttl`:
   - Producte és extern? ✓
   - Requereix logística externa? ✓ (venedor envia)
10. **Agent Compra** → `pla_enviament_extern`:
    - NO consulta ubicacions
    - NO crea ProducteLocalitzat
    - NO contacta Centre Logístic
11. **Agent Compra** → `pla_cobrament_extern`:
    - Envia immediatament `PeticioPagament` a Cobrador amb:
      - Sentit: COBRAMENT (usuari paga AgentZon)
      - Sentit: PAGAMENT (AgentZon paga venedor)
      - IdVenedorExtern: VEN-002
      - Import venedor: 149.99€
12. **Agent Cobrador** → processa dos pagaments:
    - Cobra a usuari
    - Paga a venedor VEN-002
    - Registra a `pagaments.ttl`
13. **Agent Cobrador** → retorna confirmació PAGAT
14. **Agent Compra** → comunica al venedor extern (fora del sistema, simulat)
15. **Agent Compra** → mostra resum a usuari amb indicació d'enviament extern

### Instruccions per l'execució

**Preparació prèvia:**
- Afegir producte extern amb logística externa via test 9 (modificar per VEN-002 i logística externa)
- O crear directament via interfície Venedor Extern

**Agents necessaris:**
- Directory (9000)
- Cercador (9001)
- Compra (9002)
- Cobrador (9005)
- Venedor Extern (9012)
- (Centres Logístics NO necessaris per aquest test)

**Passos:**
1. Afegir producte extern amb logística externa:
   - Accedir a `http://127.0.0.1:9012/iface`
   - Introduir dades producte i venedor
   - Marcar "Requereix logística externa = true"
   - Enviar
2. Anotar IdProducte assignat
3. Cercar el producte al cercador
4. Comprar
5. Omplir formulari
6. Confirmar
7. Verificar resposta immediata (no espera negociació transport)
8. Verificar pagaments:
   ```bash
   # Dos pagaments: un COBRAMENT, un PAGAMENT al venedor
   grep "VEN-002" data/pagaments.ttl
   ```
9. Verificar que NO hi ha lots creats:
   ```bash
   # Cap lot nou als fitxers dels centres
   ls -lh data/lots-*.ttl
   ```
10. Verificar que NO hi ha ProducteLocalitzat a `seguiment_enviaments.ttl`

---

## Notes Finals per la Demostració

### Ordre recomanat d'execució

1. **Cerca** (test 1) - Entrada al sistema
2. **Compra simple** (test 2) - Flux bàsic
3. **Compra multi-producte mateix centre** (test 3) - Optimització lots
4. **Compra multi-centre** (test 4) - Distribució
5. **Afegir producte extern logística nostra** (test 9) - Integració externs
6. **Compra extern nostra** (test 10) - Flux híbrid
7. **Afegir producte extern logística seva** (test 9 variant) - Delegació total
8. **Compra extern seva** (test 11) - Cobrament immediat
9. **Devolució vàlida** (test 5) - Reemborsament
10. **Devolució invàlida** (test 6) - Política
11. **Feedback** (test 8) - Valoració
12. **Suggeriments** (test 7) - Recomanacions

### Checklist pre-demo

- [ ] Tots els agents arrencats i registrats al Directory
- [ ] Dades de prova carregades (`data/*.ttl`)
- [ ] Ports lliures (9000-9012)
- [ ] Navegador amb accés a `http://127.0.0.1:9001/iface`
- [ ] Terminal preparat per verificar fitxers `.ttl`
- [ ] Script `run_agents.sh` provat prèviament
- [ ] IdComanda de proves pre-calculats per a tests de devolució i feedback

### Comandes útils per a la demo

```bash
# Arrencar tots els agents
cd AgentZon && ./run_agents.sh

# Verificar agents registrats al Directory
curl http://127.0.0.1:9000/Info

# Veure contingut d'un fitxer de dades
cat data/productes.ttl | less

# Comptar pagaments
grep -c "COBRAMENT\|PAGAMENT" data/pagaments.ttl

# Veure lots d'un centre
cat data/lots-CL-BCN.ttl

# Verificar ubicació producte
grep "P1003" data/ubicacions_productes.ttl

# Veure historial d'un usuari
grep "127.0.0.1" data/historial_compres.ttl
```

### Contingències

**Si un agent no arrenca:**
- Verificar que el port està lliure: `lsof -i :9001`
- Matèixer procés anterior: `kill -9 <PID>`
- Rebutjar dades corrompres: restaurar `.ttl` originals

**Si la negociació de transport triga massa:**
- El Centre Logístic negocia cada 3 hores (configurable)
- Per a demo, activar mode immediat o reduir interval a `config.py`

**Si no apareixen productes a la cerca:**
- Verificar `data/productes.ttl` no està buit
- Verificar sintaxi SPARQL al log del Cercador

**Si la devolució falla:**
- Verificar data de compra a `historial_compres.ttl`
- Verificar que el motiu és exactament "producte_defectuós" o "producte_incorrecte"

---

**Document preparat per a la demostració de la pràctica ECSDI - AgentZon**  
**Quadrimestre Primavera 2025-2026**  
**Universitat Politècnica de Catalunya**
