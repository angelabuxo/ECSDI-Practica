import argparse
from pathlib import Path

from flask import Flask, render_template, request
from rdflib import Graph

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties, send_message
from AgentZon.AgentUtil.DSO import DSO
from AgentZon.AgentUtil.FlaskServer import shutdown_server
from AgentZon.config import DATA_DIR, DEFAULT_PORTS, TEMPLATE_DIR, build_agent
from AgentZon.domain import UserShippingData
from AgentZon.protocols.centre_logistic import build_productes_localitzats, extract_shipping_details
from AgentZon.protocols.compra import build_peticio_registre_compra, extract_registration_confirmation
from AgentZon.protocols.directory import build_register_message, build_search_message, parse_directory_response
from AgentZon.services.catalog_service import CatalogService
from AgentZon.services.order_service import OrderService


class CompraAgent:
    def __init__(self, agent, directory_agent, data_dir, message_sender=send_message):
        self.agent = agent
        self.directory_agent = directory_agent
        self.message_sender = message_sender
        data_dir = Path(data_dir)
        self.catalog_service = CatalogService(data_dir / "productes.ttl")
        self.order_service = OrderService(data_dir / "comandes.ttl", data_dir / "dades_enviament_usuari.ttl")
        self.counter = 0

    def next_counter(self):
        current = self.counter
        self.counter += 1
        return current

    def resolve_agent(self, agent_type):
        message = build_search_message(self.agent, agent_type, self.directory_agent, msgcnt=self.next_counter())
        response = self.message_sender(message, self.directory_agent.address)
        return parse_directory_response(response)

    def pla_demanar_informacio_usuari(self, selected_product_ids):
        products = self.catalog_service.get_products_by_ids(selected_product_ids)
        return render_template("compra.html", products=products)

    def pla_registrar_dades_d_usuari(self, selected_product_ids, form_data):
        shipping = UserShippingData(
            user_id=form_data["user_id"],
            user_name=form_data["user_name"],
            street_address=form_data["street_address"],
            city=form_data["city"],
            priority=form_data["priority"],
            payment_method=form_data["payment_method"],
        )
        self.order_service.save_user_shipping_data(shipping)
        products = self.catalog_service.get_products_by_ids(selected_product_ids)
        return self.order_service.create_order(shipping, products)

    def pla_producte_als_nostres_magatzems(self, order):
        centre_agent = self.resolve_agent(DSO.CentreLogisticAgent)
        localized_products = [
            {
                "product_id": product.product_id,
                "name": product.name,
                "weight": product.weight,
            }
            for product in order.products
        ]
        message, _ = build_productes_localitzats(
            order.order_id,
            order.user_id,
            order.shipping_data.city,
            order.shipping_data.priority,
            localized_products,
            sender=self.agent.uri,
            receiver=centre_agent.uri,
            msgcnt=self.next_counter(),
        )
        return extract_shipping_details(self.message_sender(message, centre_agent.address))

    def pla_informar_usuari_sobre_l_enviament(self, order, shipping_details):
        return render_template("shipping_summary.html", order=order, shipping_details=shipping_details)

    def pla_delegar_registre_compra(self, order):
        opinador_agent = self.resolve_agent(DSO.OpinadorAgent)
        message = build_peticio_registre_compra(
            order,
            sender=self.agent.uri,
            receiver=opinador_agent.uri,
            msgcnt=self.next_counter(),
        )
        reply = self.message_sender(message, opinador_agent.address)
        return extract_registration_confirmation(reply)

    def pla_enviament_extern(self):
        return None


def create_app(settings, message_sender=send_message):
    service = CompraAgent(
        settings["agent"],
        settings["directory_agent"],
        settings["data_dir"],
        message_sender=message_sender,
    )
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

    @app.route("/purchase", methods=["POST"])
    def purchase():
        selected = request.form.getlist("selected_product_ids")
        return service.pla_demanar_informacio_usuari(selected)

    @app.route("/confirm-purchase", methods=["POST"])
    def confirm_purchase():
        selected = request.form.getlist("selected_product_ids")
        order = service.pla_registrar_dades_d_usuari(selected, request.form)
        service.pla_delegar_registre_compra(order)
        shipping_details = service.pla_producte_als_nostres_magatzems(order)
        return service.pla_informar_usuari_sobre_l_enviament(order, shipping_details)

    @app.route("/comm")
    def comm():
        gm = Graph()
        gm.parse(data=request.args["content"], format="xml")
        props = get_message_properties(gm)
        response = build_message(Graph(), ACL["not-understood"], sender=service.agent.uri, msgcnt=service.next_counter())
        return response.serialize(format="xml")

    @app.route("/info")
    def info():
        return service.order_service.orders_store.load_graph().serialize(format="turtle")

    @app.route("/stop")
    def stop():
        shutdown_server()
        return "Stopping"

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORTS["compra"])
    parser.add_argument("--directory-host", default="127.0.0.1")
    parser.add_argument("--directory-port", type=int, default=DEFAULT_PORTS["directory"])
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()

    agent = build_agent("CompraAgent", "Compra", args.port, host=args.host)
    directory = build_agent("DirectoryAgent", "Directory", args.directory_port, host=args.directory_host, endpoint="/Register")
    app = create_app(
        {
            "agent": agent,
            "directory_agent": directory,
            "data_dir": Path(args.data_dir),
        }
    )
    try:
        send_message(build_register_message(agent, DSO.CompraAgent, directory, msgcnt=0), directory.address)
    except Exception:
        pass
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
