#!/usr/bin/env bash
#
# mados-audio-init.sh - Initialize audio hardware for madOS
#
# This script unmutes ALSA controls and sets sensible default volumes
# for all detected sound cards. It runs at boot via systemd to ensure
# audio works out of the box in both live and installed environments.
#
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

LOG_TAG="mados-audio-init"

log() {
    systemd-cat -t "$LOG_TAG" printf "%s\n" "$1"
}

# Get list of sound card indices
get_card_indices() {
    if [[ -f /proc/asound/cards ]]; then
        sed -n -e 's/^[[:space:]]*\([0-9]\+\)[[:space:]].*/\1/p' /proc/asound/cards
    fi
}

# Unmute and set volume for a control (failures are expected for non-existent controls)
set_control() {
    local card="$1" control="$2" level="$3"
    amixer -c "$card" set "$control" "$level" unmute 2>/dev/null || true
}

# Mute a control
mute_control() {
    local card="$1" control="$2"
    amixer -c "$card" set "$control" "0%" mute 2>/dev/null || true
}

# Switch a control on/off
switch_control() {
    local card="$1" control="$2" state="$3"
    amixer -c "$card" set "$control" "$state" 2>/dev/null || true
}

# Set sensible levels on a single card
init_card() {
    local card="$1"
    log "Initializing audio on card $card"

    # Main output controls
    set_control "$card" "Master" "80%"
    set_control "$card" "Front" "80%"
    set_control "$card" "Master Mono" "80%"
    set_control "$card" "Master Digital" "80%"
    set_control "$card" "Playback" "80%"
    set_control "$card" "Headphone" "100%"
    set_control "$card" "Speaker" "80%"
    set_control "$card" "PCM" "80%"
    set_control "$card" "PCM,1" "80%"
    set_control "$card" "DAC" "80%"
    set_control "$card" "DAC,0" "80%"
    set_control "$card" "DAC,1" "80%"
    set_control "$card" "Digital" "80%"
    set_control "$card" "Wave" "80%"
    set_control "$card" "Music" "80%"
    set_control "$card" "AC97" "80%"
    set_control "$card" "Analog Front" "80%"
    set_control "$card" "Synth" "80%"

    # Ensure playback switches are on
    switch_control "$card" "Master Playback Switch" "on"
    switch_control "$card" "Master Surround" "on"
    switch_control "$card" "Speaker" "on"
    switch_control "$card" "Headphone" "on"
    switch_control "$card" "Audigy Analog/Digital Output Jack" "on"
    switch_control "$card" "SB Live Analog/Digital Output Jack" "on"

    # Via DXS channels
    set_control "$card" "VIA DXS,0" "80%"
    set_control "$card" "VIA DXS,1" "80%"
    set_control "$card" "VIA DXS,2" "80%"
    set_control "$card" "VIA DXS,3" "80%"

    # DRC
    set_control "$card" "Dynamic Range Compression" "80%"

    # Mute inputs by default (security/feedback prevention)
    mute_control "$card" "Mic"
    mute_control "$card" "Internal Mic"
    mute_control "$card" "Rear Mic"
    mute_control "$card" "IEC958"

    # Disable captures that can cause issues
    switch_control "$card" "IEC958 Capture Monitor" "off"
    switch_control "$card" "Headphone Jack Sense" "off"
    switch_control "$card" "Line Jack Sense" "off"
}

# Main
main() {
    log "Starting madOS audio initialization"

    local cards
    cards=$(get_card_indices)

    if [[ -z "$cards" ]]; then
        log "No sound cards detected"
        exit 0
    fi

    for card in $cards; do
        init_card "$card"
    done

    # Store ALSA state so it persists across reboots (installed system)
    if command -v alsactl &>/dev/null; then
        if alsactl store 2>/dev/null; then
            log "ALSA state saved"
        fi
    fi

    log "Audio initialization complete"
}

main "$@"
