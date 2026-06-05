
5. # **Descripció de l'ontologia** {#descripció-de-lontologia}

Per definir el coneixement i el vocabulari que els agents d'AgentZon han de compartir per poder comunicar-se i entendre's, hem dissenyat la nostra pròpia ontologia. L'objectiu d'aquesta és modelar formalment els conceptes del domini i el contingut dels missatges intercanviats.

A continuació es descriuen els conceptes, relacions i atributs de l'ontologia AgentZon.

### **5.1 Actor** {#5.1-actor}

Concepte arrel que representa qualsevol entitat que pot participar en el sistema, sigui com a usuari, venedor o proveïdor de serveis logístics.

#### **5.1.1 Usuari** {#5.1.1-usuari}

Concepte que representa un usuari que pot interactuar amb el sistema: realitza cerques de productes, efectua compres, proporciona feedback o sol·licita devolucions. Té com a atributs un identificador personal "IdUsuari", el seu nom "Nom", dades bancàries "DadesBancariesUsuari" i el mètode de pagament preferit "MetodePagament". Es vincula amb les seves comandes mitjançant la relació PertanyAUsuari, i és l'origen de les peticions de compra, cerca i feedback que interactuen amb la resta del sistema.

*Hem decidit que els atributs d'adreça i dades bancàries s'associïn a cada comanda individualment, ja que un mateix usuari pot utilitzar diferents adreces de lliurament i mètodes de pagament en compres diferents.*

#### **5.1.2 Transportista** {#5.1.2-transportista}

Concepte que representa un agent transportista que rep peticions de transport per lliurar lots de productes i envia les seves ofertes amb preu i data d'entrega. Té com a atributs un identificador personal "IdTransportista" i el seu nom comercial "NomTransportista". Està vinculat als lots que transporta mitjançant la relació AssignatATransportista, que el connecta amb els enviaments sota la seva responsabilitat.

#### **5.1.3 VenedorExtern** {#5.1.3-venedorextern}

Concepte que representa un venedor extern que interactua amb el sistema per afegir-hi productes o gestionar la venda i logística d'aquests. Té com a atributs un identificador personal "IdVenedorExtern", el nom comercial "Nom" i les dades bancàries "DadesBancariesVenedorExtern" on seran enviats els diners de les seves vendes. Aquest actor és responsable d'iniciar l'acció AltaProducteExtern per introduir nous articles al catàleg i de gestionar l'enviament quan un producte requereix logística externa.

### **5.2 Producte** {#5.2-producte}

Concepte que representa un producte en el sistema, entitat central del catàleg. Té com a atributs un identificador personal "IdProducte", nom "Nom", descripció "Descripcio", categoria "Categoria", marca "Marca", preu "Preu" i pes "Pes". És el nucli en la comunicació entre l'usuari des de l'Agent Cercador i l'Agent Compra. Pot estar UbicatACentre, vinculant-se amb el CentreLogistic on s'emmagatzema físicament. És objecte de la relació TeProducte quan forma part d'una Comanda o Lot, i objectiu de SobreProducte en accions de compra, feedback, devolucions i recomanacions.

#### **5.2.1 ProducteIntern** {#5.2.1-producteintern}

Concepte que representa un producte gestionat internament per AgentZon, emmagatzemat als centres logístics propis i enviat pels nostres transportistes. Hereta tots els atributs de Producte i sempre té una ubicació física mitjançant UbicatACentre. És l'objecte de la relació TeProducteIntern quan es comunica informació específica de productes interns.

#### **5.2.2 ProducteExtern** {#5.2.2-producteextern}

Concepte que representa un producte proporcionat per un venedor extern. Hereta els atributs de Producte i afegeix un identificador propi del venedor "SkuExtern", un booleà "RequereixLogisticaExterna" que indica si la responsabilitat d'enviament és externa, i la data de registre "DataAlta". Es vincula amb el venedor mitjançant PertanyAVenedorExtern. És objecte de la relació TeProducteExtern en les comunicacions específiques amb venedors externs.

### **5.3 Lot** {#5.3-lot}

Concepte que representa una agrupació logística de productes interns per a un enviament conjunt. Té com a atributs un identificador personal "IdLot", la ciutat de destinació "Ciutat", la data prevista d'entrega "DataEntrega", el pes total "PesTotal" i l'estat de gestió "Estat" (OBERT, PREPARAT, ASSIGNAT, ENVIAT). És creat i gestionat per l'Agent Centre Logistic. Utilitza la relació TeProducteIntern per llistar els productes interns que conté. Es vincula a un transportista mitjançant AssignatATransportista. És objecte de la relació SobreLot en peticions de transport, ofertes i confirmacions d'enviament.

### **5.4 Comanda** {#5.4-comanda}

Concepte que representa una comanda al sistema. Té com a atributs un identificador personal "IdComanda", el nom del destinatari "Nom", l'adreça completa amb "Carrer" i "Ciutat", la prioritat "Prioritat", el mètode de pagament "MetodePagament", la data de compra "DataCompra", la data d'entrega estimada "DataEntrega", la data d'entrega definitiva "DataEntregaDefinitiva" i l'estat "Estat". Es vincula amb l'usuari mitjançant PertanyAUsuari i amb els productes mitjançant TeProducte. És objecte de la relació SobreComanda en múltiples accions: peticions de compra, registres d'historial, peticions de pagament, feedback i devolucions.

### **5.5 Devolucio** {#5.5-devolucio}

Concepte que representa una devolució d'un producte per un usuari. Té com a atributs un identificador personal "IdDevolucio", l'estat del tràmit "Estat", l'import a retornar "ImportPagament" i el motiu "MotiuDevolucio". Es vincula amb la comanda original mitjançant SobreComanda, amb l'usuari mitjançant PertanyAUsuari, amb el producte mitjançant SobreProducte i, si és un producte extern, amb el venedor mitjançant PertanyAVenedorExtern.

### **5.6 Feedback** {#5.6-feedback}

Concepte que representa l'opinió i valoració d'un consumidor sobre un article adquirit. Té com a atributs un identificador personal "IdFeedback", un text descriptiu "Comentari" i una valoració numèrica "Puntuacio". Es vincula amb la comanda mitjançant SobreComanda, amb l'usuari mitjançant PertanyAUsuari i amb el producte mitjançant SobreProducte.

### **5.7 Recomanacio** {#5.7-recomanacio}

Concepte que representa un conjunt de suggeriments personalitzats per a un usuari basats en el seu historial de cerques i compres. Aquesta entitat es vincula amb els articles suggerits mitjançant la relació SobreProducte. És generada per l'Agent Opinador com a resultat de l'acció de recomanació i es comunica mitjançant la relació GeneraRecomanacio des d'una RespostaRecomanacio.

### **5.8 CentreLogistic** {#5.8-centrelogistic}

Concepte que representa un centre logístic físic que emmagatzema productes interns. Té com a atributs un identificador personal "IdCentreLogistic" i la ciutat on es troba ubicat "Ciutat". És el destí de la relació UbicatACentre, on es recullen tots els productes interns que hi ha en inventari. Pot aparèixer en confirmacions de localització i dades d'enviament per indicar l'origen dels productes.

### **5.9 Pagament** {#5.9-pagament}

Concepte que representa l'acte de transacció econòmica vinculat a una operació dins del sistema. Té com a atributs un identificador personal "IdPagament", l'import de l'operació "ImportPagament", el mètode de pagament "MetodePagament", la data "DataPagament", l'estat "Estat" i el sentit del moviment "SentitPagament" (COBRAMENT per a ingressos de l'usuari cap a la botiga, PAGAMENT per a pagaments de la botiga a venedors externs o retorn de diners a usuaris). Es vincula amb la comanda mitjançant SobreComanda i amb els productes afectats mitjançant SobreProducte. Pot estar associat a un usuari via PertanyAUsuari o a un venedor extern via PertanyAVenedorExtern.

### **5.10 Comunicacio** {#5.10-comunicacio}

Concepte arrel que representa qualsevol missatge intercanviat entre agents. Es divideix en dues categories principals: Accio (peticions que esperen resposta) i Resposta (confirmacions o resultats).

#### **5.10.1 Accio** {#5.10.1-accio}

**AltaProducteExtern**

Acció de sol·licitar l'addició d'un producte d'un venedor extern al catàleg. Inclou atributs com Preu, Descripcio, DataAlta, RequereixLogisticaExterna i SkuExtern. Es vincula amb el producte mitjançant TeProducteExtern i amb el venedor mitjançant PertanyAVenedorExtern. Com a resposta, es rep una ConfirmacioAltaProducteExtern. És utilitzada pel VenedorExtern quan es comunica amb l'Agent Cercador.

**ConfirmacioEnviament**

Acció que comunica que un lot ja ha estat enviat i activa el cobrament associat. Inclou atributs com IdPagament, ImportPagament, MetodePagament, DataPagament, SentitPagament, Estat, CostTransport, DataEntregaDefinitiva, IdTransportista i NomTransportista. Es vincula amb la comanda via SobreComanda, el lot via SobreLot, el transportista via AssignatATransportista i els productes via TeProducte i SobreProducte. Com a resposta, es rep una ConfirmacioPagament. És utilitzada per l'Agent Centre Logistic quan es comunica amb l'Agent Cobrador.

**EleccioTransportista**

Acció de seleccionar formalment el proveïdor de transport per a un enviament concret, especificant NomTransportista, Ciutat, DataEntregaDefinitiva i CostTransport. Es vincula amb la comanda via SobreComanda, el lot via SobreLot i el transportista via AssignatATransportista. És utilitzada per l'Agent Centre Logistic per comunicar al transportista seleccionat que la seva oferta ha estat acceptada i fixar les condicions finals del servei.

**PeticioCerca**

Acció de generar una consulta semàntica mitjançant filtres com TextConsulta, CategoriaConsulta, MarcaConsulta, PreuMinim i PreuMaxim. Com a resposta, es rep un ResultatCerca. És utilitzada per l'usuari quan es comunica amb l'Agent Cercador per cercar productes amb paràmetres específics.

**PeticioCompra**

Acció d'iniciar la compra d'un conjunt de productes. Té com a atributs directes l'IdUsuari (via PertanyAUsuari) i el MetodePagament. Es vincula amb una estructura de comanda incrustada mitjançant la relació SobreComanda. Com a resposta, es rep un ResultatCompra. És utilitzada per l'usuari quan es comunica amb l'Agent Compra.

**PeticioConsultaComanda**

Acció de consultar les dades detallades d'una comanda específica. Es vincula amb la comanda mitjançant SobreComanda. Com a resposta, es rep un graf amb les dades de la comanda (no un tipus específic de resposta). És utilitzada quan es necessita recuperar informació completa d'una comanda.

**PeticioConsultaCompresUsuari**

Acció de consultar totes les compres realitzades per un usuari. Es vincula amb l'usuari mitjançant PertanyAUsuari. Com a resposta, es rep un ResultatConsultaCompresUsuari amb la llista de comandes. És utilitzada per recuperar l'historial de compres d'un usuari.

**PeticioConsultaDadesBancariesVenedor**

Acció de consultar les dades bancàries d'un venedor extern. Es vincula amb el venedor mitjançant PertanyAVenedorExtern. Com a resposta, es rep un ResultatConsultaDadesBancariesVenedor amb la informació del venedor. És utilitzada per l'Agent Cobrador per obtenir les dades de pagament dels venedors.

**PeticioConsultaProductes**

Acció de consultar informació detallada d'un conjunt de productes pels seus identificadors. Es vincula amb els productes mitjançant SobreProducte. Com a resposta, es rep un ResultatConsultaProductes amb les dades completes dels productes. És utilitzada per obtenir informació actualitzada de productes específics.

**PeticioDevolucio**

Acció de sol·licitar la devolució d'un producte indicant IdDevolucio, ImportPagament i MotiuDevolucio. Es vincula amb la comanda via SobreComanda, l'usuari via PertanyAUsuari, el producte via SobreProducte i, si és extern, el venedor via PertanyAVenedorExtern. Com a resposta, es rep una ResolucioDevolucio. És utilitzada per l'usuari quan es comunica amb l'Agent Retornador.

**PeticioEnviamentExtern**

Acció de sol·licitar al venedor extern la gestió logística d'un producte amb enviament delegat. Inclou Ciutat, Carrer i Prioritat de l'adreça de destí. Es vincula amb la comanda via SobreComanda, el venedor via PertanyAVenedorExtern i els productes via TeProducteExtern. És utilitzada per l'Agent Compra quan es comunica amb l'Agent VenedorExtern per delegar l'enviament.

**PeticioFeedback**

Acció de sol·licitar l'opinió sobre un producte a un usuari, incloent IdFeedback, Comentari (pregunta opcional) i identificadors. Es vincula amb la comanda via SobreComanda, l'usuari via PertanyAUsuari i els productes via SobreProducte. Com a resposta, es rep una RespostaFeedback. És utilitzada per l'Agent Opinador quan es comunica amb l'usuari per sol·licitar la valoració dels productes comprats.

**PeticioPagament**

Acció de demanar processar un pagament especificant IdPagament, ImportPagament, MetodePagament i SentitPagament. Es vincula amb la comanda via SobreComanda, els productes via SobreProducte i, segons el sentit, amb l'usuari via PertanyAUsuari o el venedor via PertanyAVenedorExtern. Com a resposta, es rep una ConfirmacioPagament. És utilitzada per l'Agent Compra quan es comunica amb l'Agent Cobrador per processar el pagament d'una compra.

**PeticioRegistreCerca**

Acció de registrar una cerca a l'historial de l'usuari per a futures recomanacions. Inclou TextConsulta, CategoriaConsulta, MarcaConsulta, PreuMinim i PreuMaxim. Es vincula amb l'usuari via PertanyAUsuari i amb els productes trobats via MostraProducte. Com a resposta, es rep una ConfirmacioRegistreCerca. És utilitzada per l'Agent Cercador per registrar les cerques dels usuaris.

**PeticioRegistreCompra**

Acció de demanar a l'Agent Opinador que registri una comanda a l'historial. Es vincula amb l'usuari via PertanyAUsuari, la comanda via SobreComanda i els productes via SobreProducte. Com a resposta, es rep una ConfirmacioRegistreCompra. És utilitzada per l'Agent Compra per registrar les compres completades.

**PeticioRegistreDadesBancariesUsuari**

Acció de registrar les dades bancàries d'un usuari. Inclou DadesBancariesUsuari i MetodePagament. Es vincula amb l'usuari via PertanyAUsuari. Com a resposta, es rep una ConfirmacioRegistreDadesBancaries. És utilitzada per l'Agent Cobrador per mantenir les dades de pagament dels usuaris.

**PeticioRegistreDadesBancariesVenedor**

Acció de registrar les dades bancàries d'un venedor extern. Inclou DadesBancariesVenedorExtern i Nom. Es vincula amb el venedor via PertanyAVenedorExtern. Com a resposta, es rep una ConfirmacioRegistreDadesBancaries. És utilitzada per l'Agent Cobrador per mantenir les dades de cobrament dels venedors.

**PeticioRegistreProducteExternCompra**

Acció de notificar el registre d'un producte extern durant una compra. Inclou IdProducte, RequereixLogisticaExterna i opcionalment IdCentreLogistic. Es vincula amb el venedor via PertanyAVenedorExtern. Com a resposta, es rep una ConfirmacioRegistreProducteExternCompra. És utilitzada per l'Agent Compra per assegurar que els productes externs estan correctament registrats.

**PeticioRetornDiners**

Acció de sol·licitar la devolució de diners a un usuari o venedor. Inclou IdDevolucio, ImportPagament i MotiuDevolucio. Es vincula amb la comanda via SobreComanda, l'usuari via PertanyAUsuari, els productes via SobreProducte i, si correspon, el venedor via PertanyAVenedorExtern. Com a resposta, es rep una ConfirmacioRetornDiners. És utilitzada per l'Agent Retornador quan es comunica amb l'Agent Cobrador.

**PeticioTransport**

Acció de sol·licitar l'enviament d'un lot amb Ciutat, DataEntrega i PesTotal. Es vincula amb el lot via SobreLot i la comanda via SobreComanda. Com a resposta, es rep una RespostaOfertaTransport. És utilitzada per l'Agent Centre Logistic quan es comunica amb els Transportistes per negociar l'enviament de lots.

**PeticioCobrament**

Acció de calcular l'import a cobrar per un enviament extern. Inclou PreuProducte i CostTransport. Es vincula amb l'usuari via PertanyAUsuari. És utilitzada per l'Agent Compra quan necessita calcular l'import total d'una compra amb productes externs.

**ProducteLocalitzat**

Acció que indica la localització d'un producte en un centre per a la seva reserva i enviament. Inclou Ciutat i DataEntrega. Es vincula amb l'usuari via PertanyAUsuari, el producte (intern) via TeProducteIntern i el centre via UbicatACentre. Com a resposta, es rep una ConfirmacioLocalitzacio. És utilitzada per l'Agent Compra quan comunica a l'Agent Centre Logistic que un producte ha d'ésser localitzat i assignat a un lot per a l'enviament.

#### **5.10.2 Resposta** {#5.10.2-resposta}

**ConfirmacioAltaProducteExtern**

Resposta que confirma que un producte extern ha estat registrat correctament al catàleg. Es vincula amb el producte via SobreProducte i TeProducteExtern, incloent IdProducte, SkuExtern i DataAlta. És enviada per l'Agent Cercador quan ha emmagatzemat les dades del producte.

**ConfirmacioLocalitzacio**

Resposta que confirma la reserva i localització de productes associats a un lot logístic. Té com a atributs Estat, Ciutat i DataEntrega. Es vincula amb la comanda via SobreComanda, el lot via SobreLot, l'usuari via PertanyAUsuari, el producte via TeProducteIntern i opcionalment la petició original via EsRespostaA. És enviada per l'Agent Centre Logistic quan confirma la reserva d'estoc.

**ConfirmacioPagament**

Resposta que indica que el pagament ha estat processat i la transacció validada. Inclou IdPagament, ImportPagament, MetodePagament, SentitPagament, Estat, DataPagament i CostTransport. Es vincula amb la comanda via SobreComanda, els productes via SobreProducte i opcionalment la petició via EsRespostaA. És enviada per l'Agent Cobrador confirmant l'operació.

**ConfirmacioRegistreCompra**

Resposta que confirma que la compra ha estat registrada correctament a l'historial de compres de l'usuari. Es vincula amb la comanda via SobreComanda i opcionalment la petició via EsRespostaA. És enviada per l'Agent Opinador a l'Agent Compra.

**ConfirmacioRegistreCerca**

Resposta que confirma el registre d'una cerca a l'historial. Es vincula amb l'usuari via PertanyAUsuari i opcionalment la petició via EsRespostaA. És enviada per l'Agent Opinador.

**ConfirmacioRegistreDadesBancaries**

Resposta que confirma el registre de dades bancàries d'un usuari o venedor. Inclou Estat. Es vincula amb l'usuari via PertanyAUsuari o amb el venedor via PertanyAVenedorExtern, i opcionalment la petició via EsRespostaA. És enviada per l'Agent Cobrador.

**ConfirmacioRegistreProducteExternCompra**

Resposta que confirma el registre d'un producte extern en el context d'una compra. Inclou IdProducte i es vincula amb la petició via EsRespostaA. És enviada per l'Agent Cercador.

**ConfirmacioRetornDiners**

Resposta que confirma que els diners han estat retornats correctament. Inclou IdDevolucio, ImportPagament i Estat. Es vincula amb la comanda via SobreComanda i opcionalment la petició via EsRespostaA. És enviada per l'Agent Cobrador.

**DadesEnviament**

Resposta que comunica que un lot ja té un transportista assignat i una data definitiva d'entrega. Inclou Estat, Ciutat, DataEntrega, DataEntregaDefinitiva, NomTransportista i CostTransport. Es vincula amb la comanda via SobreComanda, el lot via SobreLot, el transportista via AssignatATransportista, els productes (externs) via TeProducteExtern i la petició original via EsRespostaA. És enviada per l'Agent Centre Logistic a l'Agent Compra.

*En el nostre cas, com que un lot passa d'estar ASSIGNAT a ENVIAT instantàniament, es fa servir aquest mateix missatge per notificar a l'Agent Compra que el producte ha estat enviat i actualitzar l'estat a la interfície.*

**ResolucioDevolucio**

Resposta que comunica la decisió final sobre una petició de devolució amb les instruccions corresponents. Inclou IdDevolucio, ImportPagament, Acceptada (booleà) i MotiuDevolucio. Es vincula amb la comanda via SobreComanda, l'usuari via PertanyAUsuari, els productes via SobreProducte i, si és extern, el venedor via PertanyAVenedorExtern, i opcionalment la petició via EsRespostaA. És enviada per l'Agent Retornador a l'usuari.

**RespostaFeedback**

Resposta que confirma que el feedback proporcionat per l'usuari ha estat registrat. Inclou IdFeedback, Puntuacio i Comentari. Es vincula amb la comanda via SobreComanda, l'usuari via PertanyAUsuari, els productes via SobreProducte i opcionalment la petició via EsRespostaA. És enviada per l'Agent Opinador.

**RespostaOfertaTransport**

Resposta que conté les ofertes dels transportistes amb preus i dates d'entrega per a un lot. Inclou NomTransportista, Ciutat, DataEntregaDefinitiva i CostTransport. Es vincula amb la comanda via SobreComanda, el lot via SobreLot, el transportista via AssignatATransportista i opcionalment la petició via EsRespostaA. És enviada pels Transportistes a l'Agent Centre Logistic.

**RespostaRecomanacio**

Resposta que conté les recomanacions personalitzades per a un usuari. Es vincula amb l'objecte Recomanacio via GeneraRecomanacio, el qual conté els productes recomanats via SobreProducte. És enviada per l'Agent Opinador com a resultat de l'algorisme de recomanació.

**ResultatCerca**

Resposta que conté els productes trobats segons els criteris de cerca. Inclou TotalResultats i es vincula amb els productes via MostraProducte, amb la petició via EsRespostaA. És enviada per l'Agent Cercador a l'usuari amb la informació detallada de cada producte localitzat.

**ResultatCompra**

Resposta enviada per l'Agent Compra com a retorn inicial a una PeticioCompra. Inclou DataEntrega. Es vincula amb la comanda via SobreComanda, la petició via EsRespostaA, i inclou nodes de ConfirmacioLocalitzacio per cada lot reservat als magatzems.

**ResultatConsultaCompresUsuari**

Resposta que conté la llista de compres d'un usuari. Es vincula amb l'usuari via PertanyAUsuari, les comandes via SobreComanda i opcionalment la petició via EsRespostaA. És enviada per l'Agent Opinador amb l'historial complet de compres.

**ResultatConsultaDadesBancariesVenedor**

Resposta amb les dades bancàries d'un venedor extern. Inclou DadesBancariesVenedorExtern i Nom. Es vincula amb el venedor via PertanyAVenedorExtern i opcionalment la petició via EsRespostaA. És enviada per l'Agent Cobrador.

**ResultatConsultaProductes**

Resposta amb la informació detallada d'un conjunt de productes. Es vincula amb els productes via SobreProducte i opcionalment la petició via EsRespostaA. És enviada per l'Agent Cercador amb les dades completes dels productes sol·licitats.
