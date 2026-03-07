"""
madOS Audio Player - GStreamer Backend with Synchronized Spectrum
=================================================================

Provides audio playback using GStreamer with real-time spectrum analysis.
The spectrum is calculated from actual audio data before playback.
"""

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstAudio", "1.0")
from gi.repository import Gst, GstAudio, GLib

import os
import threading

# Initialize GStreamer
Gst.init(None)


class GStreamerBackend:
    """Audio playback backend using GStreamer with synchronized spectrum."""

    AUDIO_EXTENSIONS = {
        ".mp3", ".flac", ".ogg", ".opus", ".wav", ".aac", ".m4a", ".wma",
        ".ape", ".mka", ".webm", ".mp4", ".aiff", ".aif", ".alac",
    }

    def __init__(self, num_bars=28):
        """Initialize GStreamer backend."""
        self.num_bars = num_bars
        self.pipeline = None
        self.spectrum = None
        self.volume_elem = None
        self.filesrc = None
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.duration = 0.0
        self.position = 0.0
        self.volume = 100
        self.is_muted = False
        self.metadata = {}
        self._spectrum_data = [0.0] * num_bars
        self._lock = threading.Lock()

    def start(self):
        """Start backend (no-op for GStreamer)."""
        pass

    def _build_pipeline(self):
        """Build GStreamer pipeline with spectrum analysis."""
        # Create elements
        self.pipeline = Gst.Pipeline.new("audio-player")
        self.filesrc = Gst.ElementFactory.make("filesrc", "file-source")
        decodebin = Gst.ElementFactory.make("decodebin", "decoder")
        audioconvert = Gst.ElementFactory.make("audioconvert", "converter")
        audioresample = Gst.ElementFactory.make("audioresample", "resampler")
        tee = Gst.ElementFactory.make("tee", "tee")

        # Spectrum branch
        queue1 = Gst.ElementFactory.make("queue", "spectrum-queue")
        self.spectrum = Gst.ElementFactory.make("spectrum", "spectrum")
        fakesink = Gst.ElementFactory.make("fakesink", "spectrum-sink")

        # Playback branch
        queue2 = Gst.ElementFactory.make("queue", "playback-queue")
        self.volume_elem = Gst.ElementFactory.make("volume", "volume")
        audiosink = Gst.ElementFactory.make("autoaudiosink", "audio-sink")

        if not all([self.pipeline, self.filesrc, decodebin, audioconvert,
                   audioresample, tee, queue1, self.spectrum, fakesink,
                   queue2, self.volume_elem, audiosink]):
            raise RuntimeError("Failed to create GStreamer elements")

        # Configure spectrum
        self.spectrum.set_property("bands", self.num_bars)
        self.spectrum.set_property("interval", 33333333)  # 33ms
        self.spectrum.set_property("threshold", -80)
        self.spectrum.set_property("post-messages", True)

        # Add to pipeline
        for elem in [self.filesrc, decodebin, audioconvert, audioresample, tee,
                    queue1, self.spectrum, fakesink, queue2, self.volume_elem, audiosink]:
            self.pipeline.add(elem)

        # Link static parts
        self.filesrc.link(decodebin)
        audioconvert.link(audioresample)
        audioresample.link(tee)

        # Link spectrum branch
        tee.link(queue1)
        queue1.link(self.spectrum)
        self.spectrum.link(fakesink)

        # Link playback branch
        tee.link(queue2)
        queue2.link(self.volume_elem)
        self.volume_elem.link(audiosink)

        # Connect signals
        decodebin.connect("pad-added", self._on_pad_added, audioconvert)

        # Connect bus
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

    def _on_pad_added(self, decodebin, pad, audioconvert):
        """Handle dynamic pad linking."""
        caps = pad.get_current_caps()
        if caps:
            structure = caps.get_structure(0)
            if structure.get_name().startswith("audio/"):
                sink_pad = audioconvert.get_static_pad("sink")
                if sink_pad and not sink_pad.is_linked():
                    pad.link(sink_pad)

    def _on_bus_message(self, bus, message):
        """Handle bus messages."""
        if message.type == Gst.MessageType.ELEMENT:
            if message.src == self.spectrum:
                self._process_spectrum(message)
        elif message.type == Gst.MessageType.EOS:
            self.is_playing = False
        elif message.type == Gst.MessageType.ERROR:
            self.is_playing = False
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            success, dur = self.pipeline.query_duration(Gst.Format.TIME)
            if success:
                self.duration = dur / Gst.SECOND

    def _process_spectrum(self, message):
        """Process spectrum data from message."""
        structure = message.get_structure()
        if structure and structure.has_field("magnitude"):
            mags = structure.get_value("magnitude")
            if mags:
                with self._lock:
                    for i, mag in enumerate(mags[:self.num_bars]):
                        # Convert dB to linear 0-1
                        linear = 10 ** (mag / 20)
                        self._spectrum_data[i] = max(0.0, min(1.0, linear))

    def play_file(self, filepath):
        """Play audio file."""
        if not os.path.isfile(filepath):
            return False

        self.stop()
        self.current_file = filepath

        if not self.pipeline:
            self._build_pipeline()

        self.filesrc.set_property("location", filepath)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.is_playing = True
        self.is_paused = False

        # Extract metadata
        self._extract_metadata(filepath)

        return True

    def _extract_metadata(self, filepath):
        """Extract file metadata."""
        self.metadata = {"title": os.path.splitext(os.path.basename(filepath))[0]}

    def toggle_pause(self):
        """Toggle pause."""
        if self.pipeline:
            if self.is_paused:
                self.pipeline.set_state(Gst.State.PLAYING)
            else:
                self.pipeline.set_state(Gst.State.PAUSED)
            self.is_paused = not self.is_paused

    def pause(self):
        """Pause playback."""
        if self.pipeline and self.is_playing:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.is_paused = True

    def resume(self):
        """Resume playback."""
        if self.pipeline and self.is_paused:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.is_paused = False

    def stop(self):
        """Stop playback."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        self.is_playing = False
        self.is_paused = False
        self.current_file = None
        with self._lock:
            self._spectrum_data = [0.0] * self.num_bars

    def seek(self, position):
        """Seek to position."""
        if self.pipeline:
            self.pipeline.seek_simple(Gst.Format.TIME,
                                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                    int(position * Gst.SECOND))

    def set_volume(self, volume):
        """Set volume."""
        self.volume = max(0, min(100, int(volume)))
        if self.volume_elem:
            self.volume_elem.set_property("volume", self.volume / 100.0)

    def set_mute(self, muted):
        """Set mute."""
        self.is_muted = muted
        if self.volume_elem:
            self.volume_elem.set_property("mute", muted)

    def toggle_mute(self):
        """Toggle mute."""
        self.set_mute(not self.is_muted)

    def get_property(self, prop):
        """Get property."""
        if prop == "time-pos":
            if self.pipeline:
                success, pos = self.pipeline.query_position(Gst.Format.TIME)
                if success:
                    return pos / Gst.SECOND
            return self.position
        elif prop == "duration":
            return self.duration
        elif prop == "pause":
            return self.is_paused
        elif prop == "idle-active":
            return not self.is_playing
        elif prop == "metadata":
            return self.metadata
        return None

    def update_state(self):
        """Update state."""
        if self.pipeline and self.is_playing:
            success, pos = self.pipeline.query_position(Gst.Format.TIME)
            if success:
                self.position = pos / Gst.SECOND

    def get_formatted_metadata(self):
        """Get formatted metadata."""
        return {
            "title": self.metadata.get("title", ""),
            "artist": self.metadata.get("artist", ""),
            "album": self.metadata.get("album", ""),
        }

    def get_audio_info(self):
        """Get audio info."""
        return {}

    def is_track_finished(self):
        """Check if track finished."""
        return not self.is_playing and self.current_file is not None

    def cleanup(self):
        """Cleanup."""
        self.stop()

    def get_spectrum(self):
        """Get spectrum data."""
        with self._lock:
            return self._spectrum_data.copy()

    @classmethod
    def is_audio_file(cls, filepath):
        """Check if audio file."""
        _, ext = os.path.splitext(filepath)
        return ext.lower() in cls.AUDIO_EXTENSIONS
