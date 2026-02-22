"""
madOS Audio Player - FFT Spectrum Analyzer
==========================================

Provides a real-time FFT spectrum analyzer using cava as the audio
analysis backend. Cava captures audio from PipeWire/PulseAudio and
outputs frequency bar data in raw binary mode.

The SpectrumAnalyzer class manages the cava subprocess, reads bar data
from a FIFO, and provides the current spectrum state for rendering.
"""

import os
import struct
import subprocess
import tempfile
import threading
import time


# Number of frequency bars
NUM_BARS = 28

# Bar peak hold and decay settings
PEAK_DECAY = 0.4       # Peak indicator falls this much per tick
BAR_GRAVITY = 0.6      # Bar gravity (how fast bars fall)


class SpectrumAnalyzer:
    """Real-time FFT spectrum analyzer using cava.

    Manages a cava subprocess that captures audio from the system
    audio server (PipeWire/PulseAudio) and outputs frequency bar
    heights as raw binary data through a FIFO pipe.

    Attributes:
        bars: List of current bar heights (0.0 to 1.0).
        peaks: List of peak indicator positions (0.0 to 1.0).
        is_active: True if cava is running and producing data.
    """

    def __init__(self, num_bars=NUM_BARS):
        self.num_bars = num_bars
        self.bars = [0.0] * num_bars
        self.peaks = [0.0] * num_bars
        self._target_bars = [0.0] * num_bars
        self.is_active = False

        self._process = None
        self._fifo_path = None
        self._config_path = None
        self._reader_thread = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Start the cava spectrum analyzer subprocess."""
        if self._process and self._process.poll() is None:
            return  # Already running

        # Check if cava is available
        if not self._find_cava():
            return

        try:
            self._setup_fifo()
            self._write_config()
            self._start_cava()
            self._start_reader()
        except Exception:
            self.stop()

    def stop(self):
        """Stop cava and clean up resources."""
        self._running = False

        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._process.kill()
                except OSError:
                    pass
            self._process = None

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1)
            self._reader_thread = None

        # Clean up temp files and directory
        tmp_dir = None
        if self._fifo_path:
            tmp_dir = os.path.dirname(self._fifo_path)
        for path in (self._fifo_path, self._config_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        if tmp_dir and os.path.isdir(tmp_dir):
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass
        self._fifo_path = None
        self._config_path = None
        self.is_active = False

    def update(self):
        """Update bar positions with smooth gravity/decay animation.

        Call this from the UI timer (~60ms) to animate bars falling.
        """
        with self._lock:
            for i in range(self.num_bars):
                target = self._target_bars[i]

                # Bars rise instantly, fall with gravity
                if target > self.bars[i]:
                    self.bars[i] = target
                else:
                    self.bars[i] = max(0.0, self.bars[i] - BAR_GRAVITY * 0.05)

                # Update peaks
                if self.bars[i] > self.peaks[i]:
                    self.peaks[i] = self.bars[i]
                else:
                    self.peaks[i] = max(0.0, self.peaks[i] - PEAK_DECAY * 0.02)

    def _find_cava(self):
        """Check if cava binary is available."""
        try:
            result = subprocess.run(
                ["which", "cava"],
                capture_output=True, timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False

    def _setup_fifo(self):
        """Create a named pipe (FIFO) for cava output."""
        tmp_dir = tempfile.mkdtemp(prefix="mados-spectrum-")
        self._fifo_path = os.path.join(tmp_dir, "cava.fifo")
        os.mkfifo(self._fifo_path)

    def _detect_audio_method(self):
        """Detect the best audio input method for cava."""
        # Check for PipeWire first (preferred on madOS)
        try:
            r = subprocess.run(
                ["pactl", "info"],
                capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0 and "PipeWire" in r.stdout:
                return "pipewire"
        except Exception:
            pass

        # Check for PulseAudio
        try:
            r = subprocess.run(
                ["pactl", "info"],
                capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0:
                return "pulse"
        except Exception:
            pass

        # Fallback to ALSA
        return "alsa"

    def _write_config(self):
        """Write cava configuration for raw output mode."""
        self._config_path = os.path.join(
            os.path.dirname(self._fifo_path), "cava.conf"
        )
        audio_method = self._detect_audio_method()
        config = f"""
[general]
bars = {self.num_bars}
framerate = 30
sensitivity = 120
autosens = 1
lower_cutoff_freq = 50
higher_cutoff_freq = 16000

[input]
method = {audio_method}
source = auto

[output]
method = raw
raw_target = {self._fifo_path}
data_format = binary
bit_format = 8bit
channels = mono
"""
        with open(self._config_path, 'w') as f:
            f.write(config)

    def _start_cava(self):
        """Start the cava subprocess."""
        self._process = subprocess.Popen(
            ["cava", "-p", self._config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _start_reader(self):
        """Start the FIFO reader thread."""
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._read_fifo, daemon=True
        )
        self._reader_thread.start()

    def _read_fifo(self):
        """Read raw bar data from cava FIFO (runs in background thread)."""
        try:
            # Open FIFO (blocks until cava connects)
            with open(self._fifo_path, 'rb') as fifo:
                self.is_active = True
                while self._running:
                    data = fifo.read(self.num_bars)
                    if not data or len(data) < self.num_bars:
                        if not self._running:
                            break
                        time.sleep(0.01)
                        continue

                    # Convert bytes (0-255) to normalized floats (0.0-1.0)
                    with self._lock:
                        for i in range(self.num_bars):
                            self._target_bars[i] = data[i] / 255.0

        except (OSError, IOError):
            pass
        finally:
            self.is_active = False

    def cleanup(self):
        """Full cleanup — alias for stop()."""
        self.stop()
