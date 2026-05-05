import requests
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF

from AgentZon.AgentUtil.ACL import ACL


def build_message(gmess, perf, sender=None, receiver=None, content=None, msgcnt=0):
    mssid = f"message-{hash(sender)}-{msgcnt:04d}"
    ms = URIRef(mssid)
    gmess.bind("acl", ACL)
    gmess.add((ms, RDF.type, OWL.NamedIndividual))
    gmess.add((ms, RDF.type, ACL.FipaAclMessage))
    gmess.add((ms, ACL.performative, perf))
    if sender is not None:
        gmess.add((ms, ACL.sender, sender))
    if receiver is not None:
        gmess.add((ms, ACL.receiver, receiver))
    if content is not None:
        gmess.add((ms, ACL.content, content))
    return gmess


def send_message(gmess, address, timeout=10):
    payload = gmess.serialize(format="xml")
    response = requests.get(address, params={"content": payload}, timeout=timeout)
    response.raise_for_status()
    graph = Graph()
    graph.parse(data=response.text, format="xml")
    return graph


def get_message_properties(msg):
    props = {
        "performative": ACL.performative,
        "sender": ACL.sender,
        "receiver": ACL.receiver,
        "ontology": ACL.ontology,
        "conversation-id": ACL["conversation-id"],
        "in-reply-to": ACL["in-reply-to"],
        "content": ACL.content,
    }

    message = msg.value(predicate=RDF.type, object=ACL.FipaAclMessage)
    if message is None:
        return {}

    data = {}
    for key, predicate in props.items():
        value = msg.value(subject=message, predicate=predicate)
        if value is not None:
            data[key] = value
    return data
