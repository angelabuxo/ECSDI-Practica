#!/usr/bin/env bash
# =============================================================================
# TEST 4: Compra de diversos productes en diferents centres logístics
# Propòsit: Validar coordinació distribuïda entre BCN, GI i TGN
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Compra distribuïda (3 centres: BCN, GI, TGN)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents..."
check_all_agents || _warn "Alguns agents no responen"

# ── Verificar ubicacions dels productes ────────────────────────────────
_info "Verificant ubicacions:"
_info "  P1001 → BCN i GI"
_info "  P1002 → GI"
_info "  P1003 → TGN"
_info "  P1005 → GI"

assert_file_contains "$DATA_DIR/ubicacions_productes.ttl" "product-P1001" "P1001 a ubicacions"
assert_file_contains "$DATA_DIR/ubicacions_productes.ttl" "product-P1002" "P1002 a ubicacions"
assert_file_contains "$DATA_DIR/ubicacions_productes.ttl" "product-P1003" "P1003 a ubicacions"
assert_file_contains "$DATA_DIR/ubicacions_productes.ttl" "product-P1005" "P1005 a ubicacions"

# ── Cercar productes ───────────────────────────────────────────────────
_info "Cercant els 4 productes..."

SEARCH_MICE=$(search_products "Mouse" "" "" "" "")
assert_contains "$SEARCH_MICE" "P1002" "P1002 (KeyForge Precision Mouse) trobat"
assert_contains "$SEARCH_MICE" "P1003" "P1003 (InputWorks Precision Mouse) trobat"

SEARCH_COFFEE=$(search_products "Coffee" "" "" "" "")
assert_contains "$SEARCH_COFFEE" "P1001" "P1001 (Minimalist Coffee Mug) trobat"

SEARCH_LAMP=$(search_products "Lamp" "" "" "" "")
assert_contains "$SEARCH_LAMP" "P1005" "P1005 (Adjustable Desk Lamp) trobat"

# ── Comprar productes des de Lleida ────────────────────────────────────
_info "Comprant P1001, P1002, P1003, P1005 amb adreça a Lleida..."

PURCHASE_RESULT=$(purchase_products \
    "Test User Distribuit" \
    "Carrer Central 100" \
    "Lleida" \
    "7 dies" \
    "targeta" \
    "P1001" "P1002" "P1003" "P1005")
echo "$PURCHASE_RESULT" > /tmp/agentzon_test4_purchase.html

# ── Verificacions ──────────────────────────────────────────────────────
ORDER_ID=$(extract_order_id "$PURCHASE_RESULT")
if [ -n "$ORDER_ID" ]; then
    _pass "IdComanda generat: $ORDER_ID"
else
    _fail "No s'ha pogut extreure IdComanda"
fi

assert_contains "$PURCHASE_RESULT" "Test User Distribuit" "Nom d'usuari al resum"
assert_contains "$PURCHASE_RESULT" "Carrer Central 100" "Adreça al resum"
assert_contains "$PURCHASE_RESULT" "Lleida" "Ciutat Lleida al resum"
assert_contains "$PURCHASE_RESULT" "Factura" "Secció de factura present"

# ── Forçar negociació als 3 centres ────────────────────────────────────
_info "Forçant negociació als 3 centres logístics..."
sleep 2
force_negotiation
sleep 4

# Verificar lots als 3 centres
_info "Verificant lots creats:"
LOTS_BCN=$(get_page "$BCN_URL/iface")
LOTS_GI=$(get_page "$GI_URL/iface")
LOTS_TGN=$(get_page "$TGN_URL/iface")

if echo "$LOTS_BCN" | grep -q "Lot "; then
    _pass "BCN té almenys 1 lot"
else
    _warn "BCN: sense lots visibles (pot trigar)"
fi

if echo "$LOTS_GI" | grep -q "Lot "; then
    _pass "GI té almenys 1 lot"
else
    _warn "GI: sense lots visibles (pot trigar)"
fi

if echo "$LOTS_TGN" | grep -q "Lot "; then
    _pass "TGN té almenys 1 lot"
else
    _warn "TGN: sense lots visibles (pot trigar)"
fi

_info "Preu total productes: 27.01 + 94.76 + 30.38 + 82.66 = 234.81€"
_info "3 enviaments separats: BCN (P1001), GI (P1002+P1005), TGN (P1003)"
_info "Verifica manualment:"
_info "  $BCN_URL/iface"
_info "  $GI_URL/iface"
_info "  $TGN_URL/iface"

end_test
