#!/bin/bash

PERSISTENCE_FILE="/mados-persistence.dat"
PERSISTENCE_MOUNT="/mnt/mados-persist"
SYNC_INTERVAL=300
LOG_FILE="/var/log/mados-persist.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" 2>/dev/null
}

find_persistence_file() {
    if [ -d /run/archiso/bootmnt ]; then
        local boot_dev="/run/archiso/bootmnt"
        
        for file in "${boot_dev}${PERSISTENCE_FILE}" \
                    "${boot_dev}/ventoy${PERSISTENCE_FILE}"; do
            if [ -f "$file" ]; then
                echo "$file"
                return 0
            fi
        done
    fi
    
    for label in "mados-persist" "vtoycow"; do
        local device=$(blkid -L "$label" 2>/dev/null)
        if [ -n "$device" ]; then
            echo "$device"
            return 0
        fi
    done
    
    return 1
}

mount_persistence() {
    local source="$1"
    
    mkdir -p "$PERSISTENCE_MOUNT"
    
    if [[ "$source" == /dev/* ]]; then
        mount -o rw "$source" "$PERSISTENCE_MOUNT"
    else
        local loop_dev=$(losetup -f --show "$source" 2>/dev/null)
        if [ -z "$loop_dev" ]; then
            log "ERROR: Failed to create loop device"
            return 1
        fi
        mount -o rw "$loop_dev" "$PERSISTENCE_MOUNT"
    fi
    
    return $?
}

sync_home_to_persistence() {
    local persist_dir="$PERSISTENCE_MOUNT"
    
    if [ ! -d "$persist_dir" ]; then
        return 1
    fi
    
    log "Syncing to persistence..."
    
    # /home - archivos y configuración de usuario
    rsync -a --delete \
        --exclude='.cache' \
        --exclude='.local/share/Trash' \
        --exclude='.thumbnails' \
        --exclude='.npm/_cacache' \
        --exclude='.node_modules/.cache' \
        /home/ "$persist_dir/home/" 2>/dev/null
    
    # /root - configuración de root
    rsync -a --delete \
        --exclude='.cache' \
        --exclude='.local/share/Trash' \
        /root/ "$persist_dir/root/" 2>/dev/null
    
    # /usr/local - binarios y scripts instalados
    rsync -a --delete \
        --exclude='/bin' \
        --exclude='/sbin' \
        --exclude='/lib' \
        /usr/local/ "$persist_dir/usr.local/" 2>/dev/null
    
    # /var/cache/pacman - paquetes descargados (ahorra bandwidth)
    rsync -a --delete \
        /var/cache/pacman/ "$persist_dir/pacman/pkg/" 2>/dev/null
    
    return $?
}

load_persistence_to_home() {
    local persist_dir="$PERSISTENCE_MOUNT"
    
    if [ ! -d "$persist_dir" ] || [ -z "$(ls -A "$persist_dir" 2>/dev/null)" ]; then
        return 1
    fi
    
    log "Loading persistence..."
    
    # /home
    if [ -d "$persist_dir/home" ]; then
        rsync -a "$persist_dir/home/" /home/ 2>/dev/null
    fi
    
    # /root
    if [ -d "$persist_dir/root" ]; then
        rsync -a "$persist_dir/root/" /root/ 2>/dev/null
    fi
    
    # /usr/local
    if [ -d "$persist_dir/usr.local" ]; then
        rsync -a "$persist_dir/usr.local/" /usr/local/ 2>/dev/null
    fi
    
    # /var/cache/pacman
    if [ -d "$persist_dir/pacman/pkg" ]; then
        mkdir -p /var/cache/pacman/pkg
        rsync -a "$persist_dir/pacman/pkg/" /var/cache/pacman/pkg/ 2>/dev/null
    fi
    
    return $?
}

start_service() {
    log "=== Starting persistence service ==="
    
    local persist_file=$(find_persistence_file)
    
    if [ -z "$persist_file" ]; then
        log "No persistence file found. Persistence disabled."
        return 0
    fi
    
    log "Found: $persist_file"
    
    if ! mount_persistence "$persist_file"; then
        log "Failed to mount. Running without persistence."
        return 1
    fi
    
    log "Persistence mounted at: $PERSISTENCE_MOUNT"
    
    load_persistence_to_home
    
    log "Sync loop started (every ${SYNC_INTERVAL}s)"
    
    while true; do
        sleep "$SYNC_INTERVAL"
        sync_home_to_persistence
    done
}

stop_service() {
    log "Stopping persistence..."
    sync_home_to_persistence
    
    for loop_dev in $(losetup -j "$PERSISTENCE_MOUNT"/* 2>/dev/null | cut -d: -f1); do
        losetup -d "$loop_dev" 2>/dev/null || true
    done
    
    umount "$PERSISTENCE_MOUNT" 2>/dev/null || true
}

case "${1:-start}" in
    start) start_service ;;
    stop)  stop_service ;;
    sync)  sync_home_to_persistence ;;
    *)     echo "Usage: $0 {start|stop|sync}" ;;
esac
