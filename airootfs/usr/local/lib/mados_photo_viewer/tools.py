"""
madOS Photo Viewer - Drawing and Editing Tools
================================================

Provides tool classes for image editing:
    - PaintTool: Freehand drawing with configurable color and brush size
    - TextTool: Click-to-place text with font size and color
    - BlurTool: Paint-over gaussian-like blur using GdkPixbuf scale trick
    - PixelateTool: Paint-over pixelation using nearest-neighbor downsampling
    - EraserTool: Removes drawing strokes by index

All tools store their operations as serializable stroke data so that
undo/redo and final compositing can replay them.
"""

import math
import cairo

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib


# ---------------------------------------------------------------------------
# Tool type constants
# ---------------------------------------------------------------------------
TOOL_NONE = "none"
TOOL_PAINT = "paint"
TOOL_TEXT = "text"
TOOL_BLUR = "blur"
TOOL_PIXELATE = "pixelate"
TOOL_ERASER = "eraser"


# ---------------------------------------------------------------------------
# Stroke data classes
# ---------------------------------------------------------------------------
class PaintStroke:
    """A freehand paint stroke composed of a list of (x, y) points."""

    def __init__(self, color, brush_size):
        """Initialize with a color tuple (r, g, b, a) and brush size in pixels."""
        self.type = TOOL_PAINT
        self.color = color  # (r, g, b, a)  floats 0-1
        self.brush_size = brush_size
        self.points = []  # [(x, y), ...]

    def add_point(self, x, y):
        """Append a point to the stroke path."""
        self.points.append((x, y))

    def draw(self, cr):
        """Render this stroke onto a cairo context.

        Args:
            cr: A cairo.Context to draw on.
        """
        if len(self.points) < 1:
            return
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.brush_size)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if len(self.points) == 1:
            # Single dot
            x, y = self.points[0]
            cr.arc(x, y, self.brush_size / 2.0, 0, 2 * math.pi)
            cr.fill()
        else:
            cr.move_to(*self.points[0])
            for pt in self.points[1:]:
                cr.line_to(*pt)
            cr.stroke()


class TextStroke:
    """A placed text annotation."""

    def __init__(self, x, y, text, color, font_size):
        """Initialize with position, text content, color, and font size."""
        self.type = TOOL_TEXT
        self.x = x
        self.y = y
        self.text = text
        self.color = color  # (r, g, b, a)
        self.font_size = font_size

    def draw(self, cr):
        """Render this text annotation onto a cairo context.

        Args:
            cr: A cairo.Context to draw on.
        """
        if not self.text:
            return
        cr.set_source_rgba(*self.color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(self.font_size)
        cr.move_to(self.x, self.y)
        cr.show_text(self.text)


class BlurStroke:
    """A paint-based blur area described by a path of (x, y) points and radius."""

    def __init__(self, brush_size):
        """Initialize with brush radius in pixels."""
        self.type = TOOL_BLUR
        self.brush_size = brush_size
        self.points = []  # [(x, y), ...]

    def add_point(self, x, y):
        """Append a point to the blur path."""
        self.points.append((x, y))

    def apply_to_pixbuf(self, pixbuf):
        """Apply a gaussian-like blur along the stroke path on a GdkPixbuf.

        This uses the scale-down-then-scale-up trick: for each point in the
        stroke, extract a bounding box, scale it down by 4x, then scale back
        up with bilinear interpolation, producing a blur effect.

        Args:
            pixbuf: A GdkPixbuf.Pixbuf to modify in place (via composite).

        Returns:
            The modified GdkPixbuf.Pixbuf.
        """
        if not self.points or pixbuf is None:
            return pixbuf

        width = pixbuf.get_width()
        height = pixbuf.get_height()
        radius = int(self.brush_size)
        scale_factor = 4  # How much to downsample for blur

        for px, py in self.points:
            # Compute bounding box for this blur point
            x0 = max(0, int(px - radius))
            y0 = max(0, int(py - radius))
            x1 = min(width, int(px + radius))
            y1 = min(height, int(py + radius))
            rw = x1 - x0
            rh = y1 - y0
            if rw < 2 or rh < 2:
                continue

            # Extract sub-region
            sub = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, pixbuf.get_has_alpha(), 8, rw, rh
            )
            pixbuf.copy_area(x0, y0, rw, rh, sub, 0, 0)

            # Scale down
            small_w = max(1, rw // scale_factor)
            small_h = max(1, rh // scale_factor)
            small = sub.scale_simple(small_w, small_h, GdkPixbuf.InterpType.BILINEAR)

            # Scale back up (this creates the blur)
            blurred = small.scale_simple(rw, rh, GdkPixbuf.InterpType.BILINEAR)

            # Copy blurred region back
            blurred.copy_area(0, 0, rw, rh, pixbuf, x0, y0)

        return pixbuf


class PixelateStroke:
    """A paint-based pixelation area described by a path and pixel block size."""

    def __init__(self, brush_size, block_size=8):
        """Initialize with brush radius and pixelation block size.

        Args:
            brush_size: Radius of the pixelation brush in pixels.
            block_size: Size of each pixel block (default 8).
        """
        self.type = TOOL_PIXELATE
        self.brush_size = brush_size
        self.block_size = block_size
        self.points = []

    def add_point(self, x, y):
        """Append a point to the pixelation path."""
        self.points.append((x, y))

    def apply_to_pixbuf(self, pixbuf):
        """Apply pixelation along the stroke path on a GdkPixbuf.

        For each point, extract a region, scale it down with NEAREST
        interpolation (creating blocky pixels), then scale back up.

        Args:
            pixbuf: A GdkPixbuf.Pixbuf to modify.

        Returns:
            The modified GdkPixbuf.Pixbuf.
        """
        if not self.points or pixbuf is None:
            return pixbuf

        width = pixbuf.get_width()
        height = pixbuf.get_height()
        radius = int(self.brush_size)
        block = max(2, self.block_size)

        for px, py in self.points:
            x0 = max(0, int(px - radius))
            y0 = max(0, int(py - radius))
            x1 = min(width, int(px + radius))
            y1 = min(height, int(py + radius))
            rw = x1 - x0
            rh = y1 - y0
            if rw < 2 or rh < 2:
                continue

            sub = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, pixbuf.get_has_alpha(), 8, rw, rh
            )
            pixbuf.copy_area(x0, y0, rw, rh, sub, 0, 0)

            # Scale down to tiny (creates pixelation on scale-up)
            small_w = max(1, rw // block)
            small_h = max(1, rh // block)
            small = sub.scale_simple(small_w, small_h, GdkPixbuf.InterpType.NEAREST)

            # Scale back up with NEAREST to get sharp pixel blocks
            pixelated = small.scale_simple(rw, rh, GdkPixbuf.InterpType.NEAREST)

            pixelated.copy_area(0, 0, rw, rh, pixbuf, x0, y0)

        return pixbuf


# ---------------------------------------------------------------------------
# EditHistory: undo/redo manager
# ---------------------------------------------------------------------------
class EditHistory:
    """Manages undo/redo stacks for editing strokes."""

    def __init__(self):
        """Initialize empty history."""
        self.strokes = []  # List of stroke objects
        self.redo_stack = []  # Strokes removed by undo

    @property
    def has_edits(self):
        """Return True if there are any strokes."""
        return len(self.strokes) > 0

    def add_stroke(self, stroke):
        """Add a completed stroke. Clears the redo stack.

        Args:
            stroke: A PaintStroke, TextStroke, BlurStroke, or PixelateStroke.
        """
        self.strokes.append(stroke)
        self.redo_stack.clear()

    def undo(self):
        """Remove the most recent stroke and push it to redo stack.

        Returns:
            The removed stroke, or None if nothing to undo.
        """
        if self.strokes:
            stroke = self.strokes.pop()
            self.redo_stack.append(stroke)
            return stroke
        return None

    def redo(self):
        """Restore the most recently undone stroke.

        Returns:
            The restored stroke, or None if nothing to redo.
        """
        if self.redo_stack:
            stroke = self.redo_stack.pop()
            self.strokes.append(stroke)
            return stroke
        return None

    def clear(self):
        """Clear all strokes and redo history."""
        self.strokes.clear()
        self.redo_stack.clear()

    def erase_at(self, x, y, radius=10):
        """Remove strokes that pass near the given point (eraser tool).

        Checks paint strokes for point proximity, text strokes for
        bounding box overlap, and blur/pixelate for path proximity.

        Args:
            x: X coordinate to test.
            y: Y coordinate to test.
            radius: Hit-test radius in pixels.

        Returns:
            True if any strokes were removed, False otherwise.
        """
        to_remove = []
        for i, stroke in enumerate(self.strokes):
            if stroke.type in (TOOL_PAINT, TOOL_BLUR, TOOL_PIXELATE):
                for px, py in stroke.points:
                    if math.hypot(px - x, py - y) < radius + stroke.brush_size / 2:
                        to_remove.append(i)
                        break
            elif stroke.type == TOOL_TEXT:
                if math.hypot(stroke.x - x, stroke.y - y) < radius + stroke.font_size:
                    to_remove.append(i)

        if to_remove:
            for i in reversed(to_remove):
                removed = self.strokes.pop(i)
                self.redo_stack.append(removed)
            return True
        return False

    def get_paint_strokes(self):
        """Return only PaintStroke and TextStroke objects for cairo overlay.

        Returns:
            List of strokes that are drawn via cairo.
        """
        return [s for s in self.strokes if s.type in (TOOL_PAINT, TOOL_TEXT)]

    def get_pixbuf_strokes(self):
        """Return only BlurStroke and PixelateStroke objects for pixbuf editing.

        Returns:
            List of strokes that modify the pixbuf directly.
        """
        return [s for s in self.strokes if s.type in (TOOL_BLUR, TOOL_PIXELATE)]


def compose_edits_onto_pixbuf(pixbuf, history):
    """Apply all editing strokes onto a pixbuf to produce the final image.

    First applies blur/pixelate strokes directly to the pixbuf data, then
    renders paint/text strokes via cairo onto a surface and composites
    everything into the final output.

    Args:
        pixbuf: The original GdkPixbuf.Pixbuf.
        history: An EditHistory instance.

    Returns:
        A new GdkPixbuf.Pixbuf with all edits applied.
    """
    if not history.has_edits:
        return pixbuf.copy()

    width = pixbuf.get_width()
    height = pixbuf.get_height()

    # Work on a copy to apply blur/pixelate
    result = pixbuf.copy()

    # Apply pixbuf-level strokes
    for stroke in history.get_pixbuf_strokes():
        result = stroke.apply_to_pixbuf(result)

    # Now draw paint/text strokes using cairo
    paint_strokes = history.get_paint_strokes()
    if paint_strokes:
        # Create a cairo surface from the pixbuf
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)

        # Draw the pixbuf onto the surface
        import gi

        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk

        Gdk.cairo_set_source_pixbuf(cr, result, 0, 0)
        cr.paint()

        # Draw all paint/text strokes
        for stroke in paint_strokes:
            cr.save()
            stroke.draw(cr)
            cr.restore()

        # Convert the surface back to a pixbuf
        result = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)

    return result
