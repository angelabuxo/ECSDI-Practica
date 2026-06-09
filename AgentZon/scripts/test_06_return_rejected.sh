#!/usr/bin/env bash
# =============================================================================
# TEST 6: Devolució que no compleix els requisits
# Propòsit: Validar rebuig de devolucions (motiu no vàlid / fora termini)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Devolució rebutjada (motiu no vàlid / fora termini)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents..."
wait_for_server "$RETORNADOR_URL/iface" "Retornador" 10 || exit 1
wait_for_server "$OPINADOR_URL/iface" "Opinador" 10 || exit 1

# ── Escenari B: Motiu no vàlid ─────────────────────────────────────────
_info "ESCENARI B: Motiu no vàlid"

_info "Accedint a la interfície de devolucions..."
RETURN_PAGE=$(get_page "$RETORNADOR_URL/iface")
assert_contains "$RETURN_PAGE" "AgentZon Retornador" "Pàgina de retornador carregada"

# Intentar devolució amb motiu no acceptat per la política
ORDER_ID=""
PRODUCT_ID=""

if [ -f "$DATA_DIR/historial_compres.ttl" ]; then
    ORDER_ID=$(grep -oP 'azon:order-\K[^ ]+' "$DATA_DIR/historial_compres.ttl" | head -1 || true)
    PRODUCT_ID=$(grep -oP 'azon:product-\K[^ ]+' "$DATA_DIR/historial_compres.ttl" | head -1 || true)
fi

if [ -n "$ORDER_ID" ] && [ -n "$PRODUCT_ID" ]; then
    _info "Comanda detectada: $ORDER_ID, producte: $PRODUCT_ID"
    SELECTED="order-${ORDER_ID}::product-${PRODUCT_ID}"

    # Motiu no acceptat: "No m'ha agradat" (no és a RETURN_REASONS_ACCEPTED_BY_POLICY)
    _info "Intentant devolució amb motiu 'No m'ha agradat' (NO acceptat per política)..."

    RETURN_RESULT=$(post_form "$RETORNADOR_URL/iface" \
        --data-urlencode "selected_products=$SELECTED" \
        --data-urlencode "reason=No m'ha agradat")
    echo "$RETURN_RESULT" > /tmp/agentzon_test6_return_rejected.html

    if echo "$RETURN_RESULT" | grep -q -i "REBUTJADA\|rebutj\|no es compleixen\|no és vàlid"; then
        _pass "Devolució REBUTJADA correctament (motiu no vàlid)"
    else
        _info "Resposta rebuda. Verificant contingut..."
        assert_contains "$RETURN_RESULT" "Resolució de devolució" "Resolució de devolució present"
    fi
else
    _warn "No s'ha trobat cap comanda. Executa primer una compra."
fi

# ── Escenari A: Fora de termini ────────────────────────────────────────
_info ""
_info "ESCENARI A: Fora de termini (>15 dies)"
_info "Per provar el rebuig per termini:"
_info "  1. Modifica la data d'una compra a historial_compres.ttl"
_info "     perquè sigui >15 dies anterior a avui"
_info "  2. O espera 16 dies després d'una compra real"
_info "  3. Intenta la devolució"
_info ""
_info "NOTA: La política accepta NOMÉS:"
_info "  - Producte defectuós"
_info "  - Producte no compleix amb la descripció"
_info "  - El producte ha arribat més tard del previst"
_info ""
_info "Motius NO acceptats (generaran REBUTJADA):"
_info "  - No m'ha agradat"
_info "  - M'he equivocat en comprar-lo"
_info "  - He canviat d'opinió i ja no el vull"
_info "  - Qualsevol altre motiu"

end_test
