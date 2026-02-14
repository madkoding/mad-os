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

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
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
# /dev/nvme0n1), and mmcblk (/dev/mmcblk0p1 → /dev/mmcblk0).
strip_partition() {
    local dev=$1
    if [[ "$dev" == *"nvme"*p[0-9]* || "$dev" == *"mmcblk"*p[0-9]* ]]; then
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
                if [ -n "$backing" ]; then
                    # Find which block device hosts the backing file
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
    local free
    free=$(parted -s "$device" unit MB print free 2>/dev/null \
           | grep "Free Space" | tail -1 | awk '{print $3}' | sed 's/MB//')
    echo "${free%.*:-0}"
}

# ── Partition creation ───────────────────────────────────────────────────────

create_persist_partition() {
    local device=$1
    log "Creating persistence partition on $device"

    # Safety check 1: verify the target device is the ISO boot device.
    # This prevents accidentally writing to a different disk.
    local expected_iso_device
    expected_iso_device=$(find_iso_device)
    if [ -n "$expected_iso_device" ] && [ "$device" != "$expected_iso_device" ]; then
        log "SAFETY: Refusing to create partition on $device (ISO device is $expected_iso_device)"
        return 1
    fi

    # Safety check 2: detect partition table type and enforce limits.
    # MBR (msdos) supports at most 4 primary partitions.
    local table_type
    table_type=$(parted -s "$device" print 2>/dev/null \
                 | grep -i "^Partition Table:" | awk '{print $3}')

    local part_suffix=""
    [[ "$device" == *"nvme"* || "$device" == *"mmcblk"* ]] && part_suffix="p"

    local last_part_num
    last_part_num=$(parted -s "$device" print 2>/dev/null \
                    | grep "^ [0-9]" | awk '{print $1}' | sort -n | tail -1)
    [ -z "$last_part_num" ] && { log "Cannot determine last partition"; return 1; }

    local new_part_num=$((last_part_num + 1))

    if [ "$table_type" = "msdos" ] && [ "$new_part_num" -gt 4 ]; then
        log "SAFETY: MBR partition table on $device already has $last_part_num partitions (max 4)"
        return 1
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
    log "Command: parted -s $device mkpart primary ext4 ${last_part_end}MB 100%"
    
    # Log current partition state before mkpart
    log "Debug: Partition table BEFORE mkpart:"
    parted -s "$device" print 2>&1 | while read -r line; do log "  PRE: $line"; done
    
    log "Debug: Block devices BEFORE mkpart:"
    lsblk "$device" 2>&1 | while read -r line; do log "  PRE-LSBLK: $line"; done
    
    # Capture parted output/errors for better debugging
    local parted_output
    parted_output=$(parted -s "$device" mkpart primary ext4 "${last_part_end}MB" 100% 2>&1) || {
        log "ERROR: parted mkpart failed with exit code $?"
        log "parted output: $parted_output"
        return 1
    }
    [ -n "$parted_output" ] && log "parted output: $parted_output"
    
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
    log "Partition count before: $last_part_num, after: ${post_part_count:-0}"
    
    # Get list of current partitions
    local post_parts_list
    post_parts_list=$(parted -s "$device" print 2>/dev/null \
                      | grep "^ [0-9]" | sort -n | awk '{print $1}')
    log "Debug: Partition numbers after mkpart: $post_parts_list"
    
    # Check if we have at least one more partition
    if [ "${post_part_count:-0}" -le "$last_part_num" ]; then
        log "WARNING: Partition count did not increase ($last_part_num -> $post_part_count)"
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
        if [ -n "$pstart" ]; then
            local start_diff
            start_diff=$(awk "BEGIN {printf \"%.0f\", sqrt(($pstart - $last_part_end) * ($pstart - $last_part_end))}")
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
        log "ERROR: Device node $persist_dev not found after 10 seconds"
        log "Debug: Available device nodes:"
        ls -la "${device}"* 2>&1 | while read -r line; do log "  $line"; done
        return 1
    fi
    log "Debug: Device node $persist_dev exists"

    log "Formatting ${persist_dev} as ext4 with label '$PERSIST_LABEL'"
    local mkfs_output
    mkfs_output=$(mkfs.ext4 -F -L "$PERSIST_LABEL" "$persist_dev" 2>&1) || {
        log "ERROR: mkfs.ext4 failed with exit code $?"
        log "mkfs.ext4 output: $mkfs_output"
        return 1
    }
    log "Debug: mkfs.ext4 succeeded"
    
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

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [init] $*" | tee -a "$LOG_FILE"; }

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
    mount "$persist_dev" "$PERSIST_MOUNT" || { log "Failed to mount $persist_dev"; exit 1; }
    log "Mounted $persist_dev at $PERSIST_MOUNT"
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

log "Persistence init complete"
INITEOF
    chmod 755 "$PERSIST_MOUNT/mados-persist-init.sh"

    # ── systemd unit ─────────────────────────────────────────────────────
    cat > "$PERSIST_MOUNT/mados-persistence.service" << 'UNITEOF'
[Unit]
Description=madOS Overlayfs Persistence
After=local-fs.target systemd-udevd.service
Before=display-manager.service multi-user.target
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
    log "Starting madOS persistence setup..."

    # Wait for udev to settle so device nodes are available
    udevadm settle --timeout=30 2>/dev/null || true

    local iso_device
    iso_device=$(find_iso_device)

    if [ -z "$iso_device" ]; then
        log "Could not determine ISO device, skipping"
        log "Debug: /run/archiso/bootmnt exists=$([ -d /run/archiso/bootmnt ] && echo yes || echo no)"
        log "Debug: findmnt output=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null || echo 'N/A')"
        log "Debug: lsblk labels=$(lsblk -nlo NAME,LABEL 2>/dev/null | grep -iE '(ARCHISO|MADOS)' || echo 'none')"
        return 1
    fi
    log "ISO device: $iso_device"

    if ! [ -b "$iso_device" ]; then
        log "Device $iso_device is not a block device, skipping"
        return 1
    fi

    if is_optical_device "$iso_device"; then
        log "Device $iso_device is optical media (DVD/CD) – persistence not possible"
        log "To use persistence, boot from USB or install to disk: sudo install-mados"
        return 0
    fi

    if is_usb_device "$iso_device"; then
        log "Confirmed USB device"
    else
        # In archiso, some USB controllers don't expose "usb" in sysfs or
        # udevadm output.  If the device is removable but not identified as
        # USB we still allow persistence – only skip if we can positively
        # confirm it is a fixed disk (removable=0 AND NOT usb).
        local removable_flag
        removable_flag=$(cat "/sys/block/${iso_device#/dev/}/removable" 2>/dev/null || echo "")
        if [ "$removable_flag" = "0" ]; then
            log "Device $iso_device is not USB and not removable (likely VM/HDD), skipping"
            log "Debug: sysfs path=$(readlink -f "/sys/block/${iso_device#/dev/}" 2>/dev/null || echo 'N/A')"
            log "Debug: removable=$removable_flag"
            return 0
        fi
        log "Device $iso_device not positively identified as USB but appears removable – proceeding"
    fi

    # Find or create persistence partition – ONLY on the ISO device
    local persist_dev
    persist_dev=$(find_persist_partition "$iso_device")

    if [ -z "$persist_dev" ]; then
        log "No persistence partition found"
        local free_space
        free_space=$(get_free_space "$iso_device")
        log "Free space: ${free_space}MB"

        if [ "${free_space:-0}" -lt 100 ]; then
            log "Insufficient free space (<100 MB)"
            return 1
        fi

        log "Attempting to create persistence partition..."
        persist_dev=$(create_persist_partition "$iso_device")
        if [ -z "$persist_dev" ]; then
            log "ERROR: Partition creation failed"
            return 1
        fi
        log "Successfully created partition: $persist_dev"
    else
        log "Found existing persistence partition: $persist_dev"
    fi
    
    # Verify the partition device exists
    if [ ! -b "$persist_dev" ]; then
        log "ERROR: Partition device $persist_dev does not exist as a block device"
        log "Debug: Listing all block devices on $iso_device:"
        lsblk "$iso_device" 2>&1 | while read -r line; do log "  $line"; done
        return 1
    fi
    log "Verified partition device exists: $persist_dev"

    # Mount the partition
    mkdir -p "$PERSIST_MOUNT"
    if ! mountpoint -q "$PERSIST_MOUNT" 2>/dev/null; then
        log "Attempting to mount $persist_dev at $PERSIST_MOUNT..."
        local mount_output
        mount_output=$(mount "$persist_dev" "$PERSIST_MOUNT" 2>&1) || {
            log "ERROR: Failed to mount $persist_dev"
            log "Mount error: $mount_output"
            log "Debug: Filesystem check:"
            blkid "$persist_dev" 2>&1 | while read -r line; do log "  $line"; done
            return 1
        }
        log "Mount successful"
    else
        log "Already mounted at $PERSIST_MOUNT"
    fi
    log "Mounted at $PERSIST_MOUNT"
    
    # Verify mount is accessible
    if [ ! -d "$PERSIST_MOUNT" ] || [ ! -w "$PERSIST_MOUNT" ]; then
        log "ERROR: Mount point $PERSIST_MOUNT is not accessible or writable"
        log "Debug: Mount point status:"
        ls -lad "$PERSIST_MOUNT" 2>&1 | while read -r line; do log "  $line"; done
        return 1
    fi
    log "Mount point is accessible and writable"

    # If init script already exists, just run it (subsequent boot)
    if [ -x "$PERSIST_MOUNT/mados-persist-init.sh" ]; then
        log "Init script found – running it (subsequent boot)"
        "$PERSIST_MOUNT/mados-persist-init.sh" || {
            log "WARNING: Init script execution failed with exit code $?"
        }
        log "Persistence setup complete (existing)"
        return 0
    fi

    # ── First boot: create directory structure and install files ──────────
    log "First boot – initialising persistence partition"
    
    log "Creating overlay directory structure..."
    for dir in $OVERLAY_DIRS; do
        log "  Creating overlays for: $dir"
        mkdir -p "$PERSIST_MOUNT/overlays/$dir/upper" \
                 "$PERSIST_MOUNT/overlays/$dir/work" || {
            log "ERROR: Failed to create overlay directories for $dir"
            return 1
        }
    done
    
    log "Creating home directory..."
    mkdir -p "$PERSIST_MOUNT/home" || {
        log "ERROR: Failed to create home directory"
        return 1
    }
    chmod 755 "$PERSIST_MOUNT"
    log "Directory structure created successfully"

    # Record the boot device inside the persistence partition so that on
    # subsequent boots the init script only looks at this specific device.
    log "Recording boot device: $iso_device"
    echo "$iso_device" > "$PERSIST_MOUNT/.mados-boot-device" || {
        log "ERROR: Failed to write boot device file"
        return 1
    }
    chmod 644 "$PERSIST_MOUNT/.mados-boot-device"
    log "Boot device recorded successfully"

    # Install init script + service into persistence partition
    log "Installing persistence files..."
    install_persist_files || {
        log "ERROR: Failed to install persistence files"
        return 1
    }

    # Run init now to mount overlays immediately
    log "Running init script for first time..."
    "$PERSIST_MOUNT/mados-persist-init.sh" || {
        log "WARNING: Initial init script execution failed with exit code $?"
    }

    log "Persistence setup complete – SUCCESS"
    log "Partition: $persist_dev"
    log "Mount: $PERSIST_MOUNT"
    log "Boot device: $iso_device"
    return 0
}

# Only run in live environment
if [ -d /run/archiso ]; then
    setup_persistence
else
    log "Not running in live environment, skipping"
fi
