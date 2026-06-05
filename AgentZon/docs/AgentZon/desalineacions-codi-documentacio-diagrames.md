# Desalineacions entre diagrames, documentació i codi d'AgentZon

## Abast i criteri de comparació

Aquest informe parteix del criteri següent:

- Els apartats **1-4** de `AgentZon-Documentació.md` s'han d'interpretar com a **documentació de disseny** i, per tant, s'han de comparar sobretot amb `Diagrames-Entrega-2.pd`.
- Els apartats **6-9** del mateix fitxer s'han d'interpretar com a **documentació de la implementació** i, per tant, s'han de comparar sobretot amb el codi actual d'`AgentZon/`.
- L'apartat **5** de `AgentZon-Documentació.md` s'ignora per a aquesta revisió, perquè la documentació actual de l'ontologia és `ontologia per agents.md`.

Per això, no totes les diferències són errors. En molts casos són simplement **canvis entre fases**: del disseny inicial a la implementació final.

## 1. Desalineacions entre el disseny inicial i la implementació actual

Aquest bloc compara el que descriuen els diagrames i els apartats 1-4 amb el que realment fa el sistema actual.

### 1.1 Cobrament intern i extern

Al disseny inicial, el flux de compra i cobrament era més centralitzat al voltant de l'`Agent Compra`.

A la implementació actual:

- `Compra` només registra les dades bancàries de l'usuari si no consten encara.
- `Compra` només envia `PeticioPagament` al `Cobrador` per als **pagaments a venedors externs**.
- El **cobrament intern a l'usuari** no el dispara `Compra`, sinó el `Centre Logístic` quan envia una `ConfirmacioEnviament` al `Cobrador`.

Això canvia de manera clara la responsabilitat del moment real del cobrament.

### 1.2 Logística externa: venedor extern, no transportista

El disseny inicial ja apuntava que l'enviament extern depenia del `Venedor Extern`.

La implementació actual ho manté:

- els `Transportista` només intervenen en la **logística interna** dels centres logístics;
- els productes amb `RequereixLogisticaExterna` es gestionen amb `PeticioEnviamentExtern` cap al `Venedor Extern`.

La diferència important és que aquest flux ha quedat més definit al codi que no pas als diagrames.

### 1.3 No existeix un “PeticioEnviamentIntern” com a missatge real

En el disseny inicial es parlava del centre logístic com a receptor d'una petició d'enviament intern relativament genèrica.

Al codi actual el flux està desdoblat:

- `Compra` envia `ProducteLocalitzat` al `Centre Logístic`;
- el centre respon amb `ConfirmacioLocalitzacio`;
- més endavant envia `DadesEnviament`;
- i finalment envia `ConfirmacioEnviament`.

Per tant, la implementació actual no utilitza un únic missatge abstracte d'enviament intern, sinó un cicle de missatges més ric.

### 1.4 D'un únic centre logístic a un sistema multi-centre

Els diagrames modelen un centre logístic genèric i una gestió de lots pensada com a peça única.

La implementació actual ja és multi-centre:

- hi ha centres independents com `CL-BCN`, `CL-GI` i `CL-TGN`;
- cada centre es registra al `Directory` amb `IdCentreLogistic` i `Ciutat`;
- `Compra` decideix quin centre usar per producte a partir de `ubicacions_productes.ttl`;
- cada centre manté els seus propis lots (`lots-CL-BCN.ttl`, `lots-CL-GI.ttl`, `lots-CL-TGN.ttl`).

Això és una evolució real respecte al disseny inicial.

### 1.5 Desencadenament de la negociació de transport

Als diagrames, el `Pla cerca de transportista` s'activa “cada 3 hores”.

Al codi actual:

- la negociació es pot llançar automàticament quan un lot queda `PREPARAT`;
- també hi ha un endpoint `/cron/negotiate-ready-lots` per processar lots preparats.

El model ha passat d'una percepció temporal rígida a un model més event-driven i operatiu.

### 1.6 Política concreta de negociació

Als diagrames, la negociació de transport queda descrita de forma general: es recullen ofertes i se n'escull una.

La implementació actual introdueix una política concreta:

- oferta baixa com a referència;
- contraoferta del `110%`;
- preu sostre del `115%`;
- si l'oferta ràpida no entra dins del sostre, es manté l'oferta econòmica.

Això no és un error documental, sinó una concreció posterior del disseny.

### 1.7 Qui informa l'usuari de l'enviament

Al disseny inicial, el centre logístic apareix com a actor més proper a la comunicació final del transport.

A la implementació actual:

- el `Centre Logístic` informa `Compra`;
- `Compra` actualitza `seguiment_enviaments.ttl`;
- l'usuari consulta l'estat a la vista resum o a `/orders/<order_id>`.

Per tant, `Compra` és ara el punt únic de resum d'enviaments.

### 1.8 Feedback i recomanacions

Als diagrames, feedback i recomanacions són processos **periòdics i proactius**.

Al codi actual:

- no existeix un `pla_demanar_feedback` periòdic;
- l'usuari entra al dashboard de l'`Opinador`;
- el sistema calcula recomanacions quan es carrega la vista;
- el feedback es registra des de formulari, sota demanda.

El sistema ha passat d'un model push a un model més aviat pull.

### 1.9 Registre de compra a l'historial

Al disseny inicial, el `Pla registre de compra` estava vinculat al `Cobrador`.

Al codi actual:

- qui envia `PeticioRegistreCompra` és `Compra`;
- l'`Opinador` només fa la persistència i respon amb `ConfirmacioRegistreCompra`.

El punt d'origen del registre ha canviat.

### 1.10 Devolucions

El disseny inicial assumia un flux més complet de devolució:

- validació;
- coordinació de la logística de retorn;
- recepció del producte retornat;
- reemborsament posterior.

Al codi actual:

- es poden retornar productes de **múltiples comandes** en una sola petició;
- la validació és **per producte**;
- només s'accepten tres motius: producte defectuós, no conforme amb la descripció o entrega tardana;
- no hi ha una logística inversa formalitzada abans del reemborsament;
- si la devolució és acceptada, el reemborsament es demana gairebé immediatament al `Cobrador`.

És una simplificació clara del flux inicial.

### 1.11 Regla dels 15 dies

Als diagrames i al text de disseny inicial, la finestra de quinze dies es combinava amb motius d'insatisfacció més amplis.

Al codi actual, la regla és més restrictiva:

- els 15 dies només compten si el motiu forma part de la política acceptada;
- motius com “No m'ha agradat” o “M'he equivocat” es deneguen sempre.

### 1.12 Alta de productes externs

Als diagrames, l'alta d'un producte extern s'entén com la sincronització de tres confirmacions: persistència local, catàleg i dades bancàries.

Al codi actual:

- el venedor té un flux de `setup` propi;
- les dades bancàries només es registren si no hi són ja;
- l'alta del producte executa en paral·lel la persistència local i la del catàleg;
- la ubicació física només s'escriu si el producte no requereix logística externa.

El flux és més flexible que el model inicial.

## 2. Canvis visibles dins d’`AgentZon-Documentació.md` entre fases

Aquest bloc no compara el document contra el codi, sinó el document **contra si mateix**.

### 2.1 Els apartats 1-4 i 6-9 no descriuen el mateix sistema

El fitxer barreja dues capes temporals:

- els apartats 1-4 encara conserven gran part del model conceptual inicial;
- els apartats 6-9 ja documenten una implementació posterior molt més concreta.

Per això hi ha contradiccions internes que no són casuals, sinó rastre del pas de fase.

### 2.2 Compra i cobrament

Hi ha una tensió clara entre:

- la visió de disseny on el cobrament sembla més centralitzat en el flux de compra;
- i la visió d'implementació on el cobrament intern surt del `Centre Logístic` i l'extern de `Compra`.

### 2.3 Centre logístic únic vs centres múltiples

L'apartat **6.3** encara parla d'un únic centre “de moment”.

L'apartat **7.3** ja descriu un sistema multi-centre complet.

Aquest és un dels canvis de fase més visibles dins del mateix `.md`.

### 2.4 Opinador: registre de compra

L'apartat **4.6** continua associant el registre de compra al `Cobrador`.

Els apartats **6.4** i **8.1** ja reflecteixen el flux actual, on aquest registre surt de `Compra`.

### 2.5 Retornador i devolucions

L'apartat **4.5** encara projecta una devolució amb més logística de retorn.

L'apartat **6.7** ja reflecteix la implementació actual:

- validació per producte;
- agrupació per comanda;
- reemborsament quasi immediat;
- retorn multi-comanda.

### 2.6 Noms de fitxers de dades

Dins del propi document hi conviuen noms antics i nous:

- `historialcerques.ttl` vs `historial_cerques.ttl`;
- `historialcompres.ttl` vs `historial_compres.ttl`;
- `compres.ttl` vs `comandes.ttl`.

Això no és només una qüestió cosmètica: també dificulta veure quina versió del sistema s'està descrivint.

## 3. Mancances i desalineacions d’`ontologia per agents.md` respecte `AgentZonOntology.rdf`

Aquest bloc substitueix l'anàlisi de l'antic apartat 5.

### 3.1 Classes estructurals de l'ontologia que falten o queden molt poc explicades

`ontologia per agents.md` se centra sobretot en missatges i models de dades pràctics, però deixa gairebé fora classes estructurals que sí existeixen a l'RDF:

- `Actor`
- `Accio`
- `Resposta`
- `Comunicacio`
- `Banc`
- `Usuari`
- `Pagament`
- `Recomanacio`
- `ProducteIntern`

Aquestes classes no són accessòries: formen part del model semàntic general de l'ontologia.

### 3.2 Classes de missatge de l’RDF que no queden ben documentades

Hi ha classes ontològiques reals que al `.md` no apareixen amb el nom correcte o queden directament absorbides dins d'altres explicacions:

- `AltaProducteExtern`
- `ConfirmacioAltaProducteExtern`
- `EleccioTransportista`
- `ProducteLocalitzat`
- `PeticioRegistreDadesBancariesUsuari`
- `PeticioRegistreDadesBancariesVenedor`
- `ConfirmacioRegistreDadesBancaries`

També hi ha casos on el concepte hi és, però amb un nom documental diferent del que defineix l'ontologia.

### 3.3 Propietats de l'ontologia que falten o queden infradocumentades

El `.md` no cobreix prou bé diverses propietats que sí són part del model RDF:

- `EsRespostaA`
- `GeneraRecomanacio`
- `Retorna`
- `UbicatACentre`
- `DadesBancariesUsuari`
- `DadesBancariesVenedorExtern`
- `DataAlta`
- `DataPagament`
- `IdPagament`
- `CostBaseKg`
- `IdBanc`
- `SkuExtern`
- `RequereixLogisticaExterna`
- `TextConsulta`
- `CategoriaConsulta`
- `MarcaConsulta`
- `PreuMinim`
- `PreuMaxim`

Algunes surten insinuades funcionalment, però no queden formalitzades com a propietats de l'ontologia.

### 3.4 Model incomplet de les recomanacions

Aquest és un dels punts ontològics més clars.

Al `.md`, `RespostaRecomanacio` es descriu com si apuntés directament als productes, sovint via `MostraProducte`.

Però a l'RDF real el model és:

- `RespostaRecomanacio`
- `GeneraRecomanacio`
- `Recomanacio`
- `SobreProducte`

Per tant, al document falta el node intermedi `Recomanacio` i la propietat `GeneraRecomanacio`, i es simplifica massa l'estructura real.

### 3.5 `MostraProducte` està sobregeneralitzat al `.md`

A l'ontologia RDF, `MostraProducte` està lligat a `ResultatCerca`.

Al `.md`, en canvi, aquesta relació es reutilitza també per descriure recomanacions. Això desdibuixa el model semàntic real, on la cerca i la recomanació no comparteixen exactament la mateixa estructura.

### 3.6 Termes del `.md` que no existeixen a l’ontologia real

Hi ha diversos noms que apareixen a `ontologia per agents.md` però **no existeixen** com a classes o propietats a `AgentZonOntology.rdf`:

- `PeticioRegistreProducteExtern`
- `ConfirmacioRegistreProducte`
- `PeticioLocalitzacioProductes`
- `PeticioCobramentIntern`
- `PeticioRegistreDadesVenedor`
- `ConfirmacioRegistreDades`
- `OfertaTransport`
- `AcceptTransportOffer`
- `RejectTransportOffer`
- `Quantitat`
- `Volum`
- `IdVenedor`

Alguns d'aquests noms corresponen a:

- simplificacions documentals;
- performatives ACL;
- noms interns de flux;
- o conceptes que existeixen al codi però no com a classes de l'ontologia.

### 3.7 Noms documentals que haurien de mapar-se a noms RDF canònics

Alguns termes del `.md` no són absurds, però haurien d'estar alineats amb el nom canònic de l'ontologia:

- `PeticioRegistreProducteExtern` hauria de mapar a `AltaProducteExtern`
- `ConfirmacioRegistreProducte` hauria de mapar a `ConfirmacioAltaProducteExtern`
- `PeticioLocalitzacioProductes` hauria de mapar a `ProducteLocalitzat`
- `PeticioRegistreDadesVenedor` hauria de mapar a `PeticioRegistreDadesBancariesVenedor`
- `ConfirmacioRegistreDades` hauria de mapar a `ConfirmacioRegistreDadesBancaries`

Sense aquest mapatge, el document sembla descriure una ontologia diferent de la que realment hi ha.

### 3.8 `ConfirmacioEnviament` queda descrita com a resposta pura, però l’RDF la modela com a acció

A `AgentZonOntology.rdf`, `ConfirmacioEnviament` és subclasse d'`Accio`.

En canvi, al `.md` sovint es presenta només com una notificació o resposta informativa.

Això és rellevant perquè el sistema actual reutilitza aquest concepte també com a contingut de missatge per activar el cobrament intern.

### 3.9 `ConfirmacioRetornDiners` sí apareix, però sense encaixar-la bé en la jerarquia

El `.md` menciona `ConfirmacioRetornDiners`, però no deixa gaire clar que a l'RDF és una classe pròpia de resposta, diferent d'una simple descripció operativa del reemborsament.

Passa una cosa similar amb `ConfirmacioRegistreDadesBancaries`: el concepte funcional hi és, però el nom ontològic complet no queda fixat.

## 4. Soroll històric i restes antigues al `.pd`

El fitxer `Diagrames-Entrega-2.pd` conté noms que ja no tenen correspondència neta amb el codi actual o que semblen restes d'iteracions intermèdies, per exemple:

- `Pla confirmar pagament`
- `Pla d'informar cobrament`
- `Pla cobrar comanda pròpia`
- `Pla de registre`
- variants duplicades o amb errades tipogràfiques com `Pla producte als nostres magatezems` o `Pla de presentacioó`

No és un problema del codi actual, però sí una font de soroll quan es vol usar el `.pd` com si fos una especificació vigent.

## 5. Què ha canviat realment del disseny a la implementació

Aquest resum recull la diferència substancial entre:

- `Diagrames-Entrega-2.pd` + apartats 1-4
- i el sistema final documentat als apartats 6-9 i implementat al codi

### 5.1 Canvis funcionals principals

1. El sistema ha passat d'un model més seqüencial a una orquestració realment asíncrona amb `ThreadPoolExecutor`, notificacions diferides i seguiment persistent.
2. La logística ha passat d'un centre genèric a una arquitectura multi-centre real, resolta via `Directory`.
3. La negociació de transport s'ha concretat en una política premium `110% / 115%`.
4. `Compra` s'ha convertit en el punt únic de resum i seguiment d'enviaments.
5. El cobrament ha quedat separat en tres casos: cobrament intern, pagament a venedor extern i devolució.
6. El feedback i les recomanacions han passat d'un model periòdic a un dashboard sota demanda.
7. Les devolucions s'han simplificat i especialitzat: validació per producte, suport multi-comanda i reemborsament quasi immediat.
8. L'alta de venedors externs s'ha fet més pràctica amb perfil previ, registre condicional de dades bancàries i separació clara entre catàleg, responsabilitat d'enviament i ubicació física.

### 5.2 Conclusió general

La conclusió més important és aquesta:

- `Diagrames-Entrega-2.pd` i els apartats 1-4 continuen sent útils com a **fotografia del disseny inicial**.
- Els apartats 6-9 i el codi actual descriuen un **sistema posterior, més concret i més distribuït**.
- `ontologia per agents.md` és útil com a guia operativa, però encara **no està totalment alineada amb `AgentZonOntology.rdf`** ni en noms ni en estructura semàntica.

Si es vol deixar la documentació neta, l'ordre més lògic seria:

1. mantenir clar que els apartats 1-4 són disseny de fase anterior;
2. revisar `ontologia per agents.md` perquè faci servir els noms canònics de l'RDF;
3. decidir si `Diagrames-Entrega-2.pd` s'ha de conservar com a document històric o si cal generar uns diagrames nous alineats amb el sistema final.
