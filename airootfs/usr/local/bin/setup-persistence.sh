#!/usr/bin/env bash
# madOS Persistence Setup
# Auto-creates persistence partition and installs overlayfs-based persistence.
# Overlayfs directories: /etc, /usr, /var, /opt (overlay) + /home (bind mount).
# The systemd service and init script are stored INSIDE the persistence
# partition so a single command on each boot restores everything.

set -euo pipefail

PERSIST_LABEL="persistence"
PERSIST_MOUNT="/mnt/persistence"
LOG_FILE="/var/log/mados-persistence.log"
OVERLAY_DIRS="etc usr var opt"

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

    # Fallback: check sysfs removable flag (some USB controllers don't
    # expose "usb" in the device path or udevadm, but the kernel still
    # marks the device as removable)
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

    # Check via udevadm for CD-ROM flag
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
            # to find the real block device
            if [[ "$raw_source" == /dev/loop* ]]; then
                local backing
                backing=$(losetup -nO BACK-FILE "$raw_source" 2>/dev/null | head -1)
                if [ -z "$backing" ]; then
                    log "ERROR: Cannot determine backing file for $raw_source"
                    return 1
                fi
                # Validate backing file exists before using df
                if [ ! -f "$backing" ]; then
                    log "ERROR: Backing file does not exist: $backing"
                    return 1
                fi
                # Find which block device hosts the backing file
                local back_dev
                back_dev=$(df --output=source "$backing" 2>/dev/null | tail -1)
                if [ -z "$back_dev" ] || [ "$back_dev" = "Filesystem" ] || [ ! -b "$back_dev" ]; then
                    log "ERROR: Cannot determine backing device for $backing"
                    return 1
                fi
                raw_source="$back_dev"
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

find_persist_partition() {
    local parent_device="${1:-}"
    local dev=""

    if [ -n "$parent_device" ] && [ -b "$parent_device" ]; then
        # Only search partitions that belong to the specified parent device.
        # This ensures we never accidentally use a persistence partition
        # on a different disk.
        dev=$(lsblk -nlo NAME,LABEL "$parent_device" 2>/dev/null \
            | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1)
        # Fallback: check each partition on the parent via blkid
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
    local free="0"

    if [ -z "$device" ] || [ ! -b "$device" ]; then
        log "ERROR: Invalid device: '$device'"
        echo "0"
        return 1
    fi

    local parted_output
    parted_output=$(parted -s "$device" unit MB print free 2>/dev/null) || {
        log "ERROR: parted failed on $device"
        echo "0"
        return 1
    }

    free=$(echo "$parted_output" | grep "Free Space" | tail -1 | awk '{print $3}' | sed 's/MB//')

    if [ -z "$free" ] || ! [[ "$free" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        log "WARNING: No free space detected or invalid value: '$free'"
        echo "0"
        return 1
    fi

    # Remove decimal part if present
    echo "${free%.*}"
}

# ── Partition creation ───────────────────────────────────────────────────────

create_persist_partition() {
    local device=$1
    log "Creating persistence partition on $device"

    # Safety check 1: verify the target device is the ISO boot device.
    # This prevents accidentally writing to a different disk.
    local expected_iso_device
    expected_iso_device=$(find_iso_device)
    if [ -z "$expected_iso_device" ]; then
        log "ERROR: Cannot determine ISO device for safety check"
        return 1
    fi
    if [ "$device" != "$expected_iso_device" ]; then
        log "SAFETY: Refusing to create partition on $device (ISO device is $expected_iso_device)"
        return 1
    fi

    # Safety check 2: detect partition table type and enforce limits.
    # MBR (msdos) supports at most 4 primary partitions.
    local table_type
    table_type=$(parted -s "$device" print 2>/dev/null \
                 | grep -i "^Partition Table:" | awk '{print $3}')

    # Validate partition table type
    case "$table_type" in
        msdos|gpt|unknown) ;;
        *)
            log "ERROR: Unsupported partition table type: '$table_type'"
            return 1
            ;;
    esac

    local part_suffix=""
    [[ "$device" == *"nvme"* || "$device" == *"mmcblk"* || "$device" == *"loop"* ]] && part_suffix="p"

    # Find the highest partition number in the partition table
    local last_part_num
    last_part_num=$(parted -s "$device" print 2>/dev/null \
                    | grep "^ [0-9]" | awk '{print $1}' | sort -n | tail -1)
    if [ -z "$last_part_num" ]; then
        log "No existing partitions found, starting with partition 1"
        last_part_num=0
    fi

    # CRITICAL FIX: Check for existing device partition nodes that may not be
    # in the partition table (e.g., isohybrid ISO with partition 1 outside the table).
    # If we create a partition that parted renumbers to fill a gap, we could
    # overwrite existing data!
    log "Debug: Checking for existing device partition nodes..."
    local highest_dev_part=0

    # Use nullglob to prevent processing literal filenames when no matches exist
    shopt -s nullglob
    local part_nodes=("${device}${part_suffix}"[0-9]* "${device}"[0-9]*)
    shopt -u nullglob

    if [ ${#part_nodes[@]} -eq 0 ]; then
        log "Debug: No existing partition device nodes found"
        highest_dev_part=0
    else
        for part_node in "${part_nodes[@]}"; do
            if [ -b "$part_node" ]; then
                local part_num
                if [[ "$device" == *"nvme"* || "$device" == *"mmcblk"* || "$device" == *"loop"* ]]; then
                    # Extract number after 'p' (e.g., nvme0n1p3 -> 3, loop0p1 -> 1)
                    part_num=$(echo "$part_node" | sed 's/.*p\([0-9]*\)$/\1/')
                else
                    # Extract trailing number (e.g., sda3 -> 3)
                    part_num=$(echo "$part_node" | sed 's/.*[^0-9]\([0-9]*\)$/\1/')
                fi
                if [ -n "$part_num" ] && [ "$part_num" -gt "$highest_dev_part" ]; then
                    highest_dev_part=$part_num
                    log "Debug: Found existing device node: $part_node (partition $part_num)"
                fi
            fi
        done
    fi
    log "Debug: Highest partition number in partition table: $last_part_num"
    log "Debug: Highest partition device node: $highest_dev_part"
    
    # Check for partition number gaps (e.g., partition 1 exists as device but not in table)
    # Build list of partition numbers from the table
    local table_part_nums
    table_part_nums=$(parted -s "$device" print 2>/dev/null \
                     | grep "^ [0-9]" | awk '{print $1}' | sort -n)
    log "Debug: Partition numbers in table: $table_part_nums"
    
    # Check if any device partition numbers are missing from the table
    local has_gap=false
    for dev_num in $(seq 1 "$highest_dev_part"); do
        local dev_path="${device}${part_suffix}${dev_num}"
        if [ -b "$dev_path" ]; then
            if ! echo "$table_part_nums" | grep -q "^${dev_num}$"; then
                log "WARNING: Partition $dev_num exists as device node but NOT in partition table"
                has_gap=true
            fi
        fi
    done
    
    # Use the maximum of partition table and device nodes to avoid conflicts
    local safe_last_part=$last_part_num
    if [ "$highest_dev_part" -gt "$last_part_num" ]; then
        log "WARNING: Found device partition nodes (up to $highest_dev_part) not in partition table (max $last_part_num)"
        log "This indicates isohybrid or special partition layout - using device node numbers for safety"
        safe_last_part=$highest_dev_part
    elif [ "$has_gap" = true ]; then
        log "WARNING: Found partition numbering gaps (devices exist but not in table)"
        log "This indicates isohybrid or special partition layout - using device node numbers for safety"
        safe_last_part=$highest_dev_part
    fi

    local new_part_num=$((safe_last_part + 1))

    if [ "$table_type" = "msdos" ] && [ "$new_part_num" -gt 4 ]; then
        log "SAFETY: MBR partition table on $device already has $safe_last_part partitions (max 4)"
        return 1
    fi
    
    # Detect if we're in a situation where partition numbers don't match
    # (e.g., isohybrid ISO where partition 1 exists as device but not in table)
    local use_sfdisk=false
    if [ "$highest_dev_part" -gt "$last_part_num" ] || [ "$has_gap" = true ]; then
        if command -v sfdisk >/dev/null 2>&1; then
            log "INFO: Will use sfdisk for explicit partition numbering (avoiding parted renumbering)"
            use_sfdisk=true
        else
            log "WARNING: Partition number mismatch detected but sfdisk not available"
            log "Proceeding with parted (may cause renumbering)"
        fi
    fi

    # Safety check 3: snapshot existing partition boundaries so we can
    # verify they were not altered after creating the new partition.
    local pre_parts
    pre_parts=$(parted -s "$device" unit MB print 2>/dev/null \
                | grep "^ [0-9]" | sort -n | awk '{print $1 ":" $2 ":" $3}')

    local persist_dev="${device}${part_suffix}${new_part_num}"
    local last_part_end
    last_part_end=$(parted -s "$device" unit MB print 2>/dev/null \
                    | grep "^ ${last_part_num}" | awk '{print $3}' | sed 's/MB//')

    log "Creating partition ${new_part_num} starting at ${last_part_end}MB"
    
    # Log current partition state before mkpart
    log "Debug: Partition table BEFORE mkpart:"
    parted -s "$device" print 2>&1 | while read -r line; do log "  PRE: $line"; done
    
    log "Debug: Block devices BEFORE mkpart:"
    lsblk "$device" 2>&1 | while read -r line; do log "  PRE-LSBLK: $line"; done
    
    # Create the partition using either sfdisk or parted
    if [ "$use_sfdisk" = true ]; then
        # Use sfdisk for explicit partition number control
        log "Using sfdisk to create partition ${new_part_num}"
        local disk_size_sectors
        disk_size_sectors=$(blockdev --getsz "$device" 2>/dev/null || echo "0")
        log "Debug: Disk size: $disk_size_sectors sectors"
        
        # Get the start sector for the new partition
        local start_sector
        start_sector=$(parted -s "$device" unit s print 2>/dev/null \
                      | grep "^ ${last_part_num}" | awk '{print $3}' | sed 's/s$//')
        # Add 1 sector to start after the last partition
        start_sector=$((start_sector + 1))
        log "Debug: New partition will start at sector $start_sector"
        
        # Create partition using sfdisk (format: start,size,type,bootable)
        # Size of "-" means "use all remaining space"
        # Type 83 is Linux filesystem for MBR
        local sfdisk_cmd
        if [ "$table_type" = "gpt" ]; then
            # GPT: use GUID for Linux filesystem
            sfdisk_cmd="$new_part_num : start=$start_sector, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4"
        else
            # MBR: use type 83 for Linux
            sfdisk_cmd="$new_part_num : start=$start_sector, type=83"
        fi
        
        log "Debug: sfdisk command: echo '$sfdisk_cmd' | sfdisk --no-reread --append $device"
        local sfdisk_output
        sfdisk_output=$(echo "$sfdisk_cmd" | sfdisk --no-reread --append "$device" 2>&1) || {
            log "ERROR: sfdisk failed with exit code $?"
            log "sfdisk output: $sfdisk_output"
            # Fall back to parted if sfdisk fails
            log "Falling back to parted..."
            use_sfdisk=false
        }
        
        if [ "$use_sfdisk" = true ]; then
            log "sfdisk output: $sfdisk_output"
        fi
    fi
    
    # Use parted if sfdisk was not used or failed
    if [ "$use_sfdisk" != true ]; then
        log "Command: parted -s $device mkpart primary ext4 ${last_part_end}MB 100%"
        # Capture parted output/errors for better debugging
        local parted_output
        parted_output=$(parted -s "$device" mkpart primary ext4 "${last_part_end}MB" 100% 2>&1) || {
            log "ERROR: parted mkpart failed with exit code $?"
            log "parted output: $parted_output"
            return 1
        }
        [ -n "$parted_output" ] && log "parted output: $parted_output"
    fi
    
    log "Debug: Immediate partition table after mkpart (before sleep):"
    parted -s "$device" print 2>&1 | while read -r line; do log "  POST-IMM: $line"; done

    sleep 2
    log "Running partprobe..."
    partprobe "$device" 2>&1 | while read -r line; do log "partprobe: $line"; done || true
    sleep 1
    
    log "Running udevadm settle..."
    udevadm settle --timeout=10 2>/dev/null || true
    log "Device update complete"
    
    log "Debug: Partition table AFTER partprobe:"
    parted -s "$device" print 2>&1 | while read -r line; do log "  POST: $line"; done
    
    log "Debug: Block devices AFTER partprobe:"
    lsblk "$device" 2>&1 | while read -r line; do log "  POST-LSBLK: $line"; done

    # Safety check 4: verify the new partition actually appears.
    # Instead of just counting, we check for a NEW partition that wasn't in pre_parts
    local post_part_count
    post_part_count=$(parted -s "$device" print 2>/dev/null \
                      | grep -c "^ [0-9]")
    log "Partition count before: $last_part_num (table) / $safe_last_part (with devices), after: ${post_part_count:-0}"
    
    # Get list of current partitions
    local post_parts_list
    post_parts_list=$(parted -s "$device" print 2>/dev/null \
                      | grep "^ [0-9]" | sort -n | awk '{print $1}')
    log "Debug: Partition numbers after mkpart: $post_parts_list"
    
    # Check if we have at least one more partition (use last_part_num for table-only count)
    if [ "${post_part_count:-0}" -le "$last_part_num" ]; then
        log "WARNING: Partition count in table did not increase ($last_part_num -> $post_part_count)"
        log "This might indicate partition renumbering or creation failure"
    fi
    
    # Find the actual new partition by checking which device node exists
    # that starts at or near last_part_end
    log "Debug: Looking for newly created partition starting near ${last_part_end}MB"
    local found_new_part=""
    local all_parts
    all_parts=$(parted -s "$device" print 2>/dev/null | grep "^ [0-9]" | awk '{print $1}')
    log "Debug: All partition numbers: $all_parts"
    
    for pnum in $all_parts; do
        local pstart psize
        pstart=$(parted -s "$device" unit MB print 2>/dev/null \
                 | grep "^ ${pnum}" | awk '{print $2}' | sed 's/MB//')
        psize=$(parted -s "$device" unit MB print 2>/dev/null \
                | grep "^ ${pnum}" | awk '{print $4}' | sed 's/MB//')
        log "Debug: Partition $pnum: start=${pstart}MB, size=${psize}MB"
        
        # Check if this partition starts at or very near last_part_end
        # (allow 1MB tolerance for alignment)
        if [ -n "$pstart" ] && [[ "$pstart" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            # Calculate absolute difference using bash arithmetic
            local start_diff
            start_diff=$(awk "BEGIN {if ($pstart > $last_part_end) print $pstart - $last_part_end; else print $last_part_end - $pstart}")
            log "Debug: Partition $pnum start difference from expected: ${start_diff}MB"
            
            if [ "$start_diff" -le 2 ]; then
                found_new_part="$pnum"
                log "Debug: Found candidate partition $pnum (starts at ${pstart}MB, expected ${last_part_end}MB)"
                break
            fi
        fi
    done
    
    if [ -z "$found_new_part" ]; then
        log "ERROR: Could not find newly created partition"
        log "Expected partition starting at ${last_part_end}MB"
        return 1
    fi
    
    # Safety check 5: verify existing partitions were not modified by comparing
    # the boundaries of pre-existing partitions
    local post_pre_parts
    post_pre_parts=$(parted -s "$device" unit MB print 2>/dev/null \
                     | grep "^ [0-9]" | sort -n | head -n "$last_part_num" \
                     | awk '{print $1 ":" $2 ":" $3}')
    log "Debug: Comparing pre-existing partition boundaries"
    log "Debug: Before: $pre_parts"
    log "Debug: After:  $post_pre_parts"
    if [ "$pre_parts" != "$post_pre_parts" ]; then
        log "WARNING: Existing partition boundaries changed after mkpart!"
        log "This is unexpected but might be due to partition table reorganization"
    fi
    
    # Update persist_dev to use the actual partition number we found
    persist_dev="${device}${part_suffix}${found_new_part}"
    log "Debug: New partition device should be: $persist_dev"

    # Wait for device node to appear
    log "Debug: Waiting for device node $persist_dev to appear..."
    local wait_count=0
    while [ ! -b "$persist_dev" ] && [ "$wait_count" -lt 10 ]; do
        sleep 1
        wait_count=$((wait_count + 1))
        log "Debug: Waiting for $persist_dev... ($wait_count/10)"
    done
    
    if [ ! -b "$persist_dev" ]; then
        # In container environments, device nodes might not be auto-created by udev
        # Try to create it manually using sysfs information
        local base_dev=$(basename "$device")
        local part_name="${base_dev}${part_suffix}${found_new_part}"
        local sysfs_dev="/sys/block/${base_dev}/${part_name}/dev"
        
        if [ -f "$sysfs_dev" ]; then
            log "Debug: Device node missing but sysfs entry exists at $sysfs_dev"
            local major=$(cut -d: -f1 < "$sysfs_dev" | tr -d '[:space:]')
            local minor=$(cut -d: -f2 < "$sysfs_dev" | tr -d '[:space:]')
            log "Debug: Creating device node $persist_dev manually (major:minor = $major:$minor)"
            mknod "$persist_dev" b "$major" "$minor" 2>/dev/null || {
                log "ERROR: Failed to create device node $persist_dev"
                log "Debug: Available device nodes:"
                ls -la "${device}"* 2>&1 | while read -r line; do log "  $line"; done
                return 1
            }
            log "Debug: Device node $persist_dev created successfully"
        else
            log "ERROR: Device node $persist_dev not found after 10 seconds and no sysfs entry"
            log "Debug: Checked sysfs path: $sysfs_dev"
            log "Debug: Available device nodes:"
            ls -la "${device}"* 2>&1 | while read -r line; do log "  $line"; done
            return 1
        fi
    fi
    log "Debug: Device node $persist_dev exists"

    log "Formatting ${persist_dev} as ext4 with label '$PERSIST_LABEL'"
    local mkfs_output
    # USB-optimized ext4 parameters:
    # -F: Force creation (required for scripted usage)
    # -L: Set volume label for easy identification
    # -E lazy_itable_init=0,lazy_journal_init=0: Complete initialization now (avoid delays later)
    # -m 1: Reduce reserved blocks from 5% to 1% (more usable space)
    # Keep journaling enabled for compatibility with mount options (commit=, data=writeback)
    mkfs_output=$(mkfs.ext4 -F -L "$PERSIST_LABEL" -E lazy_itable_init=0,lazy_journal_init=0 -m 1 "$persist_dev" 2>&1) || {
        local exit_code=$?
        log "ERROR: mkfs.ext4 failed with exit code $exit_code"
        log "mkfs.ext4 output: $mkfs_output"
        log "Attempting to clean up failed partition..."
        parted -s "$device" rm "$found_new_part" 2>/dev/null || true
        return 1
    }
    log "Debug: mkfs.ext4 succeeded with USB-optimized settings"
    
    # Wait for label to propagate
    sleep 2
    udevadm settle --timeout=10 2>/dev/null || true

    # Safety check: verify the label was written correctly.
    log "Debug: Verifying filesystem label..."
    local written_label
    written_label=$(blkid -s LABEL -o value "$persist_dev" 2>/dev/null)
    log "Debug: Label read back: '$written_label' (expected: '$PERSIST_LABEL')"
    if [ "$written_label" != "$PERSIST_LABEL" ]; then
        log "WARNING: Label verification failed (expected '$PERSIST_LABEL', got '$written_label')"
        log "Debug: Full blkid output for $persist_dev:"
        blkid "$persist_dev" 2>&1 | while read -r line; do log "  BLKID: $line"; done
        log "Attempting to continue anyway..."
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

    # SAFETY: Require parent device to prevent mounting wrong partition
    if [ -z "$parent_device" ]; then
        log "ERROR: No parent device specified, cannot safely locate persistence partition"
        echo ""
        return 1
    fi

    if [ ! -b "$parent_device" ]; then
        log "ERROR: Parent device does not exist: $parent_device"
        echo ""
        return 1
    fi

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
    # SAFETY: Verify filesystem type before mounting
    local fs_type
    fs_type=$(blkid -s TYPE -o value "$persist_dev" 2>/dev/null)
    if [ "$fs_type" != "ext4" ]; then
        log "ERROR: $persist_dev has filesystem type '$fs_type', expected ext4"
        exit 1
    fi

    mkdir -p "$PERSIST_MOUNT"
    # USB-optimized mount options for better read performance:
    # - noatime: Don't update access times (reduces write operations on reads)
    # - commit=60: Increase journal commit interval to 60s (default: 5s)
    # - data=writeback: Don't order data writes relative to metadata (faster, less safe)
    # - barrier=0: Disable write barriers (faster on USB, acceptable risk for live system)
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
    if [ ! -d "/$dir" ]; then
        log "ERROR: Lower directory /$dir does not exist, skipping overlay"
        continue
    fi

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
# so that user configurations (from /etc/skel) are preserved across reboots.
if [ -z "$(ls -A "$home_persist" 2>/dev/null)" ] && \
   [ -d /home ] && [ "$(ls -A /home 2>/dev/null)" ]; then
    if cp -a /home/. "$home_persist/" 2>/dev/null; then
        log "Seeded persistent /home with current contents"
    else
        log "ERROR: Failed to seed persistent /home - initial user config may be lost"
        exit 1
    fi
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
# iwd (wireless daemon) needs to be restarted if it was already running
# before the /etc overlay was mounted, so it picks up any persistent config.
if command -v systemctl >/dev/null 2>&1 && \
   systemctl is-active --quiet iwd.service 2>/dev/null; then
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
        log "To use persistence, boot from USB or install to disk: sudo install-mados"
        return 0
    fi

    # Check if device is a loopback device (used in test environments)
    # Loopback devices should be treated like removable devices for testing
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
            log "Debug: sysfs path=$(readlink -f "/sys/block/${iso_device#/dev/}" 2>/dev/null || echo 'N/A')"
            return 0
        fi
        ui_ok "Removable device: $iso_device"
    fi

    # Find or create persistence partition – ONLY on the ISO device
    ui_step "Checking for persistence partition"
    local persist_dev
    persist_dev=$(find_persist_partition "$iso_device")

    # Enhanced detection: force refresh of device metadata to bypass lsblk cache
    # This is critical for detecting partitions on subsequent boots where the
    # kernel cache may be stale
    if [ -z "$persist_dev" ]; then
        log "Debug: Primary detection failed, forcing device metadata refresh"
        udevadm settle --timeout=10 2>/dev/null || true
        partprobe "$iso_device" 2>/dev/null || true
        sleep 1
        
        # Direct scan of all partitions using blkid (bypasses lsblk cache)
        log "Debug: Scanning all partitions on $iso_device for persistence label"
        for part in $(lsblk -nlo NAME "$iso_device" 2>/dev/null | tail -n +2); do
            local full_part="/dev/$part"
            if [ -b "$full_part" ]; then
                local label
                label=$(blkid -s LABEL -o value "$full_part" 2>/dev/null)
                log "Debug: Partition $full_part has label: '$label'"
                if [ "$label" = "$PERSIST_LABEL" ]; then
                    persist_dev="$full_part"
                    ui_info "Found via direct scan: $persist_dev"
                    log "Found existing persistence partition via direct blkid scan: $persist_dev"
                    break
                fi
            fi
        done
    fi
    
    # Additional safeguard: global search for persistence label
    if [ -z "$persist_dev" ] && command -v blkid >/dev/null 2>&1; then
        log "Debug: Attempting global search for persistence label"
        local global_persist
        global_persist=$(blkid -L "$PERSIST_LABEL" 2>/dev/null)
        if [ -n "$global_persist" ] && [ -b "$global_persist" ]; then
            # Verify this partition belongs to our boot device
            local part_parent
            part_parent=$(lsblk -ndo PKNAME "$global_persist" 2>/dev/null)
            if [ "/dev/$part_parent" = "$iso_device" ]; then
                persist_dev="$global_persist"
                ui_info "Found via global search: $persist_dev"
                log "Found existing persistence partition via global blkid search: $persist_dev"
            else
                log "WARNING: Found partition with persistence label ($global_persist) but it belongs to /dev/$part_parent, not $iso_device - ignoring"
            fi
        fi
    fi

    if [ -z "$persist_dev" ]; then
        local free_space
        free_space=$(get_free_space "$iso_device")

        if [ "${free_space:-0}" -lt 100 ]; then
            ui_fail "Insufficient free space (${free_space:-0} MB < 100 MB)"
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
    
    # Verify the partition device exists
    if [ ! -b "$persist_dev" ]; then
        ui_fail "Partition $persist_dev not found as block device"
        log "Debug: Listing all block devices on $iso_device:"
        lsblk "$iso_device" 2>&1 | while read -r line; do log "  $line"; done
        return 1
    fi

    # Wait for device to be fully ready and not busy
    ui_step "Mounting persistence partition"
    log "Waiting for device to be ready for mounting..."
    sleep 3
    udevadm settle --timeout=10 2>/dev/null || true
    blockdev --flushbufs "$persist_dev" 2>/dev/null || true

    # Mount the partition with retry logic
    mkdir -p "$PERSIST_MOUNT"
    if ! mountpoint -q "$PERSIST_MOUNT" 2>/dev/null; then
        local mount_output
        local mount_attempts=0
        local max_attempts=3
        
        while [ $mount_attempts -lt $max_attempts ]; do
            mount_attempts=$((mount_attempts + 1))
            
            # USB-optimized mount options for better read performance:
            # - noatime: Don't update access times (reduces write operations on reads)
            # - commit=60: Increase journal commit interval to 60s (default: 5s)
            # - data=writeback: Don't order data writes relative to metadata (faster, less safe)
            # - barrier=0: Disable write barriers (faster on USB, acceptable risk for live system)
            if mount_output=$(mount -o noatime,commit=60,data=writeback,barrier=0 "$persist_dev" "$PERSIST_MOUNT" 2>&1); then
                ui_ok "Mounted at $PERSIST_MOUNT with USB-optimized options"
                break
            else
                if [ $mount_attempts -lt $max_attempts ]; then
                    ui_warn "Mount attempt $mount_attempts failed, retrying..."
                    log "Mount error: $mount_output"
                    sleep 2
                    blockdev --flushbufs "$persist_dev" 2>/dev/null || true
                else
                    ui_fail "Failed to mount after $max_attempts attempts"
                    log "Mount error: $mount_output"
                    log "Debug: Filesystem check:"
                    blkid "$persist_dev" 2>&1 | while read -r line; do log "  $line"; done
                    log "Debug: Check if device is busy:"
                    lsof "$persist_dev" 2>&1 | while read -r line; do log "  $line"; done || log "  lsof not available or no processes found"
                    fuser -v "$persist_dev" 2>&1 | while read -r line; do log "  $line"; done || log "  fuser not available or no processes found"
                    return 1
                fi
            fi
        done
    else
        ui_ok "Already mounted at $PERSIST_MOUNT"
    fi
    
    # Verify mount is accessible
    if [ ! -d "$PERSIST_MOUNT" ] || [ ! -w "$PERSIST_MOUNT" ]; then
        ui_fail "Mount point is not accessible"
        log "Debug: Mount point status:"
        ls -lad "$PERSIST_MOUNT" 2>&1 | while read -r line; do log "  $line"; done
        return 1
    fi

    # If init script already exists, just run it (subsequent boot)
    if [ -x "$PERSIST_MOUNT/mados-persist-init.sh" ]; then
        ui_step "Restoring persistent overlays"
        "$PERSIST_MOUNT/mados-persist-init.sh" || {
            ui_warn "Init script returned exit code $?"
        }
        ui_ok "Overlays restored from previous session"
        ui_done
        return 0
    fi

    # ── First boot: create directory structure and install files ──────────
    ui_step "Initialising partition (first boot)"
    
    for dir in $OVERLAY_DIRS; do
        mkdir -p "$PERSIST_MOUNT/overlays/$dir/upper" \
                 "$PERSIST_MOUNT/overlays/$dir/work" || {
            ui_fail "Failed to create overlay dirs for /$dir"
            return 1
        }
    done
    
    mkdir -p "$PERSIST_MOUNT/home" || {
        ui_fail "Failed to create home directory"
        return 1
    }
    chmod 755 "$PERSIST_MOUNT"
    ui_ok "Directory structure created"

    # ── Copy current /home contents to persistence partition ─────────────
    ui_step "Copying user configuration"
    if [ -d /home ] && [ "$(ls -A /home 2>/dev/null)" ]; then
        cp -a /home/. "$PERSIST_MOUNT/home/" 2>/dev/null && \
            ui_ok "Home contents preserved" || \
            ui_warn "Some home contents could not be copied"
    else
        ui_skip "No existing home contents"
    fi

    # Record the boot device inside the persistence partition
    echo "$iso_device" > "$PERSIST_MOUNT/.mados-boot-device" || {
        ui_fail "Failed to record boot device"
        return 1
    }
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
    ui_info "Network services restarted to pick up persistent configs"

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
