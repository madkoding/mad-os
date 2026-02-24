#!/usr/bin/env bash
# customize_airootfs.sh - Pre-install Oh My Zsh and OpenCode during ISO build
#
# This script is executed by mkarchiso inside the chroot after packages are
# installed. It pre-installs Oh My Zsh and OpenCode so they are available
# immediately in the live environment without needing network at boot.

set -e

echo "=== madOS: Pre-installing Oh My Zsh and OpenCode ==="

# ── Nordic GTK Theme (from EliverLara/Nordic) ─────────────────────────────
NORDIC_DIR="/usr/share/themes/Nordic"

if [[ -d "$NORDIC_DIR" ]]; then
    echo "✓ Nordic GTK theme already installed"
else
    echo "Installing Nordic GTK theme..."
    NORDIC_BUILD_DIR=$(mktemp -d)
    if git clone --depth=1 https://github.com/EliverLara/Nordic.git "$NORDIC_BUILD_DIR/Nordic" 2>&1; then
        mkdir -p /usr/share/themes
        cp -a "$NORDIC_BUILD_DIR/Nordic" "$NORDIC_DIR"
        # Clean up unnecessary files to save space
        rm -rf "$NORDIC_DIR/.git" "$NORDIC_DIR/.gitignore" "$NORDIC_DIR/Art" "$NORDIC_DIR/LICENSE" "$NORDIC_DIR/README.md" "$NORDIC_DIR/KDE" "$NORDIC_DIR/Wallpaper"
        echo "✓ Nordic GTK theme installed"
    else
        echo "⚠ Failed to clone Nordic GTK theme"
    fi
    [[ -n "$NORDIC_BUILD_DIR" ]] && rm -rf "$NORDIC_BUILD_DIR"
fi

# ── Nordzy Icon Theme (from MolassesLover/Nordzy-icon) ─────────────────────
NORDZY_DIR="/usr/share/icons/Nordzy-dark"

if [[ -d "$NORDZY_DIR" ]]; then
    echo "✓ Nordzy-dark icon theme already installed"
else
    echo "Installing Nordzy-dark icon theme..."
    NORDZY_BUILD_DIR=$(mktemp -d)
    if git clone --depth=1 https://github.com/MolassesLover/Nordzy-icon.git "$NORDZY_BUILD_DIR/Nordzy-icon" 2>&1; then
        cd "$NORDZY_BUILD_DIR/Nordzy-icon"
        bash install.sh -d /usr/share/icons -c dark -t default
        # Clean up build directory
        cd /
        echo "✓ Nordzy-dark icon theme installed"
    else
        echo "⚠ Failed to clone Nordzy icon theme"
    fi
    [[ -n "$NORDZY_BUILD_DIR" ]] && rm -rf "$NORDZY_BUILD_DIR"
fi

# ── Oh My Zsh ────────────────────────────────────────────────────────────
OMZ_DIR="/etc/skel/.oh-my-zsh"

if [[ ! -d "$OMZ_DIR" ]]; then
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
if [[ -d "$OMZ_DIR" && -d /home/mados && ! -d /home/mados/.oh-my-zsh ]]; then
    cp -a "$OMZ_DIR" /home/mados/.oh-my-zsh
    chown -R 1000:1000 /home/mados/.oh-my-zsh
    echo "  → Copied Oh My Zsh to /home/mados"
fi

# Copy to root
if [[ -d "$OMZ_DIR" && ! -d /root/.oh-my-zsh ]]; then
    cp -a "$OMZ_DIR" /root/.oh-my-zsh
    echo "  → Copied Oh My Zsh to /root"
fi

# Copy .zshrc to root if not present
if [[ ! -f /root/.zshrc && -f /etc/skel/.zshrc ]]; then
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
        if [[ -x "$INSTALL_DIR/$OPENCODE_CMD" ]] || command -v "$OPENCODE_CMD" &>/dev/null; then
            echo "✓ OpenCode installed via curl"
        else
            echo "⚠ curl install completed but opencode not found"
        fi
    else
        echo "⚠ curl install failed"
    fi

    # Method 2: npm fallback
    if ! command -v "$OPENCODE_CMD" &>/dev/null && [[ ! -x "$INSTALL_DIR/$OPENCODE_CMD" ]]; then
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

# ── ONLYOFFICE Desktop Editors ────────────────────────────────────────
ONLYOFFICE_APPIMAGE="/opt/onlyoffice/DesktopEditors-x86_64.AppImage"

if [[ -x "$ONLYOFFICE_APPIMAGE" ]]; then
    echo "✓ ONLYOFFICE Desktop Editors already installed"
else
    echo "Installing ONLYOFFICE Desktop Editors..."
    if bash /usr/local/bin/setup-onlyoffice.sh 2>&1; then
        if [[ -x "$ONLYOFFICE_APPIMAGE" ]]; then
            echo "✓ ONLYOFFICE Desktop Editors installed"
        else
            echo "⚠ ONLYOFFICE install completed but AppImage not found (will install at boot)"
        fi
    else
        echo "⚠ ONLYOFFICE install failed (will install at boot)"
    fi
fi

# ── Hide unwanted .desktop entries from application menu ──────────────────
echo "Hiding unwanted application menu entries..."
for desktop_file in \
    /usr/share/applications/xgps.desktop \
    /usr/share/applications/xgpsspeed.desktop \
    /usr/share/applications/pcmanfm-desktop-pref.desktop \
    /usr/share/applications/qv4l2.desktop \
    /usr/share/applications/qvidcap.desktop \
    /usr/share/applications/mpv.desktop; do
    if [[ -f "$desktop_file" ]]; then
        echo -e "[Desktop Entry]\nNoDisplay=true\nHidden=true\nType=Application" > "$desktop_file"
        echo "  → Hidden: $(basename "$desktop_file")"
    fi
done
echo "✓ Unwanted desktop entries hidden"

echo "=== madOS: Pre-installation complete ==="
