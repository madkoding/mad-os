#!/bin/bash
# Setup Oh My Zsh - installs for all users with zsh as default shell
# Used as a boot service similar to setup-claude-code.sh

set -euo pipefail

OMZ_DIR="/etc/skel/.oh-my-zsh"

# Check if Oh My Zsh is already installed in skel
if [ -d "$OMZ_DIR" ]; then
    echo "✓ Oh My Zsh already installed in /etc/skel"
    exit 0
fi

# Check if git is available
if ! command -v git &>/dev/null; then
    echo "✗ Error: git is not installed."
    exit 1
fi

# Check connectivity
if ! curl -sf --connect-timeout 5 https://github.com >/dev/null 2>&1; then
    echo "⚠ No internet connection. Oh My Zsh will be installed on next boot."
    exit 0
fi

echo "Installing Oh My Zsh..."

# Clone Oh My Zsh to /etc/skel so all users get it
git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$OMZ_DIR" 2>&1 || {
    echo "⚠ Failed to clone Oh My Zsh."
    exit 0
}

echo "✓ Oh My Zsh installed in /etc/skel"

# Copy to existing user homes that have zsh as shell
while IFS=: read -r username _ uid _ _ home shell; do
    if [ "$shell" = "/usr/bin/zsh" ] && [ -d "$home" ] && [ "$uid" -ge 1000 ] 2>/dev/null; then
        if [ ! -d "$home/.oh-my-zsh" ]; then
            cp -a "$OMZ_DIR" "$home/.oh-my-zsh"
            chown -R "$username:$username" "$home/.oh-my-zsh"
            echo "  → Installed for user $username"
        fi
    fi
done < /etc/passwd

# Copy to root if root uses zsh
if grep -q "^root:.*:/usr/bin/zsh" /etc/passwd && [ ! -d /root/.oh-my-zsh ]; then
    cp -a "$OMZ_DIR" /root/.oh-my-zsh
    echo "  → Installed for root"
fi

# Copy .zshrc to root if not present
if [ ! -f /root/.zshrc ] && [ -f /etc/skel/.zshrc ]; then
    cp /etc/skel/.zshrc /root/.zshrc
    echo "  → Copied .zshrc to root"
fi

echo "✓ Oh My Zsh setup complete"
