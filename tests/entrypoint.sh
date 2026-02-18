#!/bin/bash
# =============================================================================
# madOS Persistence Test Entrypoint
# =============================================================================
# Entrypoint script for Docker test container
# Runs all persistence tests in the correct order
# =============================================================================

set -euo pipefail

REPO_DIR="/build"
TESTS_DIR="${REPO_DIR}/tests"
LOG_DIR="/var/log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok() { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     madOS Persistence Test Suite - Docker Entrypoint          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check we're running as root (required for loopback mounts)
if [ "$(id -u)" -ne 0 ]; then
    fail "This container must run as root for loopback device operations"
    exit 1
fi

# Ensure kernel modules are loaded (needed for loopback)
log "Loading kernel modules..."
modprobe loop 2>/dev/null || true
modprobe ext4 2>/dev/null || true
modprobe vfat 2>/dev/null || true

# Show environment info
log "Environment information:"
echo "  Working directory: $(pwd)"
echo "  Python version: $(python --version 2>&1)"
echo "  Bash version: $(bash --version | head -1)"
echo "  parted version: $(parted --version | head -1)"
echo "  lsblk version: $(lsblk --version | head -1)"
echo ""

# Install pytest if not available
if ! command -v pytest &> /dev/null; then
    log "Installing pytest..."
    pip install --quiet pytest pytest-cov
fi

# Run bash syntax validation first
log "Running bash syntax validation..."
for script in setup-persistence.sh mados-persistence mados-welcome.sh; do
    if [ -f "${REPO_DIR}/airootfs/usr/local/bin/${script}" ]; then
        if bash -n "${REPO_DIR}/airootfs/usr/local/bin/${script}"; then
            ok "${script}: valid syntax"
        else
            fail "${script}: syntax error"
            exit 1
        fi
    fi
done

# Run Python validation tests
log "Running Python validation tests..."
cd "${REPO_DIR}"
if pytest "${TESTS_DIR}/test_persistence_scripts.py" -v --tb=short; then
    ok "Python validation tests passed"
else
    fail "Python validation tests failed"
    exit 1
fi

# Run Python integration tests
log "Running Python integration tests..."
if pytest "${TESTS_DIR}/test_persistence_validation.py" -v --tb=short; then
    ok "Python validation tests passed"
else
    fail "Python validation tests failed"
    exit 1
fi

# Run Python function coverage tests
log "Running function coverage tests..."
if pytest "${TESTS_DIR}/test_persistence_coverage.py" -v --tb=short; then
    ok "Function coverage tests passed"
else
    fail "Function coverage tests failed"
    exit 1
fi

# Run functional Docker tests (if test-liveusb-persistence.sh exists)
if [ -f "${TESTS_DIR}/test-liveusb-persistence.sh" ]; then
    log "Running functional Docker tests..."
    if bash "${TESTS_DIR}/test-liveusb-persistence.sh"; then
        ok "Functional Docker tests passed"
    else
        fail "Functional Docker tests failed"
        exit 1
    fi
else
    warn "test-liveusb-persistence.sh not found, skipping functional tests"
fi

# Run pytest with coverage
log "Running pytest with coverage..."
cd "${REPO_DIR}"
if pytest "${TESTS_DIR}" -v --cov=airootfs/usr/local/bin --cov-report=term-missing \
    --cov-report=xml:/build/coverage.xml --cov-report=html:/build/coverage_html; then
    ok "Pytest with coverage passed"
else
    fail "Pytest with coverage failed"
    exit 1
fi

# Show coverage report
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                         COVERAGE REPORT                        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
coverage report -m 2>/dev/null || echo "Coverage report not available"
echo ""

# Summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                  ALL TESTS COMPLETED SUCCESSFULLY              ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Coverage report: file:///build/coverage_html/index.html"
echo "Full XML report: /build/coverage.xml"
echo ""

exit 0
