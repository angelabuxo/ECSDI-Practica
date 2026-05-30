# Product-Level Multi-Centre Logistics Plan

## Summary
Implement multi-centre purchases by sending exactly one `ProducteLocalitzat` ACL request per purchased product. `Agent Compra` locates each product, chooses the responsible C.L. when needed, contacts that centre for that single product, and returns one shipment confirmation per product.

## Key Changes
- Extend directory search so multiple CentreLogisticAgent registrations can be discovered, not only the first match.
- Register each C.L. with unique name/URI/address plus IdCentreLogistic, Ciutat, and optional address text.
- Add product-location lookup in Agent Compra using ubicacions_productes.ttl.
- For each purchased product:
  - Find all UbicatACentre candidates.
  - If there is one candidate, use it.
  - If there are multiple candidates, choose the closest registered C.L. with a deterministic string heuristic: exact city match first, then normalized SequenceMatcher similarity between delivery address/city and centre address/city, then IdCentreLogistic tie-break.
  - Build ProducteLocalitzat as localized-{order_id}-{product_id} containing exactly that product.
  - Send it to the chosen C.L.; these per-product requests can run in parallel.
Update logistics confirmations so the final purchase response contains multiple shipment entries, each tied to one product, one C.L., one lot, one transportist, cost, and definitive delivery date.

## Naming Constraint
- New or changed plan methods/functionalities must keep the Prometheus plan naming style from `Entrega-1/Diagrames-Entrega-1.pd`, matching what is already implemented.
- Use `pla_...` methods named from the diagram plan/functionality names, normalized to snake_case.
- Relevant examples: `pla_enviar_compra`, `pla_localitzar_productes`, `pla_assignar_productes_a_lots`, `pla_enviar_productes`, `pla_informar_usuari_sobre_l_enviament`.
- Avoid generic implementation-only names when a diagram plan name exists.

## Interfaces And RDF
- Add/extend ontology terms for shipment-centre and shipment-product links, using existing vocabulary where possible.
- `ProducteLocalitzat` content IDs should include both order and product, e.g. `localized-{order_id}-{product_id}`.
- `extract_shipping_details` should include `product_id`, `centre_id`, and `centre_city`.
- `build_confirmacio_enviament` should embed all per-product shipment confirmations in the order confirmation.

## Test Plan
- Directory test: multiple C.L. agents register and are returned by search.
- Location test: product in two C.L. is assigned deterministically to the closest one.
- Purchase test: multi-product order sends one `ProducteLocalitzat` per product.
- Same-centre test: two products in the same C.L. still produce two logistics requests.
- Delivery-date test: each shipment date is `<=` expected order date.
- Distributed smoke test: launch multiple C.L. processes and complete a multi-product purchase through `/iface`.

## Assumptions
- The purchase remains one `Comanda`; shipments are split per product.
- `ubicacions_productes.ttl` is the product-location source of truth.
- The C.L. may use lots internally, but `Agent Compra` never groups products before contacting logistics.
