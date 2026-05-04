"""
- FIPA és un estàndard perquè "agents" (processos que parlen entre ells) s'enviïn
  missatges amb un format comú: qui envia, qui rep, què volen dir (performative)
  i el contingut (sovint RDF que descriu una oferta, una petició, etc.).

- ACL = Agent Communication Language. Aquí no fem el text tipus "REQUEST(...)"
  clàssic; encapsulem tot això com a graf RDF amb el vocabulari `acl:` (FipaAclMessage,
  sender, receiver, performative, content) perquè encaixi amb rdflib i la resta
  del projecte AgentZon.
"""

from typing import Optional
from urllib.parse import urlencode  # codifica el cos del missatge com a query string segur per URL
from urllib.request import urlopen  # crida HTTP sense dependre de requests (urllib està built-in)

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from AgentZon.config import AGENTZON


# Prefix semàntic de l'ontologia FIPA ACL en RDF — aquí viuen les propietats del "sobre" del missatge
ACL = Namespace("http://www.nuin.org/ontology/fipa/acl#")


def _first_content_subject(graph: Graph) -> Optional[URIRef]:
    """
    Donat un graf que només porta el contingut (p.ex. una oferta), troba QUIN node
    del graf és el "principal" per enllaçar-lo des del missatge com a `acl:content`.

    Per què no agafem la primera tripleta i ja? Perquè al graf poden haver-hi més
    d'un tipus (p.ex. OfertaTransport + RespostaOfertaTransport) i volem prioritzar
    el tipus més concret primer, i ignorar URIs que siguin només coses del namespace acl.
    """
    # 1) Preferim resposta a oferta de transport si n'hi ha (és el cas més específic que usem)
    for subject in graph.subjects(RDF.type, AGENTZON.RespostaOfertaTransport):
        if not str(subject).startswith(str(ACL)):
            return subject

    # 2) Sinó dades d'enviament del producte
    for subject in graph.subjects(RDF.type, AGENTZON.DadesEnviamentProducte):
        if not str(subject).startswith(str(ACL)):
            return subject

    # 3) Producte localitzat (resultat de cerca / disponibilitat)
    for subject in graph.subjects(RDF.type, AGENTZON.ProducteLocalitzat):
        if not str(subject).startswith(str(ACL)):
            return subject

    # 4) Petició de transport
    for subject in graph.subjects(RDF.type, AGENTZON.PeticioTransport):
        if not str(subject).startswith(str(ACL)):
            return subject

    # 5) Últim recurs: qualsevol subjecte que tingui un rdf:type (el primer que no sigui "cosa acl")
    for subject in graph.subjects(RDF.type, None):
        if not str(subject).startswith(str(ACL)):
            return subject

    # No hem trobat cap node "de negoci" per apuntar — el missatge pot existir sense content enllaçat
    return None


def build_message(
    performative: str,
    sender: URIRef,
    receiver: URIRef,
    content: Optional[Graph] = None,
    msgcnt: int = 0,
) -> Graph:
    """
    Munta un missatge FIPA-ACL com a graf RDF: capa d'envelope (performative, sender, receiver)
    + opcionalment tot el contingut copiat dins el mateix graf, amb un arc `content` al node principal.
    El resultat es pot serialitzar a XML i enviar per HTTP com fan els agents.
    """
    message = Graph()
    # Així el XML surt amb prefixos llegibles (acl:..., az:...) en lloc de URLs llargues
    message.bind("acl", ACL)
    message.bind("az", AGENTZON)

    # Cada missatge té un ID únic dins el namespace AgentZon (message_0, message_1, ...)
    message_subject = URIRef(f"{AGENTZON}message_{msgcnt}")
    # Aquest node ÉS un missatge FIPA segons l'ontologia acl
    message.add((message_subject, RDF.type, ACL.FipaAclMessage))
    # performative = el "verb" del missatge (request, inform, agree, refuse, not-understood, ...)
    message.add((message_subject, ACL.performative, Literal(performative)))
    message.add((message_subject, ACL.sender, sender))
    message.add((message_subject, ACL.receiver, receiver))

    if content is not None:
        # Copiem les tripletes del contingut dins aquest mateix graf (un sol blob RDF per enviar)
        for triple in content:
            message.add(triple)
        content_subject = _first_content_subject(content)
        if content_subject is not None:
            # Enllaç del missatge al node "root" del payload (és el que l'altre agent ha de llegir primer)
            message.add((message_subject, ACL.content, content_subject))

    return message


def parse_message(serialized: bytes | str) -> Graph:
    """Passa de bytes/string XML que ha arribat per la xarxa a un Graph de rdflib (per poder-hi fer queries)."""
    graph = Graph()
    # urlopen torna bytes; rdflib vol string en aquest camí
    if isinstance(serialized, bytes):
        serialized = serialized.decode("utf-8")
    graph.parse(data=serialized, format="xml")
    return graph


def get_message_properties(graph: Graph) -> dict:
    """
    Llegeix el sobre del missatge sense haver de saber SPARQL: retorna sender, receiver,
    performative i l'URI del contingut (`content`). Si el graf és estrany o incomplet, torna {}.

    Hi ha dues maneres de trobar el node del missatge: pel tipus FipaAclMessage,
    o bé pel fet que té `performative` (per compatibilitat amb graf mixtos).
    """
    # Intent 1: l'usuari típic marca el missatge explícitament com FipaAclMessage
    message_subject = next(graph.subjects(RDF.type, ACL.FipaAclMessage), None)
    if message_subject is None:
        # Intent 2: qualsevol subjecte que tingui acl:performative el tractem com a capçalera
        message_subject = next(graph.subjects(ACL.performative, None), None)
    if message_subject is None:
        return {}

    performative = graph.value(message_subject, ACL.performative)
    if performative is None:
        return {}

    return {
        "message": message_subject,  # l'URI del node missatge (per si vols més queries)
        "performative": str(performative),  # sempre string per comparar amb "inform", "request", etc.
        "sender": graph.value(message_subject, ACL.sender),
        "receiver": graph.value(message_subject, ACL.receiver),
        "content": graph.value(message_subject, ACL.content),
    }


def build_not_understood(sender: URIRef, receiver: URIRef, msgcnt: int = 0) -> Graph:
    """Resposta estándard FIPA: 'no ho he entès' sense cos — així l'altre agent sap que algo ha fallat."""
    return build_message("not-understood", sender=sender, receiver=receiver, content=None, msgcnt=msgcnt)


def send_message(address: str, graph: Graph) -> Graph:
    """
    GET cap a `address`, espera RDF/XML en resposta i el parseja. Timeout curt per no penjar indefinidament.

    separator: si l'URL ja té `?param=...`, afegim amb `&content=...`; si no, comencem amb `?`.
    """
    payload = graph.serialize(format="xml")
    query = urlencode({"content": payload})  # escapa &, espais, etc. del XML
    separator = "&" if "?" in address else "?"
    with urlopen(f"{address}{separator}{query}", timeout=5) as response:
        return parse_message(response.read())
