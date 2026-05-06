"""FIPA-ACL namespace constants reused across AgentZon agents.

@author: javier
"""

__author__ = "javier"

from rdflib import URIRef
from rdflib.namespace import ClosedNamespace


ACL = ClosedNamespace(
    uri=URIRef("http://www.nuin.org/ontology/fipa/acl#"),
    terms=[
        "FipaAclMessage",
        "KsMessage",
        "SpeechAct",
        "receiver",
        "reply-to",
        "ontology",
        "performative",
        "sender",
        "language",
        "encoding",
        "content",
        "reply-by",
        "reply-with",
        "conversation-id",
        "in-reply-to",
        "refuse",
        "subscribe",
        "agree",
        "query-ref",
        "request",
        "request-whenever",
        "query-if",
        "proxy",
        "cancel",
        "propose",
        "cfp",
        "reject-proposal",
        "failure",
        "accept-proposal",
        "not-understood",
        "inform",
        "inform-if",
        "inform-ref",
        "propagate",
        "confirm",
        "request-when",
        "disconfirm",
    ],
)
