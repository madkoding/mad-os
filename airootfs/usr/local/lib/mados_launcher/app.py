"""Main application class for the madOS Launcher dock."""

import json
import math
import os

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

# gtk-layer-shell is optional — fallback to regular window if unavailable
try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    GtkLayerShell = None
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from . import __app_id__, __app_name__
from .config import (
    NORD,
    ICON_SIZE,
    TAB_WIDTH,
    DOCK_WIDTH,
    TAB_HEIGHT,
    ICON_PADDING,
    ICON_SPACING,
    ANIMATION_DURATION,
    GRIP_DOT_RADIUS,
    GRIP_DOT_SPACING,
    GRIP_DOT_COLS,
    GRIP_DOT_COL_GAP,
    DRAG_THRESHOLD,
    MIN_MARGIN_TOP,
    DEFAULT_MARGIN_TOP,
    CONFIG_DIR,
    STATE_FILE,
    REFRESH_INTERVAL_SECONDS,
    SHADOW_SIZE,
    SHADOW_OFFSET_X,
    SHADOW_OFFSET_Y,
    SHADOW_LAYERS,
    SHADOW_BASE_ALPHA,
)
from .desktop_entries import scan_desktop_entries, launch_application, group_entries, EntryGroup
from .window_tracker import WindowTracker
from .theme import apply_theme

# --- Indicator constants ---
INDICATOR_HEIGHT = 6       # Height of the running indicator area
INDICATOR_DOT_RADIUS = 3   # Dot radius for running indicator
WINDOW_POLL_MS = 2000      # Poll compositor every 2 seconds


def _hex_to_rgb(hex_color):
    """Convert hex color string to (r, g, b) floats 0-1."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


class LauncherApp:
    """madOS Launcher dock — a retractable icon dock anchored to the left edge."""

    def __init__(self):
        # State
        self._expanded = False
        self._is_dragging = False
        self._button_pressed = False
        self._drag_start_y = 0
        self._drag_start_margin = 0
        self._margin_top = DEFAULT_MARGIN_TOP
        self._drag_update_pending = False
        self._pending_margin = 0
        self._screen_height = 768  # Will be updated
        self._auto_collapse_id = None  # Timer ID for auto-collapse after launch
        self._entries = []
        self._grouped = []         # list of DesktopEntry | EntryGroup
        self._icon_buttons = []    # list of (btn, indicator_draw, entry)

        # Window tracker
        self._tracker = WindowTracker()

        # Load persisted state
        self._load_state()

        # Apply theme
        apply_theme()

        # Build window
        self._build_window()
        self._build_ui()

        # Populate icons
        self._refresh_entries()

        # Show
        self.window.show_all()

        # The revealer should start hidden
        self._revealer.set_reveal_child(False)

        # Periodic rescan of .desktop entries
        GLib.timeout_add_seconds(REFRESH_INTERVAL_SECONDS, self._refresh_entries)

        # Periodic window state polling
        GLib.timeout_add(WINDOW_POLL_MS, self._poll_window_state)

    # ------------------------------------------------------------------ #
    # Window setup with gtk-layer-shell
    # ------------------------------------------------------------------ #

    def _build_window(self):
        """Create the GTK window and configure it as a layer-shell surface."""
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title(__app_name__)
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_name("mados-launcher-window")

        # Enable RGBA visual for transparency
        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
        self.window.set_app_paintable(True)
        self.window.connect("draw", self._on_window_draw)

        # gtk-layer-shell configuration (or fallback to regular window)
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self.window)
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_namespace(self.window, __app_id__)

            # Anchor to left and top edges only
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, False)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, False)

            # Don't push other windows — overlay mode
            GtkLayerShell.set_exclusive_zone(self.window, 0)

            # Vertical position
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, self._margin_top)
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.LEFT, 0)

            # No keyboard interactivity
            GtkLayerShell.set_keyboard_mode(
                self.window, GtkLayerShell.KeyboardMode.NONE
            )
        else:
            # Fallback: regular floating window pinned to left edge
            self.window.set_type_hint(Gdk.WindowTypeHint.DOCK)
            self.window.set_keep_above(True)
            self.window.set_skip_taskbar_hint(True)
            self.window.set_skip_pager_hint(True)
            self.window.stick()
            self.window.move(0, self._margin_top)

        # Get screen dimensions for drag clamping
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_primary_monitor() or display.get_monitor(0)
            if monitor:
                geom = monitor.get_geometry()
                self._screen_height = geom.height

        self.window.connect("destroy", self._on_destroy)

    # ------------------------------------------------------------------ #
    # UI Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        """Build the dock UI: [revealer with icons] [grip tab]."""
        # Outer container — horizontal box
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._main_box.set_name("dock-container")
        # Shadow padding — extra space for drop shadow rendering
        self._main_box.set_margin_top(SHADOW_SIZE)
        self._main_box.set_margin_end(SHADOW_SIZE + SHADOW_OFFSET_X)
        self._main_box.set_margin_bottom(SHADOW_SIZE + SHADOW_OFFSET_Y)
        self.window.add(self._main_box)

        # --- Icon area inside a revealer (slides right) ---
        self._revealer = Gtk.Revealer()
        self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self._revealer.set_transition_duration(ANIMATION_DURATION)
        self._revealer.set_reveal_child(False)

        # Container for icons (no scroll — size adapts to content)
        self._icons_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=ICON_SPACING,
        )
        self._icons_box.set_name("icons-box")

        # --- Left grip (visible when expanded, for dragging from the left) ---
        self._left_grip_event_box = Gtk.EventBox()
        self._left_grip_event_box.set_above_child(True)
        self._left_grip_event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        self._left_grip_draw = Gtk.DrawingArea()
        self._left_grip_draw.set_name("left-grip")
        self._left_grip_draw.set_size_request(TAB_WIDTH, -1)
        self._left_grip_draw.connect("draw", self._on_draw_left_grip)

        self._left_grip_event_box.add(self._left_grip_draw)

        # Reuse same drag handlers for left grip
        self._left_grip_event_box.connect("button-press-event", self._on_tab_press)
        self._left_grip_event_box.connect("button-release-event", self._on_left_grip_release)
        self._left_grip_event_box.connect("motion-notify-event", self._on_tab_motion)
        self._left_grip_event_box.connect("enter-notify-event", self._on_tab_enter)
        self._left_grip_event_box.connect("leave-notify-event", self._on_tab_leave)

        # Place left grip inside the revealer, before the icons
        self._revealer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._revealer_box.pack_start(self._left_grip_event_box, False, False, 0)
        self._revealer_box.pack_start(self._icons_box, True, True, 0)
        self._revealer.add(self._revealer_box)

        self._main_box.pack_start(self._revealer, False, False, 0)

        # --- Grip tab (always visible) ---
        self._tab_event_box = Gtk.EventBox()
        self._tab_event_box.set_above_child(True)
        self._tab_event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        self._tab_draw = Gtk.DrawingArea()
        self._tab_draw.set_name("grip-tab")
        self._tab_draw.set_size_request(TAB_WIDTH, TAB_HEIGHT)
        self._tab_draw.connect("draw", self._on_draw_grip)

        self._tab_event_box.add(self._tab_draw)
        self._main_box.pack_start(self._tab_event_box, False, False, 0)

        # Tab event handlers
        self._tab_event_box.connect("button-press-event", self._on_tab_press)
        self._tab_event_box.connect("button-release-event", self._on_tab_release)
        self._tab_event_box.connect("motion-notify-event", self._on_tab_motion)

        # Cursor change on hover
        self._tab_event_box.connect("enter-notify-event", self._on_tab_enter)
        self._tab_event_box.connect("leave-notify-event", self._on_tab_leave)

    # ------------------------------------------------------------------ #
    # Drop shadow rendering
    # ------------------------------------------------------------------ #

    def _on_window_draw(self, widget, cr):
        """Clear background to transparent and draw drop shadow behind the dock."""
        # Clear entire window to transparent
        cr.set_operator(1)  # cairo.OPERATOR_SOURCE
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(2)  # cairo.OPERATOR_OVER

        alloc = self._main_box.get_allocation()
        if alloc.width <= 1 or alloc.height <= 1:
            return False

        x, y, w, h = alloc.x, alloc.y, alloc.width, alloc.height
        radius = 8  # Matches CSS border-radius

        # Draw shadow: multiple semi-transparent layers with decreasing spread
        for i in range(SHADOW_LAYERS):
            spread = SHADOW_SIZE * (SHADOW_LAYERS - i) / SHADOW_LAYERS
            alpha = SHADOW_BASE_ALPHA / SHADOW_LAYERS

            frac = (i + 1) / SHADOW_LAYERS
            ox = SHADOW_OFFSET_X * frac
            oy = SHADOW_OFFSET_Y * frac

            sx = x - spread + ox
            sy = y - spread + oy
            sw = w + spread * 2
            sh = h + spread * 2
            sr = radius + spread

            # Dock-shaped path: flat left edge, rounded right corners
            cr.new_path()
            cr.move_to(sx, sy)
            cr.line_to(sx + sw - sr, sy)
            cr.arc(sx + sw - sr, sy + sr, sr, -math.pi / 2, 0)
            cr.line_to(sx + sw, sy + sh - sr)
            cr.arc(sx + sw - sr, sy + sh - sr, sr, 0, math.pi / 2)
            cr.line_to(sx, sy + sh)
            cr.close_path()

            cr.set_source_rgba(0, 0, 0, alpha)
            cr.fill()

        return False  # Continue to draw child widgets

    # ------------------------------------------------------------------ #
    # Cairo drawing for the grip tab
    # ------------------------------------------------------------------ #

    def _on_draw_grip(self, widget, cr):
        """Draw the grip handle: rounded rect background + dot pattern."""
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        # Background — rounded on the right side
        radius = 8
        cr.new_path()
        cr.move_to(0, 0)
        cr.line_to(w - radius, 0)
        cr.arc(w - radius, radius, radius, -math.pi / 2, 0)
        cr.line_to(w, h - radius)
        cr.arc(w - radius, h - radius, radius, 0, math.pi / 2)
        cr.line_to(0, h)
        cr.close_path()

        # Fill with nord1, or nord2 if hovered
        bg = _hex_to_rgb(NORD["nord1"])
        cr.set_source_rgb(*bg)
        cr.fill()

        # Draw grip dots (centered vertically)
        dot_color = _hex_to_rgb(NORD["nord3"])
        cr.set_source_rgb(*dot_color)

        total_dot_rows = 5
        total_height = (total_dot_rows - 1) * GRIP_DOT_SPACING
        start_y = (h - total_height) / 2
        center_x = w / 2

        for row in range(total_dot_rows):
            y = start_y + row * GRIP_DOT_SPACING
            for col in range(GRIP_DOT_COLS):
                offset = (col - (GRIP_DOT_COLS - 1) / 2) * GRIP_DOT_COL_GAP
                x = center_x + offset
                cr.arc(x, y, GRIP_DOT_RADIUS, 0, 2 * math.pi)
                cr.fill()

        # Draw a subtle direction indicator (chevron)
        chevron_color = _hex_to_rgb(NORD["nord9"])
        cr.set_source_rgba(*chevron_color, 0.6)
        cr.set_line_width(1.5)
        cr.set_line_cap(1)  # ROUND

        chevron_y = h - 14
        cx = w / 2

        if self._expanded:
            # Chevron pointing left «
            cr.move_to(cx + 3, chevron_y - 4)
            cr.line_to(cx - 2, chevron_y)
            cr.line_to(cx + 3, chevron_y + 4)
        else:
            # Chevron pointing right »
            cr.move_to(cx - 3, chevron_y - 4)
            cr.line_to(cx + 2, chevron_y)
            cr.line_to(cx - 3, chevron_y + 4)

        cr.stroke()
        return False

    # ------------------------------------------------------------------ #
    # Tab interaction: click to toggle, drag to move
    # ------------------------------------------------------------------ #

    def _on_tab_press(self, widget, event):
        """Record starting position for potential drag."""
        if event.button == 1:
            self._button_pressed = True
            self._drag_start_y = event.y_root
            self._drag_start_margin = self._margin_top
            self._is_dragging = False
            # Change cursor to grabbing
            win = widget.get_window()
            if win:
                cursor = Gdk.Cursor.new_from_name(widget.get_display(), "grabbing")
                win.set_cursor(cursor)
        return True

    def _on_tab_release(self, widget, event):
        """On release: toggle if click, save if drag."""
        if event.button != 1:
            return True

        self._button_pressed = False

        if self._is_dragging:
            # Finish drag — save new position
            self._is_dragging = False
            self._save_state()
        else:
            # Click — toggle expand/collapse
            self._expanded = not self._expanded
            self._revealer.set_reveal_child(self._expanded)
            self._tab_draw.queue_draw()  # Redraw chevron direction
            self._save_state()

        # Restore grab cursor
        win = widget.get_window()
        if win:
            cursor = Gdk.Cursor.new_from_name(widget.get_display(), "grab")
            win.set_cursor(cursor)
        return True

    def _on_tab_motion(self, widget, event):
        """Handle vertical drag while button is held."""
        if not self._button_pressed:
            return True

        delta = event.y_root - self._drag_start_y

        if not self._is_dragging and abs(delta) < DRAG_THRESHOLD:
            return True

        self._is_dragging = True

        # Calculate new margin, clamped to screen bounds
        dock_height = self.window.get_allocated_height()
        max_margin = max(0, self._screen_height - dock_height - 20)
        new_margin = int(self._drag_start_margin + delta)
        new_margin = max(MIN_MARGIN_TOP, min(new_margin, max_margin))

        # Throttle position updates to reduce flicker
        self._pending_margin = new_margin
        if not self._drag_update_pending:
            self._drag_update_pending = True
            GLib.idle_add(self._flush_drag_position)

        return True

    def _flush_drag_position(self):
        """Apply pending drag position — runs at most once per idle cycle."""
        self._drag_update_pending = False
        self._margin_top = self._pending_margin
        if HAS_LAYER_SHELL:
            GtkLayerShell.set_margin(
                self.window, GtkLayerShell.Edge.TOP, self._margin_top
            )
        else:
            self.window.move(0, self._margin_top)
        return False  # GLib.SOURCE_REMOVE

    def _on_tab_enter(self, widget, event):
        """Change cursor to grab hand on hover."""
        win = widget.get_window()
        if win:
            cursor = Gdk.Cursor.new_from_name(widget.get_display(), "grab")
            win.set_cursor(cursor)
        return False

    def _on_tab_leave(self, widget, event):
        """Restore default cursor."""
        win = widget.get_window()
        if win:
            win.set_cursor(None)
        return False

    # ------------------------------------------------------------------ #
    # Left grip drawing and interaction
    # ------------------------------------------------------------------ #

    def _on_draw_left_grip(self, widget, cr):
        """Draw a grip pattern on the left side of the expanded dock (mirrors right tab)."""
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        # Background — rounded on the left side
        radius = 8
        cr.new_path()
        cr.move_to(w, 0)
        cr.line_to(radius, 0)
        cr.arc(radius, radius, radius, -math.pi, -math.pi / 2)
        cr.line_to(0, h - radius)
        cr.arc(radius, h - radius, radius, math.pi / 2, math.pi)
        cr.line_to(w, h)
        cr.close_path()

        bg = _hex_to_rgb(NORD["nord1"])
        cr.set_source_rgb(*bg)
        cr.fill()

        # Draw grip dots (same pattern as right tab)
        dot_color = _hex_to_rgb(NORD["nord3"])
        cr.set_source_rgb(*dot_color)

        total_dot_rows = 5
        total_height = (total_dot_rows - 1) * GRIP_DOT_SPACING
        start_y = (h - total_height) / 2
        center_x = w / 2

        for row in range(total_dot_rows):
            y = start_y + row * GRIP_DOT_SPACING
            for col in range(GRIP_DOT_COLS):
                offset = (col - (GRIP_DOT_COLS - 1) / 2) * GRIP_DOT_COL_GAP
                x = center_x + offset
                cr.arc(x, y, GRIP_DOT_RADIUS, 0, 2 * math.pi)
                cr.fill()

        return False

    def _on_left_grip_release(self, widget, event):
        """On release of left grip: only save drag (no toggle)."""
        if event.button != 1:
            return True

        self._button_pressed = False

        if self._is_dragging:
            self._is_dragging = False
            self._save_state()
        # No toggle on click — left grip is only for dragging

        # Restore grab cursor
        win = widget.get_window()
        if win:
            cursor = Gdk.Cursor.new_from_name(widget.get_display(), "grab")
            win.set_cursor(cursor)
        return True

    # ------------------------------------------------------------------ #
    # Icon population and refresh
    # ------------------------------------------------------------------ #

    def _refresh_entries(self):
        """Rescan .desktop files, group by category, and rebuild icons if changed."""
        try:
            new_entries = scan_desktop_entries()
        except Exception as e:
            print(f"[mados-launcher] Error scanning desktop entries: {e}")
            return True  # Keep the timeout alive

        # Check if entries actually changed
        new_names = [e.filename for e in new_entries]
        old_names = [e.filename for e in self._entries]

        if new_names != old_names:
            self._entries = new_entries
            self._grouped = group_entries(new_entries)
            self._rebuild_icons()

        return True  # Keep the timeout running

    def _rebuild_icons(self):
        """Clear and rebuild all icon buttons in the dock."""
        # Remove old children
        for child in self._icons_box.get_children():
            self._icons_box.remove(child)
        self._icon_buttons.clear()

        for item in self._grouped:
            if isinstance(item, EntryGroup):
                self._build_group_icon(item)
            else:
                self._build_single_icon(item)

        self._icons_box.show_all()

    def _build_single_icon(self, entry):
        """Build an icon button for a single (ungrouped) entry."""
        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        btn = Gtk.Button()
        btn.get_style_context().add_class("launcher-icon")
        btn.set_tooltip_text(entry.name)
        btn.set_relief(Gtk.ReliefStyle.NONE)

        image = self._make_icon_image(entry)
        btn.add(image)
        btn.connect("clicked", self._on_icon_clicked, entry.exec_cmd)

        # Indicator drawing area (small dot below icon)
        indicator = Gtk.DrawingArea()
        indicator.set_size_request(ICON_SIZE, INDICATOR_HEIGHT)
        indicator.connect("draw", self._on_draw_indicator, entry)

        item_box.pack_start(btn, False, False, 0)
        item_box.pack_start(indicator, False, False, 0)

        self._icons_box.pack_start(item_box, False, False, 0)
        self._icon_buttons.append((btn, indicator, entry))

    def _build_group_icon(self, group):
        """Build an icon button for a group of entries — click shows a popup submenu."""
        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        btn = Gtk.Button()
        btn.get_style_context().add_class("launcher-icon")
        btn.get_style_context().add_class("launcher-group")
        btn.set_tooltip_text(f"{group.group_name} ({len(group.entries)})")
        btn.set_relief(Gtk.ReliefStyle.NONE)

        image = self._make_icon_image(group.representative)
        btn.add(image)
        btn.connect("clicked", self._on_group_clicked, group)

        # Indicator: show dot if any entry in the group is running
        indicator = Gtk.DrawingArea()
        indicator.set_size_request(ICON_SIZE, INDICATOR_HEIGHT)
        indicator.connect("draw", self._on_draw_group_indicator, group)

        item_box.pack_start(btn, False, False, 0)
        item_box.pack_start(indicator, False, False, 0)

        self._icons_box.pack_start(item_box, False, False, 0)
        # Track each entry in the group for indicator updates
        for entry in group.entries:
            self._icon_buttons.append((btn, indicator, entry))

    def _make_icon_image(self, entry):
        """Create a Gtk.Image widget from a DesktopEntry's icon."""
        if entry.pixbuf:
            pixbuf = entry.pixbuf
            if pixbuf.get_width() != ICON_SIZE or pixbuf.get_height() != ICON_SIZE:
                pixbuf = pixbuf.scale_simple(
                    ICON_SIZE, ICON_SIZE, GdkPixbuf.InterpType.BILINEAR
                )
            return Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            image = Gtk.Image.new_from_icon_name(
                "application-x-executable", Gtk.IconSize.LARGE_TOOLBAR
            )
            image.set_pixel_size(ICON_SIZE)
            return image

    def _on_group_clicked(self, button, group):
        """Show a popover listing all entries in the group."""
        popover = Gtk.Popover()
        popover.set_relative_to(button)
        popover.set_position(Gtk.PositionType.RIGHT)
        popover.get_style_context().add_class("launcher-popup")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(4)

        for entry in group.entries:
            row = Gtk.Button()
            row.set_relief(Gtk.ReliefStyle.NONE)
            row.get_style_context().add_class("popup-row")

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            hbox.set_margin_start(4)
            hbox.set_margin_end(4)
            hbox.set_margin_top(2)
            hbox.set_margin_bottom(2)

            # Icon
            if entry.pixbuf:
                pixbuf = entry.pixbuf
                small = ICON_SIZE - 2
                if pixbuf.get_width() != small or pixbuf.get_height() != small:
                    pixbuf = pixbuf.scale_simple(
                        small, small, GdkPixbuf.InterpType.BILINEAR
                    )
                icon = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                icon = Gtk.Image.new_from_icon_name(
                    "application-x-executable", Gtk.IconSize.MENU
                )
                icon.set_pixel_size(ICON_SIZE - 2)

            hbox.pack_start(icon, False, False, 0)

            # Label
            label = Gtk.Label(label=entry.name)
            label.set_xalign(0)
            hbox.pack_start(label, True, True, 0)

            # Running indicator dot
            if self._tracker.is_running(entry.exec_cmd, entry.filename):
                dot = Gtk.Label(label="\u25cf")
                dot.get_style_context().add_class("running-dot")
                hbox.pack_end(dot, False, False, 0)

            row.add(hbox)
            row.connect("clicked", self._on_popover_item_clicked, popover, entry.exec_cmd)
            vbox.pack_start(row, False, False, 0)

        popover.add(vbox)
        popover.show_all()

    def _on_popover_item_clicked(self, button, popover, exec_cmd):
        """Launch app from popover and close it."""
        popover.popdown()
        launch_application(exec_cmd)
        self._schedule_auto_collapse()

    def _on_icon_clicked(self, button, exec_cmd):
        """Launch the clicked application."""
        launch_application(exec_cmd)
        self._schedule_auto_collapse()

    def _schedule_auto_collapse(self):
        """Auto-collapse the dock 3 seconds after launching an application."""
        if not self._expanded:
            return
        # Cancel any previous pending auto-collapse
        if hasattr(self, '_auto_collapse_id') and self._auto_collapse_id:
            GLib.source_remove(self._auto_collapse_id)
        self._auto_collapse_id = GLib.timeout_add_seconds(3, self._auto_collapse)

    def _auto_collapse(self):
        """Collapse the dock (called from timer)."""
        self._auto_collapse_id = None
        if self._expanded:
            self._expanded = False
            self._revealer.set_reveal_child(False)
            self._tab_draw.queue_draw()
            self._save_state()
        return False  # GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ #
    # Window state tracking and indicators
    # ------------------------------------------------------------------ #

    def _poll_window_state(self):
        """Poll compositor for window state and update indicators."""
        changed = self._tracker.update()
        if changed:
            self._update_indicators()
        return True  # Keep polling

    def _update_indicators(self):
        """Update CSS classes and redraw indicators based on window state."""
        for btn, indicator, entry in self._icon_buttons:
            ctx = btn.get_style_context()
            running = self._tracker.is_running(entry.exec_cmd, entry.filename)
            urgent = self._tracker.is_urgent(entry.exec_cmd, entry.filename)
            focused = self._tracker.is_focused(entry.exec_cmd, entry.filename)

            # Toggle CSS classes
            if running:
                ctx.add_class("running")
            else:
                ctx.remove_class("running")

            if urgent:
                ctx.add_class("urgent")
            else:
                ctx.remove_class("urgent")

            if focused:
                ctx.add_class("focused")
            else:
                ctx.remove_class("focused")

            # Redraw the indicator dot
            indicator.queue_draw()

    def _on_draw_indicator(self, widget, cr, entry):
        """Draw a small dot indicator below the icon if the app is running."""
        running = self._tracker.is_running(entry.exec_cmd, entry.filename)
        urgent = self._tracker.is_urgent(entry.exec_cmd, entry.filename)
        focused = self._tracker.is_focused(entry.exec_cmd, entry.filename)

        if not running:
            return False

        alloc = widget.get_allocation()
        cx = alloc.width / 2
        cy = INDICATOR_HEIGHT / 2

        if urgent:
            # Urgent: pulsing orange dot
            color = _hex_to_rgb(NORD["nord12"])  # orange
            radius = INDICATOR_DOT_RADIUS + 0.5
        elif focused:
            # Focused: bright frost dot
            color = _hex_to_rgb(NORD["nord8"])   # bright blue
            radius = INDICATOR_DOT_RADIUS + 0.5
        else:
            # Running: subtle frost dot
            color = _hex_to_rgb(NORD["nord9"])   # muted blue
            radius = INDICATOR_DOT_RADIUS

        cr.set_source_rgb(*color)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()

        return False

    def _on_draw_group_indicator(self, widget, cr, group):
        """Draw indicator for a group — shows dot if any entry in the group is running."""
        any_running = False
        any_urgent = False
        any_focused = False

        for entry in group.entries:
            if self._tracker.is_running(entry.exec_cmd, entry.filename):
                any_running = True
            if self._tracker.is_urgent(entry.exec_cmd, entry.filename):
                any_urgent = True
            if self._tracker.is_focused(entry.exec_cmd, entry.filename):
                any_focused = True

        if not any_running:
            return False

        alloc = widget.get_allocation()
        cx = alloc.width / 2
        cy = INDICATOR_HEIGHT / 2

        if any_urgent:
            color = _hex_to_rgb(NORD["nord12"])
            radius = INDICATOR_DOT_RADIUS + 0.5
        elif any_focused:
            color = _hex_to_rgb(NORD["nord8"])
            radius = INDICATOR_DOT_RADIUS + 0.5
        else:
            color = _hex_to_rgb(NORD["nord9"])
            radius = INDICATOR_DOT_RADIUS

        cr.set_source_rgb(*color)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()

        return False

    # ------------------------------------------------------------------ #
    # State persistence
    # ------------------------------------------------------------------ #

    def _load_state(self):
        """Load dock position and expanded state from config file."""
        if not os.path.isfile(STATE_FILE):
            return
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            self._margin_top = int(state.get("margin_top", DEFAULT_MARGIN_TOP))
            self._expanded = bool(state.get("expanded", False))
        except Exception:
            pass

    def _save_state(self):
        """Persist dock position and expanded state to config file."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            state = {
                "margin_top": self._margin_top,
                "expanded": self._expanded,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[mados-launcher] Failed to save state: {e}")

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def _on_destroy(self, widget):
        """Save state and quit."""
        self._save_state()
        Gtk.main_quit()
