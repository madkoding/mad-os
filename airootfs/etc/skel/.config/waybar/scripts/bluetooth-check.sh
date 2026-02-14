#!/bin/bash
# Check if a Bluetooth controller is available for Waybar
# Ensures bluetooth.service is running before checking

if ! systemctl is-active --quiet bluetooth.service 2>/dev/null; then
    systemctl start bluetooth.service 2>/dev/null
    sleep 1
fi

bluetoothctl show 2>/dev/null | grep -q 'Controller'
