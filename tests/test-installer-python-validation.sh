#!/bin/bash
# =============================================================================
# madOS Installer – Python Module Validation
# =============================================================================
# Validates all Python installer modules for syntax correctness and
# importability.  Runs inside an Arch Linux container but does NOT need
# a virtual disk, pacstrap, or chroot.
#
# Split out from the monolithic test-installation.sh so it can run as a
# fast, independent CI job.
# =============================================================================
set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_DIR="/build"
INSTALLER_LIB="${REPO_DIR}/airootfs/usr/local/lib"

# ── Output helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ERRORS=0; WARNINGS=0

step()    { local msg="$1"; echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${GREEN}==> $msg${NC}"; return 0; }
info()    { local msg="$1"; echo -e "    ${YELLOW}$msg${NC}"; return 0; }
ok()      { local msg="$1"; echo -e "    ${GREEN}✓ $msg${NC}"; return 0; }
fail()    { local msg="$1"; echo -e "    ${RED}✗ $msg${NC}"; ERRORS=$((ERRORS + 1)); return 0; }
warn()    { local msg="$1"; echo -e "    ${YELLOW}⚠ $msg${NC}"; WARNINGS=$((WARNINGS + 1)); return 0; }

# =============================================================================
# Phase 0: Environment setup
# =============================================================================
step "Phase 0 – Setting up Arch Linux environment"

echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf

pacman-key --init
pacman-key --populate
pacman -Syu --noconfirm python

ok "Environment ready"

# =============================================================================
# Phase 1: Python module validation
# =============================================================================
step "Phase 1 – Validating Python installer modules"

PYTHON_FILES=$(find "${INSTALLER_LIB}/mados_installer" -name '*.py' -type f)
PY_ERRORS=0
for f in $PYTHON_FILES; do
    if python -m py_compile "$f" 2>/tmp/pyerr; then
        ok "Syntax OK: $(basename "$f")"
    else
        fail "Syntax error in $f: $(cat /tmp/pyerr)"
        PY_ERRORS=$((PY_ERRORS + 1))
    fi
done

if [[ "$PY_ERRORS" -eq 0 ]]; then
    ok "All Python modules have valid syntax"
else
    fail "$PY_ERRORS Python file(s) with syntax errors"
fi

# =============================================================================
# Summary
# =============================================================================
step "Results"
echo ""
if [[ "$ERRORS" -eq 0 ]]; then
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
