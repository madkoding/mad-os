#!/usr/bin/env bash
# madOS Persistence Setup
# Auto-creates persistence partition and installs overlayfs-based persistence.
# Overlayfs directories: /etc, /usr, /var, /opt (overlay) + /home (bind mount).
# The systemd service and init script are stored INSIDE the persistence
# partition so a single command on each boot restores everything.
#
# Simplified flow:
#   Step 1 – Detect boot device
#   Step 2 – Check for existing ext4 partition (>1 GB) on the same disk
#   Step 3 – If none, create ext4 in remaining free space after ISO/EFI
#   Step 4 – Mount the ext4 partition
#   Step 5 – First boot: set up overlayfs and move data
#   Step 6 – Confirm partition is mounted and directories are ready

set -euo pipefail

PERSIST_LABEL="persistence"
PERSIST_MOUNT="/mnt/persistence"
LOG_FILE="/var/log/mados-persistence.log"
OVERLAY_DIRS="etc usr var opt"
MIN_PERSIST_MB=1024   # minimum 1 GB for persistence partition

# ── Console UI helpers ───────────────────────────────────────────────────────
# Nord-inspired colors for professional boot output
BOLD='\033[1m'
DIM='\033[2m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

STEP_NUM=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE" >&2
}

ui_header() {
    echo -e "${BLUE}${BOLD}" >&2
    echo -e "  ┌──────────────────────────────────────────────┐" >&2
    echo -e "  │          madOS Persistence Setup              │" >&2
    echo -e "  └──────────────────────────────────────────────┘" >&2
    echo -e "${NC}" >&2
}

ui_step() {
    STEP_NUM=$((STEP_NUM + 1))
    echo -e "  ${CYAN}${BOLD}[${STEP_NUM}]${NC} ${BOLD}$*${NC}" >&2
    log "STEP $STEP_NUM: $*"
}

ui_ok() {
    echo -e "  ${GREEN}  ✓${NC} $*" >&2
    log "  OK: $*"
}

ui_warn() {
    echo -e "  ${YELLOW}  ⚠${NC} $*" >&2
    log "  WARN: $*"
}

ui_fail() {
    echo -e "  ${RED}  ✗${NC} $*" >&2
    log "  FAIL: $*"
}

ui_info() {
    echo -e "  ${DIM}    $*${NC}" >&2
    log "  INFO: $*"
}

ui_done() {
    echo "" >&2
    echo -e "  ${GREEN}${BOLD}── Persistence ready ──${NC}" >&2
    echo "" >&2
    log "Persistence setup finished successfully"
}

ui_skip() {
    echo -e "  ${DIM}  ─ $*${NC}" >&2
    log "  SKIP: $*"
}

# ── Device helpers ───────────────────────────────────────────────────────────

is_usb_device() {
    local device=${1#/dev/}

    if [ -e "/sys/block/$device" ]; then
        local device_path
        device_path=$(readlink -f "/sys/block/$device" 2>/dev/null)
        [[ "$device_path" == *"/usb"* ]] && return 0
    fi

    if command -v udevadm >/dev/null 2>&1; then
        local id_bus
        id_bus=$(udevadm info --query=property --name="/dev/$device" 2>/dev/null \
                 | grep "^ID_BUS=" | cut -d= -f2)
        [ "$id_bus" = "usb" ] && return 0
    fi

    # Fallback: check sysfs removable flag
    if [ -f "/sys/block/$device/removable" ]; then
        [ "$(cat "/sys/block/$device/removable" 2>/dev/null)" = "1" ] && return 0
    fi

    return 1
}

is_optical_device() {
    local device=${1#/dev/}

    # Check if device name matches optical drive pattern (sr0, sr1, etc.)
    [[ "$device" == sr* ]] && return 0

    # Check SCSI device type (type 5 = CD-ROM)
    if [ -f "/sys/block/$device/device/type" ]; then
        [ "$(cat "/sys/block/$device/device/type" 2>/dev/null)" = "5" ] && return 0
    fi

    if command -v udevadm >/dev/null 2>&1; then
        local id_cdrom
        id_cdrom=$(udevadm info --query=property --name="/dev/$device" 2>/dev/null \
                   | grep "^ID_CDROM=" | cut -d= -f2)
        [ "$id_cdrom" = "1" ] && return 0
    fi

    return 1
}

# Strip partition number from a block device path to get the base device.
# Handles standard disks (/dev/sda1 → /dev/sda), nvme (/dev/nvme0n1p2 →
# /dev/nvme0n1), mmcblk (/dev/mmcblk0p1 → /dev/mmcblk0), and loop (/dev/loop0p1 → /dev/loop0).
strip_partition() {
    local dev=$1
    if [[ "$dev" == *"nvme"*p[0-9]* || "$dev" == *"mmcblk"*p[0-9]* || "$dev" == *"loop"*p[0-9]* ]]; then
        echo "$dev" | sed 's/p[0-9]*$//'
    else
        echo "$dev" | sed 's/[0-9]*$//'
    fi
}

find_iso_device() {
    local iso_device=""

    if [ -d /run/archiso/bootmnt ]; then
        local raw_source
        raw_source=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null \
                     | sed 's/\[.*\]//')

        if [ -n "$raw_source" ] && [ -b "$raw_source" ]; then
            # If findmnt returned a loop device, resolve its backing file
            if [[ "$raw_source" == /dev/loop* ]]; then
                local backing
                backing=$(losetup -nO BACK-FILE "$raw_source" 2>/dev/null | head -1)
                if [ -n "$backing" ]; then
                    local back_dev
                    back_dev=$(df --output=source "$backing" 2>/dev/null | tail -1)
                    [ -n "$back_dev" ] && [ -b "$back_dev" ] && raw_source="$back_dev"
                fi
            fi
            iso_device=$(strip_partition "$raw_source")
        fi
    fi

    if [ -z "$iso_device" ]; then
        iso_device=$(lsblk -nlo NAME,LABEL 2>/dev/null \
                     | grep -iE "(ARCHISO|MADOS)" | head -1 \
                     | awk '{print $1}')
        if [ -n "$iso_device" ]; then
            iso_device=$(strip_partition "/dev/$iso_device")
        fi
    fi
    echo "$iso_device"
}

# Find the partition with the ISO filesystem (iso9660)
find_iso_partition() {
    lsblk -nlo NAME,FSTYPE 2>/dev/null \
        | awk '$2 == "iso9660" {print "/dev/" $1}' | head -1
}

# Find persistence partition on the given parent device.
# Simplified: looks for an ext4 partition with >1 GB on the same disk as boot.
# First checks by label, then scans for any qualifying ext4 partition.
find_persist_partition() {
    local parent_device="${1:-}"
    local dev=""

    if [ -n "$parent_device" ] && [ -b "$parent_device" ]; then
        # 1) Check by persistence label (fast path)
        dev=$(lsblk -nlo NAME,LABEL "$parent_device" 2>/dev/null \
            | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1)
        if [ -z "$dev" ] && command -v blkid >/dev/null 2>&1; then
            local part
            for part in $(lsblk -nlo NAME "$parent_device" 2>/dev/null \
                          | tail -n +2 | awk '{print "/dev/" $1}'); do
                if [ -b "$part" ]; then
                    local label
                    label=$(blkid -s LABEL -o value "$part" 2>/dev/null)
                    if [ "$label" = "$PERSIST_LABEL" ]; then
                        dev="$part"
                        break
                    fi
                fi
            done
        fi

        # 2) Scan for any ext4 partition >1 GB (simplified validation)
        if [ -z "$dev" ]; then
            log "Debug: scanning for ext4 partitions on $parent_device"
            local iso_part
            iso_part=$(find_iso_partition)
            log "Debug: excluding ISO partition: $iso_part (via find_iso_partition)"
            for part in $(lsblk -nlo NAME "$parent_device" 2>/dev/null | tail -n +2); do
                local full_part="/dev/$part"
                [ -b "$full_part" ] || continue
                [ "$full_part" = "$iso_part" ] && continue
                local fstype
                fstype=$(blkid -s TYPE -o value "$full_part" 2>/dev/null)
                if [ "$fstype" = "ext4" ]; then
                    # Check size ≥ MIN_PERSIST_MB
                    local size_mb
                    size_mb=$(lsblk -bnlo SIZE "$full_part" 2>/dev/null | head -1)
                    size_mb=$(( ${size_mb:-0} / 1048576 ))
                    if [ "$size_mb" -ge "$MIN_PERSIST_MB" ]; then
                        log "Found ext4 partition $full_part (${size_mb} MB) – using as persistence"
                        # Add label so future lookups are faster
                        e2label "$full_part" "$PERSIST_LABEL" 2>/dev/null && \
                            log "Added persistence label to $full_part" || \
                            log "WARNING: Could not add label to $full_part"
                        dev="$full_part"
                        break
                    else
                        log "Debug: ext4 partition $full_part too small (${size_mb} MB < $MIN_PERSIST_MB MB)"
                    fi
                fi
            done
        fi
    else
        # No parent device specified – search all devices (legacy fallback)
        dev=$(lsblk -nlo NAME,LABEL 2>/dev/null \
            | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1)
        if [ -z "$dev" ] && command -v blkid >/dev/null 2>&1; then
            dev=$(blkid -L "$PERSIST_LABEL" 2>/dev/null)
        fi
    fi
    echo "$dev"
}

get_free_space() {
    local device=$1
    local free

    # Method 1: parted free space detection
    free=$(parted -s "$device" unit MB print free 2>/dev/null \
           | grep "Free Space" | tail -1 | awk '{print $3}' | sed 's/MB//')
    free="${free%%.*}"  # strip decimal portion

    # Method 2: calculate from disk size minus end of last partition
    if [ -z "$free" ] || [ "${free:-0}" -eq 0 ]; then
        local disk_mb last_end_mb
        disk_mb=$(( $(blockdev --getsize64 "$device" 2>/dev/null || echo 0) / 1048576 ))
        last_end_mb=$(parted -s "$device" unit MB print 2>/dev/null \
                      | grep "^ [0-9]" | awk '{gsub(/MB/,""); print $3}' \
                      | sort -n | tail -1)
        last_end_mb="${last_end_mb%%.*}"
        if [ "${disk_mb:-0}" -gt 0 ] && [ "${last_end_mb:-0}" -gt 0 ]; then
            free=$((disk_mb - last_end_mb))
            log "Free space calculated from disk size ($disk_mb MB) - last partition end ($last_end_mb MB) = $free MB"
        fi
    fi

    # Method 3: calculate from disk size minus ISO size (for raw iso9660 on device)
    if [ -z "$free" ] || [ "${free:-0}" -eq 0 ]; then
        local disk_mb iso_size_bytes
        disk_mb=$(( $(blockdev --getsize64 "$device" 2>/dev/null || echo 0) / 1048576 ))
        if [ "${disk_mb:-0}" -gt 0 ] && command -v isosize >/dev/null 2>&1; then
            iso_size_bytes=$(isosize "$device" 2>/dev/null)
            if [ -n "$iso_size_bytes" ] && [ "${iso_size_bytes:-0}" -gt 0 ]; then
                local iso_mb=$((iso_size_bytes / 1048576))
                free=$((disk_mb - iso_mb))
                log "Free space calculated from disk size ($disk_mb MB) - ISO size ($iso_mb MB) = $free MB"
            fi
        fi
    fi

    echo "${free:-0}"
}

# ── Partition creation ───────────────────────────────────────────────────────
# Calculates where existing partitions (ISO + EFI) end on the disk and
# creates a new ext4 partition using all remaining free space.

create_persist_partition() {
    local device=$1
    log "Creating persistence partition on $device"

    # SAFETY: verify the target device is the ISO boot device.
    local expected_iso_device
    expected_iso_device=$(find_iso_device)
    if [ -n "$expected_iso_device" ] && [ "$device" != "$expected_iso_device" ]; then
        log "SAFETY: Refusing to create partition on $device (ISO device is $expected_iso_device)"
        return 1
    fi

    local table_type
    table_type=$(parted -s "$device" print 2>/dev/null \
                 | grep -i "^Partition Table:" | awk '{print $3}')

    local part_suffix=""
    [[ "$device" == *"nvme"* || "$device" == *"mmcblk"* || "$device" == *"loop"* ]] && part_suffix="p"

    # Scan existing device nodes to find the highest partition number
    # (accounts for isohybrid ISOs where device nodes may not be in the table)
    local highest_dev_num=0
    local dev_node
    for dev_node in "${device}${part_suffix}"[0-9]* "${device}"[0-9]*; do
        if [ -b "$dev_node" ]; then
            local dnum
            if [ -n "$part_suffix" ]; then
                dnum=$(echo "$dev_node" | sed 's/.*p\([0-9]*\)$/\1/')
            else
                dnum=$(echo "$dev_node" | sed 's/.*[^0-9]\([0-9]*\)$/\1/')
            fi
            if [ -n "$dnum" ] && [ "$dnum" -gt "$highest_dev_num" ]; then
                highest_dev_num=$dnum
                log "Debug: Found existing device node: $dev_node (partition $dnum)"
            fi
        fi
    done
    log "Debug: Highest existing device partition number: $highest_dev_num"

    # Also check partition table
    local last_part_num
    last_part_num=$(parted -s "$device" print 2>/dev/null \
                    | grep "^ [0-9]" | awk '{print $1}' | sort -n | tail -1)
    last_part_num="${last_part_num:-0}"
    log "Debug: Highest partition in table: $last_part_num"

    local safe_last_part=$last_part_num
    [ "$highest_dev_num" -gt "$safe_last_part" ] && safe_last_part=$highest_dev_num
    local sfdisk_new_part_num=$((safe_last_part + 1))
    local new_part_num=$sfdisk_new_part_num
    log "Debug: Will create partition number: $new_part_num"

    # MBR 4-partition limit check
    if [ "$table_type" = "msdos" ] && [ "$new_part_num" -gt 4 ]; then
        log "SAFETY: MBR partition table – new partition would be #$new_part_num (max 4)"
        return 1
    fi
    if [ "$table_type" = "msdos" ] && [ "$sfdisk_new_part_num" -gt 4 ]; then
        log "SAFETY: MBR table - new partition would be #$sfdisk_new_part_num (max 4)"
        return 1
    fi

    # Snapshot existing partition boundaries for safety verification
    local pre_parts
    pre_parts=$(parted -s "$device" unit MB print 2>/dev/null \
                | grep "^ [0-9]" | sort -n | awk '{print $1 ":" $2 ":" $3}')

    # ── Find where existing data ends on disk ────────────────────────────
    local used_end_sector=0

    if command -v sfdisk >/dev/null 2>&1; then
        local sector_line
        while IFS= read -r sector_line; do
            local s_start s_size s_end
            s_start=$(echo "$sector_line" | sed -n 's/.*start=\s*\([0-9]*\).*/\1/p')
            s_size=$(echo "$sector_line" | sed -n 's/.*size=\s*\([0-9]*\).*/\1/p')
            if [ -n "$s_start" ] && [ -n "$s_size" ]; then
                s_end=$((s_start + s_size))
                [ "$s_end" -gt "$used_end_sector" ] && used_end_sector=$s_end
            fi
        done < <(sfdisk -d "$device" 2>/dev/null | grep "^/")
    fi

    # Fallback: use parted to find end of last partition
    if [ "$used_end_sector" -eq 0 ] && [ "$last_part_num" -gt 0 ]; then
        local last_end_mb
        last_end_mb=$(parted -s "$device" unit MB print 2>/dev/null \
                      | grep "^ ${last_part_num}" | awk '{print $3}' | sed 's/MB//')
        last_end_mb="${last_end_mb%%.*}"
        if [ "${last_end_mb:-0}" -gt 0 ]; then
            # Convert MB to sectors (512 byte sectors)
            used_end_sector=$((last_end_mb * 2048))
            log "Debug: Fallback – last partition ends at ${last_end_mb} MB (sector $used_end_sector)"
        fi
    fi

    if [ "$used_end_sector" -eq 0 ]; then
        log "ERROR: Cannot determine where existing partitions end on $device"
        return 1
    fi

    # Align start to 1MB boundary (2048 sectors)
    local new_start=$(( ((used_end_sector + 2047) / 2048) * 2048 ))
    local disk_sectors
    disk_sectors=$(blockdev --getsz "$device" 2>/dev/null || echo "0")
    local avail_sectors=$((disk_sectors - new_start))

    # Need at least MIN_PERSIST_MB (1 GB)
    local avail_mb=$((avail_sectors / 2048))
    if [ "$disk_sectors" -eq 0 ] || [ "$avail_mb" -lt "$MIN_PERSIST_MB" ]; then
        log "Insufficient free space: ${avail_mb} MB available, need $MIN_PERSIST_MB MB"
        return 1
    fi

    log "Creating partition #$sfdisk_new_part_num at sector $new_start (${avail_mb} MB free)"

    # ── Create the partition using sfdisk (preferred) or parted ───────────
    local persist_dev="${device}${part_suffix}${new_part_num}"
    local created=false

    if command -v sfdisk >/dev/null 2>&1; then
        local sfdisk_input
        if [ "$table_type" = "gpt" ]; then
            sfdisk_input="$sfdisk_new_part_num : start=$new_start, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4"
        else
            sfdisk_input="$sfdisk_new_part_num : start=$new_start, type=83"
        fi
        log "Debug: sfdisk input: $sfdisk_input"

        local sfdisk_result
        if sfdisk_result=$(echo "$sfdisk_input" | sfdisk --append --no-reread "$device" 2>&1); then
            log "sfdisk append succeeded: $sfdisk_result"
            created=true
        else
            log "WARNING: sfdisk append failed: $sfdisk_result – falling back to parted"
        fi
    fi

    if [ "$created" != true ]; then
        local last_part_end_mb=$(( new_start / 2048 ))
        log "Command: parted -s $device mkpart primary ext4 ${last_part_end_mb}MB 100%"
        local parted_output
        parted_output=$(parted -s "$device" mkpart primary ext4 "${last_part_end_mb}MB" 100% 2>&1) || {
            log "ERROR: parted mkpart failed: $parted_output"
            return 1
        }
        [ -n "$parted_output" ] && log "parted output: $parted_output"
    fi

    # Settle devices and wait for new partition node
    sleep 2
    partprobe "$device" 2>/dev/null || true
    udevadm settle --timeout=10 2>/dev/null || true

    # Wait for device node to appear
    local wait_count=0
    while [ ! -b "$persist_dev" ] && [ "$wait_count" -lt 10 ]; do
        sleep 1
        wait_count=$((wait_count + 1))
        log "Debug: Waiting for $persist_dev... ($wait_count/10)"
    done

    # Manual device node creation if udev didn't create it
    if [ ! -b "$persist_dev" ]; then
        local base_dev_name
        base_dev_name=$(basename "$device")
        local part_name="${base_dev_name}${part_suffix}${new_part_num}"
        local sysfs_path="/sys/block/${base_dev_name}/${part_name}/dev"
        if [ -f "$sysfs_path" ]; then
            local s_major s_minor
            s_major=$(cut -d: -f1 < "$sysfs_path" | tr -d '[:space:]')
            s_minor=$(cut -d: -f2 < "$sysfs_path" | tr -d '[:space:]')
            log "Debug: Creating device node $persist_dev manually ($s_major:$s_minor)"
            mknod "$persist_dev" b "$s_major" "$s_minor" 2>/dev/null || true
        fi
    fi

    if [ ! -b "$persist_dev" ]; then
        log "ERROR: Device node $persist_dev not found after partition creation"
        return 1
    fi

    # Safety: verify existing partitions were not modified
    local post_part_count
    post_part_count=$(parted -s "$device" print 2>/dev/null | grep -c "^ [0-9]")
    log "Debug: Partition count after: ${post_part_count:-0}"

    local post_pre_parts
    post_pre_parts=$(parted -s "$device" unit MB print 2>/dev/null \
                     | grep "^ [0-9]" | sort -n | head -n "$last_part_num" \
                     | awk '{print $1 ":" $2 ":" $3}')
    if [ "$pre_parts" != "$post_pre_parts" ]; then
        log "WARNING: Existing partition boundaries changed after mkpart!"
    fi

    # Format as ext4
    log "Formatting ${persist_dev} as ext4 with label '$PERSIST_LABEL'"
    mkfs.ext4 -F -L "$PERSIST_LABEL" -E lazy_itable_init=0,lazy_journal_init=0 -m 1 "$persist_dev" 2>&1 || {
        log "ERROR: mkfs.ext4 failed on $persist_dev"
        return 1
    }

    sleep 2
    udevadm settle --timeout=10 2>/dev/null || true

    # Verify the label was written correctly
    local written_label
    written_label=$(blkid -s LABEL -o value "$persist_dev" 2>/dev/null)
    if [ "$written_label" != "$PERSIST_LABEL" ]; then
        log "WARNING: Label verification failed (expected '$PERSIST_LABEL', got '$written_label')"
    fi

    log "Created and formatted $persist_dev"
    echo "$persist_dev"
}

# ── Install init script + systemd unit INTO the persistence partition ────────

install_persist_files() {
    log "Installing persistence init script and systemd unit into $PERSIST_MOUNT"

    # ── init script ──────────────────────────────────────────────────────
    cat > "$PERSIST_MOUNT/mados-persist-init.sh" << 'INITEOF'
#!/usr/bin/env bash
# madOS Persistence Init – called by mados-persistence.service on every boot.
# Mounts the persistence partition, sets up overlayfs for /etc /usr /var /opt,
# and bind-mounts /home.
#
# SAFETY: Only searches the recorded boot device for the persistence partition.
# The boot device is saved in /mnt/persistence/.mados-boot-device during first
# setup so that we never accidentally mount a partition from another disk.
set -euo pipefail

PERSIST_LABEL="persistence"
PERSIST_MOUNT="/mnt/persistence"
OVERLAY_DIRS="etc usr var opt"
LOG_FILE="/var/log/mados-persistence.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [init] $*" | tee -a "$LOG_FILE" >&2; }

# Find partition by label, restricted to a specific parent device when provided.
find_persist_dev() {
    local parent_device="${1:-}"
    local dev=""

    if [ -n "$parent_device" ] && [ -b "$parent_device" ]; then
        # Only search partitions belonging to the parent device
        dev=$(lsblk -nlo NAME,LABEL "$parent_device" 2>/dev/null \
            | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1)
        if [ -z "$dev" ] && command -v blkid >/dev/null 2>&1; then
            local part
            for part in $(lsblk -nlo NAME "$parent_device" 2>/dev/null \
                          | tail -n +2 | awk '{print "/dev/" $1}'); do
                if [ -b "$part" ]; then
                    local label
                    label=$(blkid -s LABEL -o value "$part" 2>/dev/null)
                    if [ "$label" = "$PERSIST_LABEL" ]; then
                        dev="$part"
                        break
                    fi
                fi
            done
        fi
    else
        # No parent device specified – search all devices (fallback)
        dev=$(lsblk -nlo NAME,LABEL 2>/dev/null \
            | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1)
        if [ -z "$dev" ] && command -v blkid >/dev/null 2>&1; then
            dev=$(blkid -L "$PERSIST_LABEL" 2>/dev/null)
        fi
    fi
    echo "$dev"
}

# Try to read the recorded boot device from a previously mounted persistence
# partition, or from /run/mados.
boot_device=""
if mountpoint -q "$PERSIST_MOUNT" 2>/dev/null && \
   [ -f "$PERSIST_MOUNT/.mados-boot-device" ]; then
    boot_device=$(cat "$PERSIST_MOUNT/.mados-boot-device" 2>/dev/null)
fi

persist_dev=$(find_persist_dev "$boot_device")
if [ -z "$persist_dev" ]; then
    log "No partition with label '$PERSIST_LABEL' found – skipping"
    exit 0
fi

# Mount persistence partition if not already mounted
if ! mountpoint -q "$PERSIST_MOUNT" 2>/dev/null; then
    mkdir -p "$PERSIST_MOUNT"
    mount -o noatime,commit=60,data=writeback,barrier=0 "$persist_dev" "$PERSIST_MOUNT" || { log "Failed to mount $persist_dev"; exit 1; }
    log "Mounted $persist_dev at $PERSIST_MOUNT with USB-optimized options"
fi

# Re-read boot device after mount (it's stored inside the partition)
if [ -f "$PERSIST_MOUNT/.mados-boot-device" ]; then
    boot_device=$(cat "$PERSIST_MOUNT/.mados-boot-device" 2>/dev/null)
    # Verify the persistence partition actually belongs to the recorded boot device
    local_parent=$(lsblk -ndo PKNAME "$persist_dev" 2>/dev/null)
    if [ -n "$boot_device" ] && [ -n "$local_parent" ] && \
       [ "/dev/$local_parent" != "$boot_device" ]; then
        log "SAFETY: Persistence partition $persist_dev belongs to /dev/$local_parent but boot device is $boot_device – skipping"
        umount "$PERSIST_MOUNT" 2>/dev/null || true
        exit 0
    fi
fi

# ── overlayfs for /etc /usr /var /opt ────────────────────────────────────
for dir in $OVERLAY_DIRS; do
    upper="$PERSIST_MOUNT/overlays/$dir/upper"
    work="$PERSIST_MOUNT/overlays/$dir/work"
    mkdir -p "$upper" "$work"

    if mountpoint -q "/$dir" 2>/dev/null && \
       findmnt -n -t overlay "/$dir" >/dev/null 2>&1; then
        log "/$dir already has overlay – skipping"
        continue
    fi

    mount -t overlay overlay \
        -o "lowerdir=/$dir,upperdir=$upper,workdir=$work" \
        "/$dir" \
        && log "Overlay mounted for /$dir" \
        || log "WARNING: overlay mount failed for /$dir"
done

# ── ldconfig after /usr overlay ──────────────────────────────────────────
if command -v ldconfig >/dev/null 2>&1; then
    ldconfig
    log "ldconfig completed"
fi

# ── bind mount /home ─────────────────────────────────────────────────────
home_persist="$PERSIST_MOUNT/home"
mkdir -p "$home_persist"

# If persistent /home is empty, seed it with current /home contents
if [ -z "$(ls -A "$home_persist" 2>/dev/null)" ] && \
   [ -d /home ] && [ "$(ls -A /home 2>/dev/null)" ]; then
    cp -a /home/. "$home_persist/" 2>/dev/null && \
        log "Seeded persistent /home with current contents" || \
        log "WARNING: Failed to seed persistent /home"
fi

if ! mountpoint -q /home 2>/dev/null || \
   ! findmnt -n -o SOURCE /home 2>/dev/null | grep -q "$PERSIST_MOUNT"; then
    mount --bind "$home_persist" /home \
        && log "Bind-mounted $home_persist -> /home" \
        || log "WARNING: bind mount for /home failed"
fi

# Store device info for status queries
mkdir -p /run/mados; chmod 700 /run/mados
echo "$persist_dev" > /run/mados/persist_device
chmod 600 /run/mados/persist_device

# ── Restart network services to pick up persistent /etc configs ──────────
if systemctl is-active --quiet iwd.service 2>/dev/null; then
    systemctl restart iwd.service 2>/dev/null || log "WARNING: Failed to restart iwd.service"
    log "Restarted iwd.service to pick up persistent configuration"
fi

log "Persistence init complete"
INITEOF
    chmod 755 "$PERSIST_MOUNT/mados-persist-init.sh"

    # ── systemd unit ─────────────────────────────────────────────────────
    cat > "$PERSIST_MOUNT/mados-persistence.service" << 'UNITEOF'
[Unit]
Description=madOS Overlayfs Persistence
After=local-fs.target systemd-udevd.service
Before=display-manager.service multi-user.target getty@tty1.service
ConditionPathExists=/run/archiso

[Service]
Type=oneshot
ExecStart=/mnt/persistence/mados-persist-init.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNITEOF
    chmod 644 "$PERSIST_MOUNT/mados-persistence.service"

    log "Persistence files installed in $PERSIST_MOUNT"
}

# ── Main setup ───────────────────────────────────────────────────────────────

setup_persistence() {
    ui_header
    log "Starting madOS persistence setup..."

    # ── Step 1: Detect boot device ───────────────────────────────────────
    # Wait for udev to settle so device nodes are available
    udevadm settle --timeout=30 2>/dev/null || true

    ui_step "Detecting boot device"
    local iso_device
    iso_device=$(find_iso_device)

    if [ -z "$iso_device" ]; then
        ui_fail "Could not determine boot device"
        log "Debug: /run/archiso/bootmnt exists=$([ -d /run/archiso/bootmnt ] && echo yes || echo no)"
        log "Debug: findmnt output=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null || echo 'N/A')"
        log "Debug: lsblk labels=$(lsblk -nlo NAME,LABEL 2>/dev/null | grep -iE '(ARCHISO|MADOS)' || echo 'none')"
        return 1
    fi

    if ! [ -b "$iso_device" ]; then
        ui_fail "$iso_device is not a block device"
        return 1
    fi

    if is_optical_device "$iso_device"; then
        ui_skip "Optical media detected – persistence not available"
        return 0
    fi

    local is_loop=false
    if [[ "$iso_device" == /dev/loop* ]]; then
        is_loop=true
        ui_ok "Loopback device (test mode): $iso_device"
    elif is_usb_device "$iso_device"; then
        ui_ok "USB device: $iso_device"
    else
        local removable_flag
        removable_flag=$(cat "/sys/block/${iso_device#/dev/}/removable" 2>/dev/null || echo "")
        if [ "$removable_flag" = "0" ]; then
            ui_skip "Fixed disk detected – persistence not needed"
            return 0
        fi
        ui_ok "Removable device: $iso_device"
    fi

    # ── Step 2: Check for existing ext4 persistence partition (>1 GB) ────
    ui_step "Checking for persistence partition"
    local persist_dev
    persist_dev=$(find_persist_partition "$iso_device")

    if [ -z "$persist_dev" ]; then
        # ── Step 3: Create ext4 partition in remaining free space ─────────
        local free_space
        free_space=$(get_free_space "$iso_device")

        if [ "${free_space:-0}" -lt "$MIN_PERSIST_MB" ]; then
            ui_fail "Insufficient free space (${free_space:-0} MB < $MIN_PERSIST_MB MB)"
            return 1
        fi

        ui_info "No partition found – creating (${free_space} MB free)..."
        persist_dev=$(create_persist_partition "$iso_device")
        if [ -z "$persist_dev" ]; then
            ui_fail "Partition creation failed"
            return 1
        fi
        ui_ok "Created partition: $persist_dev"
    else
        ui_ok "Found existing partition: $persist_dev"
    fi

    if [ ! -b "$persist_dev" ]; then
        ui_fail "Partition $persist_dev not found as block device"
        return 1
    fi

    # ── Step 4: Mount the ext4 partition ─────────────────────────────────
    ui_step "Mounting persistence partition"
    mkdir -p "$PERSIST_MOUNT"

    if ! mountpoint -q "$PERSIST_MOUNT" 2>/dev/null; then
        sleep 2
        udevadm settle --timeout=10 2>/dev/null || true
        blockdev --flushbufs "$persist_dev" 2>/dev/null || true

        local mount_output
        if ! mount_output=$(mount -o noatime,commit=60,data=writeback,barrier=0 "$persist_dev" "$PERSIST_MOUNT" 2>&1); then
            ui_fail "Failed to mount $persist_dev"
            log "Mount error: $mount_output"
            return 1
        fi
        ui_ok "Mounted at $PERSIST_MOUNT"
    else
        ui_ok "Already mounted at $PERSIST_MOUNT"
    fi

    if [ ! -d "$PERSIST_MOUNT" ] || [ ! -w "$PERSIST_MOUNT" ]; then
        ui_fail "Mount point is not accessible"
        return 1
    fi

    # ── Step 5: First boot – set up overlayfs and move data ──────────────
    if [ -x "$PERSIST_MOUNT/mados-persist-init.sh" ]; then
        # Subsequent boot: just run the init script
        ui_step "Restoring persistent overlays"
        "$PERSIST_MOUNT/mados-persist-init.sh" || {
            ui_warn "Init script returned exit code $?"
        }
        ui_ok "Overlays restored from previous session"
    else
        # First boot: create directory structure and install files
        ui_step "Initialising partition (first boot)"

        for dir in $OVERLAY_DIRS; do
            mkdir -p "$PERSIST_MOUNT/overlays/$dir/upper" \
                     "$PERSIST_MOUNT/overlays/$dir/work" || {
                ui_fail "Failed to create overlay dirs for /$dir"
                return 1
            }
        done
        mkdir -p "$PERSIST_MOUNT/home"
        chmod 755 "$PERSIST_MOUNT"
        ui_ok "Directory structure created"

        # Copy current /home contents to persistence partition
        ui_step "Copying user configuration"
        if [ -d /home ] && [ "$(ls -A /home 2>/dev/null)" ]; then
            cp -a /home/. "$PERSIST_MOUNT/home/" 2>/dev/null && \
                ui_ok "Home contents preserved" || \
                ui_warn "Some home contents could not be copied"
        else
            ui_skip "No existing home contents"
        fi

        # Record the boot device
        echo "$iso_device" > "$PERSIST_MOUNT/.mados-boot-device"
        chmod 644 "$PERSIST_MOUNT/.mados-boot-device"
        log "Boot device recorded: $iso_device"

        # Install init script + service into persistence partition
        ui_step "Installing persistence files"
        install_persist_files || {
            ui_fail "Failed to install persistence files"
            return 1
        }
        ui_ok "Init script and service installed"

        # Run init now to mount overlays immediately
        ui_step "Activating overlays"
        "$PERSIST_MOUNT/mados-persist-init.sh" || {
            ui_warn "Init script returned exit code $?"
        }
        ui_ok "Overlays active: /etc /usr /var /opt /home"
    fi

    # ── Step 6: Confirm partition is mounted and directories are ready ───
    ui_step "Verifying persistence"
    local all_ok=true

    if ! mountpoint -q "$PERSIST_MOUNT" 2>/dev/null; then
        ui_fail "Persistence partition not mounted"
        all_ok=false
    fi

    for dir in $OVERLAY_DIRS; do
        if ! [ -d "$PERSIST_MOUNT/overlays/$dir/upper" ]; then
            ui_warn "Missing overlay directory for /$dir"
            all_ok=false
        fi
    done

    if ! [ -d "$PERSIST_MOUNT/home" ]; then
        ui_warn "Missing persistent /home directory"
        all_ok=false
    fi

    if [ "$all_ok" = true ]; then
        ui_ok "All persistence directories ready"
    fi

    ui_done
    log "Partition: $persist_dev | Mount: $PERSIST_MOUNT | Boot device: $iso_device"
    return 0
}

# Only run in live environment
if [ -d /run/archiso ]; then
    setup_persistence
else
    log "Not running in live environment, skipping"
fi
