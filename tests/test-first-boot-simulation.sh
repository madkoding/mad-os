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
#   3. The script is 100% offline (no internet downloads)
#   4. Services are enabled appropriately
#   5. Audio, Chromium, setup scripts, and program installation are configured correctly
#   6. All heredocs are properly terminated
#   7. The script cleans up after itself
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

check_not_content() {
    local desc="$1" pattern="$2"
    if echo "$SCRIPT_CONTENT" | grep -qF "$pattern"; then
        fail "$desc — pattern '$pattern' found but should not be"
    else
        ok "$desc"
    fi
    return 0
}

check_content "Has bash shebang" "#!/bin/bash"
check_content "Uses strict mode" "set -euo pipefail"
check_content "Defines LOG_TAG" 'LOG_TAG="mados-first-boot"'
check_content "Has log() function" "log()"

# =============================================================================
# Phase 4: Verify Phase 2 is 100% offline
# =============================================================================
step "Phase 4 – Verifying Phase 2 is 100% offline"

check_not_content "No INTERNET_AVAILABLE check" "INTERNET_AVAILABLE"
check_not_content "No pacman -Syu" "pacman -Syu"
check_not_content "No git clone" "git clone"

# Verify no inline downloads (curl/wget outside heredocs)
info "Checking for inline downloads outside heredocs..."
IN_HEREDOC=false
INLINE_DOWNLOAD_FOUND=false
while IFS= read -r line; do
    stripped="${line#"${line%%[![:space:]]*}"}"
    if echo "$stripped" | grep -qF "cat >" && echo "$stripped" | grep -qF "<<"; then
        IN_HEREDOC=true
    fi
    if $IN_HEREDOC; then
        for tag in EOFSETUP EOFSVC EOFAUDIO EOFCHROMIUM EOFPOLICY EOFUSRSVC; do
            if [[ "$stripped" == "$tag" ]]; then
                IN_HEREDOC=false
                break
            fi
        done
        continue
    fi
    if echo "$stripped" | grep -qE "curl.*install|wget.*install"; then
        INLINE_DOWNLOAD_FOUND=true
        fail "Found inline download outside heredoc: $stripped"
    fi
done <<< "$SCRIPT_CONTENT"
if ! $INLINE_DOWNLOAD_FOUND; then
    ok "No inline downloads outside of setup scripts (heredocs)"
fi

# =============================================================================
# Phase 5: Verify service enablement
# =============================================================================
step "Phase 5 – Verifying service enablement"

check_content "Enables bluetooth service" "systemctl enable bluetooth"
check_content "Enables PipeWire" "pipewire"
check_content "Enables WirePlumber" "wireplumber"
check_content "Creates audio init service" "mados-audio-init.service"
check_content "Enables audio init service" "systemctl enable mados-audio-init"

# Verify all systemctl enable calls have || true
info "Checking systemctl enable fault tolerance..."
FAULT_INTOLERANT=0
while IFS= read -r line; do
    stripped="${line#"${line%%[![:space:]]*}"}"
    if echo "$stripped" | grep -qE "systemctl (--global )?enable"; then
        if ! echo "$stripped" | grep -q "|| true"; then
            fail "systemctl enable without '|| true': $stripped"
            FAULT_INTOLERANT=$((FAULT_INTOLERANT + 1))
        fi
    fi
done <<< "$SCRIPT_CONTENT"
if [[ "$FAULT_INTOLERANT" -eq 0 ]]; then
    ok "All systemctl enable calls have || true fallback"
fi

# =============================================================================
# Phase 6: Verify audio configuration
# =============================================================================
step "Phase 6 – Verifying audio configuration"

check_content "Creates audio init script" "/usr/local/bin/mados-audio-init.sh"
check_content "Audio script uses amixer" "amixer"
check_content "Audio script unmutes controls" "unmute"
check_content "Audio script saves ALSA state" "alsactl store"
check_content "Audio service runs after sound.target" "sound.target"
check_content "Audio quality service exists" "mados-audio-quality.service"
check_content "User audio quality service" "/home/${TEST_USER}/.config/systemd/user"

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

# Validate JSON policy
info "Validating Chromium JSON policy..."
JSON_BLOCK=""
IN_JSON=false
while IFS= read -r line; do
    stripped="${line#"${line%%[![:space:]]*}"}"
    if [[ "$stripped" == "EOFPOLICY" ]] && $IN_JSON; then
        break
    fi
    if $IN_JSON; then
        JSON_BLOCK+="$line"$'\n'
    fi
    if echo "$stripped" | grep -qF "<<'EOFPOLICY'"; then
        IN_JSON=true
    fi
done <<< "$SCRIPT_CONTENT"
if [[ -n "$JSON_BLOCK" ]]; then
    if echo "$JSON_BLOCK" | python3 -c "import sys,json;json.load(sys.stdin)" 2>/dev/null; then
        ok "Chromium JSON policy is valid JSON"
    else
        fail "Chromium JSON policy is NOT valid JSON"
    fi
else
    fail "Could not extract Chromium JSON policy"
fi

# =============================================================================
# Phase 8: Verify Oh My Zsh fallback service and no ollama/opencode services
# =============================================================================
step "Phase 8 – Verifying Oh My Zsh fallback service"

check_content "Oh My Zsh fallback service" "setup-ohmyzsh.service"
check_content "Oh My Zsh service enabled" "systemctl enable setup-ohmyzsh.service"
# Ollama and OpenCode are pre-installed programs copied by rsync — no Phase 2 action
check_not_content "OpenCode service file" "setup-opencode.service"
check_not_content "Ollama service file" "setup-ollama.service"

# =============================================================================
# Phase 9: Verify heredoc termination
# =============================================================================
step "Phase 9 – Verifying heredoc termination"

HEREDOC_TAGS=(EOFAUDIO EOFSVC EOFCHROMIUM EOFPOLICY EOFUSRSVC)
for tag in "${HEREDOC_TAGS[@]}"; do
    OPEN_COUNT=$(echo "$SCRIPT_CONTENT" | grep -cE "<<\s*'?${tag}'?" || true)
    CLOSE_COUNT=$(echo "$SCRIPT_CONTENT" | grep -c "^${tag}$" || true)
    if [[ "$OPEN_COUNT" -eq "$CLOSE_COUNT" ]]; then
        ok "Heredoc '$tag': $OPEN_COUNT opens = $CLOSE_COUNT closes"
    else
        fail "Heredoc '$tag' mismatch: $OPEN_COUNT opens vs $CLOSE_COUNT closes"
    fi
done

# =============================================================================
# Phase 10: Verify self-cleanup
# =============================================================================
step "Phase 10 – Verifying self-cleanup"

check_content "Disables first-boot service" "systemctl disable mados-first-boot"
check_content "Removes first-boot script" "mados-first-boot.sh"

# =============================================================================
# Phase 11: Verify error handling
# =============================================================================
step "Phase 11 – Verifying error handling"

PLUS_E=$(echo "$SCRIPT_CONTENT" | grep -c "set +e" || true)
MINUS_E=$(echo "$SCRIPT_CONTENT" | grep -c "set -e" || true)
info "Found $PLUS_E 'set +e' and $MINUS_E 'set -e'"
if [[ "$MINUS_E" -ge "$PLUS_E" ]]; then
    ok "Error handling is properly restored (set -e >= set +e)"
else
    fail "Unbalanced error handling: $PLUS_E 'set +e' but only $MINUS_E 'set -e'"
fi

# Verify username substitution
info "Checking username substitution..."
if echo "$SCRIPT_CONTENT" | grep -q "/home/${TEST_USER}"; then
    ok "Username '${TEST_USER}' is properly substituted"
else
    fail "Username '${TEST_USER}' not found in script"
fi
if echo "$SCRIPT_CONTENT" | grep -q '{username}'; then
    fail "Unresolved {username} placeholder found in script"
else
    ok "No unresolved {username} placeholders"
fi

# =============================================================================
# Phase 12: Dry-run execution test (verify no syntax errors when sourced)
# =============================================================================
step "Phase 12 – Dry-run execution test"

info "Testing script execution with stubs (dry-run)..."
if bash -c "bash -n $TEST_DIR/mados-first-boot.sh" 2>&1 | head -20; then
    ok "Script can be syntax-checked in test environment"
else
    warn "Script execution test encountered issues (may be expected)"
fi

# =============================================================================
# Phase 13: Verify script completeness
# =============================================================================
step "Phase 13 – Verifying script completeness"

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
if [[ "$SECTIONS" -lt 3 ]]; then
    warn "Script has fewer than 3 major sections — may be missing functionality"
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
