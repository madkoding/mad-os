# Arch Linux Optimized ISO with Claude Code

Custom Arch Linux live ISO optimized for low-RAM systems (1.9GB) with Claude Code pre-configured.

## Features

- **Optimized for limited RAM**: ZRAM, kernel tuning, EarlyOOM
- **Sway compositor**: Lightweight Wayland compositor (~67MB RAM)
- **Claude Code ready**: npm + Node.js pre-installed
- **Developer tools**: Chromium, VS Code, Git, htop
- **Auto-install script**: One-command installation to disk

## Hardware Target

- RAM: 1.9GB (optimized for Intel Atom systems)
- GPU: Intel Atom (software rendering support)
- Disk: 32GB+ recommended

## Building Locally

```bash
# Install archiso
sudo pacman -S archiso

# Build ISO
sudo mkarchiso -v -w work/ -o out/ .
```

## GitHub Actions

The ISO is built automatically on every push using GitHub Actions.
Download the latest ISO from the Actions artifacts.

## System Details

- **Compositor**: Sway with Nord theme
- **Terminal**: Foot
- **Bar**: Waybar
- **Launcher**: Wofi
- **Screenshots**: grim + slurp

## Optimizations Applied

- ZRAM swap (4GB compressed in RAM)
- vm.swappiness=5, vm.vfs_cache_pressure=200
- EarlyOOM enabled
- TTY autologin
- Audio on-demand

## Claude Code

Claude Code is installed via setup script:
```bash
/usr/local/bin/setup-claude-code.sh
```

User has passwordless sudo for Claude Code operations.

## Installation

Boot from USB and run:
```bash
sudo /usr/local/bin/install-arch-optimized.sh
```

## License

Based on Arch Linux and archiso. Custom configurations MIT licensed.
