import argparse
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, render_template, request
from rdflib import Graph

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.config import DATA_DIR, DEFAULT_PORTS, TEMPLATE_DIR, build_agent
from AgentZon.domain import SearchCriteria
from AgentZon.protocols.cerca import build_peticio_cerca, build_resultat_cerca, parse_peticio_cerca
from AgentZon.protocols.directory import build_register_message, build_search_message, parse_directory_response
from AgentZon.services.catalog_service import CatalogService
from AgentZon.services.history_service import SearchHistoryService


class CercadorAgent:
    def __init__(self, agent, directory_agent, data_dir, message_sender=send_message):
        self.agent = agent
        self.directory_agent = directory_agent
        self.message_sender = message_sender
        data_dir = Path(data_dir)
        self.catalog_service = CatalogService(data_dir / "productes.ttl")
        self.search_history = SearchHistoryService(data_dir / "historial_cerques.ttl")
        self.counter = 0

    def next_counter(self):
        current = self.counter
        self.counter += 1
        return current

    def resolve_compra_agent(self):
        message = build_search_message(self.agent, DSO.CompraAgent, self.directory_agent, msgcnt=self.next_counter())
        response = self.message_sender(message, self.directory_agent.address)
        return parse_directory_response(response)

    def pla_de_cerca(self, criteria: SearchCriteria):
        products = self.catalog_service.search_products(criteria)
        self.search_history.record_search(criteria, products)
        return products

    def pla_de_presentacio(self, criteria: SearchCriteria, products):
        compra_agent = self.resolve_compra_agent()
        compra_url = _replace_path(compra_agent.address, "/purchase")
        return render_template(
            "cercador.html",
            criteria=criteria,
            products=products,
            compra_url=compra_url,
        )


def create_app(settings, message_sender=send_message):
    service = CercadorAgent(
        settings["agent"],
        settings["directory_agent"],
        settings["data_dir"],
        message_sender=message_sender,
    )
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

    @app.route("/")
    def index():
        return render_template("cercador.html", criteria=SearchCriteria(), products=[], compra_url="")

    @app.route("/search", methods=["POST"])
    def search():
        criteria = SearchCriteria(
            text=request.form.get("text", ""),
            category=request.form.get("category", ""),
            brand=request.form.get("brand", ""),
            min_price=float(request.form["min_price"]) if request.form.get("min_price") else None,
            max_price=float(request.form["max_price"]) if request.form.get("max_price") else None,
        )
        products = service.pla_de_cerca(criteria)
        return service.pla_de_presentacio(criteria, products)

    @app.route("/comm")
    def comm():
        gm = Graph()
        gm.parse(data=request.args["content"], format="xml")
        props = get_message_properties(gm)
        if not props or props.get("performative") != ACL.request:
            return build_message(Graph(), ACL["not-understood"], sender=service.agent.uri, msgcnt=service.next_counter()).serialize(format="xml")
        content = props["content"]
        parsed = parse_peticio_cerca(gm, content)
        criteria = SearchCriteria(**parsed)
        products = service.pla_de_cerca(criteria)
        response_graph, response_content = build_resultat_cerca(f"result-{service.next_counter()}", products)
        response = build_message(
            response_graph,
            ACL.inform,
            sender=service.agent.uri,
            receiver=props.get("sender"),
            content=response_content,
            msgcnt=service.next_counter(),
        )
        return response.serialize(format="xml")

    @app.route("/info")
    def info():
        return service.search_history.store.load_graph().serialize(format="turtle")

    @app.route("/stop")
    def stop():
        shutdown_server()
        return "Stopping"

    return app


def _replace_path(address, new_path):
    parsed = urlsplit(address)
    return urlunsplit((parsed.scheme, parsed.netloc, new_path, "", ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORTS["cercador"])
    parser.add_argument("--directory-host", default="127.0.0.1")
    parser.add_argument("--directory-port", type=int, default=DEFAULT_PORTS["directory"])
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()

    agent = build_agent("CercadorAgent", "Cercador", args.port, host=args.host)
    directory = build_agent("DirectoryAgent", "Directory", args.directory_port, host=args.directory_host, endpoint="/Register")
    app = create_app(
        {
            "agent": agent,
            "directory_agent": directory,
            "data_dir": Path(args.data_dir),
        }
    )
    try:
        send_message(build_register_message(agent, DSO.CercadorAgent, directory, msgcnt=0), directory.address)
    except Exception:
        pass
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
