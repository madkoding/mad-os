"""
madOS Photo Viewer - Image Canvas
===================================

A GTK DrawingArea-based canvas that handles:
    - Image rendering with zoom and pan
    - Fit-to-window and actual-size modes
    - Mouse-driven pan (drag when zoomed in)
    - Mouse-driven drawing overlay for editing tools
    - Cairo-based compositing of edit strokes on top of the image
    - Scroll-wheel and keyboard zoom

The canvas translates screen coordinates to image coordinates for tool
operations, ensuring that drawing occurs at the correct pixel positions
regardless of zoom/pan state.
"""

import math
import cairo

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from .tools import (
    TOOL_NONE, TOOL_PAINT, TOOL_TEXT, TOOL_BLUR, TOOL_PIXELATE, TOOL_ERASER,
    PaintStroke, TextStroke, BlurStroke, PixelateStroke, EditHistory,
)

# Zoom limits
ZOOM_MIN = 0.05
ZOOM_MAX = 20.0
ZOOM_STEP = 1.25  # Multiplicative step for zoom in/out


class ImageCanvas(Gtk.DrawingArea):
    """A drawing area that displays an image with zoom, pan, and editing overlays."""

    def __init__(self):
        """Initialize the canvas with default state."""
        super().__init__()

        # Image data
        self._pixbuf = None       # Original loaded GdkPixbuf
        self._filepath = None     # Path of the currently loaded image

        # View state
        self._zoom = 1.0          # Current zoom factor
        self._pan_x = 0.0         # Pan offset X (in screen pixels)
        self._pan_y = 0.0         # Pan offset Y (in screen pixels)
        self._fit_mode = True     # Auto-fit to window

        # Drag state for panning
        self._dragging = False
        self._drag_start_x = 0.0
        self._drag_start_y = 0.0
        self._drag_start_pan_x = 0.0
        self._drag_start_pan_y = 0.0

        # Tool state
        self._active_tool = TOOL_NONE
        self._tool_color = (1.0, 1.0, 1.0, 1.0)
        self._brush_size = 5.0
        self._font_size = 24.0
        self._text_content = ''
        self._drawing = False      # Is user currently drawing a stroke?
        self._current_stroke = None  # Stroke being actively drawn

        # Edit history
        self.history = EditHistory()

        # Callback for when edits change (so app can update UI)
        self.on_edits_changed = None

        # Enable events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.SMOOTH_SCROLL_MASK
        )

        # Connect signals
        self.connect('draw', self._on_draw)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event', self._on_motion)
        self.connect('scroll-event', self._on_scroll)
        self.connect('size-allocate', self._on_size_allocate)

        # Style
        style = self.get_style_context()
        style.add_class('canvas-area')

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_image(self, filepath):
        """Load an image file into the canvas.

        Supports all GdkPixbuf formats plus SVG via librsvg if available.

        Args:
            filepath: Path to the image file.

        Returns:
            True if loaded successfully, False on error.
        """
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
            self._pixbuf = pixbuf
            self._filepath = filepath
            self.history.clear()
            self._fit_mode = True
            self._calculate_fit_zoom()
            self.queue_draw()
            return True
        except GLib.Error as e:
            print(f"Error loading image: {e.message}")
            self._pixbuf = None
            self._filepath = None
            self.queue_draw()
            return False

    def get_pixbuf(self):
        """Return the current original pixbuf, or None."""
        return self._pixbuf

    def get_filepath(self):
        """Return the current image file path, or None."""
        return self._filepath

    def has_image(self):
        """Return True if an image is currently loaded."""
        return self._pixbuf is not None

    def zoom_in(self):
        """Zoom in by one step, centered on the canvas."""
        self._fit_mode = False
        new_zoom = min(self._zoom * ZOOM_STEP, ZOOM_MAX)
        self._apply_zoom_centered(new_zoom)

    def zoom_out(self):
        """Zoom out by one step, centered on the canvas."""
        self._fit_mode = False
        new_zoom = max(self._zoom / ZOOM_STEP, ZOOM_MIN)
        self._apply_zoom_centered(new_zoom)

    def zoom_fit(self):
        """Fit the image to the current window size."""
        self._fit_mode = True
        self._calculate_fit_zoom()
        self.queue_draw()

    def zoom_actual(self):
        """Set zoom to 100% (actual pixel size)."""
        self._fit_mode = False
        self._apply_zoom_centered(1.0)

    def get_zoom_percent(self):
        """Return the current zoom level as a percentage integer."""
        return int(self._zoom * 100)

    def set_tool(self, tool):
        """Set the active editing tool.

        Args:
            tool: One of TOOL_NONE, TOOL_PAINT, TOOL_TEXT, TOOL_BLUR,
                  TOOL_PIXELATE, TOOL_ERASER.
        """
        self._active_tool = tool
        # Update cursor based on tool
        window = self.get_window()
        if window is None:
            return
        if tool == TOOL_NONE:
            window.set_cursor(None)
        elif tool == TOOL_ERASER:
            cursor = Gdk.Cursor.new_from_name(self.get_display(), 'not-allowed')
            window.set_cursor(cursor)
        elif tool == TOOL_TEXT:
            cursor = Gdk.Cursor.new_from_name(self.get_display(), 'text')
            window.set_cursor(cursor)
        else:
            cursor = Gdk.Cursor.new_from_name(self.get_display(), 'crosshair')
            window.set_cursor(cursor)

    def set_tool_color(self, r, g, b, a=1.0):
        """Set the current tool color as RGBA floats 0-1."""
        self._tool_color = (r, g, b, a)

    def set_brush_size(self, size):
        """Set the brush size in pixels."""
        self._brush_size = max(1.0, min(200.0, size))

    def set_font_size(self, size):
        """Set the text tool font size in pixels."""
        self._font_size = max(6.0, min(200.0, size))

    def set_text_content(self, text):
        """Set the text content for the text tool."""
        self._text_content = text

    def undo(self):
        """Undo the last stroke."""
        stroke = self.history.undo()
        if stroke:
            self._notify_edits_changed()
            self.queue_draw()

    def redo(self):
        """Redo the last undone stroke."""
        stroke = self.history.redo()
        if stroke:
            self._notify_edits_changed()
            self.queue_draw()

    def clear_edits(self):
        """Clear all editing strokes."""
        self.history.clear()
        self._notify_edits_changed()
        self.queue_draw()

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

    def _screen_to_image(self, sx, sy):
        """Convert screen coordinates to image pixel coordinates.

        Args:
            sx: Screen X coordinate.
            sy: Screen Y coordinate.

        Returns:
            Tuple (ix, iy) of image coordinates.
        """
        alloc = self.get_allocation()
        if self._pixbuf is None:
            return (sx, sy)

        img_w = self._pixbuf.get_width()
        img_h = self._pixbuf.get_height()

        # Center of canvas
        cx = alloc.width / 2.0
        cy = alloc.height / 2.0

        # Image origin on screen
        ox = cx - (img_w * self._zoom) / 2.0 + self._pan_x
        oy = cy - (img_h * self._zoom) / 2.0 + self._pan_y

        ix = (sx - ox) / self._zoom
        iy = (sy - oy) / self._zoom
        return (ix, iy)

    def _image_to_screen(self, ix, iy):
        """Convert image pixel coordinates to screen coordinates.

        Args:
            ix: Image X coordinate.
            iy: Image Y coordinate.

        Returns:
            Tuple (sx, sy) of screen coordinates.
        """
        alloc = self.get_allocation()
        if self._pixbuf is None:
            return (ix, iy)

        img_w = self._pixbuf.get_width()
        img_h = self._pixbuf.get_height()

        cx = alloc.width / 2.0
        cy = alloc.height / 2.0

        ox = cx - (img_w * self._zoom) / 2.0 + self._pan_x
        oy = cy - (img_h * self._zoom) / 2.0 + self._pan_y

        sx = ix * self._zoom + ox
        sy = iy * self._zoom + oy
        return (sx, sy)

    # ------------------------------------------------------------------
    # Zoom helpers
    # ------------------------------------------------------------------

    def _calculate_fit_zoom(self):
        """Calculate the zoom level to fit the image in the current allocation."""
        if self._pixbuf is None:
            return

        alloc = self.get_allocation()
        if alloc.width < 2 or alloc.height < 2:
            return

        img_w = self._pixbuf.get_width()
        img_h = self._pixbuf.get_height()

        if img_w == 0 or img_h == 0:
            return

        zoom_x = alloc.width / img_w
        zoom_y = alloc.height / img_h
        self._zoom = min(zoom_x, zoom_y, 1.0)  # Don't zoom beyond 100% for fit
        self._pan_x = 0.0
        self._pan_y = 0.0

    def _apply_zoom_centered(self, new_zoom):
        """Apply a new zoom level, keeping the canvas center stable.

        Args:
            new_zoom: The target zoom factor.
        """
        self._zoom = new_zoom
        # Recenter pan if we're near center
        self.queue_draw()

    def _zoom_at_point(self, new_zoom, screen_x, screen_y):
        """Zoom in/out centered on a specific screen point.

        Adjusts the pan offset so the image pixel under the cursor stays
        in the same screen position.

        Args:
            new_zoom: Target zoom factor.
            screen_x: Screen X coordinate of the zoom center.
            screen_y: Screen Y coordinate of the zoom center.
        """
        if self._pixbuf is None:
            return

        old_zoom = self._zoom
        alloc = self.get_allocation()
        img_w = self._pixbuf.get_width()
        img_h = self._pixbuf.get_height()

        # Canvas center
        cx = alloc.width / 2.0
        cy = alloc.height / 2.0

        # Image coordinate under cursor at old zoom
        old_ox = cx - (img_w * old_zoom) / 2.0 + self._pan_x
        old_oy = cy - (img_h * old_zoom) / 2.0 + self._pan_y
        img_x = (screen_x - old_ox) / old_zoom
        img_y = (screen_y - old_oy) / old_zoom

        # New image origin to keep the same pixel under cursor
        new_ox = screen_x - img_x * new_zoom
        new_oy = screen_y - img_y * new_zoom

        self._pan_x = new_ox - (cx - (img_w * new_zoom) / 2.0)
        self._pan_y = new_oy - (cy - (img_h * new_zoom) / 2.0)
        self._zoom = new_zoom
        self.queue_draw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _on_draw(self, widget, cr):
        """Render the image and editing overlays.

        Args:
            widget: The DrawingArea widget.
            cr: The cairo.Context.
        """
        alloc = self.get_allocation()

        # Background
        cr.set_source_rgb(0.18, 0.20, 0.25)  # nord0
        cr.rectangle(0, 0, alloc.width, alloc.height)
        cr.fill()

        if self._pixbuf is None:
            # No image - draw placeholder text
            cr.set_source_rgb(0.30, 0.34, 0.42)  # nord3
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(18)
            text = "Open an image to begin"
            extents = cr.text_extents(text)
            cr.move_to(
                (alloc.width - extents.width) / 2.0,
                (alloc.height + extents.height) / 2.0
            )
            cr.show_text(text)
            return

        img_w = self._pixbuf.get_width()
        img_h = self._pixbuf.get_height()

        # Compute drawing position (centered with pan offset)
        draw_w = img_w * self._zoom
        draw_h = img_h * self._zoom
        draw_x = (alloc.width - draw_w) / 2.0 + self._pan_x
        draw_y = (alloc.height - draw_h) / 2.0 + self._pan_y

        # Draw checkerboard background for transparency
        if self._pixbuf.get_has_alpha():
            self._draw_checkerboard(cr, draw_x, draw_y, draw_w, draw_h)

        # Draw the image
        cr.save()
        cr.translate(draw_x, draw_y)
        cr.scale(self._zoom, self._zoom)
        Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
        cr.get_source().set_filter(
            cairo.FILTER_NEAREST if self._zoom > 4.0 else cairo.FILTER_BILINEAR
        )
        cr.paint()
        cr.restore()

        # Draw blur/pixelate previews would require applying to a temp pixbuf;
        # for performance, we only show them in the final composite.
        # For blur/pixelate strokes, show a translucent overlay path instead.
        for stroke in self.history.strokes:
            if stroke.type in ('blur', 'pixelate'):
                self._draw_effect_preview(cr, stroke, draw_x, draw_y)

        # Draw paint/text strokes in canvas coordinates
        cr.save()
        cr.translate(draw_x, draw_y)
        cr.scale(self._zoom, self._zoom)
        for stroke in self.history.get_paint_strokes():
            stroke.draw(cr)
        cr.restore()

        # Draw current in-progress stroke
        if self._current_stroke is not None:
            cr.save()
            cr.translate(draw_x, draw_y)
            cr.scale(self._zoom, self._zoom)
            if hasattr(self._current_stroke, 'draw'):
                self._current_stroke.draw(cr)
            cr.restore()

    def _draw_checkerboard(self, cr, x, y, w, h):
        """Draw a checkerboard pattern to indicate transparency.

        Args:
            cr: Cairo context.
            x, y: Top-left position.
            w, h: Width and height.
        """
        check_size = 12
        cr.save()
        cr.rectangle(x, y, w, h)
        cr.clip()
        for row in range(int(y), int(y + h) + check_size, check_size):
            for col in range(int(x), int(x + w) + check_size, check_size):
                r_idx = (row - int(y)) // check_size
                c_idx = (col - int(x)) // check_size
                if (r_idx + c_idx) % 2 == 0:
                    cr.set_source_rgb(0.85, 0.85, 0.85)
                else:
                    cr.set_source_rgb(0.65, 0.65, 0.65)
                cr.rectangle(col, row, check_size, check_size)
                cr.fill()
        cr.restore()

    def _draw_effect_preview(self, cr, stroke, draw_x, draw_y):
        """Draw a translucent overlay showing where blur/pixelate was applied.

        Args:
            cr: Cairo context.
            stroke: A BlurStroke or PixelateStroke.
            draw_x: Image drawing origin X.
            draw_y: Image drawing origin Y.
        """
        if not stroke.points:
            return
        cr.save()
        cr.translate(draw_x, draw_y)
        cr.scale(self._zoom, self._zoom)

        if stroke.type == 'blur':
            cr.set_source_rgba(0.53, 0.75, 0.82, 0.15)  # nord8 translucent
        else:
            cr.set_source_rgba(0.75, 0.56, 0.68, 0.15)  # nord15 translucent

        cr.set_line_width(stroke.brush_size)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if len(stroke.points) == 1:
            x, y = stroke.points[0]
            cr.arc(x, y, stroke.brush_size / 2.0, 0, 2 * math.pi)
            cr.fill()
        else:
            cr.move_to(*stroke.points[0])
            for pt in stroke.points[1:]:
                cr.line_to(*pt)
            cr.stroke()
        cr.restore()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_size_allocate(self, widget, allocation):
        """Handle window resize.

        Args:
            widget: The DrawingArea widget.
            allocation: New allocation rectangle.
        """
        if self._fit_mode:
            self._calculate_fit_zoom()

    def _on_scroll(self, widget, event):
        """Handle mouse scroll for zooming.

        Args:
            widget: The DrawingArea widget.
            event: The GdkEventScroll.

        Returns:
            True to stop propagation.
        """
        if self._pixbuf is None:
            return False

        # Determine scroll direction
        has_delta, dx, dy = event.get_scroll_deltas()
        if has_delta:
            if dy < 0:
                direction = 1  # zoom in
            elif dy > 0:
                direction = -1  # zoom out
            else:
                return False
        else:
            if event.direction == Gdk.ScrollDirection.UP:
                direction = 1
            elif event.direction == Gdk.ScrollDirection.DOWN:
                direction = -1
            else:
                return False

        self._fit_mode = False
        if direction > 0:
            new_zoom = min(self._zoom * ZOOM_STEP, ZOOM_MAX)
        else:
            new_zoom = max(self._zoom / ZOOM_STEP, ZOOM_MIN)

        self._zoom_at_point(new_zoom, event.x, event.y)
        return True

    def _on_button_press(self, widget, event):
        """Handle mouse button press for pan and tool operations.

        Args:
            widget: The DrawingArea widget.
            event: The GdkEventButton.

        Returns:
            True to stop propagation.
        """
        if self._pixbuf is None:
            return False

        if event.button == 1:  # Left click
            if self._active_tool == TOOL_NONE:
                # Start panning
                self._dragging = True
                self._drag_start_x = event.x
                self._drag_start_y = event.y
                self._drag_start_pan_x = self._pan_x
                self._drag_start_pan_y = self._pan_y
                window = self.get_window()
                if window:
                    cursor = Gdk.Cursor.new_from_name(self.get_display(), 'grabbing')
                    window.set_cursor(cursor)
            elif self._active_tool == TOOL_PAINT:
                ix, iy = self._screen_to_image(event.x, event.y)
                self._current_stroke = PaintStroke(self._tool_color, self._brush_size)
                self._current_stroke.add_point(ix, iy)
                self._drawing = True
                self.queue_draw()
            elif self._active_tool == TOOL_TEXT:
                ix, iy = self._screen_to_image(event.x, event.y)
                if self._text_content.strip():
                    stroke = TextStroke(ix, iy, self._text_content, self._tool_color, self._font_size)
                    self.history.add_stroke(stroke)
                    self._notify_edits_changed()
                    self.queue_draw()
            elif self._active_tool == TOOL_BLUR:
                ix, iy = self._screen_to_image(event.x, event.y)
                self._current_stroke = BlurStroke(self._brush_size)
                self._current_stroke.add_point(ix, iy)
                self._drawing = True
                self.queue_draw()
            elif self._active_tool == TOOL_PIXELATE:
                ix, iy = self._screen_to_image(event.x, event.y)
                self._current_stroke = PixelateStroke(self._brush_size)
                self._current_stroke.add_point(ix, iy)
                self._drawing = True
                self.queue_draw()
            elif self._active_tool == TOOL_ERASER:
                ix, iy = self._screen_to_image(event.x, event.y)
                if self.history.erase_at(ix, iy, radius=self._brush_size):
                    self._notify_edits_changed()
                    self.queue_draw()

        elif event.button == 2:  # Middle click - always pan
            self._dragging = True
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._drag_start_pan_x = self._pan_x
            self._drag_start_pan_y = self._pan_y

        return True

    def _on_button_release(self, widget, event):
        """Handle mouse button release to finish pan/draw operations.

        Args:
            widget: The DrawingArea widget.
            event: The GdkEventButton.

        Returns:
            True to stop propagation.
        """
        if event.button == 1:
            if self._dragging:
                self._dragging = False
                # Restore tool cursor
                self.set_tool(self._active_tool)
            elif self._drawing and self._current_stroke is not None:
                self._drawing = False
                self.history.add_stroke(self._current_stroke)
                self._current_stroke = None
                self._notify_edits_changed()
                self.queue_draw()
        elif event.button == 2:
            self._dragging = False

        return True

    def _on_motion(self, widget, event):
        """Handle mouse motion for panning and drawing.

        Args:
            widget: The DrawingArea widget.
            event: The GdkEventMotion.

        Returns:
            True to stop propagation.
        """
        if self._dragging:
            dx = event.x - self._drag_start_x
            dy = event.y - self._drag_start_y
            self._pan_x = self._drag_start_pan_x + dx
            self._pan_y = self._drag_start_pan_y + dy
            self._fit_mode = False
            self.queue_draw()
            return True

        if self._drawing and self._current_stroke is not None:
            ix, iy = self._screen_to_image(event.x, event.y)
            self._current_stroke.add_point(ix, iy)
            self.queue_draw()
            return True

        if self._active_tool == TOOL_ERASER:
            # Continuously erase on drag
            if event.state & Gdk.ModifierType.BUTTON1_MASK:
                ix, iy = self._screen_to_image(event.x, event.y)
                if self.history.erase_at(ix, iy, radius=self._brush_size):
                    self._notify_edits_changed()
                    self.queue_draw()

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _notify_edits_changed(self):
        """Call the edits-changed callback if one is registered."""
        if self.on_edits_changed:
            self.on_edits_changed()
