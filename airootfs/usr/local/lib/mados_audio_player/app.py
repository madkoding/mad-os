"""
madOS Audio Player - Main Application Window
==============================================

Provides the main GTK3 application window with a Winamp-inspired
compact interface. Features a track info display, seek bar, transport
controls, volume slider, and playlist panel.

The window is designed for the Sway compositor with Nord theme styling
and an app_id of "mados-audio-player" for window management rules.
"""

import os
import sys
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo

from . import __app_id__, __app_name__, __version__
from .backend import MpvBackend
from .playlist import Playlist, Track, format_time, REPEAT_OFF, REPEAT_ALL, REPEAT_ONE
from .translations import (
    TRANSLATIONS, DEFAULT_LANGUAGE,
    get_text, detect_system_language,
)
from .theme import apply_theme, NORD
from .spectrum import SpectrumAnalyzer


class AudioPlayerApp:
    """Main application class for the madOS Audio Player.

    Creates the Winamp-inspired GTK3 window with transport controls,
    track display, seek bar, volume control, and playlist panel.
    """

    # Update interval for position tracking (ms)
    UPDATE_INTERVAL_MS = 250

    def __init__(self, files=None):
        self.language = detect_system_language()
        self._seeking = False
        self._update_timer_id = None
        self._marquee_timer_id = None

        # Initialize backend, playlist, and spectrum analyzer
        self.backend = MpvBackend()
        self.playlist = Playlist()
        self.spectrum = SpectrumAnalyzer()

        # Apply theme
        apply_theme()

        # Build UI
        self._build_window()
        self._build_ui()

        # Start mpv backend
        try:
            self.backend.start()
        except RuntimeError as e:
            self._show_error(str(e))

        # Start spectrum analyzer (non-fatal if cava unavailable)
        self.spectrum.start()

        # Add files from command line
        if files:
            self._add_files_to_playlist(files)
            if not self.playlist.is_empty:
                self.playlist.set_current(0)
                self._play_current()

        # Start periodic state updates
        self._update_timer_id = GLib.timeout_add(
            self.UPDATE_INTERVAL_MS, self._on_update_tick
        )

        # Refresh playlist view with any persisted tracks from DB
        if not self.playlist.is_empty:
            self._refresh_playlist_view()

        self.window.show_all()
        self._update_status(self._t("ready"))

    def _t(self, key):
        """Get translated text for the current language."""
        return get_text(key, self.language)

    # ─── Window Setup ───────────────────────────────────────────

    def _build_window(self):
        """Create and configure the main window."""
        self.window = Gtk.Window()
        self.window.set_title(self._t("title"))
        self.window.set_default_size(480, 200)
        self.window.set_resizable(True)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Set app_id for Sway window management
        self.window.set_wmclass(__app_id__, __app_name__)
        self.window.set_role(__app_id__)

        self.window.connect("delete-event", self._on_delete)
        self.window.connect("destroy", self._on_destroy)

        # Enable drag-and-drop for files
        self.window.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
            Gdk.DragAction.COPY
        )
        self.window.connect("drag-data-received", self._on_drag_data)

    def _build_ui(self):
        """Build the complete user interface."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_box)

        # ── Track Info Display (Winamp title bar area) ──
        main_box.pack_start(self._build_track_display(), False, False, 0)

        # ── Seek Bar ──
        main_box.pack_start(self._build_seek_bar(), False, False, 0)

        # ── Transport Controls + Volume ──
        main_box.pack_start(self._build_controls(), False, False, 0)

        # ── Playlist ──
        main_box.pack_start(self._build_playlist_panel(), True, True, 0)

        # ── Status Bar ──
        main_box.pack_end(self._build_status_bar(), False, False, 0)

    # ─── Track Display ──────────────────────────────────────────

    def _build_track_display(self):
        """Build the track information display area."""
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        frame.set_app_paintable(True)
        ctx = frame.get_style_context()
        ctx.add_class("track-display")
        frame.set_margin_start(6)
        frame.set_margin_end(6)
        frame.set_margin_top(6)
        frame.set_margin_bottom(2)

        # Top row: time display + logo
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        frame.pack_start(top_row, False, False, 0)

        # Time display (large, left)
        self.time_label = Gtk.Label(label="0:00")
        self.time_label.get_style_context().add_class("time-display")
        self.time_label.set_halign(Gtk.Align.START)
        top_row.pack_start(self.time_label, False, False, 4)

        # Separator
        self.time_total_label = Gtk.Label(label="/ 0:00")
        self.time_total_label.get_style_context().add_class("time-total")
        self.time_total_label.set_halign(Gtk.Align.START)
        self.time_total_label.set_valign(Gtk.Align.END)
        self.time_total_label.set_margin_bottom(2)
        top_row.pack_start(self.time_total_label, False, False, 0)

        # Spacer
        top_row.pack_start(Gtk.Box(), True, True, 0)

        # Audio info (right side)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.get_style_context().add_class("audio-info-box")
        info_box.set_valign(Gtk.Align.CENTER)
        top_row.pack_end(info_box, False, False, 4)

        # Bitrate row: number + unit
        bitrate_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        bitrate_row.set_halign(Gtk.Align.END)
        self.bitrate_value_label = Gtk.Label(label="")
        self.bitrate_value_label.get_style_context().add_class("bitrate-label")
        self.bitrate_unit_label = Gtk.Label(label="")
        self.bitrate_unit_label.get_style_context().add_class("info-unit-label")
        self.bitrate_unit_label.set_valign(Gtk.Align.END)
        self.bitrate_unit_label.set_margin_bottom(1)
        bitrate_row.pack_start(self.bitrate_value_label, False, False, 0)
        bitrate_row.pack_start(self.bitrate_unit_label, False, False, 0)
        info_box.pack_start(bitrate_row, False, False, 0)

        # Samplerate row: number + unit
        samplerate_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        samplerate_row.set_halign(Gtk.Align.END)
        self.samplerate_value_label = Gtk.Label(label="")
        self.samplerate_value_label.get_style_context().add_class("samplerate-label")
        self.samplerate_unit_label = Gtk.Label(label="")
        self.samplerate_unit_label.get_style_context().add_class("info-unit-label")
        self.samplerate_unit_label.set_valign(Gtk.Align.END)
        self.samplerate_unit_label.set_margin_bottom(1)
        samplerate_row.pack_start(self.samplerate_value_label, False, False, 0)
        samplerate_row.pack_start(self.samplerate_unit_label, False, False, 0)
        info_box.pack_start(samplerate_row, False, False, 0)

        # Track title (scrolling marquee like Winamp)
        self._marquee_text = __app_name__
        self._marquee_offset = 0
        self._marquee_separator = "    ///    "

        self.title_area = Gtk.DrawingArea()
        self.title_area.set_size_request(-1, 30)
        self.title_area.set_margin_top(12)
        self.title_area.set_margin_start(8)
        self.title_area.set_margin_end(8)
        self.title_area.connect("draw", self._on_title_draw)
        frame.pack_start(self.title_area, False, False, 0)

        # Animation timer (~33ms / 30 FPS to match cava framerate)
        self._tick_count = 0
        self._marquee_timer_id = GLib.timeout_add(33, self._on_marquee_tick)

        # Artist / Album
        self.artist_label = Gtk.Label(label="")
        self.artist_label.get_style_context().add_class("track-artist")
        self.artist_label.set_halign(Gtk.Align.START)
        self.artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.artist_label.set_max_width_chars(60)
        frame.pack_start(self.artist_label, False, False, 0)

        # Connect spectrum drawing (draws behind children)
        frame.connect("draw", self._on_spectrum_draw)

        self._spectrum_frame = frame
        return frame

    # ─── Seek Bar ───────────────────────────────────────────────

    def _build_seek_bar(self):
        """Build the seek/progress bar."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        self.seek_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 0.5
        )
        self.seek_scale.set_draw_value(False)
        self.seek_scale.get_style_context().add_class("seek-bar")
        self.seek_scale.connect("button-press-event", self._on_seek_start)
        self.seek_scale.connect("button-release-event", self._on_seek_end)
        self.seek_scale.connect("change-value", self._on_seek_change)
        box.pack_start(self.seek_scale, True, True, 0)

        return box

    # ─── Transport Controls ─────────────────────────────────────

    def _build_controls(self):
        """Build transport controls and volume slider."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(2)
        box.set_margin_bottom(4)

        # Shuffle button (nf-md-shuffle)
        self.shuffle_btn = self._make_mode_button("\U000f049d", self._t("shuffle"))
        self.shuffle_btn.connect("clicked", self._on_shuffle_clicked)
        box.pack_start(self.shuffle_btn, False, False, 0)

        # Previous button (nf-md-skip_previous)
        prev_btn = self._make_transport_button("\U000f04ae", self._t("previous"))
        prev_btn.connect("clicked", self._on_prev_clicked)
        box.pack_start(prev_btn, False, False, 0)

        # Play/Pause button (nf-md-play)
        self.play_btn = self._make_transport_button("\U000f040a", self._t("play"))
        self.play_btn.get_style_context().add_class("play-btn")
        self.play_btn.connect("clicked", self._on_play_clicked)
        box.pack_start(self.play_btn, False, False, 0)

        # Stop button (nf-md-stop)
        stop_btn = self._make_transport_button("\U000f04db", self._t("stop"))
        stop_btn.get_style_context().add_class("stop-btn")
        stop_btn.connect("clicked", self._on_stop_clicked)
        box.pack_start(stop_btn, False, False, 0)

        # Next button (nf-md-skip_next)
        next_btn = self._make_transport_button("\U000f04ad", self._t("next"))
        next_btn.connect("clicked", self._on_next_clicked)
        box.pack_start(next_btn, False, False, 0)

        # Repeat button (nf-md-repeat)
        self.repeat_btn = self._make_mode_button("\U000f0456", self._t("repeat_off"))
        self.repeat_btn.connect("clicked", self._on_repeat_clicked)
        box.pack_start(self.repeat_btn, False, False, 0)

        # Spacer
        box.pack_start(Gtk.Box(), True, True, 0)

        # Volume icon (nf-md-volume_high)
        self.volume_icon = Gtk.Label(label="\U000f057e")
        self.volume_icon.get_style_context().add_class("volume-icon")
        self.volume_icon.set_valign(Gtk.Align.CENTER)
        event_box = Gtk.EventBox()
        event_box.add(self.volume_icon)
        event_box.connect("button-press-event", self._on_volume_icon_clicked)
        event_box.set_tooltip_text(self._t("mute"))
        box.pack_start(event_box, False, False, 0)

        # Volume slider
        self.volume_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        self.volume_scale.set_value(100)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_size_request(100, -1)
        self.volume_scale.get_style_context().add_class("volume-bar")
        self.volume_scale.connect("value-changed", self._on_volume_changed)
        self.volume_scale.set_tooltip_text(self._t("volume"))
        box.pack_start(self.volume_scale, False, False, 0)

        return box

    def _make_transport_button(self, label, tooltip):
        """Create a styled transport control button."""
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("transport-btn")
        btn.set_tooltip_text(tooltip)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        return btn

    def _make_mode_button(self, label, tooltip):
        """Create a styled mode toggle button."""
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("mode-btn")
        btn.set_tooltip_text(tooltip)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        return btn

    # ─── Playlist Panel ─────────────────────────────────────────

    def _build_playlist_panel(self):
        """Build the playlist panel with track list and action buttons."""
        self._playlist_visible = False

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)

        # Playlist header (clickable to toggle)
        header_event = Gtk.EventBox()
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.get_style_context().add_class("playlist-header")
        header.set_margin_bottom(2)
        header_event.add(header)
        header_event.connect("button-press-event", self._on_playlist_header_clicked)

        self.playlist_toggle_label = Gtk.Label(
            label=f"\U000f040a {self._t('playlist')}"
        )
        self.playlist_toggle_label.get_style_context().add_class("playlist-header")
        header.pack_start(self.playlist_toggle_label, False, False, 4)

        self.playlist_count_label = Gtk.Label(label="(0)")
        self.playlist_count_label.get_style_context().add_class("playlist-count")
        header.pack_start(self.playlist_count_label, False, False, 2)

        header.pack_start(Gtk.Box(), True, True, 0)

        self.playlist_duration_label = Gtk.Label(label="")
        self.playlist_duration_label.get_style_context().add_class("playlist-duration")
        header.pack_end(self.playlist_duration_label, False, False, 4)

        vbox.pack_start(header_event, False, False, 0)

        # Collapsible content container
        self.playlist_content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=0
        )

        # List store: index, display name, duration str, filepath, is_playing
        self.playlist_store = Gtk.ListStore(int, str, str, str, bool)

        # TreeView
        self.playlist_view = Gtk.TreeView(model=self.playlist_store)
        self.playlist_view.get_style_context().add_class("playlist-view")
        self.playlist_view.set_headers_visible(False)
        self.playlist_view.set_activate_on_single_click(False)
        self.playlist_view.connect("row-activated", self._on_playlist_row_activated)
        self.playlist_view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        # Column: Track number
        renderer_num = Gtk.CellRendererText()
        renderer_num.set_property("xalign", 1.0)
        col_num = Gtk.TreeViewColumn("#", renderer_num, text=0)
        col_num.set_fixed_width(30)
        col_num.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.playlist_view.append_column(col_num)

        # Column: Track name
        renderer_name = Gtk.CellRendererText()
        renderer_name.set_property("ellipsize", Pango.EllipsizeMode.END)
        col_name = Gtk.TreeViewColumn("Name", renderer_name, text=1)
        col_name.set_expand(True)
        col_name.set_cell_data_func(renderer_name, self._playlist_name_cell_func)
        self.playlist_view.append_column(col_name)

        # Column: Duration
        renderer_dur = Gtk.CellRendererText()
        renderer_dur.set_property("xalign", 1.0)
        col_dur = Gtk.TreeViewColumn("Dur", renderer_dur, text=2)
        col_dur.set_fixed_width(50)
        col_dur.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.playlist_view.append_column(col_dur)

        # Scrolled window for playlist
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(150)
        scroll.add(self.playlist_view)
        self.playlist_content.pack_start(scroll, True, True, 0)

        vbox.pack_start(self.playlist_content, True, True, 0)

        # Start collapsed
        self.playlist_content.set_no_show_all(True)
        self.playlist_content.hide()

        # Action buttons row (always visible)
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_row.set_margin_top(4)
        btn_row.set_margin_bottom(4)

        add_files_btn = self._make_action_button(
            f"\U000f0415 {self._t('add_files')}", self._on_add_files_clicked
        )
        btn_row.pack_start(add_files_btn, False, False, 0)

        add_folder_btn = self._make_action_button(
            f"\U000f024b {self._t('add_folder')}", self._on_add_folder_clicked
        )
        btn_row.pack_start(add_folder_btn, False, False, 0)

        btn_row.pack_start(Gtk.Box(), True, True, 0)

        remove_btn = self._make_action_button(
            f"\U000f0235 {self._t('remove_selected')}", self._on_remove_clicked
        )
        btn_row.pack_start(remove_btn, False, False, 0)

        clear_btn = self._make_action_button(
            f"\U000f01b4 {self._t('clear_playlist')}", self._on_clear_clicked
        )
        btn_row.pack_start(clear_btn, False, False, 0)

        vbox.pack_start(btn_row, False, False, 0)

        return vbox

    def _make_action_button(self, label, callback):
        """Create a small playlist action button."""
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("playlist-action-btn")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", callback)
        return btn

    def _playlist_name_cell_func(self, column, renderer, model, iter_, data=None):
        """Cell data function to highlight the currently playing track."""
        is_playing = model.get_value(iter_, 4)
        if is_playing:
            renderer.set_property("foreground", NORD['nord8'])
            renderer.set_property("weight", Pango.Weight.BOLD)
        else:
            renderer.set_property("foreground", NORD['nord4'])
            renderer.set_property("weight", Pango.Weight.NORMAL)

    def _on_playlist_header_clicked(self, widget, event):
        """Toggle playlist panel visibility."""
        if self._playlist_visible:
            self._collapse_playlist()
        else:
            self._expand_playlist()

    def _expand_playlist(self):
        """Expand the playlist panel to show tracks."""
        if self._playlist_visible:
            return
        self._playlist_visible = True
        self.playlist_content.set_no_show_all(False)
        self.playlist_content.show_all()
        self.playlist_toggle_label.set_text(
            f"\U000f0140 {self._t('playlist')}"
        )
        self.window.resize(480, 580)

    def _collapse_playlist(self):
        """Collapse the playlist panel to hide tracks."""
        if not self._playlist_visible:
            return
        self._playlist_visible = False
        self.playlist_content.hide()
        self.playlist_content.set_no_show_all(True)
        self.playlist_toggle_label.set_text(
            f"\U000f040a {self._t('playlist')}"
        )
        # Force window to shrink: temporarily set a small size request,
        # then resize and remove the constraint on the next idle cycle.
        self.window.set_size_request(480, 200)
        self.window.resize(480, 200)
        GLib.idle_add(self._reset_size_request_after_collapse)

    def _reset_size_request_after_collapse(self):
        """Remove the fixed size request so the user can still resize freely."""
        self.window.set_size_request(-1, -1)
        return False

    # ─── Status Bar ─────────────────────────────────────────────

    def _build_status_bar(self):
        """Build the bottom status bar."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.get_style_context().add_class("status-bar")

        # Logo
        logo = Gtk.Label(label="madOS Audio Player")
        logo.get_style_context().add_class("logo-area")
        bar.pack_start(logo, False, False, 4)

        bar.pack_start(Gtk.Box(), True, True, 0)

        self.status_label = Gtk.Label(label="")
        self.status_label.get_style_context().add_class("status-bar")
        bar.pack_end(self.status_label, False, False, 4)

        return bar

    # ─── Playback Control Handlers ──────────────────────────────

    def _play_current(self):
        """Play the current track from the playlist."""
        track = self.playlist.get_current_track()
        if not track:
            return

        success = self.backend.play_file(track.filepath)
        if success:
            self.play_btn.set_label("\U000f03e4")
            self._update_track_display(track)
            self._update_playlist_highlight()
            self._update_status(self._t("playing"))

    def _on_play_clicked(self, button):
        """Handle play/pause button click."""
        if not self.backend.is_playing and not self.backend.is_paused:
            # Nothing playing - start from current or first track
            if self.playlist.current_index < 0 and not self.playlist.is_empty:
                self.playlist.set_current(0)
            self._play_current()
        else:
            # Toggle pause
            self.backend.toggle_pause()
            if self.backend.is_paused:
                self.play_btn.set_label("\U000f040a")
                self._update_status(self._t("paused"))
            else:
                self.play_btn.set_label("\U000f03e4")
                self._update_status(self._t("playing"))

    def _on_stop_clicked(self, button):
        """Handle stop button click."""
        self.backend.stop()
        self.play_btn.set_label("\U000f040a")
        self.time_label.set_text("0:00")
        self.time_total_label.set_text("/ 0:00")
        self.seek_scale.set_value(0)
        self.bitrate_value_label.set_text("")
        self.bitrate_unit_label.set_text("")
        self.samplerate_value_label.set_text("")
        self.samplerate_unit_label.set_text("")
        self._update_status(self._t("stopped"))

    def _on_prev_clicked(self, button):
        """Handle previous track button."""
        # If > 3 seconds in, restart current track
        if self.backend.position > 3:
            self.backend.seek(0)
            return

        track = self.playlist.prev_track()
        if track:
            self._play_current()

    def _on_next_clicked(self, button):
        """Handle next track button."""
        track = self.playlist.next_track()
        if track:
            self._play_current()
        else:
            self._on_stop_clicked(None)

    def _on_shuffle_clicked(self, button):
        """Toggle shuffle mode."""
        self.playlist.toggle_shuffle()
        ctx = button.get_style_context()
        if self.playlist.shuffle:
            ctx.add_class("active")
            button.set_tooltip_text(f"{self._t('shuffle')}: ON")
        else:
            ctx.remove_class("active")
            button.set_tooltip_text(f"{self._t('shuffle')}: OFF")

    def _on_repeat_clicked(self, button):
        """Cycle repeat mode."""
        mode = self.playlist.cycle_repeat()
        ctx = button.get_style_context()
        if mode == REPEAT_OFF:
            button.set_label("\U000f0456")
            ctx.remove_class("active")
            button.set_tooltip_text(self._t("repeat_off"))
        elif mode == REPEAT_ALL:
            button.set_label("\U000f0456")
            ctx.add_class("active")
            button.set_tooltip_text(self._t("repeat_all"))
        elif mode == REPEAT_ONE:
            button.set_label("\U000f0458")
            ctx.add_class("active")
            button.set_tooltip_text(self._t("repeat_one"))

    # ─── Seek Handlers ──────────────────────────────────────────

    def _on_seek_start(self, widget, event):
        """User started seeking - pause position updates."""
        self._seeking = True

    def _on_seek_end(self, widget, event):
        """User finished seeking - apply the new position."""
        self._seeking = False
        if self.backend.duration > 0:
            fraction = self.seek_scale.get_value() / 100.0
            target = fraction * self.backend.duration
            self.backend.seek(target)

    def _on_seek_change(self, widget, scroll_type, value):
        """Update time display during seek."""
        if self._seeking and self.backend.duration > 0:
            fraction = max(0.0, min(1.0, value / 100.0))
            pos = fraction * self.backend.duration
            self.time_label.set_text(format_time(pos))

    # ─── Volume Handlers ────────────────────────────────────────

    def _on_volume_changed(self, scale):
        """Handle volume slider change."""
        vol = int(scale.get_value())
        self.backend.set_volume(vol)
        self._update_volume_icon(vol, self.backend.is_muted)

    def _on_volume_icon_clicked(self, widget, event):
        """Toggle mute on volume icon click."""
        self.backend.toggle_mute()
        vol = int(self.volume_scale.get_value())
        self._update_volume_icon(vol, self.backend.is_muted)

    def _update_volume_icon(self, volume, muted):
        """Update the volume icon based on level and mute state."""
        ctx = self.volume_icon.get_style_context()
        if muted:
            self.volume_icon.set_text("\U000f0581")
            ctx.add_class("muted")
        elif volume == 0:
            self.volume_icon.set_text("\U000f0e08")
            ctx.remove_class("muted")
        elif volume < 50:
            self.volume_icon.set_text("\U000f057f")
            ctx.remove_class("muted")
        else:
            self.volume_icon.set_text("\U000f057e")
            ctx.remove_class("muted")

    # ─── Playlist Handlers ──────────────────────────────────────

    def _on_playlist_row_activated(self, treeview, path, column):
        """Handle double-click on playlist row to play that track."""
        index = path.get_indices()[0]
        self.playlist.set_current(index)
        self._play_current()

    def _on_add_files_clicked(self, button):
        """Open file chooser to add audio files."""
        dialog = Gtk.FileChooserDialog(
            title=self._t("select_audio_files"),
            parent=self.window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            self._t("cancel"), Gtk.ResponseType.CANCEL,
            self._t("open"), Gtk.ResponseType.OK,
        )
        dialog.set_select_multiple(True)

        # Audio file filter
        audio_filter = Gtk.FileFilter()
        audio_filter.set_name(self._t("audio_files"))
        for ext in sorted(MpvBackend.AUDIO_EXTENSIONS):
            audio_filter.add_pattern(f"*{ext}")
        dialog.add_filter(audio_filter)

        # All files filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name(self._t("all_files"))
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            files = dialog.get_filenames()
            self._add_files_to_playlist(files)
        dialog.destroy()

    def _on_add_folder_clicked(self, button):
        """Open folder chooser to add all audio files from a directory."""
        dialog = Gtk.FileChooserDialog(
            title=self._t("select_folder"),
            parent=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            self._t("cancel"), Gtk.ResponseType.CANCEL,
            self._t("open"), Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder = dialog.get_filename()
            if folder:
                count = self.playlist.add_directory(folder)
                self._refresh_playlist_view()
                self._update_status(
                    f"{count} {self._t('tracks')}"
                )
                # Auto-expand playlist to show added tracks
                if count > 0:
                    self._expand_playlist()
        dialog.destroy()

    def _on_remove_clicked(self, button):
        """Remove selected tracks from the playlist."""
        selection = self.playlist_view.get_selection()
        model, paths = selection.get_selected_rows()
        indices = [p.get_indices()[0] for p in paths]
        self.playlist.remove_indices(indices)
        self._refresh_playlist_view()

    def _on_clear_clicked(self, button):
        """Clear the entire playlist."""
        self.backend.stop()
        self.playlist.clear()
        self._refresh_playlist_view()
        self.play_btn.set_label("\U000f040a")
        self._marquee_text = __app_name__
        self._marquee_offset = 0
        self.title_area.queue_draw()
        self.artist_label.set_text("")
        self.time_label.set_text("0:00")
        self.time_total_label.set_text("/ 0:00")
        self.seek_scale.set_value(0)
        self.bitrate_value_label.set_text("")
        self.bitrate_unit_label.set_text("")
        self.samplerate_value_label.set_text("")
        self.samplerate_unit_label.set_text("")
        self._update_status(self._t("ready"))

    def _add_files_to_playlist(self, filepaths):
        """Add files to playlist, handling both files and directories."""
        for fp in filepaths:
            if os.path.isdir(fp):
                self.playlist.add_directory(fp)
            elif os.path.isfile(fp) and MpvBackend.is_audio_file(fp):
                self.playlist.add_file(fp)
        self._refresh_playlist_view()
        # Auto-expand playlist to show the newly added tracks
        if not self.playlist.is_empty:
            self._expand_playlist()

    def _refresh_playlist_view(self):
        """Refresh the playlist TreeView from the playlist model."""
        self.playlist_store.clear()
        for i, track in enumerate(self.playlist.tracks):
            is_current = (i == self.playlist.current_index)
            dur_str = format_time(track.duration) if track.duration > 0 else ""
            self.playlist_store.append([
                i + 1,
                track.display_name(),
                dur_str,
                track.filepath,
                is_current,
            ])
        self.playlist_count_label.set_text(f"({self.playlist.count})")

    def _update_playlist_highlight(self):
        """Update which row is highlighted as playing."""
        for row in self.playlist_store:
            idx = row[0] - 1  # 1-indexed display
            row[4] = (idx == self.playlist.current_index)
        # Scroll to current track
        if 0 <= self.playlist.current_index < len(self.playlist_store):
            path = Gtk.TreePath.new_from_indices([self.playlist.current_index])
            self.playlist_view.scroll_to_cell(path, None, False, 0, 0)

    # ─── Drag and Drop ──────────────────────────────────────────

    def _on_drag_data(self, widget, drag_context, x, y, data, info, time):
        """Handle files dragged onto the window."""
        uris = data.get_uris()
        files = []
        for uri in uris:
            if uri.startswith("file://"):
                from urllib.parse import unquote
                path = unquote(uri[7:])
                files.append(path)
        if files:
            self._add_files_to_playlist(files)
            if not self.backend.is_playing and not self.playlist.is_empty:
                if self.playlist.current_index < 0:
                    self.playlist.set_current(0)
                self._play_current()

    # ─── Periodic Update ────────────────────────────────────────

    def _on_update_tick(self):
        """Periodic callback to update UI from backend state."""
        if not self.backend.is_playing and not self.backend.is_paused:
            # Check if track finished
            if self.backend.current_file and self.backend.is_track_finished():
                self._on_track_finished()
            return True

        self.backend.update_state()

        # Update seek bar
        if not self._seeking and self.backend.duration > 0:
            fraction = (self.backend.position / self.backend.duration) * 100
            self.seek_scale.set_value(fraction)
            self.time_label.set_text(format_time(self.backend.position))
            self.time_total_label.set_text(
                f"/ {format_time(self.backend.duration)}"
            )

        # Update audio info
        info = self.backend.get_audio_info()
        if info.get('bitrate'):
            parts = info['bitrate'].split(' ', 1)
            self.bitrate_value_label.set_text(parts[0])
            self.bitrate_unit_label.set_text(parts[1] if len(parts) > 1 else "")
        if info.get('samplerate'):
            parts = info['samplerate'].split(' ', 1)
            self.samplerate_value_label.set_text(parts[0])
            self.samplerate_unit_label.set_text(parts[1] if len(parts) > 1 else "")

        # Update metadata if changed
        meta = self.backend.get_formatted_metadata()
        current_track = self.playlist.get_current_track()
        if current_track and meta.get('title'):
            self.playlist.update_track_metadata(current_track, meta)
            self._update_track_display(current_track)

        # Update track duration in playlist
        if current_track and self.backend.duration > 0:
            self.playlist.update_track_duration(
                current_track, self.backend.duration
            )
            self._update_playlist_highlight()

        # Check if track finished
        if self.backend.is_track_finished():
            self._on_track_finished()

        return True

    def _on_track_finished(self):
        """Handle end of track - advance to next."""
        track = self.playlist.next_track()
        if track:
            self._play_current()
        else:
            self._on_stop_clicked(None)

    def _update_track_display(self, track):
        """Update the track info display area.

        Args:
            track: A Track object with title/artist info.
        """
        new_text = track.title or self._t("unknown_title")
        if new_text != self._marquee_text:
            self._marquee_text = new_text
            self._marquee_offset = 0
        if track.artist:
            self.artist_label.set_text(
                f"{track.artist}"
                + (f" — {track.album}" if track.album else "")
            )
        else:
            self.artist_label.set_text("")

    def _update_status(self, text):
        """Update the status bar text."""
        self.status_label.set_text(text)

    # ─── Spectrum Analyzer Drawing ──────────────────────────────

    def _on_spectrum_draw(self, widget, cr):
        """Draw the FFT spectrum analyzer as background of track display.

        Renders LED-style frequency bars behind the track info text.
        Uses cava data when available, draws only the dark background
        when spectrum data is not active.
        """
        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height

        # Draw dark background (replaces CSS background)
        cr.set_source_rgba(22 / 255, 26 / 255, 33 / 255, 0.92)
        # Rounded rectangle (matches CSS border-radius: 3px)
        radius = 3
        cr.new_sub_path()
        cr.arc(w - radius, radius, radius, -1.5708, 0)
        cr.arc(w - radius, h - radius, radius, 0, 1.5708)
        cr.arc(radius, h - radius, radius, 1.5708, 3.14159)
        cr.arc(radius, radius, radius, 3.14159, 4.71239)
        cr.close_path()
        cr.fill()

        bars = self.spectrum.bars
        if not bars or not self.spectrum.is_active:
            return False  # No spectrum data — just dark background

        num_bars = len(bars)
        if num_bars == 0:
            return False

        # Layout calculations
        padding_x = 10
        padding_bottom = 6
        usable_w = w - 2 * padding_x
        usable_h = h - padding_bottom - 4  # top margin

        # LED segment dimensions
        led_h = 3       # height of each LED segment
        led_gap = 1     # gap between segments
        led_step = led_h + led_gap  # total step per segment

        # Bar dimensions
        total_bar_gap = num_bars - 1
        bar_gap = 2
        bar_w = max(2, (usable_w - total_bar_gap * bar_gap) / num_bars)

        max_segments = max(1, int(usable_h / led_step))

        # Winamp-style LED colors (green → yellow → red)
        # Nord palette: nord14=green, nord13=yellow, nord11=red
        colors_rgb = {
            'green':  (163 / 255, 190 / 255, 140 / 255),
            'yellow': (235 / 255, 203 / 255, 139 / 255),
            'red':    (191 / 255, 97 / 255, 106 / 255),
        }

        for i, bar_val in enumerate(bars):
            x = padding_x + i * (bar_w + bar_gap)
            active_segments = int(bar_val * max_segments)

            for seg in range(active_segments):
                # Position from bottom up
                y = h - padding_bottom - (seg + 1) * led_step

                # Color based on segment height ratio
                ratio = seg / max(1, max_segments - 1)
                if ratio < 0.45:
                    r, g, b = colors_rgb['green']
                elif ratio < 0.75:
                    r, g, b = colors_rgb['yellow']
                else:
                    r, g, b = colors_rgb['red']

                # Opacity: very subtle background effect
                alpha = 0.06 + 0.08 * (seg / max(1, max_segments))

                cr.set_source_rgba(r, g, b, alpha)
                # Small rounded rectangle for each LED
                led_radius = 1
                cr.new_sub_path()
                cr.arc(x + bar_w - led_radius, y + led_radius, led_radius, -1.5708, 0)
                cr.arc(x + bar_w - led_radius, y + led_h - led_radius, led_radius, 0, 1.5708)
                cr.arc(x + led_radius, y + led_h - led_radius, led_radius, 1.5708, 3.14159)
                cr.arc(x + led_radius, y + led_radius, led_radius, 3.14159, 4.71239)
                cr.close_path()
                cr.fill()

        # Draw peak indicators
        peaks = self.spectrum.peaks
        for i, peak_val in enumerate(peaks):
            if peak_val <= 0:
                continue
            x = padding_x + i * (bar_w + bar_gap)
            peak_seg = int(peak_val * max_segments)
            if peak_seg >= max_segments:
                peak_seg = max_segments - 1
            y = h - padding_bottom - (peak_seg + 1) * led_step

            ratio = peak_seg / max(1, max_segments - 1)
            if ratio < 0.45:
                r, g, b = colors_rgb['green']
            elif ratio < 0.75:
                r, g, b = colors_rgb['yellow']
            else:
                r, g, b = colors_rgb['red']

            cr.set_source_rgba(r, g, b, 0.2)
            cr.rectangle(x, y, bar_w, led_h)
            cr.fill()

        return False  # Let GTK continue drawing children on top

    # ─── Marquee Scrolling Title ────────────────────────────────

    def _on_marquee_tick(self):
        """Advance animation at 30 FPS; marquee scrolls every other tick."""
        self._tick_count += 1
        # Marquee scrolls every 2 ticks (~66ms) to keep same visual speed
        if self._tick_count % 2 == 0:
            self._marquee_offset += 1
            self.title_area.queue_draw()
        # Update spectrum bars every tick (30 FPS)
        self.spectrum.update()
        # Redraw the track-display frame for spectrum bars
        if hasattr(self, '_spectrum_frame'):
            self._spectrum_frame.queue_draw()
        return True

    def _on_title_draw(self, widget, cr):
        """Draw the scrolling title text using cairo + Pango."""
        alloc = widget.get_allocation()
        width = alloc.width
        height = alloc.height

        # Create Pango layout for measuring and drawing
        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription.from_string(
            "Doto 17"
        )
        layout.set_font_description(font_desc)

        text = self._marquee_text
        layout.set_text(text, -1)
        text_width, text_height = layout.get_pixel_size()

        # Nord8 cyan color
        r, g, b = 136 / 255, 192 / 255, 208 / 255

        # Vertical center
        y = (height - text_height) / 2

        if text_width <= width:
            # Text fits — draw static, no scroll
            # Glow layers (outer to inner)
            cr.save()
            for alpha, spread in [(0.15, 6), (0.3, 3), (0.5, 1.5)]:
                cr.set_source_rgba(r, g, b, alpha)
                cr.move_to(spread * 0.3, y + spread * 0.15)
                PangoCairo.show_layout(cr, layout)
                cr.move_to(-spread * 0.3, y - spread * 0.15)
                PangoCairo.show_layout(cr, layout)
            cr.restore()
            # Main text
            cr.move_to(0, y)
            cr.set_source_rgb(r, g, b)
            PangoCairo.show_layout(cr, layout)
        else:
            # Text overflows — Winamp-style seamless loop scroll
            full_text = text + self._marquee_separator + text
            layout.set_text(full_text, -1)
            full_width, _ = layout.get_pixel_size()
            # The cycle is one copy of "text + separator"
            cycle_width = full_width - text_width

            offset = self._marquee_offset % cycle_width if cycle_width > 0 else 0

            # Clip to widget bounds
            cr.rectangle(0, 0, width, height)
            cr.clip()

            # Glow layers
            cr.save()
            for alpha, spread in [(0.15, 6), (0.3, 3), (0.5, 1.5)]:
                cr.set_source_rgba(r, g, b, alpha)
                cr.move_to(-offset + spread * 0.3, y + spread * 0.15)
                PangoCairo.show_layout(cr, layout)
                cr.move_to(-offset - spread * 0.3, y - spread * 0.15)
                PangoCairo.show_layout(cr, layout)
            cr.restore()

            # Main text
            cr.move_to(-offset, y)
            cr.set_source_rgb(r, g, b)
            PangoCairo.show_layout(cr, layout)

    # ─── Error Dialog ───────────────────────────────────────────

    def _show_error(self, message):
        """Show a simple error dialog."""
        dialog = Gtk.MessageDialog(
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format=message,
        )
        dialog.run()
        dialog.destroy()

    # ─── Cleanup ────────────────────────────────────────────────

    def _on_delete(self, widget, event):
        """Handle window close request."""
        self._cleanup()
        return False

    def _on_destroy(self, widget):
        """Handle window destroy."""
        self._cleanup()
        Gtk.main_quit()

    def _cleanup(self):
        """Clean up resources before exit."""
        if self._update_timer_id:
            GLib.source_remove(self._update_timer_id)
            self._update_timer_id = None

        if self._marquee_timer_id:
            GLib.source_remove(self._marquee_timer_id)
            self._marquee_timer_id = None

        self.spectrum.stop()
        self.playlist.close()
        self.backend.cleanup()
