#!/bin/bash
# Bluetooth status script for Waybar
# Returns JSON with icon, tooltip, and CSS class based on Bluetooth state
# Only runs if exec-if detects a Bluetooth controller

bt_info=$(bluetoothctl show 2>/dev/null)

if echo "$bt_info" | grep -q 'Powered: yes'; then
    if bluetoothctl devices Connected 2>/dev/null | grep -q '^Device'; then
        echo '{"text": "󰂱", "tooltip": "Bluetooth: connected", "class": "connected"}'
    else
        echo '{"text": "󰂯", "tooltip": "Bluetooth: on", "class": "on"}'
    fi
else
    echo '{"text": "󰂲", "tooltip": "Bluetooth: off", "class": "off"}'
fi
