#!/usr/bin/env bash
# mados-timezone-detect.sh - Auto-detect and set timezone for live environment
# Strategies (in order):
#   1. Read timezone from existing Linux installation on disk
#   2. Read timezone from Windows registry on NTFS partitions
#   3. IP geolocation (requires network)
#   4. Fall back to UTC
set -euo pipefail

LOG_TAG="mados-timezone"
DETECTED_TZ=""
DETECTED_LOCAL_RTC=false

log() { echo "[${LOG_TAG}] $*"; logger -t "${LOG_TAG}" "$*" 2>/dev/null || true; }

# --- Strategy 1: Read from existing Linux installations ---
detect_from_linux() {
    log "Trying to detect timezone from existing Linux installations..."
    local parts
    parts=$(lsblk -lnpo NAME,FSTYPE 2>/dev/null | awk '$2 ~ /ext[234]|btrfs|xfs/ {print $1}') || return 1
    
    for part in ${parts}; do
        local mnt="/tmp/tz-probe-$$"
        mkdir -p "${mnt}"
        if mount -o ro,noatime "${part}" "${mnt}" 2>/dev/null; then
            # Check /etc/localtime symlink
            if [[ -L "${mnt}/etc/localtime" ]]; then
                local target
                target=$(readlink -f "${mnt}/etc/localtime" 2>/dev/null || true)
                # Extract timezone from path like /usr/share/zoneinfo/America/Santiago
                local tz
                tz=$(echo "${target}" | sed -n 's|.*/zoneinfo/||p')
                if [[ -n "${tz}" && "${tz}" != "UTC" && -f "/usr/share/zoneinfo/${tz}" ]]; then
                    log "Found timezone '${tz}' from Linux partition ${part}"
                    DETECTED_TZ="${tz}"
                    umount "${mnt}" 2>/dev/null || true
                    rmdir "${mnt}" 2>/dev/null || true
                    return 0
                fi
            fi
            # Fallback: check /etc/timezone file
            if [[ -f "${mnt}/etc/timezone" ]]; then
                local tz
                tz=$(head -1 "${mnt}/etc/timezone" 2>/dev/null | tr -d '[:space:]')
                if [[ -n "${tz}" && "${tz}" != "UTC" && -f "/usr/share/zoneinfo/${tz}" ]]; then
                    log "Found timezone '${tz}' from /etc/timezone on ${part}"
                    DETECTED_TZ="${tz}"
                    umount "${mnt}" 2>/dev/null || true
                    rmdir "${mnt}" 2>/dev/null || true
                    return 0
                fi
            fi
            umount "${mnt}" 2>/dev/null || true
        fi
        rmdir "${mnt}" 2>/dev/null || true
    done
    return 1
}

# --- Strategy 2: Read from Windows registry (NTFS partitions) ---
detect_from_windows() {
    log "Trying to detect timezone from Windows installations..."
    local parts
    parts=$(lsblk -lnpo NAME,FSTYPE 2>/dev/null | awk '$2 == "ntfs" {print $1}') || return 1
    
    for part in ${parts}; do
        local mnt="/tmp/tz-probe-win-$$"
        mkdir -p "${mnt}"
        if mount -o ro,noatime -t ntfs3 "${part}" "${mnt}" 2>/dev/null || \
           mount -o ro,noatime -t ntfs "${part}" "${mnt}" 2>/dev/null; then
            # Check if this is a Windows system partition
            if [[ -d "${mnt}/Windows/System32" ]]; then
                # Windows stores RTC as local time
                DETECTED_LOCAL_RTC=true
                log "Detected Windows installation on ${part} - will set local RTC"
                
                # Try to read timezone from Windows registry using hivexget if available
                if command -v hivexget &>/dev/null; then
                    local reg_file="${mnt}/Windows/System32/config/SYSTEM"
                    if [[ -f "${reg_file}" ]]; then
                        local win_tz
                        win_tz=$(hivexget "${reg_file}" 'ControlSet001\Control\TimeZoneInformation' 'TimeZoneKeyName' 2>/dev/null || true)
                        if [[ -n "${win_tz}" ]]; then
                            # Map common Windows timezone names to IANA
                            local iana_tz
                            iana_tz=$(map_windows_tz "${win_tz}")
                            if [[ -n "${iana_tz}" ]]; then
                                log "Found timezone '${iana_tz}' from Windows registry on ${part}"
                                DETECTED_TZ="${iana_tz}"
                                umount "${mnt}" 2>/dev/null || true
                                rmdir "${mnt}" 2>/dev/null || true
                                return 0
                            fi
                        fi
                    fi
                fi
            fi
            umount "${mnt}" 2>/dev/null || true
        fi
        rmdir "${mnt}" 2>/dev/null || true
    done
    
    # If we detected Windows but couldn't get TZ, still return 1 (no TZ found)
    # but DETECTED_LOCAL_RTC is set
    return 1
}

# Map common Windows timezone names to IANA timezone names
map_windows_tz() {
    local win_tz="$1"
    case "${win_tz}" in
        "Pacific Standard Time") echo "America/Los_Angeles" ;;
        "Mountain Standard Time") echo "America/Denver" ;;
        "Central Standard Time") echo "America/Chicago" ;;
        "Eastern Standard Time") echo "America/New_York" ;;
        "Atlantic Standard Time") echo "America/Halifax" ;;
        "SA Pacific Standard Time") echo "America/Bogota" ;;
        "Pacific SA Standard Time") echo "America/Santiago" ;;
        "E. South America Standard Time") echo "America/Sao_Paulo" ;;
        "Argentina Standard Time") echo "America/Argentina/Buenos_Aires" ;;
        "Venezuela Standard Time") echo "America/Caracas" ;;
        "Central America Standard Time") echo "America/Guatemala" ;;
        "Mexico Standard Time") echo "America/Mexico_City" ;;
        "GMT Standard Time") echo "Europe/London" ;;
        "W. Europe Standard Time") echo "Europe/Berlin" ;;
        "Romance Standard Time") echo "Europe/Paris" ;;
        "Central European Standard Time") echo "Europe/Warsaw" ;;
        "FLE Standard Time") echo "Europe/Kiev" ;;
        "Russian Standard Time") echo "Europe/Moscow" ;;
        "China Standard Time") echo "Asia/Shanghai" ;;
        "Tokyo Standard Time") echo "Asia/Tokyo" ;;
        "Korea Standard Time") echo "Asia/Seoul" ;;
        "India Standard Time") echo "Asia/Kolkata" ;;
        "AUS Eastern Standard Time") echo "Australia/Sydney" ;;
        "New Zealand Standard Time") echo "Pacific/Auckland" ;;
        "Hawaiian Standard Time") echo "Pacific/Honolulu" ;;
        "Alaskan Standard Time") echo "America/Anchorage" ;;
        "US Mountain Standard Time") echo "America/Phoenix" ;;
        "Canada Central Standard Time") echo "America/Regina" ;;
        "Newfoundland Standard Time") echo "America/St_Johns" ;;
        "SA Western Standard Time") echo "America/La_Paz" ;;
        "SA Eastern Standard Time") echo "America/Cayenne" ;;
        "Montevideo Standard Time") echo "America/Montevideo" ;;
        "Paraguay Standard Time") echo "America/Asuncion" ;;
        "Cuba Standard Time") echo "America/Havana" ;;
        "US Eastern Standard Time") echo "America/Indianapolis" ;;
        "Central Europe Standard Time") echo "Europe/Budapest" ;;
        "GTB Standard Time") echo "Europe/Bucharest" ;;
        "Turkey Standard Time") echo "Europe/Istanbul" ;;
        "Israel Standard Time") echo "Asia/Jerusalem" ;;
        "Arabian Standard Time") echo "Asia/Dubai" ;;
        "SE Asia Standard Time") echo "Asia/Bangkok" ;;
        "Singapore Standard Time") echo "Asia/Singapore" ;;
        "Taipei Standard Time") echo "Asia/Taipei" ;;
        "W. Australia Standard Time") echo "Australia/Perth" ;;
        "Cen. Australia Standard Time") echo "Australia/Adelaide" ;;
        *) echo "" ;;
    esac
}

# --- Strategy 3: IP geolocation ---
detect_from_geolocation() {
    log "Trying to detect timezone via IP geolocation..."
    
    # Check network connectivity first
    if ! ping -c 1 -W 3 1.1.1.1 &>/dev/null && ! ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
        log "No network connectivity available"
        return 1
    fi
    
    local tz=""
    
    # Try multiple geolocation services
    if command -v curl &>/dev/null; then
        # Try worldtimeapi.org first (returns timezone directly)
        tz=$(curl -sf --max-time 5 "http://worldtimeapi.org/api/ip" 2>/dev/null | \
             grep -o '"timezone":"[^"]*"' | cut -d'"' -f4) || true
        
        # Fallback to ip-api.com
        if [[ -z "${tz}" ]]; then
            tz=$(curl -sf --max-time 5 "http://ip-api.com/json/?fields=timezone" 2>/dev/null | \
                 grep -o '"timezone":"[^"]*"' | cut -d'"' -f4) || true
        fi
        
        # Fallback to ipapi.co
        if [[ -z "${tz}" ]]; then
            tz=$(curl -sf --max-time 5 "https://ipapi.co/timezone/" 2>/dev/null) || true
        fi
    fi
    
    if [[ -n "${tz}" && -f "/usr/share/zoneinfo/${tz}" ]]; then
        log "Detected timezone '${tz}' via IP geolocation"
        DETECTED_TZ="${tz}"
        return 0
    fi
    
    return 1
}

# --- Apply detected timezone ---
apply_timezone() {
    local tz="${1:-UTC}"
    
    log "Applying timezone: ${tz}"
    
    # Set timezone via timedatectl if available
    if command -v timedatectl &>/dev/null; then
        timedatectl set-timezone "${tz}" 2>/dev/null || {
            # Fallback: manually set symlink
            ln -sf "/usr/share/zoneinfo/${tz}" /etc/localtime
            echo "${tz}" > /etc/timezone 2>/dev/null || true
        }
    else
        ln -sf "/usr/share/zoneinfo/${tz}" /etc/localtime
        echo "${tz}" > /etc/timezone 2>/dev/null || true
    fi
    
    # Handle local RTC (Windows dual-boot compatibility)
    if [[ "${DETECTED_LOCAL_RTC}" == "true" ]]; then
        log "Setting hardware clock to local time (Windows dual-boot detected)"
        if command -v timedatectl &>/dev/null; then
            timedatectl set-local-rtc true 2>/dev/null || true
        fi
        # Also adjust hwclock
        hwclock --localtime --hctosys 2>/dev/null || true
    fi
    
    log "Timezone set to: ${tz} (local RTC: ${DETECTED_LOCAL_RTC})"
}

# --- Main ---
main() {
    log "Starting timezone auto-detection..."
    
    # Skip if timezone was already configured (e.g., via kernel parameter)
    local boot_tz
    boot_tz=$(sed -n 's/.*timezone=\([^ ]*\).*/\1/p' /proc/cmdline 2>/dev/null || true)
    if [[ -n "${boot_tz}" && -f "/usr/share/zoneinfo/${boot_tz}" ]]; then
        log "Using timezone from kernel parameter: ${boot_tz}"
        apply_timezone "${boot_tz}"
        exit 0
    fi
    
    # Try detection strategies in order
    if detect_from_linux; then
        apply_timezone "${DETECTED_TZ}"
        exit 0
    fi
    
    if detect_from_windows; then
        apply_timezone "${DETECTED_TZ}"
        exit 0
    fi
    
    if detect_from_geolocation; then
        apply_timezone "${DETECTED_TZ}"
        exit 0
    fi
    
    # If Windows was detected but no TZ found, still handle local RTC
    if [[ "${DETECTED_LOCAL_RTC}" == "true" ]]; then
        log "No timezone detected but Windows found - keeping UTC with local RTC"
        apply_timezone "UTC"
        exit 0
    fi
    
    log "Could not auto-detect timezone, keeping UTC"
    log "You can set it manually: timedatectl set-timezone <YOUR/TIMEZONE>"
    exit 0
}

main "$@"
