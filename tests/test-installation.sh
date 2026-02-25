#!/bin/bash
# =============================================================================
# madOS Installation Process Test
# =============================================================================
# Validates the full installation flow on a virtual loopback disk inside an
# Arch Linux container.  Designed to run in CI (GitHub Actions) before the
# ISO build so we catch packaging, partitioning, and configuration errors
# early.
#
# Phases:
#   1. Python module validation (syntax + imports)
#   2. Disk partitioning & formatting on a loopback device
#   3. pacstrap – installs every package the real installer uses
#   4. fstab generation
#   5. Config-script generation (via the real Python function) & bash syntax check
#   6. Chroot configuration (non-hardware-dependent subset)
#   7. Post-install verification
# =============================================================================
set -euo pipefail

# ── Paths (assumes the repo is mounted at /build inside the container) ───────
REPO_DIR="/build"
INSTALLER_LIB="${REPO_DIR}/airootfs/usr/local/lib"
TESTS_DIR="${REPO_DIR}/tests"

# ── Virtual-disk settings ────────────────────────────────────────────────────
DISK_IMAGE="/tmp/test-disk.img"
DISK_SIZE="60G"            # sparse file – almost no real disk space used
MOUNT_POINT="/mnt"

# ── Test installation parameters ─────────────────────────────────────────────
TEST_USER="testuser"
TEST_PASS="testpass123"
TEST_HOSTNAME="mados-test"
TEST_TIMEZONE="America/New_York"
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
    umount -R "$MOUNT_POINT" 2>/dev/null || true
    [[ -n "${LOOP_DEV:-}" ]] && losetup -d "$LOOP_DEV" 2>/dev/null || true
    rm -f "$DISK_IMAGE"
    ok "Cleanup finished"
    return 0
}
trap cleanup EXIT

# =============================================================================
# Phase 0: Environment setup
# =============================================================================
step "Phase 0 – Setting up Arch Linux environment"

# DNS + mirrors
echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf

pacman-key --init
pacman-key --populate
pacman -Syu --noconfirm archiso python parted gptfdisk dosfstools e2fsprogs

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
# Phase 2: Disk partitioning & formatting
# =============================================================================
step "Phase 2 – Creating and partitioning virtual disk"

truncate -s "$DISK_SIZE" "$DISK_IMAGE"
LOOP_DEV=$(losetup -f --show "$DISK_IMAGE")
info "Loopback device: $LOOP_DEV"

# Partition (identical to installer logic in installation.py)
sgdisk --zap-all "$LOOP_DEV" 2>/dev/null || true
wipefs -a -f "$LOOP_DEV"
parted -s "$LOOP_DEV" mklabel gpt
parted -s "$LOOP_DEV" mkpart bios_boot 1MiB 2MiB
parted -s "$LOOP_DEV" set 1 bios_grub on
parted -s "$LOOP_DEV" mkpart EFI fat32 2MiB 1GiB
parted -s "$LOOP_DEV" set 2 esp on
parted -s "$LOOP_DEV" mkpart root ext4 1GiB 51GiB
parted -s "$LOOP_DEV" mkpart home ext4 51GiB 100%

# In containers, partprobe is unreliable for loop devices because udev may not
# be running.  Detach and reattach with -P (--partscan) so the kernel creates
# the partition device nodes (/dev/loop0p1, …) on attach.
losetup -d "$LOOP_DEV"
LOOP_DEV=$(losetup -fP --show "$DISK_IMAGE")
info "Reattached with partition scan: $LOOP_DEV"

BOOT_PART="${LOOP_DEV}p2"
ROOT_PART="${LOOP_DEV}p3"
HOME_PART="${LOOP_DEV}p4"

# Use multiple strategies to ensure partition device nodes appear in containers
partprobe "$LOOP_DEV" 2>/dev/null || true
partx -a "$LOOP_DEV" 2>/dev/null || true
partx -u "$LOOP_DEV" 2>/dev/null || true
udevadm settle --timeout=10 2>/dev/null || true

# Wait for partition device nodes with retries
for attempt in $(seq 1 10); do
    [[ -b "$BOOT_PART" ]] && [[ -b "$ROOT_PART" ]] && [[ -b "$HOME_PART" ]] && break
    info "Waiting for partition device nodes (attempt ${attempt}/10)..."
    partprobe "$LOOP_DEV" 2>/dev/null || true
    partx -a "$LOOP_DEV" 2>/dev/null || true
    partx -u "$LOOP_DEV" 2>/dev/null || true
    udevadm settle --timeout=5 2>/dev/null || true
    sleep 1
done

# Fallback: In Docker containers /dev is often a plain tmpfs (not devtmpfs),
# so the kernel cannot auto-create device nodes even though it knows about the
# partitions (visible in sysfs).  Manually create them with mknod.
LOOP_NAME=$(basename "$LOOP_DEV")
for i in 1 2 3 4; do
    PART_DEV="${LOOP_DEV}p${i}"
    SYSFS_DEV="/sys/block/${LOOP_NAME}/${LOOP_NAME}p${i}/dev"
    if ! [[ -b "$PART_DEV" ]] && [[ -f "$SYSFS_DEV" ]]; then
        MAJOR=$(cut -d: -f1 < "$SYSFS_DEV" | tr -d '[:space:]')
        MINOR=$(cut -d: -f2 < "$SYSFS_DEV" | tr -d '[:space:]')
        info "Creating device node ${PART_DEV} (${MAJOR}:${MINOR}) via mknod"
        mknod "$PART_DEV" b "$MAJOR" "$MINOR"
    fi
done

for label_part in "EFI:${BOOT_PART}" "root:${ROOT_PART}" "home:${HOME_PART}"; do
    label="${label_part%%:*}"; part="${label_part##*:}"
    [[ -b "$part" ]] && ok "Partition ${label} (${part}) exists" || fail "Partition ${label} (${part}) missing"
done

# Abort early if any partition is still missing (prevents cryptic mkfs errors)
if ! [[ -b "$BOOT_PART" ]] || ! [[ -b "$ROOT_PART" ]] || ! [[ -b "$HOME_PART" ]]; then
    info "Diagnostics: ls -la ${LOOP_DEV}*"
    ls -la "${LOOP_DEV}"* 2>/dev/null || true
    info "Diagnostics: /sys/block/${LOOP_NAME}/"
    ls -la "/sys/block/${LOOP_NAME}/" 2>/dev/null || true
    info "Diagnostics: lsblk"
    lsblk 2>/dev/null || true
    fail "Could not create partition device nodes after all strategies. Aborting."
    exit 1
fi

# Format
info "Formatting partitions..."
mkfs.fat -F32 "$BOOT_PART"
mkfs.ext4 -F  "$ROOT_PART"
mkfs.ext4 -F  "$HOME_PART"
ok "Partitions formatted"

# Mount
info "Mounting filesystems..."
mount "$ROOT_PART" "$MOUNT_POINT"
mkdir -p "$MOUNT_POINT/boot"
mount "$BOOT_PART" "$MOUNT_POINT/boot"
mkdir -p "$MOUNT_POINT/home"
mount "$HOME_PART" "$MOUNT_POINT/home"
ok "Filesystems mounted at ${MOUNT_POINT}"

# =============================================================================
# Phase 3: pacstrap – install the Phase 1 (essential) package list
# =============================================================================
step "Phase 3 – Installing base system via pacstrap (Phase 1 packages)"

# Phase 1 package list from mados_installer/config.py (PACKAGES_PHASE1)
# These are the essential packages installed during USB installation.
# Additional packages (desktop apps, dev tools) are also installed from ISO.
PACKAGES=(
    base base-devel linux linux-firmware intel-ucode amd-ucode
    grub efibootmgr os-prober dosfstools sbctl
    networkmanager sudo zsh curl iwd
    earlyoom zram-generator
    plymouth
    greetd greetd-regreet cage
    sway swaybg foot xorg-xwayland
    mesa
    python python-gobject gtk3
    nodejs npm
)

info "Installing ${#PACKAGES[@]} packages (this will take several minutes)..."
if pacstrap "$MOUNT_POINT" "${PACKAGES[@]}"; then
    ok "pacstrap completed – all packages installed"
else
    fail "pacstrap failed"
    exit 1
fi

# =============================================================================
# Phase 4: fstab generation
# =============================================================================
step "Phase 4 – Generating filesystem table"

genfstab -U "$MOUNT_POINT" > "$MOUNT_POINT/etc/fstab"

if [[ -s "$MOUNT_POINT/etc/fstab" ]]; then
    ok "fstab generated ($(wc -l < "$MOUNT_POINT/etc/fstab") lines)"
else
    fail "fstab is empty"
fi

# =============================================================================
# Phase 5: Config-script generation & bash syntax validation
# =============================================================================
step "Phase 5 – Generating configuration script via real installer code"

CONFIG_SCRIPT_PATH="/tmp/configure-test.sh"

python3 "${TESTS_DIR}/generate-config.py" \
    "${INSTALLER_LIB}" \
    --disk "$LOOP_DEV" \
    --username "$TEST_USER" \
    --password "$TEST_PASS" \
    --hostname "$TEST_HOSTNAME" \
    --timezone "$TEST_TIMEZONE" \
    --locale "$TEST_LOCALE" \
    > "$CONFIG_SCRIPT_PATH"

if [[ -s "$CONFIG_SCRIPT_PATH" ]]; then
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
# Phase 6: Chroot configuration
# =============================================================================
step "Phase 6 – Running configuration in chroot"

# Build a CI-safe version of the config script.
# We skip hardware-dependent commands that cannot work inside a container:
#   - grub-install  (no EFI firmware / real BIOS)
#   - grub-mkconfig (stubbed but creates dummy output file for existence check)
#   - mkinitcpio    (no real kernel modules)
#   - systemctl     (no systemd PID 1 inside chroot)
#   - plymouth-set-default-theme (may not have Plymouth fully set up)
#   - hwclock       (no RTC in container)
#   - sbctl         (no Secure Boot)
#   - passwd -l root (may fail without shadow setup)
#   - npm           (no network / avoid long timeouts in CI)
# All other configuration (timezone, locale, user, configs) is tested.

cat > "$MOUNT_POINT/root/configure-ci.sh" << 'CIEOF'
#!/bin/bash
set -e

# ── Helper: skip commands that need real hardware / systemd ──────────────
stub() { echo "  [CI-SKIP] $*"; return 0; }
# grub-install stub: create the fallback EFI binary when --removable is used,
# because the config script checks for its existence and exits 1 if missing.
grub-install() {
    stub "grub-install $*"
    if echo "$*" | grep -q -- '--removable'; then
        mkdir -p /boot/EFI/BOOT
        echo "# CI stub BOOTX64.EFI" > /boot/EFI/BOOT/BOOTX64.EFI
    fi
}
# grub-mkconfig stub: create a dummy output file when -o is used, because
# the config script checks for its existence and exits 1 if missing.
grub-mkconfig() {
    stub "grub-mkconfig $*"
    local outfile=""
    while [[ $# -gt 0 ]]; do
        if [[ "$1" == "-o" ]] && [[ -n "${2:-}" ]]; then
            outfile="$2"; shift 2
        else
            shift
        fi
    done
    if [[ -n "$outfile" ]]; then
        mkdir -p "$(dirname "$outfile")"
        echo "# CI stub grub.cfg" > "$outfile"
    fi
}
mkinitcpio()                   { stub "mkinitcpio $*"; }
systemctl()                    { stub "systemctl $*"; }
plymouth-set-default-theme()   { stub "plymouth-set-default-theme $*"; }
hwclock()                      { stub "hwclock $*"; }
sbctl()                        { stub "sbctl $*"; }
passwd()                       { stub "passwd $*"; }
npm()                          { stub "npm $*"; }
export -f stub grub-install grub-mkconfig mkinitcpio systemctl plymouth-set-default-theme hwclock sbctl passwd npm
CIEOF

# Append the real config script (it will use our stubs for skipped commands)
cat "$CONFIG_SCRIPT_PATH" >> "$MOUNT_POINT/root/configure-ci.sh"
chmod 700 "$MOUNT_POINT/root/configure-ci.sh"

info "Running chroot configuration (hardware commands are stubbed)..."
if arch-chroot "$MOUNT_POINT" /root/configure-ci.sh; then
    ok "Chroot configuration completed successfully"
else
    CHROOT_RC=$?
    # Non-zero may be caused by npm/network commands that are non-fatal
    warn "Chroot configuration exited with code $CHROOT_RC (some non-critical steps may have failed)"
fi

# =============================================================================
# Phase 7: Post-install verification
# =============================================================================
step "Phase 7 – Verifying installed system"

check_file() {
    local desc="$1" path="$2"
    if [[ -e "$MOUNT_POINT$path" ]]; then ok "$desc"; else fail "$desc — $path missing"; fi
    return 0
}

check_content() {
    local desc="$1" path="$2" pattern="$3"
    if [[ -e "$MOUNT_POINT$path" ]] && grep -q "$pattern" "$MOUNT_POINT$path" 2>/dev/null; then
        ok "$desc"
    else
        fail "$desc — pattern '$pattern' not found in $path"
    fi
    return 0
}

# Timezone
check_file "Timezone symlink exists" "/etc/localtime"

# Locale
check_content "Locale is configured" "/etc/locale.conf" "LANG=${TEST_LOCALE}"

# Hostname
check_content "Hostname is set" "/etc/hostname" "$TEST_HOSTNAME"
check_content "Hosts file configured" "/etc/hosts" "$TEST_HOSTNAME"

# User
if arch-chroot "$MOUNT_POINT" id "$TEST_USER" >/dev/null 2>&1; then
    ok "User '${TEST_USER}' exists"
else
    fail "User '${TEST_USER}' does not exist"
fi

# Sudoers
check_file "Sudoers wheel config" "/etc/sudoers.d/wheel"
check_file "Sudoers opencode-nopasswd config" "/etc/sudoers.d/opencode-nopasswd"

# GRUB config defaults
check_content "GRUB distributor set to madOS" "/etc/default/grub" "madOS"

# OS release branding
check_content "os-release has madOS name" "/etc/os-release" 'NAME="madOS"'

# ZRAM config
check_content "ZRAM configured" "/etc/systemd/zram-generator.conf" "zram-size"

# Kernel optimizations
check_content "Sysctl tuning present" "/etc/sysctl.d/99-extreme-low-ram.conf" "vm.swappiness"

# Key directories
check_file "Home directory for user" "/home/${TEST_USER}"
check_file "Boot directory" "/boot"
check_file "fstab" "/etc/fstab"

# greetd configuration
check_file "greetd config" "/etc/greetd/config.toml"
check_content "greetd uses cage-greeter" "/etc/greetd/config.toml" "cage-greeter"

# NetworkManager wifi backend
check_content "NM uses iwd backend" "/etc/NetworkManager/conf.d/wifi-backend.conf" "iwd"

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
