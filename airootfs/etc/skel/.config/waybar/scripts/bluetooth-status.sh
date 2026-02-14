#!/bin/bash
# Bluetooth status script for Waybar
# Returns JSON with icon, tooltip, and CSS class based on Bluetooth state
# Only runs if exec-if detects a Bluetooth controller

# Unblock Bluetooth rfkill (common on MT7921 combo adapters)
rfkill unblock bluetooth 2>/dev/null

# Ensure bluetooth.service is running (needed for adapters like MediaTek MT7921)
if ! systemctl is-active --quiet bluetooth.service 2>/dev/null; then
    systemctl start bluetooth.service 2>/dev/null
    sleep 2
fi

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
