"""
Agent Directori .

Altres agents et parlen amb **missatges RDF** on el "sobre"
diu coses com request/confirm/inform i el **contingut** és una acció (registrar-se o cercar).
Aquest fitxer té dues capes:
1) `AgentDirectory`: memòria local (un graf RDF amb tots els agents registrats) + `process_message`
   que entén què demanen.
2) Flask: una URL HTTP (`/Register`) on arriba el mateix XML RDF dins el query param `content`,
   tal com fa la resta del projecte amb `fipa_acl.send_message`.

No cal saber ACL: pensa "rebo un paquet estructurat, si és registre l'emmagatzemo, si és cerca torno llista".
"""

import argparse
from typing import Dict, Optional

from flask import Flask, Response, request  # web: GET amb `?content=...` com al LabDoc
from rdflib import Graph, Literal, RDF, URIRef

from AgentZon.agents.logging_utils import configure_pretty_logging
from AgentZon.config import AGENTZON
from AgentZon.protocols.directory import (
    DSO,  # vocabulari Register / Search / RegisteredAgent / respostes del directori
    build_directory_responses,
    read_directory_response,  # llegeix Name, Uri, Address, AgentType d'un node — val tant per respostes com per accions Register amb les mateixes propietats
)
from AgentZon.protocols.fipa_acl import build_message, build_not_understood, get_message_properties, parse_message


class AgentDirectory:
    """Servei de registre i descobriment d'agents seguint el patró del LabDoc."""

    def __init__(self):
        # URI fixa d'aquest agent dins l'ontologia (sur com a sender dels missatges de resposta)
        self.uri = URIRef(f"{AGENTZON}directory_agent")
        self.graph = Graph()  # aquí viu la "base de dades" en memòria: tots els RegisteredAgent
        self.graph.bind("az", AGENTZON)
        self.graph.bind("dso", DSO)

    def register_agent(self, name: str, uri: URIRef, address: str, agent_type: str) -> None:
        """
        Dona d'alta (o sobreescriu) un agent. Cada entrada és un node `directory_entry_{name}`.
        El `remove` primer evita duplicats bruts si es torna a registrar el mateix nom.
        """
        subject = URIRef(f"{AGENTZON}directory_entry_{name}")
        self.graph.remove((subject, None, None))  # esborra tripletes antigues d'aquest subjecte
        self.graph.add((subject, RDF.type, DSO.RegisteredAgent))  # "això és un agent conegut"
        self.graph.add((subject, DSO.Name, Literal(name)))
        self.graph.add((subject, DSO.Uri, uri))
        self.graph.add((subject, DSO.Address, Literal(address)))  # URL on escolta l'agent (per contactar-lo)
        self.graph.add((subject, DSO.AgentType, Literal(agent_type)))  # filtre de cerca (transportista, etc.)

    def search_agent(self, agent_type: str, name: Optional[str] = None) -> Optional[Dict[str, object]]:
        """Comoditat: la primera coincidència o None (quan només en vols un)."""
        results = self.search_agents(agent_type=agent_type, name=name)
        return results[0] if results else None

    def search_agents(self, agent_type: str, name: Optional[str] = None) -> list[Dict[str, object]]:
        """
        Recorre tots els RegisteredAgent del graf, filtra per tipus i opcionalment per nom exacte.
        Tot es compara com a string per evitar sorpreses amb Literal vs str.
        """
        results = []
        for subject in self.graph.subjects(RDF.type, DSO.RegisteredAgent):
            current_type = self.graph.value(subject, DSO.AgentType)
            current_name = self.graph.value(subject, DSO.Name)
            if str(current_type) != agent_type:
                continue
            if name is not None and str(current_name) != name:
                continue
            results.append(
                {
                    "name": str(current_name),
                    "uri": self.graph.value(subject, DSO.Uri),
                    "address": str(self.graph.value(subject, DSO.Address)),
                    "agent_type": str(current_type),
                }
            )
        return results

    def process_message(self, message: Graph) -> Graph:
        """
        Cor del protocol: descompon el missatge ACL, mira el contingut (node apuntat per acl:content)
        i branch: Register → actualitza memòria + confirm; Search → inform amb DirectoryResponse(s).

        Si el format no és el esperat (no request, sense content, tipus d'acció desconegut, cerca buida),
        es respon amb not-understood (estàndard FIPA per "no ho puc processar").
        """
        props = get_message_properties(message)  # sobre: performative, sender, receiver, URI del contingut
        if not props or props.get("performative") != "request" or props.get("content") is None:
            return build_not_understood(self.uri, AGENTZON.unknown_agent, msgcnt=0)

        action = props["content"]  # URI del node d'acció dins el graf (Register o Search)
        sender = props.get("sender") or AGENTZON.unknown_agent  # per respondre al que ha parlat (si falta, placeholder)

        # --- Branca REGISTRE: el contingut és un node tipus dso:Register amb les dades de l'agent ---
        if (action, RDF.type, DSO.Register) in message:
            # Reutilitzem read_directory_response perquè usa els mateixos predicates (Name, Uri, Address, AgentType)
            data = read_directory_response(message, action)
            self.register_agent(
                name=data["name"],
                uri=data["uri"],
                address=data["address"],
                agent_type=data["agent_type"],
            )
            return build_message("confirm", self.uri, sender, None, msgcnt=1)

        # --- Branca CERCA: node dso:Search amb AgentType obligatori; Name opcional ---
        if (action, RDF.type, DSO.Search) in message:
            agent_type = message.value(action, DSO.AgentType)
            name = message.value(action, DSO.Name)
            if agent_type is None:
                return build_not_understood(self.uri, sender, msgcnt=1)

            results = self.search_agents(agent_type=str(agent_type), name=str(name) if name is not None else None)
            if not results:
                return build_not_understood(self.uri, sender, msgcnt=1)

            content = build_directory_responses(results)  # graf amb un DirectoryResponse per cada entrada
            return build_message("inform", self.uri, sender, content, msgcnt=1)

        # Acció RDF que no és Register ni Search
        return build_not_understood(self.uri, sender, msgcnt=1)


def create_app(directory_agent: Optional[AgentDirectory] = None) -> Flask:
    """Factory Flask: permet injectar `AgentDirectory` als tests."""
    app = Flask(__name__)
    directory_agent = directory_agent or AgentDirectory()

    @app.route("/Register", methods=["GET"])
    def register():
        """
        Endpoint principal: igual que els altres agents, el client envia RDF/XML comprimit al param `content`.
        Es parseja → process_message → es torna RDF/XML amb la resposta ACL.
        """
        try:
            incoming = parse_message(request.args.get("content", ""))  # string buit si falta → graf buit / parse tolerant
            response = directory_agent.process_message(incoming)
        except Exception:
            response = build_not_understood(directory_agent.uri, AGENTZON.unknown_agent, msgcnt=0)
        return Response(response.serialize(format="xml"), mimetype="application/rdf+xml")

    @app.route("/Info", methods=["GET"])
    def info():
        """Debug/utilitat: veure tot el graf intern en Turtle al navegador o amb curl."""
        return Response(directory_agent.graph.serialize(format="turtle"), mimetype="text/turtle")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentZon DirectoryAgent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    configure_pretty_logging()
    create_app().run(host=args.host, port=args.port, debug=True)
