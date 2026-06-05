# Per aquesta entrega

# 

# 

**DOCUMENTACIÓ**

# 

**Plataforma de serveis i agents intel·ligents**   
**per gestionar una empresa global de comerç electrònic**

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

[Registre de transportistes	15](#registre-de-transportistes)

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

[5.1 Actor	24](#5.1-actor)

[5.1.1 Usuari	24](#5.1.1-usuari)

[5.1.2 Transportista	24](#5.1.2-transportista)

[5.1.3 VenedorExtern	24](#5.1.3-venedorextern)

[5.1.4 Banc	24](#heading=h.jaz8y3u42wq2)

[5.2 Producte	24](#5.2-producte)

[5.2.1 Producte Intern	25](#5.2.1-producte-intern)

[5.2.1 ProducteExtern	25](#5.2.1-producteextern)

[5.3 Lot	25](#5.3-lot)

[5.4 Comanda	25](#5.4-comanda)

[5.5 Devolució	25](#5.5-devolució)

[5.6 Feedback	25](#5.6-feedback)

[5.7 Recomanació	25](#5.7-recomanació)

[5.8 CentreLogístic	26](#5.8-centrelogístic)

[5.9 Comunicació	26](#5.9-comunicació)

[5.9.1 Acció	26](#5.9.1-acció)

[5.9.2 Resposta	27](#5.9.2-resposta)

[**6\. Implementació d’agents	29**](#implementació-d’agents)

[6.1 Agent Cercador	29](#6.1-agent-cercador)

[6.2 Agent Compra	29](#6.2-agent-compra)

[6.3 Agent Centre Logístic	30](#6.3-agent-centre-logístic)

[6.4 Agent Opinador	30](#6.4-agent-opinador)

[6.5 Agent Directory	31](#6.5-agent-directory)

[6.6 Agent Centre Logístic	31](#6.6-agent-centre-logístic)

[6.7 Agent Retornador	31](#6.7-agent-retornador)

[6.8 Agent Cobrador	32](#6.8-agent-cobrador)

[**7\. Elements del nivell avançat de la pràctica	33**](#elements-del-nivell-avançat-de-la-pràctica)

[7.1 Servei de registre per agents de transport	33](#7.1-servei-de-registre-per-agents-de-transport)

[7.2 Negociació complexa entre centre logístic i agents de transport	34](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport)

[7.3 Productes a diferents centres logístics	35](#7.3-productes-a-diferents-centres-logístics)

[**8\. Tasques amb nota extra	36**](#tasques-amb-nota-extra)

[8.1 Petició de valoracions	36](#8.1-petició-de-valoracions)

[**9\. Distribució de la feina	38**](#distribució-de-la-feina)

[**10\. Resultats i conclusió	39**](#resultats-i-conclusió)

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

Quan un producte requereix logística externa, el sistema omet el circuit de magatzems de la plataforma. La responsabilitat de l'enviament es delega completament al venedor, que s'encarrega de la seva pròpia distribució i de notificar els canvis d'estat de l'enviament a la plataforma. 

	**Cobrar compra**

El procés de cobrament de la comanda es realitza segons el mètode de distribució del producte. Si el producte és gestionat per la plataforma, el sistema processa el cobrament a l'usuari de forma automàtica en el moment en què el magatzem expedeix i confirma la sortida de la comanda. Si és propietat d’un venedor extern, el sistema tramita el pagament directament durant el procés de validació de la compra a la plataforma.

### **Gestionar negociació d’enviament** {#gestionar-negociació-d’enviament}

La negociació de l'enviament dels lots amb les empreses de transport s'activa de manera dinàmica. El procés comença automàticament quan un lot de productes s'ha completat i està preparat per sortir del magatzem, o bé es pot llançar sota demanda per part dels administradors del sistema.

### **Retornar productes** {#retornar-productes}

El procés de devolució s'executa de manera directa. Quan un usuari sol·licita la devolució (permetent agrupar diferents comandes), si la petició compleix la política, s'aprova automàticament i s'ordena el reemborsament dels diners de forma immediata, sense esperar a circuits de recepció física de la mercaderia al magatzem. 

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

Per assolir l'objectiu d'enviar la compra, el sistema segueix una seqüència de subobjectius organitzats que comencen per localitzar el producte per verificar la disponibilitat de l'estoc, seguit de confirmar la localització per bloquejar l'estoc seleccionat, assignar les dades d'enviament per vincular el producte a un lot i a un transportista, i finalment confirmar l'enviament per registrar la sortida física del producte. 

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

El sistema ha de consultar les ofertes dels transportistes disponibles i seleccionar aquell que ofereixi les millors condicions segons els criteris establerts. El sistema defineix un preu base inicial com a oferta de sortida, estableix una contraoferta equivalent al cent deu per cent del preu base i finalment aplica un sostre màxim del cent quinze per cent, la qual cosa permet rebutjar automàticament qualsevol oferta que superi aquest llindar. 

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

Aquest rol s’encarrega de la gestió de productes dins de cada magatzem. S’activa quan, en fer una comanda, un dels productes es troba al magatzem del cap. Té com a objectiu assignar els productes del magatzem a lots (segons la ciutat de destí i prioritat d’entrega). Com a resultat, fa l’acció d'agrupar els productes en lots.

*Hem decidit separar aquest rol del “Negociador d’enviament” perquè creiem que agrupar els productes ha de ser independent dels transportistes, tot i que posteriorment compartiràn agent, els considerem dos rols diferents.*

### 

### **Negociador d’enviament** {#negociador-d’enviament}

Aquest rol s’encarrega de dur a terme la negociació amb els transportistes, proposant l’enviament d’un cert nombre de paquets (per pes) a una ciutat destí i amb un termini màxim d’entrega. Un cop els diferents transportistes responen amb les propostes, el negociador escull el més adequat. La percepció d’aquest rol és el transcurs d’un cert temps determinat, cada 3 hores. L’objectiu associat és la gestió de la negociació de l’enviament dels lots, i com a resultat, l’acció d’haver escollit un transportista junt amb les dades d’entrega.

### **Gestor de devolucions** {#gestor-de-devolucions}

Aquest rol s’encarrega del procés de devolució d’un producte defectuós, equivocat o que no satisfà l’usuari. Com a percepció, s’activa quan una devolució ha estat acceptada. Té l’objectiu de gestionar aquesta devolució, i dur a terme les accions de comunicar a l’usuari les dades de la devolució i tornar-li els diners. 

### **Validador de devolucions** {#validador-de-devolucions}

Aquest rol s’encarrega de validar una devolució que un usuari ha demanat. La seva funció és verificar que la sol·licitud correspongui estrictament a un dels 3 motius recollits per la plataforma. La regla dels 15 dies és una condició secundària que només s'avalua si el motiu és vàlid. Les peticions per motius aliens o arbitraris es deneguen directament sense comprovar els terminis. El rol s’activa quan l’usuari fa una petició de devolució. Els objectius són processar la petició de devolució i si és el cas, denegar la devolució. Com a acció, comunica la decisió final sobre la devolució a l’usuari.

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

### **Registre de transportistes** {#registre-de-transportistes}

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

- *Pla afegir info producte extern a la BD*. S’activa en rebre un missatge de l’agent Venedor Extern amb dades d’un nou producte. L’agent procedeix a emmagatzemar-lo a la base de dades d’informació de productes i envia un missatge de confirmació de registre correcte.

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

- *Pla delegar registre compra*. Un cop es formalitza correctament el pagament, l'Agent Compra executa de forma directa el pla de registre de la comanda enviant un missatge de petició de registre cap a l'Agent Opinador, el qual respondrà un cop guardat el registre. 

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

- *Pla de compliment de devolució*. S’inicia amb una petició de devolució de l’usuari. L’agent construeix la petició a partir dels productes seleccionats i el motiu indicat i per a cada comanda afectada, es comunica amb l’Agent Opinador per comprovar si els productes sol·licitats compleixen la política de devolució (motius acceptats i termini de 15 dies). 

- Si la sol·licitud no és acceptada (totalment), l’agent informa l’usuari del motiu.  
- Si és acceptada (total o parcialment), el mateix pla invoca successivament el pla de retorn de diners per a cada lot de reemborsament (agrupat per comanda). En finalitzar els reemborsaments, registra un resum de la devolució i retorna a l’usuari la decisió amb l’import reemborsat i l’estat (RETORNAT o PARCIAL).

Per altra banda, es disposa de la capacitat de *Gestionar retorn de diners*, la qual es basa en un pla.

- *Pla de retorn.* S’activa des del pla de compliment quan la devolució ha estat acceptada. Per a cada lot,envia a l’Agent Cobrador la PeticioRetornDiners i rep la confirmació. El Cobrador executa el reemborsament i registra cada lot com a devolució. 

## **4.6 Agent Opinador** {#4.6-agent-opinador}

L’agent Opinador té tres capacitats.

En primer cas, la capacitat *Gestionar feedback* es basa en dos plans.

- *Pla demanar feedback*. S’activa per la periodicitat establerta i s’encarrega de sol·licitar la valoració directament a l’usuari.

- *Pla registrar feedback*. S’activa en rebre la resposta de l’usuari i emmagatzema la informació a la base de dades.

En segon cas, la capacitat *Crear suggeriments* consta d’un sol pla.

- *Pla Crear suggeriments.* S’activa de forma periòdica segons el calendari de recomanacions. Llegeix les dades de l'historial de cerques i de compres per generar propostes personalitzades i informa a l’usuari.

Per últim, la capacitat *Gestionar consultes BD* es basa en dos plans.

- *Pla Registre de compra*. S’activa quan l’Agent Compra informa d'una compra realitzada per tal d'incorporar-la a l’historial de compres. S’emmagatzema a la BD d’Historial de compres i s’envia confirmació.

- *Pla Consulta de criteris de devolució*. S’activa quan l’Agent Retornador fa una petició. L’agent llegeix l’historial de compres per verificar si es compleixen els criteris i envia la resposta corresponent.

## **4.7 Agent Venedor Extern** {#4.7-agent-venedor-extern}

L’agent Venedor extern té una capacitat.

*Afegir producte extern* es basa en quatre plans.

- *Pla afegir producte extern a la BD*. S’activa quan rep la percepció nou producte extern. Aleshores, amb les dades rebudes, per una banda emmagatzema la informació pertinent a les dues bases de dades, Responsable enviament productes i Ubicacions productes. Un cop acabat, envia un missatge de confirmació al Pla comunicar nou producte afegit.

- *Pla afegir info producte extern.* S’activa quan rep la percepció nou producte extern. Envia les dades rebudes a l’Agent Cercador per emmagatzemar-les i en rep confirmació. Un cop acabat, envia un missatge de confirmació al Pla comunicar nou producte afegit.

- *Pla delegar afegir dades bancàries del venedor extern.* S’activa quan rep la percepció nou producte extern. Aleshores envia les dades bancàries a l’Agent Cobrador perquè les emmagatzemi, i rep confirmació d’aquest. Un cop acabat això, envia un missatge de confirmació al Pla comunicar nou producte afegit.

- Pla comunicar nou producte afegit. S’activa en rebre els tres missatges de confirmació. Envia la confirmació del producte registrat correctament al Venedor extern.

# 

5. # **Descripció de l’ontologia** {#descripció-de-l’ontologia}

Per definir el coneixement i el vocabulari que els agents d’AgentZon han de compartir per poder comunicar-se i entendre's, hem dissenyat la nostra pròpia ontologia. L'objectiu d'aquesta és modelar formalment els conceptes del domini i el contingut dels missatges intercanviats.

A continuació es descriuen els conceptes, relacions i atributs de l’ontologia Agentzon.

### **5.1 Actor** {#5.1-actor}

###      **5.1.1 Usuari** {#5.1.1-usuari}

Concepte que representa un usuari que pot interactuar amb el sistema, fent una cerca de productes, comprant-ne, donant feedback o sol·licitant una devolució. Té com a atributs un identificador personal “*idUsuari*” i el seu nom personal “*Nom*”. A nivell de relacions, l'Usuari és l'origen de les peticions de compra, cerca i feedback que interactuen amb la resta del sistema. 

*Hem decidit que els atributs “Adreca” i “DadesBancaries” pertanyin directament al concepte “Comanda” i no a “Usuari” ja que comandes diferents d’un mateix usuari poden tenir adreçes de lliurament i/o mètodes de pagament diferents.*

###      **5.1.2 Transportista** {#5.1.2-transportista}

Concepte que representa un transportista que rep ofertes per lliurar comandes i envia la seva contraoferta esperant saber si és escollit o no. Té com a atributs un identificador personal *“Id*” i el cost que tenen els seus enviaments si no s’inicia cap negociació *“CostBase*”. Està vinculat a la logística mitjançant la relació AssignatATransportista, que el connecta amb els Lots que té sota la seva responsabilitat.

*Hem definit un costBase donat que quan implementem la negociació el preu del transport podrà variar.*

###      **5.1.3 VenedorExtern** {#5.1.3-venedorextern}

Concepte que representa un venedor extern que interactua amb el sistema per afegir-hi productes o gestionar la venda d’aquests. Té com a atributs un identificador personal “*Id*” i les dades bancàries on seran enviats els diners de les seves vendes *“DadesBancaries*”. Aquest actor és el responsable d'iniciar l'acció d'AltaProducteExtern per introduir nous articles al catàleg.

### **5.2 Producte** {#5.2-producte}

Concepte que representa un producte en el sistema. Té com a atributs un identificador personal IdProducte, un nom Nom, un preu Preu, un text en forma de descripció Descripcio, una categoria per a ser filtrat Categoria, el nom de la marca a la que pertany Marca i el seu pes Pes. És el nucli en la comunicació entre l’usuari des de l’Agent Cercador i l’Agent Compra. Està UbicatACentre, vinculant-se amb el CentreLogístic on s'emmagatzema físicament. És l'objecte de la relació TeProducte quan forma part d'una Comanda o d'un Lot i també és l'objectiu de la relació SobreProducte en accions de compra, feedback, devolucions i recomanacions. 

###      **5.2.1 Producte Intern** {#5.2.1-producte-intern}

###      **5.2.1 ProducteExtern** {#5.2.1-producteextern}

Concepte que representa un producte proporcionat per un venedor extern. Té com a atributs, els mateixos que Producte i, un identificador propi respecte el venedor extern “SkuExtern”, un boolea indicant si la responsabilitat d’enviament és externa “RequereixLogisticaExterna” i la data en la que es va registrar al sistema “DataAlta”. Manté les mateixes relacions que el producte.

### **5.3 Lot** {#5.3-lot}

Concepte que representa una agrupació logística de productes al sistema. Té com a atributs un identificador personal “idLot”, la ciutat de destinació comuna “Ciuta*t*”, la prioritat del lot “*prioritat*” (heretada de les comandes que conté), la data prevista d'enviament “*data\_enviament*”, la llista de productes que el formen “*productes*”, el seu pes “PesTotal” i el seu estat de gestió “*estat*”. És creat i gestionat per l’Agent Centre Logístic. Utilitza la relació TeProducte per llistar els Productes que conté. Es vincula a un professional mitjançant la relació AssignatATransportista.  És el centre de la relació SobreLot, utilitzada per les peticions de transport i confirmacions d'enviament.

### **5.4 Comanda** {#5.4-comanda}

Concepte que representa una comanda al sistema. Té com a atributs un identificador personal “*idComanda*”, l’identificador de l’usuari que la ha realitzat “*userid*”, els productes que han sigut comprats “*llista\_productes*”, l’adreça destí on ha de ser enviada “*Adreça*”, la prioritat donada per l’usuari “*prioritat*”, l’estat de la comanda “*estat*”, el preu de la comanda “*import\_total*” i la data d’entrega estimada segons la prioritat “*data\_entrega\_estimada*”. Es relaciona amb els productes mitjançant la propietat TeProducte. A més, és l'objecte de la relació SobreComanda en l'acció de registre de compra.

### **5.5 Devolució** {#5.5-devolució}

Concepte que representa una devolució d’un producte per un usuari. Té com a atributs un identificador personal “idDevolucio”, l’estat del tràmit “estat” i el motiu pel que l’usuari ha començat el tràmit “MotiuDevolucio”. Es fa sobre un Producte. Es vincula formalment amb l'article retornat mitjançant la relació SobreProducte.

### **5.6 Feedback** {#5.6-feedback}

Concepte que representa l’opinió i valoració d’un consumidor sobre un article adquirit. Té com a atributs un identificador personal “*id*”, un text descriptiu amb l'opinió de l'usuari “*comentari*” i una valoració numèrica sobre la qualitat del producte “*puntuacio*”. El Feedback s'avalua i es vincula a un Producte concret mitjançant la relació SobreProducte.

### **5.7 Recomanació** {#5.7-recomanació}

Concepte que representa un conjunt de suggeriments personalitzats per a un usuari. Aquesta entitat es vincula amb els articles suggerits a través de la relació SobreProducte. El sistema l'identifica com el resultat de l'acció de l'agent que GeneraRecomanacio.

### **5.8 CentreLogístic** {#5.8-centrelogístic}

Concepte que representa un centre logístic físic que emmagatzema productes. Té com a atributs un identificador personal “*Id*” i la ubicació geogràfica on es troba situat “*Ubicació*”. És el destí de la relació UbicatACentre, on es recullen tots els Productes que hi ha en inventari.

**5.9 Pagament**

Concepte que representa l’acte de transacció econòmica vinculat a una adquisició dins del sistema. Té com a atributs un identificador personal “IdPagament” , l’import total de l’operació “ImportPagament” , el mètode de pagament triat (com ara targeta o transferència) “MetodePagament” i l’estat actual del tràmit “Estat”. Aquesta entitat es vincula directament amb els articles comprats mitjançant la relació SobreProducte.

### **5.9 Comunicació** {#5.9-comunicació}

####     **5.9.1 Acció** {#5.9.1-acció}

**AltaProducteExtern** 

L’AltaProducteExtern és l'acció de sol·licitar afegir d'un producte d'un venedor extern amb ID extern, descripció i preu. Com a resposta, es rep un *ConfirmacioRegistreCompra*. És utilitzada pel Venedor Extern quan es comunica amb l'Agent Cercador.

**ConfirmacioEnviament**

La ConfirmacioEnviament és l’acció que comunica que un lot o producte ja ha estat enviat i pot activar el cobrament associat de la comanda, amb atributs com CostTransport, DataEntregaDefinitiva, IdTransportista i NomTransportista. Com a resposta, es rep una *ConfirmacioPagament*. És utilitzada per l’Agent Centre Logístic quan es comunica amb l’Agent Cobrador.

**EleccioTransportista**

L’EleccioTransportista és l’acció de seleccionar formalment el proveïdor per a un enviament concret, especificant atributs com IdComanda, IdLot, IdTransportista, NomTransportista, CostTransport, Ciutat i DataEntregaDefinitiva. És utilitzada per l’Agent Centre Logístic per comunicar al transportista seleccionat que la seva oferta ha estat acceptada i per fixar les condicions finals del servei.

**PeticioCerca**

La PeticioCerca és l'acció de generar una consulta semàntica mitjançant filtres com text, categoria, marca i rangs de preu. Com a resposta, es rep un *ResultatCerca*. És utilitzada per l'usuari quan es comunica amb l'Agent Cercador per cercar productes amb paràmetres específics.

**PeticioCompra**

És l'acció d'iniciar la compra d'un conjunt de productes. Té com a atributs directes l'IdUsuari i el MetodePagament. Es vincula amb una estructura de comanda incrustada mitjançant la relació SobreComanda. Com a resposta, es rep un ResultatCompra. És utilitzada per l'usuari (interfície) quan es comunica amb l'Agent Compra.

**PeticioDevolució**

La PeticioDevolució és l'acció de sol·licitar la devolució d’un producte indicant ordre, identificador del producte, quantitat i motiu. Com a resposta, es rep un *ResultatDevolució*. És utilitzada per l'usuari quan es comunica amb l'Agent Retornador per sol·licitar la devolució d'un producte.

**PeticioEnviamentExtern**

La PeticioEnviamentExtern és l’acció de sol·licitar al venedor extern la gestió logística d’un producte amb enviament delegat, incloent dades bàsiques de comanda i destí. És utilitzada per l’Agent Compra quan es comunica amb l’Agent Venedor Extern.

**PeticioFeedback**

La PeticioFeedback és l'acció de sol·licitar l’opinió sobre un producte a un usuari, incloent comentari i identificadors (usuari, ordre, producte). Com a resposta, es rep un *ResultatFeedback*. És utilitzada per l'Agent Opinador quan es comunica amb l'usuari per sol·licitar la valoració dels productes comprats.

**PeticioPagament**

La PeticioPagament és l'acció de demanar processar un pagament especificant import, moneda, mètode (targeta, transferència), i dades de facturació. Com a resposta, es rep un *ResultatPagament*. És utilitzada per l'Agent Compra quan es comunica amb l'Agent Cobrador per processar el pagament d'una compra.

**PeticioRegistreCompra**

És l'acció de demanar a l'Agent Opinador que registri una comanda a l'historial. Conté els atributs directes IdComanda i IdUsuari, apunta a la comanda mitjançant la relació SobreComanda i llista de forma explícita tots els articles adquirits mitjançant la relació SobreProducte. Com a resposta, es rep un ConfirmacioRegistreCompra.

**PeticioRegistreDadesBancariesUsuari**

**PeticioRegistreDadesBancariesVenedorExtern**

**PeticioRetornDiners**

**PeticioTransport**

La PeticioTransport és l’acció de sol·licitar l'enviament d'una comanda amb ordre, destinació, mètode d'enviament i preferències. Com a resposta, es rep un *ResultatTransport*.És utilitzada per l'Agent Centre Logístic quan es comunica amb els Transportistes per negociar l'enviament de lots.

**ProducteLocalitzat**

ProducteLocalitzat és l’acció que indica la localització d'un producte en un centre amb identificador de producte a enviar, data prevista i ubicació destí. Com a resposta, es rep una *ConfirmacioLocalitzacio*. És utilitzada per l'Agent Compra quan comunica a l'Agent Centre Logístic que un producte ha estat localitzat i assignat a un lot per a l'enviament.

 

####     **5.9.2 Resposta** {#5.9.2-resposta}

**ConfirmacioAltaProducteExtern**

Resposta que confirma que un producte extern ha estat registrat correctament al catàleg de la plataforma. És enviada per l'Agent Cercador quan ha emmagatzemat les dades del producte a la base de dades d'informació de productes.

**ConfirmacioLocalitzacio**

Concepte que representa la confirmació de reserva i localització de productes associats a un lot logístic concret per a una comanda. Té com a atributs l'IdComanda, l'IdLot, l'Estat, la Ciutat de destí i la DataEntrega prevista per a aquest tram. Es vincula amb la comanda mitjançant SobreComanda, amb el lot mitjançant SobreLot i amb els productes físics concrets mitjançant TeProducte.

**ConfirmacioPagament**

Resposta que indica que el pagament ha estat processat correctament i la transacció ha estat validada. És enviada per l'Agent Compra o a l'usuari confirmant que els diners han estat cobrats.

**ConfirmacioRegistreCompra**

Resposta que confirma que la compra ha estat registrada correctament a l'historial de compres de l'usuari. És enviada per l'Agent Opinador a l'Agent Compra perquè sàpiga que les dades de la compra ja estan disponibles.

**ConfirmacioRegistreDadesBancaries**

**ConfirmacioRetornDiners**

**DadesEnviament**

Resposta que comunica que un lot ja té un transportista assignat i una data definitiva d’entrega, però que encara no ha estat enviat. Inclou atributs com IdComanda, IdLot, IdTransportista, NomTransportista, CostTransport, Ciutat i DataEntregaDefinitiva. És enviada per l’Agent Centre Logístic a l’Agent Compra perquè aquest pugui actualitzar l’estat de la comanda i informar l’usuari dels detalls definitius de l’enviament.

**ResolucioDevolucio**

Resposta que comunica la decisió final sobre una petició de devolució (acceptada o denegada) amb les instruccions corresponents. És enviada per l'Agent Retornador a l'usuari especificant el motiu de l'acceptació o denegació.

**RespostaFeedback**

Resposta que confirma que el feedback proporcionat per l'usuari ha estat registrat correctament al sistema. És enviada per l'Agent Opinador a l'usuari com a confirmació del registre de la seva valoració.

**RespostaOfertaTransport**

Resposta que conté les ofertes dels transportistes amb preus i dates d'entrega per a un lot. És enviada pels Transportistes a l'Agent Centre Logístic perquè seleccioni la millor opció de transport.

**RespostaRecomanacio**

**ResultatCerca**

Resposta que conté els productes trobats segons els criteris de cerca especificats per l'usuari. És enviada per l'Agent Cercador a l'usuari amb la informació detallada de cada producte localitzat (nom, preu, marca, descripció).

**ResultatCompra**

Resposta enviada per l'Agent Compra com a retorn inicial a una PeticioCompra. Conté l'IdComanda, l'Estat global i la DataEntrega estimada. Es vincula directament a l'objecte central mitjançant SobreComanda i inclou una llista de nodes de tipus ConfirmacioLocalitzacio (un per cada lot reservat als magatzems).

To-Do ontologia \<-\> codi

- [ ] Al codi no fem servir producte intern, s’hauria de fer servir.  
- [ ] Eliminar el concepte Pagament.  
- [ ] Revisar que models no es guardin ids d’altres models, fer amb relacions

      # 

6. # **Implementació d’agents** {#implementació-d’agents}

Aquest apartat descriu com s’han materialitzat al codi els agents definits al disseny detallat. Abans d’entrar en cada agent, convé explicar la seva estructura general:

1. Globals de runtime (AGENT, DIRECTORY\_AGENT, comptadors de missatge, rutes als fitxers .ttl).  
2. configure\_runtime(settings, …): inicialitza aquest estat de forma explícita perquè la bateria de tests pugui muntar l’agent sense xarxa real.  
3. Plans (pla\_…): cada pla correspon a una capacitat del diagrama Prometheus de l’Entrega 2; el nom al codi ha de poder traçar-se al diagrama.  
4. @app.route("/comm"): entrada ACL: es parseja el missatge, es comprova el performative (request, inform, confirm, not-understood) i es despatxa segons el \`rdf:type\` del contingut.  
5. @app.route("/iface") (quan cal): interacció amb l’usuari; en molts casos l’usuari s’identifica per adreça IP (get\_client\_ip\_from\_request), no per un login.  
6. main(): registre al Directory (excepte el propi Directory) i arrencada amb *serve\_agent*, que llança un procés auxiliar per al registre i executa Flask en paral·lel.

Els conceptes intercanviats són classes i propietats de l’ontologia (*PeticioCerca, PeticioPagament, ResolucioDevolucio*, …) i quan un agent no entén una petició, respon *not-understood*. Per últim, les dades es concentren a data/ i es llegeixen o escriuen des dels serveis.

## **6.1 Agent Cercador** {#6.1-agent-cercador}

A través del canal d’entrada /iface, l’usuari veu el formulari de cerca i, si la resta d’agents s’han donat d’alta al Directory, botons per obrir suggeriments o feedback (Agent Opinador) i devolucions (Agent Retornador). En enviar el formulari, l’agent construeix internament una *PeticioCerca* a partir dels camps (text, categoria, marca, rang de preus), executa *pla\_de\_cerca* filtrant *productes.ttl*, registra criteris i resultats a l’historial associant-los a la IP del client, i activa *pla\_de\_presentacio*, que renderitza la llista i un formulari per marcar productes i continuar la compra.

## **6.2 Agent Compra** {#6.2-agent-compra}

L’usuari inicia la compra des de la interfície web (/iface) o bé mitjançant una PeticioCompra per /comm. En tots dos casos s’executa el processament de la comanda de forma paral·lela i asíncrona. A la interfície, l’usuari (identificat per IP) afegeix productes al cabàs, prem comprar i visualitza el resum del procés en temps real, mentre que internament es generen fils d'execució independents mitjançant un ThreadPoolExecutor per gestionar cada sol·licitud sense bloquejar el sistema.

L'Agent Compra normalitza la petició i valida l'estoc consultant els centres logístics via Directory. Després, calcula els imports i sol·licita el cobrament de forma asíncrona a l'agent Cobrador (PeticioPagament amb sentit de cobrament) mitjançant una crida ACL (request). Si el Cobrador confirma la transacció, l'Agent Compra distribueix les ordres d'enviament de manera segmentada: demana la preparació dels lots interns als centres logístics propis (PeticioEnviamentIntern) i delega la logística externa a l'agent Transportista (PeticioEnviamentExtern). En paral·lel, envia una PeticioRegistreCompra a l'Opinador perquè persisteixi el node `Comanda` complet a historial\_compres.ttl; el seguiment viu de la compra continua a seguiment\_enviaments.ttl i es mostra el ResultatCompra final a l’usuari.

*Un canvi respecte al disseny inicial ha estat que, mentre que al principi es demanava manualment un identificador (ID) a l’usuari per poder iniciar el procés de compra i carregar el seu perfil, ara tot es realitza de manera totalment transparent utilitzant la seva adreça IP com a identificador a través de la funció get\_client\_ip\_from\_request.* 

## **6.3 Agent Centre Logístic** {#6.3-agent-centre-logístic}

L’agent centre logístic s’encarrega de coordinar l’agrupació de productes en lots i de negociar el transport necessari per a les comandes confirmades, tot i així, no hi ha un únic Centre Logístic, sino varis repartits per algunes comarques de Catalunya ([apartat 7.3](#7.3-productes-a-diferents-centres-logístics)). El procés s'activa quan l'agent rep una petició amb la llista de productes localitzats, la ciutat de destinació i la prioritat de l'enviament. Un cop processada aquesta informació, l’agent executa el pla per assignar cada producte a un lot específic, calculant el pes total i assegurant que els productes agrupats comparteixin condicions d’enviament.  
Posteriorment, s'inicia la fase de negociació externa. Mitjançant una consulta simultània a diferents agents de transport s’inicia una negociació complexa ([apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport))  i, un cop obtingudes totes les respostes, l'agent executa un pla de selecció per escollir la millor oferta i retorna els detalls de l'enviament a l'Agent Compra. 

## **6.4 Agent Opinador** {#6.4-agent-opinador}

L’usuari interacciona amb l’Opinador des de la interfície web (/iface) o bé mitjançant missatges de l'ontologia AZON per /comm. A la interfície, l'usuari visualitza el dashboard amb les seves estadístiques, un llistat de productes comprats pendents de valorar i un bloc de recomanacions personalitzades generades pel pla\_de\_creacio\_de\_suggeriments, el qual llegeix de productes.ttl, historial\_cerques.ttl i historial\_compres.ttl amb un límit ajustable d'entre 1 i 10 productes. 

Quan l’usuari envia una valoració des del formulari, s’executa el pla\_de\_registre\_de\_feedback. L’agent cerca de forma automatitzada la comanda més recent a historial\_compres.ttl que conté el producte triat, genera un ID estructurat ocult (FB-producte-comanda) i en registra la puntuació i el comentari a feedback.ttl.

A través de /comm, l’Opinador respon a les peticions ACL (request) d'altres agents de l'ecosistema de forma asíncrona. Si rep una PeticioRegistreCompra, s’executa el pla\_de\_registre\_de\_compra per emmagatzemar la nova comanda com a node `Comanda` a historial\_compres.ttl i retorna una ConfirmacioRegistreCompra. Si rep una PeticioConsultaComanda, recupera aquest snapshot perquè l’Agent Compra pugui reconstruir la vista `/orders/<id>`. Si rep una PeticioDevolucio, s'activa el pla\_de\_consulta\_ de\_criteris\_devolucio, on l'Opinador avalua el motiu i comprova que no hagin passat més de 15 dies des de la compra. Finalment, retorna una ResolucioDevolucio detallant si s'accepta o es denega la sol·licitud per a cada producte.

*Un canvi respecte al disseny inicial ha estat que, mentre que al principi es demanava manualment un identificador (ID) a l’usuari per poder carregar el seu perfil i registrar les seves interaccions, ara tot el procés es realitza de manera totalment transparent utilitzant la seva adreça IP com a identificador d'usuari a través de la funció get\_client\_ip.*

## **6.5 Agent Directory** {#6.5-agent-directory}

El Directory només accepta missatges ACL amb performative request a /Register. Segons el tipus d’acció al contingut, executa una de dues operacions.

En un DSO.Register, l’agent que acaba d’arrencar envia la seva URI, nom, adreça HTTP de treball i tipus DSO (CercadorAgent, CentreLogisticAgent, etc.). El directori afegeix aquestes triples al graf intern, registra també qualsevol metadada associada a la URI de l’agent al missatge, escriu un log del registre i respon amb confirm cap al sol·licitant.

En un DSO.Search, un agent que necessita un servei indica el *dso:AgentType* buscat. El directori recorre el graf, copia al graf de resposta tots els agents que coincideixen amb aquell tipus (pot haver-hi diversos centres logístics o transportistes) i retorna inform amb les adreces i URIs necessàries perquè el client obri la comunicació directa. El sol·licitant parseja la resposta i obté un objecte Agent amb .address i .uri. Qualsevol altra acció o missatge mal format rep not-understood.

A més, exposa /Info, que serialitza tot el graf del directori en Turtle per inspecció o depuració (veure quins agents estan registrats després d’executar run\_agents.sh), i /Stop per aturar el servidor.

*Aquest agent no formava part del nostre disseny detallat ja que no té una funció relacionada amb les funcionalitats, simplement desa en un graf RDF els agents vius, confirma les altes, respon cerques per AgentType i permet depurar l’estat via /Info.*

## **6.6 Agent Centre Logístic** {#6.6-agent-centre-logístic}

L’Agent Centre Logístic s’encarrega de rebre la petició de productes localitzats enviada per l’Agent Compra i de transformar-la en un procés de preparació i enviament de la comanda. Un cop rep el missatge, extreu les dades de la comanda, la ciutat de lliurament, la data prevista i els productes implicats, i els agrupa en un lot logístic persistent, reutilitzant un lot existent si ja hi ha coincidència de destinació i data. A partir d’aquí, consulta en paral·lel els agents de transport disponibles per obtenir les seves ofertes, selecciona la millor proposta segons el cost i, en cas d’empat, segons la data de lliurament. Aquesta lògica es coordina des de agent\_centre\_logistic.py, amb el suport dels missatges definits a centre\_logistic.py i la gestió de lots a logistics\_service.py.

Després d’escollir el transportista, l’agent li notifica formalment l’assignació i, si el directori permet localitzar l’Agent Cobrador, inicia també el procés de cobrament intern perquè es registri la factura associada a l’enviament. Finalment, genera i retorna un graf RDF de confirmació d’enviament amb tots els detalls rellevants del lot, el transportista assignat, la data definitiva de lliurament i, si escau, la factura incorporada. 

## **6.7 Agent Retornador** {#6.7-agent-retornador}

L’usuari inicia la devolució des de la interfície web (/*iface*) o bé mitjançant una *PeticioDevolucio* per /*comm*. En tots dos casos s’executa *pla\_compliment\_de\_devolucio*. A la interfície, l’usuari (identificat per IP) veu els productes del seu historial, en selecciona un o més, tria un motiu i envia la sol·licitud.

El Retornador normalitza la petició i agrupa els productes per comanda. Després, per a cada comanda, consulta l’Opinador mitjançant ACL (request amb *PeticioDevolucio,* resposta inform amb *ResolucioDevolucio*), resolent l’agent via Directory sense adreces fixes. La política la aplica l’Opinador sobre *historial\_compres.ttl*: només s’accepten els motius de producte defectuós, no conforme amb la descripció o entrega endarrerida, i la compra no pot tenir més de quinze dies. La resta de motius del formulari acaben en denegació amb el missatge estàndard de rebuig. La validació és per producte, de manera que la resposta pot ser parcial dins la mateixa sol·licitud.

Si no queda cap producte acceptat, l’usuari rep la denegació i el flux s’atura. Si n’hi ha, *pla\_retorn* calcula els imports des de *productes.ttl*, separa lots interns i externs segons *responsable\_enviament\_productes.ttl* i demana el reemborsament al Cobrador (*PeticioRetornDiners*), que el confirma automàticament. Es registra el resum a *devolucions.ttl* i es mostra el resultat final a la interfície. 

*Un canvi respecte al disseny inicial ha estat que ara s’admet el retorn de productes de diferents comandes en una sola petició, no cal que tots les producte a reotrnar siguin de la mateixa.*

## **6.8 Agent Cobrador** {#6.8-agent-cobrador}

El Cobrador només rep peticions per ACL a /comm. Segons el tipus de contingut, executa un dels cinc plans previstos al disseny.

En la capacitat Guardar dades bancàries, *pla\_registrar\_dades\_usuari* processa una *PeticioRegistreDadesBancariesUsuari* (habitualment de l’Agent Compra), desa IBAN i mètode de pagament a *dades\_bancaries\_usuari.ttl* i respon amb confirmació ACL. *pla\_registrar\_dades\_venedor* fa el mateix per a venedors externs quan el Venedor Extern envia *PeticioRegistreDadesBancariesVenedor*, escrivint a *dades\_bancaries\_venedors\_externs.ttl.*

En Cobrar compra, *pla\_cobrament\_intern* s’activa quan arriba una *ConfirmacioEnviament* del Centre Logístic (lot enviat i llest per cobrar): calcula l’import sumant els preus del catàleg més el cost de transport del missatge, registra el pagament a *pagaments.ttl* amb SentitPagament \= COBRAMENT i estat PAGAT, i retorna ConfirmacioPagament. *pla\_cobrament\_extern* atén *PeticioPagament* de l’Agent Compra per productes de venedor extern: accepta l’import i metadades de la petició, el registra amb sentit PAGAMENT (diners sortints cap al venedor) i confirma igualment amb PAGAT.

En Gestionar devolucions, *pla\_retornar\_diners* rep *PeticioRetornDiners* del Retornador, escriu el reemborsament a *devolucions.ttl* amb estat RETORNAT i respon amb la confirmació corresponent. 

*Després del feedback de la segona entrega, es va aplicar un canvi per la distinció COBRAMENT / PAGAMENT (SentitPagament) per diferenciar cobrar l’usuari i pagar un venedor extern.*

7. # **Elements del nivell avançat de la pràctica** {#elements-del-nivell-avançat-de-la-pràctica}

## **7.1 Servei de registre per agents de transport**  {#7.1-servei-de-registre-per-agents-de-transport}

S’ha implementat la funcionalitat d’un directori d’agents de transport des d’on els transportistes es registren dins del propi Agent Directory, és a dir, no hi ha un directori separat només per a transport, sinó que els transportistes es distingeixen pel tipus *DSO.TransportistaAgent* i per metadades pròpies (*azon:IdTransportista*). Cada Agent Transportista és un servidor Flask independent i cada centre logístic descobreix dinàmicament tots els transportistes registrats abans d’iniciar la negociació descrita a l’[apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport).

Per fer-ho, s’ha centralitzat la comunicació a través d'un sol Directory, evitant que els centres logístics tinguin les URL dels transportistes cablejades. Com a demostració, s'han configurat dos transportistes en ports diferents (9010 i 9011): *fast* (8,0 EUR/kg, 1 dia) i *economy* (4,0 EUR/kg, 3 dies). Les condicions comercials de cada instància es poden personalitzar en l'arrencada (--transport-id, \--price-per-kg, \--delivery-days) sense modificar el codi. Això dóna una gran flexibilitat al sistema, ja que permet afegir nous transportistes que, només amb registrar-se al Directory, passen a participar automàticament en les següents negociacions dels centres.

**FLUX D’EXEMPLE**

Suposem que el sistema està en marxa, amb Directory al port 9000, Centre Logístic de Barcelona al 9003, i els dos transportistes per defecte. Un lot del centre BCN ha passat a estat PREPARAT i s’activa la negociació de transport:

1. **Arrencada dels transportistes (registre):** Cada procés *agent\_transportista* construeix el seu Agent i crida *register\_transport\_agent*(directory), que envia un DSO.Register amb AgentType \= TransportistaAgent i el seu IdTransportista (fast, economy, etc.). L’Agent Directory desa les triples al graf intern i respon confirm. A partir d’aquest moment l’empresa de transport és visible per a qualsevol agent que faci una cerca del tipus adequat.

2. **El centre necessita transportistes per a un lot:** Abans de contactar cap transportista, el centre crida *resolve\_transport\_agents*() (des de *pla\_cerca\_de\_transportista*). Si no hi ha una llista fixa de proves, construeix un DSO.Search cap al Directory mitjançant *resolve\_agents\_via\_directory*(..., DSO.TransportistaAgent).

3. **Resposta del Directory:** El Directory retorna un inform amb totes les URIs registrades com a transportista. En la configuració per defecte hi ha dues entrades: *Transportista-fast* i *Transportista-economy*. El centre parseja la resposta amb *parse\_directory\_responses* i converteix cada entrada en un objecte Agent amb .uri, .name i .address (endpoint /comm).

4. **Resultat de la descoberta:** El centre disposa ja d’una llista d’adreces HTTP vàlides per contactar cada transportista de forma directa, sense tornar a passar pel Directory. Gràcies a IdTransportista, pot distingir fast d’economy encara que comparteixin el mateix tipus DSO. El que passa després en obrir comunicació P2P amb cadascun (ofertes, contraofertes i selecció) queda descrit a l’[apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport).

5. **Transportista nou després d’haver arrencat el sistema:** Si s’executa una tercera instància (p. ex. \--transport-id premium \--port 9012), en registrar-se al Directory amb el mateix mecanisme del pas 1 apareixerà automàticament a la propera DSO.Search, sense reiniciar centres ni modificar fitxers de configuració. El centre BCN descobrirà tres transportistes en lloc de dos quan torni a cridar resolve\_transport\_agents().

## **7.2 Negociació complexa entre centre logístic i agents de transport** {#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport}

Un cop l’Agent Centre Logístic ha descobert els transportistes disponibles ([apartat 7.1](#7.1-servei-de-registre-per-agents-de-transport)), negocia l’assignació de cada lot PREPARAT mitjançant un protocol FIPA Contract Net: el centre sol·licita propostes a tots els candidats, envia una contraoferta de preu i cada transportista pot acceptar-la, rebutjar-la o respondre amb una nova proposta. La política concreta prioritza el servei més ràpid (oferta inicial més cara) només si el preu final queda dins d’un sostre calculat a partir de l’oferta més barata. En cas contrari, s’assigna directament l’opció econòmica sense negociar-la. 

Per fer-ho, s'ha implementat un procés que s'inicia amb l'enviament en paral·lel d'una PeticioTransport a tots els transportistes per recollir les ofertes inicials. Un cop classificades l'oferta baixa i l'alta, el centre calcula una contraoferta (110% del preu mínim) i un preu sostre (115%), i envia una ContraofertaTransport únicament al transportista de l'oferta alta. Segons la rèplica d'aquest (agree, propose o refuse), s'assignarà el servei ràpid si el preu final no supera el sostre establert. En cas contrari, es mantindrà l'oferta baixa inicial sense negociar. Finalment, el centre confirma el guanyador amb accept-proposal, descarta la resta de licitadors i notifica l'Agent Compra enviant les corresponents DadesEnviament i ConfirmacioEnviament.

**FLUX D’EXEMPLE**

Suposem un lot de 5,0 kg preparat al centre BCN, amb els transportistes per defecte (*economy*: 4 €/kg / 3 dies; fast: 8 €/kg / 1 dia). El centre ja ha resolt les seves adreces via Directory (7.1):

1. Sol·licitud de propostes: dins *pla\_cerca\_de\_transportista*, el centre envia *PeticioTransport* en paral·lel (*ThreadPoolExecutor*) a fast i economy. Cada transportista rep les dades del lot per /comm.  
2. Ofertes inicials: economy respon propose amb 20,00 € (5x4) i entrega en 3 dies; fast respon propose amb 40,00 € (5x8) i entrega en 1 dia. El centre classifica economy com a oferta baixa (P\_baix \= 20 €) i fast com a oferta alta (P\_alta \= 40 €).  
3. Càlcul de la contraoferta: el centre calcula P\_contra \= 20 × 1,10 \= 22,00 € i P\_sostre \= 20 × 1,15 \= 23,00 €. Interpretació: està disposat a pagar un 10 % per sobre del mínim del mercat i com a màxim un 15 % per obtenir el servei ràpid.  
4. Contraoferta només al premium: dins pla\_negociar\_contraoferta, el centre envia ContraofertaTransport (propose, preu 22 €) només a fast. Economy no rep cap contraoferta.  
5. Resposta del transportista ràpid (escenaris possibles):  
- agree a 22 € → el centre contracta fast a 22 € (entrega en 1 dia): premium acceptable dins del sostre.  
- propose a 23 € → 23 ≤ 23 → el centre accepta fast a 23 € (15 % sobre economy).  
- propose a 28 € o refuse → el centre recau en economy a 20 € i 3 dies (oferta baixa inicial, sense negociació).

Selecció i notificació: dins *pla\_de\_transportista\_escollit*, el centre determina el guanyador, envia accept-proposal al transportista escollit i reject-proposal als altres. Després assigna el lot (*assign\_transport\_to\_lot*), notifica l’Agent Compra amb *DadesEnviament* i *ConfirmacioEnviament*, i activa el cobrament intern del cost de transport repartit per pes.

## **7.3 Productes a diferents centres logístics** {#7.3-productes-a-diferents-centres-logístics}

S’ha implementat el suport per a comandes multi-centre: una mateixa compra pot incloure productes emmagatzemats en centres logístics diferents (Barcelona, Girona, Tarragona). L’Agent Compra segmenta la comanda per centre, envia en paral·lel la localització de cada producte al centre que li correspon i cada centre gestiona de forma autònoma el seu lot i la negociació amb transportistes (apartats 7.1 i 7.2). L’usuari rep un únic resultat de compra immediat i, a mesura que cada centre avança, diferents blocs d’informació de seguiment (data i transportista per lot/centre).

Per fer-ho s'han desplegat tres agents Centre Logístic independents (CL-BCN, CL-GI i CL-TGN) registrats al Directory. A partir del fitxer *ubicacions\_productes.ttl*, el sistema identifica els centres candidats per a cada línia de la comanda, selecciona el més proper a la destinació i consolida els productes en grups per centre. Si la comanda implica diferents punts d'origen, l'Agent Compra els contacta en paral·lel, rebent una ConfirmacioLocalitzacio immediata amb el lot assignat. Posteriorment, cada centre gestiona el seu lot i negocia de forma independent amb els transportistes del Directory. Finalment, l'Agent Compra rep les dades i confirmacions d'enviament, guarda el seguiment a *seguiment\_enviaments.ttl* i calcula la data de lliurament global de la comanda com el màxim de les dates rebudes.

**FLUX D’EXEMPLE**

Suposem que l’usuari compra des de la interfície de Compra (ciutat de lliurament Barcelona) els productes P1001 (disponible a BCN i GI) i P1003 (només a TGN). El sistema té actius els tres centres logístics i els transportistes del Directory:

1. **Creació de la comanda**: L’Agent Compra valida la compra i executa *pla\_producte\_als\_nostres\_magatzems* en paral·lel amb el registre bancari i la persistència del node `Comanda` a *historial\_compres.ttl* via Opinador.  
2. **Assignació de centre per producte**: es llegeix *ubicacions\_productes.ttl*. P1001 pot anar a BCN o GI; com que l’usuari demana entrega a Barcelona, s’assigna CL-BCN. P1003 només té candidat CL-TGN. La comanda queda partida en dos grups: {P1001 → BCN} i {P1003 → TGN}.  
3. **Enviament paral·lel als centres**: l’Agent Compra envia un ProducteLocalitzat al centre BCN (port 9003\) i un altre al centre TGN (port 9008). Cada centre respon amb ConfirmacioLocalitzacio (lot obert, data estimada, centre d’origen). L’Agent Compra desa aquestes reserves a *seguiment\_enviaments.ttl* i retorna a l’usuari un ResultatCompra immediat: encara pot no haver-hi transportista assignat, però ja consten dos enviaments (un per centre).  
4. **Processament autònom per centre**: quan cada lot passa a PREPARAT, el centre BCN negocia el seu lot amb els transportistes ([apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport)) i el centre TGN fa el mateix de forma independent.  
5. **Actualitzacions asíncrones a Compra**: el centre BCN envia DadesEnviament i, després, ConfirmacioEnviament. El centre TGN fa el mateix per al lot de P1003. L’Agent Compra actualitza *seguiment\_enviaments.ttl*; quan es consulta la comanda, la data final es deriva del màxim de les dates oficials rebudes.  
6. **Informació múltiple per a l’usuari**: a la pàgina de resum, l’usuari veu dos blocs d’enviament: un amb centre BCN i un altre amb centre TGN. Així es compleix el requisit de rebre múltiples informacions de data d’entrega i transportista dins la mateixa comanda.

   # 

8. # **Tasques amb nota extra** {#tasques-amb-nota-extra}

Per tal d’augmentar la complexitat del projecte i poder aspirar a més nota, s’ha decidit implementar una funcionalitat més a part de les 3 ja implementades dels elements de nivell avançat. Aquesta funcionalitat extra és la petició de valoracions.

## **8.1 Petició de valoracions** {#8.1-petició-de-valoracions}

Quan l’usuari accedeix a /iface, el sistema li mostra els productes comprats que encara no ha valorat i una llista de suggeriments personalitzats calculats a partir de l’historial de cerques i compres. Les compres queden registrades automàticament després de cada transacció gràcies a la coordinació amb l’Agent Compra, de manera que l’usuari no ha d’introduir manualment identificadors de comanda. 

Per fer-ho, l’Agent Cercador guarda cada cerca a *historial\_cerques.ttl* i, en finalitzar una compra, l’Agent Compra envia en paral·lel una PeticioRegistreCompra a l’Opinador, que executa *pla\_de\_registre\_de\_compra* i desa la `Comanda` completa a *historial\_compres.ttl*. Al dashboard, es calcula la diferència entre productes comprats i productes ja valorats a *feedback.ttl*, i el formulari activa *pla\_de\_registre\_de\_feedback*, generant un identificador. En paral·lel, *pla\_de\_creacio\_de\_suggeriments* pondera categories i marques de compres i cerques prèvies per proposar fins a 10 productes del catàleg que l’usuari encara no ha comprat. 

**FLUX D’EXEMPLE**

Suposem un usuari que utilitza AgentZon des del navegador (IP 192.168.1.50) i que el sistema està en marxa amb Cercador (9001), Compra (9002) i Opinador (9004):

1. **Recollida d’historial de cerques**: l’usuari cerca «teclat mecànic» a la interfície del Cercador. L’agent registra els criteris i els productes trobats a *historial\_cerques.ttl* amb user\_id \= IP de l’usuari.  
2. **Compra i registre automàtic**: l’usuari compra el producte P1002 des de Compra. En paral·lel amb la logística, l’Agent Compra executa *pla\_delegar\_registre\_compra* i envia PeticioRegistreCompra a l’Opinador. L’Opinador respon ConfirmacioRegistreCompra i afegeix el node `Comanda` complet a *historial\_compres.ttl.*  
3. **Accés al dashboard de valoracions**: més endavant, l’usuari accedeix a la secció de recomanacions i feedback i l’Agent Opinador identifica el perfil per IP i detecta que P1002 està comprat però absent de *feedback.ttl* i el mostra al desplegable «productes pendents de valorar».  
4. **Enviament de la valoració:** l’usuari selecciona P1002, assigna 4 estrelles i escriu un comentari. En enviar el formulari s’executa pla\_de\_registre\_de\_feedback: es vincula a la comanda correcta, es crea FB-P1002-ORDER-... i es guarda a *feedback.ttl.*   
5. **Recomanacions proactives**: en carregar el mateix dashboard, *pla\_de\_creacio\_de\_suggeriments* analitza les cerques i compres de la IP (categories i marques més freqüents), puntua productes del catàleg encara no comprats i mostra, per exemple, accessoris de la mateixa marca o categoria amb un límit configurable (per defecte 5, màxim 10). 

9. # **Distribució de la feina** {#distribució-de-la-feina}

Pel que fa a la distribució de tasques, cal destacar que la primera entrega del projecte va ser totalment col·laborativa. Els diagrames de la primera part es van realitzar conjuntament entre tots els membres de l'equip, fet que ens va permetre establir una base sòlida i una visió unificada de tot el sistema abans de començar el desenvolupament individual.

De cara a l'organització general de la segona entrega, la intenció inicial, un cop acabat el disseny detallat conjuntament, era treballar per separat i dividint el projecte per funcionalitats. Per organitzar-nos millor hem decidit assignar un encarregat principal per a cada àrea general. D'aquesta manera, en Pol s'ha ocupat de guiar i estructurar el codi, l'Àngela s'ha encarregat de modificar principalment el disseny de l'ontologia i diagrames i la Paula ha assumit la redacció de la documentació tècnica. Tots aquests canvis s’han fet amb reunions i posades en comú constants, ja que, malgrat tenir tasques assignades, tothom ha estat implicat en totes les àrees per assegurar que el projecte avancés de manera totalment coordinada.

Finalment, pel que fa a la programació, hem vist que el més eficient era repartir-nos el desenvolupament dels agents. Amb aquest enfocament, en Pol s'ha ocupat de l'agent compra, el centre logístic, transportista i el retornador, l'Àngela s'ha encarregat de l'agent cerca i el cobrador, i la Paula s'ha encarregat de l'agent opinador i el venedor extern.

# 

10. # **Resultats i conclusió** {#resultats-i-conclusió}

**Què cal documentar?**  
Evaluación crítica de los resultados obtenidos en la práctica y consideraciones sobre los límites de vuestra solución (competencia).
