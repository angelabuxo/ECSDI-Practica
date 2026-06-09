#!/usr/bin/env bash
# =============================================================================
# TEST 1: Cerca de productes
# Propòsit: Validar la funcionalitat de cerca amb múltiples criteris
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Cerca de productes (Coffee, 0-50€)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents necessaris..."
wait_for_server "$CERCADOR_URL/iface" "Cercador" 10 || exit 1
wait_for_server "$OPINADOR_URL/iface" "Opinador" 10 || exit 1

# ── Executar cerca ─────────────────────────────────────────────────────
_info "Cercant: text='Coffee', rang preu 0-50€..."
SEARCH_RESULT=$(search_products "Coffee" "" "" "0" "50")
echo "$SEARCH_RESULT" > /tmp/agentzon_test1_search.html

# ── Verificacions ──────────────────────────────────────────────────────
_info "Verificant resultats de cerca..."
assert_contains "$SEARCH_RESULT" "P1001" "Producte P1001 (Minimalist Coffee Mug) apareix als resultats"
assert_contains "$SEARCH_RESULT" "P1009" "Producte P1009 (Insulated Coffee Mug) apareix als resultats"
assert_contains "$SEARCH_RESULT" "27.01" "Preu de P1001 (27.01€) visible"
assert_contains "$SEARCH_RESULT" "12.79" "Preu de P1009 (12.79€) visible"
assert_contains "$SEARCH_RESULT" "CasaNova" "Marca CasaNova visible"
assert_contains "$SEARCH_RESULT" "Homely" "Marca Homely visible"

# ── Verificar registre a historial_cerques ─────────────────────────────
_info "Verificant registre a historial_cerques.ttl..."
sleep 2
assert_file_contains "$DATA_DIR/historial_cerques.ttl" "Coffee" \
    "Cerca 'Coffee' registrada a historial_cerques.ttl"
assert_file_not_empty "$DATA_DIR/historial_cerques.ttl" \
    "historial_cerques.ttl no és buit"

end_test
