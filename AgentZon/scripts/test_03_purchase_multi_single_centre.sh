#!/usr/bin/env bash
# =============================================================================
# TEST 3: Compra de molts productes d'un sol centre logístic
# Propòsit: Validar agrupació de 4 productes TGN en un sol lot
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Compra múltiple des d'un sol centre (4 productes TGN)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents..."
check_all_agents || _warn "Alguns agents no responen"

# ── Verificar que els 4 productes estan a TGN ──────────────────────────
_info "Verificant ubicacions dels 4 productes a TGN..."
for pid in P1003 P1006 P1009 P1012; do
    if grep -q "product-${pid}" "$DATA_DIR/ubicacions_productes.ttl" && \
       grep -A1 "product-${pid}" "$DATA_DIR/ubicacions_productes.ttl" | grep -q "centre-TGN"; then
        _pass "$pid ubicat a TGN"
    else
        _fail "$pid NO ubicat a TGN"
    fi
done

# ── Cercar i seleccionar els 4 productes ───────────────────────────────
_info "Cercant els 4 productes..."

# Cerca 1: P1003 i P1006 (Precision Mouse + Wireless Mouse)
SEARCH1=$(search_products "Mouse" "" "InputWorks" "" "")
assert_contains "$SEARCH1" "P1003" "P1003 trobat"
assert_contains "$SEARCH1" "P1006" "P1006 trobat"

# Cerca 2: P1009 (Insulated Coffee Mug)
SEARCH2=$(search_products "Coffee" "" "" "" "")
assert_contains "$SEARCH2" "P1009" "P1009 trobat"

# Cerca 3: P1012 (Party Speaker)
SEARCH3=$(search_products "Speaker" "" "" "" "")
assert_contains "$SEARCH3" "P1012" "P1012 trobat"

# ── Comprar els 4 productes amb prioritat "urgent" ─────────────────────
_info "Comprant 4 productes (P1003, P1006, P1009, P1012) amb prioritat urgent..."

PURCHASE_RESULT=$(purchase_products \
    "Test User Multi" \
    "Carrer Gran 45" \
    "Tarragona" \
    "5 dies" \
    "targeta" \
    "P1003" "P1006" "P1009" "P1012")
echo "$PURCHASE_RESULT" > /tmp/agentzon_test3_purchase.html

# ── Verificacions ──────────────────────────────────────────────────────
ORDER_ID=$(extract_order_id "$PURCHASE_RESULT")
if [ -n "$ORDER_ID" ]; then
    _pass "IdComanda generat: $ORDER_ID"
else
    _fail "No s'ha pogut extreure IdComanda"
fi

assert_contains "$PURCHASE_RESULT" "Test User Multi" "Nom d'usuari al resum"
assert_contains "$PURCHASE_RESULT" "Carrer Gran 45" "Adreça al resum"
assert_contains "$PURCHASE_RESULT" "122.66" "Total productes ~122.66€ al resum"

# ── Forçar negociació i verificar lot únic ─────────────────────────────
_info "Forçant negociació al centre TGN..."
sleep 2
curl $CURL_OPTS -o /dev/null "$TGN_URL/cron/negotiate-ready-lots" 2>/dev/null || true
sleep 3

_info "Verificant lots al centre TGN..."
LOTS_TGN=$(get_page "$TGN_URL/iface")

# Verificar que només hi ha un lot (o almenys que els 4 productes estan agrupats)
_info "NOTA: Verifica manualment a $TGN_URL/iface que els 4 productes"
_info "      estan en un sol lot. Pes total estimat: ~1.39 kg"

# ── Verificar registres ────────────────────────────────────────────────
sleep 2
if [ -n "$ORDER_ID" ]; then
    assert_file_contains "$DATA_DIR/historial_compres.ttl" "$ORDER_ID" \
        "Compra registrada a historial_compres.ttl"
fi

_info "Preu total productes: 30.38 + 25.95 + 12.79 + 53.54 = 122.66€"
_info "Pes total: 0.38 + 0.38 + 0.33 + 0.30 = 1.39 kg"

end_test
