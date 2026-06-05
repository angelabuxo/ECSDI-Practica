

6. # **Implementació d’agents** {#implementació-d’agents}

Aquest apartat descriu com s’han materialitzat al codi els agents definits al disseny detallat. Abans d’entrar en cada agent, convé explicar la seva estructura general:

1. Globals de runtime (AGENT, DIRECTORY\_AGENT, comptadors de missatge, rutes als fitxers .ttl).  
2. configure\_runtime(settings, …): inicialitza aquest estat de forma explícita perquè la bateria de tests pugui muntar l’agent sense xarxa real.  
3. Plans (pla\_…): cada pla correspon a una capacitat del diagrama Prometheus de l’Entrega 2; el nom al codi ha de poder traçar-se al diagrama.  
4. @app.route("/comm"): entrada ACL: es parseja el missatge, es comprova el performative i es despatxa segons el \`rdf:type\` del contingut. En la majoria d'agents només s'accepten \`request\`; algunes excepcions, com l'Agent Compra, també processen \`inform\` per actualitzacions asíncrones d'enviament.  
5. @app.route("/iface") (quan cal): interacció amb l’usuari; en molts casos l’usuari s’identifica per adreça IP (get\_client\_ip\_from\_request), no per un login.  
6. Bloc \`if __name__ == "__main__":\`: registre al Directory (excepte el propi Directory) i arrencada amb *serve\_agent*, que llança un procés auxiliar per al registre i executa Flask en paral·lel.

Els conceptes intercanviats són classes i propietats de l’ontologia (*PeticioCerca, PeticioPagament, ResolucioDevolucio*, …) i quan un agent no entén una petició, respon *not-understood*. Per últim, les dades es concentren a data/ i es llegeixen o escriuen des dels serveis.

## **6.1 Agent Cercador** {#6.1-agent-cercador}

A través del canal d’entrada /iface, l’usuari veu el formulari de cerca i, si la resta d’agents s’han donat d’alta al Directory, botons per obrir suggeriments o feedback (Agent Opinador) i devolucions (Agent Retornador). En enviar el formulari, l’agent construeix internament una PeticioCerca a partir dels camps (text, categoria, marca, rang de preus), executa pla\_de\_cerca filtrant productes.ttl, envia criteris i resultats a l’Agent Opinador amb pla\_registrar\_cerca\_a\_opinador (IP del client com a identificador d’usuari), i activa pla\_de\_presentacio, que renderitza la llista i un formulari per marcar productes i continuar la compra a l’Agent Compra (si està registrat al Directory).

## **6.2 Agent Compra** {#6.2-agent-compra}

L'usuari inicia la compra des del cercador a /iface o mitjançant una PeticioCompra per /comm. L'agent normalitza la petició, consulta els productes al Cercador i construeix la comanda. El processament executa en paral·lel: registre de dades bancàries al Cobrador (PeticioRegistreDadesBancariesUsuari), delegació de la comanda a l'Opinador (PeticioRegistreCompra → historial\_compres.ttl), localització als centres logístics via Directory (ProducteLocalitzat, amb resposta ConfirmacioLocalitzacio) i logística externa al Venedor Extern (PeticioEnviamentExtern, amb PeticioPagament de sentit PAGAMENT cap als venedors externs). A la interfície, l'usuari (identificat per IP) primer omple les dades d'enviament i, un cop confirmada la compra, veu un resum de factura i seguiment; el seguiment viu es persisteix localment a seguiment\_enviaments.ttl. El cobrament intern a l'usuari (COBRAMENT) no el dispara l'Agent Compra en el moment de la compra: el Cobrador el processa més endavant quan un centre logístic envia ConfirmacioEnviament. Per /comm retorna un ResultatCompra; per /iface renderitza el resum HTML.

*Un canvi respecte al disseny inicial ha estat que, mentre que al principi es demanava manualment un identificador (ID) a l’usuari per poder iniciar el procés de compra i carregar el seu perfil, ara tot es realitza de manera totalment transparent utilitzant la seva adreça IP com a identificador a través de la funció get\_client\_ip\_from\_request.* 

## **6.3 Agent Centre Logístic** {#6.3-agent-centre-logístic}

L'agent centre logístic coordina l'agrupació de productes en lots i la negociació de transport per a comandes internes. No hi ha un únic centre ([apartat 7.3](#7.3-productes-a-diferents-centres-logístics)): hi ha diverses instàncies independents (p. ex. CL-BCN, CL-GI, CL-TGN), cadascuna amb el seu fitxer lots-\<centre\>.ttl i registrada al Directory amb IdCentreLogistic i ciutat.

El procés s'activa quan l'Agent Compra envia una ProducteLocalitzat amb ciutat de destinació, data d'entrega i dades del producte. L'agent executa pla\_assignar\_producte\_a\_lot, reutilitzant un lot OBERT amb mateixa ciutat, data d'entrega i centre, calculant el pes total; quan el lot assoleix el llindar de pes queda PREPARAT. Respon immediatament amb ConfirmacioLocalitzacio.

Si el lot és PREPARAT, s'inicia automàticament la negociació de transport ([apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport)): consulta paral·lela als transportistes via Directory, possible contraoferta premium a l'oferta alta (pla\_negociar\_contraoferta), selecció segons la política 110% / 115% (pla\_de\_transportista\_escollit) i notificació d'acceptació/rebuig als transportistes. Després informa l'Agent Compra amb DadesEnviament per producte, dispara el cobrament intern al Cobrador (ConfirmacioEnviament) i envia la confirmació final d'enviament. També existeix /cron/negotiate-ready-lots per lots preparats dins la finestra d'entrega.

## **6.4 Agent Opinador** {#6.4-agent-opinador}

L'usuari interacciona amb l'Opinador des de /iface o mitjançant missatges AZON per /comm. A la interfície visualitza un dashboard amb estadístiques, productes comprats pendents de valorar, sol·licituds proactives de feedback i recomanacions personalitzades. Les recomanacions les genera pla\_de\_creacio\_de\_suggeriments a partir del catàleg obtingut del Cercador via ACL, més historial\_cerques.ttl i historial\_compres.ttl, amb un límit ajustable d'entre 1 i 10 productes.

Quan l'usuari envia una valoració des del formulari, s'executa pla\_de\_registre\_de\_feedback: l'agent associa el producte a la comanda més recent que el conté a historial\_compres.ttl, genera un ID FB-\<producte\>-\<comanda\> i enregistra puntuació i comentari a feedback.ttl.

Per /comm, l'Opinador respon a peticions ACL (request) d'altres agents. Segons el tipus de missatge: PeticioRegistreCerca → registre a historial\_cerques.ttl; PeticioRegistreCompra → pla\_de\_registre\_de\_compra a historial\_compres.ttl i ConfirmacioRegistreCompra; PeticioConsultaCompresUsuari i PeticioConsultaComanda → consultes d'historial; RespostaFeedback → registre de feedback; PeticioDevolucio → pla\_de\_consulta\_de\_criteris\_devolucio, que avalua el motiu i comprova que no hagin passat més de 15 dies des de la compra, retornant una ResolucioDevolucio amb acceptació total o parcial per producte.

*Un canvi respecte al disseny inicial ha estat que, mentre que al principi es demanava manualment un identificador (ID) a l’usuari per poder carregar el seu perfil i registrar les seves interaccions, ara tot el procés es realitza de manera totalment transparent utilitzant la seva adreça IP com a identificador d'usuari a través de la funció get\_client\_ip.*

## **6.5 Agent Directory** {#6.5-agent-directory}

El Directory només accepta missatges ACL amb performative request a /Register. Segons el tipus d’acció al contingut, executa una de dues operacions.

En un DSO.Register, l’agent que acaba d’arrencar envia la seva URI, nom, adreça HTTP de treball i tipus DSO (CercadorAgent, CentreLogisticAgent, etc.). El directori afegeix aquestes triples al graf intern, registra també qualsevol metadada associada a la URI de l’agent al missatge, escriu un log del registre i respon amb confirm cap al sol·licitant.

En un DSO.Search, un agent que necessita un servei indica el *dso:AgentType* buscat. El directori recorre el graf, copia al graf de resposta tots els agents que coincideixen amb aquell tipus (pot haver-hi diversos centres logístics o transportistes) i retorna inform amb les adreces i URIs necessàries perquè el client obri la comunicació directa. El sol·licitant parseja la resposta i obté un objecte Agent amb .address i .uri. Qualsevol altra acció o missatge mal format rep not-understood.

A més, exposa /Info, que serialitza tot el graf del directori en Turtle per inspecció o depuració (veure quins agents estan registrats després d’executar run\_agents.sh), i /Stop per aturar el servidor.

## **6.6 Agent Retornador** {#6.6-agent-retornador}

L'usuari inicia la devolució des de la interfície web (/iface) o mitjançant una PeticioDevolucio per /comm. En tots dos casos s'executa pla\_compliment\_de\_devolucio. A la interfície, l'usuari (identificat per IP) consulta els productes comprats via l'Opinador (PeticioConsultaCompresUsuari), en selecciona un o més, tria un motiu i envia la sol·licitud.

El Retornador agrupa els productes per comanda. Després, per a cada comanda, consulta l'Opinador mitjançant ACL (request amb PeticioDevolucio, resposta inform amb ResolucioDevolucio), resolent l'agent via Directory sense adreces fixes. La política la aplica l'Opinador sobre historial\_compres.ttl: només s'accepten els motius de producte defectuós, no conforme amb la descripció o entrega endarrerida, i la compra no pot tenir més de quinze dies. La resta de motius del formulari acaben en denegació amb el missatge estàndard de rebuig. La validació és per producte, de manera que la resposta pot ser parcial dins la mateixa sol·licitud.

Si no queda cap producte acceptat, l'usuari rep la denegació i el flux s'atura. Si n'hi ha, pla\_compliment\_de\_devolucio calcula els imports a partir dels snapshots de producte retornats per l'Opinador, separa productes interns i externs per venedor (seller\_id i requires\_external\_logistics) i, per cada lot de reemborsament, crida pla\_retorn per demanar el reemborsament al Cobrador (PeticioRetornDiners), que el confirma automàticament. El Retornador registra cada lot i el resum a devolucions.ttl i mostra el resultat final a la interfície (o retorna ResolucioDevolucio per /comm).

*Un canvi respecte al disseny inicial ha estat que ara s’admet el retorn de productes de diferents comandes en una sola petició, no cal que tots les producte a reotrnar siguin de la mateixa.*

## **6.7 Agent Cobrador** {#6.7-agent-cobrador}

El Cobrador rep peticions ACL (request) a /comm i també exposa /iface per inspeccionar pagaments.ttl en Turtle. Segons el tipus de contingut, executa un dels sis plans del codi.

En la capacitat Guardar dades bancàries, pla\_registrar\_dades\_usuari processa una PeticioRegistreDadesBancariesUsuari (habitualment de l'Agent Compra), desa les dades bancàries i el mètode de pagament a dades\_bancaries\_usuari.ttl i respon amb confirmació ACL. pla\_registrar\_dades\_venedor fa el mateix per a venedors externs quan el Venedor Extern envia PeticioRegistreDadesBancariesVenedor, escrivint a dades\_bancaries\_venedors\_externs.ttl. pla\_consulta\_dades\_venedor atén PeticioConsultaDadesBancariesVenedor i retorna el perfil bancari del venedor.

En Cobrar compra, pla\_cobrament\_intern s'activa quan arriba una ConfirmacioEnviament del Centre Logístic (via build\_peticio\_cobrament\_intern): calcula l'import sumant els preus del producte inclosos al missatge més el cost de transport, registra el pagament a pagaments.ttl amb SentitPagament \= COBRAMENT i estat PAGAT, i retorna ConfirmacioPagament. pla\_cobrament\_extern atén PeticioPagament de l'Agent Compra per productes de venedor extern: accepta l'import i metadades de la petició, el registra amb sentit PAGAMENT (diners sortints cap al venedor) i confirma amb PAGAT.

En Gestionar devolucions, pla\_retornar\_diners rep PeticioRetornDiners del Retornador, accepta automàticament el reemborsament i respon amb ConfirmacioRetornDiners; no escriu a devolucions.ttl (això ho fa el Retornador).

## **6.8 Agent Venedor Extern** {#6.8-agent-venedor-extern}

L'usuari interacciona amb el Venedor Extern des /iface. A la interfície, primer ha de completar el perfil del venedor (nom i dades bancàries); aquestes dades es deleguen al Cobrador (PeticioRegistreDadesBancariesVenedor). Després pot donar d'alta un o més productes indicant preu, pes, SKU extern i mode logístic (enviament propi del venedor o delegat a un centre logístic de la plataforma).

En registrar un producte, s'executa process\_alta\_producte\_extern: si cal, registra les dades bancàries al Cobrador; envia l'AltaProducteExtern al Cercador per afegir el producte a productes.ttl; i notifica l'Agent Compra amb PeticioRegistreProducteExternCompra perquè guardi la responsabilitat logística i, si escau, la ubicació del producte a ubicacions\_productes.ttl. Respon amb ConfirmacioAltaProducteExtern.

Per /comm, l'agent atén dues accions ACL (request). Amb AltaProducteExtern repeteix el flux d'alta descrit. Amb PeticioEnviamentExtern (enviada per l'Agent Compra en una compra amb logística externa), pla\_enviament\_extern\_acl respon amb DadesEnviament i data d'entrega estimada (cinc dies), delegant el lliurament al venedor sense passar pels transportistes interns. Qualsevol altra acció o missatge mal format rep not-understood. L'agent no manté fitxers .ttl propis: delega la persistència al Cercador, Compra i Cobrador, i es descobreix via Directory com a VenedorExternAgent.

# 

7. # **Elements del nivell avançat de la pràctica** {#elements-del-nivell-avançat-de-la-pràctica}

## **7.1 Servei de registre per agents de transport**  {#7.1-servei-de-registre-per-agents-de-transport}

S’ha implementat la funcionalitat d’un directori d’agents de transport des d’on els transportistes es registren dins del propi Agent Directory, és a dir, no hi ha un directori separat només per a transport, sinó que els transportistes es distingeixen pel tipus *DSO.TransportistaAgent* i per metadades pròpies (*azon:IdTransportista*). Cada Agent Transportista és un servidor Flask independent i cada centre logístic descobreix dinàmicament tots els transportistes registrats abans d’iniciar la negociació descrita a l’[apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport).

Per fer-ho, s’ha centralitzat la comunicació a través d'un sol Directory, evitant que els centres logístics tinguin les URL dels transportistes prefixades. Com a demostració, s'han configurat dos transportistes en ports diferents (9010 i 9011): *fast* (8,0 EUR/kg, 1 dia) i *economy* (4,0 EUR/kg, 3 dies). Les condicions comercials de cada instància es poden personalitzar en l'arrencada (--transport-id, \--price-per-kg, \--delivery-days) sense modificar el codi. Això dóna una gran flexibilitat al sistema, ja que permet afegir nous transportistes que, només amb registrar-se al Directory, passen a participar automàticament en les següents negociacions dels centres.

**FLUX D’EXEMPLE**

Suposem que el sistema està en marxa, amb Directory al port 9000, Centre Logístic de Barcelona al 9003, i els dos transportistes per defecte. Un lot del centre BCN ha passat a estat PREPARAT i s’activa la negociació de transport:

1. **Arrencada dels transportistes (registre):** Cada procés *agent\_transportista* construeix el seu Agent i crida *register\_transport\_agent*(directory), que envia un DSO.Register amb AgentType \= TransportistaAgent i el seu IdTransportista (fast, economy, etc.). L’Agent Directory desa les triples al graf intern i respon confirm. A partir d’aquest moment l’empresa de transport és visible per a qualsevol agent que faci una cerca del tipus adequat.

2. **El centre necessita transportistes per a un lot:** Abans de contactar cap transportista, el centre crida *resolve\_transport\_agents*() (des de *pla\_cerca\_de\_transportista*). Si no hi ha una llista fixa de proves, construeix un DSO.Search cap al Directory mitjançant *resolve\_agents\_via\_directory*(..., DSO.TransportistaAgent).

3. **Resposta del Directory:** El Directory retorna un inform amb totes les URIs registrades com a transportista. En la configuració per defecte hi ha dues entrades: *Transportista-fast* i *Transportista-economy*. El centre parseja la resposta amb *parse\_directory\_responses* i converteix cada entrada en un objecte Agent amb .uri, .name i .address (endpoint /comm).

4. **Resultat de la descoberta:** El centre disposa ja d’una llista d’adreces HTTP vàlides per contactar cada transportista de forma directa, sense tornar a passar pel Directory. Gràcies a IdTransportista, pot distingir fast d’economy encara que comparteixin el mateix tipus DSO. El que passa després en obrir comunicació P2P amb cadascun (ofertes, contraofertes i selecció) queda descrit a l’[apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport).

5. **Transportista nou després d’haver arrencat el sistema:** Si s’executa una tercera instància (p. ex. \--transport-id premium \--port 9012), en registrar-se al Directory amb el mateix mecanisme del pas 1 apareixerà automàticament a la propera DSO.Search, sense reiniciar centres ni modificar fitxers de configuració. El centre BCN descobrirà tres transportistes en lloc de dos quan torni a cridar resolve\_transport\_agents().

## **7.2 Negociació complexa entre centre logístic i agents de transport** {#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport}

Un cop l’Agent Centre Logístic ha descobert els transportistes disponibles ([apartat 7.1](#7.1-servei-de-registre-per-agents-de-transport)), negocia l’assignació de cada lot PREPARAT mitjançant un protocol inspirat en FIPA Contract Net: el centre sol·licita propostes a tots els candidats i envia una contraoferta de preu al transportista premium. Amb la implementació actual, el transportista contraofertat pot acceptar-la (\`agree\`) o rebutjar-la (\`refuse\`); el codi del centre també està preparat per interpretar una nova proposta (\`propose\`) si en un futur s’hi amplia el comportament dels transportistes. La política concreta prioritza el servei més ràpid (oferta inicial més cara) només si el preu final queda dins d’un sostre calculat a partir de l’oferta més barata. En cas contrari, s’assigna directament l’opció econòmica sense negociar-la. 

Per fer-ho, s'ha implementat un procés que s'inicia amb l'enviament en paral·lel d'una PeticioTransport a tots els transportistes per recollir les ofertes inicials. Un cop classificades l'oferta baixa i l'alta, el centre calcula una contraoferta (110% del preu mínim) i un preu sostre (115%), i envia una ContraofertaTransport únicament al transportista de l'oferta alta. En la implementació actual, aquest transportista respon normalment amb \`agree\` o \`refuse\`; si en algun moment retornés una nova oferta amb \`propose\`, el centre també la sabria interpretar i comparar amb el sostre. En cas contrari, es mantindrà l'oferta baixa inicial sense negociar. Finalment, el centre confirma el guanyador amb accept-proposal, descarta la resta de licitadors i notifica l'Agent Compra enviant les corresponents DadesEnviament i ConfirmacioEnviament.

**FLUX D’EXEMPLE**

Suposem un lot de 5,0 kg preparat al centre BCN, amb els transportistes per defecte (*economy*: 4 €/kg / 3 dies; fast: 8 €/kg / 1 dia). El centre ja ha resolt les seves adreces via Directory (7.1):

1. Sol·licitud de propostes: dins *pla\_cerca\_de\_transportista*, el centre envia *PeticioTransport* en paral·lel (*ThreadPoolExecutor*) a fast i economy. Cada transportista rep les dades del lot per /comm.  
2. Ofertes inicials: economy respon propose amb 20,00 € (5x4) i entrega en 3 dies; fast respon propose amb 40,00 € (5x8) i entrega en 1 dia. El centre classifica economy com a oferta baixa (P\_baix \= 20 €) i fast com a oferta alta (P\_alta \= 40 €).  
3. Càlcul de la contraoferta: el centre calcula P\_contra \= 20 × 1,10 \= 22,00 € i P\_sostre \= 20 × 1,15 \= 23,00 €. Interpretació: està disposat a pagar un 10 % per sobre del mínim del mercat i com a màxim un 15 % per obtenir el servei ràpid.  
4. Contraoferta només al premium: dins pla\_negociar\_contraoferta, el centre envia ContraofertaTransport (propose, preu 22 €) només a fast. Economy no rep cap contraoferta.  
5. Resposta del transportista ràpid (escenaris possibles):  
- agree a 22 € → el centre contracta fast a 22 € (entrega en 1 dia): premium acceptable dins del sostre.  
- refuse → el centre recau en economy a 20 € i 3 dies (oferta baixa inicial, sense negociació).  
- propose a 23 € → cas contemplat pel codi del centre però no emès pels transportistes actuals; si existís, 23 ≤ 23 i el centre acceptaria fast a 23 €.

Selecció i notificació: dins *pla\_de\_transportista\_escollit*, el centre determina el guanyador, envia accept-proposal al transportista escollit i reject-proposal als altres. Després assigna el lot (*assign\_transport\_to\_lot*), notifica l’Agent Compra amb *DadesEnviament* i *ConfirmacioEnviament*, i activa el cobrament intern del cost de transport repartit per pes.

## **7.3 Productes a diferents centres logístics** {#7.3-productes-a-diferents-centres-logístics}

S’ha implementat el suport per a comandes multi-centre: una mateixa compra pot incloure productes emmagatzemats en centres logístics diferents (Barcelona, Girona, Tarragona). L’Agent Compra segmenta la comanda per centre, envia en paral·lel la localització de cada producte al centre que li correspon i cada centre gestiona de forma autònoma el seu lot i la negociació amb transportistes (apartats 7.1 i 7.2). L’usuari rep un únic resultat de compra immediat i, a mesura que cada centre avança, diferents blocs d’informació de seguiment (data i transportista per lot/centre).

Per fer-ho s'han desplegat tres agents Centre Logístic independents (CL-BCN, CL-GI i CL-TGN) registrats al Directory. A partir del fitxer *ubicacions\_productes.ttl*, el sistema identifica els centres candidats per a cada línia de la comanda, prioritza els centres amb ciutat exacta o més semblant a la destinació de l'usuari i consolida els productes en grups per centre. Si la comanda implica diferents punts d'origen, l'Agent Compra els contacta en paral·lel, rebent una ConfirmacioLocalitzacio immediata amb el lot assignat. Posteriorment, cada centre gestiona el seu lot i negocia de forma independent amb els transportistes del Directory. Finalment, l'Agent Compra rep les dades i confirmacions d'enviament, guarda el seguiment a *seguiment\_enviaments.ttl* i calcula la data de lliurament global de la comanda com el màxim de les dates rebudes.

**FLUX D’EXEMPLE**

Suposem que l’usuari compra des de la interfície de Compra (ciutat de lliurament Barcelona) els productes P1001 (disponible a BCN i GI) i P1003 (només a TGN). El sistema té actius els tres centres logístics i els transportistes del Directory:

1. **Creació de la comanda**: L’Agent Compra valida la compra, guarda les dades d’enviament a *dades\_enviament\_usuari.ttl* i executa *pla\_producte\_als\_nostres\_magatzems* en paral·lel amb el registre bancari i el registre de la compra a *historial\_compres.ttl* via l’Opinador.  
2. **Assignació de centre per producte**: es llegeix *ubicacions\_productes.ttl*. P1001 pot anar a BCN o GI; com que l’usuari demana entrega a Barcelona, el sistema prioritza CL-BCN per coincidència exacta de ciutat. P1003 només té candidat CL-TGN. La comanda queda partida en dos grups: {P1001 → BCN} i {P1003 → TGN}.  
3. **Enviament paral·lel als centres**: l’Agent Compra envia un ProducteLocalitzat al centre BCN (port 9003\) i un altre al centre TGN (port 9008). Cada centre respon amb ConfirmacioLocalitzacio (lot obert, data estimada, centre d’origen). L’Agent Compra desa aquestes reserves a *seguiment\_enviaments.ttl* i retorna a l’usuari un ResultatCompra immediat: encara pot no haver-hi transportista assignat, però ja consten dos enviaments (un per centre).  
4. **Processament autònom per centre**: quan cada lot passa a PREPARAT, el centre BCN negocia el seu lot amb els transportistes ([apartat 7.2](#7.2-negociació-complexa-entre-centre-logístic-i-agents-de-transport)) i el centre TGN fa el mateix de forma independent.  
5. **Actualitzacions asíncrones a Compra**: el centre BCN envia DadesEnviament i, després, ConfirmacioEnviament. El centre TGN fa el mateix per al lot de P1003. L’Agent Compra actualitza *seguiment\_enviaments.ttl* i recalcula la data final de la comanda com el màxim de les dates rebudes.  
6. **Informació múltiple per a l’usuari**: a la pàgina de resum, l’usuari veu dos blocs d’enviament: un amb centre BCN i un altre amb centre TGN. Així es compleix el requisit de rebre múltiples informacions de data d’entrega i transportista dins la mateixa comanda.

   # 

8. # **Tasques amb nota extra** {#tasques-amb-nota-extra}

Per tal d’augmentar la complexitat del projecte i poder aspirar a més nota, s’ha decidit implementar una funcionalitat més a part de les 3 ja implementades dels elements de nivell avançat. Aquesta funcionalitat extra és la petició de valoracions.

## **8.1 Petició de valoracions** {#8.1-petició-de-valoracions}

Quan l'usuari accedeix a l’interfície l'Agent Opinador (/iface del port 9004), el sistema li mostra els productes comprats que ja poden valorar-se i una llista de suggeriments personalitzats calculats a partir de l'historial de cerques i compres. Les compres queden registrades automàticament després de cada transacció gràcies a la coordinació amb l'Agent Compra, de manera que l'usuari no ha d'introduir manualment identificadors de comanda. En la configuració per defecte de desenvolupament, l'Opinador funciona en mode prova i permet valorar productes passats 60 segons; la política real de dies continua disponible i es mostra a la interfície.

Per fer-ho, quan l'usuari fa una cerca al Cercador, aquest executa pla\_registrar\_cerca\_a\_opinador i envia una PeticioRegistreCerca a l'Opinador; l'Opinador executa pla\_registre\_cerca\_acl i persisteix els criteris i productes trobats a historial\_cerques.ttl (fitxer del qual l'Opinador és l'únic propietari). En finalitzar una compra, l'Agent Compra envia una PeticioRegistreCompra a l'Opinador mitjançant pla\_delegar\_registre\_compra; l'Opinador executa pla\_de\_registre\_de\_compra i desa la comanda a historial\_compres.ttl.

En enviar el formulari s'executa pla\_de\_registre\_de\_feedback: el sistema associa automàticament el producte seleccionat a la comanda més recent que el conté, genera l'identificador FB-{product\_id}-{order\_id} i desa puntuació i comentari a feedback.ttl.

Els suggeriments es generen amb pla\_de\_creacio\_de\_suggeriments, que obté el catàleg actual via des del Cercador (PeticioCerca), sense llegir productes.ttl directament, llegeix historial\_cerques.ttl i historial\_compres.ttl de l'usuari (identificat per IP) i pondera categories i marques de compres (×3 i ×2) i de cerques (+1 cadascuna). Aleshores, proposa productes del catàleg encara no comprats.

A més, l'Opinador periòdicament recalcula suggeriments i genera sol·licituds de feedback (pla\_de\_demanar\_feedback, amb identificadors FB-REQ-{product\_id}-{order\_id}). Per defecte, el cicle de recomanacions s'executa cada 60 segons i el de sol·licituds de feedback cada 120 segons.

**FLUX D’EXEMPLE**

Suposem un usuari que utilitza AgentZon des del navegador (IP 192.168.1.50) i que el sistema està en marxa amb Cercador (9001), Compra (9002) i Opinador (9004):

1. **Recollida d'historial de cerques:** l'usuari cerca «teclat mecànic» a la interfície del Cercador (/iface del port 9001). El Cercador executa pla\_de\_cerca i, a continuació, pla\_registrar\_cerca\_a\_opinador, que envia PeticioRegistreCerca a l'Opinador. L'Opinador desa els criteris i els productes trobats a historial\_cerques.ttl amb user\_id \= IP de l'usuari.  
2. **Compra i registre automàtic:** l'usuari compra el producte P1002 des de Compra. En paral·lel amb la logística i el registre bancari al Cobrador, l'Agent Compra executa pla\_delegar\_registre\_compra i envia PeticioRegistreCompra a l'Opinador. L'Opinador respon ConfirmacioRegistreCompra i afegeix la comanda amb els seus productes a historial\_compres.ttl.  
3. **Accés al dashboard de valoracions:** més endavant, l'usuari accedeix a l'Opinador (/iface, port 9004\) des de l'enllaç del Cercador. L'Agent Opinador identifica el perfil per IP. Si P1002 està comprat, absent de feedback.ttl i ha transcorregut el temps mínim, el mostra al desplegable del formulari «Valorar un producte». Si encara no ha passat aquest temps, apareix a la secció «Productes encara no valorables», no al desplegable. En el mode prova per defecte això passa als 60 segons; amb la política real, als 14 dies.  
4. **Enviament de la valoració:** l'usuari selecciona P1002, assigna 4 estrelles i escriu un comentari. En enviar el formulari s'executa pla\_de\_registre\_de\_feedback: es vincula a la comanda més recent que conté P1002, es crea FB-P1002-{order\_id} (p. ex. FB-P1002-ORDER-... si l'order\_id inclou el prefix ORDER-) i es guarda a feedback.ttl.  
5. **Recomanacions proactives:** en carregar el dashboard, es mostren suggeriments des de la memòria proactiva o, si no n'hi ha, pla\_de\_creacio\_de\_suggeriments els calcula al moment. El pla analitza cerques i compres de la IP (categories i marques més freqüents), puntua productes del catàleg encara no comprats i mostra, per exemple, accessoris de la mateixa marca o categoria. En segon pla, l'Opinador torna a executar aquest pla periòdicament (60 s per recomanacions) i pot mostrar també «Sol·licituds de feedback» generades per pla\_de\_demanar\_feedback (120 s per defecte).
