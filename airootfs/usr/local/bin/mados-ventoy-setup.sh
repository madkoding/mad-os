#!/bin/bash
# =============================================================================
# mados-ventoy-setup.sh - Persistence Detection & State Writer
# =============================================================================
# This script runs at boot to detect if persistence is available and writes
# state to /run/mados-persist.env for other services to use.
#
# It does NOT create persistence images during boot (the USB is mounted and
# in use, making writes unreliable or impossible).
#
# === PERSISTENCE MODES ===
#
# 1. ARCHISO cow_device (true persistence via boot parameter):
#    - User creates a partition labeled 'mados-persist' on the USB
#    - GRUB "with Persistence" entry auto-detects it via cow_label=
#    - Archiso uses the partition as its overlay → fully transparent
#
# 2. VENTOY native persistence:
#    - User creates .dat file BEFORE booting using Ventoy tools
#    - Ventoy handles the overlay internally
#    - See: https://www.ventoy.net/en/plugin_persistence.html
#
# 3. RSYNC-based persistence (fallback):
#    - If a partition/file labeled 'mados-persist' exists but cow_device
#      was not used, the mados-persist-sync service syncs /home periodically
#
# =============================================================================

CONFIG_FILE="/etc/mados/ventoy-persist.conf"
STATE_FILE="/run/mados-persist.env"

log_info() {
    local msg="$1"
    echo "[mados-persist] $msg"
    return 0
}

log_warn() {
    local msg="$1"
    echo "[mados-persist] WARNING: $msg"
    return 0
}

load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        # shellcheck source=/dev/null
        . "$CONFIG_FILE"
    fi
    return 0
}

is_ventoy_boot() {
    [[ -f /proc/cmdline ]] && grep -q "ventoy" /proc/cmdline
}

is_live_environment() {
    [[ -d /run/archiso ]]
}

# Check if archiso was booted with cow_device= (true persistence)
detect_cow_device() {
    if [[ -f /proc/cmdline ]]; then
        local cmdline
        cmdline=$(cat /proc/cmdline)
        for param in $cmdline; do
            case "$param" in
                cow_device=*)
                    echo "${param#*=}"
                    return 0
                    ;;
                *) ;;
            esac
        done
    fi
    return 1
}

# Check if archiso was booted with cow_label= (true persistence by label)
detect_cow_label() {
    if [[ -f /proc/cmdline ]]; then
        local cmdline
        cmdline=$(cat /proc/cmdline)
        for param in $cmdline; do
            case "$param" in
                cow_label=*)
                    echo "${param#*=}"
                    return 0
                    ;;
                *) ;;
            esac
        done
    fi
    return 1
}

# Look for a partition labeled mados-persist (for rsync-based fallback)
detect_persistence_partition() {
    local device
    device=$(blkid -L "mados-persist" 2>/dev/null)
    if [[ -n "$device" ]] && [[ -b "$device" ]]; then
        echo "$device"
        return 0
    fi
    return 1
}

# Look for persistence .dat files on the boot mount
detect_persistence_file() {
    local boot_mnt="/run/archiso/bootmnt"

    if [[ ! -d "$boot_mnt" ]]; then
        return 1
    fi

    for file in \
        "$boot_mnt/ventoy/persistence/persistence.dat" \
        "$boot_mnt/ventoy/mados-persistence.dat" \
        "$boot_mnt/mados-persistence.dat"; do
        if [[ -f "$file" ]]; then
            echo "$file"
            return 0
        fi
    done

    return 1
}

# Write persistence state to /run/mados-persist.env
# Other services (mados-persist-sync) read this file
write_state() {
    local mode="$1"
    local device="$2"

    mkdir -p "$(dirname "$STATE_FILE")"
    cat > "$STATE_FILE" << EOF
# mados persistence state (auto-generated at boot)
MADOS_PERSIST_MODE="${mode}"
MADOS_PERSIST_DEVICE="${device}"
MADOS_PERSIST_VENTOY=$(is_ventoy_boot && echo "1" || echo "0")
MADOS_PERSIST_ACTIVE=$( [[ "$mode" != "none" ]] && echo "1" || echo "0" )
EOF
    chmod 644 "$STATE_FILE"
    return 0
}

main() {
    load_config

    if ! is_live_environment; then
        log_info "Not in live environment, skipping persistence detection"
        write_state "none" ""
        return 0
    fi

    log_info "Detecting persistence configuration..."

    # Priority 1: archiso cow_device= parameter (real transparent persistence)
    local cow_dev
    cow_dev=$(detect_cow_device)
    if [[ -n "$cow_dev" ]]; then
        log_info "Archiso cow_device persistence ACTIVE: $cow_dev"
        log_info "All changes are saved transparently to the device"
        write_state "cow_device" "$cow_dev"
        return 0
    fi

    # Priority 2: archiso cow_label= parameter (real persistence by label)
    local cow_label
    cow_label=$(detect_cow_label)
    if [[ -n "$cow_label" ]]; then
        local label_dev
        label_dev=$(blkid -L "$cow_label" 2>/dev/null)
        if [[ -n "$label_dev" ]]; then
            log_info "Archiso cow_label persistence ACTIVE: $cow_label -> $label_dev"
            write_state "cow_label" "$label_dev"
            return 0
        else
            log_warn "cow_label=$cow_label specified but no matching partition found"
        fi
    fi

    # Priority 3: Partition labeled mados-persist (for rsync-based sync)
    local persist_part
    persist_part=$(detect_persistence_partition)
    if [[ -n "$persist_part" ]]; then
        log_info "Found persistence partition: $persist_part"
        log_info "rsync-based sync will be used (mados-persist-sync service)"
        write_state "partition" "$persist_part"
        return 0
    fi

    # Priority 4: Persistence .dat file on boot device (rsync-based sync)
    local persist_file
    persist_file=$(detect_persistence_file)
    if [[ -n "$persist_file" ]]; then
        log_info "Found persistence file: $persist_file"
        log_info "rsync-based sync will be used (mados-persist-sync service)"
        write_state "file" "$persist_file"
        return 0
    fi

    # No persistence found
    if is_ventoy_boot; then
        log_info "Booted via Ventoy but no persistence configured"
        log_info "To enable: mados-persistence info"
    else
        log_info "No persistence configured, using tmpfs (changes lost on reboot)"
        log_info "To enable: create a partition labeled 'mados-persist' on the USB"
        log_info "Then boot with 'madOS Live with Persistence' option"
    fi

    write_state "none" ""
    return 0
}

main "$@"
