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
    return 1
}

find_iso_device() {
    local iso_device=""

    if [ -d /run/archiso/bootmnt ]; then
        iso_device=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null \
                     | sed 's/\[.*\]//' | sed 's/p\?[0-9]*$//')
    fi

    if [ -z "$iso_device" ]; then
        iso_device=$(lsblk -nlo NAME,LABEL 2>/dev/null \
                     | grep -iE "(ARCHISO|MADOS)" | head -1 \
                     | awk '{print $1}' | sed 's/[0-9]*$//')
        [ -n "$iso_device" ] && iso_device="/dev/$iso_device"
    fi
    echo "$iso_device"
}

# Find the partition with the ISO filesystem (iso9660)
find_iso_partition() {
    lsblk -nlo NAME,FSTYPE 2>/dev/null \
        | awk '$2 == "iso9660" {print "/dev/" $1}' | head -1
}

find_persist_partition() {
    lsblk -nlo NAME,LABEL 2>/dev/null \
        | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1
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

    local part_suffix=""
    [[ "$device" == *"nvme"* || "$device" == *"mmcblk"* ]] && part_suffix="p"

    local last_part_num
    last_part_num=$(parted -s "$device" print 2>/dev/null \
                    | grep "^ [0-9]" | tail -1 | awk '{print $1}')
    [ -z "$last_part_num" ] && { log "Cannot determine last partition"; return 1; }

    local new_part_num=$((last_part_num + 1))
    local persist_dev="${device}${part_suffix}${new_part_num}"
    local last_part_end
    last_part_end=$(parted -s "$device" unit MB print 2>/dev/null \
                    | grep "^ ${last_part_num}" | awk '{print $3}' | sed 's/MB//')

    log "Creating partition ${new_part_num} starting at ${last_part_end}MB"
    parted -s "$device" mkpart primary ext4 "${last_part_end}MB" 100% 2>/dev/null \
        || { log "parted failed"; return 1; }

    sleep 2; partprobe "$device" 2>/dev/null || true; sleep 1
    udevadm settle 2>/dev/null || true

    [ -b "$persist_dev" ] || { log "$persist_dev not found"; return 1; }

    log "Formatting ${persist_dev} as ext4 with label '$PERSIST_LABEL'"
    mkfs.ext4 -F -L "$PERSIST_LABEL" "$persist_dev" >/dev/null 2>&1 \
        || { log "mkfs.ext4 failed"; return 1; }

    log "Created $persist_dev"
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
set -euo pipefail

PERSIST_LABEL="persistence"
PERSIST_MOUNT="/mnt/persistence"
OVERLAY_DIRS="etc usr var opt"
LOG_FILE="/var/log/mados-persistence.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [init] $*" | tee -a "$LOG_FILE"; }

# Find partition by label
find_persist_dev() {
    lsblk -nlo NAME,LABEL 2>/dev/null \
        | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1
}

persist_dev=$(find_persist_dev)
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
DefaultDependencies=no
After=local-fs.target
Before=display-manager.service multi-user.target
ConditionPathExists=/run/archiso

[Service]
Type=oneshot
ExecStart=/mnt/persistence/mados-persist-init.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=sysinit.target
UNITEOF
    chmod 644 "$PERSIST_MOUNT/mados-persistence.service"

    log "Persistence files installed in $PERSIST_MOUNT"
}

# ── Main setup ───────────────────────────────────────────────────────────────

setup_persistence() {
    log "Starting madOS persistence setup..."

    local iso_device
    iso_device=$(find_iso_device)

    if [ -z "$iso_device" ]; then
        log "Could not determine ISO device, skipping"
        return 1
    fi
    log "ISO device: $iso_device"

    if ! is_usb_device "$iso_device"; then
        log "Device $iso_device is not USB (likely ISO/CD/VM), skipping"
        return 0
    fi
    log "Confirmed USB device"

    # Find or create persistence partition
    local persist_dev
    persist_dev=$(find_persist_partition)

    if [ -z "$persist_dev" ]; then
        log "No persistence partition found"
        local free_space
        free_space=$(get_free_space "$iso_device")
        log "Free space: ${free_space}MB"

        if [ "${free_space:-0}" -lt 100 ]; then
            log "Insufficient free space (<100 MB)"
            return 1
        fi

        persist_dev=$(create_persist_partition "$iso_device")
        [ -z "$persist_dev" ] && { log "Partition creation failed"; return 1; }
        log "Created partition: $persist_dev"
    else
        log "Found existing persistence partition: $persist_dev"
    fi

    # Mount the partition
    mkdir -p "$PERSIST_MOUNT"
    if ! mountpoint -q "$PERSIST_MOUNT" 2>/dev/null; then
        mount "$persist_dev" "$PERSIST_MOUNT" 2>/dev/null \
            || { log "Failed to mount $persist_dev"; return 1; }
    fi
    log "Mounted at $PERSIST_MOUNT"

    # If init script already exists, just run it (subsequent boot)
    if [ -x "$PERSIST_MOUNT/mados-persist-init.sh" ]; then
        log "Init script found – running it (subsequent boot)"
        "$PERSIST_MOUNT/mados-persist-init.sh"
        log "Persistence setup complete (existing)"
        return 0
    fi

    # ── First boot: create directory structure and install files ──────────
    log "First boot – initialising persistence partition"

    for dir in $OVERLAY_DIRS; do
        mkdir -p "$PERSIST_MOUNT/overlays/$dir/upper" \
                 "$PERSIST_MOUNT/overlays/$dir/work"
    done
    mkdir -p "$PERSIST_MOUNT/home"
    chmod 755 "$PERSIST_MOUNT"

    # Install init script + service into persistence partition
    install_persist_files

    # Run init now to mount overlays immediately
    "$PERSIST_MOUNT/mados-persist-init.sh"

    log "Persistence setup complete"
    return 0
}

# Only run in live environment
if [ -d /run/archiso ]; then
    setup_persistence
else
    log "Not running in live environment, skipping"
fi
