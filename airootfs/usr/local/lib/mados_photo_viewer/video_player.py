"""
madOS Photo Viewer - Video Player
===================================

GStreamer-based video player widget with play/pause, seek bar, volume
control, and time display. Embeds a GStreamer video sink inside a GTK
DrawingArea using the waylandsink or gtksink depending on availability.

Uses playbin for automatic codec selection and the GstVideo overlay
interface for embedding.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

# GStreamer may not be available on all systems
GST_AVAILABLE = False
try:
    gi.require_version('Gst', '1.0')
    gi.require_version('GstVideo', '1.0')
    from gi.repository import Gst, GstVideo
    Gst.init(None)
    GST_AVAILABLE = True
except (ValueError, ImportError):
    pass

from gi.repository import Gtk, Gdk, GLib


def format_time(nanoseconds):
    """Convert GStreamer nanoseconds to a human-readable time string.

    Args:
        nanoseconds: Time value in nanoseconds.

    Returns:
        Formatted string like "01:23" or "1:23:45".
    """
    if nanoseconds < 0:
        return "00:00"
    seconds = int(nanoseconds / Gst.SECOND) if GST_AVAILABLE else int(nanoseconds / 1e9)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class VideoPlayer(Gtk.Box):
    """A complete video player widget with controls.

    Contains a video display area, play/pause button, seek slider,
    time label, and volume control.
    """

    def __init__(self):
        """Initialize the video player widget."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._filepath = None
        self._playing = False
        self._duration = -1
        self._seeking = False
        self._update_id = None

        # Video display area
        self._video_area = Gtk.DrawingArea()
        self._video_area.set_hexpand(True)
        self._video_area.set_vexpand(True)
        self._video_area.set_size_request(640, 360)
        self._video_area.connect('realize', self._on_video_realize)
        self._video_area.connect('draw', self._on_video_draw)
        self.pack_start(self._video_area, True, True, 0)

        # Controls bar
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls.get_style_context().add_class('video-controls')

        # Play/Pause button
        self._play_btn = Gtk.Button(label="\u25B6")
        self._play_btn.set_tooltip_text("Play")
        self._play_btn.connect('clicked', self._on_play_clicked)
        controls.pack_start(self._play_btn, False, False, 0)

        # Stop button
        self._stop_btn = Gtk.Button(label="\u25A0")
        self._stop_btn.set_tooltip_text("Stop")
        self._stop_btn.connect('clicked', self._on_stop_clicked)
        controls.pack_start(self._stop_btn, False, False, 0)

        # Time label (current)
        self._time_label = Gtk.Label(label="00:00")
        self._time_label.set_width_chars(8)
        controls.pack_start(self._time_label, False, False, 0)

        # Seek slider
        self._seek_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        self._seek_scale.set_draw_value(False)
        self._seek_scale.set_hexpand(True)
        self._seek_scale.connect('button-press-event', self._on_seek_press)
        self._seek_scale.connect('button-release-event', self._on_seek_release)
        self._seek_scale.connect('value-changed', self._on_seek_changed)
        controls.pack_start(self._seek_scale, True, True, 0)

        # Duration label
        self._duration_label = Gtk.Label(label="00:00")
        self._duration_label.set_width_chars(8)
        controls.pack_start(self._duration_label, False, False, 0)

        # Volume icon
        vol_label = Gtk.Label(label="\U0001F50A")
        controls.pack_start(vol_label, False, False, 0)

        # Volume slider
        self._volume_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        self._volume_scale.set_draw_value(False)
        self._volume_scale.set_value(80)
        self._volume_scale.set_size_request(100, -1)
        self._volume_scale.connect('value-changed', self._on_volume_changed)
        controls.pack_start(self._volume_scale, False, False, 0)

        self.pack_start(controls, False, False, 0)

        # GStreamer pipeline
        self._pipeline = None
        self._bus = None
        self._xid = None

        if GST_AVAILABLE:
            self._setup_pipeline()

    def _setup_pipeline(self):
        """Create the GStreamer playbin pipeline."""
        self._pipeline = Gst.ElementFactory.make('playbin', 'player')
        if self._pipeline is None:
            print("Warning: Could not create GStreamer playbin element")
            return

        # Try to use gtksink first (works well with Wayland)
        gtksink = Gst.ElementFactory.make('gtksink', 'videosink')
        if gtksink is not None:
            self._pipeline.set_property('video-sink', gtksink)
            # Replace the drawing area with gtksink's widget
            video_widget = gtksink.get_property('widget')
            if video_widget is not None:
                self.remove(self._video_area)
                self._video_area = video_widget
                self._video_area.set_hexpand(True)
                self._video_area.set_vexpand(True)
                # Re-pack at the beginning
                self.pack_start(self._video_area, True, True, 0)
                self.reorder_child(self._video_area, 0)
        else:
            # Fall back to autovideosink
            autosink = Gst.ElementFactory.make('autovideosink', 'videosink')
            if autosink:
                self._pipeline.set_property('video-sink', autosink)

        # Set initial volume
        self._pipeline.set_property('volume', 0.8)

        # Bus for messages
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::eos', self._on_eos)
        self._bus.connect('message::error', self._on_error)
        self._bus.connect('message::state-changed', self._on_state_changed)

    def _on_video_realize(self, widget):
        """Handle the video area being realized (for X11 embedding)."""
        window = widget.get_window()
        if window and hasattr(window, 'get_xid'):
            self._xid = window.get_xid()

    def _on_video_draw(self, widget, cr):
        """Draw a dark background on the video area when no video is showing."""
        alloc = widget.get_allocation()
        cr.set_source_rgb(0.18, 0.20, 0.25)
        cr.rectangle(0, 0, alloc.width, alloc.height)
        cr.fill()
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_video(self, filepath):
        """Load and prepare a video file for playback.

        Args:
            filepath: Full path to the video file.

        Returns:
            True if loading started, False if GStreamer is unavailable.
        """
        if not GST_AVAILABLE or self._pipeline is None:
            return False

        self.stop()
        self._filepath = filepath
        uri = GLib.filename_to_uri(filepath, None)
        self._pipeline.set_property('uri', uri)
        self._duration = -1
        self._seek_scale.set_value(0)
        self._time_label.set_text("00:00")
        self._duration_label.set_text("00:00")
        return True

    def play(self):
        """Start or resume playback."""
        if not GST_AVAILABLE or self._pipeline is None:
            return
        self._pipeline.set_state(Gst.State.PLAYING)
        self._playing = True
        self._play_btn.set_label("\u275A\u275A")  # pause symbol
        self._play_btn.set_tooltip_text("Pause")
        self._start_update_timer()

    def pause(self):
        """Pause playback."""
        if not GST_AVAILABLE or self._pipeline is None:
            return
        self._pipeline.set_state(Gst.State.PAUSED)
        self._playing = False
        self._play_btn.set_label("\u25B6")
        self._play_btn.set_tooltip_text("Play")
        self._stop_update_timer()

    def stop(self):
        """Stop playback and reset to the beginning."""
        if not GST_AVAILABLE or self._pipeline is None:
            return
        self._pipeline.set_state(Gst.State.NULL)
        self._playing = False
        self._play_btn.set_label("\u25B6")
        self._play_btn.set_tooltip_text("Play")
        self._seek_scale.set_value(0)
        self._time_label.set_text("00:00")
        self._stop_update_timer()

    def cleanup(self):
        """Release GStreamer resources. Call before destroying the widget."""
        self._stop_update_timer()
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)

    @property
    def is_playing(self):
        """Return True if video is currently playing."""
        return self._playing

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _on_play_clicked(self, button):
        """Toggle play/pause."""
        if self._playing:
            self.pause()
        else:
            self.play()

    def _on_stop_clicked(self, button):
        """Stop playback."""
        self.stop()

    def _on_seek_press(self, widget, event):
        """Mark that user is dragging the seek slider."""
        self._seeking = True
        return False

    def _on_seek_release(self, widget, event):
        """Execute the seek when user releases the slider."""
        self._seeking = False
        if not GST_AVAILABLE or self._pipeline is None:
            return False
        value = self._seek_scale.get_value()
        if self._duration > 0:
            seek_pos = int(value / 100.0 * self._duration)
            self._pipeline.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                seek_pos
            )
        return False

    def _on_seek_changed(self, scale):
        """Update time label while user drags seek slider."""
        if self._seeking and self._duration > 0:
            value = scale.get_value()
            pos = int(value / 100.0 * self._duration)
            self._time_label.set_text(format_time(pos))

    def _on_volume_changed(self, scale):
        """Update playback volume."""
        if self._pipeline:
            vol = scale.get_value() / 100.0
            self._pipeline.set_property('volume', vol)

    # ------------------------------------------------------------------
    # GStreamer bus messages
    # ------------------------------------------------------------------

    def _on_eos(self, bus, message):
        """Handle end-of-stream: stop playback."""
        self.stop()

    def _on_error(self, bus, message):
        """Handle GStreamer errors."""
        err, debug = message.parse_error()
        print(f"GStreamer error: {err.message}")
        print(f"Debug info: {debug}")
        self.stop()

    def _on_state_changed(self, bus, message):
        """Handle state change: query duration when playing starts."""
        if message.src != self._pipeline:
            return
        old, new, pending = message.parse_state_changed()
        if new == Gst.State.PLAYING and self._duration < 0:
            # Query duration
            success, duration = self._pipeline.query_duration(Gst.Format.TIME)
            if success:
                self._duration = duration
                self._duration_label.set_text(format_time(duration))

    # ------------------------------------------------------------------
    # Timer for updating seek position
    # ------------------------------------------------------------------

    def _start_update_timer(self):
        """Start a periodic timer to update the seek slider and time label."""
        if self._update_id is None:
            self._update_id = GLib.timeout_add(250, self._update_position)

    def _stop_update_timer(self):
        """Stop the periodic update timer."""
        if self._update_id is not None:
            GLib.source_remove(self._update_id)
            self._update_id = None

    def _update_position(self):
        """Periodic callback to update seek slider position.

        Returns:
            True to continue the timer, False to stop.
        """
        if not self._playing or self._pipeline is None:
            return False

        if self._seeking:
            return True

        success, position = self._pipeline.query_position(Gst.Format.TIME)
        if success:
            self._time_label.set_text(format_time(position))
            if self._duration > 0:
                percent = (position / self._duration) * 100.0
                self._seek_scale.set_value(percent)

        # Re-query duration if we didn't get it yet
        if self._duration < 0:
            success, duration = self._pipeline.query_duration(Gst.Format.TIME)
            if success:
                self._duration = duration
                self._duration_label.set_text(format_time(duration))

        return True
