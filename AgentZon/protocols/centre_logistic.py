# Aquest fitxer defineix els objectes que viatgen dins dels protocols de
# l'Agent Centre Logístic. La comunicació FIPA-ACL es podrà afegir més endavant;
# aquí només representem el contingut dels missatges segons l'ontologia.


class ProducteLocalitzat:
    """Missatge de l'Agent Compra al Centre Logístic per enviar un producte."""

    def __init__(
        self,
        id_producte: str,
        id_comanda: str,
        userid: str,
        adreca: str,
        prioritat: int,
        data_limit: str,
        pes: float,
        import_producte: float,
    ):
        self.id_producte = id_producte
        self.id_comanda = id_comanda
        self.userid = userid
        self.adreca = adreca
        self.prioritat = prioritat
        self.data_limit = data_limit
        self.pes = pes
        self.import_producte = import_producte


class PeticioTransport:
    """Petició que el Centre Logístic prepara per negociar el transport d'un lot."""

    def __init__(self, id_lot: str, centre_logistic_id: str, adreca: str, data_enviament: str, pes: float, prioritat: int):
        self.id_lot = id_lot
        self.centre_logistic_id = centre_logistic_id
        self.adreca = adreca
        self.data_enviament = data_enviament
        self.pes = pes
        self.prioritat = prioritat


class RespostaOfertaTransport:
    """Oferta rebuda d'un transportista extern per a un lot."""

    def __init__(self, id_lot: str, transportista_id: str, cost: float, data_enviament: str):
        self.id_lot = id_lot
        self.transportista_id = transportista_id
        self.cost = cost
        self.data_enviament = data_enviament


class EleccioTransportista:
    """Resultat de la selecció del transportista per part del Centre Logístic."""

    def __init__(self, id_lot: str, transportista_id: str, cost: float, data_enviament: str):
        self.id_lot = id_lot
        self.transportista_id = transportista_id
        self.cost = cost
        self.data_enviament = data_enviament


class DadesEnviamentProducte:
    """Missatge del Centre Logístic a l'Agent Compra amb les dades definitives d'enviament."""

    def __init__(
        self,
        id_lot: str,
        id_comanda: str,
        userid: str,
        id_producte: str,
        transportista_id: str,
        data_entrega_definitiva: str,
    ):
        self.id_lot = id_lot
        self.id_comanda = id_comanda
        self.userid = userid
        self.id_producte = id_producte
        self.transportista_id = transportista_id
        self.data_entrega_definitiva = data_entrega_definitiva


class PeticioCobramentProducte:
    """Petició del Centre Logístic a l'Agent Cobrador quan un producte s'ha enviat."""

    def __init__(self, userid: str, id_comanda: str, id_producte: str, import_cobrament: float):
        self.userid = userid
        self.id_comanda = id_comanda
        self.id_producte = id_producte
        self.import_cobrament = import_cobrament
