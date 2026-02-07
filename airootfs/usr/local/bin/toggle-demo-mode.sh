#!/bin/bash
# Toggle DEMO_MODE in install-mados-gtk.py

INSTALLER="/usr/local/bin/install-mados-gtk.py"

if [ ! -f "$INSTALLER" ]; then
    echo "Error: $INSTALLER not found"
    exit 1
fi

# Check current mode
if grep -q "^DEMO_MODE = True" "$INSTALLER"; then
    # Switch to real mode
    sed -i 's/^DEMO_MODE = True/DEMO_MODE = False/' "$INSTALLER"
    echo "✅ Switched to REAL INSTALLATION mode"
    echo "⚠️  WARNING: Installer will now make actual changes to disk!"
elif grep -q "^DEMO_MODE = False" "$INSTALLER"; then
    # Switch to demo mode
    sed -i 's/^DEMO_MODE = False/DEMO_MODE = True/' "$INSTALLER"
    echo "✅ Switched to DEMO mode"
    echo "ℹ️  Installer will simulate installation without disk changes"
else
    echo "Error: Could not find DEMO_MODE variable in $INSTALLER"
    exit 1
fi
