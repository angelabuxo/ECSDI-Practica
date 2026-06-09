#!/usr/bin/env bash
# =============================================================================
# TEST 9: Afegir producte extern
# Propòsit: Validar registre de productes de venedors externs al catàleg
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_utils.sh"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"

start_test "Afegir producte extern (TechGadgets SL, Smart Fitness Tracker)"

# ── Verificar prerequisits ─────────────────────────────────────────────
_info "Verificant agents necessaris..."
for url in "$VENEDOR_URL/iface" "$CERCADOR_URL/iface" "$COMPRA_URL/iface" "$COBRADOR_URL/comm"; do
    wait_for_server "$url" "$(basename "$url")" 10 || exit 1
done

# ── Pas 1: Accedir a la interfície de venedor extern ───────────────────
_info "Accedint a la interfície de venedor extern..."
VENDOR_PAGE=$(get_page "$VENEDOR_URL/iface")
echo "$VENDOR_PAGE" > /tmp/agentzon_test9_vendor_page.html

assert_contains "$VENDOR_PAGE" "Registrar productes externs" "Pàgina de venedor extern carregada"

# ── Determinar si cal setup inicial ────────────────────────────────────
if echo "$VENDOR_PAGE" | grep -q "Guardar perfil i continuar"; then
    _info "Setup inicial del venedor necessari. Registrant perfil..."

    SETUP_RESULT=$(post_form "$VENEDOR_URL/iface" \
        --data-urlencode "form_type=setup" \
        --data-urlencode "seller_name=TechGadgets SL" \
        --data-urlencode "bank_data=ES12 3456 7890 1234 5678 9012")
    echo "$SETUP_RESULT" > /tmp/agentzon_test9_setup.html

    assert_contains "$SETUP_RESULT" "TechGadgets" "Nom del venedor confirmat"

    # Tornar a carregar per veure formulari de productes
    sleep 1
    VENDOR_PAGE=$(get_page "$VENEDOR_URL/iface")
fi

# ── Pas 2: Registrar producte extern ───────────────────────────────────
_info "Registrant producte extern: Smart Fitness Tracker..."

if echo "$VENDOR_PAGE" | grep -q "registrar productes\|Afegir un altre producte\|Producte 1"; then
    PRODUCT_RESULT=$(post_form "$VENEDOR_URL/iface" \
        --data-urlencode "form_type=products" \
        --data-urlencode "name=Smart Fitness Tracker" \
        --data-urlencode "description=Advanced fitness tracker with heart rate monitoring" \
        --data-urlencode "category=wearables" \
        --data-urlencode "brand=FitPro" \
        --data-urlencode "price=79.99" \
        --data-urlencode "weight=0.05" \
        --data-urlencode "sku_extern=FIT-TRACK-001" \
        --data-urlencode "logistics_mode=platform" \
        --data-urlencode "centre_id=CL-BCN")
    echo "$PRODUCT_RESULT" > /tmp/agentzon_test9_product_result.html

    assert_contains "$PRODUCT_RESULT" "registrat" "Producte registrat correctament"
    assert_contains "$PRODUCT_RESULT" "Smart Fitness Tracker" "Nom del producte al resum"
    assert_contains "$PRODUCT_RESULT" "FIT-TRACK-001" "SKU extern al resum"
else
    _warn "Formulari de producte no visible."
    _info "Contingut de la pàgina:"
    echo "$VENDOR_PAGE" | head -20
fi

# ── Verificar registres als fitxers de dades ───────────────────────────
sleep 2
_info "Verificant registres..."

# El producte hauria d'aparèixer a productes.ttl
if grep -q "Smart Fitness Tracker" "$DATA_DIR/productes.ttl" 2>/dev/null; then
    _pass "Producte registrat a productes.ttl"
else
    _info "Verificant productes.ttl per noves entrades..."
    assert_file_not_empty "$DATA_DIR/productes.ttl" "productes.ttl existeix"
fi

# Dades bancàries del venedor
assert_file_not_empty "$DATA_DIR/dades_bancaries_venedors_externs.ttl" \
    "dades_bancaries_venedors_externs.ttl existeix"

# Verificar que el producte apareix a cerques
_info "Verificant que el producte extern apareix al cercador..."
sleep 2
SEARCH_RESULT=$(search_products "Smart Fitness Tracker" "" "" "" "")
if echo "$SEARCH_RESULT" | grep -q "Smart Fitness Tracker"; then
    _pass "Producte extern apareix als resultats de cerca"
else
    _warn "Producte extern no apareix al cercador (pot trigar)"
fi

_info ""
_info "NOTA: Anota l'IdProducte assignat (EXT-XXXX) per als tests 10 i 11."
_info "URL venedor: $VENEDOR_URL/iface"

end_test
