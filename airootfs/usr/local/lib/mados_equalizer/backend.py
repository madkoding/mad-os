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
    2. Writes config to ~/.config/pipewire/pipewire.conf.d/mados-eq.conf
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


CONFIG_DIR = ".config"
DEFAULT_AUDIO_SINK = "@DEFAULT_AUDIO_SINK@"
DEFAULT_SINK = "@DEFAULT_SINK@"

# Config path for the standalone filter-chain (NOT in pipewire.conf.d to
# avoid PipeWire auto-loading it — the EQ process is managed separately)
EQ_CONFIG_DIR = Path.home() / CONFIG_DIR / "mados" / "equalizer"
EQ_CONFIG_FILE = EQ_CONFIG_DIR / "filter-chain.conf"

# Legacy config location (pipewire.conf.d) — cleaned up to prevent conflicts
LEGACY_PIPEWIRE_CONFIG_FILE = (
    Path.home() / CONFIG_DIR / "pipewire" / "pipewire.conf.d" / "mados-eq.conf"
)

# Node name used to identify the EQ in PipeWire
EQ_NODE_NAME = "mados-eq"
EQ_NODE_DESCRIPTION = "madOS Equalizer"

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
        self.active_sink = ""
        self.active_sink_name = ""
        self._apply_lock = threading.Lock()
        self._eq_process = None  # Subprocess running 'pipewire -c'
        self._last_error = ""  # Last error message from PipeWire
        self._original_default_sink_id = None  # ID of original default sink before EQ

        # Detect available audio systems
        self.has_pipewire = self._check_command("pw-cli")
        self.has_wpctl = self._check_command("wpctl")
        self.has_pulseaudio = self._check_command("pactl")

        # Clean up legacy configs and orphaned EQ nodes from prior sessions
        self._cleanup_legacy_config()
        self._cleanup_orphaned_eq()

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

    def _cleanup_legacy_config(self):
        """Remove legacy EQ configs from pipewire.conf.d.

        Old versions wrote the EQ config directly into pipewire.conf.d,
        causing PipeWire to auto-load the filter-chain on daemon start.
        This conflicted with the managed subprocess approach and could
        create duplicate or phantom EQ nodes.
        """
        try:
            if LEGACY_PIPEWIRE_CONFIG_FILE.exists():
                LEGACY_PIPEWIRE_CONFIG_FILE.unlink()
            # Also clean the old filter-chain.conf.d location
            legacy_alt = (
                Path.home()
                / CONFIG_DIR
                / "pipewire"
                / "filter-chain.conf.d"
                / "mados-eq.conf"
            )
            if legacy_alt.exists():
                legacy_alt.unlink()
        except OSError:
            pass

    def _cleanup_orphaned_eq(self):
        """Destroy any orphaned mados-eq PipeWire nodes.

        If the equalizer app crashed without cleaning up, a stale
        filter-chain node may remain in the PipeWire graph.  This
        method removes it so the next apply starts fresh.
        """
        if self.has_pipewire:
            self._run_command(["pw-cli", "destroy", EQ_NODE_NAME], timeout=2)

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
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", f"Command not found: {args[0]}"
        except Exception as e:
            return -1, "", str(e)

    def _detect_output_device(self):
        """Detect the currently active audio output device.

        Tries wpctl first (PipeWire), then falls back to pactl (PulseAudio).
        Updates self.active_sink and self.active_sink_name.
        """
        self.active_sink = ""
        self.active_sink_name = ""

        # Try wpctl (PipeWire WirePlumber)
        if self.has_wpctl:
            try:
                rc, stdout, _ = self._run_command(
                    ["wpctl", "inspect", DEFAULT_AUDIO_SINK]
                )
                if rc == 0 and stdout:
                    for line in stdout.splitlines():
                        line = line.strip()
                        if "node.name" in line and "=" in line:
                            # Parse: node.name = "alsa_output..."
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                name = parts[1].strip().strip('"').strip("'")
                                self.active_sink = name
                        if "node.description" in line and "=" in line:
                            parts = line.split("=", 1)
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
                rc, stdout, _ = self._run_command(["wpctl", "status"])
                if rc == 0 and stdout:
                    # Look for the default sink marked with *
                    in_sinks = False
                    for line in stdout.splitlines():
                        if "Sinks:" in line:
                            in_sinks = True
                            continue
                        if in_sinks:
                            if (
                                line.strip() == ""
                                or ("Sources:" in line)
                                or ("Filters:" in line)
                            ):
                                in_sinks = False
                                continue
                            if "*" in line:
                                # Extract the sink name after the asterisk
                                parts = line.split(".", 1)
                                if len(parts) == 2:
                                    sink_desc = parts[1].strip()
                                    # Remove volume info in brackets
                                    if "[" in sink_desc:
                                        sink_desc = sink_desc[
                                            : sink_desc.index("[")
                                        ].strip()
                                    self.active_sink_name = sink_desc
                                    self.active_sink = sink_desc
                                return
            except Exception:
                pass

        # Fallback: try pactl
        if self.has_pulseaudio:
            try:
                rc, stdout, _ = self._run_command(["pactl", "get-default-sink"])
                if rc == 0 and stdout.strip():
                    self.active_sink = stdout.strip()

                # Get description
                rc2, stdout2, _ = self._run_command(["pactl", "list", "sinks", "short"])
                if rc2 == 0 and stdout2:
                    for line in stdout2.splitlines():
                        if self.active_sink in line:
                            parts = line.split("\t")
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
        return ""

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
        nodes_str = ""
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
        links_str = ""
        for i in range(7):
            band_out = i + 1
            band_in = i + 2
            links_str += f"""
                    {{ output = "eq_band_{band_out}:Out" input = "eq_band_{band_in}:In" }}"""

        # Determine target sink
        target_sink = (
            self.active_sink
            if self.active_sink
            else "alsa_output.pci-0000_00_1b.0.analog-stereo"
        )

        config = f"""# madOS Equalizer - Standalone PipeWire filter-chain config
# Auto-generated by madOS Equalizer — do not edit manually

context.properties = {{
    log.level        = 0
    support.dbus     = false
}}

context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.*       = support/libspa-support
}}

context.modules = [
    {{  name = libpipewire-module-rt
        args = {{
            nice.level   = -11
        }}
        flags = [ ifexists nofail ]
    }}
    # Required for IPC with the running PipeWire daemon
    {{  name = libpipewire-module-protocol-native }}
    # Required for creating client-side nodes in the PipeWire graph
    {{  name = libpipewire-module-client-node }}
    # Required for wrapping nodes in an adapter with converter/resampler
    {{  name = libpipewire-module-adapter }}
    {{  name = libpipewire-module-filter-chain
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

    def _write_config(self):
        """Write the standalone filter-chain config file.

        Writes to EQ_CONFIG_DIR (outside pipewire.conf.d) so PipeWire
        does not auto-load it.  The file is launched via 'pipewire -c'.

        Returns:
            True if the config was written successfully.
        """
        try:
            EQ_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            config_content = self._generate_filter_chain_config()

            # Write atomically: write to temp file, then rename
            tmp_file = EQ_CONFIG_FILE.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(config_content)
            tmp_file.rename(EQ_CONFIG_FILE)

            return True
        except OSError as e:
            print(f"Error writing EQ config: {e}")
            return False

    def _stop_eq_process(self):
        """Stop the running filter-chain subprocess if any.

        Terminates the 'pipewire -c' process that hosts the EQ filter
        and waits for it to exit.  Also cleans up orphaned PipeWire
        nodes via pw-cli as a safety net.
        """
        if self._eq_process is not None:
            try:
                self._eq_process.terminate()
                try:
                    self._eq_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._eq_process.kill()
                    self._eq_process.wait(timeout=1)
            except Exception:
                pass
            finally:
                self._eq_process = None

        # Safety net: destroy orphaned nodes via pw-cli
        if self.has_pipewire:
            self._run_command(
                ["pw-cli", "destroy", EQ_NODE_NAME],
                timeout=2,
            )

    @staticmethod
    def _parse_id_from_line(line):
        """Extract an integer node ID from a pw-cli/wpctl id line.

        Parses lines like ``id 42, type PipeWire:Interface:Node/3``
        and returns the integer ``42``, or *None* on failure.
        """
        parts = line.split(",")[0].split()
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                pass
        return None

    def _parse_node_id_from_inspect(self, stdout):
        """Return the node ID from ``wpctl inspect`` output, or *None*."""
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("id "):
                return self._parse_id_from_line(stripped)
        return None

    def _save_original_default_sink(self):
        """Save the current default sink ID so it can be restored later.

        Uses wpctl to find the current default audio sink node ID
        before the EQ sink replaces it.
        """
        if self._original_default_sink_id is not None:
            return  # Already saved

        if not self.has_wpctl:
            return

        try:
            rc, stdout, _ = self._run_command(
                ["wpctl", "inspect", DEFAULT_AUDIO_SINK]
            )
            if rc == 0 and stdout:
                node_id = self._parse_node_id_from_inspect(stdout)
                if node_id is not None:
                    self._original_default_sink_id = node_id
        except Exception:
            pass

    def _set_default_sink_to_eq(self):
        """Set the PipeWire default audio sink to the EQ capture node.

        After the filter-chain process starts, the EQ capture node
        (mados-eq-capture) appears as an Audio/Sink in PipeWire.
        Setting it as the default sink routes all audio through the EQ.

        Returns:
            True if the default sink was changed successfully.
        """
        if not self.has_wpctl:
            return False

        # Find the EQ capture node ID using pw-cli
        eq_node_id = self._find_eq_sink_node_id()
        if eq_node_id is None:
            return False

        try:
            rc, _, _ = self._run_command(
                ["wpctl", "set-default", str(eq_node_id)]
            )
            return rc == 0
        except Exception:
            return False

    def _parse_eq_sink_from_objects(self, stdout):
        """Parse ``pw-cli list-objects`` output and return the EQ sink node ID.

        Returns the integer node ID whose ``node.name`` matches the
        EQ capture name, or *None* if not found.
        """
        current_id = None
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("id "):
                current_id = self._parse_id_from_line(stripped)
            elif current_id is not None and "node.name" in stripped:
                if f'"{EQ_NODE_NAME}-capture"' in stripped:
                    return current_id
        return None

    def _find_eq_sink_node_id(self):
        """Find the PipeWire node ID of the EQ capture sink.

        Searches the PipeWire object list for a node whose name matches
        the EQ capture node name (mados-eq-capture).

        Returns:
            The node ID as an integer, or None if not found.
        """
        if not self.has_pipewire:
            return None

        try:
            rc, stdout, _ = self._run_command(
                ["pw-cli", "list-objects"], timeout=3
            )
            if rc != 0 or not stdout:
                return None

            return self._parse_eq_sink_from_objects(stdout)
        except Exception:
            return None

    def _restore_default_sink(self):
        """Restore the original default audio sink after disabling EQ.

        Uses the saved original sink ID to restore routing so audio
        goes directly to the hardware output again.
        """
        if self._original_default_sink_id is None:
            return

        if not self.has_wpctl:
            self._original_default_sink_id = None
            return

        try:
            self._run_command(
                ["wpctl", "set-default", str(self._original_default_sink_id)]
            )
        except Exception:
            pass
        finally:
            self._original_default_sink_id = None

    def _start_eq_process(self):
        """Start a new PipeWire process hosting the EQ filter-chain.

        Runs 'pipewire -c <config>' as a subprocess.  The process
        connects to the running PipeWire daemon and creates the filter
        nodes without restarting the daemon itself, so other audio
        streams are not interrupted.

        Returns:
            True if the process started successfully.
        """
        self._stop_eq_process()

        try:
            self._eq_process = subprocess.Popen(
                ["pipewire", "-c", str(EQ_CONFIG_FILE)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            # Brief wait for the node to appear in the PipeWire graph
            time.sleep(0.3)

            # Verify the process is still running
            if self._eq_process.poll() is not None:
                stderr_output = ""
                try:
                    raw = self._eq_process.stderr.read()
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="replace")
                    stderr_output = raw.strip()
                except Exception:
                    pass
                rc = self._eq_process.returncode
                self._eq_process = None
                if stderr_output:
                    self._last_error = stderr_output
                    print(f"EQ process failed (rc={rc}): {stderr_output}")
                else:
                    self._last_error = f"Process exited with code {rc}"
                    print(f"EQ process exited unexpectedly (rc={rc})")
                return False

            return True
        except Exception as e:
            print(f"Error starting EQ process: {e}")
            self._eq_process = None
            return False

    def apply_eq(self, gains=None):
        """Apply equalizer settings to the audio output.

        Writes the filter-chain config and (re)starts a lightweight
        'pipewire -c' subprocess to host the EQ node.  Unlike the old
        approach that restarted the entire PipeWire daemon, this only
        restarts the filter-chain process, avoiding audio interruption
        on other streams.

        Args:
            gains: Optional list of 8 gain values in dB. If None, uses
                   the current stored gains.

        Returns:
            Tuple of (success: bool, message: str).
        """
        with self._apply_lock:
            if gains is not None:
                if len(gains) != 8:
                    return False, "Invalid number of gain values"
                self.gains = [float(g) for g in gains]

            if not self.enabled:
                return self.disable_eq()

            if not self.has_pipewire:
                # Try PulseAudio fallback
                return self._apply_eq_pulseaudio()

            # Save the current default sink before switching to EQ
            self._save_original_default_sink()

            # Write config and (re)start the filter-chain process
            if not self._write_config():
                return False, "Failed to write filter-chain configuration"

            if not self._start_eq_process():
                detail = self._last_error or "unknown error"
                return False, f"Failed to start filter-chain: {detail}"

            # Route all audio through the EQ by setting it as default sink
            if not self._set_default_sink_to_eq():
                print("Warning: Could not set EQ as default sink. "
                      "Audio may not be routed through the equalizer.")

            return True, "eq_applied"

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
        """Disable the equalizer by stopping the filter-chain process.

        Restores the original default audio sink so audio bypasses the
        EQ and goes directly to the hardware output.

        Returns:
            Tuple of (success: bool, message: str).
        """
        self.enabled = False

        if self.has_pipewire:
            # Restore original default sink before stopping the EQ process
            self._restore_default_sink()
            self._stop_eq_process()
            # Remove config file
            try:
                if EQ_CONFIG_FILE.exists():
                    EQ_CONFIG_FILE.unlink()
            except OSError:
                pass
        elif self.has_pulseaudio:
            self._disable_eq_pulseaudio()

        return True, "eq_disabled"

    def _build_mbeq_gains(self):
        """Build 15-band mbeq gains from 8-band equalizer gains."""
        mbeq_gains = [0.0] * 15
        mbeq_gains[0] = self.gains[0]
        mbeq_gains[2] = self.gains[1]
        mbeq_gains[3] = self.gains[1]
        mbeq_gains[4] = self.gains[2]
        mbeq_gains[6] = self.gains[3]
        mbeq_gains[7] = self.gains[3]
        mbeq_gains[8] = self.gains[4]
        mbeq_gains[9] = self.gains[4]
        mbeq_gains[10] = self.gains[5]
        mbeq_gains[11] = self.gains[5]
        mbeq_gains[12] = self.gains[6]
        mbeq_gains[13] = self.gains[7]
        mbeq_gains[14] = self.gains[7]
        return mbeq_gains

    def _apply_eq_pulseaudio(self):
        """Apply EQ using PulseAudio LADSPA module as fallback.

        Uses pactl to load the mbeq LADSPA plugin with the current
        gain settings applied to the default sink.

        Returns:
            Tuple of (success: bool, message: str).
        """
        if not self.has_pulseaudio:
            return False, "No audio system available"

        try:
            self._disable_eq_pulseaudio()

            mbeq_gains = self._build_mbeq_gains()
            control_str = ",".join(str(g) for g in mbeq_gains)

            rc, sink_name, _ = self._run_command(["pactl", "get-default-sink"])
            if rc != 0 or not sink_name.strip():
                return False, "Could not determine default audio sink"

            sink_name = sink_name.strip()

            rc, _, stderr = self._run_command(
                [
                    "pactl",
                    "load-module",
                    "module-ladspa-sink",
                    "sink_name=mados_eq",
                    'sink_properties=device.description="madOS Equalizer"',
                    f"master={sink_name}",
                    "plugin=mbeq",
                    "label=mbeq",
                    f"control={control_str}",
                ]
            )

            if rc == 0:
                self._run_command(["pactl", "set-default-sink", "mados_eq"])
                return True, "eq_applied"
            else:
                return False, f"Failed to load LADSPA module: {stderr}"

        except Exception as e:
            return False, f"PulseAudio EQ error: {e}"

    def _disable_eq_pulseaudio(self):
        """Remove PulseAudio LADSPA EQ module if loaded."""
        if not self.has_pulseaudio:
            return

        try:
            # Find and unload the mados_eq module
            rc, stdout, _ = self._run_command(["pactl", "list", "modules", "short"])
            if rc == 0 and stdout:
                for line in stdout.splitlines():
                    if "mados_eq" in line or "mados-eq" in line:
                        parts = line.split("\t")
                        if parts:
                            module_id = parts[0].strip()
                            self._run_command(["pactl", "unload-module", module_id])
        except Exception:
            pass

    def get_volume(self):
        """Get the current master volume level.

        Returns:
            Tuple of (volume: float 0.0-1.0, muted: bool).
        """
        if self.has_wpctl:
            try:
                rc, stdout, _ = self._run_command(
                    ["wpctl", "get-volume", DEFAULT_AUDIO_SINK]
                )
                if rc == 0 and stdout:
                    # Output format: "Volume: 0.75" or "Volume: 0.75 [MUTED]"
                    parts = stdout.strip().split()
                    if len(parts) >= 2:
                        try:
                            vol = float(parts[1])
                            muted = "[MUTED]" in stdout
                            self.master_volume = vol
                            self.muted = muted
                            return vol, muted
                        except ValueError:
                            pass
            except Exception:
                pass

        if self.has_pulseaudio:
            try:
                rc, stdout, _ = self._run_command(
                    ["pactl", "get-sink-volume", DEFAULT_SINK]
                )
                if rc == 0 and stdout:
                    # Parse percentage from output
                    for part in stdout.split():
                        if "%" in part:
                            try:
                                pct = int(part.replace("%", ""))
                                self.master_volume = pct / 100.0
                                break
                            except ValueError:
                                continue

                rc2, stdout2, _ = self._run_command(
                    ["pactl", "get-sink-mute", DEFAULT_SINK]
                )
                if rc2 == 0 and stdout2:
                    self.muted = "yes" in stdout2.lower()

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
                rc, _, _ = self._run_command(
                    ["wpctl", "set-volume", DEFAULT_AUDIO_SINK, f"{volume:.2f}"]
                )
                return rc == 0
            except Exception:
                pass

        if self.has_pulseaudio:
            try:
                pct = int(volume * 100)
                rc, _, _ = self._run_command(
                    ["pactl", "set-sink-volume", DEFAULT_SINK, f"{pct}%"]
                )
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
                self._run_command(["wpctl", "set-mute", DEFAULT_AUDIO_SINK, "toggle"])
                self.muted = not self.muted
                return self.muted
            except Exception:
                pass

        if self.has_pulseaudio:
            try:
                self._run_command(["pactl", "set-sink-mute", DEFAULT_SINK, "toggle"])
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
        state = "1" if muted else "0"

        if self.has_wpctl:
            try:
                rc, _, _ = self._run_command(
                    ["wpctl", "set-mute", DEFAULT_AUDIO_SINK, state]
                )
                return rc == 0
            except Exception:
                pass

        if self.has_pulseaudio:
            pa_state = "yes" if muted else "no"
            try:
                rc, _, _ = self._run_command(
                    ["pactl", "set-sink-mute", DEFAULT_SINK, pa_state]
                )
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
            "pipewire": self.has_pipewire,
            "wpctl": self.has_wpctl,
            "pulseaudio": self.has_pulseaudio,
            "active_sink": self.active_sink,
            "active_sink_name": self.active_sink_name,
        }

    def cleanup(self):
        """Clean up resources when the application is closing.

        Restores the original default audio sink, stops the filter-chain
        subprocess, and removes config files.
        """
        self._restore_default_sink()
        self._stop_eq_process()
        try:
            if EQ_CONFIG_FILE.exists():
                EQ_CONFIG_FILE.unlink()
        except OSError:
            pass
