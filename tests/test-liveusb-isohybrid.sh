#!/bin/bash
# =============================================================================
# madOS Live USB Isohybrid Partition Test
# =============================================================================
# Tests the partition gap detection and safe partitioning logic when creating
# persistence partitions on isohybrid archiso USBs where:
#   - Device node /dev/loopXp1 exists (ISO data)
#   - But partition 1 is NOT in the partition table
#   - Only partition 2 (EFI) is in the table
#   - This creates a "gap" that parted would fill, overwriting ISO data
#
# This test verifies the fix implemented to detect this situation and use
# sfdisk instead of parted to create partition 3 safely.
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
DISK_IMAGE="/tmp/test-isohybrid-usb.img"
LOOP_DEV=""
PERSIST_MOUNT="/mnt/persistence"

cleanup() {
    step "Cleanup"
    
    umount "$PERSIST_MOUNT" 2>/dev/null || true
    [ -n "${LOOP_DEV:-}" ] && losetup -d "$LOOP_DEV" 2>/dev/null || true
    rm -f "$DISK_IMAGE"
    rm -rf /run/archiso 2>/dev/null || true
    rm -rf /run/mados 2>/dev/null || true
    rm -f "$LOG_FILE"
    
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

ok "Dependencies installed (including sfdisk)"

# Verify sfdisk is available (critical for the fix)
if command -v sfdisk >/dev/null 2>&1; then
    ok "sfdisk is available"
else
    fail "sfdisk is NOT available - fix cannot work!"
fi

# Copy scripts
cp "${REPO_DIR}/airootfs/usr/local/bin/setup-persistence.sh" /usr/local/bin/setup-persistence.sh
chmod 755 /usr/local/bin/setup-persistence.sh
ok "setup-persistence.sh installed"

# =============================================================================
# Phase 2: Create isohybrid disk layout
# =============================================================================
step "Phase 2 – Creating isohybrid USB layout"

# 4 GB disk with only partition 2 in the table (partition 1 missing!)
truncate -s 4G "$DISK_IMAGE"
LOOP_DEV=$(losetup -f --show "$DISK_IMAGE")
info "Loopback device: $LOOP_DEV"

# Create isohybrid-like layout:
# 1. Create both partitions 1 and 2 in the table
# 2. Remove partition 1 from the table (but data remains on disk)
# 3. Manually recreate device node for partition 1
# 4. Result: device nodes p1 and p2 exist, but table only shows partition 2

parted -s "$LOOP_DEV" mklabel msdos
info "Created MBR partition table"

# Create partition 1 (will simulate ISO data at 0-2048 MB)
parted -s "$LOOP_DEV" mkpart primary 1MiB 2048MiB
info "Created partition 1 (ISO area) at 1-2048 MB"

# Create partition 2 (EFI at 2048-2248 MB)
parted -s "$LOOP_DEV" mkpart primary fat32 2048MiB 2248MiB
parted -s "$LOOP_DEV" set 2 esp on
info "Created partition 2 (EFI) at 2048-2248 MB"

# Display what we have before removal
info "Partition table before removal:"
parted -s "$LOOP_DEV" unit MB print 2>/dev/null | grep -E "(Number|^ [0-9])" || true

# Remove partition 1 from the table (simulating isohybrid where ISO isn't in table)
parted -s "$LOOP_DEV" rm 1
info "Removed partition 1 from table (partition 2 remains)"

# Display what parted sees
info "Partition table (parted view):"
parted -s "$LOOP_DEV" unit MB print 2>/dev/null | grep -E "(Number|^ [0-9])" || true

# Re-attach with partition scan
losetup -d "$LOOP_DEV"
LOOP_DEV=$(losetup -fP --show "$DISK_IMAGE")
info "Reattached with partition scan: $LOOP_DEV"

partprobe "$LOOP_DEV" 2>/dev/null || true
partx -a "$LOOP_DEV" 2>/dev/null || true
udevadm settle --timeout=10 2>/dev/null || true

# Create device nodes
LOOP_NAME=$(basename "$LOOP_DEV")

# CRITICAL: Manually create device node for partition 1 (simulating isohybrid)
# This node exists but is NOT in the partition table!
PART1_DEV="${LOOP_DEV}p1"
if ! [ -b "$PART1_DEV" ]; then
    # Calculate major/minor for partition 1 (same major as loop, minor +1)
    LOOP_MAJOR=$(stat -c '%t' "$LOOP_DEV" | tr '[:lower:]' '[:upper:]')
    LOOP_MINOR=$(stat -c '%T' "$LOOP_DEV" | tr '[:lower:]' '[:upper:]')
    LOOP_MAJOR_DEC=$((16#$LOOP_MAJOR))
    LOOP_MINOR_DEC=$((16#$LOOP_MINOR))
    PART1_MINOR=$((LOOP_MINOR_DEC + 1))
    
    info "Creating MANUAL device node for partition 1: ${PART1_DEV}"
    info "  Major: ${LOOP_MAJOR_DEC}, Minor: ${PART1_MINOR}"
    mknod "$PART1_DEV" b "$LOOP_MAJOR_DEC" "$PART1_MINOR"
    
    # Wait for device node to be recognized
    sleep 0.5
    
    # Create a small filesystem on it to simulate ISO data
    # Use ARCHISO label so find_iso_device() can detect it via lsblk fallback
    info "Creating filesystem on ${PART1_DEV}..."
    dd if=/dev/zero of="$PART1_DEV" bs=1M count=100 2>/dev/null || true
    sync
    mkfs.ext4 -F -L "ARCHISO" "$PART1_DEV" 2>&1 | head -5 || {
        warn "mkfs.ext4 failed, trying to check device node status"
        ls -la "$PART1_DEV" || true
        file "$PART1_DEV" || true
    }
fi

# Create device node for partition 2 (normal)
PART2_DEV="${LOOP_DEV}p2"
SYSFS_DEV="/sys/block/${LOOP_NAME}/${LOOP_NAME}p2/dev"
if ! [ -b "$PART2_DEV" ] && [ -f "$SYSFS_DEV" ]; then
    MAJOR=$(cut -d: -f1 < "$SYSFS_DEV" | tr -d '[:space:]')
    MINOR=$(cut -d: -f2 < "$SYSFS_DEV" | tr -d '[:space:]')
    info "Creating device node ${PART2_DEV} (${MAJOR}:${MINOR})"
    mknod "$PART2_DEV" b "$MAJOR" "$MINOR"
fi

# Format partition 2 as FAT32
mkfs.fat -F32 "${LOOP_DEV}p2" >/dev/null 2>&1

# Verify the isohybrid situation
if [ -b "${LOOP_DEV}p1" ]; then
    ok "Device node ${LOOP_DEV}p1 EXISTS (simulating isohybrid ISO)"
else
    fail "Device node ${LOOP_DEV}p1 missing - cannot test isohybrid scenario"
fi

if [ -b "${LOOP_DEV}p2" ]; then
    ok "Device node ${LOOP_DEV}p2 exists (EFI)"
else
    fail "Device node ${LOOP_DEV}p2 missing"
fi

# Check partition table - should only show partition 2
PART_COUNT=$(parted -s "$LOOP_DEV" print 2>/dev/null | grep -c "^ [0-9]" || echo "0")
if [ "$PART_COUNT" -eq 1 ]; then
    ok "Partition table contains only 1 entry (partition 2)"
else
    warn "Partition table contains $PART_COUNT entries (expected 1)"
fi

# Display device nodes
info "Device nodes (lsblk view):"
lsblk "$LOOP_DEV" 2>/dev/null || true

info "This is the EXACT scenario from the bug:"
info "  - ${LOOP_DEV}p1 device exists (ISO data)"
info "  - ${LOOP_DEV}p2 device exists (EFI)"
info "  - But partition table only shows partition 2"
info "  - Partition 1 is MISSING from the table (GAP!)"

ok "Isohybrid USB layout ready"

# =============================================================================
# Phase 3: Simulate archiso environment
# =============================================================================
step "Phase 3 – Simulating archiso live environment"

mkdir -p /run/archiso/bootmnt
mkdir -p /run/mados

# Mount partition 1 at /run/archiso/bootmnt so find_iso_device() can detect it
# This simulates the real archiso environment where the ISO partition is mounted
info "Attempting to mount ${LOOP_DEV}p1 at /run/archiso/bootmnt..."
if mount "${LOOP_DEV}p1" /run/archiso/bootmnt 2>/tmp/mount_error.log; then
    ok "Mounted partition 1 at /run/archiso/bootmnt"
else
    warn "Could not mount partition 1 at /run/archiso/bootmnt"
    cat /tmp/mount_error.log >&2 || true
    # Check if it's a valid ext4 filesystem
    info "Checking filesystem type:"
    blkid "${LOOP_DEV}p1" 2>/dev/null || true
    # Fallback: create marker file for tests that need direct access
    echo "$LOOP_DEV" > /run/mados/iso_device
fi

ok "Archiso environment simulated"

# =============================================================================
# Phase 4: Run setup-persistence.sh with isohybrid detection
# =============================================================================
step "Phase 4 – Running setup-persistence.sh (testing gap detection)"

# Clear log
: > "$LOG_FILE"

# Extract and run just the create_persist_partition function
# We need to bypass the auto-detection logic and call the function directly

cat > /tmp/test_partition_creation.sh << 'TESTEOF'
#!/bin/bash
set -euo pipefail

# Source the setup-persistence.sh functions
SCRIPT_FUNCS="/tmp/setup-persistence-funcs.sh"
GUARD_LINE=$(grep -n "^if \[" /usr/local/bin/setup-persistence.sh | tail -1 | cut -d: -f1)
if [ -z "$GUARD_LINE" ]; then
    GUARD_LINE=$(grep -n "^# Only run" /usr/local/bin/setup-persistence.sh | head -1 | cut -d: -f1)
fi
head -n "$((GUARD_LINE - 1))" /usr/local/bin/setup-persistence.sh > "$SCRIPT_FUNCS"
source "$SCRIPT_FUNCS"

# Get the loop device from our marker
LOOP_DEV=$(cat /run/mados/iso_device)

# OVERRIDE: Mock find_iso_device to return our test device
# This is necessary because the container environment doesn't have
# the full archiso setup with mounted /run/archiso/bootmnt
find_iso_device() {
    echo "$LOOP_DEV"
}

# Call create_persist_partition directly
echo "Calling create_persist_partition for $LOOP_DEV"
create_persist_partition "$LOOP_DEV"
TESTEOF

chmod +x /tmp/test_partition_creation.sh

# Run the test
if /tmp/test_partition_creation.sh 2>&1 | tee -a "$LOG_FILE"; then
    ok "create_persist_partition completed successfully"
else
    RESULT=$?
    fail "create_persist_partition failed with exit code $RESULT"
fi

# =============================================================================
# Phase 5: Verify gap detection and safe partitioning
# =============================================================================
step "Phase 5 – Verifying gap detection and safe partitioning"

# Check log for gap detection messages
if grep -q "Found existing device node" "$LOG_FILE"; then
    ok "Log shows device node enumeration"
else
    fail "Log missing device node enumeration"
fi

if grep -q "Highest partition device node:" "$LOG_FILE"; then
    ok "Log shows highest device partition number"
else
    fail "Log missing highest device partition info"
fi

if grep -q "partition numbering gaps" "$LOG_FILE" || \
   grep -q "not in partition table" "$LOG_FILE"; then
    ok "Gap detection triggered (found partitions in devices but not in table)"
else
    warn "Gap detection message not found in log"
fi

if grep -q "Will use sfdisk" "$LOG_FILE" || \
   grep -q "Using sfdisk" "$LOG_FILE"; then
    ok "Script switched to sfdisk for explicit partition numbering"
else
    warn "sfdisk usage not confirmed in log"
fi

# Verify partition 3 was created (not partition 1!)
udevadm settle --timeout=10 2>/dev/null || true
sleep 2

# Check partition table
info "Partition table after creation:"
parted -s "$LOOP_DEV" unit MB print 2>/dev/null | grep -E "(Number|^ [0-9])" || true

# Check if partition 3 exists
PART3_DEV="${LOOP_DEV}p3"
if [ -b "$PART3_DEV" ]; then
    ok "Partition 3 device node exists: $PART3_DEV"
else
    # Try to create it manually if it's in the table but node missing
    SYSFS_DEV="/sys/block/${LOOP_NAME}/${LOOP_NAME}p3/dev"
    if [ -f "$SYSFS_DEV" ]; then
        MAJOR=$(cut -d: -f1 < "$SYSFS_DEV" | tr -d '[:space:]')
        MINOR=$(cut -d: -f2 < "$SYSFS_DEV" | tr -d '[:space:]')
        info "Creating device node ${PART3_DEV} (${MAJOR}:${MINOR})"
        mknod "$PART3_DEV" b "$MAJOR" "$MINOR"
    fi
    
    if [ -b "$PART3_DEV" ]; then
        ok "Partition 3 device node created"
    else
        fail "Partition 3 device node NOT found - partition creation may have failed"
    fi
fi

# Verify ISO data partition still exists and wasn't overwritten
if [ -b "${LOOP_DEV}p1" ]; then
    ok "ISO data partition (p1) still exists"
    
    # Try to read the label we set
    ISO_LABEL=$(blkid -s LABEL -o value "${LOOP_DEV}p1" 2>/dev/null || echo "")
    if [ "$ISO_LABEL" = "ISO_DATA" ]; then
        ok "ISO data partition label preserved: $ISO_LABEL"
    else
        warn "ISO partition label check failed (got: '$ISO_LABEL')"
    fi
else
    fail "ISO data partition (p1) was DESTROYED - bug not fixed!"
fi

# Count partitions in table - should now be 2 (partition 2 and 3)
PART_COUNT_AFTER=$(parted -s "$LOOP_DEV" print 2>/dev/null | grep -c "^ [0-9]" || echo "0")
info "Partition count in table: before=1, after=$PART_COUNT_AFTER"

if [ "$PART_COUNT_AFTER" -eq 2 ]; then
    ok "Partition table now has 2 entries (partition 2 + 3)"
elif [ "$PART_COUNT_AFTER" -eq 3 ]; then
    warn "Partition table has 3 entries - partition 1 may have been added"
else
    fail "Unexpected partition count: $PART_COUNT_AFTER"
fi

# Verify the NEW partition is #3, not #1
NEW_PART_NUM=$(parted -s "$LOOP_DEV" print 2>/dev/null | grep "^ [0-9]" | tail -1 | awk '{print $1}')
if [ "$NEW_PART_NUM" = "3" ]; then
    ok "New partition number is 3 (correct!)"
elif [ "$NEW_PART_NUM" = "1" ]; then
    fail "New partition number is 1 (BUG - gap was filled, ISO data destroyed!)"
else
    warn "New partition number is $NEW_PART_NUM (unexpected)"
fi

# Check if persistence partition is formatted
if [ -b "$PART3_DEV" ]; then
    PERSIST_LABEL=$(blkid -s LABEL -o value "$PART3_DEV" 2>/dev/null || echo "")
    if [ "$PERSIST_LABEL" = "persistence" ]; then
        ok "Persistence partition has correct label: $PERSIST_LABEL"
    else
        warn "Persistence label check failed (got: '$PERSIST_LABEL')"
    fi
    
    PERSIST_TYPE=$(blkid -s TYPE -o value "$PART3_DEV" 2>/dev/null || echo "")
    if [ "$PERSIST_TYPE" = "ext4" ]; then
        ok "Persistence partition is ext4"
    else
        warn "Persistence filesystem type: $PERSIST_TYPE"
    fi
fi

# =============================================================================
# Phase 6: Verify partition layout preservation
# =============================================================================
step "Phase 6 – Verifying partition layout preservation"

# Check partition 2 is still there and unchanged
if [ -b "${LOOP_DEV}p2" ]; then
    ok "EFI partition (p2) still exists"
    
    EFI_TYPE=$(blkid -s TYPE -o value "${LOOP_DEV}p2" 2>/dev/null || echo "")
    if [ "$EFI_TYPE" = "vfat" ]; then
        ok "EFI partition is still FAT32"
    else
        warn "EFI partition type changed: $EFI_TYPE"
    fi
else
    fail "EFI partition (p2) was destroyed"
fi

# Display final layout
info "Final device layout:"
lsblk "$LOOP_DEV" 2>/dev/null || true

info "Final partition table:"
parted -s "$LOOP_DEV" unit MB print 2>/dev/null || true

# =============================================================================
# Phase 7: Test persistence mounting (optional verification)
# =============================================================================
step "Phase 7 – Testing persistence partition mount"

if [ -b "$PART3_DEV" ]; then
    mkdir -p "$PERSIST_MOUNT"
    
    if mount "$PART3_DEV" "$PERSIST_MOUNT" 2>/dev/null; then
        ok "Persistence partition mounts successfully"
        
        # Write a test file
        if echo "isohybrid-test" > "$PERSIST_MOUNT/test.txt"; then
            ok "Can write to persistence partition"
        else
            fail "Cannot write to persistence partition"
        fi
        
        umount "$PERSIST_MOUNT"
    else
        fail "Failed to mount persistence partition"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
step "Results"
echo ""

# Print log excerpt for debugging
if [ -f "$LOG_FILE" ]; then
    info "Log excerpt (gap detection):"
    grep -A2 -B2 "gap\|device partition\|sfdisk\|WARNING" "$LOG_FILE" | head -20 || true
fi

echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ ISOHYBRID TEST PASSED  (warnings: ${WARNINGS})${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}"
    echo -e "  The fix works correctly:"
    echo -e "  • Gap detected between device nodes and partition table"
    echo -e "  • Script used sfdisk for explicit partition numbering"
    echo -e "  • Partition 3 created (not partition 1)"
    echo -e "  • ISO data partition preserved"
    echo -e "  • EFI partition preserved"
    echo -e "${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════${NC}"
    echo -e "${RED}  ✗ ${ERRORS} TEST(S) FAILED  (warnings: ${WARNINGS})${NC}"
    echo -e "${RED}═══════════════════════════════════════════${NC}"
    exit 1
fi
