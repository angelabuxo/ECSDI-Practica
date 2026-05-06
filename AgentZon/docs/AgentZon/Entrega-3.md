# 

# **ENTREGA 2**

# **Especificació del sistema i disseny arquitectònic**

Enginyeria de coneixements i sistemes distribuïts intel·ligents

Universitat Politècnica de Catalunya

Quadrimestre Primavera 2025-2026

| Professor | Javier Béjar |
| ----: | :---- |
| **Membres de l’equip** | Àngela Buxó López Paula Mas Pascual Pol Montanera Vives |

**Índex**

[**1\. Introduction	5**](#introduction)

[**2\. System Specification	6**](#system-specification)

[**2.1 Scenarios	6**](#2.1-scenarios)

[Buscar productes	6](#buscar-productes)

[Comprar productes	6](#comprar-productes)

[Gestionar negociació d’enviament	6](#gestionar-negociació-d’enviament)

[Retornar productes	6](#retornar-productes)

[Gestionar Feedback	7](#gestionar-feedback)

[Recomanar productes	7](#recomanar-productes)

[Introduïr productes externs	7](#introduïr-productes-externs)

[**2.2 Goal Overview	8**](#2.2-goal-overview)

[Buscar productes	8](#buscar-productes-1)

[Comprar productes	8](#comprar-productes-1)

[Retornar productes	10](#retornar-productes-1)

[Recomanar productes	11](#recomanar-productes-1)

[Gestionar Feedback	11](#gestionar-feedback-1)

[Introduïr productes externs	12](#introduïr-productes-externs-1)

[**2.3 System Roles	13**](#2.3-system-roles)

[Gestor de cerca de productes	13](#gestor-de-cerca-de-productes)

[Gestor de petició de compra	13](#gestor-de-petició-de-compra)

[Gestor de comanda	13](#gestor-de-comanda)

[Gestor de magatzem	13](#gestor-de-magatzem)

[Negociador d’enviament	13](#negociador-d’enviament)

[Gestor de devolucions	14](#gestor-de-devolucions)

[Validador de devolucions	14](#validador-de-devolucions)

[Gestor de feedback	14](#gestor-de-feedback)

[Gestor de pagaments	14](#gestor-de-pagaments)

[Gestor de suggeriments	14](#gestor-de-suggeriments)

[Gestor venedors externs	14](#gestor-venedors-externs)

[**2.4 Analysis Overview	15**](#2.4-analysis-overview)

[Usuari	15](#usuari)

[Venedor extern	15](#venedor-extern)

[Transportista	15](#transportista)

[Proveïdor de pagament	15](#proveïdor-de-pagament)

[Gestor del sistema (AgentZon)	15](#gestor-del-sistema-\(agentzon\))

[**3\. Architectural Design	16**](#architectural-design)

[**3.1 Data Coupling	16**](#3.1-data-coupling)

[Informació Productes	16](#informació-productes)

[Historial de cerques	16](#historial-de-cerques)

[Historial de compres	16](#historial-de-compres)

[Feedback	16](#feedback)

[Dades bancàries Usuari	16](#dades-bancàries-usuari)

[Dades d’enviament Usuari	16](#dades-d’enviament-usuari)

[Ubicacions Productes	16](#ubicacions-productes)

[Dades bancàries venedors externs	16](#dades-bancàries-venedors-externs)

[Responsable enviament productes	16](#responsable-enviament-productes)

[Lots	17](#lots)

[Devolucions	17](#devolucions)

[**3.2 Agent-Role Grouping	18**](#3.2-agent-role-grouping)

[Agent Cercador	18](#agent-cercador)

[Agent Compra	18](#agent-compra)

[Agent Cobrador	18](#agent-cobrador)

[Agent Centre Logístic	18](#agent-centre-logístic)

[Agent Retornador	18](#agent-retornador)

[Agent Opinador	18](#agent-opinador)

[Agent Venedor Extern	18](#agent-venedor-extern)

[**3.3 Agent Acquintance	19**](#3.3-agent-acquintance)

[**4\. Detailed design	20**](#detailed-design)

[4.1 Agent Cercador	20](#4.1-agent-cercador)

[4.2 Agent Compra	20](#4.2-agent-compra)

[4.3 Agent Cobrador	21](#4.3-agent-cobrador)

[4.4 Agent Centre Logístic	21](#4.4-agent-centre-logístic)

[4.5 Agent Retornador	22](#4.5-agent-retornador)

[4.6 Agent Opinador	22](#4.6-agent-opinador)

[4.7 Agent Venedor Extern	23](#4.7-agent-venedor-extern)

[**5\. Descripció de l’ontologia	24**](#descripció-de-l’ontologia)

[Reutilització d'Ontologies Existents	24](#reutilització-d'ontologies-existents)

[5.1 Actor	24](#5.1-actor)

[5.1.1 Usuari	24](#5.1.1-usuari)

[5.1.2 Transportista	24](#5.1.2-transportista)

[5.1.3 VenedorExtern	24](#5.1.3-venedorextern)

[5.1.4 ProveïdorPagament	24](#5.1.4-proveïdorpagament)

[5.2 Producte	25](#5.2-producte)

[5.2.1 ProducteExtern	25](#heading=h.x53sci559wmb)

[5.3 Lot	25](#5.3-lot)

[5.4 Comanda	25](#5.4-comanda)

[5.5 Devolució	25](#5.5-devolució)

[5.6 Feedback	25](#5.6-feedback)

[5.7 OfertaProducte	25](#5.7-ofertatransport)

[5.8 CentreLogístic	25](#5.8-centrelogístic)

[5.9 Comunicació	25](#5.9-comunicació)

[5.10.1 Acció	25](#5.10.1-acció)

[5.10.2 Resposta	25](#5.10.2-resposta)

[**6\. Justificació implementació	27**](#implementació-d’agents)

[**7\. Elements del nivell avançat de la pràctica	27**](#elements-del-nivell-avançat-de-la-pràctica)

[**8\. Tasques amb nota extra	27**](#tasques-amb-nota-extra)

[**9\. Jocs de prova	27**](#jocs-de-prova)

[**10\. Distribució de la feina	28**](#distribució-de-la-feina)

[**11\. Resultats i conclusió	28**](#resultats-i-conclusió)

# 

1. # **Introduction** {#introduction}

L'objectiu principal d'aquest projecte és el disseny i la implementació d'una plataforma de serveis i agents intel·ligents capaç de gestionar els processos d'una empresa global de comerç electrònic. El sistema, AgentZon, busca permetre que un usuari delegui la cerca i compra de productes a un assistent virtual personalitzat, el qual ha de ser capaç de raonar per presentar les millors opcions disponibles.

Aquesta plataforma no només gestiona la interacció directa amb l'usuari, sinó que també coordina tota la logística interna: des de la localització de productes en centres logístics distribuïts geogràficament fins a la negociació complexa amb transportistes externs per a l'enviament de lots de paquets. A més, AgentZon inclou funcionalitats avançades com la gestió de devolucions, la recopilació de *feedback* i la generació de recomanacions proactives basades en l'historial de l'usuari.

Al llarg del document s'han comentat algunes decisions que s'han pres al llarg de l'anàlisi del projecte per tal de facilitar-ne la comprensió. Aquestes decisions, el seu motiu i justificació estan explicades en un *color gris clar i en cursiva*.

2. # **System Specification** {#system-specification}

## **2.1 Scenarios** {#2.1-scenarios}

### **Buscar productes** {#buscar-productes}

Quan l’usuari fa la petició de buscar un o diversos productes al sistema introduint una sèrie de paràmetres, el sistema processa la consulta i li retorna tota la informació detallada dels productes trobats.

### **Comprar productes** {#comprar-productes}

Quan l’usuari, després d’haver seleccionat els productes que vol comprar, fa una petició de compra, se li demanen les seves preferències d’enviament i dades de pagament. Quan es validen aquestes dades, el sistema valida la transacció. Dins d’aquest escenari hi ha dos subescenaris:

	**Gestionar enviament**

L’enviament de productes es pot gestionar de dues maneres:

**Enviament propi**

Si AgentZon gestiona l’enviament, quan s’ha validat la transacció d’una compra, el sistema localitza els productes, els assigna a lots i es coordina amb l’escenari *Gestionar negociació d’enviament* per tal de poder informar dels detalls de l’entrega.

**Enviament extern**

Si el venedor extern s’encarrega de la logística de transport, el sistema es limita a rebre i comunicar a l’usuari la informació de l’enviament (transportista, estat i data estimada d’entrega).

	**Cobrar compra**

Quan s’ha validat la transacció de l’enviament d’una compra, el sistema redirigeix l’usuari a la passarel·la de pagament i aquest introdueix les dades de pagament. Es processa la transacció i el sistema registra l’estat del pagament i informa l’usuari amb la factura, en cas que els productes comprats provinguin d’una botiga externa, es realitza la transferència cap a aquesta.

### **Gestionar negociació d’enviament** {#gestionar-negociació-d’enviament}

Diàriament es proposen enviaments de lots a les empreses de transport i, a través d’una negociació, s’escullen els transportistes per enviar les comandes i obtenir la data definitiva d’entrega.

### **Retornar productes** {#retornar-productes}

Quan l’usuari sol·licita la devolució d’un producte comprat i el sistema verifica l’estat i la política de devolució de la botiga, s’accepta o rebutja la sol·licitud i s’informa l’usuari. Si és acceptada, el sistema gestiona la logística de retorn, l’usuari envia el producte i el sistema confirma la recepció i processa el reemborsament.

### **Gestionar Feedback** {#gestionar-feedback}

Quan han passat 2 setmanes de la compra d’una comanda, es demana a l’usuari la seva opinió sobre el/s producte/s que ha comprat. El sistema registra la valoració i millora el sistema de suggeriments per a l’usuari.

### **Recomanar productes** {#recomanar-productes}

El sistema analitza les dades d’historial i preferències de l’usuari i genera una llista de productes recomanats de manera periòdica. 

### **Introduïr productes externs** {#introduïr-productes-externs}

Els venedors externs proporcionen informació sobre els productes que volen vendre a la plataforma i el sistema els enregistra. A més, indiquen si volen que la botiga s’encarregui de l'enviament dels productes o si prefereixen gestionar-ho ells mateixos. Aquesta informació queda associada als productes i serà utilitzada durant el procés de compra. Un cop el producte ha sigut acceptat i correctament emmagatzemat al sistema, s’envia un missatge de confirmació.

*Hem decidit crear aquest últim escenari ja que hem considerat que el fet que intervingui un nou actor, els venedors externs, requereix que tota la comunicació amb aquest i la integració dels productes proporcionats no formin part de cap altre escenari existent, a més, té una pròpia percepció que l’activa, quan els venedors externs informen periòdicament dels nous productes.* 

## 

## **2.2 Goal Overview** {#2.2-goal-overview}

### **Buscar productes** {#buscar-productes-1}

Objectiu on es descriu que s’ha de poder cercar un o diversos productes dins del sistema mitjançant uns paràmetres determinats i obtenir la informació detallada dels resultats trobats. Per a satisfer aquest, s’han de complir els següents subobjectius:

**Processar petició**

El sistema ha de ser capaç de gestionar la petició de cerca realitzada per l’usuari per tal d’interpretar correctament la consulta i iniciar el procés de cerca corresponent. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Rebre dades cerca**

El sistema ha de rebre els paràmetres introduïts per l’usuari, com la marca, model, rang de preu… per tal de poder utilitzar-los en la consulta.

**Realitzar cerca**

Un cop rebudes les dades, el sistema ha d’executar la cerca dins de la base de dades de productes per tal de trobar aquells que coincideixin amb els criteris especificats.

**Mostrar productes**

El sistema ha de mostrar a l’usuari els productes trobats com a resultat de la cerca, amb la informació rellevant de cadascun d’ells perquè l’usuari els pugui revisar.

### **Comprar productes** {#comprar-productes-1}

Objectiu on es descriu que l’usuari ha de poder comprar un o diversos productes que ha seleccionat prèviament. Quan l’usuari fa la petició de compra, el sistema li demana les seves preferències d’enviament i les dades de pagament. Quan aquestes dades es validen, el sistema duu a terme la transacció. Dins d’aquest objectiu es gestionen també els processos d’enviament i pagament dels productes. Per a satisfer aquest, s’han de complir els següents subobjectius:

**Gestionar petició de compra**

El sistema ha de gestionar la sol·licitud de compra realitzada per l’usuari per tal de recopilar tota la informació necessària per completar la transacció. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Rebre detalls de compra**

El sistema ha de rebre la informació dels productes seleccionats per l’usuari i les seves preferències inicials per tal de preparar el procés de compra.

**Validar compra**

El sistema ha de verificar que la comanda es pot processar correctament. Això inclou comprovar la existència dels productes sol·licitats i registrar la comanda dins del sistema.

**Gestionar enviament**

El sistema ha de coordinar tota la logística necessària per fer arribar els productes des dels centres logístics fins a l'usuari final. Per a satisfer aquest, s’han de complir els següents subobjectius:

**Enviar compra**

El sistema ha de gestionar el procés d’enviament dels productes un cop validada la transacció de compra. Aquest procés inclou la localització dels productes, l’organització dels enviaments, la selecció del transportista i la comunicació de la informació a l’usuari. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

	**Localitzar productes**

El sistema ha de determinar en quin centre logístic es troben els productes de la comanda per tal de preparar el procés d’enviament.

**Assignar productes a lots**

El sistema ha d’agrupar els productes de les comandes en diferents lots segons criteris predefinits per tal d’optimitzar el procés d’enviament.

Hem decidit separar “Assignar productes a lots” i no definir-lo com a subobjectiu de Gestionar negociació d’enviament perquè hem suposat que la negociació d’enviament es fa sobre lots ja creats, és a dir, lots que ja han estat creats prèviament.

**Informar detalls d’enviament**

El sistema ha de comunicar a l’usuari la informació relacionada amb l’enviament de la comanda, com el transportista seleccionat i la data estimada d’entrega.

**Notificar venta a Venedor extern**

El sistema ha de comunicar al venedor extern els detalls de la transacció realitzada per tal de coordinar la logística corresponent en cas que aquest producte sigui d’enviament extern.

**Cobrar compra**

El sistema ha de gestionar el procés de pagament de la compra a través d’una passarel·la de pagament. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Rebre detalls de pagament**

El sistema ha de rebre les dades de pagament introduïdes per l’usuari a la passarel·la de pagament.

**Realitzar cobrament**

El sistema ha de processar la transacció econòmica corresponent a la compra.

**Processar pagament amb botiga externa**

Si el producte pertany a una botiga externa, el sistema ha de transferir el pagament a la botiga. També ha de comunicar-se amb la botiga externa per tal de validar i registrar la transacció realitzada.

**Informar del cobrament**

El sistema ha d’informar l’usuari sobre l’estat del pagament i proporcionar la factura corresponent.

**Gestionar negociació d’enviament**

El sistema ha de gestionar el procés d’organització dels enviaments i la negociació amb els transportistes disponibles per tal de seleccionar l’opció més adequada per a cada enviament. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Proposar enviament de lots**

El sistema ha de proposar l’enviament dels lots als transportistes disponibles indicant les característiques de l’enviament.

**Escollir transportistes**

El sistema ha de consultar les ofertes dels transportistes disponibles i seleccionar aquell que ofereixi les millors condicions segons els criteris establerts.

### **Retornar productes** {#retornar-productes-1}

Objectiu on es descriu que l’usuari ha de poder sol·licitar la devolució d’un producte comprat. El sistema ha de verificar l’estat del producte i la política de devolució de la botiga per determinar si la sol·licitud és vàlida. En funció del resultat, la devolució serà acceptada o rebutjada i s’informarà l’usuari. Si és acceptada, el sistema gestionarà la logística de retorn del producte i el reemborsament corresponent. Per a satisfer aquest, s’han de complir els següents subobjectius:

	**Processar petició devolució**

El sistema ha de processar la petició de devolució de l’usuari comprovant que tots els camps siguin correctes.

	**Validar devolució**

El sistema ha de verificar que la devolució compleixi les condicions de la 	política de devolucions. Un cop comprovada la validesa, el sistema ha de determinar si la sol·licitud de devolució és acceptada o rebutjada segons les condicions definides. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

		**Denegar devolució**

El sistema ha d’informar l’usuari sobre l’estat denegat de la seva sol·licitud de devolució, aportant informació sobre el motiu pel qual s’ha denegat la devolució.

	**Acceptar devolució**

El sistema ha de gestionar la sol·licitud realitzada per l’usuari per dur a terme el procés de devolució. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

	**Comunicar detalls devolució**

El sistema ha d’informar l’usuari sobre el procés de retorn del producte i les instruccions necessàries per realitzar-lo.

	**Recollir producte retornat**

El sistema ha de registrar que el producte retornat ha estat rebut correctament per tal de continuar amb el procés de devolució i  ha d’establir comunicació amb la botiga o servei extern encarregat de gestionar el retorn per coordinar el procés.

**Retornar diners**

Un cop confirmada la recepció del producte retornat, el sistema ha de processar el reemborsament corresponent a l’usuari segons la forma de pagament utilitzada.

### **Recomanar productes** {#recomanar-productes-1}

Objectiu on es descriu que el sistema ha de poder analitzar les dades disponibles sobre l’usuari, com l’historial de cerques i de compres, per tal de generar una llista de productes recomanats de manera periòdica. Aquestes recomanacions permeten oferir suggeriments personalitzats que poden resultar d’interès per a l’usuari. Per a satisfer aquest, s’han de complir els següents subobjectius:

**Obtenir suggeriments**

El sistema ha de recopilar la informació necessària sobre l’activitat de l’usuari per tal de poder generar recomanacions adequades. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Consultar historial de cerques**

El sistema ha d’analitzar les cerques realitzades anteriorment per l’usuari per tal d’identificar interessos o preferències en determinats productes o categories.

**Consultar historial de compres**

El sistema ha de consultar les compres realitzades prèviament per l’usuari per tal de detectar patrons de compra i poder suggerir productes similars o relacionats.

**Generar suggeriments**

El sistema ha de processar la informació obtinguda de l’historial de cerques i compres per tal d’elaborar una llista de productes recomanats adaptada als interessos de l’usuari.

**Comunicar suggeriments**

El sistema ha de mostrar a l’usuari els productes recomanats, presentant-los de manera clara perquè l’usuari els pugui consultar i, si ho desitja, obtenir més informació o afegir-los al procés de compra.

### **Gestionar Feedback** {#gestionar-feedback-1}

Objectiu on es descriu que el sistema ha de poder gestionar les valoracions i opinions dels usuaris després d’haver realitzat una compra. Passat un temps determinat, es demana a l’usuari la seva opinió sobre el producte o productes comprats. El sistema registra aquesta informació i utilitza aquestes dades per millorar el sistema de suggeriments. Per a satisfer aquest, s’han de complir els següents subobjectius:

**Obtenir Feedback**

El sistema ha de recopilar la valoració de l’usuari sobre els productes adquirits per tal de conèixer la seva experiència de compra. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Demanar Feedback**

El sistema ha de sol·licitar a l’usuari la seva opinió sobre el producte o productes comprats després d’un període determinat des de la compra.

**Rebre dades Feedback**

El sistema ha de rebre les valoracions, comentaris o puntuacions proporcionades per l’usuari.

**Processar Feedback**

El sistema ha de tractar la informació rebuda per tal d’actualitzar les dades relacionades amb els productes i millorar el funcionament del sistema. Per a satisfer aquest objectiu s’han de complir els següents subobjectius:

**Registrar FeedBack**

El sistema ha de guardar les valoracions i comentaris de l’usuari al sistema.

**Millorar suggeriments**

El sistema ha d’utilitzar el feedback rebut per ajustar i millorar el sistema de recomanació de productes per a l’usuari.

### **Introduïr productes externs** {#introduïr-productes-externs-1}

Objectiu on es descriu que el sistema ha de permetre la incorporació i gestió de productes provinents de botigues externes, assegurant que aquests es puguin integrar dins del catàleg general i participar en els processos de compra, enviament i pagament. Per a satisfer aquest, s’han de complir els següents subobjectius:

	**Processar petició de nous productes**

El sistema ha de gestionar la sol·licitud de les botigues externes que volen incorporar nous productes a la plataforma. Per a això, ha de rebre les dades dels productes, com la descripció, el preu, la categoria, la disponibilitat i les condicions d’enviament.

	**Actualitzar productes en venda**

El sistema ha de registrar els productes nous dins del catàleg i permetre a les botigues externes modificar la informació d’aquests, com el preu, l’estoc o les seves característiques.

	**Acordar gestió d’enviament**

El sistema ha de determinar com es gestionarà l’enviament dels productes de botigues externes, ja sigui per part de la plataforma o delegant aquesta responsabilitat a la botiga externa segons les condicions acordades amb el venedor. 

## 

## **2.3 System Roles** {#2.3-system-roles}

### **Gestor de cerca de productes** {#gestor-de-cerca-de-productes}

Aquest rol s’encarrega de cercar productes dins de la botiga electrònica amb unes certes restriccions (p.e.: preu, qualitat, valoracions) i presentar una llista de productes possibles a comprar. Com a percepció, aquest rol espera que l’usuari faci una petició sobre una cerca d’un producte. L’objectiu associat al rol és la cerca dels productes. Com a resultat, es mostren els detalls de la cerca (una llista de productes possibles a comprar).

### **Gestor de petició de compra** {#gestor-de-petició-de-compra}

Aquest rol s’encarrega de gestionar el procés de compra de manera automatitzada un cop l’usuari ha escollit els productes. La percepció d’aquest objectiu és una petició de comprar productes. S’associa a l’objectiu de gestionar les peticions de compres de productes i en conseqüència, realitza les accions de confirmar la compra i consultar l’adreça de lliurament, la prioritat de l'entrega i el mètode de pagament.

### **Gestor de comanda** {#gestor-de-comanda}

Aquest rol s’encarrega de gestionar les comandes individuals dels usuaris i preparar la logística per al seu enviament des d’un dels centres logístics de la tenda. Com a percepció, aquest rol rep la confirmació d’una compra. Els seus objectius són localitzar productes i informar sobre els detalls de l’enviament als usuaris receptors. Per tant, les accions associades son informar sobre la data d’enviament i el transportista.

*Hem decidit crear un rol que s’encarregui de les comandes “individualitzades” de cada client separant-lo del “Gestor de petició de compra” perquè creiem que l’objectiu de localitzar els productes i seguir el seguiment d’una comanda no hauria de recaure sobre el mateix rol que s’encarrega de la interacció directa amb el client.*

### **Gestor de magatzem** {#gestor-de-magatzem}

Aquest rol s’encarrega de la gestió de productes dins d’un magatzem. S’activa quan, en fer una comanda, un dels productes es troba al magatzem del cap. Té com a objectiu assignar els productes del magatzem a lots (segons la ciutat de destí i prioritat d’entrega). Com a resultat, fa l’acció d'agrupar els productes en lots.

*Hem decidit separar aquest rol del “Negociador d’enviament” perquè creiem que agrupar els productes ha de ser independent dels transportistes, tot i que posteriorment compartiràn agent, els considerem dos rols diferents.*

### 

### **Negociador d’enviament** {#negociador-d’enviament}

Aquest rol s’encarrega de dur a terme la negociació amb els transportistes, proposant l’enviament d’un cert nombre de paquets (per pes) a una ciutat destí i amb un termini màxim d’entrega. Un cop els diferents transportistes responen amb les propostes, el negociador escull el més adequat. La percepció d’aquest rol és el transcurs d’un cert temps determinat, cada 3 hores. L’objectiu associat és la gestió de la negociació de l’enviament dels lots, i com a resultat, l’acció d’haver escollit un transportista junt amb les dades d’entrega.

### **Gestor de devolucions** {#gestor-de-devolucions}

Aquest rol s’encarrega del procés de devolució d’un producte defectuós, equivocat o que no satisfà l’usuari. Com a percepció, s’activa quan una devolució ha estat acceptada. Té l’objectiu de gestionar aquesta devolució, i dur a terme les accions de comunicar a l’usuari les dades de la devolució i tornar-li els diners. 

### **Validador de devolucions** {#validador-de-devolucions}

Aquest rol s’encarrega de validar una devolució que un usuari ha demanat. Comprova el motiu de devolució, és a dir, que el producte sigui equivocat/defectuós, o, si és el cas que el client està insatisfet, que la petició de devolució s’hagi fet dins dels primers quinze dies des de la recepció del producte. El rol s’activa quan l’usuari fa una petició de devolució. Els objectius són processar la petició de devolució i si és el cas, denegar la devolució. Com a acció, comunica la decisió final sobre la devolució a l’usuari.

*Hem decidit distingir el rol de “Gestor de devolucions” i el de “Validador de devolucions” ja que aquest segon s’encarrega únicament de decidir la validesa de la petició, i comuincar-ho en cas que no ho sigui, és el Gestor de devolucions qui, en cas de ser acceptada, la gestionarà.*

### **Gestor de feedback** {#gestor-de-feedback}

Aquest rol s’encarrega de sol·licitar i recollir l’opinió de l’usuari sobre un producte un temps després d’haver-lo rebut. La percepció d’aquest rol és quan ha passat una setmana que l’usuari ha rebut el producte. L’objectiu és gestionar el feedback i com a resultat, executa l’acció de demanar feedback.

### **Gestor de pagaments** {#gestor-de-pagaments}

Aquest rol s’encarrega de gestionar els pagaments dels productes. Aquest s’activa un cop el producte ha estat enviat. El seu objectiu és cobrar la compra. Les accions resultants són enviar la factura al client i si el producte és ofert per un venedor extern, la transferència de diners a aquest venedor.

*Hem decidit separar “Gestor de pagaments” dels altres involucrats en la compra ja que el cobrament depèn de la confirmació de l’enviament i, per tant, ha d’estar fora del flux de la comanda.*

### **Gestor de suggeriments** {#gestor-de-suggeriments}

Aquest rol s'encarrega de recomanar productes a l'usuari de manera proactiva analitzant el seu historial de compres i cerques. S’activa periòdicament. El seu objectiu és recomanar productes a l’usuari. Com a resultat, realitza l’acció de comunicació de suggeriments.

### **Gestor venedors externs** {#gestor-venedors-externs}

Aquest rol s'encarrega de rebre periòdicament la informació sobre les característiques dels productes que els comerciants externs volen vendre a través de la plataforma i integrar-los. La percepció d’aquest rol és una petició d’un venedor extern per oferir el seu producte. L’objectiu és integrar els productes dels venedors externs. Com a resultat, executa l’acció d’actualitzar catàleg de productes i confirma que el procés s’ha realitzat als venedors externs.

## **2.4 Analysis Overview** {#2.4-analysis-overview}

S’han identificat 6 actors principals per al sistema:

### **Usuari** {#usuari}

És l’actor principal de compra i delega les seves tasques a l’agent assistent virtual. S’encarrega d’imposar les seves restriccions de cerca de productes, fer peticions de compra i/o devolució i proporcionar feedback sobre els productes comprats.

### **Venedor extern** {#venedor-extern}

Representa les empreses o venedors externs que anuncien els seus productes a la plataforma. Interactua amb el sistema mitjançant el seu agent representant, informant periòdicament de l’estoc dels seus productes.

### **Transportista** {#transportista}

Representa el servei de transport extern encarregat de fer l’enviament dels productes als usuaris. Interactua amb els centres logístics del sistema per rebre conjunts de paquets que estan destinats a ubicacions properes i, quan aquests s’han entregat, confirmar l’entrega.

**Registre de transportistes**

Representa el registre que conté tots els transportistes amb les seves condicions. Quan el centre logístic vol enviar algun lot, demana quins transportistes poden realitzar-ho.

### **Proveïdor de pagament** {#proveïdor-de-pagament}

És l’entitat encarregada de processar el cobrament al mètode de pagament de l’usuari i realitzar les transferències corresponents als venedors externs un cop es confirma l’enviament. En el cas que s’hagi de fer una devolució, aquesta entitat també és l'encarregada del reemborsament dels diners.

### **Gestor del sistema (AgentZon)** {#gestor-del-sistema-(agentzon)}

És l’element central de la plataforma i engloba el control de totes les tasques, coordinant els agents interns que es comuniquen amb els diferents actors externs. S’encarrega d’accions com: mostrar productes, enviar factures, gestionar recomanacions de productes, notificar dades d’enviament als usuaris i gestionar les negociacions amb els transportistes des dels centres logístics.

# 

3. # **Architectural Design** {#architectural-design}

## **3.1 Data Coupling** {#3.1-data-coupling}

El sistema conté diverses fonts de dades que són modificades i/o consultades pels diferents agents. 

### **Informació Productes** {#informació-productes}

Conté els productes que hi ha la plataforma i la seva informació. És consultat pel rol Gestor de cerca de productes.

### **Historial de cerques**  {#historial-de-cerques}

Conté els productes cercats per cada usuari. És modificat pel rol Gestor de cerca de productes i consultat pel Gestor de suggeriments.

### **Historial de compres** {#historial-de-compres}

Conté la informació de quines compres ha realitzat cada usuari. És consultat i modificat pel Gestor de suggeriments i consultat pel Gestor de feedback.

### **Feedback** {#feedback}

Conté el feedback donat per cada usuari de cada producte. És modificat pel rol Gestor de feedback i consultat pel Gestor de suggeriments.

### **Dades bancàries Usuari** {#dades-bancàries-usuari}

Conté les dades bancàries dels usuaris del sistema. És modificat i consultat pel Gestor de pagaments.

### **Dades d’enviament Usuari** {#dades-d’enviament-usuari}

Conté les dades d’enviament de cada usuari. És modificat pel rol Gestor de petició de comanda i consultat pel Gestor de comanda.

### **Ubicacions Productes** {#ubicacions-productes}

Conté la localització del magatzem que conté cada producte venut al sistema. És modificat pel rol pel rol Gestor venedors externs i consultat pel rol Gestor de comanda.

*Hem decidit separar “Ubicacions Productes” de “Informació productes” perquè dos agents diferents consulten aquestes BD, i hem pensat que l’”Ag. Compra” no té per què conèixer informació detallada dels productes, amb la ubicació d’aquests ja en té suficient per localitzar-los.*

### **Dades bancàries venedors externs** {#dades-bancàries-venedors-externs}

Conté les dades bancàries dels venedors externs per a fer-hi el pagament dels seus productes venuts. És modificat i consultat pel Gestor de pagaments.

### **Responsable enviament productes** {#responsable-enviament-productes}

Conté les dades d’enviament de cada producte extern, si ha de ser enviat per la botiga o s’encarrega el venedor extern. És modificat pel rol Gestor venedors externs i consultat pel Gestor de comanda.

*Hem considerat separar “Responsable enviament productes” de “Informació productes” pel mateix motiu que “Ubicacions Productes”. L’ “Ag. Cercador”, quan consulta la informació detallada dels productes, no té per què conèixer qui s’encarregaria d’enviar-los en cas que es compressin. A més, això evita que molts agents comparteixin les mateixes dades.*

### **Lots** {#lots}

Conté les agrupacions de productes en lots de cada magatzem i l’id d’usuari que l’ha comprat. És modificat pel Gestor de magatzem i consultat per aquest mateix i el rol Negociador d’enviament.

### **Devolucions** {#devolucions}

Conté tots els productes que han sigut retornats. És modificat pel rol Gestor de devolucions.

## **3.2 Agent-Role Grouping** {#3.2-agent-role-grouping}

### **Agent Cercador** {#agent-cercador}

Agent que processa les consultes dels usuaris segons paràmetres específics, retornant informació detallada sobre els productes. Efectua el rol de Gestor de cerca de productes.

### **Agent Compra** {#agent-compra}

Agent que coordina el procés d'adquisició, processant la llista de productes, l'adreça i la prioritat d'entrega, i generant la data prevista de lliurament. Efectua els rols de Petició de compra i Gestor de comanda.

*Hem decidit separar aquests dos agents per dues raons. Per una banda, accedeixen a fonts de dades totalment diferents, i d’aquesta manera evitem n agent amb accés a un gran nombre d’aquestes. I per altra banda, l’agent cercador només s’ocupa d’un còmput, mentre que l’Agent Compra té un rol molt més comunicatiu i de gestió.*

### **Agent Cobrador** {#agent-cobrador}

Agent que s'encarrega de processar els cobraments als clients, les transferències als venedors externs i els reemborsaments necessaris en cas de devolució. Efectua el rol de Gestor de pagaments.

### **Agent Centre Logístic** {#agent-centre-logístic}

Agent que gestiona l'estoc en un magatzem, agrupa les comandes en lots i negocia amb les empreses de transport per obtenir les millors condicions d'enviament. N’existeix un per cada magatzem de productes. Efectua els rols de Gestor de magatzem i Negociador d’enviament. 

### **Agent Retornador** {#agent-retornador}

Agent que gestiona les sol·licituds de devolució, verificant si compleixen els terminis i motius, i coordina la logística per retornar el paquet a la botiga. Efectua els rols de Validador de devolucions i Gestor de devolucions.

### **Agent Opinador** {#agent-opinador}

Agent encarregat de sol·licitar i registrar les valoracions dels usuaris un cop rebut el producte i de generar recomanacions proactives basades en l'historial de cerques i compres. Efectua els rols Gestor de suggeriments i Gestor de feedback.

*S’ha decidit ajuntar els rols Gestor de suggeriments i Gestor de feedback per dos motius. En primer lloc, accedeixen a quasi les mateixes fonts de dades, per tant, simplifica l’acoblament si és tot un mateix agent. Per altra banda, ambdós s’activen periòdicament per fer les seves funcions, per tant són dos rols proactius i això facilita la seva agrupació.*

### **Agent Venedor Extern** {#agent-venedor-extern}

Agent encarregat de comunicar-se amb els venedors externs per tal d'introduir els seus productes al catàleg i gestionar les compres dels seus productes. Efectua el rol de Gestor venedors externs.

## 

## **3.3 Agent Acquintance** {#3.3-agent-acquintance}

**Agent Retornador → Agent Cobrador**  
Protocol: Retorn diners devolució. Un cop l'Agent Retornador ha validat que la petició de l'usuari compleix amb les polítiques de devolució, inicia aquest protocol per sol·licitar el reemborsament. L'Agent Cobrador rep l'ordre i executa la transacció financera per retornar l'import corresponent al compte del client.

**Agent Compra → Agent Cobrador**  
Protocol: Realitzar Cobrament. L'Agent Compra envia a l'Agent Cobrador el detall dels productes adquirits, l'import total acumulat de la factura i la informació de l'usuari a qui s'ha d'efectuar el càrrec. L'Agent Cobrador, quan rebi la confirmació de l’enviament de productes, executarà l'operació financera.

**Agent Compra → Agent Centre Logístic**   
Protocol: Enviar Productes. Donat que el sistema disposa d'un agent per a cada centre logístic, l'Agent Compra s'encarrega de dividir la comanda i enviar a cada responsable de magatzem exclusivament els identificadors dels productes que es troben sota la seva gestió. En aquesta comunicació, a més dels IDs dels productes, s'inclouen les dades del lloc d'entrega i les preferències d'enviament de l'usuari. Amb aquesta informació, l’Agent Centre Logístic pot agrupar els productes en els lots pertinents. Aquest protocol es dona només si és un enviament de gestió interna.

**Agent Centre Logístic** **→ Agent Compra**  
Protocol: Dades Enviament. Després de gestionar la preparació del paquet i negociar amb les empreses de distribució, el Centre Logístic respon a l'Agent Compra especificant la data definitiva prevista per al lliurament i l'identificador del transportista assignat.

*Hem decidit separar la comunicació entre els dos agents, Agent Centre Logístic i Agent Compra, en dos protocols perquè entre una comunicació i l’altra hi ha una percepció externa que no se sap quan arribarà.*

**Agent Cercador → Agent Compra**  
Protocol: Nova Compra. L'Agent Cercador, un cop l'usuari ha finalitzat la tria, envia els identificadors únics dels productes seleccionats. D'aquesta manera, l'Agent Compra rep tota la informació necessària per començar el procés de compra.

4. # **Detailed design** {#detailed-design}

## **4.1 Agent Cercador** {#4.1-agent-cercador}

L’agent Cercador disposa de dues capacitats.

En primer cas, la capacitat *Processar Cerca* es basa en dos plans.

- *Pla de cerca*. S’inicia amb la petició de cerca de l’usuari, realitza la consulta a la base de dades d’informació de productes i emmagatzema els productes cercats. Envia un missatge al Pla de presentació amb els resultats obtinguts.

- *Pla de presentació*. S’activa amb el missatge de Resultats obtinguts per part del Pla de cerca i mostra els detalls d’aquests a l’usuari.

En segon cas, la capacitat *Afegir informació de producte extern* es basa en un sol pla.

- *Pla afegit info producte extern a la BD*. S’activa en rebre un missatge de l’agent Venedor Extern amb dades d’un nou producte. L’agent procedeix a emmagatzemar-lo a la base de dades d’informació de productes i envia un missatge de confirmació de registre correcte.

## **4.2 Agent Compra** {#4.2-agent-compra}

L’agent Compra disposa de quatre capacitats.

En primer lloc, la capacitat *Processar petició compra* es basa en un sol pla.

- *Pla demanar informació usuari*. S’inicia amb la recepció de la petició de compra i s'encarrega de sol·licitar a l'usuari les dades de l'adreça d'enviament, la prioritat i el mètode de pagament.

En segon lloc, la capacitat *Gestionar compra* té un sol plà. 

- *Pla registrar dades d’usuari.* S’inicia quan es reben les dades d’enviament i bancàries per part de l’usuari. Es comunica amb l’Agent Cobrador per desar les dades bancàries de l’usuari i en rep confirmació. També guarda a “Dades d’enviament d’usuari” l’adreça d’enviament i confirma la compra a l’usuari. Finalment envia un missatge a Cp. Localitzar productes perquè comenci el seu procés, i a Cp. Registrar nova compra perquè la registri.

En tercer lloc, la capacitat *Localitzar productes* es basa en 4 plans.

- *Pla enviament extern*. S’inicia amb el missatge per part de la capacitat Gestionar compra. Consulta la base de dades de Responsable enviament productes i, en cas de ser extern, es comunica al Venedor extern i a l’Agent Cobrador per a que cobri aquell producte extern a l’usuari.

- *Pla producte als nostres magatzems.* S’inicia amb el missatge per part de la capacitat Gestionar compra. Consulta les bases de dades d’Ubicacions productes i Dades d’enviament usuari i envia un missatge a cada Agent Centre Logístic que pertoca perquè gestionin l’enviament.

- *Pla informar usuari sobre l’enviament.* S’inicia al rebre els missatges per part dels Agents Centre Logístics de la Data d’entrega definitiva i el transportista escollit. Aleshores, informa  l’Usuari.

Per últim, la capacitat *Registrar nova compra* es basa en un sol pla.

- *Pla delegar registre compra*. S’executa en rebre la notificació de compra confirmada per part de la Cp.Gestionar compra. Consisteix a enviar a l’Agent Opinador les dades de la compra perquè les pugui afegir a l’historial, i rebre una confirmació.

## **4.3 Agent Cobrador** {#4.3-agent-cobrador}

L’agent Cobrador disposa de tres capacitats.

En primer cas, la capacitat *Guardar dades bancàries* es basa en un pla.

- *Registrar dades de venedors externs*. S’inicia en rebre un missatge de l’Agent Venedor Extern amb les dades bancàries d'un venedor; l’agent procedeix a desar-les a la base de dades “Dades bancàries venedors externs” i envia un missatge de confirmació.  
- *Registrar dades d'usuari*. S’activa en rebre les dades bancàries d'un usuari per part de l’Agent Compra; l’agent emmagatzema la informació a la base de dades “Dades bancàries Usuari” i envia la confirmació del registre correcte a l’Agent Compra.

En segon cas, la capacitat *Cobrar compra* es basa en un pla.

- *Pla de cobrament intern*. S’inicia amb un missatge de l’Agent Centre Logístic comunicant que s’han enviat alguns productes i es poden cobrar. L’agent envia l’acció de cobrar al Proveïdor de pagament extern i envia la factura a l’usuari. Un cop finalitzat envia la confirmació a l’Agent Centre Logístic.  
- *Pla de cobrament extern*. S’activa amb un missatge de l’Agent Compra a mesura que s’ha de cobrar algun producte d'enviament extern. Aleshores fa l’acció de pagament al Venedor Extern i envia el missatge de confirmació a l’Agent Compra.

En tercer cas, la capacitat *Gestionar Devolucions* es basa en un sol pla.

- *Pla retornar diners*. S’activa en rebre un missatge de l’Agent Retornador amb les instruccions per fer el cobrament d’una devolució. L’agent llegeix les dades de l’usuari per procedir al retorn dels diners i envia un missatge de confirmació de devolució feta a l’Agent Retornador. En cas de ser un producte extern, llegeix les dades dels Venedors externs per a gestionar-ho.

## **4.4 Agent Centre Logístic** {#4.4-agent-centre-logístic}

L’agent Centre Logístic disposa de tres capacitats.

En primer cas, *Gestionar magatzem.* Aquesta capacitat es basa en un sol pla. 

- *Pla assignar producte a lot*. Permet processar el missatge de l’Agent Compra quan es localitza un producte que ha de ser enviat. S’emmagatzema el producte a la BD Lots amb la resta de productes que compleixen condicions compatibles.

Per altra banda, es disposa de la capacitat de *Negociar transport,* la qual es divideix en dos plans.

- *Pla cerca de transportista*. Cada 3 hores es llegeix la base de dades per decidir quins lots s'envien i es fa la proposta al centre de transportistes. 

- *Pla de transportista escollit*. S’activa amb les ofertes rebudes per part dels transportistes. Es comunica l’elecció al centre de transportistes i s’envien missatges a l’usuari amb el transportista escollit i la data d’entrega definitiva que se’ns ha proporcionat.

Finalment, la capacitat de Gestionar post-enviament, la qual es basa en un pla. 

- Pla producte s’ha enviat. S’activa quan un lot té una data igual a avui. Envia un missatge a l’Agent cobrador comunicant que ja pot cobrar els productes concrets als usuaris pertinents i rep confirmació d’aquest.

## **4.5 Agent Retornador** {#4.5-agent-retornador}

L’agent Retornador disposa de dues capacitats.

En primer cas, *Validar devolució*. Aquesta capacitat es basa en un sol pla.

- *Pla de compliment de devolució*. S'inicia amb la petició de devolució de l'usuari. Es comunica amb l’Agent Opinador per verificar si la comanda compleix els requisits de devolució. Amb la resposta rebuda, l'agent executa la resposta final enviant a l’usuari l’acceptació o denegació de la seva sol·licitud. A més, si ha sigut acceptada, ho comunica a la capacitat Gestionar retorn de diners.

Per altra banda, es disposa de la capacitat de *Gestionar retorn de diners*, la qual es basa en un pla.

- *Pla de retorn.* Aquesta s'activa un cop confirmada l'acceptació de la devolució per part de la capacitat anterior i es demana a l’Agent Cobrador l'execució del pagament i es rep la seva confirmació*.* Registra la transacció a la base de dades de devolucions i comunica la informació pertinent a l’usuari. 

## **4.6 Agent Opinador** {#4.6-agent-opinador}

L’agent Opinador té tres capacitats.

En primer cas, la capacitat *Gestionar feedback* es basa en dos plans.

- *Pla demanar feedback*. S’activa per la periodicitat establerta i s’encarrega de sol·licitar la valoració directament a l’usuari.

- *Pla registrar feedback*. S’activa en rebre la resposta de l’usuari i emmagatzema la informació a la base de dades.

En segon cas, la capacitat *Crear suggeriments* consta d’un sol pla.

- *Pla Crear suggeriments.* S’activa de forma periòdica segons el calendari de recomanacions. Llegeix les dades de l'historial de cerques i de compres per generar propostes personalitzades i informa a l’usuari.

Per últim, la capacitat *Gestionar consultes BD* es basa en dos plans.

- *Pla Registre de compra*. S’activa quan l’Agent Cobrador informa d'una compra realitzada per tal d'incorporar-la a l’historial de compres. S’emmagatzema a la BD d’Historial de compres i s’envia confirmació.

- *Pla Consulta de criteris de devolució*. S’activa quan l’Agent Retornador fa una petició. L’agent llegeix l’historial de compres per verificar si es compleixen els criteris i envia la resposta corresponent.

## 

## **4.7 Agent Venedor Extern** {#4.7-agent-venedor-extern}

L’agent Venedor extern té una capacitat.

*Afegir producte extern* es basa en quatre plans.

- *Pla afegir producte extern a la BD*. S’activa quan rep la percepció nou producte extern. Aleshores, amb les dades rebudes, per una banda emmagatzema la informació pertinent a les dues bases de dades, Responsable enviament productes i Ubicacions productes. Un cop acabat, envia un missatge de confirmació al Pla comunicar nou producte afegit.

- *Pla afegir info producte extern.* S’activa quan rep la percepció nou producte extern. Envia les dades rebudes a l’Agent Cercador per emmagatzemar-les i en rep confirmació. Un cop acabat, envia un missatge de confirmació al Pla comunicar nou producte afegit.

- *Pla delegar afegir dades bancàries del venedor extern.* S’activa quan rep la percepció nou producte extern. Aleshores envia les dades bancàries a l’Agent Cobrador perquè les emmagatzemi, i rep confirmació d’aquest. Un cop acabat això, envia un missatge de confirmació al Pla comunicar nou producte afegit.

- Pla comunicar nou producte afegit. S’activa en rebre els tres missatges de confirmació. Envia la confirmació del producte registrat correctament al Venedor extern.

# 

5. # **Descripció de l’ontologia** {#descripció-de-l’ontologia}

**Què cal documentar?**  
Descripción de la ontología/ontologías que habéis diseñado para vuestra práctica describiendo las decisiones que habéis tomado. Básicamente, tenéis que contar qué habéis representado, como habéis decidido lo que debíais representar, como lo habéis representado (clases, atributos relaciones) y donde habéis usado esa representación (qué agentes/protocolos la usan y cómo)

Per definir el coneixement i el vocabulari que els agents d’AgentZon han de compartir per poder comunicar-se i entendre's, hem dissenyat la nostra pròpia ontologia. L'objectiu d'aquesta és modelar formalment els conceptes del domini i el contingut dels missatges intercanviats.

## **Reutilització d'Ontologies Existents** {#reutilització-d'ontologies-existents}

Sabem que una molt bona pràctica en el disseny d'ontologies és reutilitzar i aprofitar ontologies ja existents, és per això que en un principi vam pensar d’importar **GoodRelations (gr)** i **Friend of a Friend (foaf)** per les classes Producte com una subclasse de gr:ProductOrService, Usuari com una subclasse de foaf:Person, i VenedorExtern i Transportista com a subclasse de foaf:Organization. No obstant això, ens vam adonar que degut a les limitacions de l’enunciat i a les consideracions que hem de fer, ens era més fàcil i intuïtiu fer el disseny completament nosaltres, definint els atributs i les relacions que considerem per cada concepte.

## **5.1 Actor** {#5.1-actor}

###      **5.1.1 Usuari** {#5.1.1-usuari}

Concepte que representa un usuari que pot interactuar amb el sistema, fent una cerca de productes, comprant-ne, donant feedback o sol·licitant una devolució. Té com a atributs un identificador personal “idUsuari” i el seu nom personal “Nom”.  
*Hem decidit que els atributs “Adreca” i “DadesBancaries” pertanyin directament al concepte “Comanda” i no a “Usuari” ja que comandes diferents d’un mateix usuari poden tenir adreçes de lliurament i/o mètodes de pagament diferents.*

###      **5.1.2 Transportista** {#5.1.2-transportista}

Concepte que representa un transportista que rep ofertes per lliurar comandes i envia la seva contraoferta esperant saber si és escollit o no. Té com a atributs un identificador personal “Id”, la ubicació des d’on es mou “Ubicació” i el cost que tenen els seus enviaments si no s’inicia cap negociació “CostBase”.  
*Hem definit un costBase donat que quan implementem la negociació el preu del transport podrà variar.*

###      **5.1.3 VenedorExtern** {#5.1.3-venedorextern}

Concepte que representa un venedor extern que interactua amb el sistema per afegir-hi productes o gestionar la venda d’aquests. Té com a atributs un identificador personal “Id” i les dades bancàries on seran enviats els diners de les seves vendes “DadesBancaries”.

###      **5.1.4 ProveïdorPagament** {#5.1.4-proveïdorpagament}

Concepte que representa un proveïdor de pagament que interactua amb el sistema per realitzar el cobrament als usuaris corresponents. Té com a atributs un identificador personal “Id”.

## **5.2 Producte** {#5.2-producte}

Concepte que representa un producte en el sistema. Té com a atributs un identificador personal “id”, un nom “nom”, un preu “preu”, un text en forma de descripció “descr”, una categoria per a ser filtrat “categ”, el nom de la marca a la que pertany “marca” i el seu pes “pes”. És el nucli en la comunicació entre l’usuari des de l’Agent Cercador i l’Agent Compra.

###      **5.2.1 ProducteExtern**

## **5.3 Lot** {#5.3-lot}

Concepte que representa una agrupació logística de productes al sistema. Té com a atributs un identificador personal “id”, l’identificador del centre logístic que el gestiona “centre\_logistic\_id”, l’adreça de destinació comuna “adreça”, la prioritat del lot “prioritat” (heretada de les comandes que conté), la data prevista d'enviament “data\_enviament”, la llista de productes que el formen “productes” i el seu estat de gestió “estat”. És creat i gestionat per l’Agent Centre Logístic.

## **5.4 Comanda** {#5.4-comanda}

Concepte que representa una comanda al sistema. Té com a atributs un identificador personal “idComanda”, l’identificador de l’usuari que la ha realitzat “userid”, els productes que han sigut comprats “llista\_productes”, l’adreça destí on ha de ser enviada “Adreça”, la prioritat donada per l’usuari “prioritat”, l’estat de la comanda “estat”, el preu de la comanda “import\_total” i la data d’entrega estimada segons la prioritat “data\_entrega\_estimada”. Es fa sobre molts Productes i és pagada per un Usuari. És gestionada per l’Agent Compta, per fer el seguiment del pagament i enviament. 

## **5.5 Devolució** {#5.5-devolució}

Concepte que representa una devolució d’un producte per un usuari. Té com a atributs un identificador personal “id”. Es fa sobre un Producte i és tramitada per x.

## **5.6 Feedback** {#5.6-feedback}

Concepte que representa l’opinió i valoració d’un consumidor sobre un article adquirit. Té com a atributs un identificador personal “id”, un text descriptiu amb l'opinió de l'usuari “comentari” i una valoració numèrica sobre la qualitat del producte “puntuacio”. Aquesta entitat és el mecanisme mitjançant el qual l’Usuari dona Feedback per expressar la seva satisfacció. El Feedback avalua un Producte concret i ambdues entitats queden vinculades dins d'una RespostaFeedback.

*En un principi, vam pensar de crear un concepte Suggeriment, però ens vam adonar que les suggerències no son un concepte com a tal, sino el fet de mostrar certs productes amb prioritat en la cerca de productes de l’usuari.*

## **5.7 OfertaTransport** {#5.7-ofertatransport}

Concepte que representa una oferta de transport donada per un Transportista. Té com a atributs la data d’enviament.

## **5.8 CentreLogístic** {#5.8-centrelogístic}

Concepte que representa un centre logístic físic que emmagatzema productes. Té com a atributs un identificador personal “Id” i la ubicació geogràfica on es troba situat “Ubicació”. Aquesta entitat és la responsable de distribuir Lots de productes i s’encarrega de negociar la PeticioTransport amb els agents transportistes per coordinar els enviaments. També té la capacitat de rebre l’Oferta de transport per part de tercers i enviar la RespostaOfertaTransport per formalitzar el servei, a més de rebre l’Avís de ProducteLocalitzat quan un article és identificat correctament dins del seu inventari.

## **5.9 Comunicació** {#5.9-comunicació}

###      **5.10.1 Acció** {#5.10.1-acció}

          **PeticióCerca**  
          La PeticioCerca és l'acció de generar una consulta semàntica mitjançant filtres com text, categ, marca i rangs de preu. Aquests paràmetres es capturen en un graf RDF que defineix els criteris de l'usuari de forma estructurada. Com a resposta, es rep un *ResultatCerca*.

          PeticióCompra  
          Acció que representa fer una petició de compra. Utilitzats per l'Agent Compra per completar les dades d'enviament abans de tancar la comanda. 

          PeticióInfoUsuari  
          Acció que representa fer una petició d’informació a l’usuari. Utilitzats per l'Agent Compra per completar les dades d'enviament abans de tancar la comanda. 

          PeticióAfegirProducteExtern  
          Acció que representa fer una petici  
          PeticióDevolució  
          PeticióFeedback  
          PeticióPagament  
          PeticióTransport  
          Acció que representa fer una petició de transport. El Centre Logístic la genera per negociar amb transportistes externs, enviant el pes total del lot.   
          ProducteLocalitzat

###      **5.10.2 Resposta** {#5.10.2-resposta}

          **RespostaCerca**  
          El ResultatCerca és l'acció que representa la resposta a una petició. Mitjançant la relació mostra, es construeix un graf RDF que agrupa els productes trobats al catàleg. Aquest resultat inclou tota la informació detallada de cada article (nom, preu, marca i descripció).  
*S'ha inclòs un comptador total per facilitar la paginació a la interfície.*

          InfoUsuari  
          Tipus de resposta que representa la resposta a una petició d’informació d’usuari.  
          NegociacióTransport  
          Tipus de resposta que representa la resposta a una petició de transport.  
          RespostaDevolució  
          Tipus de resposta que representa la resposta a una petició de devolució.  
          RespostaFeedback  
          Tipus de resposta que representa la resposta a una petició de feedback.  
          RespostaSuggeriment  
          Tipus de resposta que representa la resposta a una petició de suggeriment.

## 5.3 Atributs i 5.4 Relacions (vocabulari refinat)

L'ontologia utilitza una única convenció `UpperCamelCase` en català per a totes les classes, atributs i relacions. `acl:sender`, `acl:receiver` i `acl:ontology` pertanyen al sobre FIPA-ACL i no formen part de l'ontologia AgentZon.

**Actor**
Manté només actors externs (`Usuari`, `Transportista`, `VenedorExtern`, `Banc`). Els agents desplegats per AgentZon (Cercador, Compra, Centre Logístic, Opinador, Transportista) són elements de desplegament i no classes d'ontologia; comuniquen mitjançant l'envoltori FIPA-ACL.

**Producte**
Atributs: `IdProducte`, `Nom`, `Descripcio`, `Categoria`, `Marca`, `Preu`, `Pes`.

**Comanda**
Atributs: `IdComanda`, `IdUsuari`, `Nom`, `Carrer`, `Ciutat`, `Prioritat`. Relacions: `TeProducte` → `Producte`, `TeDadesEnviament` → `DadesEnviamentUsuari`.

**DadesEnviamentUsuari**
Atributs: `IdUsuari`, `Nom`, `Carrer`, `Ciutat`, `Prioritat`, `MetodePagament`.

**Lot**
Atributs: `IdLot`, `Ciutat`, `Prioritat`, `PesTotal`. Relacions: `TeProducte` → `Producte`, `SobreComanda` → `Comanda`, `AssignatATransportista` → `Transportista`.

**CentreLogistic**
Atributs: `IdCentreLogistic`, `Ciutat`. Distribueix `Lot` i negocia `PeticioTransport` amb cada `Transportista`.

**UbicacioProducte**
Relacions: `SobreProducte` → `Producte`, `UbicatACentre` → `CentreLogistic`.

**PeticioCerca** (subclasse d'`Accio`)
Atributs: `TextConsulta`, `CategoriaConsulta`, `MarcaConsulta`, `PreuMinim`, `PreuMaxim`.

**ResultatCerca** (subclasse de `Resposta`)
Atributs: `TotalResultats`. Relacions: `MostraProducte` → `Producte`, `EsRespostaA` → `PeticioCerca`.

**ProducteLocalitzat** (subclasse d'`Accio`)
Atributs: `IdComanda`, `IdUsuari`, `Ciutat`, `Prioritat`. Relacions: `TeProducte` → `Producte`, `SobreComanda` → `Comanda`.

**PeticioTransport** (subclasse d'`Accio`)
Atributs: `IdLot`, `IdComanda`, `Ciutat`, `Prioritat`, `PesTotal`. Relacions: `SobreLot` → `Lot`, `SobreComanda` → `Comanda`.

**RespostaOfertaTransport** (subclasse de `Resposta`)
Atributs: `IdLot`, `IdComanda`, `IdTransportista`, `NomTransportista`, `Ciutat`, `DataEntrega`, `CostTransport`. Relacions: `SobreLot` → `Lot`, `SobreComanda` → `Comanda`, `AssignatATransportista` → `Transportista`, `EsRespostaA` → `PeticioTransport`.

**PeticioRegistreCompra** (subclasse d'`Accio`)
Atributs: `IdComanda`, `IdUsuari`. Relacions: `SobreComanda` → `Comanda`, `TeProducte` → `Producte`.

**ConfirmacioRegistreCompra** (subclasse de `Resposta`)
Atributs: `IdComanda`. Relacions: `SobreComanda` → `Comanda`, `EsRespostaA` → `PeticioRegistreCompra`.

**HistorialCompra**
Atributs: `IdComanda`, `IdUsuari`. Relacions: `SobreComanda` → `Comanda`, `TeProducte` → `Producte`.

**HistorialCerca**
Atributs: `TextConsulta`, `CategoriaConsulta`, `MarcaConsulta`, `PreuMinim`, `PreuMaxim`, `TotalResultats`. Relacions: `MostraProducte` → `Producte`.

`Pes` és un atribut de `Producte`; `PesTotal` és l'agregació pertanyent a `Lot` i a `PeticioTransport`.

Hem de parlar: l’ag compra quan li diu al CL que ha localitzat un producte:

- Li envia lid de lusuari, ladreça detsi, la data denviament..????? els diners????  
- perq despres quan aquest envia el lot amb el producte, li ha de dir al ag bancari que li cobra a tal persona tanta pasta no? ho vam fer aixi? 

Una posibilidad es que generéis de manera aleatoria una base de datos de productos. Una vez definida la ontología no es difícil el hacer un programa que vaya generando instancias de las diferentes clases dando valores aleatorios a los diferentes campos dentro de los rangos que tengan sentido. En el repositorio de código dentro de la carpeta Examples/InfoSources tenéis el script RandomInfo.py que os puede servir de ejemplo.

6. # **Implementació d’agents** {#implementació-d’agents}

**Què cal documentar?**  
Detalle sobre la implementación de los agentes a partir del diseño detallado, como habéis plasmado el diseño detallado en los agentes que habéis implementado, qué agentes extra habéis incluido (si hay alguno que no estuviera en el diseño detallado) y por qué lo habéis incluido, que cambios habéis incluido sobre el diseño detallado inicial. Detalle sobre qué hacen los agentes y cómo lo hacen

7. # **Elements del nivell avançat de la pràctica** {#elements-del-nivell-avançat-de-la-pràctica}

**Què cal documentar?**  
Si habéis hecho el nivel avanzado de la práctica, qué elementos habéis incluido y cómo los habéis implementado. Estos elementos han de aparecer también en el diseño.

1. Negociación compleja entre el centro logístico y agentes de transporte de manera que, al recibir las ofertas de envío, el centro logístico envía a los agentes de transporte una contra oferta con un precio ligeramente inferior a la oferta mínima. Los agentes de transporte pueden replicar aceptando la contra oferta, proponiendo otra inferior a su oferta inicial, pero mayor que la contra oferta o rechazándola. Si nadie acepta la oferta, se asigna el envío al transportista con la primera oferta más barata y si alguno acepta o propone una contra oferta, se asigna a la repuesta más barata (en caso de empate se decide al azar).  
2. Los pedidos pueden incluir productos que están en diferentes centros logísticos, se distribuye a cada uno de ellos los productos que les tocan y cada uno de ellos escoge un agente de transporte en su área geográfica. Aquí el usuario recibe múltiples informaciones sobre fecha de entrega y transportista.  
3. Implementación de la petición de valoraciones a los usuarios después de un tiempo de que han recibido sus productos y la recomendación periódica proactiva de productos a partir del historial de compra y búsquedas.

# 

8. # **Tasques amb nota extra** {#tasques-amb-nota-extra}

**Què cal documentar?**  
Si habéis hecho alguna de las tareas que dan nota extra, explicad todo el proceso, por ejemplo, si os habéis puesto de acuerdo con otro grupo para compartir un agente, explicad como habéis decidido la parte de la ontología común.

- Ponerse de acuerdo con otro grupo en la ontología de los agentes de transporte y utilizar también un agente del otro grupo en la demostración de la práctica.  
- Hacer alguna más extensiones de las que se proponen para el nivel avanzado

9. # **Jocs de prova** {#jocs-de-prova}

**Què cal documentar?**  
Definición de los juegos de prueba que muestran el funcionamiento de la práctica explicando cómo los habéis escogido y por qué (esto es de la competencia). Estos juegos de prueba los deberéis mostrar en la entrega de la práctica (y han de funcionar)

10. # **Distribució de la feina** {#distribució-de-la-feina}

**Què cal documentar?**  
Descripción detallada de la planificación del trabajo incluyendo la división de las tareas entre los miembros del grupo. La planificación ha de ser la realidad, no ciencia ficción.

**Conjuntament**  
Per a la primera part del projecte, és a dir, el disseny de les dues primeres fases de la metodologia Prometheus (Especificació del sistema i Disseny arquitectònic), vam treballar els tres membres de l’equip conjuntament, ja que la presa de decisions requeria que tots hi estiguéssim d’acord. A més, des d’un inici ens vam adonar que cadascú podia interpretar els objectius de manera diferent; escoltar diferents punts de vista i discutir-los ens va ajudar a aconseguir un disseny molt més robust i precís.  
Després de la primera entrega i de rebre el feedback del professor, vam dedicar un cap de setmana a corregir i millorar el nostre disseny conjuntament. 

**Àngela Buxó**  
De cara a la segona fase de la metodologia, mentre els meus companys treballaven en el disseny detallat, jo em vaig encarregar del disseny de la nostra ontologia amb Protégé. Tot i així, la comunicació entre els tres va ser essencial tant per a decisions clau relacionades amb l'ontologia com per al disseny detallat, assegurant que el vocabulari dissenyat cobrís totes les necessitats dels agents. 

**Paula Mas**

**Pol Montanera**

Especificació del Sistema: Tots  
Disseny arquitectònic: Tots  
Disseny detallat: tots  
Ontologia:  
Implementació:

- Agent Cercador: angi  
- Agent Compra: mount  
- Agent Cobrador  
- Agent Centre Logístic: mount  
- Agent Retornador  
- Agent Opinador  
- Agent Venedor Extern  
- Agent Extern Usuari  
- Agent Extern Banc  
- Agent Extern Transportista  
- Agent Venedor Extern  
- Protocols: paula i mount  
- Tests

11. # **Resultats i conclusió** {#resultats-i-conclusió}

**Què cal documentar?**  
Evaluación crítica de los resultados obtenidos en la práctica y consideraciones sobre los límites de vuestra solución (competencia).

**Info a tenir en compte**

- [x] ~~Diseño del sistema usando la metodología Prometheus actualizado con los comentarios de la primera y segunda entrega. Esto incluye también la fase de diseño detallado.~~  
- [ ] Descripción de la ontología/ontologías que habéis diseñado para vuestra práctica describiendo las decisiones que habéis tomado. Básicamente, tenéis que contar qué habéis representado, como habéis decidido lo que debíais representar, como lo habéis representado (clases, atributos relaciones) y donde habéis usado esa representación (qué agentes/protocolos la usan y cómo)  
- [ ] Detalle sobre la implementación de los agentes a partir del diseño detallado, como habéis plasmado el diseño detallado en los agentes que habéis implementado, qué agentes extra habéis incluido (si hay alguno que no estuviera en el diseño detallado) y por qué lo habéis incluido, que cambios habéis incluido sobre el diseño detallado inicial. Detalle sobre qué hacen los agentes y cómo lo hacen  
- [ ] Si habéis hecho el nivel avanzado de la práctica, qué elementos habéis incluido y cómo los habéis implementado. Estos elementos han de aparecer también en el diseño.  
- [ ] Si habéis hecho alguna de las tareas que dan nota extra, explicad todo el proceso, por ejemplo, si os habéis puesto de acuerdo con otro grupo para compartir un agente, explicad como habéis decidido la parte de la ontología común.  
- [ ] Definición de los juegos de prueba que muestran el funcionamiento de la práctica explicando cómo los habéis escogido y por qué (esto es de la competencia). Estos juegos de prueba los deberéis mostrar en la entrega de la práctica (y han de funcionar)  
- [ ] Descripción detallada de la planificación del trabajo incluyendo la división de las tareas entre los miembros del grupo. La planificación ha de ser la realidad, no ciencia ficción.  
- [ ] Evaluación crítica de los resultados obtenidos en la práctica y consideraciones sobre los límites de vuestra solución (competencia).