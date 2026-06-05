
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

**PeticioConsultaComanda**

**PeticioConsultaCompresUsuari**

**PeticioConsultaDadesBancariesVenedor**

**PeticioConsultaProductes**

**PeticioDevolució**

La PeticioDevolució és l'acció de sol·licitar la devolució d’un producte indicant ordre, identificador del producte, quantitat i motiu. Com a resposta, es rep un *ResultatDevolució*. És utilitzada per l'usuari quan es comunica amb l'Agent Retornador per sol·licitar la devolució d'un producte.

**PeticioEnviamentExtern**

La PeticioEnviamentExtern és l’acció de sol·licitar al venedor extern la gestió logística d’un producte amb enviament delegat, incloent dades bàsiques de comanda i destí. És utilitzada per l’Agent Compra quan es comunica amb l’Agent Venedor Extern.

**PeticioFeedback**

La PeticioFeedback és l'acció de sol·licitar l’opinió sobre un producte a un usuari, incloent comentari i identificadors (usuari, ordre, producte). Com a resposta, es rep un *ResultatFeedback*. És utilitzada per l'Agent Opinador quan es comunica amb l'usuari per sol·licitar la valoració dels productes comprats.

**PeticioPagament**

La PeticioPagament és l'acció de demanar processar un pagament especificant import, moneda, mètode (targeta, transferència), i dades de facturació. Com a resposta, es rep un *ResultatPagament*. És utilitzada per l'Agent Compra quan es comunica amb l'Agent Cobrador per processar el pagament d'una compra.

**PeticioRegistreCerca**

**PeticioRegistreCompra**

És l'acció de demanar a l'Agent Opinador que registri una comanda a l'historial. Conté els atributs directes IdComanda i IdUsuari, apunta a la comanda mitjançant la relació SobreComanda i llista de forma explícita tots els articles adquirits mitjançant la relació SobreProducte. Com a resposta, es rep un ConfirmacioRegistreCompra.

**PeticioRegistreDadesBancariesUsuari**

**PeticioRegistreDadesBancariesVenedorExtern**

**PeticioRegistreProducteExternCompra**

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

**ConfirmacioRegistreCerca**

**ConfirmacioRegistreCompra**

Resposta que confirma que la compra ha estat registrada correctament a l'historial de compres de l'usuari. És enviada per l'Agent Opinador a l'Agent Compra perquè sàpiga que les dades de la compra ja estan disponibles.

**ConfirmacioRegistreDadesBancaries**

**ConfirmacioRegistreProducteExternCompra**

**ConfirmacioRetornDiners**

**DadesEnviament**

Resposta que comunica que un lot ja té un transportista assignat i una data definitiva d’entrega. Inclou atributs com IdComanda, IdLot, IdTransportista, NomTransportista, CostTransport, Ciutat i DataEntregaDefinitiva. És enviada per l’Agent Centre Logístic a l’Agent Compra perquè aquest pugui actualitzar l’estat de la comanda i informar l’usuari dels detalls definitius de l’enviament.

*En el nostre cas, com que un lot passa d’estar ASSIGNAT a ENVIAT instantàniament (no sabem quan el Transportista realment envia el lot), es fa servir aquest mateix missatge (dins el protocol InformacióEnviament) per notificar a Ag. Compra que el producte ha estat enviat i, per tant, actualitzar l’estat a la interfície.*

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

**ResultatConsultaCompresUsuari**

**ResultatConsultaDadesBancariesVenedor**

**ResultatConsultaProductes**

