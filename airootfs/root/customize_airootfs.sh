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

# ════════════════════════════════════════════════════════════════════════════
# NVM (Node Version Manager) - para npm a nivel de usuario
# ════════════════════════════════════════════════════════════════════════════
export NVM_DIR="/root/.nvm"

install_nvm() {
    if [[ -d "$NVM_DIR" ]]; then
        echo "✓ NVM already installed"
        return 0
    fi
    
    echo "Installing NVM..."
    if curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash 2>&1; then
        echo "✓ NVM installed"
        return 0
    else
        echo "⚠ NVM install failed"
        return 1
    fi
}

install_node_user() {
    local user_home="$1"
    local user_nvm_dir="$user_home/.nvm"
    
    if [[ -d "$user_nvm_dir" ]]; then
        echo "  ✓ NVM already installed for user"
        return 0
    fi
    
    echo "  Installing NVM for user..."
    sudo -u "$user" curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | NVM_DIR="$user_nvm_dir" HOME="$user_home" bash 2>&1 || return 1
    
    if [[ -d "$user_nvm_dir" ]]; then
        echo "  ✓ NVM installed for user"
        return 0
    fi
    return 1
}

install_node_via_nvm() {
    local nvm_dir="$1"
    local node_version="24"
    
    if [[ -s "$nvm_dir/nvm.sh" ]]; then
        # shellcheck source=/dev/null
        source "$nvm_dir/nvm.sh" 2>/dev/null
        
        if nvm list "$node_version" 2>/dev/null | grep -q "$node_version"; then
            echo "  ✓ Node $node_version already installed"
            return 0
        fi
        
        echo "  Installing Node $node_version..."
        if nvm install "$node_version" 2>&1; then
            echo "  ✓ Node $node_version installed"
            nvm alias default "$node_version" 2>/dev/null || true
            return 0
        else
            echo "  ⚠ Node install failed"
            return 1
        fi
    fi
    return 1
}

if install_nvm; then
    # Install node for root
    install_node_via_nvm "$NVM_DIR"
    
    # Install node for mados user if exists
    if id mados &>/dev/null; then
        install_node_user /home/mados
    fi
    
    # Install node for skel (will be available for new users)
    install_node_user /etc/skel
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

# Copy .zshrc to mados user
if [[ -d /home/mados && ! -f /home/mados/.zshrc && -f /etc/skel/.zshrc ]]; then
    cp /etc/skel/.zshrc /home/mados/.zshrc
    chown 1000:1000 /home/mados/.zshrc
    echo "  → Copied .zshrc to /home/mados"
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
    
    # Install via curl (official method - binary)
    if curl -fsSL https://opencode.ai/install | OPENCODE_INSTALL_DIR="$INSTALL_DIR" bash; then
        if [[ -x "$INSTALL_DIR/$OPENCODE_CMD" ]] || command -v "$OPENCODE_CMD" &>/dev/null; then
            echo "✓ OpenCode installed"
        else
            echo "⚠ curl install completed but opencode not found"
        fi
    else
        echo "⚠ OpenCode install failed"
    fi
fi

# ── Ollama ───────────────────────────────────────────────────────────────
OLLAMA_CMD="ollama"

if command -v "$OLLAMA_CMD" &>/dev/null; then
    echo "✓ Ollama already installed"
else
    echo "Installing Ollama..."
    if curl -fsSL https://ollama.com/install.sh | sh; then
        echo "✓ Ollama installed"
    else
        echo "⚠ Ollama install failed"
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
