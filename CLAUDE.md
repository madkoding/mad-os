# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **madOS** - an AI-orchestrated Arch Linux distribution built using `archiso`. It's optimized for low-RAM systems (1.9GB) with Intel Atom processors and features **Claude Code** as an integrated AI assistant for system management and orchestration.

The project uses archiso to build a custom live/installer ISO with a beautiful TUI installer and pre-configured development environment.

## Building the ISO

### Local Build

```bash
# Install archiso if not already installed
sudo pacman -S archiso

# Build the ISO (requires root)
sudo mkarchiso -v -w work/ -o out/ .

# Output: out/madOS-*.iso
```

**Notes:**
- Build requires ~10GB free disk space for the work directory
- Build artifacts in `work/` (can be deleted after build)
- Final ISO appears in `out/` directory
- Use `-w` flag to specify work directory (created if doesn't exist)
- Build time: ~10-20 minutes depending on internet and CPU

### GitHub Actions Build

The ISO is built automatically on push to main via `.github/workflows/build-iso.yml`:
1. Uses Docker with `archlinux:latest` image
2. Installs archiso
3. Runs mkarchiso in privileged mode
4. Generates SHA256 checksums
5. Uploads ISO and checksums as artifacts (90-day retention)

## Repository Structure

### Core archiso Files

- **`profiledef.sh`**: ISO metadata (name: "madOS", publisher, version) and file permissions
- **`packages.x86_64`**: Package list for the ISO (one per line)
  - Includes `dialog` for the TUI installer
  - Node.js, npm for Claude Code
  - Sway, Waybar, Wofi for desktop
- **`pacman.conf`**: Pacman configuration for the build

### Boot Configuration

- **`grub/`**: GRUB bootloader config for UEFI boot
- **`syslinux/`**: Syslinux config for BIOS boot
- **`efiboot/`**: EFI boot loader configuration

### Root Filesystem (`airootfs/`)

Files copied into the live environment root:

- **`airootfs/etc/`**: System configuration files
  - `sysctl.d/99-extreme-low-ram.conf`: Kernel parameters for RAM optimization
  - `systemd/zram-generator.conf`: ZRAM swap configuration (50% RAM, zstd)
  - `skel/`: Default user files (copied to new user homes)
    - `.config/sway/`: Sway compositor configuration (Nord theme)
    - `.config/waybar/`: Status bar configuration
    - `.config/foot/`, `.config/alacritty/`: Terminal configs
    - `.config/wofi/`: Application launcher config

- **`airootfs/usr/local/bin/`**: Custom scripts
  - `install-mados`: Launcher (runs the GTK installer)
  - `install-mados-gtk.py`: **GTK installer** (graphical, Python + GTK3, Nord theme)
  - `setup-claude-code.sh`: Installs Claude Code via npm

## The Installer

madOS includes a graphical GTK installer with Nord theme.

### Launcher (`install-mados`)
Runs the GTK installer as root.

### GTK Installer (`install-mados-gtk.py`)
Beautiful graphical installer using Python + GTK3 with Nord theme.

**Features:**
- **Visual design**: madOS logo (SVG), Nord color scheme, modern UI
- **Mouse navigation**: Click-through wizard interface
- **Progress visualization**: Animated progress bar with real-time log
- **Interactive forms**: Text entries, combo boxes, validation
- **Theme**: CSS-styled with Nord colors (polar night background, frost accents)

**Dependencies**: `python`, `python-gobject`, `gtk3` (~15MB)

**Pages:**
1. Welcome (logo, features, start button)
2. Disk selection (visual list with sizes)
3. User account (form with validation)
4. Regional settings (timezone/locale dropdowns)
5. Summary (review all settings)
6. Installation (progress bar + log viewer)
7. Completion (success screen with reboot)

### Usage in Live Environment
```bash
# User boots from USB → Sway auto-starts → Installer launches automatically
# Or manually:
sudo install-mados
```

### Installer Flow
1. Welcome screen with madOS branding
2. Disk selection (with size info)
3. Confirmation warning (with disk details)
4. User account creation (username, password)
5. Regional settings (timezone, locale)
6. Installation summary review
7. Automated installation with progress bar
8. Completion screen with next steps
9. Auto-reboot option

### Key Installation Steps
- Partitioning: 1GB EFI, 32GB root, rest home
- Formatting: FAT32 (EFI), ext4 (root/home)
- Base system: Full package install via pacstrap
- Configuration: User, locale, GRUB, services
- Optimizations: ZRAM, kernel tuning, EarlyOOM
- Claude Code: Installed globally via npm

## System Optimizations

madOS includes aggressive RAM optimizations for 1.9GB systems:

### Kernel Parameters (99-extreme-low-ram.conf)
- `vm.vfs_cache_pressure=200`: Aggressive cache reclamation
- `vm.swappiness=5`: Minimal swap usage (prefer RAM)
- `vm.dirty_ratio=5`, `vm.dirty_background_ratio=3`: Quick writeback
- `vm.min_free_kbytes=16384`: Reserve 16MB free RAM
- TCP/network optimizations: Reduced buffers, faster timeouts

### ZRAM Configuration
- Size: 50% of physical RAM
- Algorithm: zstd compression
- Priority: 100 (highest)
- Type: swap

### Enabled Services
- **earlyoom**: Kills processes before OOM
- **iwd**: Wireless daemon
- **systemd-timesyncd**: Time synchronization

### Auto-start Features
- TTY1 autologin (configured user)
- Sway auto-start from `.bash_profile`
- Passwordless sudo for Claude Code operations

## Modifying the ISO

### Adding/Removing Packages

Edit `packages.x86_64`:
```bash
# Add a line for each package
vim packages.x86_64

# Don't forget to rebuild ISO after changes
```

**Important**: Keep `python`, `python-gobject`, and `gtk3` in the list for the installer to work.

### Changing System Configuration

1. Modify files in `airootfs/etc/`
2. Update file permissions in `profiledef.sh` if adding executable scripts
3. Rebuild ISO

### Customizing User Environment

Edit default configs in `airootfs/etc/skel/`:
- Sway config: `airootfs/etc/skel/.config/sway/config`
- Waybar: `airootfs/etc/skel/.config/waybar/`
- Terminal: `airootfs/etc/skel/.config/foot/foot.ini`

### Customizing the Installer

Edit `airootfs/usr/local/bin/install-mados-gtk.py`:

**Key customization points**:
- **Theme/CSS**: Edit the `apply_theme()` method (Nord colors, styles)
- **Partition layout**: Change sizes in `run_installation()` method
- **Package list**: Edit the `packages` list
- **Default values**: Timezone, locale, hostname format
- **Translations**: Edit the `TRANSLATIONS` dictionary for i18n

**After editing**:
1. Update `profiledef.sh` if changing script name/location
2. Rebuild ISO to include changes

## Testing the ISO

```bash
# After building, test in QEMU
qemu-system-x86_64 \
  -enable-kvm \
  -m 2048 \
  -cdrom out/madOS-*.iso \
  -boot d

# Test with lower RAM (target hardware)
qemu-system-x86_64 \
  -enable-kvm \
  -m 1920 \
  -cdrom out/madOS-*.iso \
  -boot d
```

## Branding and Identity

**System Name**: madOS (all lowercase in filenames, styled in display)

**Tagline**: "AI-Orchestrated Arch Linux System - Powered by Claude Code"

**Visual Identity**:
- ASCII art logo (see README.md and installer)
- Nord color scheme
- Blue/white TUI theme
- GRUB entry shows "madOS" instead of "Arch"

**Files with branding**:
- `profiledef.sh`: iso_name, iso_publisher, iso_application
- `install-mados-gtk.py`: Welcome screen, completion screen
- `README.md`: Full branding and documentation
- GRUB config: Distributor name

## Key Features

- **Compositor**: Sway (i3-compatible Wayland compositor, ~67MB RAM)
- **Terminal**: Foot (default) and Alacritty
- **Browser**: Chromium
- **Editor**: VS Code, vim, nano
- **Development**: Node.js 24.x, npm, git
- **AI Integration**: Claude Code pre-installed globally
- **Autologin**: TTY1 autologin to user, auto-starts Sway
- **Passwordless sudo**: Configured for Claude Code operations
- **Persistent Storage**: Dynamic persistence on live USB using free space

## Persistent Storage

madOS includes automatic persistent storage for live USB environments:

- **Location**: `airootfs/usr/local/bin/setup-persistence.sh` - Auto-setup script
- **Service**: `airootfs/etc/systemd/system/mados-persistence.service` - Runs on boot
- **Management Tool**: `airootfs/usr/local/bin/mados-persistence` - User-facing CLI tool
- **Documentation**: `docs/PERSISTENCE.md` - Full documentation

### How It Works

1. On first boot from USB, systemd service runs setup script
2. Script detects USB device and checks for free space
3. If ≥100MB free, creates ext4 partition with label `MADOS_PERSIST`
4. Partition is mounted and used for persistent storage
5. User changes, packages, and files persist across reboots

### User Commands

```bash
# Check persistence status
mados-persistence status

# Enable persistence (if not auto-configured)
sudo mados-persistence enable

# Temporarily disable for session
sudo mados-persistence disable

# Permanently remove persistence partition
sudo mados-persistence remove
```

### Implementation Details

- **Dynamic Size**: Uses ALL free space on USB (e.g., 16GB USB = ~12GB persistence)
- **Partition Label**: `MADOS_PERSIST` for easy identification
- **Filesystem**: ext4 with optimal settings for USB storage
- **Mount Point**: `/run/archiso/cowspace_persistent`
- **Auto-detection**: Finds USB device via archiso boot mount
- **Error Handling**: Logs to `/var/log/mados-persistence.log`

## Hardware Target

- **CPU**: Intel Atom or similar low-power processors
- **RAM**: 1.9GB (optimizations target ~1.5GB usable after kernel/services)
- **GPU**: Intel integrated (software rendering support via llvmpipe if needed)
- **Disk**: 32GB+ recommended for installation (1GB EFI + 32GB root + home)
- **Network**: WiFi support via iwd

## Claude Code Integration

Claude Code is available in both the live ISO and installed system. The system is designed for Claude Code to help with:
- System configuration and troubleshooting
- Package management
- Service management
- Code development and debugging
- Learning and documentation

Claude Code has passwordless sudo access for seamless system orchestration.

### Installation in Live ISO

Claude Code is automatically installed in the live ISO environment via systemd service:

- **Service**: `airootfs/etc/systemd/system/setup-claude-code.service` - Runs at boot
- **Script**: `airootfs/usr/local/bin/setup-claude-code.sh` - Installation script
- **Requirements**: Network connectivity (curl, npm)

**How it works:**
1. Service runs after `network-online.target` and `pacman-init.service`
2. Checks if `claude` binary exists (skips if present)
3. Verifies npm is available and network is accessible
4. Installs via `npm install -g @anthropic-ai/claude-code`
5. Exits gracefully if network unavailable (can be run manually later)

**Manual installation:**
```bash
# If auto-install didn't run (no network at boot)
sudo setup-claude-code.sh

# Verify installation
claude --version
```

### Installation in Installed System

During system installation, Claude Code is installed via:
1. The installer attempts npm install (non-fatal if fails)
2. A systemd service installs it on first boot if not present
3. Same mechanism as live ISO ensures it's always available
