#!/bin/bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SCRIPTS_DIR="${REPO_DIR}/airootfs/usr/local/lib/mados_installer/scripts"
MAIN_SCRIPT="${SCRIPTS_DIR}/configure-system.sh"
APPLY_SCRIPT="${SCRIPTS_DIR}/apply-configuration.sh"
PLYMOUTH_SCRIPT="${SCRIPTS_DIR}/setup-plymouth.sh"
REBUILD_SCRIPT="${SCRIPTS_DIR}/rebuild-initramfs.sh"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ERRORS=0; WARNINGS=0

step()    { echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${GREEN}==> $1${NC}"; }
info()    { echo -e "    ${YELLOW}$1${NC}"; }
ok()      { echo -e "    ${GREEN}✓ $1${NC}"; }
fail()    { echo -e "    ${RED}✗ $1${NC}"; ERRORS=$((ERRORS + 1)); }
warn()    { echo -e "    ${YELLOW}⚠ $1${NC}"; WARNINGS=$((WARNINGS + 1)); }

check_content() { 
    local file="$1" pattern="$2" desc="$3"
    if grep -qF "$pattern" "$file" 2>/dev/null; then
        ok "$desc"
    else
        fail "$desc (pattern not found: $pattern)"
    fi
}

# Check scripts exist
for script in "$MAIN_SCRIPT" "$APPLY_SCRIPT"; do
    if [[ ! -f "$script" ]]; then
        echo -e "${RED}ERROR: Script not found: $script${NC}"
        exit 1
    fi
done

step "Phase 1 – Validating bash syntax"
for script in "$MAIN_SCRIPT" "$APPLY_SCRIPT" "$PLYMOUTH_SCRIPT" "$REBUILD_SCRIPT"; do
    if bash -n "$script" 2>/dev/null; then
        ok "Syntax OK: $(basename $script)"
    else
        fail "Syntax error: $(basename $script)"
    fi
done

step "Phase 2 – Verifying script structure"
check_content "$MAIN_SCRIPT" "#!/bin/bash" "Main script has shebang"
check_content "$MAIN_SCRIPT" "set -e" "Main script uses set -e"
check_content "$APPLY_SCRIPT" "#!/bin/bash" "Apply script has shebang"

step "Phase 3 – Verifying graphical environment checks"
check_content "$APPLY_SCRIPT" "cage" "Checks cage"
check_content "$APPLY_SCRIPT" "regreet" "Checks regreet"
check_content "$APPLY_SCRIPT" "greetd" "Configures greetd"
check_content "$APPLY_SCRIPT" "greetd/config.toml" "References greetd config"
check_content "$APPLY_SCRIPT" "regreet.toml" "References regreet config"
check_content "$APPLY_SCRIPT" "sway" "References sway"
check_content "$APPLY_SCRIPT" "hyprland" "References hyprland"
check_content "$APPLY_SCRIPT" "hyprland-session" "References hyprland-session"
check_content "$APPLY_SCRIPT" "sway.desktop" "References sway.desktop"
check_content "$APPLY_SCRIPT" "hyprland.desktop" "References hyprland.desktop"
check_content "$APPLY_SCRIPT" "getty@tty2" "Enables getty@tty2 fallback"
check_content "$APPLY_SCRIPT" "GRAPHICAL_OK" "Has health check logic"

step "Phase 4 – Verifying offline operation"
for script in "$MAIN_SCRIPT" "$APPLY_SCRIPT"; do
    # Verify no online update calls
    if grep -qF "pacman -Syu" "$script" 2>/dev/null; then
        fail "Found online update in $(basename $script)"
    else
        ok "No online update in $(basename $script)"
    fi
done

step "Phase 5 – Verifying Plymouth setup"
check_content "$PLYMOUTH_SCRIPT" "plymouth" "Plymouth script configures plymouth"
check_content "$PLYMOUTH_SCRIPT" "mados.plymouth" "Creates mados theme"

step "Test Summary"
if [[ "$ERRORS" -gt 0 ]]; then
    echo -e "    ${RED}RESULT: $ERRORS ERRORS, $WARNINGS warnings${NC}"
    exit 1
else
    echo -e "    ${GREEN}RESULT: ALL TESTS PASSED ($WARNINGS warnings)${NC}"
    exit 0
fi
