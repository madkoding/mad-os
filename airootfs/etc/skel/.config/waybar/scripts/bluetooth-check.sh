#!/bin/bash
# Check if a Bluetooth controller is available for Waybar
# Handles rfkill, module loading, and service startup for MT7921 adapters

# Unblock Bluetooth rfkill (common on MT7921 combo adapters)
rfkill unblock bluetooth 2>/dev/null

# Ensure btusb module is loaded (MT7921 BT uses USB interface)
modprobe btusb 2>/dev/null

if ! systemctl is-active --quiet bluetooth.service 2>/dev/null; then
    systemctl start bluetooth.service 2>/dev/null
    sleep 2
fi

bluetoothctl show 2>/dev/null | grep -q 'Controller'
