#!/bin/bash
# =============================================================================
# madOS Installer – Config Script Generation & Validation
# =============================================================================
# Generates the chroot configuration script using the real Python installer
# code and validates its bash syntax.  Does NOT need a virtual disk, pacstrap,
# or chroot – only Python.
#
# Split out from the monolithic test-installation.sh so it can run as a
# fast, independent CI job.
# =============================================================================
set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_DIR="/build"
INSTALLER_LIB="${REPO_DIR}/airootfs/usr/local/lib"
TESTS_DIR="${REPO_DIR}/tests"

# ── Test parameters ──────────────────────────────────────────────────────────
TEST_USER="testuser"
TEST_PASS="testpass123"
TEST_HOSTNAME="mados-test"
TEST_TIMEZONE="America/New_York"
TEST_LOCALE="en_US.UTF-8"

# ── Output helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ERRORS=0; WARNINGS=0

step()    { echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${GREEN}==> $1${NC}"; }
info()    { echo -e "    ${YELLOW}$1${NC}"; }
ok()      { echo -e "    ${GREEN}✓ $1${NC}"; }
fail()    { echo -e "    ${RED}✗ $1${NC}"; ERRORS=$((ERRORS + 1)); }
warn()    { echo -e "    ${YELLOW}⚠ $1${NC}"; WARNINGS=$((WARNINGS + 1)); }

# =============================================================================
# Phase 0: Environment setup
# =============================================================================
step "Phase 0 – Setting up Arch Linux environment"

echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf

pacman-key --init
pacman -Syu --noconfirm python

ok "Environment ready"

# =============================================================================
# Phase 1: Config-script generation & bash syntax validation
# =============================================================================
step "Phase 1 – Generating configuration script via real installer code"

CONFIG_SCRIPT_PATH="/tmp/configure-test.sh"

python3 "${TESTS_DIR}/generate-config.py" \
    "${INSTALLER_LIB}" \
    --disk "/dev/loop0" \
    --username "$TEST_USER" \
    --password "$TEST_PASS" \
    --hostname "$TEST_HOSTNAME" \
    --timezone "$TEST_TIMEZONE" \
    --locale "$TEST_LOCALE" \
    > "$CONFIG_SCRIPT_PATH"

if [ -s "$CONFIG_SCRIPT_PATH" ]; then
    ok "Config script generated ($(wc -l < "$CONFIG_SCRIPT_PATH") lines)"
else
    fail "Config script is empty"
fi

info "Validating bash syntax..."
if bash -n "$CONFIG_SCRIPT_PATH" 2>/tmp/bash_syntax_err; then
    ok "Config script has valid bash syntax"
else
    fail "Config script has bash syntax errors:"
    cat /tmp/bash_syntax_err
fi

# =============================================================================
# Summary
# =============================================================================
step "Results"
echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ ALL TESTS PASSED  (warnings: ${WARNINGS})${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════${NC}"
    echo -e "${RED}  ✗ ${ERRORS} TEST(S) FAILED  (warnings: ${WARNINGS})${NC}"
    echo -e "${RED}═══════════════════════════════════════════${NC}"
    exit 1
fi
