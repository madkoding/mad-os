#!/bin/bash
# =============================================================================
# madOS Live USB Persistence Test
# =============================================================================
# Validates the overlayfs-based persistence system in a simulated live USB
# environment using a loopback disk inside a container.
#
# Phases:
#   1. Environment setup – install dependencies
#   2. Simulated USB disk – create loopback with ISO + empty partition
#   3. Simulate archiso environment – /run/archiso, lsblk labels, etc.
#   4. Run setup-persistence.sh – create persistence partition + overlays
#   5. Verify init script and service are stored inside persistence partition
#   6. Verify overlayfs mounts for /etc, /usr, /var, /opt
#   7. Verify bind mount for /home
#   8. Verify ldconfig ran
#   9. Simulate reboot – unmount everything, re-run init script, re-verify
#  10. Test second boot – run setup-persistence.sh again to verify detection
#  11. Verify systemd service file syntax
#  12. Verify mados-persistence CLI (status / help)
# =============================================================================
set -euo pipefail

REPO_DIR="/build"
LOG_FILE="/var/log/mados-persistence.log"

# ── Output helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ERRORS=0; WARNINGS=0

step()    { echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${GREEN}==> $1${NC}"; }
info()    { echo -e "    ${YELLOW}$1${NC}"; }
ok()      { echo -e "    ${GREEN}✓ $1${NC}"; }
fail()    { echo -e "    ${RED}✗ $1${NC}"; ERRORS=$((ERRORS + 1)); }
warn()    { echo -e "    ${YELLOW}⚠ $1${NC}"; WARNINGS=$((WARNINGS + 1)); }

# ── Cleanup on exit ──────────────────────────────────────────────────────────
DISK_IMAGE="/tmp/test-usb.img"
LOOP_DEV=""
PERSIST_MOUNT="/mnt/persistence"
OVERLAY_DIRS="etc usr var opt"

cleanup() {
    step "Cleanup"

    # Unmount overlays in reverse order
    umount /home 2>/dev/null || true
    for dir in $(echo $OVERLAY_DIRS | tr ' ' '\n' | tac | tr '\n' ' '); do
        umount "/$dir" 2>/dev/null || true
    done
    umount "$PERSIST_MOUNT" 2>/dev/null || true
    umount /run/archiso/bootmnt 2>/dev/null || true

    [ -n "${LOOP_DEV:-}" ] && losetup -d "$LOOP_DEV" 2>/dev/null || true
    rm -f "$DISK_IMAGE"
    rm -rf /run/archiso 2>/dev/null || true
    rm -rf /run/mados 2>/dev/null || true
    ok "Cleanup finished"
}
trap cleanup EXIT

# =============================================================================
# Phase 1: Environment setup
# =============================================================================
step "Phase 1 – Setting up test environment"

echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf

pacman-key --init
pacman -Syu --noconfirm parted e2fsprogs dosfstools util-linux

ok "Dependencies installed"

# =============================================================================
# Phase 2: Create simulated USB disk with ISO partition + free space
# =============================================================================
step "Phase 2 – Creating simulated USB disk"

# 4 GB sparse disk: 2 GB for "ISO", 200 MB EFI, rest free for persistence
truncate -s 4G "$DISK_IMAGE"
LOOP_DEV=$(losetup -f --show "$DISK_IMAGE")
info "Loopback device: $LOOP_DEV"

parted -s "$LOOP_DEV" mklabel msdos
# Partition 1: simulated ISO data (~2 GB)
parted -s "$LOOP_DEV" mkpart primary 1MiB 2048MiB
# Partition 2: simulated EFI (FAT32, 200 MB)
parted -s "$LOOP_DEV" mkpart primary fat32 2048MiB 2248MiB

# Re-attach with partition scan
losetup -d "$LOOP_DEV"
LOOP_DEV=$(losetup -fP --show "$DISK_IMAGE")
info "Reattached with partition scan: $LOOP_DEV"

partprobe "$LOOP_DEV" 2>/dev/null || true
partx -a "$LOOP_DEV" 2>/dev/null || true
udevadm settle --timeout=10 2>/dev/null || true

# Create device nodes if needed (Docker / container environments)
LOOP_NAME=$(basename "$LOOP_DEV")
for i in 1 2; do
    PART_DEV="${LOOP_DEV}p${i}"
    SYSFS_DEV="/sys/block/${LOOP_NAME}/${LOOP_NAME}p${i}/dev"
    if ! [ -b "$PART_DEV" ] && [ -f "$SYSFS_DEV" ]; then
        MAJOR=$(cut -d: -f1 < "$SYSFS_DEV" | tr -d '[:space:]')
        MINOR=$(cut -d: -f2 < "$SYSFS_DEV" | tr -d '[:space:]')
        info "Creating device node ${PART_DEV} (${MAJOR}:${MINOR})"
        mknod "$PART_DEV" b "$MAJOR" "$MINOR"
    fi
done

# Format partition 1 as ext4 with ARCHISO label (simulates ISO partition)
# This allows setup-persistence.sh to find the boot device via lsblk
mkfs.ext4 -F -L "ARCHISO" "${LOOP_DEV}p1" >/dev/null 2>&1

# Format partition 2 as FAT32 (EFI)
mkfs.fat -F32 "${LOOP_DEV}p2" >/dev/null 2>&1

# Verify partitions
[ -b "${LOOP_DEV}p1" ] && ok "Partition 1 (ISO sim) exists" || fail "Partition 1 missing"
[ -b "${LOOP_DEV}p2" ] && ok "Partition 2 (EFI) exists" || fail "Partition 2 missing"

# Show layout
info "Disk layout:"
parted -s "$LOOP_DEV" unit MB print free 2>/dev/null || true

ok "Simulated USB disk ready"

# =============================================================================
# Phase 3: Simulate archiso live environment
# =============================================================================
step "Phase 3 – Simulating archiso live environment"

mkdir -p /run/archiso/bootmnt

# Partition 1 now has ARCHISO label, which allows setup-persistence.sh's
# find_iso_device() to discover the loop device via lsblk.
# Optionally mount it to more closely simulate real environment.
mount "${LOOP_DEV}p1" /run/archiso/bootmnt 2>/dev/null || true

# Copy scripts into place
cp "${REPO_DIR}/airootfs/usr/local/bin/setup-persistence.sh" /usr/local/bin/setup-persistence.sh
chmod 755 /usr/local/bin/setup-persistence.sh

cp "${REPO_DIR}/airootfs/usr/local/bin/mados-persistence" /usr/local/bin/mados-persistence
chmod 755 /usr/local/bin/mados-persistence

ok "Scripts installed"

# =============================================================================
# Phase 4: Manually create the persistence partition (simulating what
#           setup-persistence.sh does on a real USB – we bypass the USB
#           detection logic that can't work in a container)
# =============================================================================
step "Phase 4 – Creating persistence partition"

# Create partition 3 using free space
parted -s "$LOOP_DEV" mkpart primary ext4 2248MiB 100% 2>/dev/null

partprobe "$LOOP_DEV" 2>/dev/null || true
partx -a "$LOOP_DEV" 2>/dev/null || true
partx -u "$LOOP_DEV" 2>/dev/null || true
udevadm settle --timeout=10 2>/dev/null || true

# Create device node if needed
PERSIST_PART="${LOOP_DEV}p3"
SYSFS_DEV="/sys/block/${LOOP_NAME}/${LOOP_NAME}p3/dev"
if ! [ -b "$PERSIST_PART" ] && [ -f "$SYSFS_DEV" ]; then
    MAJOR=$(cut -d: -f1 < "$SYSFS_DEV" | tr -d '[:space:]')
    MINOR=$(cut -d: -f2 < "$SYSFS_DEV" | tr -d '[:space:]')
    info "Creating device node ${PERSIST_PART} (${MAJOR}:${MINOR})"
    mknod "$PERSIST_PART" b "$MAJOR" "$MINOR"
fi

[ -b "$PERSIST_PART" ] && ok "Partition 3 (persistence) exists" || { fail "Partition 3 missing"; exit 1; }

# Format with ext4 and label "persistence"
mkfs.ext4 -F -L "persistence" "$PERSIST_PART" >/dev/null 2>&1
ok "Formatted $PERSIST_PART as ext4 with label 'persistence'"

# Verify label (use blkid as primary — lsblk may fail in containers with mknod nodes)
DETECTED_LABEL=$(blkid -s LABEL -o value "$PERSIST_PART" 2>/dev/null | tr -d '[:space:]')
[ "$DETECTED_LABEL" = "persistence" ] && ok "Label verified: $DETECTED_LABEL" \
    || fail "Expected label 'persistence', got '$DETECTED_LABEL'"

# =============================================================================
# Phase 5: Mount persistence and install init script + service
# =============================================================================
step "Phase 5 – Installing persistence files"

mkdir -p "$PERSIST_MOUNT"
mount "$PERSIST_PART" "$PERSIST_MOUNT"
ok "Mounted persistence partition at $PERSIST_MOUNT"

# Create overlay directory structure
for dir in $OVERLAY_DIRS; do
    mkdir -p "$PERSIST_MOUNT/overlays/$dir/upper" \
             "$PERSIST_MOUNT/overlays/$dir/work"
done
mkdir -p "$PERSIST_MOUNT/home"
chmod 755 "$PERSIST_MOUNT"
ok "Overlay directories created"

# Run setup-persistence.sh functions to install init script and service.
# We source all function definitions but skip the auto-execution block at the
# bottom by truncating before the "# Only run in live environment" guard.
GUARD_LINE=$(grep -n "^if \[" /usr/local/bin/setup-persistence.sh | tail -1 | cut -d: -f1)
if [ -z "$GUARD_LINE" ]; then
    # Fallback: find the guard comment
    GUARD_LINE=$(grep -n "^# Only run" /usr/local/bin/setup-persistence.sh | head -1 | cut -d: -f1)
fi
head -n "$((GUARD_LINE - 1))" /usr/local/bin/setup-persistence.sh > /tmp/_persist_funcs.sh
echo "install_persist_files" >> /tmp/_persist_funcs.sh
bash /tmp/_persist_funcs.sh

# Verify files were created
[ -x "$PERSIST_MOUNT/mados-persist-init.sh" ] \
    && ok "Init script installed in persistence partition" \
    || fail "Init script missing from persistence partition"

[ -f "$PERSIST_MOUNT/mados-persistence.service" ] \
    && ok "Systemd unit installed in persistence partition" \
    || fail "Systemd unit missing from persistence partition"

# Verify service file content
grep -q "Before=.*display-manager.service" "$PERSIST_MOUNT/mados-persistence.service" \
    && ok "Service runs before display-manager.service" \
    || fail "Service missing Before=display-manager.service"

grep -q "ConditionPathExists=/run/archiso" "$PERSIST_MOUNT/mados-persistence.service" \
    && ok "Service has archiso condition" \
    || fail "Service missing archiso condition"

# Unmount before running init (init script will mount it itself)
umount "$PERSIST_MOUNT"
ok "Unmounted persistence (will be re-mounted by init script)"

# =============================================================================
# Phase 6: Run init script and verify overlayfs mounts
# =============================================================================
step "Phase 6 – Running persistence init script (first boot simulation)"

# The init script lives inside the persistence partition, so we must mount
# the partition first, then run the script (which is what the systemd service
# does — it calls setup-persistence.sh which mounts and runs the init script).
mount "$PERSIST_PART" "$PERSIST_MOUNT"
"$PERSIST_MOUNT/mados-persist-init.sh"

# Verify persistence partition is mounted
mountpoint -q "$PERSIST_MOUNT" \
    && ok "Persistence partition mounted at $PERSIST_MOUNT" \
    || fail "Persistence partition not mounted"

# Verify overlay mounts
for dir in $OVERLAY_DIRS; do
    if findmnt -n -t overlay "/$dir" >/dev/null 2>&1; then
        ok "Overlay mounted for /$dir"
    else
        fail "Overlay NOT mounted for /$dir"
    fi
done

# Verify /home bind mount
if mountpoint -q /home 2>/dev/null; then
    ok "/home is a mountpoint (bind mount active)"
else
    fail "/home is NOT a mountpoint"
fi

# Verify ldconfig ran (check log)
if [ -f "$LOG_FILE" ] && grep -q "ldconfig completed" "$LOG_FILE"; then
    ok "ldconfig was executed after /usr overlay"
else
    warn "ldconfig execution not confirmed in log"
fi

# Verify /run/mados/persist_device
if [ -f /run/mados/persist_device ]; then
    STORED_DEV=$(cat /run/mados/persist_device)
    ok "Device info stored: $STORED_DEV"
else
    fail "/run/mados/persist_device not found"
fi

# =============================================================================
# Phase 7: Test data persistence across overlays
# =============================================================================
step "Phase 7 – Testing data persistence"

# Write test file to /etc (overlay)
echo "mados-test-config" > /etc/mados-persistence-test
if [ -f /etc/mados-persistence-test ]; then
    ok "File written to /etc overlay"
else
    fail "Could not write to /etc overlay"
fi

# Write test file to /home (bind mount)
echo "mados-home-test" > /home/mados-persistence-test
if [ -f /home/mados-persistence-test ]; then
    ok "File written to /home bind mount"
else
    fail "Could not write to /home bind mount"
fi

# Verify the file exists in the persistence partition's upper layer
if [ -f "$PERSIST_MOUNT/overlays/etc/upper/mados-persistence-test" ]; then
    ok "File persisted to etc upper layer"
else
    fail "File NOT in etc upper layer"
fi

if [ -f "$PERSIST_MOUNT/home/mados-persistence-test" ]; then
    ok "File persisted to home directory"
else
    fail "File NOT in home directory"
fi

# =============================================================================
# Phase 8: Simulate reboot – unmount everything and re-run init
# =============================================================================
step "Phase 8 – Simulating reboot (unmount + re-mount)"

# Unmount in correct order (reverse of OVERLAY_DIRS)
umount /home 2>/dev/null || true
for dir in $(echo $OVERLAY_DIRS | tr ' ' '\n' | tac | tr '\n' ' '); do
    umount "/$dir" 2>/dev/null || true
done
umount "$PERSIST_MOUNT" 2>/dev/null || true

info "All persistence mounts removed"

# Clear log for clean verification
: > "$LOG_FILE"

# Re-run init script (simulating what systemd does on boot)
mount "$PERSIST_PART" "$PERSIST_MOUNT"
"$PERSIST_MOUNT/mados-persist-init.sh"

# Verify everything is back
for dir in $OVERLAY_DIRS; do
    if findmnt -n -t overlay "/$dir" >/dev/null 2>&1; then
        ok "After reboot: overlay /$dir restored"
    else
        fail "After reboot: overlay /$dir NOT restored"
    fi
done

if mountpoint -q /home 2>/dev/null; then
    ok "After reboot: /home bind mount restored"
else
    fail "After reboot: /home NOT restored"
fi

# Verify persisted data survived the "reboot"
if [ -f /etc/mados-persistence-test ] && \
   grep -q "mados-test-config" /etc/mados-persistence-test; then
    ok "After reboot: /etc test file survived"
else
    fail "After reboot: /etc test file LOST"
fi

if [ -f /home/mados-persistence-test ] && \
   grep -q "mados-home-test" /home/mados-persistence-test; then
    ok "After reboot: /home test file survived"
else
    fail "After reboot: /home test file LOST"
fi

# =============================================================================
# Phase 9: Test running setup-persistence.sh again (second boot scenario)
# =============================================================================
step "Phase 9 – Testing second boot detection (setup-persistence.sh should detect existing partition)"

# Unmount overlays but leave persistence partition mounted
umount /home 2>/dev/null || true
for dir in $(echo $OVERLAY_DIRS | tr ' ' '\n' | tac | tr '\n' ' '); do
    umount "/$dir" 2>/dev/null || true
done

# Clear log for clean verification
: > "$LOG_FILE"

# Run setup-persistence.sh again - it should detect the existing partition
# and not try to create a new one
info "Running setup-persistence.sh again (should detect existing partition)"
SETUP_EXIT_CODE=0
/usr/local/bin/setup-persistence.sh 2>&1 | tee -a "$LOG_FILE" || SETUP_EXIT_CODE=$?

# Ensure log file is flushed to disk
sync
sleep 0.5

if [ "$SETUP_EXIT_CODE" -eq 0 ]; then
    ok "setup-persistence.sh ran successfully on second boot"
else
    fail "setup-persistence.sh failed on second boot (exit code: $SETUP_EXIT_CODE)"
fi

# Verify it found the existing partition and didn't try to create a new one
# Debug: Show what's in the log file
info "Debug: Checking log file for partition detection messages"
info "Debug: Log file size: $(wc -l < "$LOG_FILE" 2>/dev/null || echo '0') lines"
if [ -f "$LOG_FILE" ]; then
    info "Debug: Log file relevant lines:"
    grep -i "found\|partition\|OK:\|INFO:" "$LOG_FILE" 2>&1 | head -20 | while read -r line; do
        echo "    $line"
    done
fi

if grep -q "  OK: Found existing partition" "$LOG_FILE" || \
   grep -q "  INFO: Found via direct scan" "$LOG_FILE" || \
   grep -q "  INFO: Found via global search" "$LOG_FILE"; then
    ok "Existing persistence partition was detected"
elif grep -q "already has overlay" "$LOG_FILE"; then
    ok "Existing persistence partition was detected (via overlay check)"
else
    fail "Could not confirm existing partition was detected"
fi

# Verify it did NOT try to create a partition
if grep -q "Creating persistence partition" "$LOG_FILE"; then
    fail "setup-persistence.sh tried to create a new partition when one already existed!"
elif grep -q "sfdisk failed\|parted mkpart failed" "$LOG_FILE"; then
    fail "setup-persistence.sh failed to create partition (should have detected existing one)"
else
    ok "No duplicate partition creation attempted"
fi

# Verify overlays are mounted after second run
for dir in $OVERLAY_DIRS; do
    if findmnt -n -t overlay "/$dir" >/dev/null 2>&1; then
        ok "After second setup: overlay /$dir mounted"
    else
        fail "After second setup: overlay /$dir NOT mounted"
    fi
done

if mountpoint -q /home 2>/dev/null; then
    ok "After second setup: /home bind mount active"
else
    fail "After second setup: /home NOT mounted"
fi

# =============================================================================
# Phase 10: Test systemd service file (syntax validation)
# =============================================================================
step "Phase 10 – Validating systemd service syntax"

SERVICE_FILE="${REPO_DIR}/airootfs/etc/systemd/system/mados-persistence.service"

if [ -f "$SERVICE_FILE" ]; then
    ok "Service file exists in repo"
else
    fail "Service file missing from repo"
fi

# Check key directives
grep -q "Type=oneshot" "$SERVICE_FILE" && ok "Type=oneshot" || fail "Missing Type=oneshot"
grep -q "RemainAfterExit=yes" "$SERVICE_FILE" && ok "RemainAfterExit=yes" || fail "Missing RemainAfterExit"
grep -q "Before=.*display-manager.service" "$SERVICE_FILE" \
    && ok "Before display-manager.service" \
    || fail "Missing Before=display-manager.service"
grep -q "ConditionPathExists=/run/archiso" "$SERVICE_FILE" \
    && ok "ConditionPathExists=/run/archiso" \
    || fail "Missing ConditionPathExists"
grep -q "WantedBy=multi-user.target" "$SERVICE_FILE" \
    && ok "WantedBy=multi-user.target" \
    || fail "Missing WantedBy=multi-user.target"

# =============================================================================
# Phase 11: Validate script syntax
# =============================================================================
step "Phase 11 – Validating script syntax"

for script in setup-persistence.sh mados-persistence; do
    SCRIPT_PATH="${REPO_DIR}/airootfs/usr/local/bin/$script"
    if bash -n "$SCRIPT_PATH" 2>/tmp/bash_err; then
        ok "$script: valid bash syntax"
    else
        fail "$script: syntax error: $(cat /tmp/bash_err)"
    fi
done

# Validate the embedded init script (extract and check)
if [ -x "$PERSIST_MOUNT/mados-persist-init.sh" ]; then
    if bash -n "$PERSIST_MOUNT/mados-persist-init.sh" 2>/tmp/bash_err; then
        ok "mados-persist-init.sh: valid bash syntax"
    else
        fail "mados-persist-init.sh: syntax error: $(cat /tmp/bash_err)"
    fi
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
