"""
madOS Video Player - GStreamer Player Engine
=============================================

Encapsulates the GStreamer pipeline for video playback. Provides a clean
API for play, pause, stop, seek, volume, speed control, and subtitle
loading. The video sink widget is exposed for embedding in the GTK UI.
"""

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

GST_AVAILABLE = False
try:
    gi.require_version("Gst", "1.0")
    gi.require_version("GstVideo", "1.0")
    from gi.repository import Gst, GstVideo  # noqa: F401

    Gst.init(None)
    GST_AVAILABLE = True
except (ValueError, ImportError):
    pass

from gi.repository import Gtk, GLib


def format_time(nanoseconds):
    """Convert GStreamer nanoseconds to a human-readable time string.

    Args:
        nanoseconds: Time value in nanoseconds.

    Returns:
        Formatted string like "01:23" or "1:23:45".
    """
    if nanoseconds < 0:
        return "00:00"
    total_seconds = int(nanoseconds / Gst.SECOND) if GST_AVAILABLE else int(nanoseconds / 1e9)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class PlayerEngine:
    """GStreamer-based video playback engine.

    Signals are communicated via callback functions set by the caller:
        on_eos()        - End of stream reached
        on_error(msg)   - Error occurred
        on_state(state) - State changed ('playing', 'paused', 'stopped')
        on_duration(ns) - Duration discovered (in nanoseconds)
        on_position(ns) - Position update (called periodically)
        on_tags(tags)   - Stream tags discovered (dict with title, artist, etc)
    """

    # Playback speed presets
    SPEED_PRESETS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]

    def __init__(self):
        """Initialize the player engine."""
        self._pipeline = None
        self._video_widget = None
        self._playing = False
        self._duration = -1
        self._speed = 1.0
        self._volume = 0.8
        self._muted = False
        self._mute_volume = 0.8
        self._update_id = None
        self._uri = None

        # Callbacks
        self.on_eos = None
        self.on_error = None
        self.on_state = None
        self.on_duration = None
        self.on_position = None
        self.on_tags = None

        if GST_AVAILABLE:
            self._setup_pipeline()

    @property
    def available(self):
        """Return True if GStreamer is available."""
        return GST_AVAILABLE and self._pipeline is not None

    @property
    def video_widget(self):
        """Return the GTK widget for video display, or None."""
        return self._video_widget

    @property
    def is_playing(self):
        """Return True if currently playing."""
        return self._playing

    @property
    def duration(self):
        """Return duration in nanoseconds, or -1 if unknown."""
        return self._duration

    @property
    def speed(self):
        """Return the current playback speed."""
        return self._speed

    @property
    def volume(self):
        """Return the current volume (0.0 to 1.0)."""
        return self._volume

    @property
    def muted(self):
        """Return True if muted."""
        return self._muted

    def _setup_pipeline(self):
        """Create the GStreamer playbin pipeline with appropriate video sink."""
        self._pipeline = Gst.ElementFactory.make("playbin", "player")
        if self._pipeline is None:
            return

        # Try gtksink first (best for Wayland/GTK integration)
        gtksink = Gst.ElementFactory.make("gtksink", "videosink")
        if gtksink is not None:
            self._pipeline.set_property("video-sink", gtksink)
            self._video_widget = gtksink.get_property("widget")
        else:
            # Fall back to autovideosink
            autosink = Gst.ElementFactory.make("autovideosink", "videosink")
            if autosink:
                self._pipeline.set_property("video-sink", autosink)

        # Set initial volume
        self._pipeline.set_property("volume", self._volume)

        # Connect bus signals
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self._on_bus_eos)
        bus.connect("message::error", self._on_bus_error)
        bus.connect("message::state-changed", self._on_bus_state_changed)
        bus.connect("message::tag", self._on_bus_tag)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, filepath):
        """Load a media file.

        Args:
            filepath: Absolute path to the media file.

        Returns:
            True if loading started, False if GStreamer unavailable.
        """
        if not self.available:
            return False

        self.stop()
        self._uri = GLib.filename_to_uri(filepath, None)
        self._pipeline.set_property("uri", self._uri)
        self._duration = -1
        return True

    def play(self):
        """Start or resume playback."""
        if not self.available:
            return
        self._pipeline.set_state(Gst.State.PLAYING)
        self._playing = True
        self._start_update_timer()
        self._apply_speed()
        if self.on_state:
            self.on_state("playing")

    def pause(self):
        """Pause playback."""
        if not self.available:
            return
        self._pipeline.set_state(Gst.State.PAUSED)
        self._playing = False
        self._stop_update_timer()
        if self.on_state:
            self.on_state("paused")

    def toggle_play_pause(self):
        """Toggle between play and pause."""
        if self._playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        """Stop playback and reset position."""
        if not self.available:
            return
        self._pipeline.set_state(Gst.State.NULL)
        self._playing = False
        self._stop_update_timer()
        if self.on_state:
            self.on_state("stopped")

    def seek(self, position_ns):
        """Seek to an absolute position.

        Args:
            position_ns: Position in nanoseconds.
        """
        if not self.available:
            return

        # Remember whether we were playing before the seek
        was_playing = self._playing

        # Pipeline must be at least PAUSED to accept a seek
        _, state, _ = self._pipeline.get_state(0)
        if state == Gst.State.NULL or state == Gst.State.READY:
            self._pipeline.set_state(Gst.State.PAUSED)

        self._pipeline.seek(
            self._speed,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            Gst.SeekType.SET,
            int(position_ns),
            Gst.SeekType.NONE,
            0,
        )

        # If we were not playing, stay paused after seek
        if not was_playing:
            self._pipeline.set_state(Gst.State.PAUSED)
            self._playing = False

    def seek_relative(self, offset_ns):
        """Seek relative to current position.

        Args:
            offset_ns: Offset in nanoseconds (positive=forward, negative=backward).
        """
        if not self.available:
            return
        success, position = self._pipeline.query_position(Gst.Format.TIME)
        if success:
            new_pos = max(0, position + offset_ns)
            if self._duration > 0:
                new_pos = min(new_pos, self._duration)
            self.seek(new_pos)

    def get_position(self):
        """Query current position.

        Returns:
            Position in nanoseconds, or -1 if unavailable.
        """
        if not self.available:
            return -1
        success, position = self._pipeline.query_position(Gst.Format.TIME)
        return position if success else -1

    def set_volume(self, volume):
        """Set playback volume.

        Args:
            volume: Volume level from 0.0 to 1.0.
        """
        self._volume = max(0.0, min(1.0, volume))
        if self._pipeline and not self._muted:
            self._pipeline.set_property("volume", self._volume)

    def toggle_mute(self):
        """Toggle mute state.

        Returns:
            True if now muted, False if unmuted.
        """
        if self._muted:
            self._muted = False
            if self._pipeline:
                self._pipeline.set_property("volume", self._volume)
        else:
            self._muted = True
            self._mute_volume = self._volume
            if self._pipeline:
                self._pipeline.set_property("volume", 0.0)
        return self._muted

    def set_speed(self, speed):
        """Set playback speed.

        Args:
            speed: Speed multiplier (e.g. 1.0 = normal, 2.0 = double).
        """
        self._speed = max(0.1, min(8.0, speed))
        if self._playing:
            self._apply_speed()

    def speed_up(self):
        """Increase speed to the next preset.

        Returns:
            The new speed value.
        """
        for s in self.SPEED_PRESETS:
            if s > self._speed + 0.01:
                self.set_speed(s)
                return self._speed
        return self._speed

    def speed_down(self):
        """Decrease speed to the previous preset.

        Returns:
            The new speed value.
        """
        for s in reversed(self.SPEED_PRESETS):
            if s < self._speed - 0.01:
                self.set_speed(s)
                return self._speed
        return self._speed

    def reset_speed(self):
        """Reset speed to normal (1.0x)."""
        self.set_speed(1.0)

    def load_subtitle(self, filepath):
        """Load an external subtitle file.

        Args:
            filepath: Path to the subtitle file (.srt, .sub, .ass, etc).
        """
        if not self.available:
            return
        sub_uri = GLib.filename_to_uri(filepath, None)
        self._pipeline.set_property("suburi", sub_uri)
        # Enable subtitle rendering
        flags = self._pipeline.get_property("flags")
        # Flag bit 2 = text (subtitles)
        flags |= (1 << 2)
        self._pipeline.set_property("flags", flags)

    def cleanup(self):
        """Release GStreamer resources."""
        self._stop_update_timer()
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _apply_speed(self):
        """Apply the current speed to the pipeline via a seek."""
        if not self.available:
            return
        success, position = self._pipeline.query_position(Gst.Format.TIME)
        if not success:
            position = 0
        self._pipeline.seek(
            self._speed,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            Gst.SeekType.SET,
            position,
            Gst.SeekType.NONE,
            0,
        )

    def _start_update_timer(self):
        """Start periodic position updates."""
        if self._update_id is None:
            self._update_id = GLib.timeout_add(250, self._update_tick)

    def _stop_update_timer(self):
        """Stop periodic position updates."""
        if self._update_id is not None:
            GLib.source_remove(self._update_id)
            self._update_id = None

    def _update_tick(self):
        """Periodic callback to emit position updates.

        Returns:
            True to continue, False to stop.
        """
        if not self._playing or not self._pipeline:
            return False

        success, position = self._pipeline.query_position(Gst.Format.TIME)
        if success and self.on_position:
            self.on_position(position)

        # Try to discover duration if not yet known
        if self._duration < 0:
            ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
            if ok:
                self._duration = dur
                if self.on_duration:
                    self.on_duration(dur)

        return True

    # ------------------------------------------------------------------
    # Bus signal handlers
    # ------------------------------------------------------------------

    def _on_bus_eos(self, bus, message):
        """Handle end-of-stream."""
        self._playing = False
        self._stop_update_timer()
        if self.on_eos:
            self.on_eos()

    def _on_bus_error(self, bus, message):
        """Handle errors."""
        err, debug = message.parse_error()
        self.stop()
        if self.on_error:
            self.on_error(f"{err.message}")

    def _on_bus_state_changed(self, bus, message):
        """Handle pipeline state changes."""
        if message.src != self._pipeline:
            return
        _, new, _ = message.parse_state_changed()
        if new == Gst.State.PLAYING and self._duration < 0:
            ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
            if ok:
                self._duration = dur
                if self.on_duration:
                    self.on_duration(dur)

    def _on_bus_tag(self, bus, message):
        """Handle stream tag messages."""
        taglist = message.parse_tag()
        tags = {}
        for i in range(taglist.n_tags()):
            tag = taglist.nth_tag_name(i)
            try:
                val = taglist.get_value_index(tag, 0)
                if isinstance(val, str):
                    tags[tag] = val
            except Exception:
                pass
        if tags and self.on_tags:
            self.on_tags(tags)
