**Agent cercador:**

- **Producte:** Representa un article estàndard dins del catàleg.	

  IdProducte, Nom, Descripcio, Categoria, Marca, Preu, Pes.

- **Producte Extern:** Representa un article enviat i registrat per un venedor extern. 

  Hereta els de Producte, i el codi hi afegeix: IdProducte, Nom, Marca, Categoria, Preu, Pes, Descripcio.

- **PeticioCerca (REQUEST):** Inicia el flux sol·licitant l'aplicació de filtres semàntics (text, marca, preus) sobre el catàleg general. Usuari (Interfície Web) → Agent Cercador

- **ResultatCerca (INFORM):** Resposta automàtica al missatge anterior. Retorna un llistat associant múltiples conceptes Producte trobats de forma síncrona. Agent Cercador → Usuari (Interfície Web)

- **PeticioRegistreProducteExtern (REQUEST):** Sol·licita la creació i desament d'un nou article de naturalesa externa directament a la ruta /comm del cercador. Venedor Extern → Agent Cercador

- **ConfirmacioRegistreProducte (INFORM):** Resposta asíncrona que notifica l'èxit de l'operació i confirma que les triples s'han guardat correctament al fitxer local productes.ttl. Agent Cercador → Venedor Extern

**Agent compra:** 

- **Comanda:** Representa l'agrupació de productes adquirits per un usuari, les seves dades de lliurament i l'estat del procés.

  Atributs: IdComanda, IdUsuari, Nom, Carrer, Ciutat, Prioritat, Estat, MetodePagament, DataEntrega, DataEntregaDefinitiva.

  Relacions: TeProducte (apunta a instàncies de Producte).

- **Lot:** Agrupació logística d'articles gestionada per un centre logístic concret per al seu transport definitiu.

  Atributs: IdLot, Ciutat, Estat, DataEntrega, IdCentreLogistic.

  Relacions: TeProducte (apunta a instàncies de Producte).

- **ConfirmacioLocalitzacio:** Sub-node semàntic que serveix per certificar que uns productes d'una comanda han estat físicament localitzats i reservats en un magatzem/lot concret.

  Atributs: IdComanda, IdLot, Estat, Ciutat, DataEntrega.

  Relacions: SobreComanda (apunta a Comanda), SobreLot (apunta a Lot), TeProducte (apunta a instàncies de Producte).

- **PeticioCompra (REQUEST):** Inicia la tramitació d'un carret de la compra amb les preferències de l'usuari. Té els atributs IdUsuari i MetodePagament i la relació SobreComanda. Usuari (Interfície)--\>Agent Compra.

- **ResultatCompra (INFORM):** Resposta inicial que confirma la creació de la comanda, el seu estat i l'estimació de temps. Té els atributs IdComanda, Estat, DataEntrega i la relació SobreComanda (apunta a la comanda) i inclou sub-nodes connectats de tipus ConfirmacioLocalitzacio. Agent Compra--\>Usuari (Interfície).

- **PeticioPagament (REQUEST):** Sol·licita l'execució del cobrament bancari de la comanda en base a un mètode determinat. Agent Compra--\>Agent Cobrador.

- **PeticioEnviamentExtern (REQUEST):** Sol·licita a un proveïdor aliè a la plataforma que s'encarregui de fer el lliurament dels productes comprats. Té els atributs IdComanda, Ciutat, Prioritat i la relació SobreComanda. Agent Compra--\>Agent Venedor Extern.

- **DadesEnviament (INFORM):** Notificació que actualitza que un lot logístic ja té un transportista assignat abans de sortir físicament. Agent Centre Logístic--\>Agent Compra.

- **ConfirmacioEnviament (INFORM):** Notificació formal que indica que un paquet o lot s'ha expedit. El node principal conté IdComanda i DataEntregaDefinitiva, i es ramifica en sub-nodes amb atributs del lot (IdLot, NomTransportista, CostTransport, etc.) i relacions SobreLot, SobreComanda i AssignatATransportista. Agent Centre Logístic--\>Agent Compra.

- **PeticioRegistreCompra (REQUEST):** Sol·licita l'emmagatzematge perpetu de la transacció finalitzada per al perfil de l'usuari. Té els atributs IdComanda, IdUsuari i les relacions SobreComanda i SobreProducte. Agent Compra →  Agent Opinador.

**Agent Opinador:**

- **Feedback:** Representa l'opinió i valoració d'un usuari sobre un article adquirit 

  Atributs: IdFeedback, IdUsuari, IdComanda, Comentari, Puntuacio

  Relacions: SobreProducte (apunta a la instància de Producte de la qual es dona l'opinió).

- **Devolucio:** Representa la sol·licitud formal d'un client per retornar un producte 

  Atributs: IdDevolucio, IdComanda, IdUsuari, MotiuDevolucio, Quantitat

  Relacions: SobreProducte (apunta al producte concret que es vol retornar).

- **ResolucioDevolucio:** Representa el dictamen i resposta del sistema sobre una devolució 

  Atributs: IdDevolucio, IdComanda, IdUsuari, ImportPagament, Acceptada (booleà), MotiuDevolucio

  Relacions: SobreProducte (llista de productes retornats).

- **RespostaFeedback:** Confirmació pura del sistema de que una opinió ha estat guardada 

  Atributs: IdFeedback, IdUsuari, IdComanda

  Relacions: Cap de sortida (actua com a simple confirmació d'emmagatzematge).

- **RespostaRecomanacio:** Conjunt de suggeriments personalitzats de productes per a un usuari 

  Atributs: IdUsuari, TotalResultats

  Relacions: MostraProducte (apunta a cadascun dels productes recomanats per a l'usuari).

- **PeticioRegistreCompra (REQUEST):** Sol·licita formalment l'emmagatzematge perpetu de la transacció finalitzada. Conté els atributs IdComanda, IdUsuari i les relacions SobreComanda i SobreProducte. Agent Compra \--\> Agent Opinador.

- **ConfirmacioRegistreCompra (INFORM):** Resposta que confirma que les dades de la compra s'han indexat correctament a l'historial del client. Agent Opinador \--\> Agent Compra.

- **PeticioFeedback (REQUEST):** Nota del codi: Utilitzada conceptualment a la interfície web interna quan l'usuari demana valorar un producte comprat.

- **RespostaFeedback (INFORM):** Missatge asíncron que conté la nota, el comentari i l'ID del producte que l'usuari ha decidit enviar, per tal que es desi a la base de dades. Conté els atributs IdFeedback, IdUsuari, IdComanda i la relació SobreProducte. Usuari (Interfície) \--\> Agent Opinador.

- **PeticioDevolucio (REQUEST):** Sol·licitud enviada des de la interfície per iniciar el tràmit de retorn. Conté els atributs IdDevolucio, IdComanda, IdUsuari, MotiuDevolucio, Quantitat i la relació SobreProducte. Usuari (Interfície) \--\> Agent Opinador.

- **ResolucioDevolucio (INFORM):** Resposta definitiva de l'agent al client determinant si s'aprova el reemborsament econòmic o es denega. Conté els atributs IdDevolucio, IdComanda, IdUsuari, ImportPagament, Acceptada, MotiuDevolucio i la relació SobreProducte. Agent Opinador \--\> Usuari (Interfície).

- **RespostaRecomanacio (INFORM):** Enviament periòdic o sota demanda d'un graf que llista productes afins als gustos del client. Conté els atributs IdUsuari, TotalResultats i la relació MostraProducte apuntant a cadascun d'ells. Agent Opinador \--\> Usuari (Interfície).

**Agent retornador:**

- **PeticioDevolucio (REQUEST):** Missatge amb el qual l'usuari sol·licita formalment retornar un producte. Conté els atributs IdDevolucio, IdComanda, IdUsuari, MotiuDevolucio, Quantitat i la relació SobreProducte. Usuari (Interfície) \--\> Agent Retornador.  
- **ResolucioDevolucio (INFORM):** Resposta síncrona en la qual l'agent comunica la decisió final al client (si està acceptada o no) i l'import exacte del desavantatge econòmic. Conté els atributs IdDevolucio, IdComanda, IdUsuari, ImportPagament, Acceptada, MotiuDevolucio i la relació SobreProducte. Agent Retornador \--\> Usuari (Interfície).  
- **PeticioPagament (REQUEST):** Acció de devolució de capital a favor del client. L'agent Retornador reutilitza aquesta estructura del protocol de pagaments enviant l'import calculat de la devolució en sentit negatiu o de devolució (reemborsament) indicant les dades bancàries o de targeta. Agent Retornador \--\> Agent Cobrador.

**Agent centre logístic:**

- **CentreLogistic** (Representa la infraestructura del magatzem physically responsable de custodiar els productes)  
  Atributs: IdCentreLogistic (Codi alfanumèric del magatzem, ex: "CL-BCN"), Ciutat (Ubicació on es troba localitzat).  
- **Lot** (Agrupació d'embalatges generada per expedir comandes conjuntes cap a una mateixa destinació)  
  Atributs: IdLot (Codi del lot), Ciutat (Destinació del tram), Estat (Fase logística, ex: "ASSIGNAT"), DataEntrega (Previsió de lliurament).  
  Relacions: TeProducte (Apuntador cap a les instàncies de producte que conté el paquet).  
- **ConfirmacioLocalitzacio** (Node de certificació on el magatzem bloqueja l'estoc físic d'una venda)  
  Atributs: IdComanda (Venda vinculada), IdLot (Lot assignat), Estat (Condició interna), Ciutat (Destinació), DataEntrega (Previsió).  
  Relacions: SobreComanda (Apunta a la comanda), SobreLot (Apunta al lot), TeProducte (Llista de productes bloquejats).  
- **DadesEnviament** (Estructura informativa que lliga el lot a un transportista concret)  
  Atributs: IdComanda (Venda), IdLot (Lot), IdTransportista (Codi de l'agència de transport), NomTransportista (Nom de l'empresa), Ciutat (Destí), DataEntregaDefinitiva (Data exacta d'arribada acordada), CostTransport (Preu flotant del transport).  
  Relacions: SobreLot (Apunta al lot), SobreComanda (Apunta a la comanda).  
- **ConfirmacioEnviament** (Veredicte de sortida física on el magatzem formalitza l'expedició)  
  Atributs: IdComanda, DataEntregaDefinitiva (Globals de comanda); IdLot, IdTransportista, NomTransportista, Ciutat, DataEntregaDefinitiva, CostTransport (Detalls interns dels sub-nodes de lot).  
  Relacions: SobreLot (Apunta al lot), SobreComanda (Apunta a la comanda), AssignatATransportista (Enllaça cap a l'agent transportista), TeProducte (Llista final).  
- **PeticioLocalitzacioProductes (REQUEST):** Nota del codi: Utilitzada internament per l'Agent Compra enviant un llistat de gènere per conèixer la seva disponibilitat als magatzems. Agent Compra → Agent Centre Logístic.  
- **ConfirmacioLocalitzacio (INFORM):** Resposta on el magatzem certifica haver retingut i encabit la mercaderia a un lot. Conté els atributs de lotatge (IdComanda, IdLot, Estat, Ciutat, DataEntrega) i les relacions SobreComanda, SobreLot i TeProducte. Agent Centre Logístic → Agent Compra.  
- **PeticioTransport (REQUEST):** Acció de sol·licitud on el magatzem llança una licitació de càrrec enviant dades de pes i volum per demanar pressupost. Agent Centre Logístic → Agent Transportista.  
- **DadesEnviament (INFORM):** Notificació que actualitza que el magatzem ha lligat amb èxit un transportista al paquet de forma prèvia a la seva sortida. Conté els atributs IdComanda, IdLot, IdTransportista, NomTransportista, Ciutat, DataEntregaDefinitiva, CostTransport i les relacions SobreLot i SobreComanda. Agent Centre Logístic → Agent Compra.  
- **ConfirmacioEnviament (INFORM):** Notificació d'expedició definitiva de mercaderia. Conté a l'arrel l'atribut IdComanda i DataEntregaDefinitiva i bifurca asíncronament sub-nodes amb les dades reals del transport (IdLot, NomTransportista, CostTransport) i les relacions SobreLot, SobreComanda, AssignatATransportista i TeProducte. Agent Centre Logístic → Agent Compra.  
- **PeticioCobramentIntern (REQUEST):** Acció on el Centre Logístic demana moure fons comptables interns cap al seu balanç per cobrir les despeses operatives de preparació i tramesa. Agent Centre Logístic → Agent Cobrador.

Agent venedor extern:

- ProducteExtern (Representa l'estructura d'un producte propietat d'un comerciant aliè a la plataforma)  
  Atributs: IdProducte (Codi identificador de l'article extern), Nom (Nom comercial de cara al públic), Descripcio (Text descriptiu de les funcionalitats), Categoria (Grup o etiqueta de classificació del catàleg), Marca (Fabricant de l'article), Preu (Valor econòmic flotant), Pes (Massa flotant utilitzada per a la logística).  
- PeticioEnviamentExtern (Entitat semàntica que recull les obligacions de lliurament delegat d'una compra)  
  Atributs: IdComanda (Codi de la comanda original realitzada per l'usuari), Ciutat (Localitat geogràfica de destinació final), Prioritat (Urgència del transport acordada, ex: "Alta").  
  Relacions: SobreComanda (Apunta cap a la instància de Comanda global).  
- DadesEnviament (Estructura de confirmació del lliurament on el venedor extern assigna les dades de repartiment)  
  Atributs: IdComanda (Referència de la comanda), Ciutat (Destinació), DataEntrega (Previsió exacta establerta pel venedor), Estat (Condició de la distribució, ex: "DELEGAT"), NomTransportista (Nom de la companyia o el literal "Venedor extern"), IdTransportista (Identificador del venedor com a responsable del transport).  
  Relacions: TeProducte (Llista de nodes ProducteExtern que viatgen en aquest paquet).  
- PeticioRegistreProducteExtern (REQUEST): Sol·licita la creació i desament d'un nou article de naturalesa externa directament a la ruta /comm del cercador. Conté els atributs de ProducteExtern. Venedor Extern → Agent Cercador.  
- ConfirmacioRegistreProducte (INFORM): Resposta asíncrona que notifica l'èxit de l'operació i confirma que les triples s'han guardat correctament al fitxer local productes.ttl. Agent Cercador → Venedor Extern.  
- PeticioEnviamentExtern (REQUEST): Sol·licita a un proveïdor aliè a la plataforma que s'encarregui de fer el lliurament dels productes comprats. Té els atributs IdComanda, Ciutat, Prioritat i la relació SobreComanda. Agent Compra → Agent Venedor Extern.  
- DadesEnviament (INFORM): Notificació de resposta on el venedor extern assumeix la comanda i retorna les metadades de l'expedició. Conté els atributs IdComanda, Ciutat, DataEntrega, Estat, NomTransportista, IdTransportista i la relació TeProducte. Agent Venedor Extern → Agent Compra.  
- PeticioRegistreDadesVenedor (REQUEST): Acció on el venedor extern envia les seves credencials de facturació i mètodes de cobrament per ser validat en el sistema financer. Venedor Extern → Agent Cobrador.  
- ConfirmacioRegistreDades (INFORM): Resposta asíncrona de la passarel·la que valida el compte de destí per a futures transferències comercials. Agent Cobrador → Venedor Extern.

Agent transportista:

- OfertaTransport (Representa la proposta comercial formal de preu i terminis que fa un transportista per moure un lot)  
  Atributs: \* IdLot: Identificador únic del lot de mercaderia pel qual es licita. IdTransportista: Codi identificador de l'agència de transports que fa l'oferta.  
  NomTransportista: Nom comercial de l'empresa de transports.  
  CostTransport: Preu flotant de l'enviament proposat per l'agència.  
  DataEntregaDefinitiva: Previsió exacta del dia de lliurament calculada segons els terminis de l'empresa.  
  Ciutat: Localitat geogràfica de destinació final de la mercaderia.  
  Relacions: \* SobreLot: Apunta directament cap al node de la classe Lot associat a l'oferta.  
- Lot (Instància compartida per referenciar el paquet físic de productes a transportar)  
  Atributs: IdLot, Ciutat, Estat, DataEntrega, IdCentreLogistic.  
- PeticioTransport (REQUEST): Sol·licitud enviada pel magatzem demanant tarifes de transport. Conté les dades de destí i pes del lot. Agent Centre Logístic → Agent Transportista.  
- RespostaOfertaTransport (INFORM): Proposta comercial formal amb el cost calculat i la data de lliurament per al lot. Conté els atributs IdLot, IdTransportista, NomTransportista, CostTransport, DataEntregaDefinitiva, Ciutat i la relació SobreLot. Agent Transportista → Agent Centre Logístic.  
- AcceptTransportOffer (ACCEPT-PROPOSAL): Missatge amb el qual el centre logístic accepta formalment el pressupost ofertat per l'agència de transports. Agent Centre Logístic → Agent Transportista.  
- RejectTransportOffer (REJECT-PROPOSAL): Missatge de rebuig de l'oferta en cas que un altre transportista hagi ofert un millor preu o termini. Agent Centre Logístic → Agent Transportista.

Agent cobrador:

- **PeticioPagament:** Representa la sol·licitud formal per carregar o moure un determinat capital a través de la passarel·la bancària.  
  Atributs: IdComanda, ImportPagament, MetodePagament, SentitPagament  
- **ConfirmacioPagament:** Certificat emès pel Cobrador que valida que la transacció financera s'ha executat amb èxit.  
  Atributs: IdComanda, ImportPagament, Estat  
  Relacions: EsRespostaA  
- **PeticioCobramentIntern:** Estructura utilitzada pels Centres Logístics per demanar i extreure crèdits interns per despeses de gestió i transport.  
  Atributs: IdComanda, IdLot, ImportPagament, IdCentreLogistic  
- **PeticioRetornDiners:** Sol·licitud de reemborsament econòmic generada cap a la passarel·la arran d'una devolució acceptada pel sistema.  
  Atributs: IdDevolucio, IdComanda, ImportPagament, MotiuDevolucio, IdUsuari  
  Relacions: SobreProducte  
- **ConfirmacioRetornDiners:** Certificat final que confirma que el reemborsament dels diners s'ha aplicat correctament al compte de l'usuari.  
  Atributs: IdDevolucio, IdComanda, ImportPagament, Estat  
  Relacions: EsRespostaA  
- **PeticioRegistreDadesBancariesUsuari / PeticioRegistreDadesBancariesVenedor:** Estructures per donar d'alta i guardar de forma segura les credencials financeres a la passarel·la.  
  Atributs: IdUsuari / IdVenedor, DadesBancaries, MetodePagament  
- **PeticioPagament (REQUEST):** Sol·licita l'execució del cobrament bancari de la comanda en base a un mètode determinat (Sentit: COBRAMENT). Agent Compra → Agent Cobrador  
- **ConfirmacioPagament (INFORM):** Resposta de la passarel·la que valida que el cobrament o transferència interna s'ha efectuat. Conté els atributs IdComanda, ImportPagament, Estat i la relació EsRespostaA. Agent Cobrador → Agent Compra o Agent Centre Logístic  
- **PeticioCobramentIntern (REQUEST):** Sol·licita extreure de la caixa comuna els fons per cobrir els paquets. Conté els atributs IdComanda, IdLot, ImportPagament i IdCentreLogistic. Agent Centre Logístic → Agent Cobrador  
- **PeticioRetornDiners (REQUEST):** Sol·licitud de reemborsament de fons cap al client (Sentt: PAGAMENT). Conté els atributs IdDevolucio, IdComanda, ImportPagament, MotiuDevolucio, IdUsuari i la relació SobreProducte. Agent Retornador → Agent Cobrador  
- **ConfirmacioRetornDiners (INFORM):** Resposta on la passarel·la certifica el tancament del reemborsament. Conté els atributs IdDevolucio, IdComanda, ImportPagament, Estat i la relació EsRespostaA. Agent Cobrador → Agent Retornador  
- **PeticioRegistreDadesVenedor (REQUEST):** Acció on el venedor extern demana registrar el seu compte per a les liquidacions. Venedor Extern → Agent Cobrador  
- **ConfirmacioRegistreDades (INFORM):** Resposta asíncrona de la passarel·la que valida que l'entitat financera ja pot operar. Agent Cobrador → Venedor Extern  
  i

  **1\. Models de Dades Unificats**   
* **Producte**  
  * **Descripció:** Article estàndard dins del catàleg general.  
  * **Atributs:** IdProducte, Nom, Descripcio, Categoria, Marca, Preu, Pes.  
* **Producte Extern**  
  * **Descripció:** Article que hereta de Producte, registrat i propietat d'un comerciant aliè.  
  * **Atributs:** IdProducte, Nom, Descripcio, Categoria, Marca, Preu, Pes.  
* **Comanda**  
  * **Descripció:** Agrupació de productes comprats per un usuari i l'estat del seu cicle de vida.  
  * **Atributs:** IdComanda, IdUsuari, Nom, Carrer, Ciutat, Prioritat, Estat, MetodePagament, DataEntrega, DataEntregaDefinitiva.  
  * **Relacions:** TeProducte (apunta a instàncies de Producte).  
* **Lot**  
  * **Descripció:** Agrupació logística d'articles en un magatzem per al seu transport conjunt.  
  * **Atributs:** IdLot, Ciutat, Estat, DataEntrega, IdCentreLogistic.  
  * **Relacions:** TeProducte (apunta a instàncies de Producte).  
* **Centre Logistic**  
  * **Descripció:** Infraestructura física del magatzem responsable de custodiar l'estoc.  
  * **Atributs:** IdCentreLogistic, Ciutat.  
* **Feedback**  
  * **Descripció:** Opinió, comentari i valoració d'un usuari sobre un article adquirit.  
  * **Atributs:** IdFeedback, IdUsuari, IdComanda, Comentari, Puntuacio.  
  * **Relacions:** SobreProducte (apunta a la instància de Producte).  
* **Devolucio**  
  * **Descripció:** Sol·licitud formal i registre de la intenció de retornar un gènere.  
  * **Atributs:** IdDevolucio, IdComanda, IdUsuari, MotiuDevolucio, Quantitat.  
  * **Relacions:** SobreProducte (apunta a Producte).

  ## **2\. Flux de Missatges Emesos (Accions i Predicats Semàntics)**

Aquestes estructures **no són models de dades persistents**. Són els objectes de l'ontologia que fan d'embolcall (*AgentAction* o *Predicate*) per als missatges FIPA-ACL. S'organitzen segons qui els **emet**:

### **Usuari (Interfície Web)**

* **PeticioCerca (REQUEST):** *\[Acció\]* Demana aplicar filtres sobre el catàleg.  
  * *Atributs:* Text de cerca, marca, preus. $\\rightarrow$ *Cap a Agent Cercador*.  
* **PeticioCompra (REQUEST):** *\[Acció\]* Inicia la tramitació del carret de la compra.  
  * *Atributs:* IdUsuari, MetodePagament. *Relacions:* SobreComanda. $\\rightarrow$ *Cap a Agent Compra*.  
* **RespostaFeedback (INFORM):** *\[Predicat/Acció\]* Envia l'opinió de l'usuari perquè es desi.  
  * *Atributs:* IdFeedback, IdUsuari, IdComanda. *Relacions:* SobreProducte. $\\rightarrow$ *Cap a Agent Opinador*.  
* **PeticioDevolucio (REQUEST):** *\[Acció\]* Sol·licitud per demanar el retorn d'un producte.  
  * *Atributs:* IdDevolucio, IdComanda, IdUsuari, MotiuDevolucio, Quantitat. *Relacions:* SobreProducte. $\\rightarrow$ *Cap a Agent Opinador o Retornador*.

  ### **Agent Cercador**

* **ResultatCerca (INFORM):** *\[Predicat\]* Retorna el llistat síncron de coincidències.  
  * *Contingut:* Llista d'instàncies del model Producte. $\\rightarrow$ *Cap a Usuari*.  
* **ConfirmacioRegistreProducte (INFORM):** *\[Predicat\]* Notifica que les triples s'han guardat a productes.ttl.  
  * *Atributs:* Èxit (booleà), IdProducte. $\\rightarrow$ *Cap a Agent Venedor Extern*.

  ### **Agent Compra**

* **ResultatCompra (INFORM):** *\[Predicat\]* Confirma la creació de la comanda i l'estimació inicial.  
  * *Atributs:* IdComanda, Estat, DataEntrega. *Relacions:* SobreComanda. *Sub-nodes:* ConfirmacioLocalitzacio. $\\rightarrow$ *Cap a Usuari*.  
* **PeticioPagament (REQUEST):** *\[Acció\]* Sol·licita realitzar un cobrament de targeta o bancari.  
  * *Atributs:* IdComanda, ImportPagament, MetodePagament, Sentit ("COBRAMENT"). $\\rightarrow$ *Cap a Agent Cobrador*.  
* **PeticioLocalitzacioProductes (REQUEST):** *\[Acció\]* Demana comprovar disponibilitat als magatzems.  
  * *Contingut:* Llista de IdProducte i quantitats. $\\rightarrow$ *Cap a Agent Centre Logístic*.  
* **PeticioEnviamentExtern (REQUEST):** *\[Acció\]* Delega el lliurament logístic a un proveïdor extern.  
  * *Atributs:* IdComanda, Ciutat, Prioritat. *Relacions:* SobreComanda. $\\rightarrow$ *Cap a Agent Venedor Extern*.  
* **PeticioRegistreCompra (REQUEST):** *\[Acció\]* Demana desar la transacció finalitzada a l'historial del client.  
  * *Atributs:* IdComanda, IdUsuari. *Relacions:* SobreComanda, SobreProducte. $\\rightarrow$ *Cap a Agent Opinador*.

  ### **Agent Opinador**

* **ConfirmacioRegistreCompra (INFORM):** *\[Predicat\]* Certifica que la compra s'ha indexat a l'historial.  
  * *Atributs:* IdComanda, Estat. $\\rightarrow$ *Cap a Agent Compra*.  
* **ResolucioDevolucio (INFORM):** *\[Predicat\]* Resposta amb el veredicte de la devolució.  
  * *Atributs:* IdDevolucio, IdComanda, IdUsuari, ImportPagament, Acceptada (booleà), MotiuDevolucio. *Relacions:* SobreProducte. $\\rightarrow$ *Cap a Usuari*.  
* **RespostaRecomanacio (INFORM):** *\[Predicat\]* Graf amb els suggeriments personalitzats enviats al client.  
  * *Atributs:* IdUsuari, TotalResultats. *Relacions:* MostraProducte (llista de Producte). $\\rightarrow$ *Cap a Usuari*.

  ### **Agent Retornador**

* **ResolucioDevolucio (INFORM):** *\[Predicat\]* Comunica síncronament la decisió de la devolució i el reemborsament econòmic calculat.  
  * *Atributs:* (Mateixos atributs que la resolució de l'opinador). $\\rightarrow$ *Cap a Usuari*.  
* **PeticioRetornDiners (REQUEST):** *\[Acció\]* Sol·licita la devolució física del capital a favor del client.  
  * *Atributs:* IdDevolucio, IdComanda, ImportPagament, MotiuDevolucio, IdUsuari. *Relacions:* SobreProducte. $\\rightarrow$ *Cap a Agent Cobrador*.

  ### **Agent Centre Logístic**

* **ConfirmacioLocalitzacio (INFORM):** *\[Predicat\]* Certifica el bloqueig de l'estoc dins d'un lot.  
  * *Atributs:* IdComanda, IdLot, Estat, Ciutat, DataEntrega. *Relacions:* SobreComanda, SobreLot, TeProducte. $\\rightarrow$ *Cap a Agent Compra*.  
* **PeticioTransport (REQUEST):** *\[Acció\]* Llança una licitació enviant dades de pes i destí del lot per demanar pressupost.  
  * *Atributs:* IdLot, PesTotal, Volum, Ciutat. $\\rightarrow$ *Cap a Agent Transportista*.  
* **AcceptTransportOffer / RejectTransportOffer (ACCEPT/REJECT-PROPOSAL):** *\[Accions\]* Accepta o rebutja formalment la licitació d'una agència.  
  * *Atributs:* IdLot, IdTransportista. $\\rightarrow$ *Cap a Agent Transportista*.  
* **DadesEnviament (INFORM):** *\[Predicat\]* Notificació que vincula el paquet a una agència concreta abans de sortir.  
  * *Atributs:* IdComanda, IdLot, IdTransportista, NomTransportista, Ciutat, DataEntregaDefinitiva, CostTransport. *Relacions:* SobreLot, SobreComanda. $\\rightarrow$ *Cap a Agent Compra*.  
* **ConfirmacioEnviament (INFORM):** *\[Predicat\]* Notificació formal de sortida física (expedició).  
  * *Atributs globals:* IdComanda, DataEntregaDefinitiva. *Sub-nodes de lot:* IdLot, NomTransportista, CostTransport. *Relacions:* SobreLot, SobreComanda, AssignatATransportista, TeProducte. $\\rightarrow$ *Cap a Agent Compra*.  
* **PeticioCobramentIntern (REQUEST):** *\[Acció\]* Demana fons comptables interns per cobrir despeses logístiques.  
  * *Atributs:* IdComanda, IdLot, ImportPagament, IdCentreLogistic. $\\rightarrow$ *Cap a Agent Cobrador*.

  ### **Agent Venedor Extern**

* **PeticioRegistreProducteExtern (REQUEST):** *\[Acció\]* Sol·licita crear un nou article a /comm.  
  * *Contingut:* Passa una instància del model ProducteExtern. $\\rightarrow$ *Cap a Agent Cercador*.  
* **DadesEnviament (INFORM):** *\[Predicat\]* Assumeix la comanda delegada i en retorna les metadades de distribució pròpia.  
  * *Atributs:* IdComanda, Ciutat, DataEntrega, Estat ("DELEGAT"), NomTransportista ("Venedor extern"), IdTransportista. *Relacions:* TeProducte. $\\rightarrow$ *Cap a Agent Compra*.  
* **PeticioRegistreDadesVenedor (REQUEST):** *\[Acció\]* Demana registrar credencials de facturació.  
  * *Atributs:* IdVenedor, DadesBancaries, MetodePagament. $\\rightarrow$ *Cap a Agent Cobrador*.

  ### **Agent Transportista**

* **RespostaOfertaTransport (INFORM):** *\[Predicat\]* Proposta de pressupost i data calculada per a la licitació del lot.  
  * *Atributs:* IdLot, IdTransportista, NomTransportista, CostTransport, DataEntregaDefinitiva, Ciutat. *Relacions:* SobreLot. $\\rightarrow$ *Cap a Agent Centre Logístic*.

  ### **Agent Cobrador**

* **ConfirmacioPagament (INFORM):** *\[Predicat\]* Certificat d'èxit de l'operació de càrrec o transferència interna.  
  * *Atributs:* IdComanda, ImportPagament, Estat. *Relacions:* EsRespostaA. $\\rightarrow$ *Cap a Agent Compra o Centre Logístic*.  
* **ConfirmacioRetornDiners (INFORM):** *\[Predicat\]* Certificat de tancament i aplicació del reemborsament a l'usuari.  
  * *Atributs:* IdDevolucio, IdComanda, ImportPagament, Estat. *Relacions:* EsRespostaA. $\\rightarrow$ *Cap a Agent Retornador*.  
* **ConfirmacioRegistreDades (INFORM):** *\[Predicat\]* Resposta asíncrona que valida la passarel·la per operar amb aquest compte.  
  * *Atributs:* IdVenedor / IdUsuari, Estat. $\\rightarrow$ *Cap a Agent Venedor Extern*.