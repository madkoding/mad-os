#!/usr/bin/env bash
# customize_airootfs.sh - Pre-install Oh My Zsh and OpenCode during ISO build
#
# This script is executed by mkarchiso inside the chroot after packages are
# installed. It pre-installs Oh My Zsh and OpenCode so they are available
# immediately in the live environment without needing network at boot.

set -e

echo "=== madOS: Pre-installing Oh My Zsh and OpenCode ==="

# ── Oh My Zsh ────────────────────────────────────────────────────────────
OMZ_DIR="/etc/skel/.oh-my-zsh"

if [ ! -d "$OMZ_DIR" ]; then
    echo "Installing Oh My Zsh to /etc/skel..."
    if git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$OMZ_DIR" 2>&1; then
        echo "✓ Oh My Zsh installed to /etc/skel"
    else
        echo "⚠ Failed to clone Oh My Zsh (will install at boot)"
    fi
else
    echo "✓ Oh My Zsh already present in /etc/skel"
fi

# Copy to mados user home if it exists
if [ -d "$OMZ_DIR" ] && [ -d /home/mados ] && [ ! -d /home/mados/.oh-my-zsh ]; then
    cp -a "$OMZ_DIR" /home/mados/.oh-my-zsh
    chown -R 1000:1000 /home/mados/.oh-my-zsh
    echo "  → Copied Oh My Zsh to /home/mados"
fi

# Copy to root
if [ -d "$OMZ_DIR" ] && [ ! -d /root/.oh-my-zsh ]; then
    cp -a "$OMZ_DIR" /root/.oh-my-zsh
    echo "  → Copied Oh My Zsh to /root"
fi

# Copy .zshrc to root if not present
if [ ! -f /root/.zshrc ] && [ -f /etc/skel/.zshrc ]; then
    cp /etc/skel/.zshrc /root/.zshrc
    echo "  → Copied .zshrc to /root"
fi

# ── OpenCode ─────────────────────────────────────────────────────────────
OPENCODE_CMD="opencode"
INSTALL_DIR="/usr/local/bin"

if command -v "$OPENCODE_CMD" &>/dev/null; then
    echo "✓ OpenCode already installed"
else
    echo "Installing OpenCode..."

    # Method 1: curl install script (downloads binary directly)
    if curl -fsSL https://opencode.ai/install | OPENCODE_INSTALL_DIR="$INSTALL_DIR" bash; then
        if [ -x "$INSTALL_DIR/$OPENCODE_CMD" ] || command -v "$OPENCODE_CMD" &>/dev/null; then
            echo "✓ OpenCode installed via curl"
        else
            echo "⚠ curl install completed but opencode not found"
        fi
    else
        echo "⚠ curl install failed"
    fi

    # Method 2: npm fallback
    if ! command -v "$OPENCODE_CMD" &>/dev/null && [ ! -x "$INSTALL_DIR/$OPENCODE_CMD" ]; then
        echo "Trying npm fallback..."
        if command -v npm &>/dev/null; then
            if npm install -g --unsafe-perm opencode-ai 2>&1; then
                echo "✓ OpenCode installed via npm"
            else
                echo "⚠ npm install also failed (will install at boot)"
            fi
        else
            echo "⚠ npm not available (will install at boot)"
        fi
    fi
fi

echo "=== madOS: Pre-installation complete ==="
