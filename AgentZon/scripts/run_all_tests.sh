#!/usr/bin/env bash
# =============================================================================
# run_all_tests.sh — Executa tots els jocs de prova d'AgentZon en seqüència.
#
# Ús:
#   ./scripts/run_all_tests.sh          # Executa tots els tests
#   ./scripts/run_all_tests.sh 1 3      # Executa només tests 1 i 3
#   ./scripts/run_all_tests.sh --clean  # Neteja dades i executa tots
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS=(
    "01_search:TEST 1: Cerca de productes"
    "02_purchase_internal:TEST 2: Compra producte intern"
    "03_purchase_multi_single_centre:TEST 3: Compra múltiple (1 centre)"
    "04_purchase_multi_centres:TEST 4: Compra múltiple (3 centres)"
    "05_return_accepted:TEST 5: Devolució acceptada"
    "06_return_rejected:TEST 6: Devolució rebutjada"
    "07_suggestions:TEST 7: Suggeriments"
    "08_feedback:TEST 8: Feedback"
    "09_external_product:TEST 9: Afegir producte extern"
    "10_buy_external_our_logistics:TEST 10: Compra extern (logística nostra)"
    "11_buy_external_their_logistics:TEST 11: Compra extern (logística venedor)"
)

CLEAN_FIRST=false
SELECTED_TESTS=()

for arg in "$@"; do
    case "$arg" in
        --clean|-c) CLEAN_FIRST=true ;;
        *) SELECTED_TESTS+=("$arg") ;;
    esac
done

echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  AgentZon — Jocs de Prova (Entrega 3)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Data: $(date)"
echo "Directori: $ROOT_DIR"
echo

# ── Verificar que els scripts existeixen ───────────────────────────────
for t in "${TESTS[@]}"; do
    slug="${t%%:*}"
    script="$SCRIPT_DIR/test_${slug}.sh"
    if [ ! -f "$script" ]; then
        echo -e "${RED}ERROR: No s'ha trobat $script${NC}"
        exit 1
    fi
done

# ── Netejar dades si s'ha demanat ──────────────────────────────────────
if [ "$CLEAN_FIRST" = true ]; then
    echo -e "${BLUE}[PRE] Netejant dades de runtime...${NC}"
    "$ROOT_DIR/cleanup_data.sh" 2>/dev/null || true
    echo
fi

# ── Executar tests ─────────────────────────────────────────────────────
PASSED_TESTS=0
FAILED_TESTS=0
TOTAL_TESTS=0

for t in "${TESTS[@]}"; do
    slug="${t%%:*}"
    label="${t#*:}"
    script="$SCRIPT_DIR/test_${slug}.sh"

    # Filtrar per tests seleccionats
    if [ ${#SELECTED_TESTS[@]} -gt 0 ]; then
        test_num="${slug%%_*}"
        found=false
        for s in "${SELECTED_TESTS[@]}"; do
            if [ "$s" = "$test_num" ]; then
                found=true
                break
            fi
        done
        if [ "$found" = false ]; then
            continue
        fi
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo
    echo -e "${BLUE}▶ Executant $label ($slug)...${NC}"

    if bash "$script"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓ $label COMPLETAT${NC}"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗ $label HA FALLAT${NC}"
    fi
done

# ── Resum final ────────────────────────────────────────────────────────
echo
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  RESUM FINAL${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "  Tests executats: $TOTAL_TESTS"
echo -e "  ${GREEN}Correctes: $PASSED_TESTS${NC}"
if [ "$FAILED_TESTS" -gt 0 ]; then
    echo -e "  ${RED}Fallides: $FAILED_TESTS${NC}"
fi
echo

if [ "$FAILED_TESTS" -eq 0 ] && [ "$TOTAL_TESTS" -gt 0 ]; then
    echo -e "${GREEN}  Tots els tests han passat correctament!${NC}"
    exit 0
elif [ "$TOTAL_TESTS" -eq 0 ]; then
    echo -e "${BLUE}  No s'ha executat cap test.${NC}"
    exit 0
else
    echo -e "${RED}  Alguns tests han fallat. Revisa la sortida anterior.${NC}"
    exit 1
fi
