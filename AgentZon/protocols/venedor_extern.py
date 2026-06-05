"""Missatges d'alta de producte extern, confirmació i enviament delegat al venedor."""

from datetime import date

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces
from protocols.rdf_refs import (
    _seller_id_from_iri,
    ensure_order_node,
    ensure_transportista_node,
    first_product_node,
    link_product,
    order_id_from_node,
    product_nodes_from_content,
    transport_id_from_node,
)

CENTRE_RESOURCE_BY_ID = {
    "CL-BCN": "centre-BCN",
    "CL-GI": "centre-GI",
    "CL-TGN": "centre-TGN",
}


def _add_external_product_node(graph, product_node, product):
    graph.add((product_node, RDF.type, AZON.ProducteExtern))
    if product.get("product_id"):
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if product.get("name"):
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
    if product.get("description"):
        graph.add((product_node, AZON.Descripcio, Literal(product["description"])))
    if product.get("category"):
        graph.add((product_node, AZON.Categoria, Literal(product["category"])))
    if product.get("brand"):
        graph.add((product_node, AZON.Marca, Literal(product["brand"])))
    if product.get("price") is not None:
        graph.add((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
    if product.get("weight") is not None:
        graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if product.get("sku_extern"):
        graph.add((product_node, AZON.SkuExtern, Literal(product["sku_extern"])))
    if product.get("data_alta"):
        graph.add((product_node, AZON.DataAlta, Literal(product["data_alta"], datatype=XSD.date)))
    if product.get("requires_external_logistics") is not None:
        graph.add(
            (
                product_node,
                AZON.RequereixLogisticaExterna,
                Literal(bool(product["requires_external_logistics"]), datatype=XSD.boolean),
            )
        )
    if product.get("seller_id"):
        graph.add((product_node, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(product["seller_id"])]))
    if product.get("centre_id") and not product.get("requires_external_logistics"):
        centre_resource = CENTRE_RESOURCE_BY_ID.get(product["centre_id"])
        if centre_resource:
            centre_node = AZON[centre_resource]
            graph.add((centre_node, RDF.type, AZON.CentreLogistic))
            graph.add((centre_node, AZON.IdCentreLogistic, Literal(product["centre_id"])))
            graph.add((product_node, AZON.UbicatACentre, centre_node))


def _parse_external_product_node(graph, product_node):
    weight_value = graph.value(product_node, AZON.Pes)
    external_flag = graph.value(product_node, AZON.RequereixLogisticaExterna)
    centre_id = ""
    centre_node = graph.value(product_node, AZON.UbicatACentre)
    if centre_node is not None:
        centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
        if centre_id_value is not None:
            centre_id = str(centre_id_value)
    return {
        "product_id": str(graph.value(product_node, AZON.IdProducte) or ""),
        "name": str(graph.value(product_node, AZON.Nom) or ""),
        "description": str(graph.value(product_node, AZON.Descripcio) or ""),
        "category": str(graph.value(product_node, AZON.Categoria) or ""),
        "brand": str(graph.value(product_node, AZON.Marca) or ""),
        "price": float(graph.value(product_node, AZON.Preu) or 0.0),
        "weight": float(weight_value) if weight_value is not None else 0.0,
        "sku_extern": str(graph.value(product_node, AZON.SkuExtern) or ""),
        "data_alta": str(graph.value(product_node, AZON.DataAlta) or ""),
        "requires_external_logistics": str(external_flag).lower() == "true" if external_flag is not None else False,
        "seller_id": _seller_id_from_iri(graph.value(product_node, AZON.PertanyAVenedorExtern) or ""),
        "centre_id": centre_id,
    }


def build_alta_producte_extern(product, seller, request_id=None, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[request_id or f"alta-extern-{product.get('sku_extern', 'new')}"]
    graph.add((content, RDF.type, AZON.AltaProducteExtern))

    seller_node = AZON[f"seller-{seller['seller_id']}"]
    graph.add((seller_node, RDF.type, AZON.VenedorExtern))
    graph.add((seller_node, AZON.IdVenedorExtern, Literal(seller["seller_id"])))
    if seller.get("seller_name"):
        graph.add((seller_node, AZON.Nom, Literal(seller["seller_name"])))
    if seller.get("bank_data"):
        graph.add((seller_node, AZON.DadesBancariesVenedorExtern, Literal(seller["bank_data"])))

    product_payload = {**product, "seller_id": seller["seller_id"]}
    product_node = AZON[f"product-draft-{product_payload.get('product_id') or product_payload.get('sku_extern', 'new')}"]
    _add_external_product_node(graph, product_node, product_payload)
    link_product(graph, content, product_node, product_kind="extern")

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_alta_producte_extern(graph, content):
    product = None
    product_node = first_product_node(graph, content)
    if product_node is not None:
        product = _parse_external_product_node(graph, product_node)
    if product is None:
        raise ValueError("AltaProducteExtern sense producte associat")

    seller_id = product.get("seller_id") or ""
    bank_data = ""
    for seller_node in graph.subjects(RDF.type, AZON.VenedorExtern):
        node_seller_id = graph.value(seller_node, AZON.IdVenedorExtern)
        if node_seller_id is not None and str(node_seller_id) == seller_id:
            bank_data = str(graph.value(seller_node, AZON.DadesBancariesVenedorExtern) or "")
            break
    if not bank_data:
        for seller_node in graph.subjects(RDF.type, AZON.VenedorExtern):
            bank_data = str(graph.value(seller_node, AZON.DadesBancariesVenedorExtern) or "")
            seller_id = str(graph.value(seller_node, AZON.IdVenedorExtern) or seller_id)
            break

    return {
        "product": product,
        "seller": {"seller_id": seller_id, "bank_data": bank_data},
    }


def build_confirmacio_alta_producte_extern(
    product_id,
    sku_extern,
    data_alta=None,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"confirmacio-alta-{product_id}"]
    product_node = AZON[f"product-{product_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioAltaProducteExtern))
    graph.add((product_node, RDF.type, AZON.ProducteExtern))
    graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    graph.add((product_node, AZON.SkuExtern, Literal(sku_extern)))
    graph.add((product_node, AZON.DataAlta, Literal(data_alta or date.today().isoformat(), datatype=XSD.date)))
    graph.add((content, AZON.SobreProducte, product_node))
    graph.add((content, AZON.TeProducteExtern, product_node))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_confirmacio_alta_producte_extern(graph, content=None):
    if content is None:
        props = get_message_properties(graph)
        content = props["content"]
    product_node = first_product_node(graph, content)
    if product_node is None:
        return {
            "product_id": "",
            "sku_extern": "",
            "data_alta": "",
        }
    return {
        "product_id": str(graph.value(product_node, AZON.IdProducte) or ""),
        "sku_extern": str(graph.value(product_node, AZON.SkuExtern) or ""),
        "data_alta": str(graph.value(product_node, AZON.DataAlta) or ""),
    }


def build_peticio_enviament_extern(order, seller_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-shipping-request-{order['order_id']}-{seller_id}"]
    shipping = order["shipping_data"]
    order_node = ensure_order_node(graph, order["order_id"])

    graph.add((content, RDF.type, AZON.PeticioEnviamentExtern))
    graph.add((content, AZON.PertanyAVenedorExtern, AZON["venedor-" + str(seller_id)]))
    graph.add((content, AZON.Ciutat, Literal(shipping["city"])))
    graph.add((content, AZON.Carrer, Literal(shipping.get("street_address", ""))))
    graph.add((content, AZON.Prioritat, Literal(shipping["priority"])))
    graph.add((content, AZON.SobreComanda, order_node))

    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        _add_external_product_node(graph, product_node, product)
        link_product(graph, content, product_node, product_kind="extern")

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_enviament_extern(graph, content):
    products = []
    for _, product_node in product_nodes_from_content(graph, content):
        products.append(_parse_external_product_node(graph, product_node))
    seller_id_iri = graph.value(content, AZON.PertanyAVenedorExtern)
    seller_id = _seller_id_from_iri(seller_id_iri)
    if seller_id is None and products:
        seller_id = products[0].get("seller_id")
    return {
        "order_id": order_id_from_node(graph, content),
        "seller_id": str(seller_id or ""),
        "city": str(graph.value(content, AZON.Ciutat) or ""),
        "street_address": str(graph.value(content, AZON.Carrer) or ""),
        "priority": str(graph.value(content, AZON.Prioritat) or ""),
        "products": products,
    }


def build_resposta_enviament_extern(
    order_id,
    products,
    seller_id,
    delivery_date,
    city,
    status="DELEGAT",
    seller_display_name=None,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"dades-enviament-extern-{order_id}-{seller_id}"]
    transport_name = seller_display_name or seller_id
    order_node = ensure_order_node(graph, order_id)
    transport_node = ensure_transportista_node(graph, seller_id, transport_name)

    graph.add((content, RDF.type, AZON.DadesEnviament))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.Ciutat, Literal(city)))
    graph.add((content, AZON.DataEntrega, Literal(delivery_date)))
    graph.add((content, AZON.Estat, Literal(status)))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((content, AZON.NomTransportista, Literal(transport_name)))
    for product in products:
        product_node = AZON[f"product-{product['product_id']}"]
        _add_external_product_node(graph, product_node, product)
        link_product(graph, content, product_node, product_kind="extern")
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_external_shipments_from_reply(reply):
    if isinstance(reply, Graph):
        reply_graph = reply
    else:
        reply_graph = Graph()
        reply_graph.parse(data=reply, format="xml")

    props = get_message_properties(reply_graph)
    if not props:
        return []
    content = props["content"]
    if (content, RDF.type, AZON.DadesEnviament) not in reply_graph:
        return []

    order_id = order_id_from_node(reply_graph, content)
    city = str(reply_graph.value(content, AZON.Ciutat) or "")
    delivery_date = str(reply_graph.value(content, AZON.DataEntrega) or "")
    status = str(reply_graph.value(content, AZON.Estat) or "DELEGAT")
    transport_name = str(reply_graph.value(content, AZON.NomTransportista) or "Venedor extern")
    seller_id = transport_id_from_node(reply_graph, content)
    transport_id = seller_id if seller_id and seller_id != transport_name else ""

    shipments = []
    for _, product_node in product_nodes_from_content(reply_graph, content):
        product = _parse_external_product_node(reply_graph, product_node)
        shipments.append(
            {
                "localized_product_id": f"pext-{product['product_id']}",
                "order_id": order_id,
                "lot_id": "EXTERN",
                "status": status,
                "city": city,
                "delivery_date": delivery_date,
                "centre_id": None,
                "centre_city": "Venedor extern",
                "transport_id": transport_id,
                "transport_name": transport_name,
                "product": product,
                "external_logistics": True,
            }
        )
    return shipments
