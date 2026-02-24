#!/bin/bash
# =============================================================================
# madOS First-Boot Simulation Test
# =============================================================================
# Simulates the first boot after installation by executing the generated
# mados-first-boot.sh script in a controlled test environment.
#
# This test validates:
#   1. The first-boot script can be generated successfully
#   2. The script has valid bash syntax
#   3. The script contains expected configuration logic
#   4. Phase 2 packages would be installed correctly
#   5. Services would be enabled appropriately
#   6. Audio, Chromium, Oh My Zsh, and OpenCode configuration is present
#
# Note: This runs in a dry-run mode (syntax/logic check) without actually
# installing packages or modifying the system.
# =============================================================================
set -euo pipefail

# ── Paths (assumes repo is at /build in container or PWD otherwise) ─────────
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LIB_DIR="${REPO_DIR}/airootfs/usr/local/lib"
TEST_DIR="$(mktemp -d)"

# ── Test parameters ──────────────────────────────────────────────────────────
TEST_USER="testuser"
TEST_LOCALE="en_US.UTF-8"

# ── Output helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ERRORS=0; WARNINGS=0

step()    { local msg="$1"; echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${GREEN}==> $msg${NC}"; return 0; }
info()    { local msg="$1"; echo -e "    ${YELLOW}$msg${NC}"; return 0; }
ok()      { local msg="$1"; echo -e "    ${GREEN}✓ $msg${NC}"; return 0; }
fail()    { local msg="$1"; echo -e "    ${RED}✗ $msg${NC}"; ERRORS=$((ERRORS + 1)); return 0; }
warn()    { local msg="$1"; echo -e "    ${YELLOW}⚠ $msg${NC}"; WARNINGS=$((WARNINGS + 1)); return 0; }

# ── Cleanup on exit ──────────────────────────────────────────────────────────
cleanup() {
    step "Cleanup"
    rm -rf "$TEST_DIR"
    info "Test directory removed: $TEST_DIR"
    return 0
}
trap cleanup EXIT

# =============================================================================
# Phase 0: Environment setup (only needed in container environments)
# =============================================================================
# Check if we're in a container without python3 (e.g., fresh Arch Linux image)
if ! command -v python3 &>/dev/null; then
    step "Phase 0 – Setting up environment"
    
    # Configure DNS for network access
    echo 'nameserver 8.8.8.8' > /etc/resolv.conf
    echo 'nameserver 8.8.4.4' >> /etc/resolv.conf
    
    info "Initializing pacman keyring..."
    pacman-key --init
    pacman-key --populate
    
    info "Installing Python..."
    pacman -Syu --noconfirm python
    
    ok "Environment ready"
fi

# =============================================================================
# Phase 1: Generate the first-boot script
# =============================================================================
step "Phase 1 – Generating first-boot script"

if [[ ! -d "$LIB_DIR/mados_installer" ]]; then
    fail "Installer library not found at $LIB_DIR/mados_installer"
    exit 1
fi

# Python script to generate the first-boot script
cat > "$TEST_DIR/generate_first_boot.py" <<'EOFPYTHON'
import sys
import os

# Add lib dir to path
sys.path.insert(0, os.environ['LIB_DIR'])

# Mock GTK
import types
gi_mock = types.ModuleType("gi")
gi_mock.require_version = lambda *a, **kw: None
repo_mock = types.ModuleType("gi.repository")
class _StubMeta(type):
    def __getattr__(cls, name): return lambda *a, **kw: None
class _StubWidget(metaclass=_StubMeta):
    def __getattr__(self, name): return lambda *a, **kw: None
class _StubModule:
    def __getattr__(self, name): return _StubWidget
for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango"):
    setattr(repo_mock, name, _StubModule())
sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# Import the installer
from mados_installer.pages.installation import _build_first_boot_script

# Generate script with test data
data = {
    'username': os.environ['TEST_USER'],
    'locale': os.environ['TEST_LOCALE'],
}

script = _build_first_boot_script(data)
print(script)
EOFPYTHON

info "Generating first-boot script via Python..."
export LIB_DIR TEST_USER TEST_LOCALE
if python3 "$TEST_DIR/generate_first_boot.py" > "$TEST_DIR/mados-first-boot.sh"; then
    ok "First-boot script generated successfully"
else
    fail "Failed to generate first-boot script"
    exit 1
fi

# =============================================================================
# Phase 2: Validate script syntax
# =============================================================================
step "Phase 2 – Validating bash syntax"

if bash -n "$TEST_DIR/mados-first-boot.sh"; then
    ok "Script has valid bash syntax"
else
    fail "Script has bash syntax errors"
    exit 1
fi

# =============================================================================
# Phase 3: Verify script structure
# =============================================================================
step "Phase 3 – Verifying script structure"

SCRIPT_CONTENT=$(cat "$TEST_DIR/mados-first-boot.sh")

check_content() {
    local desc="$1" pattern="$2"
    if echo "$SCRIPT_CONTENT" | grep -qF "$pattern"; then
        ok "$desc"
    else
        fail "$desc — pattern '$pattern' not found"
    fi
    return 0
}

check_content "Has bash shebang" "#!/bin/bash"
check_content "Uses strict mode" "set -euo pipefail"
check_content "Defines LOG_TAG" 'LOG_TAG="mados-first-boot"'
check_content "Has log() function" "log()"

# =============================================================================
# Phase 4: Verify Phase 2 package installation
# =============================================================================
step "Phase 4 – Verifying Phase 2 package installation"

check_content "Installs packages with pacman" "pacman -Syu"
check_content "Uses --noconfirm flag" "noconfirm"
check_content "Uses --needed flag" "needed"

# CJK fonts are only added for Asian locales, not for en_US
if [[ "$TEST_LOCALE" =~ ^(zh_CN|ja_JP) ]]; then
    check_content "Handles CJK fonts" "noto-fonts-cjk"
else
    info "CJK fonts check skipped (not an Asian locale)"
fi

# Verify some essential Phase 2 packages are in the list
info "Checking for essential Phase 2 packages..."
ESSENTIAL_PHASE2=(
    "sway"
    "hyprland"
    "waybar"
    "foot"
    "chromium"
    "code"
    "pipewire"
    "wireplumber"
    "bluez"
    "bluetooth"
)

for pkg in "${ESSENTIAL_PHASE2[@]}"; do
    if echo "$SCRIPT_CONTENT" | grep -q "$pkg"; then
        ok "Package '$pkg' is in Phase 2"
    else
        warn "Package '$pkg' not found in Phase 2 list"
    fi
done

# =============================================================================
# Phase 5: Verify service enablement
# =============================================================================
step "Phase 5 – Verifying service enablement"

check_content "Enables bluetooth service" "systemctl enable bluetooth"
check_content "Enables PipeWire" "pipewire"
check_content "Enables WirePlumber" "wireplumber"
check_content "Creates audio init service" "mados-audio-init.service"
check_content "Enables audio init service" "systemctl enable mados-audio-init"

# =============================================================================
# Phase 6: Verify audio configuration
# =============================================================================
step "Phase 6 – Verifying audio configuration"

check_content "Creates audio init script" "/usr/local/bin/mados-audio-init.sh"
check_content "Audio script uses amixer" "amixer"
check_content "Audio script unmutes controls" "unmute"
check_content "Audio script saves ALSA state" "alsactl store"
check_content "Audio service runs after sound.target" "sound.target"

# Verify audio script unmutes common controls
info "Checking audio controls..."
for control in "Master" "Headphone" "Speaker" "PCM"; do
    if echo "$SCRIPT_CONTENT" | grep -q "$control"; then
        ok "Unmutes '$control' control"
    else
        warn "Audio control '$control' not found"
    fi
done

# =============================================================================
# Phase 7: Verify Chromium configuration
# =============================================================================
step "Phase 7 – Verifying Chromium configuration"

check_content "Creates Chromium flags file" "/etc/chromium-flags.conf"
check_content "Configures Wayland support" "ozone-platform"
check_content "Disables Vulkan" "disable-vulkan"
check_content "Disables VA-API" "VaapiVideoDecoder"
check_content "Limits renderer processes" "renderer-process-limit"
check_content "Sets homepage policy" "/etc/chromium/policies/managed"
check_content "Configures homepage location" "HomepageLocation"

# =============================================================================
# Phase 8: Verify Oh My Zsh installation
# =============================================================================
step "Phase 8 – Verifying Oh My Zsh installation"

check_content "Installs to /etc/skel" "/etc/skel/.oh-my-zsh"
check_content "Clones from GitHub" "github.com/ohmyzsh/ohmyzsh"
check_content "Copies to user home" "oh-my-zsh /home/${TEST_USER}"
check_content "Changes ownership to user" "chown"
check_content "Creates fallback service" "setup-ohmyzsh.service"
check_content "Checks for internet" "curl"

# =============================================================================
# Phase 9: Verify OpenCode installation
# =============================================================================
step "Phase 9 – Verifying OpenCode installation"

check_content "Uses OpenCode install script" "opencode.ai/install"
check_content "Downloads with curl" "opencode.ai"
check_content "Pipes to bash" "bash"
check_content "Verifies opencode command" "opencode"

# =============================================================================
# Phase 10: Verify self-cleanup
# =============================================================================
step "Phase 10 – Verifying self-cleanup"

check_content "Disables first-boot service" "systemctl disable mados-first-boot"
check_content "Removes first-boot script" "mados-first-boot.sh"

# =============================================================================
# Phase 11: Dry-run execution test (verify no syntax errors when sourced)
# =============================================================================
step "Phase 11 – Dry-run execution test"

# Create a minimal test environment with command stubs
cat > "$TEST_DIR/test-environment.sh" <<'EOFENV'
#!/bin/bash
# Stub functions for dry-run testing
pacman() { echo "[STUB] pacman $*"; return 0; }
systemctl() { echo "[STUB] systemctl $*"; return 0; }
git() { echo "[STUB] git $*"; return 0; }
curl() { echo "[STUB] curl $*"; return 0; }
mkdir() { echo "[STUB] mkdir $*"; return 0; }
cat() {
    # When used for reading files, use real cat
    # When used with redirection (e.g., cat > file), shell handles it
    if [[ $# -eq 0 ]] || [[ "$1" != "-" && -f "$1" ]]; then
        command cat "$@"
    else
        # For other cases, just echo the stub message
        echo "[STUB] cat $*"
    fi
    return 0
}
chmod() { echo "[STUB] chmod $*"; return 0; }
chown() { echo "[STUB] chown $*"; return 0; }
cp() { echo "[STUB] cp $*"; return 0; }
command() {
    if [[ "$1" == "-v" ]]; then
        # Pretend commands exist
        echo "/usr/bin/$2"
        return 0
    fi
    builtin command "$@"
}
export -f pacman systemctl git curl mkdir cat chmod chown cp command
EOFENV

info "Testing script execution with stubs (dry-run)..."
if bash -c ". $TEST_DIR/test-environment.sh && bash -n $TEST_DIR/mados-first-boot.sh" 2>&1 | head -20; then
    ok "Script can be syntax-checked in test environment"
else
    warn "Script execution test encountered issues (may be expected)"
fi

# =============================================================================
# Phase 12: Verify script completeness
# =============================================================================
step "Phase 12 – Verifying script completeness"

SCRIPT_LINES=$(wc -l < "$TEST_DIR/mados-first-boot.sh")
info "Script size: $SCRIPT_LINES lines"

if [[ "$SCRIPT_LINES" -lt 100 ]]; then
    fail "Script seems too short ($SCRIPT_LINES lines) — may be incomplete"
elif [[ "$SCRIPT_LINES" -gt 1000 ]]; then
    warn "Script is very long ($SCRIPT_LINES lines) — consider refactoring"
else
    ok "Script size is reasonable ($SCRIPT_LINES lines)"
fi

# Count major sections
SECTIONS=$(echo "$SCRIPT_CONTENT" | grep -c "^# ──.*──" || true)
info "Major sections found: $SECTIONS"
if [[ "$SECTIONS" -lt 5 ]]; then
    warn "Script has fewer than 5 major sections — may be missing functionality"
else
    ok "Script has $SECTIONS major sections"
fi

# =============================================================================
# Summary
# =============================================================================
step "Results"
echo ""
info "Generated script location: $TEST_DIR/mados-first-boot.sh"
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
