#!/bin/bash
# =============================================================================
# mados-persist-detect.sh - Persistence State Reader
# =============================================================================
# Reads persistence state written by mados-ventoy-setup.sh and makes
# persistence data available to the system.
#
# State is stored in /run/mados-persist.env with these variables:
#   MADOS_PERSIST_MODE    = cow_device|cow_label|partition|file|none
#   MADOS_PERSIST_DEVICE  = device path or file path
#   MADOS_PERSIST_VENTOY  = 1 if booted via Ventoy, 0 otherwise
#   MADOS_PERSIST_ACTIVE  = 1 if any persistence is active, 0 otherwise
# =============================================================================

STATE_FILE="/run/mados-persist.env"
PERSISTENCE_MOUNT="/mnt/mados-persist"

log() {
    local msg="$1"
    echo "[mados-persist-detect] $msg"
    return 0
}

read_state() {
    if [[ -f "$STATE_FILE" ]]; then
        # shellcheck source=/dev/null
        . "$STATE_FILE"
        return 0
    fi
    return 1
}

mount_persistence_source() {
    local source="$1"
    local target="$PERSISTENCE_MOUNT"

    mkdir -p "$target"

    # If already mounted, skip
    if mountpoint -q "$target" 2>/dev/null; then
        log "Already mounted at $target"
        return 0
    fi

    if [[ "$source" == /dev/* ]]; then
        # Block device - mount directly
        mount -o rw "$source" "$target" 2>/dev/null
        return $?
    elif [[ -f "$source" ]]; then
        # File (.dat) - set up loop device
        local loop_dev
        loop_dev=$(losetup -f --show "$source" 2>/dev/null)
        if [[ -z "$loop_dev" ]]; then
            log "ERROR: Failed to create loop device for $source"
            return 1
        fi
        mount -o rw "$loop_dev" "$target" 2>/dev/null
        return $?
    fi

    log "ERROR: Unknown source type: $source"
    return 1
}

main() {
    log "Reading persistence state..."

    if ! read_state; then
        log "No state file found at $STATE_FILE"
        log "Run mados-ventoy-setup.service first"
        exit 0
    fi

    log "Mode: ${MADOS_PERSIST_MODE:-none}"
    log "Device: ${MADOS_PERSIST_DEVICE:-none}"
    log "Ventoy: ${MADOS_PERSIST_VENTOY:-0}"
    log "Active: ${MADOS_PERSIST_ACTIVE:-0}"

    case "$MADOS_PERSIST_MODE" in
        cow_device|cow_label)
            # Archiso handles this natively via overlay - nothing to do
            log "Archiso overlay persistence is active, no extra setup needed"
            ;;
        partition|file)
            # rsync-based persistence: mount the source for the sync service
            if [[ -n "$MADOS_PERSIST_DEVICE" ]]; then
                if mount_persistence_source "$MADOS_PERSIST_DEVICE"; then
                    log "Persistence source mounted at $PERSISTENCE_MOUNT"
                else
                    log "WARNING: Failed to mount persistence source"
                fi
            fi
            ;;
        none|*)
            log "No persistence active"
            ;;
    esac

    return 0
}

main "$@"
