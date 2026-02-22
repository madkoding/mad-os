#!/bin/bash

VENTOY_PERSIST_SIZE_MB=4096
MIN_FREE_SPACE_MB=512
PERSISTENCE_LABEL="mados-persist"
PERSISTENCE_FILE="mados-persistence.dat"
VENTOY_JSON="/ventoy/ventoy.json"
CONFIG_FILE="/etc/mados/ventoy-persist.conf"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[Ventoy Auto-Persist]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[Ventoy Auto-Persist]${NC} $1"
}

log_error() {
    echo -e "${RED}[Ventoy Auto-Persist]${NC} $1"
}

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        . "$CONFIG_FILE"
        log_info "Loaded config from $CONFIG_FILE"
        if [ -n "$VENTOY_PERSIST_SIZE_MB" ]; then
            VENTOY_PERSIST_SIZE_MB="${VENTOY_PERSIST_SIZE_MB}"
            log_info "Persistence size: ${VENTOY_PERSIST_SIZE_MB}MB"
        fi
    fi
}

is_ventoy_boot() {
    if [ -f /proc/cmdline ]; then
        local cmdline=$(cat /proc/cmdline)
        if echo "$cmdline" | grep -q "ventoy"; then
            return 0
        fi
    fi
    return 1
}

is_ventoy_usb() {
    local boot_dev="$1"
    
    if [ -d "${boot_dev}/ventoy" ]; then
        return 0
    fi
    
    if is_ventoy_boot; then
        return 0
    fi
    
    for label in "VTOYEFI" "VTOY"; do
        if blkid -L "$label" >/dev/null 2>&1; then
            return 0
        fi
    done
    
    return 1
}

find_ventoy_partition() {
    for label in "VTOYEFI" "VTOY"; do
        local device=$(blkid -L "$label" 2>/dev/null)
        if [ -n "$device" ]; then
            echo "$device"
            return 0
        fi
    done
    
    if [ -d /run/archiso/bootmnt ]; then
        local ventoy_path="/run/archiso/bootmnt"
        if [ -d "$ventoy_path/ventoy" ] || [ -f "$ventoy_path/ventoy/ventoy.json" ]; then
            echo "$ventoy_path"
            return 0
        fi
        
        if is_ventoy_boot; then
            echo "$ventoy_path"
            return 0
        fi
    fi
    
    return 1
}

get_usb_device() {
    local boot_dev="$1"
    
    if [ -b "$boot_dev" ]; then
        local dev_name=$(basename "$boot_dev")
        local dev_base="/dev/${dev_name%%[0-9]*}"
        echo "$dev_base"
        return 0
    elif [ -d "$boot_dev" ]; then
        local device=$(df "$boot_dev" 2>/dev/null | tail -1 | awk '{print $1}')
        if [ -b "$device" ]; then
            local dev_name=$(basename "$device")
            local dev_base="/dev/${dev_name%%[0-9]*}"
            echo "$dev_base"
            return 0
        fi
        
        local mount_device=$(findmnt -n -o SOURCE "$boot_dev" 2>/dev/null)
        if [ -b "$mount_device" ]; then
            local dev_name=$(basename "$mount_device")
            local dev_base="/dev/${dev_name%%[0-9]*}"
            echo "$dev_base"
            return 0
        fi
    fi
    
    return 1
}

get_free_space_mb() {
    local device="$1"
    
    if [ -b "$device" ]; then
        local sector_size=512
        local total_sectors=$(blockdev --getsize64 "$device" 2>/dev/null)
        total_sectors=$((total_sectors / sector_size))
        
        local last_part=$(parted -s "$device" print 2>/dev/null | grep -E "^[0-9]+" | tail -1 | awk '{print $1}')
        
        if [ -z "$last_part" ]; then
            echo "0"
            return 1
        fi
        
        local last_part_start=$(parted -s "$device" unit s print 2>/dev/null | grep -E "^\s*$last_part" | awk '{print $2}' | sed 's/s//')
        local disk_end=$(parted -s "$device" unit s print 2>/dev/null | grep "Disk /dev" | awk '{print $3}' | sed 's/s//')
        
        if [ -z "$last_part_start" ] || [ -z "$disk_end" ]; then
            echo "0"
            return 1
        fi
        
        local free_sectors=$((disk_end - last_part_start))
        local free_mb=$((free_sectors * sector_size / 1024 / 1024))
        
        echo "$free_mb"
        return 0
    fi
    
    echo "0"
    return 1
}

create_persistence_image() {
    local ventoy_path="$1"
    local size_mb="$2"
    local output_file="${ventoy_path}/ventoy/${PERSISTENCE_FILE}"
    
    log_info "Creating persistence image of ${size_mb}MB at $output_file"
    
    mkdir -p "${ventoy_path}/ventoy"
    
    dd if=/dev/zero of="$output_file" bs=1M count="$size_mb" status=progress 2>&1
    
    if [ $? -ne 0 ]; then
        log_error "Failed to create persistence image"
        return 1
    fi
    
    mkfs.ext4 -F -L "$PERSISTENCE_LABEL" "$output_file" >/dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        log_error "Failed to format persistence image"
        rm -f "$output_file"
        return 1
    fi
    
    log_info "Persistence image created successfully"
    return 0
}

find_iso_file() {
    local ventoy_path="$1"
    
    for ext in iso IMG; do
        local iso_file=$(find "$ventoy_path" -maxdepth 3 -iname "*.${ext}" -type f 2>/dev/null | head -1)
        if [ -n "$iso_file" ]; then
            echo "$iso_file"
            return 0
        fi
    done
    
    return 1
}

create_ventoy_json() {
    local ventoy_path="$1"
    local iso_file="$2"
    
    local ventoy_dir="${ventoy_path}/ventoy"
    mkdir -p "$ventoy_dir"
    
    local json_file="${ventoy_dir}/ventoy.json"
    
    local iso_basename
    iso_basename=$(basename "$iso_file")
    
    cat > "$json_file" << EOF
{
    "persistence" : [
        {
            "image": "/ISO/${iso_basename}",
            "backend": "/ventoy/${PERSISTENCE_FILE}"
        }
    ]
}
EOF
    
    log_info "Created ventoy.json at $json_file"
    log_info "ISO: ${iso_basename}"
    log_info "Persistence: ${PERSISTENCE_FILE}"
}

setup_ventoy_persistence() {
    load_config
    
    if [ ! -d /run/archiso ]; then
        log_warn "Not in live environment, skipping Ventoy auto-persistence"
        return 0
    fi
    
    log_info "Starting Ventoy auto-persistence setup..."
    
    if ! is_ventoy_boot; then
        log_info "Not booted via Ventoy (standard USB boot), skipping auto-persistence"
        return 0
    fi
    
    log_info "Ventoy boot detected, searching for Ventoy partition..."
    
    local ventoy_part=$(find_ventoy_partition)
    
    if [ -z "$ventoy_part" ]; then
        log_warn "Not running on Ventoy USB, skipping auto-persistence"
        return 1
    fi
    
    log_info "Ventoy partition found: $ventoy_part"
    
    if ! is_ventoy_usb "$ventoy_part"; then
        log_warn "Not a Ventoy USB, skipping"
        return 1
    fi
    
    local mount_point=""
    if [ -b "$ventoy_part" ]; then
        if mountpoint -q "$ventoy_part" 2>/dev/null; then
            mount_point=$(findmnt -n -o TARGET "$ventoy_part" 2>/dev/null)
        else
            mount_point=$(findmnt -n -o TARGET "$ventoy_part" 2>/dev/null)
            if [ -z "$mount_point" ]; then
                mount_point="/mnt/ventoy"
                mkdir -p "$mount_point"
                mount -o rw "$ventoy_part" "$mount_point" 2>/dev/null
                if [ $? -ne 0 ]; then
                    log_error "Cannot mount Ventoy partition as read-write"
                    return 1
                fi
            fi
        fi
    elif [ -d "$ventoy_part" ]; then
        mount_point="$ventoy_part"
    fi
    
    if [ -z "$mount_point" ]; then
        log_error "Could not determine mount point for Ventoy partition"
        return 1
    fi
    
    log_info "Mount point: $mount_point"
    
    local ro_check_file="${mount_point}/.ventoy_write_test"
    touch "$ro_check_file" 2>/dev/null
    if [ ! -f "$ro_check_file" ]; then
        log_warn "Ventoy partition is read-only, attempting remount..."
        mount -o remount,rw "$mount_point" 2>/dev/null
        touch "$ro_check_file" 2>/dev/null
        if [ ! -f "$ro_check_file" ]; then
            log_error "Cannot write to Ventoy partition. Is this a live ISO booted in read-only mode?"
            return 1
        fi
    fi
    rm -f "$ro_check_file"
    
    local usb_dev=$(get_usb_device "$ventoy_part")
    
    if [ -z "$usb_dev" ]; then
        log_error "Could not determine USB device"
        return 1
    fi
    
    log_info "USB device: $usb_dev"
    
    local persist_file="${mount_point}/ventoy/${PERSISTENCE_FILE}"
    
    if [ -f "$persist_file" ]; then
        log_info "Persistence file already exists: $persist_file"
        return 0
    fi
    
    local free_space=$(get_free_space_mb "$usb_dev")
    
    if [ "$free_space" -lt "$MIN_FREE_SPACE_MB" ]; then
        log_warn "Not enough free space on USB (${free_space}MB available, ${MIN_FREE_SPACE_MB}MB minimum)"
        return 1
    fi
    
    log_info "Free space available: ${free_space}MB"
    
    local size_to_use=$((free_space - 256))
    if [ "$size_to_use" -gt "$VENTOY_PERSIST_SIZE_MB" ]; then
        size_to_use=$VENTOY_PERSIST_SIZE_MB
    fi
    
    if [ "$size_to_use" -lt "$MIN_FREE_SPACE_MB" ]; then
        log_warn "Not enough space after reserving buffer"
        return 1
    fi
    
    log_info "Creating persistence file of ${size_to_use}MB..."
    
    if ! create_persistence_image "$mount_point" "$size_to_use"; then
        return 1
    fi
    
    local iso_file=$(find_iso_file "$mount_point")
    
    if [ -n "$iso_file" ]; then
        log_info "Found ISO: $iso_file"
        create_ventoy_json "$mount_point" "$iso_file"
    else
        log_warn "No ISO file found, creating ventoy.json without ISO reference"
        create_ventoy_json "$mount_point" "/ISO/madOS.iso"
    fi
    
    log_info "Ventoy auto-persistence setup completed successfully!"
    log_info "The system will now use persistence on next boot"
    
    return 0
}

setup_ventoy_persistence
