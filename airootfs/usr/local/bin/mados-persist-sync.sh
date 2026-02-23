#!/bin/bash
# =============================================================================
# mados-persist-sync.sh - Periodic rsync-based Persistence Service
# =============================================================================
# This service provides "soft" persistence by periodically syncing user data
# between the live system and a mounted persistence partition/file.
#
# It reads state from /run/mados-persist.env (written by mados-ventoy-setup.sh)
# and only runs when:
#   - MADOS_PERSIST_MODE is "partition" or "file" (rsync mode)
#   - The persistence mount at /mnt/mados-persist is available
#
# For cow_device/cow_label modes, archiso handles persistence natively
# and this service is not needed.
#
# Synced directories:
#   /home/         → persist/home/
#   /root/         → persist/root/
#   /etc/mados/    → persist/etc.mados/
# =============================================================================

STATE_FILE="/run/mados-persist.env"
PERSISTENCE_MOUNT="/mnt/mados-persist"
SYNC_INTERVAL=300
LOG_FILE="/var/log/mados-persist.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" 2>/dev/null
}

read_state() {
    if [ -f "$STATE_FILE" ]; then
        # shellcheck source=/dev/null
        . "$STATE_FILE"
        return 0
    fi
    return 1
}

is_rsync_mode() {
    read_state || return 1
    case "$MADOS_PERSIST_MODE" in
        partition|file) return 0 ;;
        *) return 1 ;;
    esac
}

is_persistence_mounted() {
    mountpoint -q "$PERSISTENCE_MOUNT" 2>/dev/null
}

sync_to_persistence() {
    local persist_dir="$PERSISTENCE_MOUNT"

    if ! is_persistence_mounted; then
        log "WARNING: Persistence not mounted at $persist_dir"
        return 1
    fi

    log "Syncing to persistence..."

    # /home - user files and configuration
    rsync -a --delete \
        --exclude='.cache' \
        --exclude='.local/share/Trash' \
        --exclude='.thumbnails' \
        --exclude='.npm/_cacache' \
        /home/ "$persist_dir/home/" 2>/dev/null

    # /root - root configuration
    rsync -a --delete \
        --exclude='.cache' \
        --exclude='.local/share/Trash' \
        /root/ "$persist_dir/root/" 2>/dev/null

    # /etc/mados - madOS configuration
    if [ -d /etc/mados ]; then
        mkdir -p "$persist_dir/etc.mados/"
        rsync -a --delete \
            /etc/mados/ "$persist_dir/etc.mados/" 2>/dev/null
    fi

    log "Sync complete"
    return 0
}

load_from_persistence() {
    local persist_dir="$PERSISTENCE_MOUNT"

    if ! is_persistence_mounted; then
        return 1
    fi

    if [ -z "$(ls -A "$persist_dir" 2>/dev/null)" ]; then
        log "Persistence mount is empty, nothing to load"
        return 1
    fi

    log "Loading persisted data..."

    # /home
    if [ -d "$persist_dir/home" ]; then
        rsync -a "$persist_dir/home/" /home/ 2>/dev/null
        log "Restored /home"
    fi

    # /root
    if [ -d "$persist_dir/root" ]; then
        rsync -a "$persist_dir/root/" /root/ 2>/dev/null
        log "Restored /root"
    fi

    # /etc/mados
    if [ -d "$persist_dir/etc.mados" ]; then
        mkdir -p /etc/mados
        rsync -a "$persist_dir/etc.mados/" /etc/mados/ 2>/dev/null
        log "Restored /etc/mados"
    fi

    return 0
}

start_service() {
    log "=== Starting persistence sync service ==="

    if ! is_rsync_mode; then
        local mode="${MADOS_PERSIST_MODE:-unknown}"
        if [ "$mode" = "cow_device" ] || [ "$mode" = "cow_label" ]; then
            log "Archiso native persistence active, rsync not needed"
        else
            log "No rsync-based persistence configured (mode=$mode)"
        fi
        exit 0
    fi

    if ! is_persistence_mounted; then
        log "Persistence not mounted at $PERSISTENCE_MOUNT, cannot start"
        log "Ensure mados-persistence-detect.service ran successfully"
        exit 1
    fi

    log "Persistence mounted at: $PERSISTENCE_MOUNT"

    # Load previous persisted data
    load_from_persistence

    log "Starting sync loop (every ${SYNC_INTERVAL}s)"

    # Sync periodically (this runs as Type=simple, blocks here)
    while true; do
        sleep "$SYNC_INTERVAL"
        sync_to_persistence
    done
}

stop_service() {
    log "Stopping persistence sync..."
    sync_to_persistence
    log "Final sync complete"
}

case "${1:-start}" in
    start) start_service ;;
    stop)  stop_service ;;
    sync)  sync_to_persistence ;;
    *)     echo "Usage: $0 {start|stop|sync}" ;;
esac
