"""Directory Service Ontology namespace constants used by AgentZon.

@author: javier
"""

__author__ = "javier"

from rdflib import URIRef
from rdflib.namespace import ClosedNamespace


DSO = ClosedNamespace(
    uri=URIRef("http://www.semanticweb.org/directory-service-ontology#"),
    terms=[
        "Register",
        "RegisterResult",
        "RegisterAction",
        "Deregister",
        "InfoAgent",
        "ServiceAgent",
        "Search",
        "SolverAgent",
        "Modify",
        "AgentType",
        "Uri",
        "Name",
        "Address",
        "FlightsAgent",
        "HotelsAgent",
        "TravelServiceAgent",
        "PersonalAgent",
        "WeatherAgent",
        "PaymentAgent",
        "DirectoryAgent",
        "CercadorAgent",
        "CompraAgent",
        "CentreLogisticAgent",
        "OpinadorAgent",
    ],
)
