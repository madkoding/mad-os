#!/bin/bash

PERSISTENCE_FILE=""
PERSISTENCE_MOUNT="/mnt/mados-persist"

find_persistence_file() {
    local boot_dev="$1"
    
    for file in "$boot_dev/mados-persistence.dat" \
                "$boot_dev/ventoy/mados-persistence.dat" \
                "/isodevice/mados-persistence.dat"; do
        if [ -f "$file" ]; then
            PERSISTENCE_FILE="$file"
            return 0
        fi
    done
    
    for label in "mados-persist" "vtoycow" "casper-rw" "persistence"; do
        local device=$(blkid -L "$label" 2>/dev/null)
        if [ -n "$device" ] && [ -b "$device" ]; then
            PERSISTENCE_FILE="$device"
            return 0
        fi
    done
    
    return 1
}

find_boot_device() {
    local root_dev=""
    
    if [ -f /proc/cmdline ]; then
        local cmdline=$(cat /proc/cmdline)
        
        for param in $cmdline; do
            case "$param" in
                archisosearchuuid=*)
                    local uuid="${param#*=}"
                    root_dev=$(blkid -U "$uuid" 2>/dev/null)
                    break
                    ;;
            esac
        done
    fi
    
    if [ -z "$root_dev" ] && [ -d /run/archiso/bootmnt ]; then
        root_dev=$(df /run/archiso/bootmnt 2>/dev/null | tail -1 | awk '{print $1}')
    fi
    
    if [ -n "$root_dev" ]; then
        local dev_name=$(basename "$root_dev")
        local dev_base="/dev/${dev_name%%[0-9]*}"
        local part_num="${root_dev##*[^0-9]}"
        
        if [ "$part_num" -gt 1 ]; then
            echo "${dev_base}${((part_num - 1))}"
        else
            echo "${dev_base}"
        fi
    fi
}

setup_archiso_persistence() {
    local persist_file="$1"
    
    local cow_device=""
    local cow_label=""
    
    if [[ "$persist_file" == /dev/* ]]; then
        cow_device="$persist_file"
    else
        if [[ "$persist_file" == *.dat ]]; then
            local loop_dev=$(losetup -f --show "$persist_file" 2>/dev/null)
            if [ -n "$loop_dev" ]; then
                cow_device="$loop_dev"
            fi
        fi
        
        if [ -z "$cow_device" ] && [ -f "$persist_file" ]; then
            cow_device="$persist_file"
        fi
    fi
    
    if [ -n "$cow_device" ]; then
        local cow_dir="/run/archiso/cowspace"
        
        if [ ! -d "$cow_dir" ]; then
            cow_dir="/.snapshots"
            mkdir -p "$cow_dir"
        fi
        
        mount --bind "$cow_dir" "$cow_dir" 2>/dev/null || true
        
        export MADOS_PERSISTENCE_DEVICE="$cow_device"
        export MADOS_PERSISTENCE_ACTIVE=1
        
        return 0
    fi
    
    return 1
}

mount_persistence_dat() {
    local source="$1"
    local target="$PERSISTENCE_MOUNT"
    
    mkdir -p "$target"
    
    if [[ "$source" == /dev/* ]]; then
        mount -o rw "$source" "$target"
    else
        local loop_dev=$(losetup -f --show "$source")
        mount -o rw "$loop_dev" "$target"
    fi
    
    echo "$target"
}

main() {
    echo "[mados-persist] Starting persistence detection..."
    
    local boot_dev=$(find_boot_device)
    if [ -z "$boot_dev" ]; then
        echo "[mados-persist] Could not find boot device, using tmpfs mode"
        exit 0
    fi
    
    echo "[mados-persist] Boot device: $boot_dev"
    
    if find_persistence_file "$boot_dev"; then
        echo "[mados-persist] Found persistence: $PERSISTENCE_FILE"
        
        if setup_archiso_persistence "$PERSISTENCE_FILE"; then
            echo "[mados-persist] Archiso persistence configured: $MADOS_PERSISTENCE_DEVICE"
        else
            local persist_dir=$(mount_persistence_dat "$PERSISTENCE_FILE")
            if [ -d "$persist_dir" ]; then
                echo "[mados-persist] Persistence mounted at: $persist_dir"
                export MADOS_PERSISTENCE_DIR="$persist_dir"
            fi
        fi
        
        export MADOS_PERSISTENCE_ACTIVE=1
        echo "[mados-persist] Persistence is active"
    else
        echo "[mados-persist] No persistence file found, using tmpfs mode"
    fi
}

main "$@"
