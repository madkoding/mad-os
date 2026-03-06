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
# NVM (Node Version Manager) y Node
# NOTA: No se instala en la imagen ISO para reducir tamaño.
# Se instalará automáticamente post-instalación para el usuario.
# ════════════════════════════════════════════════════════════════════════════
echo "NVM and Node installation skipped (will be installed post-installation)"

# ── Oh My Zsh ────────────────────────────────────────────────────────────
# Solo instala en /etc/skel - los usuarios root y mados usan symlinks
# para ahorrar ~400-600MB en la ISO
OMZ_DIR="/etc/skel/.oh-my-zsh"

if [[ ! -d "$OMZ_DIR" ]]; then
    echo "Installing Oh My Zsh to /etc/skel..."
    if git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$OMZ_DIR" 2>&1; then
        echo "✓ Oh My Zsh installed to /etc/skel"
        
        # Crear symlinks en lugar de copias para ahorrar espacio
        # mados user
        if [[ -d /home/mados ]]; then
            ln -sf /etc/skel/.oh-my-zsh /home/mados/.oh-my-zsh
            chown -h 1000:1000 /home/mados/.oh-my-zsh
            echo "  → Linked Oh My Zsh to /home/mados"
        fi
        
        # root user
        ln -sf /etc/skel/.oh-my-zsh /root/.oh-my-zsh
        echo "  → Linked Oh My Zsh to /root"
    else
        echo "⚠ Failed to clone Oh My Zsh (will install at boot)"
    fi
else
    echo "✓ Oh My Zsh already present in /etc/skel"
fi

# Copy .zshrc to mados user
if [[ -d /home/mados && ! -f /home/mados/.zshrc && -f /etc/skel/.zshrc ]]; then
    cp /etc/skel/.zshrc /home/mados/.zshrc
    chown 1000:1000 /home/mados/.zshrc
    echo "  → Copied .zshrc to /home/mados"
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
    # The installer puts it in ~/.opencode/bin/opencode
    if curl -fsSL https://opencode.ai/install | bash; then
        # Find and copy the installed binary
        if [[ -x "$HOME/.opencode/bin/opencode" ]]; then
            cp "$HOME/.opencode/bin/opencode" "$INSTALL_DIR/$OPENCODE_CMD"
            chmod +x "$INSTALL_DIR/$OPENCODE_CMD"
            echo "✓ OpenCode installed"
        else
            echo "⚠ OpenCode binary not found in ~/.opencode/bin/"
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

# ════════════════════════════════════════════════════════════════════════════
# Clean up package cache to reduce ISO size
# ════════════════════════════════════════════════════════════════════════════
echo "Cleaning up package cache..."
rm -rf /var/cache/pacman/pkg/*

echo "Removing unnecessary files (docs, man pages, locales)..."
rm -rf /usr/share/doc/*
rm -rf /usr/share/man/*
rm -rf /usr/share/locale/*
rm -rf /usr/share/gtk-doc/*
find /usr/share/gnome/help -type f -delete 2>/dev/null || true
find /usr/share/gnome/parsers -type f -delete 2>/dev/null || true

echo "Cleaning up npm cache..."
rm -rf /root/.npm 2>/dev/null || true
rm -rf /home/mados/.npm 2>/dev/null || true
rm -rf /root/.cache/npm 2>/dev/null || true
rm -rf /home/mados/.cache/npm 2>/dev/null || true

echo "Removing package test files..."
find /usr/lib/python3.*/site-packages -type d -name "test*" -exec rm -rf {} + 2>/dev/null || true
find /usr/lib/python3.*/site-packages -type d -name "*_tests" -exec rm -rf {} + 2>/dev/null || true
find /usr/lib/python3.*/site-packages -name "test_*.py" -delete 2>/dev/null || true
find /usr/lib/python3.*/site-packages -name "*_test.py" -delete 2>/dev/null || true
find /usr/lib/python3.*/site-packages -name "conftest.py" -delete 2>/dev/null || true

echo "Removing debug symbols and unnecessary binaries..."
find /usr -name "*.debug" -type f -delete 2>/dev/null || true
find /usr -name "*.pyc" -type f -delete 2>/dev/null || true
find /usr -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "Removing unused fonts and icons..."
rm -rf /usr/share/fonts/truetype/hints 2>/dev/null || true
rm -rf /usr/share/fonts/truetype/arphic 2>/dev/null || true
rm -rf /usr/share/fonts/truetype/dejavu 2>/dev/null || true
rm -rf /usr/share/fonts/truetype/liberation 2>/dev/null || true
rm -rf /usr/share/icons/hicolor 2>/dev/null || true
rm -rf /usr/share/icons/Adwaita 2>/dev/null || true
rm -rf /usr/share/pixmaps/gnome 2>/dev/null || true

echo "Removing unnecessary locales (keeping en_US, es_ES)..."
for lang in /usr/share/locale/*; do
    lang_name=$(basename "$lang")
    if [[ "$lang_name" != "en_US" && "$lang_name" != "es_ES" && "$lang_name" != "locale.alias" ]]; then
        rm -rf "$lang"
    fi
done

echo "✓ Package cache cleaned"
echo "✓ Unnecessary files removed"

echo "=== madOS: Pre-installation complete ==="
