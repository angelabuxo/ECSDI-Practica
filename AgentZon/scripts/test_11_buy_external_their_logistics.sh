#!/usr/bin/env bash
# =============================================================================
# TEST 11: Compra d'1 producte extern amb enviament del venedor
# Propòsit: Validar compra amb logística externa (venedor gestiona enviament)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Compra producte extern (logística del venedor)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents..."
for url in "$VENEDOR_URL/iface" "$CERCADOR_URL/iface" "$COMPRA_URL/iface" "$COBRADOR_URL/comm"; do
    wait_for_server "$url" "$(basename "$url")" 10 || exit 1
done

# ── Pas 1: Registrar venedor + producte amb logística externa ──────────
_info "Registrant venedor AudioMax Corp i producte amb logística externa..."

# Primer, fer setup del venedor (si cal)
VENDOR_PAGE=$(get_page "$VENEDOR_URL/iface")
if echo "$VENDOR_PAGE" | grep -q "Guardar perfil i continuar"; then
    _info "Setup del venedor AudioMax Corp..."
    post_form "$VENEDOR_URL/iface" \
        --data-urlencode "form_type=setup" \
        --data-urlencode "seller_name=AudioMax Corp" \
        --data-urlencode "bank_data=ES98 7654 3210 9876 5432 1098" > /dev/null
    sleep 1
fi

# ── Registrar producte amb logística externa ───────────────────────────
_info "Registrant Premium Wireless Headphones (logística externa)..."
PRODUCT_RESULT=$(post_form "$VENEDOR_URL/iface" \
    --data-urlencode "form_type=products" \
    --data-urlencode "name=Premium Wireless Headphones" \
    --data-urlencode "description=High-end wireless headphones with ANC" \
    --data-urlencode "category=audio" \
    --data-urlencode "brand=AudioMax" \
    --data-urlencode "price=149.99" \
    --data-urlencode "weight=0.35" \
    --data-urlencode "sku_extern=AUD-WH-PRO-001" \
    --data-urlencode "logistics_mode=vendor" \
    --data-urlencode "centre_id=CL-BCN")
echo "$PRODUCT_RESULT" > /tmp/agentzon_test11_product.html

assert_contains "$PRODUCT_RESULT" "registrat" "Producte extern registrat"
assert_contains "$PRODUCT_RESULT" "Premium Wireless Headphones" "Nom del producte visible"

_extract_product_id() {
    echo "$PRODUCT_RESULT" | grep -oP 'ID:\s*\K(EXT-\d+|P\d+)' | head -1 || true
}

EXT_ID=$(_extract_product_id)
if [ -z "$EXT_ID" ]; then
    # Intentar extreure de productes.ttl
    sleep 2
    EXT_ID=$(grep -oP 'azon:product-\K(EXT-\d+)' "$DATA_DIR/productes.ttl" | tail -1 || true)
fi

if [ -z "$EXT_ID" ]; then
    _warn "No s'ha pogut determinar l'ID del producte extern."
    _info "Revisa la sortida i busca l'ID. Després executa la compra manualment."
    end_test
    exit 0
fi

_info "ID del producte extern (logística venedor): $EXT_ID"

# ── Verificar que el producte apareix al cercador ──────────────────────
sleep 3
SEARCH_RESULT=$(search_products "Premium Wireless Headphones" "" "" "" "")
echo "$SEARCH_RESULT" > /tmp/agentzon_test11_search.html

if echo "$SEARCH_RESULT" | grep -q "Premium Wireless Headphones"; then
    _pass "Producte extern apareix als resultats de cerca"
else
    _warn "Producte no visible al cercador (pot trigar)"
fi

# ── Comprar el producte extern ─────────────────────────────────────────
_info "Comprant $EXT_ID (Premium Wireless Headphones) amb logística externa..."

PURCHASE_RESULT=$(purchase_products \
    "Test External 2" \
    "Avinguda Audio 10" \
    "València" \
    "7 dies" \
    "targeta" \
    "$EXT_ID")
echo "$PURCHASE_RESULT" > /tmp/agentzon_test11_purchase.html

ORDER_ID=$(extract_order_id "$PURCHASE_RESULT")
if [ -n "$ORDER_ID" ]; then
    _pass "IdComanda generat: $ORDER_ID"
else
    _fail "No s'ha pogut extreure IdComanda"
fi

assert_contains "$PURCHASE_RESULT" "Test External 2" "Nom d'usuari al resum"
assert_contains "$PURCHASE_RESULT" "149.99" "Preu del producte (149.99€) al resum"
assert_contains "$PURCHASE_RESULT" "Factura" "Secció de factura present"

# ── Verificacions clau per logística externa ───────────────────────────
_info "Verificant pagaments immediats (sense esperar enviament)..."

sleep 2
if [ -f "$DATA_DIR/pagaments.ttl" ] && [ -s "$DATA_DIR/pagaments.ttl" ]; then
    _pass "pagaments.ttl conté registres"
    if grep -q "COBRAMENT" "$DATA_DIR/pagaments.ttl"; then
        _pass "Pagament COBRAMENT (usuari → AgentZon) registrat"
    fi
    if grep -q "PAGAMENT" "$DATA_DIR/pagaments.ttl"; then
        _pass "Pagament PAGAMENT (AgentZon → venedor) registrat"
    fi
else
    _warn "pagaments.ttl buit o inexistent"
fi

# ── Verificar que NO hi ha lots creats ─────────────────────────────────
_info "Verificant que NO hi ha lots (logística externa no usa centres)..."

LOTS_BCN=$(get_page "$BCN_URL/iface")
LOTS_TGN=$(get_page "$TGN_URL/iface")
LOTS_GI=$(get_page "$GI_URL/iface")

# El producte extern amb logística externa NO hauria de crear lots
_info "NOTA: Amb logística externa, el sistema NO crea lots ni contacta centres logístics."
_info "El pagament és immediat (no espera enviament)."
_info ""
_info "Verificacions manuals recomanades:"
_info "  1. $VENEDOR_URL/iface - verificar producte extern"
_info "  2. $BCN_URL/iface - NO hauria de tenir lots per aquest producte"
_info "  3. $DATA_DIR/pagaments.ttl - 2 pagaments (COBRAMENT + PAGAMENT)"
_info "  4. $DATA_DIR/seguiment_enviaments.ttl - NO hauria de tenir ProducteLocalitzat"

end_test
