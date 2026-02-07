# madOS - AI-Orchestrated Arch Linux

```
╔═══════════════════════════════════════════════════╗
║                                                   ║
║     ███╗   ███╗ █████╗ ██████╗  ██████╗ ███████╗ ║
║     ████╗ ████║██╔══██╗██╔══██╗██╔═══██╗██╔════╝ ║
║     ██╔████╔██║███████║██║  ██║██║   ██║███████╗ ║
║     ██║╚██╔╝██║██╔══██║██║  ██║██║   ██║╚════██║ ║
║     ██║ ╚═╝ ██║██║  ██║██████╔╝╚██████╔╝███████║ ║
║     ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝ ║
║                                                   ║
║         AI-Orchestrated Arch Linux System        ║
║              Powered by Claude Code              ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
```

**madOS** is a custom Arch Linux distribution optimized for low-RAM systems, featuring **Claude Code** as an AI assistant to orchestrate and manage your operating system intelligently.

## ✨ Features

- 🤖 **Claude Code Integration**: AI-powered system orchestration and assistance
- 💾 **Low-RAM Optimized**: Designed for 1.9GB RAM systems (Intel Atom)
- 🚀 **Lightweight Desktop**: Sway compositor (~67MB RAM usage)
- 🛠️ **Developer Ready**: Node.js, npm, Git, VS Code pre-installed
- ⚡ **Performance Tuned**: ZRAM, EarlyOOM, kernel optimizations
- 🎨 **Beautiful TUI Installer**: Intuitive installation experience

## 🎯 Hardware Target

- **CPU**: Intel Atom or equivalent
- **RAM**: 1.9GB minimum (optimized for limited memory)
- **GPU**: Intel integrated graphics (software rendering support)
- **Storage**: 32GB+ recommended
- **Boot**: UEFI and BIOS support

## 📦 What's Included

### Desktop Environment
- **Sway**: i3-compatible Wayland compositor (Nord theme)
- **Waybar**: Customizable status bar
- **Wofi**: Application launcher
- **Foot**: Fast terminal emulator
- **Mako**: Notification daemon

### Applications
- **Chromium**: Web browser
- **VS Code**: Code editor
- **PCManFM**: File manager
- **LXAppearance**: Theme configurator

### Developer Tools
- **Claude Code**: AI assistant for system management
- **Node.js** (v24.x) & npm
- **Git**: Version control
- **htop**: System monitor
- **Vim & Nano**: Text editors

### System Optimizations
- **ZRAM**: 50% RAM compressed swap (zstd)
- **EarlyOOM**: Prevents system freezes
- **Kernel tuning**: `vm.swappiness=5`, `vm.vfs_cache_pressure=200`
- **Network optimizations**: Reduced TCP buffers

## 🚀 Quick Start

### Download madOS

Build the ISO locally or download from GitHub Actions artifacts.

### Boot from USB

1. Create bootable USB:
   ```bash
   sudo dd if=madOS-*.iso of=/dev/sdX bs=4M status=progress oflag=sync
   ```

2. Boot from USB and wait for Sway to auto-start

### Install madOS

Once in the live environment:

1. **Open terminal** (Super+Enter)
2. **Run the installer**:
   ```bash
   sudo install-mados
   ```

   This automatically selects the best installer:
   - **GTK (Graphical)** if you're in Sway/Wayland
   - **TUI (Text)** as fallback

3. **Follow the beautiful installer**:
   - 💾 Select installation disk
   - 👤 Create user account
   - 🌍 Choose timezone and language
   - ✅ Review and confirm
   - ☕ Wait ~10 minutes

4. **Reboot and enjoy madOS!**

### Installer Options

madOS includes **three installers** to choose from:

#### 🎨 **GTK Installer** (Recommended)
```bash
sudo install-mados-gtk.py
```
- Beautiful graphical interface with Nord theme
- madOS logo and visual design
- Mouse-friendly navigation
- Real-time progress visualization
- ~15MB extra dependencies (Python + GTK3)

#### 📟 **TUI Installer** (Lightweight)
```bash
sudo install-mados.sh
```
- Beautiful text-based interface with colors
- Keyboard-only navigation
- ASCII art branding
- Works without graphical environment
- Uses `dialog` (~200KB)

#### ⌨️ **CLI Installer** (Legacy)
```bash
sudo /usr/local/bin/install-arch-optimized.sh
```
- Original command-line installer
- Minimal, fast, no frills
- For advanced users or automation

## 🛠️ Building the ISO

### Requirements

- Arch Linux system (or Arch-based)
- `archiso` package installed
- ~10GB free disk space
- Root access

### Build Locally

```bash
# Install archiso
sudo pacman -S archiso

# Clone this repository
git clone https://github.com/yourusername/madOS.git
cd madOS

# Build the ISO
sudo mkarchiso -v -w work/ -o out/ .

# Find your ISO in out/
ls -lh out/
```

**Build time**: ~10-20 minutes depending on your internet and CPU

### Build with GitHub Actions

The ISO is automatically built on every push to `main`:

1. Push to main branch
2. Check **Actions** tab on GitHub
3. Wait for build to complete (~15 minutes)
4. Download ISO from **Artifacts**

## 🎨 Customization

### Add/Remove Packages

Edit `packages.x86_64`:
```bash
# Add packages (one per line)
echo "firefox" >> packages.x86_64

# Remove packages
sed -i '/chromium/d' packages.x86_64
```

### Customize Desktop

Default configurations in `airootfs/etc/skel/.config/`:
- Sway: `airootfs/etc/skel/.config/sway/config`
- Waybar: `airootfs/etc/skel/.config/waybar/`
- Terminal: `airootfs/etc/skel/.config/foot/foot.ini`

### Modify Installer

The TUI installer: `airootfs/usr/local/bin/install-mados.sh`

Change partition sizes, default packages, or installation flow.

## 🧠 Using Claude Code

After installation, Claude Code is pre-installed. Start it with:

```bash
claude
```

### What Can Claude Do?

- 📝 **Code assistance**: Write, debug, and review code
- 🔧 **System management**: Configure services, troubleshoot issues
- 📚 **Documentation**: Explain commands and concepts
- 🚀 **Automation**: Create scripts and workflows
- 💡 **Problem solving**: Intelligent system orchestration

### Example Commands

```bash
# Start Claude Code CLI
claude

# Use Claude with specific context
claude --message "optimize my sway config"

# Get system help
claude --message "how do I check disk usage?"
```

## 📊 System Architecture

```
madOS Stack
├── Hardware Layer
│   └── Intel Atom / 1.9GB RAM
├── Kernel Layer
│   ├── Linux kernel (latest)
│   ├── ZRAM (compressed swap)
│   └── Optimized sysctl parameters
├── System Services
│   ├── systemd
│   ├── EarlyOOM
│   ├── iwd (wireless)
│   └── PipeWire (audio)
├── Display Server
│   └── Wayland (via Sway)
├── Desktop Environment
│   ├── Sway compositor
│   ├── Waybar (status)
│   ├── Wofi (launcher)
│   └── Nord theme
├── Applications
│   ├── Chromium
│   ├── VS Code
│   └── Developer tools
└── AI Layer
    └── Claude Code (system orchestration)
```

## 🔧 Post-Installation

### First Boot

1. System auto-logs in and starts Sway
2. Waybar shows system stats
3. Press `Super+Enter` for terminal
4. Type `claude` to start AI assistant

### Essential Keybindings

- `Super+Enter` - Terminal
- `Super+D` - Application launcher
- `Super+Shift+Q` - Close window
- `Super+1-9` - Switch workspace
- `Super+Shift+E` - Exit Sway

### Install Additional Software

```bash
# Using pacman
sudo pacman -S <package>

# Using AUR helper (install yay first)
yay -S <aur-package>
```

### Update System

```bash
# Full system update
sudo pacman -Syu

# Update Claude Code
npm update -g @anthropic-ai/claude-code
```

## 📈 Performance Tips

madOS is already optimized, but you can:

1. **Monitor RAM**: `htop` or `free -h`
2. **Check ZRAM**: `zramctl`
3. **Disable services**: `systemctl disable <service>`
4. **Use lightweight apps**: Replace Chromium with qutebrowser
5. **Trim unused packages**: `sudo pacman -Rns $(pacman -Qtdq)`

## 🐛 Troubleshooting

### Installation Issues

- **No disks detected**: Check connections, try `lsblk`
- **Pacstrap fails**: Check internet connection
- **GRUB install fails**: Verify UEFI/BIOS mode

### Boot Issues

- **Won't boot**: Check BIOS boot order
- **Kernel panic**: Boot with `systemd.unit=rescue.target`
- **No display**: Try different compositor or X11

### Performance Issues

- **High RAM usage**: Check `htop`, disable unused services
- **Slow compositor**: Switch from Sway to dwm or i3
- **ZRAM not working**: `systemctl status systemd-zram-setup@zram0`

## 🤝 Contributing

Contributions welcome! This project is open source.

### Areas for Contribution

- 🎨 Themes and appearance
- 📦 Package selection optimization
- 🔧 System optimizations
- 📝 Documentation
- 🐛 Bug fixes

## 📜 License

Based on Arch Linux and archiso.

Custom configurations and scripts: **MIT License**

## 🙏 Credits

- **Arch Linux**: The base distribution
- **archiso**: ISO building tool
- **Anthropic**: Claude Code AI
- **Sway**: Wayland compositor
- **Nord Theme**: Color scheme

## 📞 Support

- **Documentation**: See `/usr/share/doc/madOS/` (after install)
- **Arch Wiki**: https://wiki.archlinux.org/
- **Issues**: GitHub Issues

---

**Made with 🤖 and ❤️ for the Arch Linux community**
