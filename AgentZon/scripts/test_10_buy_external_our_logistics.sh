#!/usr/bin/env bash
# =============================================================================
# TEST 10: Compra d'1 producte extern amb enviament nostre
# Propòsit: Validar compra de producte extern amb logística AgentZon
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Compra producte extern (logística AgentZon)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Aquest test requereix un producte extern creat prèviament (test 9)."
echo

_info "Verificant agents..."
check_all_agents || _warn "Alguns agents no responen"

# ── Buscar el producte extern creat al test 9 ──────────────────────────
_info "Cercant productes externs disponibles..."

# Buscar per nom "Smart Fitness Tracker" (del test 9)
SEARCH_RESULT=$(search_products "Smart Fitness Tracker" "" "" "" "")
echo "$SEARCH_RESULT" > /tmp/agentzon_test10_search.html

if echo "$SEARCH_RESULT" | grep -q "Smart Fitness Tracker"; then
    _pass "Producte extern 'Smart Fitness Tracker' trobat"

    # Extreure l'ID del producte extern
    EXT_ID=$(echo "$SEARCH_RESULT" | grep -oP 'value="(EXT-\d+)"' | head -1 | grep -oP 'EXT-\d+' || true)
    if [ -z "$EXT_ID" ]; then
        # Intentar amb PXXXX (si el sistema li assigna un ID normal)
        EXT_ID=$(echo "$SEARCH_RESULT" | grep -oP 'value="(P\d+)"' | tail -1 | grep -oP 'P\d+' || true)
    fi

    if [ -n "$EXT_ID" ]; then
        _info "ID del producte extern: $EXT_ID"

        # ── Comprar el producte extern ──────────────────────────────────
        _info "Comprant producte extern $EXT_ID..."

        PURCHASE_RESULT=$(purchase_products \
            "Test External 1" \
            "Carrer Extern 50" \
            "Barcelona" \
            "7 dies" \
            "targeta" \
            "$EXT_ID")
        echo "$PURCHASE_RESULT" > /tmp/agentzon_test10_purchase.html

        ORDER_ID=$(extract_order_id "$PURCHASE_RESULT")
        if [ -n "$ORDER_ID" ]; then
            _pass "IdComanda generat: $ORDER_ID"
        fi

        assert_contains "$PURCHASE_RESULT" "Test External 1" "Nom d'usuari al resum"
        assert_contains "$PURCHASE_RESULT" "79.99" "Preu del producte (79.99€) al resum"
        assert_contains "$PURCHASE_RESULT" "Factura" "Secció de factura present"

        # ── Forçar negociació ──────────────────────────────────────────
        _info "Forçant negociació al centre BCN..."
        sleep 2
        curl $CURL_OPTS -o /dev/null "$BCN_URL/cron/negotiate-ready-lots" 2>/dev/null || true
        sleep 3

        # ── Verificacions ──────────────────────────────────────────────
        _info "Verificant registres..."
        sleep 2

        # Verificar lots a BCN (el producte extern amb logística nostra va a BCN)
        LOTS_BCN=$(get_page "$BCN_URL/iface")
        assert_contains "$LOTS_BCN" "Centre logístic" "Pàgina de lots BCN carregada"

        if [ -n "$ORDER_ID" ]; then
            assert_file_contains "$DATA_DIR/historial_compres.ttl" "$ORDER_ID" \
                "Compra registrada a historial_compres.ttl"
        fi

        # Verificar pagaments (2: COBRAMENT + PAGAMENT)
        if [ -f "$DATA_DIR/pagaments.ttl" ] && [ -s "$DATA_DIR/pagaments.ttl" ]; then
            _pass "pagaments.ttl conté registres de pagament"
            if grep -q "COBRAMENT\|PAGAMENT" "$DATA_DIR/pagaments.ttl"; then
                _pass "Pagaments amb sentits COBRAMENT/PAGAMENT registrats"
            fi
        fi

        _info "NOTA: El producte extern amb logística nostra:"
        _info "  - Centre BCN gestiona l'enviament"
        _info "  - Es cobra a l'usuari QUAN S'ENVIA"
        _info "  - Es paga al venedor QUAN S'ENVIA"
    else
        _warn "No s'ha pogut extreure l'ID del producte extern."
    fi
else
    _warn "No s'ha trobat 'Smart Fitness Tracker'. Executa primer el test 9:"
    _info "  ./scripts/test_09_external_product.sh"
fi

end_test
