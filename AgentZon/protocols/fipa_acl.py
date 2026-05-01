from typing import Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from AgentZon.config import AGENTZON


ACL = Namespace("http://www.nuin.org/ontology/fipa/acl#")


def _first_content_subject(graph: Graph) -> Optional[URIRef]:
    for subject in graph.subjects(RDF.type, None):
        if not str(subject).startswith(str(ACL)):
            return subject
    return None


def build_message(
    performative: str,
    sender: URIRef,
    receiver: URIRef,
    content: Optional[Graph] = None,
    msgcnt: int = 0,
) -> Graph:
    """Construeix un missatge FIPA-ACL serialitzable com a RDF/XML."""
    message = Graph()
    message.bind("acl", ACL)
    message.bind("az", AGENTZON)

    message_subject = URIRef(f"{AGENTZON}message_{msgcnt}")
    message.add((message_subject, RDF.type, ACL.FipaAclMessage))
    message.add((message_subject, ACL.performative, Literal(performative)))
    message.add((message_subject, ACL.sender, sender))
    message.add((message_subject, ACL.receiver, receiver))

    if content is not None:
        for triple in content:
            message.add(triple)
        content_subject = _first_content_subject(content)
        if content_subject is not None:
            message.add((message_subject, ACL.content, content_subject))

    return message


def parse_message(serialized: bytes | str) -> Graph:
    """Converteix un missatge RDF/XML rebut per HTTP en un graf RDF."""
    graph = Graph()
    if isinstance(serialized, bytes):
        serialized = serialized.decode("utf-8")
    graph.parse(data=serialized, format="xml")
    return graph


def get_message_properties(graph: Graph) -> dict:
    """Extreu camps principals d'un missatge FIPA-ACL."""
    message_subject = next(graph.subjects(RDF.type, ACL.FipaAclMessage), None)
    if message_subject is None:
        message_subject = next(graph.subjects(ACL.performative, None), None)
    if message_subject is None:
        return {}

    performative = graph.value(message_subject, ACL.performative)
    if performative is None:
        return {}

    return {
        "message": message_subject,
        "performative": str(performative),
        "sender": graph.value(message_subject, ACL.sender),
        "receiver": graph.value(message_subject, ACL.receiver),
        "content": graph.value(message_subject, ACL.content),
    }


def build_not_understood(sender: URIRef, receiver: URIRef, msgcnt: int = 0) -> Graph:
    return build_message("not-understood", sender=sender, receiver=receiver, content=None, msgcnt=msgcnt)


def send_message(address: str, graph: Graph) -> Graph:
    """Envia un missatge RDF/XML a un endpoint d'agent i retorna la resposta RDF."""
    payload = graph.serialize(format="xml")
    query = urlencode({"content": payload})
    separator = "&" if "?" in address else "?"
    with urlopen(f"{address}{separator}{query}", timeout=5) as response:
        return parse_message(response.read())
