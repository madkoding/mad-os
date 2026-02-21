#!/usr/bin/env bash
# madOS Media Helper
# Shared functions for detecting boot media type.
# Source this file from setup scripts that need to check if software
# can be installed before proceeding.

# Detect if the system booted from optical media (CD/DVD)
is_optical_media() {
    [[ ! -d /run/archiso/bootmnt ]] && return 1

    # Cache the boot device source (avoids repeated findmnt calls)
    local boot_dev
    boot_dev=$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null \
               | sed 's/\[.*\]//')

    [[ -z "$boot_dev" ]] && return 1

    # Method 1: Check if archiso boot device is an optical drive (sr0, sr1, etc.)
    if [[ "$boot_dev" == /dev/sr* || "$boot_dev" == /dev/cdrom* ]]; then
        return 0
    fi

    # Method 2: Check if the boot device uses iso9660 filesystem on an optical drive
    local boot_fstype
    boot_fstype=$(findmnt -n -o FSTYPE /run/archiso/bootmnt 2>/dev/null)
    if [[ "$boot_fstype" == "iso9660" ]]; then
        local base_dev=${boot_dev%%[0-9]*}
        base_dev=${base_dev%p}  # handle nvme-style names
        if [[ -b "$base_dev" ]]; then
            local dev_name=${base_dev#/dev/}
            # Check SCSI device type (type 5 = CD-ROM)
            local dev_type="/sys/block/$dev_name/device/type"
            if [[ -f "$dev_type" && "$(cat "$dev_type" 2>/dev/null)" == "5" ]]; then
                return 0
            fi
            # Check via udevadm for CD-ROM flag
            if command -v udevadm >/dev/null 2>&1; then
                local id_cdrom
                id_cdrom=$(udevadm info --query=property --name="$base_dev" 2>/dev/null \
                           | grep "^ID_CDROM=" | cut -d= -f2)
                [[ "$id_cdrom" == "1" ]] && return 0
            fi
        fi
    fi

    # Method 3: Check /proc/sys/dev/cdrom/info for the boot device
    if [[ -f /proc/sys/dev/cdrom/info ]]; then
        local dev_name=${boot_dev#/dev/}
        if grep -q "$dev_name" /proc/sys/dev/cdrom/info 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# Check if the environment supports installing software.
# Returns 0 if software can be installed (writable media),
# returns 1 if on read-only media (CD/DVD).
can_install_software() {
    # Not in live environment – assume installed system (always OK)
    [[ ! -d /run/archiso ]] && return 0

    # If on optical media, can't persist installations
    if is_optical_media; then
        return 1
    fi

    # USB or other writable media – allow installation
    return 0
}
