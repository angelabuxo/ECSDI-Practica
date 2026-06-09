#!/usr/bin/env bash
# =============================================================================
# TEST 8: Donar feedback a producte
# Propòsit: Validar registre de valoracions i la seva integració
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Feedback de producte (valoració 5 estrelles)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Aquest test requereix compres prèvies amb almenys 14 dies"
_info "o mode demo (OPINADOR_FEEDBACK_MIN_SECONDS)."
_info "NOTA: Si OPINADOR_FEEDBACK_MIN_SECONDS=60, espera 60s després de comprar."
echo

_info "Verificant agents..."
wait_for_server "$OPINADOR_URL/iface" "Opinador" 10 || exit 1

# ── Verificar que hi ha compres ────────────────────────────────────────
_info "Verificant historial de compres..."
if ! [ -f "$DATA_DIR/historial_compres.ttl" ] || ! [ -s "$DATA_DIR/historial_compres.ttl" ] || [ "$(wc -l < "$DATA_DIR/historial_compres.ttl")" -le 1 ]; then
    _fail "No hi ha compres a l'historial. Executa primer una compra (test 2)."
    _info "./scripts/test_02_purchase_internal.sh"
    end_test
    exit 1
fi
_pass "historial_compres.ttl conté compres"

# ── Accedir a la pàgina d'opinador ─────────────────────────────────────
_info "Accedint a la interfície de feedback..."
OPINADOR_PAGE=$(get_page "$OPINADOR_URL/iface")
echo "$OPINADOR_PAGE" > /tmp/agentzon_test8_opinador.html

assert_contains "$OPINADOR_PAGE" "Valorar un producte" "Secció de valoració present"

# ── Comprovar si hi ha productes pendents de feedback ──────────────────
_info "Verificant productes pendents de valoració..."

if echo "$OPINADOR_PAGE" | grep -q "No tens cap producte pendent de valoració"; then
    _warn "No hi ha productes pendents de valoració."
    _info "Possible causes:"
    _info "  - La compra és massa recent (OPINADOR_FEEDBACK_MIN_SECONDS)"
    _info "  - Ja s'ha valorat tot"
    _info "  - OPINADOR_FEEDBACK_POLICY_DAYS=14 i no han passat 14 dies"
    _info ""
    _info "Per forçar feedback en mode demo, modifica config.py:"
    _info "  OPINADOR_FEEDBACK_MIN_SECONDS = 10"
    _info "  OPINADOR_FEEDBACK_POLICY_DAYS = 0"
else
    _pass "Hi ha productes disponibles per valorar"

    # ── Intentar enviar feedback ────────────────────────────────────────
    # Extreure un product_id disponible del select
    PRODUCT_ID=$(echo "$OPINADOR_PAGE" | grep -oP 'value="P\d+"' | head -1 | grep -oP 'P\d+' || true)

    if [ -n "$PRODUCT_ID" ]; then
        _info "Enviant feedback per $PRODUCT_ID (5 estrelles)..."

        FEEDBACK_RESULT=$(post_form "$OPINADOR_URL/iface" \
            --data-urlencode "action=feedback" \
            --data-urlencode "product_id=$PRODUCT_ID" \
            --data-urlencode "rating=5" \
            --data-urlencode "comment=Excel·lent producte, molt content amb la compra")
        echo "$FEEDBACK_RESULT" > /tmp/agentzon_test8_feedback_result.html

        assert_contains "$FEEDBACK_RESULT" "AgentZon Opinador" "Resposta de feedback rebuda"

        # Verificar registre a feedback.ttl
        sleep 2
        if [ -f "$DATA_DIR/feedback.ttl" ] && grep -q "$PRODUCT_ID" "$DATA_DIR/feedback.ttl"; then
            _pass "Feedback registrat a feedback.ttl per $PRODUCT_ID"
        else
            _info "Verificant feedback.ttl..."
            assert_file_not_empty "$DATA_DIR/feedback.ttl" "feedback.ttl té contingut"
        fi
    else
        _warn "No s'ha pogut extreure un product_id del formulari."
    fi
fi

_info "URL per feedback manual: $OPINADOR_URL/iface"

end_test
