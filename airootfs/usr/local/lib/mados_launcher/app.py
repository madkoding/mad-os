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
    ICON_ZOOM_SIZE,
    ICON_ZOOM_STEP,
    ICON_ZOOM_INTERVAL_MS,
)
from .desktop_entries import scan_desktop_entries, launch_application, group_entries, EntryGroup
from .window_tracker import WindowTracker
from .theme import apply_theme

# --- Indicator constants ---
INDICATOR_HEIGHT = 6  # Height of the running indicator area
INDICATOR_DOT_RADIUS = 3  # Dot radius for running indicator
WINDOW_POLL_MS = 2000  # Poll compositor every 2 seconds

# --- Bounce animation constants ---
BOUNCE_AMPLITUDE = 3  # Pixels to jump up/down
BOUNCE_DURATION_MS = 50  # Milliseconds per bounce frame
BOUNCE_TOTAL_SECONDS = 3  # Total duration of bounce animation


def _hex_to_rgb(hex_color):
    """Convert hex color string to (r, g, b) floats 0-1."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


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
        self._grouped = []  # list of DesktopEntry | EntryGroup
        self._icon_buttons = []  # list of (btn, indicator_draw, entry)

        # Icon zoom animation state: id(btn) -> {current_size, target_size, timer (GLib source ID or None), entry, btn}
        self._zoom_state = {}

        # Bounce animation state: id(btn) -> {offset, direction, timer, original_y}
        self._bounce_state = {}

        # Active popover reference (for dismissing on outside click)
        self._active_popover = None

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

        # Force collapsed state at startup (ignore saved state)
        self._expanded = False
        self._revealer.set_reveal_child(False)

        # Show
        self.window.show_all()

        # Initialize grip positions
        self._update_grip_position()

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
        # Capa 1: padre transparente de 150px
        self.window.set_size_request(-1, 150)

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
            GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
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
        self.window.connect("button-press-event", self._on_window_button_press)

    # ------------------------------------------------------------------ #
    # UI Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        """Build the dock UI: [revealer with icons] [grip tab]."""
        # Create revealer for expand/collapse animation
        self._revealer = Gtk.Revealer()
        self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self._revealer.set_transition_duration(ANIMATION_DURATION)
        self._revealer.connect("notify::child-revealed", self._on_revealer_animation_done)

        # Use Fixed container para posicionar elementos exactamente
        self._fixed = Gtk.Fixed()
        self._fixed.set_size_request(-1, 150)
        self.window.add(self._fixed)

        # Posicion X inicial del revealer (después de los grips) - mitad de espacio
        self._revealer_x = TAB_WIDTH  # 14px en lugar de 28px

        # Capa 2 visual: fondo gris de 50px centrado verticalmente (margen de 50px arriba y abajo)
        self._visual_bg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._visual_bg.set_name("dock-bg")
        self._visual_bg.set_size_request(-1, 50)
        self._fixed.put(self._visual_bg, 0, 50)

        # Fondo gris detras de los iconos (mismo tamaño que el grip, centrado verticalmente)
        self._icons_bg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._icons_bg.set_name("icons-bg")
        self._icons_bg.set_size_request(-1, 50)
        self._fixed.put(self._icons_bg, self._revealer_x, 50)

        # Capa 3: caja de iconos (150px de alto)
        self._icons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._icons_box.set_size_request(-1, 150)
        self._revealer.add(self._icons_box)

        # Add revealer - posicionado a la izquierda (después de los grips)
        self._fixed.put(self._revealer, self._revealer_x, 0)

        # --- Grip tab - a la derecha del revealer, centrado verticalmente ---
        # Centrado: y = (150 - TAB_HEIGHT) / 2 = (150 - 60) / 2 = 45
        self._tab_y = (150 - TAB_HEIGHT) // 2
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
        # Initially position grip at x=0 (collapsed state)
        self._fixed.put(self._tab_event_box, 0, self._tab_y)

        # --- Left grip (visible when expanded, on the left side) ---
        self._left_grip_event_box = Gtk.EventBox()
        self._left_grip_event_box.set_above_child(True)
        self._left_grip_event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
        )

        self._left_grip_draw = Gtk.DrawingArea()
        self._left_grip_draw.set_name("left-grip")
        self._left_grip_draw.set_size_request(TAB_WIDTH, TAB_HEIGHT)
        self._left_grip_draw.connect("draw", self._on_draw_left_grip)

        self._left_grip_event_box.add(self._left_grip_draw)
        # Initially hidden (will show when expanded)
        self._left_grip_event_box.hide()
        self._fixed.put(self._left_grip_event_box, 0, self._tab_y)

        # Left grip event handlers
        self._left_grip_event_box.connect("button-press-event", self._on_left_grip_press)
        self._left_grip_event_box.connect("button-release-event", self._on_left_grip_release)

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
        """Clear background to 100% transparent."""
        cr.set_operator(1)  # cairo.OPERATOR_SOURCE
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(2)  # cairo.OPERATOR_OVER
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
            self._update_grip_position()
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
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, self._margin_top)
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

    def _on_revealer_animation_done(self, widget, gparam):
        """Move grip to final position after revealer animation completes."""
        self._update_grip_position()

    def _update_grip_position(self):
        """Update grip tab x position based on revealer width."""
        if self._expanded:
            child = self._revealer.get_child()
            if child:
                child.show_all()
                width = child.get_allocated_width()
                # Actualizar ancho del fondo de iconos
                self._icons_bg.set_size_request(width, 50)
                # En expanded, poner grip derecho a la derecha del contenido
                self._fixed.move(self._tab_event_box, self._revealer_x + width, self._tab_y)
                # Grip izquierdo a la izquierda de los iconos
                self._left_grip_event_box.show()
                self._fixed.move(self._left_grip_event_box, 0, self._tab_y)
        else:
            # En collapsed, solo el grip derecho visible en x=0
            self._left_grip_event_box.hide()
            self._fixed.move(self._tab_event_box, 0, self._tab_y)
            # Fondo de iconos oculto
            self._icons_bg.set_size_request(0, 50)

    # ------------------------------------------------------------------ #
    # Left grip drawing and interaction
    # ------------------------------------------------------------------ #

    def _on_draw_left_grip(self, widget, cr):
        """Draw a rectangular grip pattern on the left side."""
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        # Background — rectangular (no rounded corners)
        cr.new_path()
        cr.rectangle(0, 0, w, h)
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

    def _on_left_grip_press(self, widget, event):
        """Record starting position for potential drag."""
        if event.button == 1:
            self._button_pressed = True
            self._is_dragging = False
        return True

    def _on_left_grip_release(self, widget, event):
        """On release of left grip: toggle if click, save if drag."""
        if event.button != 1:
            return True

        self._button_pressed = False

        if self._is_dragging:
            self._is_dragging = False
            self._save_state()
        else:
            # Click — toggle (collapse) the dock
            self._expanded = not self._expanded
            self._revealer.set_reveal_child(self._expanded)
            self._update_grip_position()
            self._tab_draw.queue_draw()  # Redraw chevron direction
            self._save_state()

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
        # Capa 3: contenedor de icono de 150px de alto
        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        item_box.set_size_request(48, 150)

        # Alignment para centrar el icono de 48px
        align = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0, yscale=0)
        align.set_size_request(48, 48)

        btn = Gtk.Button()
        btn.get_style_context().add_class("launcher-icon")
        btn.set_tooltip_text(entry.name)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_size_request(48, 48)

        image = self._make_icon_image(entry)
        image.set_size_request(ICON_SIZE, ICON_SIZE)
        btn.add(image)
        btn.connect("clicked", self._on_icon_clicked, entry.exec_cmd)

        # Zoom on hover
        btn.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        btn.connect("enter-notify-event", self._on_icon_enter, entry)
        btn.connect("leave-notify-event", self._on_icon_leave, entry)

        align.add(btn)

        # Indicator
        indicator = Gtk.DrawingArea()
        indicator.set_size_request(48, 4)
        indicator.connect("draw", self._on_draw_indicator, entry)

        item_box.pack_start(align, True, True, 0)
        item_box.pack_end(indicator, False, False, 0)

        self._icons_box.pack_start(item_box, False, False, 0)
        self._icon_buttons.append((btn, indicator, entry, align))

    def _build_group_icon(self, group):
        """Build an icon button for a group of entries — click shows a popup submenu."""
        # Capa 3: contenedor de icono de 150px de alto
        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        item_box.set_size_request(48, 150)

        # Alignment para centrar el icono
        align = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0, yscale=0)
        align.set_size_request(48, 48)

        btn = Gtk.Button()
        btn.get_style_context().add_class("launcher-icon")
        btn.get_style_context().add_class("launcher-group")
        btn.set_tooltip_text(f"{group.group_name} ({len(group.entries)})")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_size_request(48, 48)

        image = self._make_icon_image(group.representative)
        image.set_size_request(ICON_SIZE, ICON_SIZE)
        btn.add(image)
        btn.connect("clicked", self._on_group_clicked, group)

        # Zoom on hover
        btn.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        btn.connect("enter-notify-event", self._on_icon_enter, group.representative)
        btn.connect("leave-notify-event", self._on_icon_leave, group.representative)

        align.add(btn)

        # Indicator
        indicator = Gtk.DrawingArea()
        indicator.set_size_request(48, 4)
        indicator.connect("draw", self._on_draw_group_indicator, group)

        item_box.pack_start(align, True, True, 0)
        item_box.pack_end(indicator, False, False, 0)

        self._icons_box.pack_start(item_box, False, False, 0)
        # Track each entry in the group for indicator updates
        for entry in group.entries:
            self._icon_buttons.append((btn, indicator, entry, align))

    def _make_icon_image(self, entry):
        """Create a Gtk.Image widget from a DesktopEntry's icon."""
        if entry.pixbuf:
            pixbuf = entry.pixbuf
            if pixbuf.get_width() != ICON_SIZE or pixbuf.get_height() != ICON_SIZE:
                pixbuf = pixbuf.scale_simple(ICON_SIZE, ICON_SIZE, GdkPixbuf.InterpType.BILINEAR)
            return Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            image = Gtk.Image.new_from_icon_name(
                "application-x-executable", Gtk.IconSize.LARGE_TOOLBAR
            )
            image.set_pixel_size(ICON_SIZE)
            return image

    def _on_group_clicked(self, button, group):
        """Show a popover listing all entries in the group."""
        # Dismiss any previously open popover
        self._dismiss_active_popover()

        popover = Gtk.Popover()
        popover.set_relative_to(button)
        popover.set_position(Gtk.PositionType.RIGHT)
        popover.get_style_context().add_class("launcher-popup")
        popover.connect("closed", self._on_popover_closed)

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
                    pixbuf = pixbuf.scale_simple(small, small, GdkPixbuf.InterpType.BILINEAR)
                icon = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
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
        self._active_popover = popover

    def _on_popover_item_clicked(self, button, popover, exec_cmd):
        """Launch app from popover and close it."""
        popover.popdown()
        btn = popover.get_relative_to()
        self._cancel_zoom_animation(btn)
        launch_application(exec_cmd)
        self._start_bounce_animation(btn)
        self._schedule_auto_collapse()

    def _on_icon_clicked(self, button, exec_cmd):
        """Launch the clicked application."""
        self._cancel_zoom_animation(button)
        launch_application(exec_cmd)
        self._start_bounce_animation(button)
        self._schedule_auto_collapse()

    def _cancel_zoom_animation(self, btn):
        """Cancel any running zoom animation on the given button."""
        key = id(btn)
        state = self._zoom_state.get(key)
        if state and state.get("timer"):
            GLib.source_remove(state["timer"])
            del self._zoom_state[key]

    def _start_bounce_animation(self, btn):
        """Start bounce animation on the clicked icon button."""
        key = id(btn)
        if key in self._bounce_state:
            return

        align = None
        for item in self._icon_buttons:
            if item[0] == btn:
                align = item[3]
                break

        if not align:
            return

        self._bounce_state[key] = {
            "start_time": GLib.get_monotonic_time(),
            "timer": GLib.timeout_add(16, self._bounce_tick, key),  # ~60fps
            "btn": btn,
            "align": align,
        }

    def _bounce_tick(self, key):
        """Advance one frame of the bounce animation."""
        state = self._bounce_state.get(key)
        if not state:
            return False

        elapsed = (GLib.get_monotonic_time() - state["start_time"]) / 1000000.0  # seconds

        # Sinusoidal bounce going UP only, infinite loop until dock closes
        # Frequency: 1 bounce per second
        # 150px container - 48px icon = 102px available, use 64px
        bounce = abs(math.sin(elapsed * math.pi * 2))
        y_offset = bounce * 0.42  # ~64px of 150px

        state["align"].set_property("yalign", 0.5 - y_offset)

        return True

    def _schedule_auto_collapse(self):
        """Auto-collapse the dock 3 seconds after launching an application."""
        if not self._expanded:
            return
        # Cancel any previous pending auto-collapse
        if hasattr(self, "_auto_collapse_id") and self._auto_collapse_id:
            GLib.source_remove(self._auto_collapse_id)
        self._auto_collapse_id = GLib.timeout_add_seconds(3, self._auto_collapse)

    def _auto_collapse(self):
        """Collapse the dock (called from timer)."""
        self._auto_collapse_id = None
        # Stop all bounce animations
        for key, state in list(self._bounce_state.items()):
            if state.get("timer"):
                GLib.source_remove(state["timer"])
            if state.get("align"):
                state["align"].set_property("yalign", 0.5)
        self._bounce_state.clear()

        if self._expanded:
            self._expanded = False
            self._revealer.set_reveal_child(False)
            self._tab_draw.queue_draw()
            self._save_state()
        return False  # GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ #
    # Popover dismiss on outside click
    # ------------------------------------------------------------------ #

    def _dismiss_active_popover(self):
        """Close the currently active popover, if any."""
        if self._active_popover:
            try:
                self._active_popover.popdown()
            except (AttributeError, RuntimeError):
                pass
            self._active_popover = None

    def _on_popover_closed(self, popover):
        """Clear active popover reference when it closes."""
        if self._active_popover is popover:
            self._active_popover = None

    def _on_window_button_press(self, widget, event):
        """Dismiss any open popover when clicking on the dock background."""
        self._dismiss_active_popover()
        return False  # Let the event propagate

    # ------------------------------------------------------------------ #
    # Icon zoom animation on hover
    # ------------------------------------------------------------------ #

    def _on_icon_enter(self, btn, event, entry):
        """Start zoom-in animation when mouse enters an icon button."""
        self._animate_icon_zoom(btn, ICON_ZOOM_SIZE, entry)
        return False

    def _on_icon_leave(self, btn, event, entry):
        """Start zoom-out animation when mouse leaves an icon button."""
        self._animate_icon_zoom(btn, ICON_SIZE, entry)
        return False

    def _animate_icon_zoom(self, btn, target_size, entry):
        """Begin an animated zoom toward target_size for the given icon button."""
        key = id(btn)
        state = self._zoom_state.get(key)

        # Cancel any running animation for this button
        if state and state.get("timer"):
            GLib.source_remove(state["timer"])

        current = state["current_size"] if state else ICON_SIZE

        # Find the Fixed container to get the image
        image = btn.get_child()

        self._zoom_state[key] = {
            "current_size": current,
            "target_size": target_size,
            "entry": entry,
            "btn": btn,
            "image": image,
            "timer": GLib.timeout_add(ICON_ZOOM_INTERVAL_MS, self._zoom_tick, key),
        }

    def _zoom_tick(self, key):
        """Advance one frame of the icon zoom animation."""
        state = self._zoom_state.get(key)
        if not state:
            return False

        current = state["current_size"]
        target = state["target_size"]

        if current == target:
            state["timer"] = None
            return False  # Animation complete

        # Step toward target
        if current < target:
            new_size = min(current + ICON_ZOOM_STEP, target)
        else:
            new_size = max(current - ICON_ZOOM_STEP, target)

        state["current_size"] = new_size
        image = state.get("image")
        if image:
            self._apply_icon_size(image, new_size, state.get("entry"))

        if new_size == target:
            state["timer"] = None
            return False  # Done
        return True  # Continue animation

    def _apply_icon_size(self, image, size, entry=None):
        """Set the icon image to the given pixel size."""
        if image is None:
            return
        if entry and entry.pixbuf:
            pixbuf = entry.pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
            image.set_from_pixbuf(pixbuf)
        else:
            image.set_pixel_size(size)

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
            color = _hex_to_rgb(NORD["nord8"])  # bright blue
            radius = INDICATOR_DOT_RADIUS + 0.5
        else:
            # Running: subtle frost dot
            color = _hex_to_rgb(NORD["nord9"])  # muted blue
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
