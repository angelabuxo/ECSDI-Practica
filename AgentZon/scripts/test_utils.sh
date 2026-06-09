#!/usr/bin/env bash
# Shared utilities per als jocs de prova d'AgentZon.
# S'ha de fer `source` des dels scripts de test individuals.

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── Default hosts & ports ─────────────────────────────────────────────
HOST="${HOST:-127.0.0.1}"
CURL_OPTS="${CURL_OPTS:--s -L --connect-timeout 5 --max-time 120}"
BASE_URL="http://${HOST}"

CERCADOR_URL="${BASE_URL}:9001"
COMPRA_URL="${BASE_URL}:9002"
BCN_URL="${BASE_URL}:9003"
OPINADOR_URL="${BASE_URL}:9004"
COBRADOR_URL="${BASE_URL}:9005"
RETORNADOR_URL="${BASE_URL}:9009"
GI_URL="${BASE_URL}:9007"
TGN_URL="${BASE_URL}:9008"
FAST_URL="${BASE_URL}:9010"
ECONOMY_URL="${BASE_URL}:9011"
VENEDOR_URL="${BASE_URL}:9012"

# ── Test counters ──────────────────────────────────────────────────────
PASSED=0
FAILED=0
TEST_NAME=""

# ── Logging helpers ────────────────────────────────────────────────────
_pass()  { echo -e "  ${GREEN}[PASS]${NC} $*"; PASSED=$((PASSED+1)); }
_fail()  { echo -e "  ${RED}[FAIL]${NC} $*"; FAILED=$((FAILED+1)); }
_info()  { echo -e "  ${BLUE}[INFO]${NC} $*"; }
_warn()  { echo -e "  ${YELLOW}[WARN]${NC} $*"; }

start_test() {
    TEST_NAME="$1"
    echo
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  TEST: ${TEST_NAME}${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    PASSED=0
    FAILED=0
}

end_test() {
    local total=$((PASSED + FAILED))
    echo
    if [ "$FAILED" -eq 0 ]; then
        echo -e "  ${GREEN}Resultat: ${PASSED}/${total} comprovacions correctes${NC}"
    else
        echo -e "  ${RED}Resultat: ${FAILED}/${total} comprovacions fallides${NC}"
    fi
    echo -e "${BLUE}────────────────────────────────────────────────────────${NC}"
}

# ── Server readiness ──────────────────────────────────────────────────
wait_for_server() {
    local url="$1"
    local desc="${2:-$url}"
    local max_attempts="${3:-30}"
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null --connect-timeout 2 "$url" 2>/dev/null; then
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    _fail "El servidor $desc no respon a $url"
    return 1
}

check_all_agents() {
    local missing=0
    _info "Verificant que tots els agents estan actius..."
    for url in "$CERCADOR_URL/iface" "$COMPRA_URL/iface" "$BCN_URL/iface" \
               "$OPINADOR_URL/iface" "$RETORNADOR_URL/iface" \
               "$TGN_URL/iface" "$GI_URL/iface" "$VENEDOR_URL/iface"; do
        if ! curl -s -o /dev/null --connect-timeout 2 "$url"; then
            _warn "  No es pot connectar a: $url"
            missing=$((missing + 1))
        fi
    done
    if [ $missing -gt 0 ]; then
        _warn "$missing agent(s) no responen. Pots arrencar-los amb: ./run_agents.sh"
    fi
    return $missing
}

# ── Form submission helpers ────────────────────────────────────────────
# Fa POST amb url-encoded form data. Retorna el body i guarda la URL final a $REDIRECT_URL.
post_form() {
    local url="$1"
    shift
    curl $CURL_OPTS -X POST "$url" "$@"
}

get_page() {
    local url="$1"
    shift
    curl $CURL_OPTS "$url" "$@"
}

# ── Assertion helpers ──────────────────────────────────────────────────
assert_contains() {
    local haystack="$1"
    local needle="$2"
    local desc="${3:-Conté '$needle'}"
    if echo "$haystack" | grep -q -F "$needle"; then
        _pass "$desc"
    else
        _fail "$desc"
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local desc="${3:-No conté '$needle'}"
    if echo "$haystack" | grep -q -F "$needle"; then
        _fail "$desc"
    else
        _pass "$desc"
    fi
}

assert_file_contains() {
    local file="$1"
    local needle="$2"
    local desc="${3:-Fitxer $file conté '$needle'}"
    if [ -f "$file" ] && grep -q -F "$needle" "$file"; then
        _pass "$desc"
    else
        _fail "$desc"
    fi
}

assert_file_not_empty() {
    local file="$1"
    local desc="${2:-Fitxer $file no està buit}"
    if [ -f "$file" ] && [ -s "$file" ]; then
        _pass "$desc"
    else
        _fail "$desc"
    fi
}

# ── Search product (per obtenir IDs) ───────────────────────────────────
search_products() {
    local text="${1:-}"
    local category="${2:-}"
    local brand="${3:-}"
    local min_price="${4:-}"
    local max_price="${5:-}"
    post_form "$CERCADOR_URL/iface" \
        --data-urlencode "text=$text" \
        --data-urlencode "category=$category" \
        --data-urlencode "brand=$brand" \
        --data-urlencode "min_price=$min_price" \
        --data-urlencode "max_price=$max_price"
}

# ── Force logistics negotiation ────────────────────────────────────────
force_negotiation() {
    _info "Forçant negociació de lots..."
    for centre_url in "$BCN_URL" "$TGN_URL" "$GI_URL"; do
        curl $CURL_OPTS -o /dev/null "$centre_url/cron/negotiate-ready-lots" 2>/dev/null || true
    done
}

# ── Purchase products ──────────────────────────────────────────────────
purchase_products() {
    local user_name="$1"
    local street="$2"
    local city="$3"
    local priority="$4"
    local payment="${5:-targeta}"
    shift 5
    local product_ids=("$@")

    local form_args=()
    for pid in "${product_ids[@]}"; do
        form_args+=(--data-urlencode "selected_product_ids=$pid")
    done
    form_args+=(--data-urlencode "user_name=$user_name")
    form_args+=(--data-urlencode "street_address=$street")
    form_args+=(--data-urlencode "city=$city")
    form_args+=(--data-urlencode "priority=$priority")
    form_args+=(--data-urlencode "payment_method=$payment")

    post_form "$COMPRA_URL/iface" "${form_args[@]}"
}

# ── Verify TTL data files ──────────────────────────────────────────────
verify_ttl_not_empty() {
    local file="$1"
    local desc="${2:-$file conté dades}"
    if [ -f "$file" ] && [ -s "$file" ] && [ "$(wc -l < "$file")" -gt 1 ]; then
        _pass "$desc"
    else
        _fail "$desc"
    fi
}

# ── Extract order ID from HTML ─────────────────────────────────────────
extract_order_id() {
    local html="$1"
    echo "$html" | grep -oP 'Comanda:\s*<strong>\K[^<]+' | head -1
}

# ── Clean data files between tests ─────────────────────────────────────
clean_runtime_data() {
    _info "Netejant dades de runtime..."
    local data_dir="${DATA_DIR:-data}"
    for f in historial_cerques.ttl historial_compres.ttl pagaments.ttl \
             seguiment_enviaments.ttl lots-CL-BCN.ttl lots-CL-GI.ttl lots-CL-TGN.ttl \
             devolucions.ttl feedback.ttl dades_bancaries_usuari.ttl \
             dades_bancaries_venedors_externs.ttl dades_enviament_usuari.ttl \
             responsable_enviament_productes.ttl proactive_state.json; do
        if [ -f "$data_dir/$f" ]; then
            echo "" > "$data_dir/$f"
        fi
    done
    _info "Dades netejades."
}
