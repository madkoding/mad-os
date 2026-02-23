"""
madOS Video Player - Main Application Window
==============================================

VLC-inspired video player window with Nord theme, GStreamer playback,
menu bar, transport controls, seek bar, volume control, and playlist
sidebar. Supports keyboard shortcuts, drag-and-drop, and fullscreen.
"""

import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from . import __version__, __app_id__, __app_name__
from .theme import apply_theme
from .translations import detect_system_language, get_text, get_languages
from .playlist import Playlist, RepeatMode, is_media_file, ALL_MEDIA_EXTENSIONS
from .player import PlayerEngine, format_time, GST_AVAILABLE
from .database import PlaylistDB

if GST_AVAILABLE:
    from gi.repository import Gst


class VideoPlayerApp(Gtk.Window):
    """Main video player application window."""

    def __init__(self, initial_files=None):
        """Initialize the video player application.

        Args:
            initial_files: Optional list of file paths to load into playlist.
        """
        super().__init__(title=__app_name__)

        self._language = detect_system_language()
        self._fullscreen_active = False
        self._playlist_visible = False
        self._controls_visible = True
        self._hide_controls_id = None
        self._programmatic_seek_update = False
        self._seek_debounce_id = None

        # Apply Nord theme
        apply_theme()

        # Player engine and playlist
        self._engine = PlayerEngine()
        self._engine.on_eos = self._on_eos
        self._engine.on_error = self._on_error
        self._engine.on_state = self._on_state_changed
        self._engine.on_duration = self._on_duration
        self._engine.on_position = self._on_position
        self._engine.on_tags = self._on_tags
        self._playlist = Playlist()
        self._db = PlaylistDB()

        # Window setup
        self.set_default_size(640, 400)
        self.set_wmclass(__app_id__, __app_name__)
        self.set_icon_name("multimedia-video-player")
        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self._on_key_press)

        # Enable drag-and-drop
        self.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
            Gdk.DragAction.COPY,
        )
        self.connect("drag-data-received", self._on_drag_data)

        # Build UI
        self._build_ui()

        # Load initial files
        if initial_files:
            for f in initial_files:
                abspath = os.path.abspath(f)
                if os.path.isdir(abspath):
                    self._playlist.add_directory(abspath)
                elif os.path.isfile(abspath):
                    self._playlist.add_file(abspath)
            self._refresh_playlist_view()
        else:
            # Restore session playlist if no files given
            self._restore_session()

        # Show window first so gtksink widget is realized before playback
        self.show_all()
        self._playlist_panel.set_visible(False)
        self._update_title()

        # Start playback after window is visible (gtksink needs realized widget)
        if initial_files and not self._playlist.is_empty:
            GLib.idle_add(self._play_current)

    def _t(self, key):
        """Get translated string."""
        return get_text(key, self._language)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build the complete user interface."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # Menu bar
        self._menu_bar = self._build_menu_bar()
        vbox.pack_start(self._menu_bar, False, False, 0)

        # Main content: video + playlist
        self._content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(self._content_paned, True, True, 0)

        # Video area container
        video_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._content_paned.pack1(video_box, True, False)

        # Video display
        self._video_container = Gtk.Overlay()
        video_box.pack_start(self._video_container, True, True, 0)

        if self._engine.video_widget:
            self._video_display = self._engine.video_widget
            self._video_display.set_hexpand(True)
            self._video_display.set_vexpand(True)
        else:
            self._video_display = Gtk.DrawingArea()
            self._video_display.set_hexpand(True)
            self._video_display.set_vexpand(True)
            self._video_display.connect("draw", self._on_video_draw)

        self._video_display.get_style_context().add_class("video-area")
        self._video_container.add(self._video_display)

        # Placeholder reference (no overlay displayed)
        self._placeholder = Gtk.Box()
        self._placeholder_text = Gtk.Label()

        # Double-click on video for fullscreen
        self._video_event = Gtk.EventBox()
        self._video_event.set_above_child(False)
        self._video_event.connect("button-press-event", self._on_video_click)

        # Seek bar
        self._build_seek_bar(video_box)

        # Transport controls
        self._build_controls(video_box)

        # Playlist sidebar
        self._playlist_panel = self._build_playlist_panel()
        self._content_paned.pack2(self._playlist_panel, False, False)
        self._content_paned.set_position(440)

        # Status bar
        self._build_status_bar(vbox)

    def _build_menu_bar(self):
        """Build the menu bar."""
        menu_bar = Gtk.MenuBar()

        # --- File menu ---
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label=self._t("file"))
        file_item.set_submenu(file_menu)

        open_item = Gtk.MenuItem(label=self._t("open_file"))
        open_item.connect("activate", self._on_open_file)
        file_menu.append(open_item)

        open_dir_item = Gtk.MenuItem(label=self._t("open_directory"))
        open_dir_item.connect("activate", self._on_open_directory)
        file_menu.append(open_dir_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        save_pl_item = Gtk.MenuItem(label=self._t("save_playlist"))
        save_pl_item.connect("activate", lambda w: self._on_save_playlist_dialog())
        file_menu.append(save_pl_item)

        load_pl_item = Gtk.MenuItem(label=self._t("load_playlist"))
        load_pl_item.connect("activate", lambda w: self._on_load_playlist_dialog())
        file_menu.append(load_pl_item)

        manage_pl_item = Gtk.MenuItem(label=self._t("manage_playlists"))
        manage_pl_item.connect("activate", lambda w: self._on_manage_playlists_dialog())
        file_menu.append(manage_pl_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label=self._t("quit"))
        quit_item.connect("activate", lambda w: self._on_destroy(w))
        file_menu.append(quit_item)

        menu_bar.append(file_item)

        # --- Playback menu ---
        playback_menu = Gtk.Menu()
        playback_item = Gtk.MenuItem(label=self._t("playback"))
        playback_item.set_submenu(playback_menu)

        play_item = Gtk.MenuItem(label=self._t("play") + " / " + self._t("pause"))
        play_item.connect("activate", lambda w: self._engine.toggle_play_pause())
        playback_menu.append(play_item)

        stop_item = Gtk.MenuItem(label=self._t("stop"))
        stop_item.connect("activate", lambda w: self._engine.stop())
        playback_menu.append(stop_item)

        playback_menu.append(Gtk.SeparatorMenuItem())

        next_item = Gtk.MenuItem(label=self._t("next_track"))
        next_item.connect("activate", lambda w: self._on_next())
        playback_menu.append(next_item)

        prev_item = Gtk.MenuItem(label=self._t("prev_track"))
        prev_item.connect("activate", lambda w: self._on_previous())
        playback_menu.append(prev_item)

        playback_menu.append(Gtk.SeparatorMenuItem())

        fwd10_item = Gtk.MenuItem(label=self._t("forward_10"))
        fwd10_item.connect("activate", lambda w: self._seek_relative(10))
        playback_menu.append(fwd10_item)

        bwd10_item = Gtk.MenuItem(label=self._t("backward_10"))
        bwd10_item.connect("activate", lambda w: self._seek_relative(-10))
        playback_menu.append(bwd10_item)

        playback_menu.append(Gtk.SeparatorMenuItem())

        speed_up_item = Gtk.MenuItem(label=self._t("speed_up"))
        speed_up_item.connect("activate", lambda w: self._on_speed_up())
        playback_menu.append(speed_up_item)

        speed_down_item = Gtk.MenuItem(label=self._t("speed_down"))
        speed_down_item.connect("activate", lambda w: self._on_speed_down())
        playback_menu.append(speed_down_item)

        normal_speed_item = Gtk.MenuItem(label=self._t("normal_speed"))
        normal_speed_item.connect("activate", lambda w: self._on_reset_speed())
        playback_menu.append(normal_speed_item)

        menu_bar.append(playback_item)

        # --- Audio menu ---
        audio_menu = Gtk.Menu()
        audio_item = Gtk.MenuItem(label=self._t("audio"))
        audio_item.set_submenu(audio_menu)

        mute_item = Gtk.MenuItem(label=self._t("mute"))
        mute_item.connect("activate", lambda w: self._on_toggle_mute())
        audio_menu.append(mute_item)

        vol_up_item = Gtk.MenuItem(label=self._t("volume_up"))
        vol_up_item.connect("activate", lambda w: self._adjust_volume(0.1))
        audio_menu.append(vol_up_item)

        vol_down_item = Gtk.MenuItem(label=self._t("volume_down"))
        vol_down_item.connect("activate", lambda w: self._adjust_volume(-0.1))
        audio_menu.append(vol_down_item)

        menu_bar.append(audio_item)

        # --- Video menu ---
        video_menu = Gtk.Menu()
        video_item = Gtk.MenuItem(label=self._t("video"))
        video_item.set_submenu(video_menu)

        fullscreen_item = Gtk.MenuItem(label=self._t("fullscreen"))
        fullscreen_item.connect("activate", lambda w: self._toggle_fullscreen())
        video_menu.append(fullscreen_item)

        menu_bar.append(video_item)

        # --- Subtitle menu ---
        sub_menu = Gtk.Menu()
        sub_item = Gtk.MenuItem(label=self._t("subtitle"))
        sub_item.set_submenu(sub_menu)

        open_sub_item = Gtk.MenuItem(label=self._t("open_subtitle"))
        open_sub_item.connect("activate", self._on_open_subtitle)
        sub_menu.append(open_sub_item)

        menu_bar.append(sub_item)

        # --- View menu ---
        view_menu = Gtk.Menu()
        view_item = Gtk.MenuItem(label=self._t("view"))
        view_item.set_submenu(view_menu)

        playlist_toggle_item = Gtk.MenuItem(label=self._t("show_playlist"))
        playlist_toggle_item.connect("activate", lambda w: self._toggle_playlist())
        self._playlist_menu_item = playlist_toggle_item
        view_menu.append(playlist_toggle_item)

        menu_bar.append(view_item)

        # --- Help menu ---
        help_menu = Gtk.Menu()
        help_item = Gtk.MenuItem(label=self._t("help"))
        help_item.set_submenu(help_menu)

        about_item = Gtk.MenuItem(label=self._t("about"))
        about_item.connect("activate", self._on_about)
        help_menu.append(about_item)

        menu_bar.append(help_item)

        return menu_bar

    def _build_placeholder(self):
        """Build the placeholder overlay shown when no video is loaded."""
        overlay_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        overlay_box.set_halign(Gtk.Align.CENTER)
        overlay_box.set_valign(Gtk.Align.CENTER)
        overlay_box.get_style_context().add_class("video-placeholder")

        icon = Gtk.Label(label="\u25b6")
        icon.get_style_context().add_class("placeholder-icon")
        overlay_box.pack_start(icon, False, False, 0)

        text = Gtk.Label(label=self._t("drop_files_here"))
        text.get_style_context().add_class("placeholder-text")
        overlay_box.pack_start(text, False, False, 0)
        self._placeholder_text = text

        return overlay_box

    def _build_seek_bar(self, parent):
        """Build the seek bar area."""
        seek_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        seek_box.get_style_context().add_class("seek-bar")

        # Current time
        self._time_label = Gtk.Label(label="00:00")
        self._time_label.get_style_context().add_class("time-label")
        self._time_label.set_width_chars(8)
        seek_box.pack_start(self._time_label, False, False, 0)

        # Seek slider
        self._seek_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 1000, 1
        )
        self._seek_scale.set_draw_value(False)
        self._seek_scale.set_hexpand(True)
        self._seek_scale.get_style_context().add_class("seek-slider")
        self._seek_scale.connect("value-changed", self._on_seek_changed)
        seek_box.pack_start(self._seek_scale, True, True, 0)

        # Duration
        self._duration_label = Gtk.Label(label="00:00")
        self._duration_label.get_style_context().add_class("time-label")
        self._duration_label.set_width_chars(8)
        seek_box.pack_start(self._duration_label, False, False, 0)

        parent.pack_start(seek_box, False, False, 0)

    def _build_controls(self, parent):
        """Build the transport control bar."""
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.get_style_context().add_class("control-bar")
        self._controls_bar = controls

        # Previous
        prev_btn = Gtk.Button(label="\u23ee")
        prev_btn.set_tooltip_text(self._t("prev_track"))
        prev_btn.get_style_context().add_class("transport-btn")
        prev_btn.connect("clicked", lambda w: self._on_previous())
        controls.pack_start(prev_btn, False, False, 0)

        # Stop
        stop_btn = Gtk.Button(label="\u23f9")
        stop_btn.set_tooltip_text(self._t("stop"))
        stop_btn.get_style_context().add_class("transport-btn")
        stop_btn.connect("clicked", lambda w: self._engine.stop())
        controls.pack_start(stop_btn, False, False, 0)

        # Play/Pause
        self._play_btn = Gtk.Button(label="\u25b6")
        self._play_btn.set_tooltip_text(self._t("play"))
        self._play_btn.get_style_context().add_class("transport-btn")
        self._play_btn.get_style_context().add_class("play-btn")
        self._play_btn.connect("clicked", lambda w: self._on_play_clicked())
        controls.pack_start(self._play_btn, False, False, 0)

        # Next
        next_btn = Gtk.Button(label="\u23ed")
        next_btn.set_tooltip_text(self._t("next_track"))
        next_btn.get_style_context().add_class("transport-btn")
        next_btn.connect("clicked", lambda w: self._on_next())
        controls.pack_start(next_btn, False, False, 0)

        # Separator
        controls.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Now playing label
        self._now_playing_label = Gtk.Label(label=self._t("no_file"))
        self._now_playing_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._now_playing_label.set_hexpand(True)
        self._now_playing_label.set_xalign(0.0)
        self._now_playing_label.get_style_context().add_class("title-label")
        controls.pack_start(self._now_playing_label, True, True, 4)

        # Speed label
        self._speed_label = Gtk.Label(label="1.0x")
        self._speed_label.get_style_context().add_class("speed-label")
        self._speed_label.set_width_chars(5)
        controls.pack_start(self._speed_label, False, False, 0)

        # Separator
        controls.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Shuffle button
        self._shuffle_btn = Gtk.ToggleButton(label="\u21c6")
        self._shuffle_btn.set_tooltip_text(self._t("shuffle"))
        self._shuffle_btn.connect("toggled", self._on_shuffle_toggled)
        controls.pack_start(self._shuffle_btn, False, False, 0)

        # Repeat button
        self._repeat_btn = Gtk.Button(label="\u21bb")
        self._repeat_btn.set_tooltip_text(self._t("repeat_off"))
        self._repeat_btn.connect("clicked", self._on_repeat_clicked)
        controls.pack_start(self._repeat_btn, False, False, 0)

        # Separator
        controls.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Volume mute button
        self._mute_btn = Gtk.Button(label="\U0001f50a")
        self._mute_btn.set_tooltip_text(self._t("volume"))
        self._mute_btn.connect("clicked", lambda w: self._on_toggle_mute())
        controls.pack_start(self._mute_btn, False, False, 0)

        # Volume slider
        self._volume_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        self._volume_scale.set_draw_value(False)
        self._volume_scale.set_value(80)
        self._volume_scale.set_size_request(100, -1)
        self._volume_scale.get_style_context().add_class("volume-slider")
        self._volume_scale.connect("value-changed", self._on_volume_changed)
        controls.pack_start(self._volume_scale, False, False, 0)

        # Separator
        controls.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Playlist toggle
        self._playlist_btn = Gtk.ToggleButton(label="\u2261")
        self._playlist_btn.set_tooltip_text(self._t("playlist"))
        self._playlist_btn.set_active(False)
        self._playlist_btn.connect("toggled", self._on_playlist_toggled)
        controls.pack_start(self._playlist_btn, False, False, 0)

        # Fullscreen
        fs_btn = Gtk.Button(label="\u2922")
        fs_btn.set_tooltip_text(self._t("fullscreen"))
        fs_btn.connect("clicked", lambda w: self._toggle_fullscreen())
        controls.pack_start(fs_btn, False, False, 0)

        parent.pack_start(controls, False, False, 0)

    def _build_playlist_panel(self):
        """Build the playlist sidebar panel."""
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.get_style_context().add_class("playlist-panel")
        panel.set_size_request(280, -1)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.get_style_context().add_class("playlist-header")

        title = Gtk.Label(label=self._t("playlist"))
        title.set_hexpand(True)
        title.set_xalign(0.0)
        header.pack_start(title, True, True, 0)
        self._playlist_title_label = title

        # Playlist toolbar buttons
        add_btn = Gtk.Button(label="+")
        add_btn.set_tooltip_text(self._t("add_files"))
        add_btn.connect("clicked", self._on_open_file)
        header.pack_start(add_btn, False, False, 0)

        clear_btn = Gtk.Button(label="\u2715")
        clear_btn.set_tooltip_text(self._t("clear_playlist"))
        clear_btn.connect("clicked", self._on_clear_playlist)
        header.pack_start(clear_btn, False, False, 0)

        panel.pack_start(header, False, False, 0)

        # Scrolled list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # ListStore: index, filename, icon (playing indicator)
        self._playlist_store = Gtk.ListStore(int, str, str)
        self._playlist_view = Gtk.TreeView(model=self._playlist_store)
        self._playlist_view.set_headers_visible(False)
        self._playlist_view.set_activate_on_single_click(False)
        self._playlist_view.connect("row-activated", self._on_playlist_row_activated)

        # Playing indicator column
        renderer_icon = Gtk.CellRendererText()
        col_icon = Gtk.TreeViewColumn("", renderer_icon, text=2)
        col_icon.set_fixed_width(24)
        col_icon.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self._playlist_view.append_column(col_icon)

        # Filename column
        renderer_name = Gtk.CellRendererText()
        renderer_name.set_property("ellipsize", Pango.EllipsizeMode.END)
        col_name = Gtk.TreeViewColumn("", renderer_name, text=1)
        col_name.set_expand(True)
        self._playlist_view.append_column(col_name)

        scroll.add(self._playlist_view)
        panel.pack_start(scroll, True, True, 0)

        return panel

    def _build_status_bar(self, parent):
        """Build the status bar at the bottom."""
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._status_bar.get_style_context().add_class("status-bar")

        self._status_label = Gtk.Label(label=self._t("no_file"))
        self._status_label.set_xalign(0.0)
        self._status_label.set_hexpand(True)
        self._status_bar.pack_start(self._status_label, True, True, 0)

        self._status_count = Gtk.Label(label="")
        self._status_bar.pack_start(self._status_count, False, False, 0)

        parent.pack_start(self._status_bar, False, False, 0)

    # ------------------------------------------------------------------
    # Video area drawing
    # ------------------------------------------------------------------

    def _on_video_draw(self, widget, cr):
        """Draw dark background on fallback video area."""
        alloc = widget.get_allocation()
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.rectangle(0, 0, alloc.width, alloc.height)
        cr.fill()
        return False

    def _on_video_click(self, widget, event):
        """Handle click on video area (double-click = fullscreen)."""
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self._toggle_fullscreen()

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def _play_current(self):
        """Load and play the current playlist item."""
        filepath = self._playlist.current
        if filepath is None:
            return

        if self._engine.load(filepath):
            self._engine.play()
            self._placeholder.set_visible(False)
            self._update_title()
            self._update_now_playing()
            self._highlight_current_in_playlist()

    def _on_play_clicked(self):
        """Handle play button click."""
        if self._engine.is_playing:
            self._engine.pause()
        elif self._playlist.current:
            if self._engine.get_position() >= 0:
                self._engine.play()
            else:
                self._play_current()
        elif not self._playlist.is_empty:
            self._playlist.select(0)
            self._play_current()

    def _on_next(self):
        """Play the next track."""
        track = self._playlist.next()
        if track:
            self._play_current()

    def _on_previous(self):
        """Play the previous track or restart current."""
        # If more than 3 seconds in, restart current track
        pos = self._engine.get_position()
        if GST_AVAILABLE and pos > 3 * Gst.SECOND:
            self._engine.seek(0)
            return
        track = self._playlist.previous()
        if track:
            self._play_current()

    def _seek_relative(self, seconds):
        """Seek relative by given seconds."""
        if GST_AVAILABLE:
            self._engine.seek_relative(int(seconds * Gst.SECOND))

    def _on_speed_up(self):
        """Increase playback speed."""
        self._engine.speed_up()
        self._speed_label.set_text(f"{self._engine.speed:.2g}x")

    def _on_speed_down(self):
        """Decrease playback speed."""
        self._engine.speed_down()
        self._speed_label.set_text(f"{self._engine.speed:.2g}x")

    def _on_reset_speed(self):
        """Reset playback speed to normal."""
        self._engine.reset_speed()
        self._speed_label.set_text("1.0x")

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    def _on_volume_changed(self, scale):
        """Handle volume slider change."""
        vol = scale.get_value() / 100.0
        self._engine.set_volume(vol)
        self._update_volume_icon()

    def _adjust_volume(self, delta):
        """Adjust volume by delta (positive or negative)."""
        new_vol = self._engine.volume + delta
        new_vol = max(0.0, min(1.0, new_vol))
        self._engine.set_volume(new_vol)
        self._volume_scale.set_value(new_vol * 100)
        self._update_volume_icon()

    def _on_toggle_mute(self):
        """Toggle mute."""
        muted = self._engine.toggle_mute()
        self._update_volume_icon()

    def _update_volume_icon(self):
        """Update the mute button icon."""
        if self._engine.muted:
            self._mute_btn.set_label("\U0001f507")
        elif self._engine.volume > 0.5:
            self._mute_btn.set_label("\U0001f50a")
        elif self._engine.volume > 0:
            self._mute_btn.set_label("\U0001f509")
        else:
            self._mute_btn.set_label("\U0001f507")

    # ------------------------------------------------------------------
    # Seek bar
    # ------------------------------------------------------------------

    def _on_seek_changed(self, scale):
        """Handle seek bar value change (user-initiated only)."""
        if self._programmatic_seek_update:
            return
        if GST_AVAILABLE and self._engine.duration > 0:
            value = scale.get_value()
            position = int(value / 1000.0 * self._engine.duration)
            self._time_label.set_text(format_time(position))
            # Debounce: cancel previous pending seek and schedule new one
            if self._seek_debounce_id is not None:
                GLib.source_remove(self._seek_debounce_id)
            self._seek_debounce_id = GLib.timeout_add(
                50, self._do_debounced_seek, position
            )

    def _do_debounced_seek(self, position_ns):
        """Execute a debounced seek operation."""
        self._seek_debounce_id = None
        self._engine.seek(position_ns)
        return False

    # ------------------------------------------------------------------
    # Engine callbacks
    # ------------------------------------------------------------------

    def _on_eos(self):
        """Handle end of stream."""
        next_track = self._playlist.next()
        if next_track:
            GLib.idle_add(self._play_current)
        else:
            GLib.idle_add(self._on_playback_finished)

    def _on_playback_finished(self):
        """Handle all playback finished."""
        self._play_btn.set_label("\u25b6")
        self._play_btn.set_tooltip_text(self._t("play"))
        self._update_title()

    def _on_error(self, message):
        """Handle playback error."""
        print(f"Playback error: {message}")
        self._status_label.set_text(f"{self._t('error')}: {message}")

    def _on_state_changed(self, state):
        """Handle player state change."""
        if state == "playing":
            self._play_btn.set_label("\u275a\u275a")
            self._play_btn.set_tooltip_text(self._t("pause"))
            self._placeholder.set_visible(False)
        elif state == "paused":
            self._play_btn.set_label("\u25b6")
            self._play_btn.set_tooltip_text(self._t("play"))
        elif state == "stopped":
            self._play_btn.set_label("\u25b6")
            self._play_btn.set_tooltip_text(self._t("play"))
            self._seek_scale.set_value(0)
            self._time_label.set_text("00:00")

    def _on_duration(self, duration_ns):
        """Handle duration discovery."""
        self._duration_label.set_text(format_time(duration_ns))

    def _on_position(self, position_ns):
        """Handle position update."""
        self._time_label.set_text(format_time(position_ns))
        if self._engine.duration > 0:
            self._programmatic_seek_update = True
            percent = (position_ns / self._engine.duration) * 1000.0
            self._seek_scale.set_value(percent)
            self._programmatic_seek_update = False

    def _on_tags(self, tags):
        """Handle stream tags."""
        title = tags.get("title", "")
        if title:
            self._now_playing_label.set_text(title)

    # ------------------------------------------------------------------
    # Playlist management
    # ------------------------------------------------------------------

    def _refresh_playlist_view(self):
        """Refresh the playlist TreeView from the Playlist model."""
        self._playlist_store.clear()
        for i, filepath in enumerate(self._playlist.items):
            icon = "\u25b6" if i == self._playlist.current_index else ""
            name = os.path.basename(filepath)
            self._playlist_store.append([i, name, icon])
        self._update_status_count()

    def _highlight_current_in_playlist(self):
        """Update the playing indicator in the playlist."""
        for row in self._playlist_store:
            idx = row[0]
            row[2] = "\u25b6" if idx == self._playlist.current_index else ""

    def _on_playlist_row_activated(self, treeview, path, column):
        """Handle double-click on playlist item."""
        model = treeview.get_model()
        itr = model.get_iter(path)
        if itr:
            idx = model.get_value(itr, 0)
            self._playlist.select(idx)
            self._play_current()

    def _on_shuffle_toggled(self, button):
        """Handle shuffle toggle."""
        self._playlist.toggle_shuffle()

    def _on_repeat_clicked(self, button):
        """Cycle repeat mode."""
        mode = self._playlist.cycle_repeat()
        label_map = {
            RepeatMode.NONE: ("\u21bb", "repeat_off"),
            RepeatMode.ALL: ("\u21bb\u2200", "repeat_all"),
            RepeatMode.ONE: ("\u21bb\u2081", "repeat_one"),
        }
        label, tip_key = label_map.get(mode, ("\U0001f501", "repeat_off"))
        self._repeat_btn.set_label(label)
        self._repeat_btn.set_tooltip_text(self._t(tip_key))

    def _on_clear_playlist(self, widget=None):
        """Clear the playlist."""
        self._engine.stop()
        self._playlist.clear()
        self._refresh_playlist_view()
        self._placeholder.set_visible(True)
        self._update_title()
        self._now_playing_label.set_text(self._t("no_file"))

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------

    def _on_open_file(self, widget=None):
        """Show file open dialog."""
        dialog = Gtk.FileChooserDialog(
            title=self._t("open_file"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        dialog.set_select_multiple(True)

        # Media file filter
        media_filter = Gtk.FileFilter()
        media_filter.set_name("Media Files")
        for ext in sorted(ALL_MEDIA_EXTENSIONS):
            media_filter.add_pattern(f"*{ext}")
            media_filter.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(media_filter)

        # All files filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All Files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
            was_empty = self._playlist.is_empty
            for f in filenames:
                self._playlist.add_file(f)
            self._refresh_playlist_view()
            if was_empty and not self._playlist.is_empty:
                self._play_current()
        dialog.destroy()

    def _on_open_directory(self, widget=None):
        """Show directory open dialog."""
        dialog = Gtk.FileChooserDialog(
            title=self._t("open_directory"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            directory = dialog.get_filename()
            was_empty = self._playlist.is_empty
            self._playlist.add_directory(directory)
            self._refresh_playlist_view()
            if was_empty and not self._playlist.is_empty:
                self._play_current()
        dialog.destroy()

    def _on_open_subtitle(self, widget=None):
        """Open subtitle file dialog."""
        dialog = Gtk.FileChooserDialog(
            title=self._t("open_subtitle"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )

        sub_filter = Gtk.FileFilter()
        sub_filter.set_name("Subtitle Files")
        for ext in ["*.srt", "*.sub", "*.ass", "*.ssa", "*.vtt"]:
            sub_filter.add_pattern(ext)
        dialog.add_filter(sub_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            sub_file = dialog.get_filename()
            self._engine.load_subtitle(sub_file)
        dialog.destroy()

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def _on_drag_data(self, widget, context, x, y, data, info, time):
        """Handle files dropped onto the window."""
        uris = data.get_uris()
        was_empty = self._playlist.is_empty
        for uri in uris:
            filepath = GLib.filename_from_uri(uri)[0]
            if os.path.isdir(filepath):
                self._playlist.add_directory(filepath)
            elif os.path.isfile(filepath) and is_media_file(filepath):
                self._playlist.add_file(filepath)
        self._refresh_playlist_view()
        if was_empty and not self._playlist.is_empty:
            self._play_current()

    # ------------------------------------------------------------------
    # Fullscreen
    # ------------------------------------------------------------------

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self._fullscreen_active:
            self.unfullscreen()
            self._menu_bar.set_visible(True)
            self._status_bar.set_visible(True)
            if self._playlist_visible:
                self._playlist_panel.set_visible(True)
            self._fullscreen_active = False
        else:
            self.fullscreen()
            self._menu_bar.set_visible(False)
            self._status_bar.set_visible(False)
            self._playlist_panel.set_visible(False)
            self._fullscreen_active = True

    # ------------------------------------------------------------------
    # Playlist panel toggle
    # ------------------------------------------------------------------

    def _toggle_playlist(self):
        """Toggle playlist panel visibility and resize window accordingly."""
        self._playlist_visible = not self._playlist_visible
        self._playlist_panel.set_visible(self._playlist_visible)
        self._playlist_btn.set_active(self._playlist_visible)
        self._resize_for_playlist()

    def _on_playlist_toggled(self, button):
        """Handle playlist toggle button."""
        self._playlist_visible = button.get_active()
        self._playlist_panel.set_visible(self._playlist_visible)
        self._resize_for_playlist()

    def _resize_for_playlist(self):
        """Resize window when playlist visibility changes."""
        if self._fullscreen_active:
            return
        playlist_width = 280
        current_width, current_height = self.get_size()
        if self._playlist_visible:
            self.resize(current_width + playlist_width, current_height)
        else:
            new_width = max(400, current_width - playlist_width)
            self.resize(new_width, current_height)

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def _on_language_change(self, widget, language):
        """Handle language change."""
        self._language = language
        self._update_title()
        self._placeholder_text.set_text(self._t("drop_files_here"))
        self._playlist_title_label.set_text(self._t("playlist"))
        if not self._engine.is_playing and self._playlist.is_empty:
            self._now_playing_label.set_text(self._t("no_file"))
            self._status_label.set_text(self._t("no_file"))

    # ------------------------------------------------------------------
    # About dialog
    # ------------------------------------------------------------------

    def _on_about(self, widget):
        """Show about dialog."""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            message_format=self._t("about_text").format(version=__version__),
        )
        dialog.set_title(self._t("about"))
        dialog.run()
        dialog.destroy()

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _on_key_press(self, widget, event):
        """Handle keyboard shortcuts."""
        key = event.keyval
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        # Space - play/pause
        if key == Gdk.KEY_space:
            self._on_play_clicked()
            return True

        # F - fullscreen
        if key == Gdk.KEY_f or key == Gdk.KEY_F11:
            self._toggle_fullscreen()
            return True

        # Escape - exit fullscreen
        if key == Gdk.KEY_Escape:
            if self._fullscreen_active:
                self._toggle_fullscreen()
                return True

        # Right arrow - forward 10s
        if key == Gdk.KEY_Right:
            if ctrl:
                self._seek_relative(60)
            else:
                self._seek_relative(10)
            return True

        # Left arrow - backward 10s
        if key == Gdk.KEY_Left:
            if ctrl:
                self._seek_relative(-60)
            else:
                self._seek_relative(-10)
            return True

        # Up arrow - volume up
        if key == Gdk.KEY_Up:
            self._adjust_volume(0.05)
            return True

        # Down arrow - volume down
        if key == Gdk.KEY_Down:
            self._adjust_volume(-0.05)
            return True

        # M - mute
        if key == Gdk.KEY_m or key == Gdk.KEY_M:
            self._on_toggle_mute()
            return True

        # N - next track
        if key == Gdk.KEY_n or key == Gdk.KEY_N:
            self._on_next()
            return True

        # P - previous track
        if key == Gdk.KEY_p or key == Gdk.KEY_P:
            self._on_previous()
            return True

        # S - stop
        if key == Gdk.KEY_s or key == Gdk.KEY_S:
            if not ctrl:
                self._engine.stop()
                return True

        # L - playlist toggle
        if key == Gdk.KEY_l or key == Gdk.KEY_L:
            self._toggle_playlist()
            return True

        # ] - speed up
        if key == Gdk.KEY_bracketright:
            self._on_speed_up()
            return True

        # [ - speed down
        if key == Gdk.KEY_bracketleft:
            self._on_speed_down()
            return True

        # = - reset speed
        if key == Gdk.KEY_equal or key == Gdk.KEY_BackSpace:
            self._on_reset_speed()
            return True

        # Ctrl+O - open file
        if ctrl and key == Gdk.KEY_o:
            self._on_open_file()
            return True

        # Ctrl+Q - quit
        if ctrl and key == Gdk.KEY_q:
            self._on_destroy(widget)
            return True

        return False

    # ------------------------------------------------------------------
    # UI updates
    # ------------------------------------------------------------------

    def _update_title(self):
        """Update the window title."""
        name = self._playlist.get_display_name()
        if name:
            self.set_title(f"{name} - {self._t('title')}")
        else:
            self.set_title(self._t("title"))

    def _update_now_playing(self):
        """Update the now playing label."""
        name = self._playlist.get_display_name()
        if name:
            self._now_playing_label.set_text(name)
            self._status_label.set_text(name)
        else:
            self._now_playing_label.set_text(self._t("no_file"))

    def _update_status_count(self):
        """Update the playlist count in status bar."""
        count = self._playlist.count
        if count > 0:
            idx = self._playlist.current_index + 1
            self._status_count.set_text(f"{idx} {self._t('of')} {count}")
        else:
            self._status_count.set_text("")

    # ------------------------------------------------------------------
    # Playlist persistence (SQLite)
    # ------------------------------------------------------------------

    def _restore_session(self):
        """Restore last session playlist from database."""
        try:
            session = self._db.load_session_playlist()
            if session and session["filepaths"]:
                for fp in session["filepaths"]:
                    if os.path.isfile(fp):
                        self._playlist.items.append(fp)
                if self._playlist.items:
                    self._playlist.current_index = max(
                        0, min(session["current_index"], len(self._playlist.items) - 1)
                    )
                    rm = session.get("repeat_mode", "none")
                    if rm in (RepeatMode.NONE, RepeatMode.ALL, RepeatMode.ONE):
                        self._playlist.repeat_mode = rm
                    if session.get("shuffle", False):
                        self._playlist.toggle_shuffle()
                    self._refresh_playlist_view()
        except Exception:
            pass

    def _save_session(self):
        """Save the current session playlist to database."""
        try:
            self._db.save_session_playlist(
                filepaths=list(self._playlist.items),
                current_index=self._playlist.current_index,
                repeat_mode=self._playlist.repeat_mode,
                shuffle=self._playlist.shuffle,
            )
        except Exception:
            pass

    def _on_save_playlist_dialog(self):
        """Show a dialog to save the current playlist with a name."""
        if self._playlist.is_empty:
            return

        dialog = Gtk.Dialog(
            title=self._t("save_playlist"),
            parent=self,
            modal=True,
        )
        dialog.add_button(self._t("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t("save"), Gtk.ResponseType.OK)
        dialog.set_default_size(350, -1)

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        label = Gtk.Label(label=self._t("playlist_name"))
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)

        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.pack_start(entry, False, False, 0)

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and name:
            self._db.save_playlist(name, list(self._playlist.items))
            self._status_label.set_text(self._t("playlist_saved"))

    def _on_load_playlist_dialog(self):
        """Show a dialog to load a saved playlist."""
        saved = self._db.list_playlists()
        if not saved:
            dlg = Gtk.MessageDialog(
                parent=self,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=self._t("no_saved_playlists"),
            )
            dlg.run()
            dlg.destroy()
            return

        dialog = Gtk.Dialog(
            title=self._t("load_playlist"),
            parent=self,
            modal=True,
        )
        dialog.add_button(self._t("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t("load"), Gtk.ResponseType.OK)
        dialog.set_default_size(400, 300)

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        # List of playlists
        store = Gtk.ListStore(int, str)  # id, name
        for pid, pname in saved:
            if pname != "__session__":
                store.append([pid, pname])

        tree = Gtk.TreeView(model=store)
        tree.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("", renderer, text=1)
        tree.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(tree)
        box.pack_start(scroll, True, True, 0)

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()

        selected_name = None
        if response == Gtk.ResponseType.OK:
            sel = tree.get_selection()
            model, treeiter = sel.get_selected()
            if treeiter:
                selected_name = model[treeiter][1]

        dialog.destroy()

        if selected_name:
            filepaths = self._db.load_playlist(selected_name)
            if filepaths:
                self._engine.stop()
                self._playlist.clear()
                for fp in filepaths:
                    if os.path.isfile(fp):
                        self._playlist.items.append(fp)
                if self._playlist.items:
                    self._playlist.current_index = 0
                self._refresh_playlist_view()
                self._update_title()
                self._status_label.set_text(self._t("playlist_loaded"))

    def _on_manage_playlists_dialog(self):
        """Show a dialog to rename or delete saved playlists."""
        dialog = Gtk.Dialog(
            title=self._t("manage_playlists"),
            parent=self,
            modal=True,
        )
        dialog.add_button(self._t("close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(450, 350)

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        store = Gtk.ListStore(int, str)

        def refresh_store():
            store.clear()
            for pid, pname in self._db.list_playlists():
                if pname != "__session__":
                    store.append([pid, pname])

        refresh_store()

        tree = Gtk.TreeView(model=store)
        tree.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("", renderer, text=1)
        tree.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(tree)
        box.pack_start(scroll, True, True, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(btn_box, False, False, 0)

        rename_btn = Gtk.Button(label=self._t("rename_playlist"))
        delete_btn = Gtk.Button(label=self._t("delete_playlist"))

        def on_rename(widget):
            sel = tree.get_selection()
            model, treeiter = sel.get_selected()
            if not treeiter:
                return
            old_name = model[treeiter][1]
            rename_dlg = Gtk.Dialog(
                title=self._t("rename_playlist"),
                parent=dialog,
                modal=True,
            )
            rename_dlg.add_button(self._t("cancel"), Gtk.ResponseType.CANCEL)
            rename_dlg.add_button(self._t("ok"), Gtk.ResponseType.OK)
            rbox = rename_dlg.get_content_area()
            rbox.set_spacing(8)
            rbox.set_margin_start(12)
            rbox.set_margin_end(12)
            rbox.set_margin_top(12)
            rbox.set_margin_bottom(12)
            lbl = Gtk.Label(label=self._t("new_name"))
            lbl.set_halign(Gtk.Align.START)
            rbox.pack_start(lbl, False, False, 0)
            entry = Gtk.Entry()
            entry.set_text(old_name)
            entry.set_activates_default(True)
            rbox.pack_start(entry, False, False, 0)
            rename_dlg.set_default_response(Gtk.ResponseType.OK)
            rename_dlg.show_all()
            resp = rename_dlg.run()
            new_name = entry.get_text().strip()
            rename_dlg.destroy()
            if resp == Gtk.ResponseType.OK and new_name and new_name != old_name:
                self._db.rename_playlist(old_name, new_name)
                refresh_store()

        def on_delete(widget):
            sel = tree.get_selection()
            model, treeiter = sel.get_selected()
            if not treeiter:
                return
            name = model[treeiter][1]
            confirm = Gtk.MessageDialog(
                parent=dialog,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=self._t("confirm_delete"),
            )
            resp = confirm.run()
            confirm.destroy()
            if resp == Gtk.ResponseType.YES:
                self._db.delete_playlist(name)
                refresh_store()

        rename_btn.connect("clicked", on_rename)
        delete_btn.connect("clicked", on_delete)
        btn_box.pack_start(rename_btn, False, False, 0)
        btn_box.pack_start(delete_btn, False, False, 0)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _on_destroy(self, widget):
        """Clean up and quit."""
        self._save_session()
        self._db.close()
        self._engine.cleanup()
        Gtk.main_quit()
