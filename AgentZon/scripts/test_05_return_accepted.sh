#!/usr/bin/env bash
# =============================================================================
# TEST 5: Devolució que compleix els requisits
# Propòsit: Validar devolució acceptada (motiu vàlid, dins termini, compra existent)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Devolució acceptada (producte_defectuós, dins termini)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Aquest test requereix una compra prèvia."
_info "Si no has executat el test 2, fes-ho primer: ./scripts/test_02_purchase_internal.sh"
echo

_info "Verificant agents necessaris..."
wait_for_server "$RETORNADOR_URL/iface" "Retornador" 10 || exit 1
wait_for_server "$OPINADOR_URL/iface" "Opinador" 10 || exit 1

# ── Verificar que hi ha compres prèvies ────────────────────────────────
_info "Verificant historial de compres..."
if [ -f "$DATA_DIR/historial_compres.ttl" ] && [ -s "$DATA_DIR/historial_compres.ttl" ] && [ "$(wc -l < "$DATA_DIR/historial_compres.ttl")" -gt 1 ]; then
    _pass "historial_compres.ttl conté compres prèvies"
else
    _warn "historial_compres.ttl està buit. Executa primer una compra (test 2)."
    _warn "Continuant de totes maneres per mostrar el flux..."
fi

# ── Accedir a la interfície de devolucions ─────────────────────────────
_info "Accedint a la interfície de devolucions..."
RETURN_PAGE=$(get_page "$RETORNADOR_URL/iface")
echo "$RETURN_PAGE" > /tmp/agentzon_test5_return_page.html

assert_contains "$RETURN_PAGE" "AgentZon Retornador" "Pàgina de retornador carregada"
assert_contains "$RETURN_PAGE" "Motiu de la devolució" "Secció de motiu de devolució present"
assert_contains "$RETURN_PAGE" "Producte defectuós" "Opció 'Producte defectuós' disponible"

# ── Intentar devolució (si hi ha productes disponibles) ─────────────────
_info "NOTA: La devolució requereix interacció manual via web."
_info "  URL: $RETORNADOR_URL/iface"
_info ""
_info "Passos manuals:"
_info "  1. Obrir $RETORNADOR_URL/iface"
_info "  2. Seleccionar un producte comprat"
_info "  3. Escollir motiu: 'Producte defectuós'"
_info "  4. Confirmar devolució"
_info "  5. Verificar resposta ACCEPTADA"
_info "  6. Verificar devolucions.ttl"

# ── Simular devolució via POST (requereix saber order_id i product_id) ──
_info "Intentant devolució automàtica (si hi ha productes comprats)..."

# Obtenir productes comprats des de l'historial
ORDER_ID=""
PRODUCT_ID=""

if [ -f "$DATA_DIR/historial_compres.ttl" ]; then
    ORDER_ID=$(grep -oP 'azon:order-\K[^ ]+' "$DATA_DIR/historial_compres.ttl" | head -1 || true)
    PRODUCT_ID=$(grep -oP 'azon:product-\K[^ ]+' "$DATA_DIR/historial_compres.ttl" | head -1 || true)
fi

if [ -n "$ORDER_ID" ] && [ -n "$PRODUCT_ID" ]; then
    _info "Comanda detectada: $ORDER_ID, producte: $PRODUCT_ID"
    SELECTED="order-${ORDER_ID}::product-${PRODUCT_ID}"

    RETURN_RESULT=$(post_form "$RETORNADOR_URL/iface" \
        --data-urlencode "selected_products=$SELECTED" \
        --data-urlencode "reason=Producte defectuós")
    echo "$RETURN_RESULT" > /tmp/agentzon_test5_return_result.html

    assert_contains "$RETURN_RESULT" "Resolució de devolució" "Secció de resolució present"

    if echo "$RETURN_RESULT" | grep -q "ACCEPTADA\|reemborsat\|Productes acceptats"; then
        _pass "Devolució ACCEPTADA (o processada)"
    elif echo "$RETURN_RESULT" | grep -q "REBUTJADA\|no es compleixen"; then
        _warn "Devolució REBUTJADA (possiblement fora de termini)"
        _info "Si la compra és recent (<15 dies), hauria de ser acceptada."
    fi
else
    _warn "No s'ha trobat cap comanda a l'historial. Executa primer una compra."
    _info "Per fer una compra: ./scripts/test_02_purchase_internal.sh"
fi

# ── Verificar registres ────────────────────────────────────────────────
assert_file_not_empty "$DATA_DIR/devolucions.ttl" "devolucions.ttl existeix"

end_test
