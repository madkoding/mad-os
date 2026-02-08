#!/bin/bash
# Toggle DEMO_MODE in mados_installer config

CONFIG="/usr/local/lib/mados_installer/config.py"

if [ ! -f "$CONFIG" ]; then
    echo "Error: $CONFIG not found"
    exit 1
fi

# Check current mode
if grep -q "^DEMO_MODE = True" "$CONFIG"; then
    # Switch to real mode
    sed -i 's/^DEMO_MODE = True/DEMO_MODE = False/' "$CONFIG"
    echo "✅ Switched to REAL INSTALLATION mode"
    echo "⚠️  WARNING: Installer will now make actual changes to disk!"
elif grep -q "^DEMO_MODE = False" "$CONFIG"; then
    # Switch to demo mode
    sed -i 's/^DEMO_MODE = False/DEMO_MODE = True/' "$CONFIG"
    echo "✅ Switched to DEMO mode"
    echo "ℹ️  Installer will simulate installation without disk changes"
else
    echo "Error: Could not find DEMO_MODE variable in $CONFIG"
    exit 1
fi
