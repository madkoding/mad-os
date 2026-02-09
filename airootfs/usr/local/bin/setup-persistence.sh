#!/usr/bin/env bash
# madOS Persistence Setup
# Auto-creates and mounts a persistence partition on the live USB

PERSIST_LABEL="MADOS_PERSIST"
MOUNT_POINT="/run/archiso/cowspace_persistent"
LOG_FILE="/var/log/mados-persistence.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if a device is a USB device
is_usb_device() {
    local device=$1
    
    # Remove /dev/ prefix if present
    device=${device#/dev/}
    
    # Check if device is on USB bus via sysfs
    if [ -e "/sys/block/$device" ]; then
        # Follow the device symlink to check for usb in the path
        local device_path=$(readlink -f "/sys/block/$device" 2>/dev/null)
        if [[ "$device_path" == *"/usb"* ]]; then
            return 0
        fi
    fi
    
    # Alternative: check using udevadm
    if command -v udevadm >/dev/null 2>&1; then
        local id_bus=$(udevadm info --query=property --name="/dev/$device" 2>/dev/null | grep "^ID_BUS=" | cut -d= -f2)
        if [ "$id_bus" = "usb" ]; then
            return 0
        fi
    fi
    
    return 1
}

# Find the device where the ISO is running from
find_iso_device() {
    local iso_device=""
    
    # Check for archiso boot device via mountpoint
    if [ -d /run/archiso/bootmnt ]; then
        iso_device=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null | sed 's/\[.*\]//' | sed 's/p\?[0-9]*$//')
    fi
    
    # Fallback: check mounted devices for ARCHISO or MADOS label
    if [ -z "$iso_device" ]; then
        iso_device=$(lsblk -nlo NAME,LABEL 2>/dev/null | grep -iE "(ARCHISO|MADOS)" | head -1 | awk '{print $1}' | sed 's/[0-9]*$//')
        if [ -n "$iso_device" ]; then
            iso_device="/dev/$iso_device"
        fi
    fi
    
    echo "$iso_device"
}

# Check if persistence partition exists
find_persist_partition() {
    lsblk -nlo NAME,LABEL | grep "$PERSIST_LABEL" | awk '{print "/dev/" $1}' | head -1
}

# Get free space on device (in MB)
get_free_space() {
    local device=$1
    
    # Get unallocated space using parted
    local free_space_output=$(parted -s "$device" unit MB print free 2>/dev/null | grep "Free Space" | tail -1)
    
    if [ -n "$free_space_output" ]; then
        # Extract size in MB
        local size_mb=$(echo "$free_space_output" | awk '{print $3}' | sed 's/MB//')
        echo "${size_mb%.*}"  # Remove decimal part
    else
        echo 0
    fi
}

# Create persistence partition using all free space
create_persist_partition() {
    local device=$1
    
    log "Creating persistence partition on $device"
    
    # Get device info
    local device_type=$(lsblk -ndo TYPE "$device" 2>/dev/null)
    local part_suffix=""
    
    # Determine partition suffix (nvme uses p1, others use 1)
    if [[ "$device" == *"nvme"* ]] || [[ "$device" == *"mmcblk"* ]]; then
        part_suffix="p"
    fi
    
    # Get the last partition number
    local last_part_num=$(parted -s "$device" print 2>/dev/null | grep "^ [0-9]" | tail -1 | awk '{print $1}')
    
    if [ -z "$last_part_num" ]; then
        log "Could not determine last partition number"
        return 1
    fi
    
    local new_part_num=$((last_part_num + 1))
    local persist_dev="${device}${part_suffix}${new_part_num}"
    
    # Get the end of the last partition
    local last_part_end=$(parted -s "$device" unit MB print 2>/dev/null | grep "^ ${last_part_num}" | awk '{print $3}' | sed 's/MB//')
    
    # Create partition using all remaining space
    log "Creating partition ${new_part_num} starting at ${last_part_end}MB"
    
    if ! parted -s "$device" mkpart primary ext4 "${last_part_end}MB" 100% 2>/dev/null; then
        log "Failed to create partition with parted"
        return 1
    fi
    
    # Wait for partition to appear
    sleep 2
    partprobe "$device" 2>/dev/null || true
    sleep 1
    udevadm settle || true
    
    # Verify partition exists
    if [ ! -b "$persist_dev" ]; then
        log "Partition $persist_dev not found after creation"
        return 1
    fi
    
    # Format with ext4
    log "Formatting ${persist_dev} as ext4..."
    if ! mkfs.ext4 -F -L "$PERSIST_LABEL" "$persist_dev" >/dev/null 2>&1; then
        log "Failed to format partition"
        return 1
    fi
    
    log "Successfully created and formatted $persist_dev"
    echo "$persist_dev"
}

# Setup persistence
setup_persistence() {
    log "Starting madOS persistence setup..."
    
    # Find ISO device
    local iso_device=$(find_iso_device)
    
    if [ -z "$iso_device" ]; then
        log "Could not determine ISO device, skipping persistence setup"
        return 1
    fi
    
    log "ISO device detected: $iso_device"
    
    # Check if device is a USB device
    if ! is_usb_device "$iso_device"; then
        log "Device $iso_device is not a USB device (likely ISO/CD/VM), skipping persistence setup"
        log "Persistence is only available when booting from USB devices"
        return 0
    fi
    
    log "Confirmed USB device, proceeding with persistence setup"
    
    # Check for existing persistence partition
    local persist_dev=$(find_persist_partition)
    
    if [ -z "$persist_dev" ]; then
        log "No persistence partition found"
        
        # Check free space
        local free_space=$(get_free_space "$iso_device")
        log "Free space on $iso_device: ${free_space}MB"
        
        if [ "$free_space" -lt 100 ]; then
            log "Insufficient free space (need at least 100MB), skipping persistence"
            return 1
        fi
        
        # Create persistence partition
        persist_dev=$(create_persist_partition "$iso_device")
        
        if [ -z "$persist_dev" ]; then
            log "Failed to create persistence partition"
            return 1
        fi
        
        log "Created persistence partition: $persist_dev"
    else
        log "Found existing persistence partition: $persist_dev"
    fi
    
    # Create mount point
    mkdir -p "$MOUNT_POINT"
    
    # Mount persistence partition
    if mount "$persist_dev" "$MOUNT_POINT" 2>/dev/null; then
        log "Successfully mounted persistence partition at $MOUNT_POINT"
        
        # Create necessary directories in persistence
        mkdir -p "$MOUNT_POINT/upper"
        mkdir -p "$MOUNT_POINT/work"
        
        # Set permissions
        chmod 755 "$MOUNT_POINT"
        
        # Store device info for later use
        echo "$persist_dev" > /tmp/mados_persist_device
        
        log "Persistence setup complete"
        return 0
    else
        log "Failed to mount persistence partition"
        return 1
    fi
}

# Only run if booted from live environment
if [ -d /run/archiso ]; then
    setup_persistence
else
    log "Not running in live environment, skipping"
fi
