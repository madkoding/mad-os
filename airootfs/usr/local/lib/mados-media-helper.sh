#!/usr/bin/env bash
# madOS Media Helper
# Shared functions for detecting boot media type and persistence availability.
# Source this file from setup scripts that need to check if persistent storage
# is available before installing software.

# Detect if the system booted from optical media (CD/DVD)
is_optical_media() {
    # Method 1: Check if archiso boot device is an optical drive (sr0, sr1, etc.)
    if [ -d /run/archiso/bootmnt ]; then
        local boot_dev
        boot_dev=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null \
                   | sed 's/\[.*\]//')
        if [[ "$boot_dev" == /dev/sr* ]] || [[ "$boot_dev" == /dev/cdrom* ]]; then
            return 0
        fi
    fi

    # Method 2: Check if the boot device uses iso9660 filesystem on an optical drive
    if [ -d /run/archiso/bootmnt ]; then
        local boot_fstype
        boot_fstype=$(findmnt -n -o FSTYPE /run/archiso/bootmnt 2>/dev/null)
        if [ "$boot_fstype" = "iso9660" ]; then
            local boot_src
            boot_src=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null \
                       | sed 's/\[.*\]//')
            local base_dev=${boot_src%%[0-9]*}
            base_dev=${base_dev%p}  # handle nvme-style names
            if [ -b "$base_dev" ]; then
                local dev_name=${base_dev#/dev/}
                # Check if it's a removable optical device
                local removable="/sys/block/$dev_name/removable"
                local dev_type="/sys/block/$dev_name/device/type"
                if [ -f "$dev_type" ] && [ "$(cat "$dev_type" 2>/dev/null)" = "5" ]; then
                    return 0  # SCSI type 5 = CD-ROM
                fi
                # Check via udevadm
                if command -v udevadm >/dev/null 2>&1; then
                    local id_type
                    id_type=$(udevadm info --query=property --name="$base_dev" 2>/dev/null \
                              | grep "^ID_CDROM=" | cut -d= -f2)
                    [ "$id_type" = "1" ] && return 0
                fi
            fi
        fi
    fi

    # Method 3: Check /proc/sys/dev/cdrom/info for the boot device
    if [ -f /proc/sys/dev/cdrom/info ]; then
        local boot_dev
        if [ -d /run/archiso/bootmnt ]; then
            boot_dev=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null \
                       | sed 's/\[.*\]//')
        fi
        if [ -n "${boot_dev:-}" ]; then
            local dev_name=${boot_dev#/dev/}
            if grep -q "$dev_name" /proc/sys/dev/cdrom/info 2>/dev/null; then
                return 0
            fi
        fi
    fi

    return 1
}

# Check if persistence partition is available and mounted
has_persistence() {
    local persist_mount="${1:-/mnt/persistence}"

    # Check if persistence partition is mounted
    if mountpoint -q "$persist_mount" 2>/dev/null; then
        return 0
    fi

    # Check if a persistence partition exists (even if not mounted yet)
    local persist_dev
    persist_dev=$(lsblk -nlo NAME,LABEL 2>/dev/null \
                  | grep "persistence" | awk '{print "/dev/" $1}' | head -1)
    if [ -z "$persist_dev" ] && command -v blkid >/dev/null 2>&1; then
        persist_dev=$(blkid -L "persistence" 2>/dev/null)
    fi

    [ -n "$persist_dev" ] && return 0
    return 1
}

# Check if the environment supports installing software persistently.
# Returns 0 if software can be installed (writable and persistent),
# returns 1 if on read-only media without persistence.
can_install_software() {
    # Not in live environment – assume installed system (always OK)
    [ ! -d /run/archiso ] && return 0

    # If persistence is available, installations will survive reboots
    has_persistence && return 0

    # If on optical media without persistence, can't persist installations
    if is_optical_media; then
        return 1
    fi

    # USB or other writable media – persistence might be set up later,
    # but installations in tmpfs will be lost. Still allow it since
    # the user might be testing or persistence will be set up soon.
    return 0
}
