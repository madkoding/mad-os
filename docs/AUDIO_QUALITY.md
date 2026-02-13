# Audio Quality Auto-Detection

madOS includes automatic audio quality detection and configuration that ensures you get the best possible audio experience on your hardware.

## Overview

The audio quality system automatically:
- Detects your hardware's maximum sample rate (44.1kHz to 192kHz)
- Detects maximum bit depth (16/24/32-bit)
- Configures PipeWire and WirePlumber for optimal quality
- Persists settings across reboots
- Works in both live ISO and installed systems

## How It Works

### Detection Process

1. **Hardware Scanning**: The system scans `/proc/asound` to detect audio hardware capabilities
2. **Sample Rate Detection**: Identifies the maximum supported sample rate from hardware parameters
3. **Bit Depth Detection**: Checks for S32_LE (32-bit), S24_LE (24-bit), or S16_LE (16-bit) support
4. **Buffer Calculation**: Calculates optimal quantum (buffer) sizes based on sample rate

### Supported Quality Levels

| Sample Rate | Bit Depth | Quantum | Use Case |
|-------------|-----------|---------|----------|
| 44.1 kHz    | 16-bit    | 384     | CD quality |
| 48 kHz      | 24-bit    | 512     | Studio quality (default) |
| 96 kHz      | 24-bit    | 768     | High-resolution audio |
| 192 kHz     | 32-bit    | 1024    | Professional audio |

### Configuration Files

The system generates two configuration files:

#### PipeWire Configuration
Location: `/etc/pipewire/pipewire.conf.d/99-mados-hq-audio.conf`

Sets:
- Clock rate (sample rate)
- Quantum (buffer size)
- Resampling quality (maximum: 10)
- Audio format (S16LE/S24LE/S32LE)
- Real-time priority settings

#### WirePlumber Configuration
Location: `/etc/pipewire/wireplumber.conf.d/99-mados-hq-audio.conf`

Sets:
- ALSA device parameters
- ACP (Advanced Card Profile) enabling
- UCM (Use Case Manager) enabling
- Period sizes for low latency
- IEC958 codec support

## Live ISO vs Installed System

### Live ISO Environment

On the live ISO, audio quality detection runs at boot via systemd service:
- Service: `mados-audio-quality.service`
- Runs after: `mados-audio-init.service` (basic audio unmuting)
- Configuration: System-wide in `/etc/pipewire`

### Installed System

After installation:
- System-wide service runs at boot (same as live ISO)
- User-specific service runs before PipeWire starts
- Configuration copied to `/etc/skel` for new users
- Settings persist in `/etc/pipewire` system-wide

## Manual Configuration

### Viewing Current Settings

Check the generated configuration:

```bash
# System-wide configuration
cat /etc/pipewire/pipewire.conf.d/99-mados-hq-audio.conf

# User configuration (if exists)
cat ~/.config/pipewire/pipewire.conf.d/99-mados-hq-audio.conf

# Check systemd service status
systemctl status mados-audio-quality.service

# Check user service
systemctl --user status mados-audio-quality.service
```

### Re-running Detection

To re-detect and apply audio quality settings:

```bash
# As root (system-wide)
sudo /usr/local/bin/mados-audio-quality.sh

# As user (user-specific)
/usr/local/bin/mados-audio-quality.sh

# Restart audio services to apply
systemctl --user restart pipewire.service wireplumber.service
```

### Checking Audio Quality

Verify your current audio quality:

```bash
# Check PipeWire status
pw-cli info 0

# List audio devices
pactl list sinks short

# Check sample rate
pactl list sinks | grep -i "sample spec"

# Monitor real-time audio
pw-top
```

### Troubleshooting

#### Audio Not Working After Configuration

1. Check service status:
```bash
systemctl status mados-audio-quality.service
journalctl -u mados-audio-quality.service -b
```

2. Verify hardware detection:
```bash
cat /proc/asound/cards
cat /proc/asound/card0/pcm0p/sub0/hw_params
```

3. Restart audio stack:
```bash
systemctl --user restart pipewire.service
systemctl --user restart pipewire-pulse.service
systemctl --user restart wireplumber.service
```

#### Configuration Not Applied

Check if PipeWire is using the configuration:

```bash
# Check loaded configuration
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Core") | .info.props'

# Verify clock rate
pw-metadata -n settings | grep clock.rate
```

#### High CPU Usage

If you experience high CPU usage, the quantum might be too small for your hardware. Edit the configuration manually:

```bash
# Edit system-wide config
sudo nano /etc/pipewire/pipewire.conf.d/99-mados-hq-audio.conf

# Increase quantum values
default.clock.quantum = 1024
default.clock.min-quantum = 512
default.clock.max-quantum = 4096

# Restart services
systemctl --user restart pipewire.service wireplumber.service
```

## Technical Details

### Default Values

If hardware detection fails, the system uses these safe defaults:
- Sample Rate: 48000 Hz (48 kHz)
- Bit Depth: 24-bit (S24LE)
- Quantum: 512 samples
- Min Quantum: 256 samples
- Max Quantum: 2048 samples

### Resampling Quality

The system sets resampling quality to 10 (maximum), using:
- High-quality interpolation
- Low aliasing
- Minimal distortion
- CPU: ~2-5% overhead

### Real-Time Priority

PipeWire is configured with real-time scheduling:
- Nice level: -11 (high priority)
- RT priority: 88
- Soft limit: Unlimited
- Hard limit: Unlimited

This ensures smooth audio without xruns (buffer underruns/overruns).

### Buffer Latency

Approximate latency by sample rate:

| Sample Rate | Quantum | Latency |
|-------------|---------|---------|
| 44.1 kHz    | 384     | ~8.7 ms |
| 48 kHz      | 512     | ~10.7 ms |
| 96 kHz      | 768     | ~8 ms |
| 192 kHz     | 1024    | ~5.3 ms |

## Integration with Existing Audio

The audio quality system works alongside:

1. **mados-audio-init.sh**: Basic ALSA mixer control (volume, unmute)
2. **PipeWire**: Modern audio server (replaces PulseAudio)
3. **WirePlumber**: Session manager for PipeWire
4. **ALSA**: Low-level hardware interface

The systems work together:
```
Hardware → ALSA → PipeWire (with quality config) → WirePlumber → Applications
                      ↑
              mados-audio-init (volume/unmute)
```

## Benefits

1. **Automatic**: No manual configuration needed
2. **Optimal**: Always uses the best quality your hardware supports
3. **Persistent**: Settings survive reboots
4. **Safe**: Falls back to defaults if detection fails
5. **Compatible**: Works with all ALSA-compatible hardware
6. **Low-overhead**: Minimal CPU usage (~2-5%)
7. **Professional**: Studio-quality audio on supported hardware

## Related Commands

```bash
# Audio debugging
aplay -l                              # List playback devices
arecord -l                            # List capture devices
cat /proc/asound/cards                # Show sound cards
amixer                                # ALSA mixer control
pactl info                            # PulseAudio/PipeWire info
pw-cli ls Node                        # List PipeWire nodes

# Configuration management
ls /etc/pipewire/pipewire.conf.d/     # System configs
ls ~/.config/pipewire/pipewire.conf.d/ # User configs

# Service management
systemctl list-units '*audio*'        # List audio services
journalctl -f -u mados-audio-quality.service  # Follow logs
```

## References

- [PipeWire Documentation](https://docs.pipewire.org/)
- [WirePlumber Documentation](https://pipewire.pages.freedesktop.org/wireplumber/)
- [ALSA Project](https://www.alsa-project.org/)
- [madOS Audio Architecture](../CLAUDE.md#audio-integration)
