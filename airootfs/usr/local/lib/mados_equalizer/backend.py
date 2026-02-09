"""
madOS Audio Equalizer - PipeWire/PulseAudio Backend
====================================================

Provides audio backend integration for applying equalizer settings
using PipeWire's filter-chain module. Falls back to PulseAudio's
LADSPA module-based approach if PipeWire is not available.

The backend creates a PipeWire filter-chain configuration that implements
an 8-band parametric EQ using bq_peaking (peaking EQ) filters, then
manages the filter-chain lifecycle to apply real-time EQ changes.

Architecture:
    1. Generates PipeWire filter-chain config with bq_peaking nodes
    2. Writes config to ~/.config/pipewire/filter-chain.conf.d/mados-eq.conf
    3. Destroys any existing mados-eq node, then restarts filter-chain
    4. Detects active audio output devices via wpctl/pactl
    5. Manages master volume via wpctl (PipeWire) or pactl (PulseAudio)
"""

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .presets import FREQUENCY_BANDS


# PipeWire filter-chain config directory
PIPEWIRE_CONFIG_DIR = Path.home() / '.config' / 'pipewire' / 'filter-chain.conf.d'
PIPEWIRE_CONFIG_FILE = PIPEWIRE_CONFIG_DIR / 'mados-eq.conf'

# Node name used to identify the EQ in PipeWire
EQ_NODE_NAME = 'mados-eq'
EQ_NODE_DESCRIPTION = 'madOS Equalizer'

# Q factor for peaking EQ filters (bandwidth)
DEFAULT_Q = 1.0


class AudioBackend:
    """Audio backend for applying equalizer settings via PipeWire or PulseAudio.

    This class manages the lifecycle of the equalizer filter-chain,
    detects audio output devices, and controls master volume.

    Attributes:
        gains: List of 8 gain values (dB) for each frequency band.
        enabled: Whether the equalizer is currently active.
        master_volume: Master volume level (0.0 to 1.0).
        muted: Whether the master output is muted.
        active_sink: Name of the currently active audio output sink.
        has_pipewire: Whether PipeWire is available on the system.
        has_pulseaudio: Whether PulseAudio tools are available.
        _apply_lock: Threading lock to prevent concurrent apply operations.
    """

    def __init__(self):
        """Initialize the audio backend and detect available audio systems."""
        self.gains = [0.0] * 8
        self.enabled = False
        self.master_volume = 1.0
        self.muted = False
        self.active_sink = ''
        self.active_sink_name = ''
        self._apply_lock = threading.Lock()

        # Detect available audio systems
        self.has_pipewire = self._check_command('pw-cli')
        self.has_wpctl = self._check_command('wpctl')
        self.has_pulseaudio = self._check_command('pactl')

        # Detect active output device
        self._detect_output_device()

    @staticmethod
    def _check_command(command):
        """Check if a command-line tool is available on the system.

        Args:
            command: The command name to check.

        Returns:
            True if the command is found in PATH.
        """
        return shutil.which(command) is not None

    def _run_command(self, args, timeout=5):
        """Run a subprocess command and return its output.

        Args:
            args: List of command arguments.
            timeout: Maximum time in seconds to wait for the command.

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, '', 'Command timed out'
        except FileNotFoundError:
            return -1, '', f'Command not found: {args[0]}'
        except Exception as e:
            return -1, '', str(e)

    def _detect_output_device(self):
        """Detect the currently active audio output device.

        Tries wpctl first (PipeWire), then falls back to pactl (PulseAudio).
        Updates self.active_sink and self.active_sink_name.
        """
        self.active_sink = ''
        self.active_sink_name = ''

        # Try wpctl (PipeWire WirePlumber)
        if self.has_wpctl:
            try:
                rc, stdout, _ = self._run_command(['wpctl', 'inspect', '@DEFAULT_AUDIO_SINK@'])
                if rc == 0 and stdout:
                    for line in stdout.splitlines():
                        line = line.strip()
                        if 'node.name' in line and '=' in line:
                            # Parse: node.name = "alsa_output..."
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                name = parts[1].strip().strip('"').strip("'")
                                self.active_sink = name
                        if 'node.description' in line and '=' in line:
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                desc = parts[1].strip().strip('"').strip("'")
                                self.active_sink_name = desc
                    if self.active_sink:
                        return
            except Exception:
                pass

        # Try wpctl status as alternative
        if self.has_wpctl:
            try:
                rc, stdout, _ = self._run_command(['wpctl', 'status'])
                if rc == 0 and stdout:
                    # Look for the default sink marked with *
                    in_sinks = False
                    for line in stdout.splitlines():
                        if 'Sinks:' in line:
                            in_sinks = True
                            continue
                        if in_sinks:
                            if line.strip() == '' or ('Sources:' in line) or ('Filters:' in line):
                                in_sinks = False
                                continue
                            if '*' in line:
                                # Extract the sink name after the asterisk
                                parts = line.split('.', 1)
                                if len(parts) == 2:
                                    sink_desc = parts[1].strip()
                                    # Remove volume info in brackets
                                    if '[' in sink_desc:
                                        sink_desc = sink_desc[:sink_desc.index('[')].strip()
                                    self.active_sink_name = sink_desc
                                    self.active_sink = sink_desc
                                return
            except Exception:
                pass

        # Fallback: try pactl
        if self.has_pulseaudio:
            try:
                rc, stdout, _ = self._run_command([
                    'pactl', 'get-default-sink'
                ])
                if rc == 0 and stdout.strip():
                    self.active_sink = stdout.strip()

                # Get description
                rc2, stdout2, _ = self._run_command([
                    'pactl', 'list', 'sinks', 'short'
                ])
                if rc2 == 0 and stdout2:
                    for line in stdout2.splitlines():
                        if self.active_sink in line:
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                self.active_sink_name = parts[1]
                            break

                if not self.active_sink_name:
                    self.active_sink_name = self.active_sink
            except Exception:
                pass

    def get_output_device_name(self):
        """Get the display name of the active audio output device.

        Returns:
            The device description string, or a fallback message.
        """
        if self.active_sink_name:
            return self.active_sink_name
        if self.active_sink:
            return self.active_sink
        return ''

    def refresh_output_device(self):
        """Re-detect the active output device.

        Returns:
            The updated device display name.
        """
        self._detect_output_device()
        return self.get_output_device_name()

    def _generate_filter_chain_config(self):
        """Generate PipeWire filter-chain configuration for the 8-band EQ.

        Creates a configuration with bq_peaking filter nodes for each
        frequency band, chained in series.

        Returns:
            The complete PipeWire filter-chain configuration as a string.
        """
        # Build nodes for each EQ band
        nodes_str = ''
        for i, (freq, gain) in enumerate(zip(FREQUENCY_BANDS, self.gains)):
            band_num = i + 1
            freq_float = float(freq)
            gain_float = float(gain)
            nodes_str += f"""
                    {{
                        type = builtin
                        name = eq_band_{band_num}
                        label = bq_peaking
                        control = {{ "Freq" = {freq_float} "Q" = {DEFAULT_Q} "Gain" = {gain_float} }}
                    }}"""

        # Build links to chain bands in series
        links_str = ''
        for i in range(7):
            band_out = i + 1
            band_in = i + 2
            links_str += f"""
                    {{ output = "eq_band_{band_out}:Out" input = "eq_band_{band_in}:In" }}"""

        # Determine target sink
        target_sink = self.active_sink if self.active_sink else 'alsa_output.pci-0000_00_1b.0.analog-stereo'

        config = f"""# madOS Equalizer - Auto-generated PipeWire filter-chain config
# Do not edit manually - managed by madOS Equalizer application

context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.name = "{EQ_NODE_NAME}"
            node.description = "{EQ_NODE_DESCRIPTION}"
            media.name = "{EQ_NODE_DESCRIPTION}"
            filter.graph = {{
                nodes = [{nodes_str}
                ]
                links = [{links_str}
                ]
            }}
            capture.props = {{
                node.name = "{EQ_NODE_NAME}-capture"
                media.class = Audio/Sink
                audio.channels = 2
                audio.position = [ FL FR ]
            }}
            playback.props = {{
                node.name = "{EQ_NODE_NAME}-playback"
                node.target = "{target_sink}"
                node.passive = true
                audio.channels = 2
                audio.position = [ FL FR ]
            }}
        }}
    }}
]
"""
        return config

    def _write_pipewire_config(self):
        """Write the PipeWire filter-chain configuration file.

        Creates the config directory if needed and writes the generated
        filter-chain configuration.

        Returns:
            True if the config was written successfully.
        """
        try:
            PIPEWIRE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config_content = self._generate_filter_chain_config()
            with open(PIPEWIRE_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(config_content)
            return True
        except OSError as e:
            print(f"Error writing PipeWire config: {e}")
            return False

    def _remove_pipewire_config(self):
        """Remove the PipeWire filter-chain configuration file.

        Returns:
            True if the file was removed or did not exist.
        """
        try:
            if PIPEWIRE_CONFIG_FILE.exists():
                PIPEWIRE_CONFIG_FILE.unlink()
            return True
        except OSError as e:
            print(f"Error removing PipeWire config: {e}")
            return False

    def _destroy_existing_eq(self):
        """Destroy any existing madOS EQ node in PipeWire.

        Uses pw-cli to find and destroy the node by name.
        """
        if not self.has_pipewire:
            return

        try:
            # Try to destroy by name using pw-cli
            self._run_command(
                ['pw-cli', 'destroy', EQ_NODE_NAME],
                timeout=3,
            )
        except Exception:
            pass

        # Brief pause to allow PipeWire to process the destruction
        time.sleep(0.2)

    def _restart_filter_chain(self):
        """Restart the PipeWire filter-chain to load the new configuration.

        First destroys any existing EQ node, then relies on PipeWire to
        automatically load the new configuration from the config file.

        Returns:
            True if the operation appeared successful.
        """
        self._destroy_existing_eq()

        # PipeWire should auto-load the config from the conf.d directory.
        # If not, we can try to manually load it using pipewire -c
        # Give PipeWire a moment to pick up the new config
        time.sleep(0.3)

        # Try to manually trigger a reload if available
        try:
            # Send SIGHUP to PipeWire to trigger config reload
            self._run_command(['pkill', '-HUP', 'pipewire'], timeout=2)
        except Exception:
            pass

        time.sleep(0.3)
        return True

    def apply_eq(self, gains=None):
        """Apply equalizer settings to the audio output.

        This is the main method for updating the EQ. It generates a new
        PipeWire filter-chain config, writes it, and restarts the chain.

        Args:
            gains: Optional list of 8 gain values in dB. If None, uses
                   the current stored gains.

        Returns:
            Tuple of (success: bool, message: str).
        """
        with self._apply_lock:
            if gains is not None:
                if len(gains) != 8:
                    return False, 'Invalid number of gain values'
                self.gains = [float(g) for g in gains]

            if not self.enabled:
                return self.disable_eq()

            if not self.has_pipewire:
                # Try PulseAudio fallback
                return self._apply_eq_pulseaudio()

            # Write PipeWire config and restart
            if not self._write_pipewire_config():
                return False, 'Failed to write PipeWire configuration'

            if not self._restart_filter_chain():
                return False, 'Failed to restart filter-chain'

            return True, 'eq_applied'

    def apply_eq_async(self, gains=None, callback=None):
        """Apply equalizer settings asynchronously in a background thread.

        Args:
            gains: Optional list of 8 gain values in dB.
            callback: Optional callable(success, message) to invoke when done.
                      Will be called from the background thread.
        """
        def _apply():
            success, message = self.apply_eq(gains)
            if callback:
                callback(success, message)

        thread = threading.Thread(target=_apply, daemon=True)
        thread.start()

    def enable_eq(self):
        """Enable the equalizer and apply current settings.

        Returns:
            Tuple of (success: bool, message: str).
        """
        self.enabled = True
        return self.apply_eq()

    def disable_eq(self):
        """Disable the equalizer by removing the filter-chain.

        Returns:
            Tuple of (success: bool, message: str).
        """
        self.enabled = False

        if self.has_pipewire:
            self._destroy_existing_eq()
            self._remove_pipewire_config()
        elif self.has_pulseaudio:
            self._disable_eq_pulseaudio()

        return True, 'eq_disabled'

    def _apply_eq_pulseaudio(self):
        """Apply EQ using PulseAudio LADSPA module as fallback.

        Uses pactl to load the mbeq LADSPA plugin with the current
        gain settings applied to the default sink.

        Returns:
            Tuple of (success: bool, message: str).
        """
        if not self.has_pulseaudio:
            return False, 'No audio system available'

        try:
            # First unload any existing mados EQ module
            self._disable_eq_pulseaudio()

            # Build control values for mbeq (15-band, we map our 8 to the closest)
            # mbeq has bands at: 50, 100, 156, 220, 311, 440, 622, 880, 1250,
            # 1750, 2500, 3500, 5000, 10000, 20000 Hz
            # Map our 8 bands to the closest mbeq bands
            mbeq_gains = [0.0] * 15
            # 60Hz -> band 0 (50Hz)
            mbeq_gains[0] = self.gains[0]
            # 170Hz -> band 2 (156Hz) and band 3 (220Hz)
            mbeq_gains[2] = self.gains[1]
            mbeq_gains[3] = self.gains[1]
            # 310Hz -> band 4 (311Hz)
            mbeq_gains[4] = self.gains[2]
            # 600Hz -> band 7 (622Hz)
            mbeq_gains[6] = self.gains[3]
            mbeq_gains[7] = self.gains[3]
            # 1kHz -> band 8 (880Hz) and band 9 (1250Hz)
            mbeq_gains[8] = self.gains[4]
            mbeq_gains[9] = self.gains[4]
            # 3kHz -> band 11 (3500Hz)
            mbeq_gains[10] = self.gains[5]
            mbeq_gains[11] = self.gains[5]
            # 6kHz -> band 12 (5000Hz)
            mbeq_gains[12] = self.gains[6]
            # 12kHz -> band 13 (10000Hz) and band 14 (20000Hz)
            mbeq_gains[13] = self.gains[7]
            mbeq_gains[14] = self.gains[7]

            control_str = ','.join(str(g) for g in mbeq_gains)

            # Get current default sink
            rc, sink_name, _ = self._run_command(['pactl', 'get-default-sink'])
            if rc != 0 or not sink_name.strip():
                return False, 'Could not determine default audio sink'

            sink_name = sink_name.strip()

            # Load LADSPA mbeq module
            rc, stdout, stderr = self._run_command([
                'pactl', 'load-module', 'module-ladspa-sink',
                f'sink_name=mados_eq',
                f'sink_properties=device.description="madOS Equalizer"',
                f'master={sink_name}',
                'plugin=mbeq',
                'label=mbeq',
                f'control={control_str}',
            ])

            if rc == 0:
                # Set the LADSPA sink as default
                self._run_command(['pactl', 'set-default-sink', 'mados_eq'])
                return True, 'eq_applied'
            else:
                return False, f'Failed to load LADSPA module: {stderr}'

        except Exception as e:
            return False, f'PulseAudio EQ error: {e}'

    def _disable_eq_pulseaudio(self):
        """Remove PulseAudio LADSPA EQ module if loaded."""
        if not self.has_pulseaudio:
            return

        try:
            # Find and unload the mados_eq module
            rc, stdout, _ = self._run_command(['pactl', 'list', 'modules', 'short'])
            if rc == 0 and stdout:
                for line in stdout.splitlines():
                    if 'mados_eq' in line or 'mados-eq' in line:
                        parts = line.split('\t')
                        if parts:
                            module_id = parts[0].strip()
                            self._run_command([
                                'pactl', 'unload-module', module_id
                            ])
        except Exception:
            pass

    def get_volume(self):
        """Get the current master volume level.

        Returns:
            Tuple of (volume: float 0.0-1.0, muted: bool).
        """
        if self.has_wpctl:
            try:
                rc, stdout, _ = self._run_command([
                    'wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'
                ])
                if rc == 0 and stdout:
                    # Output format: "Volume: 0.75" or "Volume: 0.75 [MUTED]"
                    parts = stdout.strip().split()
                    if len(parts) >= 2:
                        try:
                            vol = float(parts[1])
                            muted = '[MUTED]' in stdout
                            self.master_volume = vol
                            self.muted = muted
                            return vol, muted
                        except ValueError:
                            pass
            except Exception:
                pass

        if self.has_pulseaudio:
            try:
                rc, stdout, _ = self._run_command([
                    'pactl', 'get-sink-volume', '@DEFAULT_SINK@'
                ])
                if rc == 0 and stdout:
                    # Parse percentage from output
                    for part in stdout.split():
                        if '%' in part:
                            try:
                                pct = int(part.replace('%', ''))
                                self.master_volume = pct / 100.0
                                break
                            except ValueError:
                                continue

                rc2, stdout2, _ = self._run_command([
                    'pactl', 'get-sink-mute', '@DEFAULT_SINK@'
                ])
                if rc2 == 0 and stdout2:
                    self.muted = 'yes' in stdout2.lower()

                return self.master_volume, self.muted
            except Exception:
                pass

        return self.master_volume, self.muted

    def set_volume(self, volume):
        """Set the master volume level.

        Args:
            volume: Volume level from 0.0 to 1.5 (150%).

        Returns:
            True if the volume was set successfully.
        """
        volume = max(0.0, min(1.5, volume))
        self.master_volume = volume

        if self.has_wpctl:
            try:
                rc, _, _ = self._run_command([
                    'wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@',
                    f'{volume:.2f}'
                ])
                return rc == 0
            except Exception:
                pass

        if self.has_pulseaudio:
            try:
                pct = int(volume * 100)
                rc, _, _ = self._run_command([
                    'pactl', 'set-sink-volume', '@DEFAULT_SINK@',
                    f'{pct}%'
                ])
                return rc == 0
            except Exception:
                pass

        return False

    def toggle_mute(self):
        """Toggle mute state on the default audio output.

        Returns:
            The new muted state (True if now muted).
        """
        if self.has_wpctl:
            try:
                self._run_command([
                    'wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'
                ])
                self.muted = not self.muted
                return self.muted
            except Exception:
                pass

        if self.has_pulseaudio:
            try:
                self._run_command([
                    'pactl', 'set-sink-mute', '@DEFAULT_SINK@', 'toggle'
                ])
                self.muted = not self.muted
                return self.muted
            except Exception:
                pass

        self.muted = not self.muted
        return self.muted

    def set_mute(self, muted):
        """Set the mute state explicitly.

        Args:
            muted: True to mute, False to unmute.

        Returns:
            True if the operation was successful.
        """
        self.muted = muted
        state = '1' if muted else '0'

        if self.has_wpctl:
            try:
                rc, _, _ = self._run_command([
                    'wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', state
                ])
                return rc == 0
            except Exception:
                pass

        if self.has_pulseaudio:
            pa_state = 'yes' if muted else 'no'
            try:
                rc, _, _ = self._run_command([
                    'pactl', 'set-sink-mute', '@DEFAULT_SINK@', pa_state
                ])
                return rc == 0
            except Exception:
                pass

        return False

    def get_backend_info(self):
        """Get information about the detected audio backend.

        Returns:
            Dictionary with backend detection results.
        """
        return {
            'pipewire': self.has_pipewire,
            'wpctl': self.has_wpctl,
            'pulseaudio': self.has_pulseaudio,
            'active_sink': self.active_sink,
            'active_sink_name': self.active_sink_name,
        }

    def cleanup(self):
        """Clean up resources when the application is closing.

        Removes the EQ filter-chain if it was enabled.
        """
        if self.enabled:
            self.disable_eq()
