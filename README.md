<div align="center">

![madOS Logo](docs/mados-logo.png)

# madOS

**AI-Orchestrated Arch Linux System**

[![Build Status](https://img.shields.io/github/actions/workflow/status/madkoding/mad-os/build-iso.yml?branch=main&style=flat-square)](https://github.com/madkoding/mad-os/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Arch Linux](https://img.shields.io/badge/Arch-Linux-blue?style=flat-square)](https://archlinux.org)

</div>

madOS is a custom Arch Linux distribution optimized for low-RAM systems (1.9GB), featuring integrated Claude Code AI assistance for intelligent system management and orchestration. Includes open source drivers for Intel, AMD, and NVIDIA GPUs.

## Overview

- **Claude Code Integration** - AI-powered system orchestration and assistance
- **Low-RAM Optimized** - Designed for 1.9GB+ RAM systems with any x86_64 processor
- **Lightweight Desktop** - Sway Wayland compositor (~67MB RAM footprint)
- **Developer Ready** - Node.js, npm, Git, VS Code pre-installed
- **Performance Tuned** - ZRAM compression, EarlyOOM, kernel optimizations
- **Dual Installers** - GTK graphical and TUI text-based installers
- **Multi-GPU Support** - Open source drivers for Intel, AMD, and NVIDIA

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Intel Atom or equivalent | Any x86_64 |
| RAM | 1.9GB | 2GB+ |
| Storage | 32GB | 64GB+ |
| GPU | Intel/AMD/NVIDIA (open drivers) | Any x86_64 compatible |
| Boot | UEFI or BIOS | UEFI |

## Features

### Desktop Environment
- **Sway** - i3-compatible Wayland compositor with Nord theme
- **Waybar** - Customizable status bar
- **Wofi** - Application launcher
- **Foot** - Fast terminal emulator
- **Mako** - Notification daemon

### Applications
- **Chromium** - Web browser
- **VS Code** - Code editor
- **PCManFM** - File manager
- **LXAppearance** - Theme configuration

### madOS Native Apps
- **madOS Equalizer** (`mados-equalizer`) - 8-band audio equalizer with PipeWire/PulseAudio
- **madOS PDF Viewer** (`mados-pdf-viewer`) - PDF viewer with annotations and digital signatures
- **madOS Photo Viewer** (`mados-photo-viewer`) - Photo viewer/editor with video playback
- **madOS WiFi** (`mados-wifi`) - NetworkManager-based WiFi configuration tool

### Developer Tools
- **Claude Code** - AI assistant (`claude` command)
- **Node.js 24.x** & npm
- **Git** - Version control
- **htop** - System monitor
- **Vim & Nano** - Text editors

### System Optimizations
- **ZRAM** - Compressed swap using 50% RAM with zstd
- **EarlyOOM** - Out-of-memory killer to prevent freezes
- **Kernel tuning** - `vm.swappiness=5`, `vm.vfs_cache_pressure=200`
- **Network stack** - Optimized TCP buffers for low memory

### GPU Drivers (Open Source)
- **Intel** - intel-media-driver, vulkan-intel, libva-intel-driver
- **AMD** - xf86-video-amdgpu, vulkan-radeon, libva-mesa-driver
- **NVIDIA** - xf86-video-nouveau (open source driver)
- **Mesa** - OpenGL/Vulkan implementation for all GPUs

## Quick Start

### Installation

1. **Create bootable USB:**
   ```bash
   sudo dd if=madOS-*.iso of=/dev/sdX bs=4M status=progress oflag=sync
   ```

2. **Boot from USB** - Sway will auto-start in the live environment

3. **Run the installer:**
   ```bash
   sudo install-mados
   ```

   The smart launcher automatically selects:
   - **GTK Installer** - If running under Wayland/X11
   - **TUI Installer** - Text-based fallback

4. **Follow the installer** (~10 minutes):
   - Select installation disk
   - Create user account
   - Configure timezone and locale
   - Review and confirm settings

5. **Reboot** into your new madOS system

### Installer Options

| Installer | Command | Description | Size |
|-----------|---------|-------------|------|
| Smart (Auto) | `sudo install-mados` | Auto-detects best option | - |
| GTK | `sudo install-mados-gtk.py` | Graphical interface | +15MB |
| TUI | `sudo install-mados.sh` | Text-based, keyboard only | +200KB |
| CLI | `sudo install-arch-optimized.sh` | Legacy minimal installer | Base |

## Building the ISO

### Requirements

- Arch Linux or Arch-based system
- `archiso` package
- ~10GB free disk space
- Root access

### Local Build

```bash
# Install archiso
sudo pacman -S archiso

# Build the ISO
sudo mkarchiso -v -w work/ -o out/ .

# Output location
ls -lh out/madOS-*.iso
```

Build time: ~10-20 minutes

### GitHub Actions

ISO builds automatically on push to `main`:

1. Push to main branch
2. Monitor build in GitHub Actions tab (~15 minutes)
3. Download ISO from Artifacts

## Customization

### Add/Remove Packages

Edit `packages.x86_64` (one package per line):

```bash
# Add package
echo "firefox" >> packages.x86_64

# Remove package
sed -i '/chromium/d' packages.x86_64
```

### Desktop Configuration

Default user configurations:

| Component | Location |
|-----------|----------|
| Sway | `airootfs/etc/skel/.config/sway/config` |
| Waybar | `airootfs/etc/skel/.config/waybar/` |
| Terminal | `airootfs/etc/skel/.config/foot/foot.ini` |

### Modify Installer

Edit `airootfs/usr/local/bin/install-mados.sh` to customize:
- Partition layout and sizes
- Default packages
- Installation flow

## Using Claude Code

After installation, Claude Code is available globally:

```bash
# Start interactive session
claude

# Send direct message
claude --message "optimize system performance"

# Get help with commands
claude --message "how to check disk usage?"
```

### Capabilities

- **Code assistance** - Write, debug, and review code
- **System management** - Configure services, troubleshoot issues
- **Documentation** - Explain commands and concepts
- **Automation** - Create scripts and workflows
- **Problem solving** - Intelligent system orchestration

## System Architecture

```
madOS Architecture
├── Hardware (1.9GB RAM, Intel/AMD/NVIDIA GPU)
├── Kernel (Linux latest + ZRAM + sysctl tuning)
├── Services (systemd, EarlyOOM, iwd, PipeWire)
├── Display (Wayland via Sway)
├── Desktop (Sway, Waybar, Wofi, Nord theme)
├── Applications (Chromium, VS Code, dev tools)
└── AI Layer (Claude Code system orchestration)
```

## Post-Installation

### First Boot

1. System auto-logs into TTY1 and starts Sway
2. Waybar displays system status
3. Press `Super+Enter` to open terminal
4. Run `claude` to start AI assistant

### Key Bindings

| Shortcut | Action |
|----------|--------|
| `Super+Enter` | Open terminal |
| `Super+D` | Application launcher |
| `Super+Shift+Q` | Close window |
| `Super+1-9` | Switch workspace |
| `Super+Shift+E` | Exit Sway |

### Package Management

```bash
# Install software
sudo pacman -S <package>

# Update system
sudo pacman -Syu

# Update Claude Code
npm update -g @anthropic-ai/claude-code
```

## Performance Monitoring

```bash
# Monitor RAM usage
htop
free -h

# Check ZRAM status
zramctl

# View system services
systemctl list-units --type=service

# Remove orphaned packages
sudo pacman -Rns $(pacman -Qtdq)
```

## Troubleshooting

### Installation

| Issue | Solution |
|-------|----------|
| No disks detected | Check connections, run `lsblk` |
| Pacstrap fails | Verify internet connection |
| GRUB install error | Check UEFI/BIOS boot mode |

### Boot

| Issue | Solution |
|-------|----------|
| Won't boot | Verify BIOS boot order |
| Kernel panic | Boot with `systemd.unit=rescue.target` |
| No display | Try different TTY (Ctrl+Alt+F2-F6), check GPU drivers |
| Black screen with NVIDIA | Nouveau may need `nomodeset` kernel parameter |
| AMD screen flicker | Update kernel or try `amdgpu.dc=0` parameter |

### Performance

| Issue | Solution |
|-------|----------|
| High RAM usage | Check `htop`, disable unused services |
| Slow compositor | Consider i3 or dwm instead of Sway |
| ZRAM issues | `systemctl status systemd-zram-setup@zram0` |

## Resources

- **Website:** https://madkoding.github.io/mad-os/
- **Documentation:** `/usr/share/doc/madOS/` (after install)
- **Arch Wiki:** https://wiki.archlinux.org/
- **Issues:** GitHub Issues

## Contributing

Contributions are welcome. Areas for contribution:

- Themes and visual improvements
- Package optimization
- System tuning
- Documentation
- Bug fixes

## License

- Custom configurations and scripts: **MIT License**
- Based on Arch Linux and archiso

## Credits

- **Arch Linux** - Base distribution
- **archiso** - ISO building framework
- **Anthropic** - Claude Code AI
- **Sway** - Wayland compositor
- **Nord Theme** - Color scheme

---

Built for the Arch Linux community
