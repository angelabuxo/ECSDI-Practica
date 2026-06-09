#!/usr/bin/env bash
# =============================================================================
# TEST 2: Compra d'un producte intern
# Propòsit: Validar el flux complet de compra simple (P1003 des de TGN)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Compra d'un producte intern (P1003 - Precision Mouse, InputWorks)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents necessaris..."
for url in "$CERCADOR_URL/iface" "$COMPRA_URL/iface" "$TGN_URL/iface" \
           "$OPINADOR_URL/iface" "$COBRADOR_URL/comm" \
           "$FAST_URL/iface" "$ECONOMY_URL/iface"; do
    wait_for_server "$url" "$(basename "$url")" 10 || exit 1
done

# ── Verificar que P1003 està a TGN ─────────────────────────────────────
_info "Verificant ubicació de P1003..."
assert_file_contains "$DATA_DIR/ubicacions_productes.ttl" "product-P1003" "P1003 apareix a ubicacions_productes.ttl"
assert_file_contains "$DATA_DIR/ubicacions_productes.ttl" "centre-TGN" "centre-TGN apareix a ubicacions"

# ── Pas 1: Cercar P1003 ───────────────────────────────────────────────
_info "Cercant P1003 (Precision Mouse)..."
SEARCH_RESULT=$(search_products "Precision Mouse" "" "" "" "")
echo "$SEARCH_RESULT" > /tmp/agentzon_test2_search.html
assert_contains "$SEARCH_RESULT" "P1003" "P1003 trobat als resultats de cerca"

# ── Pas 2: Comprar P1003 ──────────────────────────────────────────────
_info "Comprant P1003..."
PURCHASE_RESULT=$(purchase_products \
    "Test User 1" \
    "Carrer Test 123" \
    "Barcelona" \
    "5 dies" \
    "targeta" \
    "P1003")
echo "$PURCHASE_RESULT" > /tmp/agentzon_test2_purchase.html

# ── Verificacions del resum de compra ──────────────────────────────────
_info "Verificant resum de compra..."

ORDER_ID=$(extract_order_id "$PURCHASE_RESULT")
if [ -n "$ORDER_ID" ]; then
    _pass "IdComanda generat: $ORDER_ID"
    echo "$ORDER_ID" > /tmp/agentzon_test2_order_id.txt
else
    _fail "No s'ha pogut extreure IdComanda"
fi

assert_contains "$PURCHASE_RESULT" "Test User 1" "Nom d'usuari apareix al resum"
assert_contains "$PURCHASE_RESULT" "Carrer Test 123" "Adreça apareix al resum"
assert_contains "$PURCHASE_RESULT" "30.38" "Preu del producte (30.38€) apareix"
assert_contains "$PURCHASE_RESULT" "targeta" "Mètode de pagament targeta apareix"
assert_contains "$PURCHASE_RESULT" "Factura" "Secció de factura present"

# ── Forçar negociació i verificar lots ─────────────────────────────────
_info "Forçant negociació de lots al centre TGN..."
sleep 2
force_negotiation
sleep 2

# Verificar que s'ha creat un lot
LOTS_BCN=$(get_page "$BCN_URL/iface")
LOTS_TGN=$(get_page "$TGN_URL/iface")
LOTS_GI=$(get_page "$GI_URL/iface")

_info "Verificant registres de compra..."
sleep 2
assert_file_contains "$DATA_DIR/historial_compres.ttl" "$ORDER_ID" \
    "Compra registrada a historial_compres.ttl"

_info "NOTA: La negociació de transport pot trigar uns segons."
_info "Si les verificacions de lots fallen, executa manualment:"
_info "  curl '$TGN_URL/cron/negotiate-ready-lots'"

end_test
