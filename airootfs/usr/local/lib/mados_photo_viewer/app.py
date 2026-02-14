"""
madOS Photo Viewer - Main Application Window
==============================================

The primary application window that integrates all components:
    - Menu bar with File operations (Open, Save, Save As, Set Wallpaper)
    - Main toolbar with navigation and zoom controls
    - Editing toolbar with tool selection, color picker, brush/font size
    - Central canvas for image display and editing
    - Video player that replaces the canvas for video files
    - Status bar with file info, position, and zoom level
    - Keyboard shortcuts for all major actions
    - Language selection for i18n

The window sets app_id to "mados-photo-viewer" for Sway integration.
"""

import os
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from . import __app_id__, __app_name__, __version__
from .canvas import ImageCanvas
from .tools import (
    TOOL_NONE, TOOL_PAINT, TOOL_TEXT, TOOL_BLUR, TOOL_PIXELATE, TOOL_ERASER,
    compose_edits_onto_pixbuf,
)
from .navigator import FileNavigator, is_image_file, is_video_file, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, ALL_EXTENSIONS
from .video_player import VideoPlayer, GST_AVAILABLE
from .translations import get_text, detect_system_language, DEFAULT_LANGUAGE
from .theme import apply_theme, NORD


class PhotoViewerApp(Gtk.Window):
    """Main application window for the madOS Photo Viewer."""

    def __init__(self, initial_file=None):
        """Initialize the application window and all UI components.

        Args:
            initial_file: Optional path to a file to open on startup.
        """
        super().__init__(title=__app_name__)

        # Apply the Nord theme
        apply_theme()

        # State
        self._language = detect_system_language()
        self._navigator = FileNavigator()
        self._current_mode = 'image'  # 'image' or 'video'

        # Window properties
        self.set_default_size(900, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        # Set app_id for Sway/Wayland
        self.set_wmclass(__app_id__, __app_name__)
        self.connect('delete-event', self._on_delete_event)
        self.connect('key-press-event', self._on_key_press)

        # Main vertical layout
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self._main_box)

        # Build UI sections
        self._build_menu_bar()
        self._build_main_toolbar()
        self._build_edit_toolbar()
        self._build_content_area()
        self._build_status_bar()

        # Show everything
        self.show_all()

        # Hide edit toolbar by default (shown when a tool is active)
        self._edit_toolbar.set_visible(True)

        # Open initial file if provided
        if initial_file and os.path.isfile(initial_file):
            self._open_file(os.path.abspath(initial_file))

        self._update_ui_state()

    # ==================================================================
    # UI CONSTRUCTION
    # ==================================================================

    def _build_menu_bar(self):
        """Build the menu bar with File and View menus."""
        menubar = Gtk.MenuBar()
        menubar.get_style_context().add_class('tool-bar')

        # --- File menu ---
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label=self._t('open'))
        file_item.set_submenu(file_menu)

        open_item = Gtk.MenuItem(label=self._t('open') + "  (Ctrl+O)")
        open_item.connect('activate', lambda w: self._on_open())
        file_menu.append(open_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        save_item = Gtk.MenuItem(label=self._t('save') + "  (Ctrl+S)")
        save_item.connect('activate', lambda w: self._on_save())
        file_menu.append(save_item)

        save_as_item = Gtk.MenuItem(label=self._t('save_as') + "  (Ctrl+Shift+S)")
        save_as_item.connect('activate', lambda w: self._on_save_as())
        file_menu.append(save_as_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        wallpaper_item = Gtk.MenuItem(label=self._t('set_wallpaper'))
        wallpaper_item.connect('activate', lambda w: self._on_set_wallpaper())
        file_menu.append(wallpaper_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit  (Ctrl+Q)")
        quit_item.connect('activate', lambda w: self._on_quit())
        file_menu.append(quit_item)

        menubar.append(file_item)

        self._main_box.pack_start(menubar, False, False, 0)
        self._menu_bar = menubar

    def _build_main_toolbar(self):
        """Build the main toolbar with navigation and zoom controls."""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.get_style_context().add_class('tool-bar')
        toolbar.set_margin_top(2)
        toolbar.set_margin_bottom(2)

        # Open button
        btn_open = Gtk.Button(label=self._t('open'))
        btn_open.set_tooltip_text("Ctrl+O")
        btn_open.connect('clicked', lambda w: self._on_open())
        toolbar.pack_start(btn_open, False, False, 2)

        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Navigation
        self._btn_prev = Gtk.Button(label="\u25C0")
        self._btn_prev.get_style_context().add_class('nav-button')
        self._btn_prev.set_tooltip_text(self._t('prev_image') + " (Left)")
        self._btn_prev.connect('clicked', lambda w: self._on_prev())
        toolbar.pack_start(self._btn_prev, False, False, 2)

        self._btn_next = Gtk.Button(label="\u25B6")
        self._btn_next.get_style_context().add_class('nav-button')
        self._btn_next.set_tooltip_text(self._t('next_image') + " (Right)")
        self._btn_next.connect('clicked', lambda w: self._on_next())
        toolbar.pack_start(self._btn_next, False, False, 2)

        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Zoom controls
        btn_zoom_out = Gtk.Button(label="\u2212")
        btn_zoom_out.get_style_context().add_class('zoom-button')
        btn_zoom_out.set_tooltip_text(self._t('zoom_out') + " (-)")
        btn_zoom_out.connect('clicked', lambda w: self._canvas.zoom_out())
        toolbar.pack_start(btn_zoom_out, False, False, 1)

        self._zoom_label = Gtk.Label(label="100%")
        self._zoom_label.set_width_chars(6)
        toolbar.pack_start(self._zoom_label, False, False, 2)

        btn_zoom_in = Gtk.Button(label="+")
        btn_zoom_in.get_style_context().add_class('zoom-button')
        btn_zoom_in.set_tooltip_text(self._t('zoom_in') + " (+)")
        btn_zoom_in.connect('clicked', lambda w: self._canvas.zoom_in())
        toolbar.pack_start(btn_zoom_in, False, False, 1)

        btn_fit = Gtk.Button(label=self._t('fit_window'))
        btn_fit.set_tooltip_text("Ctrl+0")
        btn_fit.connect('clicked', lambda w: self._canvas.zoom_fit())
        toolbar.pack_start(btn_fit, False, False, 2)

        btn_actual = Gtk.Button(label="1:1")
        btn_actual.set_tooltip_text(self._t('actual_size') + " (Ctrl+1)")
        btn_actual.connect('clicked', lambda w: self._canvas.zoom_actual())
        toolbar.pack_start(btn_actual, False, False, 2)

        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        # Wallpaper button
        btn_wallpaper = Gtk.Button(label=self._t('set_wallpaper'))
        btn_wallpaper.connect('clicked', lambda w: self._on_set_wallpaper())
        toolbar.pack_start(btn_wallpaper, False, False, 2)

        # Save button on the right
        btn_save = Gtk.Button(label=self._t('save'))
        btn_save.set_tooltip_text("Ctrl+S")
        btn_save.connect('clicked', lambda w: self._on_save())
        toolbar.pack_end(btn_save, False, False, 2)

        self._main_box.pack_start(toolbar, False, False, 0)
        self._main_toolbar = toolbar

    def _build_edit_toolbar(self):
        """Build the editing toolbar with tool buttons and options."""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.get_style_context().add_class('tool-bar')
        toolbar.set_margin_top(1)
        toolbar.set_margin_bottom(1)

        # Tool toggle buttons (radio group behavior)
        self._tool_buttons = {}

        tools = [
            (TOOL_PAINT, 'paint'),
            (TOOL_TEXT, 'text_tool'),
            (TOOL_BLUR, 'blur_tool'),
            (TOOL_PIXELATE, 'pixelate_tool'),
            (TOOL_ERASER, 'eraser'),
        ]

        for tool_id, label_key in tools:
            btn = Gtk.ToggleButton(label=self._t(label_key))
            btn.get_style_context().add_class('tool-button')
            btn.connect('toggled', self._on_tool_toggled, tool_id)
            toolbar.pack_start(btn, False, False, 2)
            self._tool_buttons[tool_id] = btn

        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)

        # Color picker
        color_label = Gtk.Label(label=self._t('color') + ":")
        toolbar.pack_start(color_label, False, False, 2)

        self._color_button = Gtk.ColorButton()
        initial_color = Gdk.RGBA()
        initial_color.parse('#ECEFF4')
        self._color_button.set_rgba(initial_color)
        self._color_button.set_use_alpha(True)
        self._color_button.connect('color-set', self._on_color_set)
        toolbar.pack_start(self._color_button, False, False, 2)

        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)

        # Brush size
        brush_label = Gtk.Label(label=self._t('brush_size') + ":")
        toolbar.pack_start(brush_label, False, False, 2)

        self._brush_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 1, 100, 1
        )
        self._brush_scale.set_value(5)
        self._brush_scale.set_size_request(80, -1)
        self._brush_scale.set_hexpand(True)
        self._brush_scale.set_draw_value(True)
        self._brush_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._brush_scale.connect('value-changed', self._on_brush_size_changed)
        toolbar.pack_start(self._brush_scale, False, False, 2)

        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)

        # Font size (for text tool)
        font_label = Gtk.Label(label=self._t('font_size') + ":")
        toolbar.pack_start(font_label, False, False, 2)

        self._font_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 8, 120, 1
        )
        self._font_scale.set_value(24)
        self._font_scale.set_size_request(80, -1)
        self._font_scale.set_hexpand(True)
        self._font_scale.set_draw_value(True)
        self._font_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._font_scale.connect('value-changed', self._on_font_size_changed)
        toolbar.pack_start(self._font_scale, False, False, 2)

        # Text entry
        self._text_entry = Gtk.Entry()
        self._text_entry.set_placeholder_text(self._t('text_placeholder'))
        self._text_entry.set_width_chars(20)
        self._text_entry.connect('changed', self._on_text_changed)
        toolbar.pack_start(self._text_entry, False, False, 2)

        # Right side: Undo/Redo/Clear
        toolbar.pack_start(Gtk.Box(), True, True, 0)  # Spacer

        btn_undo = Gtk.Button(label=self._t('undo'))
        btn_undo.set_tooltip_text("Ctrl+Z")
        btn_undo.connect('clicked', lambda w: self._canvas.undo())
        toolbar.pack_end(btn_undo, False, False, 2)

        btn_redo = Gtk.Button(label=self._t('redo'))
        btn_redo.set_tooltip_text("Ctrl+Y")
        btn_redo.connect('clicked', lambda w: self._canvas.redo())
        toolbar.pack_end(btn_redo, False, False, 2)

        btn_clear = Gtk.Button(label=self._t('clear_edits'))
        btn_clear.get_style_context().add_class('destructive-action')
        btn_clear.connect('clicked', lambda w: self._canvas.clear_edits())
        toolbar.pack_end(btn_clear, False, False, 2)

        self._main_box.pack_start(toolbar, False, False, 0)
        self._edit_toolbar = toolbar

    def _build_content_area(self):
        """Build the central content area with canvas and video player."""
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.set_transition_duration(200)

        # Image canvas
        self._canvas = ImageCanvas()
        self._canvas.on_edits_changed = self._on_edits_changed
        # Wrap in a frame for a subtle border
        canvas_frame = Gtk.Frame()
        canvas_frame.set_shadow_type(Gtk.ShadowType.NONE)
        canvas_frame.add(self._canvas)
        self._content_stack.add_named(canvas_frame, 'image')

        # Video player
        self._video_player = VideoPlayer()
        self._content_stack.add_named(self._video_player, 'video')

        self._content_stack.set_visible_child_name('image')
        self._main_box.pack_start(self._content_stack, True, True, 0)

    def _build_status_bar(self):
        """Build the status bar at the bottom of the window."""
        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status.get_style_context().add_class('status-bar')

        self._status_filename = Gtk.Label(label="")
        self._status_filename.set_xalign(0)
        self._status_filename.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        status.pack_start(self._status_filename, True, True, 4)

        self._status_index = Gtk.Label(label="")
        self._status_index.set_xalign(1)
        status.pack_start(self._status_index, False, False, 4)

        self._status_zoom = Gtk.Label(label="")
        self._status_zoom.set_xalign(1)
        self._status_zoom.set_width_chars(8)
        status.pack_start(self._status_zoom, False, False, 4)

        self._status_dimensions = Gtk.Label(label="")
        self._status_dimensions.set_xalign(1)
        status.pack_start(self._status_dimensions, False, False, 4)

        self._main_box.pack_start(status, False, False, 0)
        self._status_bar = status

    # ==================================================================
    # FILE OPERATIONS
    # ==================================================================

    def _on_open(self):
        """Show file chooser dialog and open the selected file."""
        dialog = Gtk.FileChooserDialog(
            title=self._t('open_file'),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )

        # Add filters
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All Media (Images & Videos)")
        for ext in ALL_EXTENSIONS:
            all_filter.add_pattern(f"*{ext}")
            all_filter.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(all_filter)

        img_filter = Gtk.FileFilter()
        img_filter.set_name("Images")
        for ext in IMAGE_EXTENSIONS:
            img_filter.add_pattern(f"*{ext}")
            img_filter.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(img_filter)

        vid_filter = Gtk.FileFilter()
        vid_filter.set_name("Videos")
        for ext in VIDEO_EXTENSIONS:
            vid_filter.add_pattern(f"*{ext}")
            vid_filter.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(vid_filter)

        any_filter = Gtk.FileFilter()
        any_filter.set_name("All Files")
        any_filter.add_pattern("*")
        dialog.add_filter(any_filter)

        # Start in the current file's directory if available
        current = self._navigator.current_file
        if current:
            dialog.set_current_folder(os.path.dirname(current))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if filepath:
                self._open_file(filepath)
        dialog.destroy()

    def _open_file(self, filepath):
        """Open a media file by path.

        Determines whether it is an image or video and switches the
        appropriate viewer.

        Args:
            filepath: Full path to the file.
        """
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath):
            self._show_error(f"File not found: {filepath}")
            return

        # Load directory listing
        self._navigator.load_directory(filepath)

        if is_video_file(filepath):
            self._show_video(filepath)
        elif is_image_file(filepath):
            self._show_image(filepath)
        else:
            # Try loading as image anyway (GdkPixbuf might support it)
            self._show_image(filepath)

        self._update_ui_state()

    def _show_image(self, filepath):
        """Switch to image mode and load the given image.

        Args:
            filepath: Path to the image file.
        """
        # Stop any video playback
        self._video_player.stop()
        self._current_mode = 'image'
        self._content_stack.set_visible_child_name('image')
        self._edit_toolbar.set_visible(True)

        success = self._canvas.load_image(filepath)
        if not success:
            self._show_error(f"Could not load image: {os.path.basename(filepath)}")

    def _show_video(self, filepath):
        """Switch to video mode and load the given video.

        Args:
            filepath: Path to the video file.
        """
        if not GST_AVAILABLE:
            self._show_error("GStreamer is not available. Cannot play video files.")
            return

        self._current_mode = 'video'
        self._content_stack.set_visible_child_name('video')
        # Hide editing toolbar for video mode
        self._edit_toolbar.set_visible(False)

        self._video_player.load_video(filepath)
        self._video_player.play()

    def _on_save(self):
        """Save the edited image to the original file path."""
        if self._current_mode != 'image':
            return
        if not self._canvas.has_image():
            return
        if not self._canvas.history.has_edits:
            return  # Nothing to save

        filepath = self._canvas.get_filepath()
        if filepath:
            self._save_to_file(filepath)

    def _on_save_as(self):
        """Show Save As dialog and save the edited image."""
        if self._current_mode != 'image':
            return
        if not self._canvas.has_image():
            return

        dialog = Gtk.FileChooserDialog(
            title=self._t('save_as'),
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_do_overwrite_confirmation(True)

        # Suggest current filename
        current = self._canvas.get_filepath()
        if current:
            dialog.set_current_folder(os.path.dirname(current))
            dialog.set_current_name(os.path.basename(current))

        # File type filters
        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG Image (*.png)")
        png_filter.add_pattern("*.png")
        dialog.add_filter(png_filter)

        jpg_filter = Gtk.FileFilter()
        jpg_filter.set_name("JPEG Image (*.jpg)")
        jpg_filter.add_pattern("*.jpg")
        jpg_filter.add_pattern("*.jpeg")
        dialog.add_filter(jpg_filter)

        bmp_filter = Gtk.FileFilter()
        bmp_filter.set_name("BMP Image (*.bmp)")
        bmp_filter.add_pattern("*.bmp")
        dialog.add_filter(bmp_filter)

        tiff_filter = Gtk.FileFilter()
        tiff_filter.set_name("TIFF Image (*.tiff)")
        tiff_filter.add_pattern("*.tiff")
        tiff_filter.add_pattern("*.tif")
        dialog.add_filter(tiff_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if filepath:
                self._save_to_file(filepath)
        dialog.destroy()

    def _save_to_file(self, filepath):
        """Compose edits and save the result to a file.

        Determines the output format from the file extension.

        Args:
            filepath: Destination file path.
        """
        pixbuf = self._canvas.get_pixbuf()
        if pixbuf is None:
            return

        # Compose all edits onto the pixbuf
        result = compose_edits_onto_pixbuf(pixbuf, self._canvas.history)

        # Determine format from extension
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        format_map = {
            '.png': 'png',
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.bmp': 'bmp',
            '.tiff': 'tiff',
            '.tif': 'tiff',
        }

        fmt = format_map.get(ext, 'png')

        try:
            if fmt == 'jpeg':
                result.savev(filepath, fmt, ['quality'], ['95'])
            else:
                result.savev(filepath, fmt, [], [])
            self._status_filename.set_text(
                f"{self._t('success')}: {self._t('save')} -> {os.path.basename(filepath)}"
            )
        except GLib.Error as e:
            self._show_error(f"Save failed: {e.message}")

    def _on_set_wallpaper(self):
        """Set the current image as the Sway desktop wallpaper."""
        if self._current_mode != 'image':
            return

        filepath = self._canvas.get_filepath()
        if not filepath:
            return

        # If there are edits, save to a temp file first
        if self._canvas.history.has_edits:
            pixbuf = self._canvas.get_pixbuf()
            result = compose_edits_onto_pixbuf(pixbuf, self._canvas.history)
            tmp_path = os.path.expanduser('~/.cache/mados-wallpaper.png')
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
            try:
                result.savev(tmp_path, 'png', [], [])
                filepath = tmp_path
            except GLib.Error:
                pass  # Fall through to use original file

        filepath = os.path.abspath(filepath)

        try:
            result = subprocess.run(
                ['swaymsg', 'output', '*', 'bg', filepath, 'fill'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self._status_filename.set_text(self._t('wallpaper_set'))
                # Try to update sway config
                self._update_sway_config(filepath)
            else:
                self._show_error(self._t('wallpaper_error') + f" ({result.stderr.strip()})")
        except FileNotFoundError:
            self._show_error(self._t('wallpaper_error') + " (swaymsg not found)")
        except subprocess.TimeoutExpired:
            self._show_error(self._t('wallpaper_error') + " (timeout)")

    def _update_sway_config(self, filepath):
        """Attempt to update the Sway config with the new wallpaper path.

        Looks for an existing 'output * bg' line and replaces it, or
        appends one at the end.

        Args:
            filepath: Absolute path to the wallpaper image.
        """
        config_path = os.path.expanduser('~/.config/sway/config')
        if not os.path.isfile(config_path):
            return

        try:
            with open(config_path, 'r') as f:
                lines = f.readlines()

            new_line = f"output * bg {filepath} fill\n"
            found = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('output') and ' bg ' in stripped:
                    lines[i] = new_line
                    found = True
                    break

            if not found:
                lines.append('\n' + new_line)

            with open(config_path, 'w') as f:
                f.writelines(lines)
        except (IOError, OSError):
            pass  # Silently fail if we can't update the config

    # ==================================================================
    # NAVIGATION
    # ==================================================================

    def _on_prev(self):
        """Navigate to the previous file in the directory."""
        if self._check_unsaved_on_navigate():
            return
        filepath = self._navigator.go_prev()
        if filepath:
            if is_video_file(filepath):
                self._show_video(filepath)
            else:
                self._show_image(filepath)
            self._update_ui_state()

    def _on_next(self):
        """Navigate to the next file in the directory."""
        if self._check_unsaved_on_navigate():
            return
        filepath = self._navigator.go_next()
        if filepath:
            if is_video_file(filepath):
                self._show_video(filepath)
            else:
                self._show_image(filepath)
            self._update_ui_state()

    def _check_unsaved_on_navigate(self):
        """If there are unsaved edits, prompt the user.

        Returns:
            True if the navigation should be cancelled, False to proceed.
        """
        if self._current_mode != 'image':
            return False
        if not self._canvas.history.has_edits:
            return False

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=self._t('unsaved_changes'),
        )
        dialog.format_secondary_text(self._t('save_before_closing'))
        dialog.add_buttons(
            self._t('save'), Gtk.ResponseType.YES,
            "Discard", Gtk.ResponseType.NO,
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self._on_save()
            return False
        elif response == Gtk.ResponseType.NO:
            self._canvas.clear_edits()
            return False
        else:
            return True  # Cancel navigation

    # ==================================================================
    # EDITING TOOLS
    # ==================================================================

    def _on_tool_toggled(self, button, tool_id):
        """Handle tool button toggle, enforcing radio-group behavior.

        Args:
            button: The ToggleButton that was toggled.
            tool_id: The tool constant (TOOL_PAINT, etc.)
        """
        if button.get_active():
            # Deactivate all other tool buttons
            for tid, btn in self._tool_buttons.items():
                if tid != tool_id:
                    btn.handler_block_by_func(self._on_tool_toggled)
                    btn.set_active(False)
                    btn.handler_unblock_by_func(self._on_tool_toggled)
            self._canvas.set_tool(tool_id)
        else:
            # If this button was deactivated, check if any other is active
            any_active = any(btn.get_active() for btn in self._tool_buttons.values())
            if not any_active:
                self._canvas.set_tool(TOOL_NONE)

    def _on_color_set(self, color_button):
        """Handle color picker change."""
        rgba = color_button.get_rgba()
        self._canvas.set_tool_color(rgba.red, rgba.green, rgba.blue, rgba.alpha)

    def _on_brush_size_changed(self, scale):
        """Handle brush size slider change."""
        self._canvas.set_brush_size(scale.get_value())

    def _on_font_size_changed(self, scale):
        """Handle font size slider change."""
        self._canvas.set_font_size(scale.get_value())

    def _on_text_changed(self, entry):
        """Handle text entry change."""
        self._canvas.set_text_content(entry.get_text())

    def _on_edits_changed(self):
        """Callback from canvas when edit history changes."""
        self._update_title()

    # ==================================================================
    # LANGUAGE
    # ==================================================================

    def _t(self, key):
        """Shortcut for getting a translated string.

        Args:
            key: Translation key.

        Returns:
            Translated string in the current language.
        """
        return get_text(key, self._language)

    def _rebuild_ui_labels(self):
        """Update all visible labels to the current language.

        This is called after a language change. Rather than rebuilding the
        entire UI, we update the text of existing widgets.
        """
        self.set_title(self._t('title'))
        self._update_title()

        # Update tool button labels
        tool_labels = {
            TOOL_PAINT: 'paint',
            TOOL_TEXT: 'text_tool',
            TOOL_BLUR: 'blur_tool',
            TOOL_PIXELATE: 'pixelate_tool',
            TOOL_ERASER: 'eraser',
        }
        for tool_id, label_key in tool_labels.items():
            if tool_id in self._tool_buttons:
                self._tool_buttons[tool_id].set_label(self._t(label_key))

        # Update tooltips
        self._btn_prev.set_tooltip_text(self._t('prev_image') + " (Left)")
        self._btn_next.set_tooltip_text(self._t('next_image') + " (Right)")

        # Update text entry placeholder
        self._text_entry.set_placeholder_text(self._t('text_placeholder'))

        # Update status bar
        self._update_ui_state()

    # ==================================================================
    # KEYBOARD SHORTCUTS
    # ==================================================================

    def _on_key_press(self, widget, event):
        """Handle global keyboard shortcuts.

        Args:
            widget: The window.
            event: The GdkEventKey.

        Returns:
            True if the key was handled.
        """
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK
        key = event.keyval

        # Ctrl shortcuts
        if ctrl and not shift:
            if key == Gdk.KEY_o:
                self._on_open()
                return True
            elif key == Gdk.KEY_s:
                self._on_save()
                return True
            elif key == Gdk.KEY_z:
                self._canvas.undo()
                return True
            elif key == Gdk.KEY_y:
                self._canvas.redo()
                return True
            elif key == Gdk.KEY_q:
                self._on_quit()
                return True
            elif key == Gdk.KEY_0:
                self._canvas.zoom_fit()
                return True
            elif key == Gdk.KEY_1:
                self._canvas.zoom_actual()
                return True

        if ctrl and shift:
            if key == Gdk.KEY_S or key == Gdk.KEY_s:
                self._on_save_as()
                return True

        # Non-modifier shortcuts
        if not ctrl and not shift:
            if key == Gdk.KEY_Left:
                self._on_prev()
                return True
            elif key == Gdk.KEY_Right:
                self._on_next()
                return True
            elif key in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
                self._canvas.zoom_in()
                self._update_zoom_label()
                return True
            elif key in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
                self._canvas.zoom_out()
                self._update_zoom_label()
                return True
            elif key == Gdk.KEY_space:
                if self._current_mode == 'video':
                    if self._video_player.is_playing:
                        self._video_player.pause()
                    else:
                        self._video_player.play()
                    return True

        return False

    # ==================================================================
    # WINDOW LIFECYCLE
    # ==================================================================

    def _on_delete_event(self, widget, event):
        """Handle window close: check for unsaved edits.

        Args:
            widget: The window.
            event: The GdkEvent.

        Returns:
            True to prevent closing, False to allow it.
        """
        if self._current_mode == 'image' and self._canvas.history.has_edits:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=self._t('unsaved_changes'),
            )
            dialog.format_secondary_text(self._t('save_before_closing'))
            dialog.add_buttons(
                self._t('save'), Gtk.ResponseType.YES,
                "Discard", Gtk.ResponseType.NO,
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            )
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                self._on_save()
                self._cleanup_and_quit()
                return False
            elif response == Gtk.ResponseType.NO:
                self._cleanup_and_quit()
                return False
            else:
                return True  # Cancel close
        else:
            self._cleanup_and_quit()
            return False

    def _on_quit(self):
        """Trigger window close via the delete-event path."""
        event = Gdk.Event.new(Gdk.EventType.DELETE)
        self.emit('delete-event', event)

    def _cleanup_and_quit(self):
        """Clean up resources and quit the GTK main loop."""
        self._video_player.cleanup()
        Gtk.main_quit()

    # ==================================================================
    # UI STATE UPDATES
    # ==================================================================

    def _update_ui_state(self):
        """Refresh all status indicators and button sensitivity."""
        self._update_title()
        self._update_status_bar()
        self._update_zoom_label()
        self._update_nav_buttons()

    def _update_title(self):
        """Update the window title with the current filename and edit state."""
        title = self._t('title')
        filename = self._navigator.current_filename
        if filename:
            modified = '*' if (self._current_mode == 'image' and self._canvas.history.has_edits) else ''
            title = f"{modified}{filename} - {title}"
        self.set_title(title)

    def _update_status_bar(self):
        """Update the status bar labels."""
        filename = self._navigator.current_filename
        self._status_filename.set_text(filename if filename else self._t('no_images'))

        if self._navigator.has_files:
            idx = self._navigator.current_index
            total = self._navigator.total_count
            self._status_index.set_text(f"{idx} {self._t('of')} {total}")
        else:
            self._status_index.set_text("")

        if self._current_mode == 'image' and self._canvas.has_image():
            pixbuf = self._canvas.get_pixbuf()
            if pixbuf:
                w = pixbuf.get_width()
                h = pixbuf.get_height()
                self._status_dimensions.set_text(f"{w} x {h}")
            else:
                self._status_dimensions.set_text("")
        else:
            self._status_dimensions.set_text("")

        self._update_zoom_label()

    def _update_zoom_label(self):
        """Update the zoom percentage display."""
        if self._current_mode == 'image':
            pct = self._canvas.get_zoom_percent()
            self._zoom_label.set_text(f"{pct}%")
            self._status_zoom.set_text(f"{pct}%")
        else:
            self._zoom_label.set_text("")
            self._status_zoom.set_text("")

    def _update_nav_buttons(self):
        """Enable/disable navigation buttons based on file count."""
        has_nav = self._navigator.total_count > 1
        self._btn_prev.set_sensitive(has_nav)
        self._btn_next.set_sensitive(has_nav)

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _show_error(self, message):
        """Show an error dialog.

        Args:
            message: The error message to display.
        """
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=self._t('error'),
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
