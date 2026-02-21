# madOS Debugging Guide

Guide for debugging issues in the madOS live and installed environments.

## Quick Debug Tool

madOS includes a built-in debug helper:

```bash
# Show all available log sources
mados-debug

# View specific logs
mados-debug sway        # Sway compositor logs
mados-debug journal     # Full systemd journal (current boot)
mados-debug apps        # Python app logs (photo viewer, PDF, wifi, equalizer)
mados-debug chromium    # Chromium browser logs
mados-debug network     # NetworkManager / iwd logs
mados-debug audio       # PipeWire / audio logs
mados-debug boot        # Boot and systemd startup logs
mados-debug installer   # madOS installer logs
```

## Log Locations

### System Logs (journalctl)

```bash
# All logs from current boot
journalctl -b

# Follow live logs
journalctl -f

# Logs from a specific unit
journalctl -u NetworkManager
journalctl -u setup-opencode.service

# Kernel messages
journalctl -k

# Logs with priority (errors and above)
journalctl -p err -b
```

### Sway (Compositor)

Sway logs to the journal when started from the login shell:

```bash
# Sway logs
journalctl --user -u sway 2>/dev/null || journalctl -b | grep -i sway

# Or check the Sway log file (if redirected)
cat /tmp/sway-*.log 2>/dev/null

# Live Sway debugging (run from a terminal inside Sway)
swaymsg -t get_tree      # Window tree
swaymsg -t get_outputs    # Display info
swaymsg -t get_inputs     # Input devices
```

### Chromium

```bash
# Launch Chromium with verbose logging
chromium --enable-logging --v=1 2>&1 | tee /tmp/chromium.log

# Check Chromium flags configuration
cat /etc/chromium-flags.conf

# Check if Chromium is crashing
journalctl -b | grep -i chrom
```

### Python Applications (Photo Viewer, PDF Viewer, WiFi, Equalizer)

```bash
# Run apps directly to see error output
python3 -m mados_photo_viewer 2>&1
python3 -m mados_pdf_viewer 2>&1
python3 -m mados_equalizer 2>&1

# Note: PYTHONPATH must include /usr/local/lib
# The launcher scripts set this automatically, but for manual debugging:
export PYTHONPATH="/usr/local/lib:$PYTHONPATH"
python3 -m mados_photo_viewer

# Check GTK/GObject is available
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK OK')"

# Check if modules are importable
python3 -c "import sys; sys.path.insert(0, '/usr/local/lib'); import mados_photo_viewer; print('OK')"
```

### Network

```bash
# NetworkManager logs
journalctl -u NetworkManager -b

# IWD (WiFi daemon) logs
journalctl -u iwd -b

# Network interfaces
ip link show
ip addr show

# WiFi networks
nmcli device wifi list
iwctl station wlan0 scan && iwctl station wlan0 get-networks
```

### Audio (PipeWire)

```bash
# PipeWire status
systemctl --user status pipewire pipewire-pulse wireplumber

# PipeWire logs
journalctl --user -u pipewire -b
journalctl --user -u wireplumber -b

# Audio devices
wpctl status
pactl list sinks short
pactl list sources short

# ALSA devices
aplay -l
arecord -l
```

### Boot & Startup

```bash
# Boot time analysis
systemd-analyze
systemd-analyze blame
systemd-analyze critical-chain

# Failed services
systemctl --failed

# All service statuses
systemctl list-units --type=service --state=running
systemctl list-units --type=service --state=failed
```

### madOS Installer

```bash
# Installer logs are written during installation
cat /tmp/mados-install.log 2>/dev/null

# Run installer manually with verbose output
sudo /usr/local/bin/install-mados-gtk.py 2>&1 | tee /tmp/installer-debug.log
```

## Common Issues

### Chromium Won't Start

**Symptom:** Chromium fails to open or crashes immediately.

**Cause:** Chromium may fail to start due to GPU driver issues or missing dependencies.

**Fix:** Check Chromium flags and logs:
```bash
cat /etc/chromium-flags.conf
chromium --enable-logging --v=1 2>&1 | tee /tmp/chromium.log
```

### Chromium GPU / VA-API / Vulkan Errors

**Symptom:** Chromium shows errors like `vaInitialize failed`, `Failed to detect any valid GPUs`,
`ContextResult::kTransientFailure`, or `Network service crashed`.

**Cause:** Intel Atom and other legacy GPUs don't support VA-API hardware video decode or Vulkan.
Chromium tries to use these features and crashes when they fail.

**Fix:** madOS already configures `/etc/chromium-flags.conf` with safe defaults:
- `--disable-vulkan` — Prevents Vulkan errors on unsupported hardware
- `--disable-features=VaapiVideoDecoder,VaapiVideoEncoder,UseChromeOSDirectVideoDecoder` — Disables VA-API
- `--renderer-process-limit=3` — Saves RAM on low-memory systems

On legacy hardware, the session startup also sets `CHROMIUM_FLAGS="--disable-gpu"` to force
software rendering. To manually force software rendering:
```bash
CHROMIUM_FLAGS="--disable-gpu" chromium
```

### Python Apps Won't Open

**Symptom:** Photo Viewer, PDF Viewer, WiFi config, or Equalizer won't start.

**Cause:** The Python modules are in `/usr/local/lib/` which is not in Python's default module path.

**Fix:** The launcher scripts should set PYTHONPATH. Verify:
```bash
cat /usr/local/bin/mados-photo-viewer
# Should contain: export PYTHONPATH="/usr/local/lib${PYTHONPATH:+:$PYTHONPATH}"
```

For manual testing:
```bash
PYTHONPATH=/usr/local/lib python3 -m mados_photo_viewer
```

### Black Screen / No Display

**Symptom:** Screen is black after boot, Sway doesn't start.

**Debug:**
```bash
# Switch to TTY2
# Press Ctrl+Alt+F2

# Check Sway status
journalctl -b | grep sway

# Check GPU
lspci | grep -i vga
cat /var/log/Xorg.0.log 2>/dev/null

# Try software rendering
export WLR_RENDERER=pixman
export LIBGL_ALWAYS_SOFTWARE=1
sway
```

### No Audio

**Symptom:** No sound output.

**Debug:**
```bash
# Check PipeWire
systemctl --user status pipewire wireplumber

# Restart audio
systemctl --user restart pipewire wireplumber

# Check default sink
wpctl status
wpctl set-volume @DEFAULT_AUDIO_SINK@ 80%
```

### No WiFi

**Symptom:** WiFi networks not showing.

**Debug:**
```bash
# Check hardware
rfkill list all
ip link show

# Start services
sudo systemctl start NetworkManager
sudo systemctl start iwd

# Scan for networks
nmcli device wifi rescan
nmcli device wifi list
```

## Filing Bug Reports

When reporting bugs, please include the output of:

```bash
mados-debug > /tmp/mados-debug-report.txt 2>&1
```

This captures essential system information for troubleshooting.
