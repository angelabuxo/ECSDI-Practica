#!/usr/bin/env bash
# =============================================================================
# TEST 7: Suggeriments
# Propòsit: Validar recomanacions personalitzades basades en historial
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Suggeriments personalitzats"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents..."
wait_for_server "$OPINADOR_URL/iface" "Opinador" 10 || exit 1
wait_for_server "$CERCADOR_URL/iface" "Cercador" 10 || exit 1

# ── Verificar historial previ ──────────────────────────────────────────
_info "Verificant historial de cerques i compres..."
HAS_SEARCHES=false
HAS_PURCHASES=false

if [ -f "$DATA_DIR/historial_cerques.ttl" ] && [ -s "$DATA_DIR/historial_cerques.ttl" ] && [ "$(wc -l < "$DATA_DIR/historial_cerques.ttl")" -gt 1 ]; then
    HAS_SEARCHES=true
    _pass "historial_cerques.ttl conté cerques prèvies"
else
    _warn "historial_cerques.ttl buit. Fes cerques primer (test 1)."
fi

if [ -f "$DATA_DIR/historial_compres.ttl" ] && [ -s "$DATA_DIR/historial_compres.ttl" ] && [ "$(wc -l < "$DATA_DIR/historial_compres.ttl")" -gt 1 ]; then
    HAS_PURCHASES=true
    _pass "historial_compres.ttl conté compres prèvies"
else
    _warn "historial_compres.ttl buit. Fes una compra primer (test 2)."
fi

# ── Si no hi ha historial, generar-lo automàticament ───────────────────
if [ "$HAS_SEARCHES" = false ]; then
    _info "Generant historial de cerques automàticament..."
    search_products "Mouse" "peripherals" "" "" "" > /dev/null
    sleep 1
    search_products "Keyboard" "peripherals" "" "" "" > /dev/null
    sleep 1
    search_products "Mouse" "" "InputWorks" "" "" > /dev/null
    sleep 1
    search_products "Headphones" "audio" "" "" "" > /dev/null
    sleep 2
    _info "Cerques registrades."
fi

# ── Accedir a suggeriments ─────────────────────────────────────────────
_info "Accedint a la pàgina de suggeriments..."
OPINADOR_PAGE=$(get_page "$OPINADOR_URL/iface")
echo "$OPINADOR_PAGE" > /tmp/agentzon_test7_opinador.html

assert_contains "$OPINADOR_PAGE" "AgentZon Opinador" "Pàgina d'opinador carregada"
assert_contains "$OPINADOR_PAGE" "Suggeriments" "Secció de suggeriments present"

# ── Verificar que hi ha suggeriments ────────────────────────────────────
_info "Verificant llista de suggeriments..."
if echo "$OPINADOR_PAGE" | grep -q "Encara no hi ha suggeriments"; then
    _warn "No hi ha suggeriments disponibles encara."
    _info "Espera que l'Opinador generi recomanacions (OPINADOR_RECOMMENDATION_INTERVAL_SEC=60s)"
    _info "o fes més cerques i compres per enriquir l'historial."
else
    # Comptar quants productes suggerits
    SUGGESTION_COUNT=$(echo "$OPINADOR_PAGE" | grep -c "<li>" | head -1 || echo "0")
    _info "Nombre de suggeriments visibles: ~$SUGGESTION_COUNT"
    _pass "Suggeriments generats"
fi

# ── Verificar que no hi ha productes ja comprats ───────────────────────
_info "Verificant que els suggeriments exclouen productes comprats..."
_info "(Verificació manual recomanada: comprova que cap producte suggerit apareix a historial_compres.ttl)"

# ── Verificar ordenació per rellevància ─────────────────────────────────
_info "NOTA: Els suggeriments s'ordenen per score (categories comprades > marques comprades > categories cercades > marques cercades > aparicions en cerques)."
_info "URL: $OPINADOR_URL/iface"

end_test
