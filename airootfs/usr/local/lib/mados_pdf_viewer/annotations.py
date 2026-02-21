"""
madOS PDF Viewer - Annotations Module

Provides data models and UI helpers for:
  - TextAnnotation: text overlays placed on PDF pages.
  - SignaturePad: freehand drawing canvas for digital signatures.
  - SignaturePlacement: a placed signature on a page.
  - FormFieldManager: detection and interaction with PDF form fields.
"""

import os
import json
import math
import cairo

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from .theme import hex_to_rgb_float, NORD_FROST, NORD_POLAR_NIGHT, NORD_SNOW_STORM
from .translations import get_text

# ── Signature storage directory ───────────────────────────────────────────────

SIGNATURE_DIR = os.path.expanduser("~/.config/mados/signatures")


def ensure_signature_dir():
    """Create the signature storage directory if it does not exist."""
    os.makedirs(SIGNATURE_DIR, exist_ok=True)


JSON_EXTENSION = ".json"


class TextAnnotation:
    """
    A text overlay positioned on a specific PDF page.

    Coordinates are in PDF-point space (unscaled).

    Attributes:
        page_index: 0-based page the annotation belongs to.
        x, y:       Position in PDF points (top-left origin after transform).
        text:       The annotation text (may contain newlines).
        font_size:  Font size in PDF points.
        color:      Hex color string, e.g. '#BF616A'.
        opacity:    Opacity in [0..1].
        dragging:   Internal flag for drag operations.
    """

    def __init__(
        self, page_index, x, y, text="", font_size=14, color="#2E3440", opacity=1.0
    ):
        self.page_index = page_index
        self.x = x
        self.y = y
        self.text = text
        self.font_size = font_size
        self.color = color
        self.opacity = opacity
        self.dragging = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0

    def hit_test(self, px, py, scale=1.0):
        """
        Check whether point (px, py) in scaled coords is inside this annotation.

        Uses a simple bounding box based on text length and font size.

        Args:
            px, py: Point in display (scaled) coordinates.
            scale: Current zoom scale.

        Returns:
            True if the point is inside the bounding box.
        """
        x = self.x * scale
        y = self.y * scale
        fs = self.font_size * scale

        lines = self.text.split("\n") if self.text else [""]
        max_line_len = max(len(line) for line in lines) if lines else 1
        w = max_line_len * fs * 0.6  # approximate width
        h = len(lines) * fs * 1.3

        return (x <= px <= x + w) and (y <= py <= y + h)

    def start_drag(self, px, py, scale=1.0):
        """Begin a drag operation from point (px, py) in scaled coords."""
        self.dragging = True
        self._drag_offset_x = px - self.x * scale
        self._drag_offset_y = py - self.y * scale

    def update_drag(self, px, py, scale=1.0):
        """Update position during drag."""
        if self.dragging and scale > 0:
            self.x = (px - self._drag_offset_x) / scale
            self.y = (py - self._drag_offset_y) / scale

    def end_drag(self):
        """End the drag operation."""
        self.dragging = False

    def to_dict(self):
        """Serialize to a JSON-compatible dict."""
        return {
            "page_index": self.page_index,
            "x": self.x,
            "y": self.y,
            "text": self.text,
            "font_size": self.font_size,
            "color": self.color,
            "opacity": self.opacity,
        }

    @classmethod
    def from_dict(cls, d):
        """Deserialize from a dict."""
        return cls(
            page_index=d.get("page_index", 0),
            x=d.get("x", 0),
            y=d.get("y", 0),
            text=d.get("text", ""),
            font_size=d.get("font_size", 14),
            color=d.get("color", "#2E3440"),
            opacity=d.get("opacity", 1.0),
        )


class SignaturePlacement:
    """
    A placed signature on a specific PDF page.

    Attributes:
        page_index: 0-based page number.
        x, y:       Position in PDF points.
        width, height: Size in PDF points.
        surface:    cairo.ImageSurface of the signature image.
        opacity:    Opacity in [0..1].
        dragging:   Internal drag flag.
        resizing:   Internal resize flag.
    """

    DEFAULT_WIDTH = 150
    DEFAULT_HEIGHT = 60

    def __init__(
        self, page_index, x, y, surface, width=None, height=None, opacity=0.85
    ):
        self.page_index = page_index
        self.x = x
        self.y = y
        self.surface = surface
        self.width = width or self.DEFAULT_WIDTH
        self.height = height or self.DEFAULT_HEIGHT
        self.opacity = opacity
        self.dragging = False
        self.resizing = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0

    def hit_test(self, px, py, scale=1.0):
        """Check whether (px, py) in scaled coords hits this signature."""
        x = self.x * scale
        y = self.y * scale
        w = self.width * scale
        h = self.height * scale
        return (x <= px <= x + w) and (y <= py <= y + h)

    def hit_test_resize_handle(self, px, py, scale=1.0, handle_size=10):
        """Check if (px, py) hits the bottom-right resize handle."""
        x2 = (self.x + self.width) * scale
        y2 = (self.y + self.height) * scale
        return (
            x2 - handle_size <= px <= x2 + handle_size
            and y2 - handle_size <= py <= y2 + handle_size
        )

    def start_drag(self, px, py, scale=1.0):
        """Begin dragging the signature."""
        self.dragging = True
        self._drag_offset_x = px - self.x * scale
        self._drag_offset_y = py - self.y * scale

    def update_drag(self, px, py, scale=1.0):
        """Update position while dragging."""
        if self.dragging and scale > 0:
            self.x = (px - self._drag_offset_x) / scale
            self.y = (py - self._drag_offset_y) / scale

    def end_drag(self):
        """End drag operation."""
        self.dragging = False

    def start_resize(self):
        """Begin resizing from the bottom-right corner."""
        self.resizing = True

    def update_resize(self, px, py, scale=1.0):
        """Update size while resizing."""
        if self.resizing and scale > 0:
            new_w = (px / scale) - self.x
            new_h = (py / scale) - self.y
            self.width = max(30, new_w)
            self.height = max(15, new_h)

    def end_resize(self):
        """End resize operation."""
        self.resizing = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SignaturePad  (GTK DrawingArea widget)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SignaturePad(Gtk.DrawingArea):
    """
    A freehand drawing canvas for capturing signatures.

    Renders strokes on a white background.  The result can be exported
    to a cairo.ImageSurface for placement on the PDF.
    """

    def __init__(self, width=400, height=150):
        super().__init__()
        self.set_size_request(width, height)
        self._width = width
        self._height = height

        # List of strokes; each stroke is a list of (x, y) tuples.
        self.strokes = []
        self._current_stroke = []
        self._drawing = False

        # Pen settings
        self.pen_color = (0.18, 0.20, 0.25)  # nord0
        self.pen_width = 2.5

        # Events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)

        style = self.get_style_context()
        style.add_class("signature-pad")

    def clear(self):
        """Clear all strokes."""
        self.strokes = []
        self._current_stroke = []
        self._drawing = False
        self.queue_draw()

    def has_content(self):
        """Return True if there are any strokes drawn."""
        return len(self.strokes) > 0

    def to_surface(self):
        """
        Export the signature as a cairo.ImageSurface (with transparent background).

        Returns:
            cairo.ImageSurface, or None if empty.
        """
        if not self.strokes:
            return None

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self._width, self._height)
        ctx = cairo.Context(surface)

        # Transparent background
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)

        # Draw strokes
        self._render_strokes(ctx)

        return surface

    def save_to_file(self, filepath):
        """
        Save the signature strokes as a JSON file plus a PNG rendering.

        Args:
            filepath: Path without extension; will create .json and .png.
        """
        ensure_signature_dir()

        # Save strokes as JSON
        json_path = filepath + JSON_EXTENSION
        data = {
            "width": self._width,
            "height": self._height,
            "pen_width": self.pen_width,
            "strokes": self.strokes,
        }
        with open(json_path, "w") as f:
            json.dump(data, f)

        # Save PNG
        surface = self.to_surface()
        if surface:
            png_path = filepath + ".png"
            surface.write_to_png(png_path)

    def load_from_file(self, filepath):
        """
        Load signature strokes from a JSON file.

        Args:
            filepath: Path without extension (or with .json).

        Returns:
            True if loaded successfully, False otherwise.
        """
        json_path = (
            filepath if filepath.endswith(JSON_EXTENSION) else filepath + JSON_EXTENSION
        )
        if not os.path.isfile(json_path):
            return False

        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            self.strokes = data.get("strokes", [])
            self.pen_width = data.get("pen_width", 2.5)
            self.queue_draw()
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def _on_draw(self, widget, ctx):
        """Handle the draw signal: render background and strokes."""
        alloc = self.get_allocation()

        # White background
        ctx.set_source_rgb(0.925, 0.937, 0.957)  # nord6
        ctx.rectangle(0, 0, alloc.width, alloc.height)
        ctx.fill()

        # Guide line
        ctx.set_source_rgba(0.53, 0.75, 0.82, 0.4)  # nord8
        y_guide = alloc.height * 0.75
        ctx.set_line_width(1.0)
        ctx.set_dash([4, 4])
        ctx.move_to(20, y_guide)
        ctx.line_to(alloc.width - 20, y_guide)
        ctx.stroke()
        ctx.set_dash([])

        # Draw strokes
        self._render_strokes(ctx)

        # Draw current stroke in progress
        if self._current_stroke and len(self._current_stroke) > 1:
            self._draw_single_stroke(ctx, self._current_stroke)

    def _render_strokes(self, ctx):
        """Render all completed strokes on the given context."""
        for stroke in self.strokes:
            if len(stroke) > 1:
                self._draw_single_stroke(ctx, stroke)

    def _draw_single_stroke(self, ctx, points):
        """Draw a single stroke as a smooth line through the given points."""
        ctx.set_source_rgb(*self.pen_color)
        ctx.set_line_width(self.pen_width)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        ctx.move_to(points[0][0], points[0][1])
        for i in range(1, len(points)):
            # Smooth interpolation: use midpoints for quadratic-like curves
            if i < len(points) - 1:
                mx = (points[i][0] + points[i + 1][0]) / 2.0
                my = (points[i][1] + points[i + 1][1]) / 2.0
                ctx.curve_to(
                    points[i][0],
                    points[i][1],
                    points[i][0],
                    points[i][1],
                    mx,
                    my,
                )
            else:
                ctx.line_to(points[i][0], points[i][1])
        ctx.stroke()

    def _on_button_press(self, widget, event):
        """Start a new stroke on left-click."""
        if event.button == 1:
            self._drawing = True
            self._current_stroke = [(event.x, event.y)]
            self.queue_draw()

    def _on_button_release(self, widget, event):
        """Finish the current stroke."""
        if event.button == 1 and self._drawing:
            self._drawing = False
            if len(self._current_stroke) > 1:
                self.strokes.append(list(self._current_stroke))
            self._current_stroke = []
            self.queue_draw()

    def _on_motion(self, widget, event):
        """Add a point to the current stroke."""
        if self._drawing:
            self._current_stroke.append((event.x, event.y))
            self.queue_draw()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SignatureDialog
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SignatureDialog(Gtk.Dialog):
    """
    A dialog window containing a SignaturePad plus save/load/clear buttons.

    Returns:
        Gtk.ResponseType.OK if the user confirms with a drawn signature.
        Gtk.ResponseType.CANCEL otherwise.

    Access the signature surface via self.get_signature_surface().
    """

    def __init__(self, parent, lang="English"):
        super().__init__(
            title=get_text("draw_signature", lang),
            transient_for=parent,
            modal=True,
        )
        self.lang = lang
        self.set_default_size(450, 280)

        self.add_button(get_text("clear_signature", lang), Gtk.ResponseType.REJECT)
        self.add_button(get_text("load_signature", lang), Gtk.ResponseType.APPLY)
        self.add_button(get_text("save_signature", lang), Gtk.ResponseType.YES)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(8)
        content.set_margin_bottom(8)

        label = Gtk.Label(label=get_text("draw_signature", lang))
        label.set_halign(Gtk.Align.START)
        content.pack_start(label, False, False, 0)

        self.signature_pad = SignaturePad(420, 140)
        content.pack_start(self.signature_pad, True, True, 0)

        self.connect("response", self._on_response)
        self.show_all()

    def get_signature_surface(self):
        """Return the drawn signature as a cairo.ImageSurface, or None."""
        return self.signature_pad.to_surface()

    def _on_response(self, dialog, response_id):
        """Handle special response codes (clear, save, load)."""
        if response_id == Gtk.ResponseType.REJECT:
            # Clear
            self.signature_pad.clear()
            # Don't close the dialog - re-emit to stay open
            self.stop_emission_by_name("response")
            return

        if response_id == Gtk.ResponseType.YES:
            # Save signature
            if self.signature_pad.has_content():
                ensure_signature_dir()
                # Generate a filename from timestamp
                import time

                name = f"signature_{int(time.time())}"
                path = os.path.join(SIGNATURE_DIR, name)
                self.signature_pad.save_to_file(path)
                self._show_info(get_text("signature_saved", self.lang))
            self.stop_emission_by_name("response")
            return

        if response_id == Gtk.ResponseType.APPLY:
            # Load signature
            self._load_signature_chooser()
            self.stop_emission_by_name("response")

    def _load_signature_chooser(self):
        """Show a file chooser to pick a saved signature JSON."""
        ensure_signature_dir()
        chooser = Gtk.FileChooserDialog(
            title=get_text("load_signature", self.lang),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button("Open", Gtk.ResponseType.OK)

        ff = Gtk.FileFilter()
        ff.set_name(f"Signature files (*{JSON_EXTENSION})")
        ff.add_pattern(f"*{JSON_EXTENSION}")
        chooser.add_filter(ff)
        chooser.set_current_folder(SIGNATURE_DIR)

        if chooser.run() == Gtk.ResponseType.OK:
            filepath = chooser.get_filename()
            if self.signature_pad.load_from_file(filepath):
                self._show_info(get_text("signature_loaded", self.lang))
        chooser.destroy()

    def _show_info(self, message):
        """Show a brief info dialog."""
        dlg = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        dlg.run()
        dlg.destroy()


class TextAnnotationDialog(Gtk.Dialog):
    """
    Dialog for creating or editing a text annotation.

    Lets the user enter text, choose font size, and pick a color.
    """

    def __init__(self, parent, lang="English", existing=None):
        """
        Args:
            parent: Parent Gtk.Window.
            lang: Language for UI strings.
            existing: Optional TextAnnotation to edit.
        """
        title = get_text("text_annotation", lang)
        super().__init__(
            title=title,
            transient_for=parent,
            modal=True,
        )
        self.lang = lang
        self.set_default_size(380, 250)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(8)
        content.set_margin_bottom(8)

        # Text entry
        lbl = Gtk.Label(label=get_text("add_text", lang))
        lbl.set_halign(Gtk.Align.START)
        content.pack_start(lbl, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(-1, 100)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll.add(self.text_view)
        content.pack_start(scroll, True, True, 0)

        # Font size
        hbox_fs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox_fs.pack_start(
            Gtk.Label(label=get_text("font_size", lang)), False, False, 0
        )
        self.font_size_spin = Gtk.SpinButton.new_with_range(6, 72, 1)
        self.font_size_spin.set_value(14)
        hbox_fs.pack_start(self.font_size_spin, False, False, 0)
        content.pack_start(hbox_fs, False, False, 0)

        # Color
        hbox_color = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox_color.pack_start(
            Gtk.Label(label=get_text("text_color", lang)), False, False, 0
        )
        self.color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse("#2E3440")
        self.color_button.set_rgba(rgba)
        hbox_color.pack_start(self.color_button, False, False, 0)
        content.pack_start(hbox_color, False, False, 0)

        # Pre-fill if editing
        if existing:
            buf = self.text_view.get_buffer()
            buf.set_text(existing.text)
            self.font_size_spin.set_value(existing.font_size)
            rgba = Gdk.RGBA()
            rgba.parse(existing.color)
            self.color_button.set_rgba(rgba)

        self.show_all()

    def get_annotation_data(self):
        """
        Return the user-entered data as a dict.

        Keys: text, font_size, color.
        """
        buf = self.text_view.get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)

        font_size = self.font_size_spin.get_value_as_int()

        rgba = self.color_button.get_rgba()
        color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255),
        )

        return {
            "text": text,
            "font_size": font_size,
            "color": color,
        }


class FormFieldManager:
    """
    Manages form field detection and data entry for PDF forms.

    Stores user-entered data keyed by (page_index, field_id).
    """

    def __init__(self, pdf_document):
        """
        Args:
            pdf_document: A PDFDocument instance from renderer.py.
        """
        self.pdf_doc = pdf_document
        # {page_index: {field_id: value}}
        self.form_data = {}
        self.highlight_enabled = False

    def get_fields_for_page(self, page_index):
        """
        Return form fields for a given page.

        Returns:
            List of dicts with keys: id, type, area, current_value.
        """
        mappings = self.pdf_doc.get_form_fields(page_index)
        page = self.pdf_doc.get_page(page_index)
        if page is None:
            return []

        _, page_height = page.get_size()
        fields = []

        for mapping in mappings:
            field = mapping.field
            area = mapping.area
            field_id = field.get_id()
            field_type = field.get_field_type()

            # Transform coordinates to top-left origin
            rect = {
                "x1": area.x1,
                "y1": page_height - area.y2,
                "x2": area.x2,
                "y2": page_height - area.y1,
            }

            # Get current / existing value
            current_value = None
            try:
                if field_type == Poppler.FormFieldType.TEXT:
                    current_value = field.get_text() or ""
                elif field_type == Poppler.FormFieldType.BUTTON:
                    current_value = (
                        field.get_state() if hasattr(field, "get_state") else False
                    )
            except Exception:
                current_value = None

            # Check if user has overridden
            user_value = self.form_data.get(page_index, {}).get(field_id)
            if user_value is not None:
                current_value = user_value

            fields.append(
                {
                    "id": field_id,
                    "type": field_type,
                    "area": rect,
                    "current_value": current_value,
                }
            )

        return fields

    def set_field_value(self, page_index, field_id, value):
        """
        Set a form field value.

        Args:
            page_index: 0-based page.
            field_id: The Poppler field ID.
            value: String for text fields, bool for checkboxes.
        """
        if page_index not in self.form_data:
            self.form_data[page_index] = {}
        self.form_data[page_index][field_id] = value

    def get_field_value(self, page_index, field_id):
        """Return the user-entered value for a field, or None."""
        return self.form_data.get(page_index, {}).get(field_id)

    def get_data_for_page(self, page_index):
        """Return the {field_id: value} dict for a page."""
        return self.form_data.get(page_index, {})

    def get_all_data(self):
        """Return the full form data dict."""
        return dict(self.form_data)

    def clear(self):
        """Clear all user-entered form data."""
        self.form_data.clear()

    def hit_test_field(self, page_index, px, py, scale=1.0):
        """
        Check if (px, py) in scaled coords hits any form field on the page.

        Args:
            page_index: 0-based page.
            px, py: Point in display (scaled) coordinates.
            scale: Current zoom scale.

        Returns:
            The field dict if hit, otherwise None.
        """
        fields = self.get_fields_for_page(page_index)
        for f in fields:
            r = f["area"]
            x1 = r["x1"] * scale
            y1 = r["y1"] * scale
            x2 = r["x2"] * scale
            y2 = r["y2"] * scale
            if x1 <= px <= x2 and y1 <= py <= y2:
                return f
        return None


# Need Poppler for FormFieldType references above
import gi

gi.require_version("Poppler", "0.18")
from gi.repository import Poppler


class FormFieldDialog(Gtk.Dialog):
    """
    Dialog for editing a single form field value (text or checkbox).
    """

    def __init__(self, parent, field_info, lang="English"):
        """
        Args:
            parent: Parent Gtk.Window.
            field_info: Dict from FormFieldManager.get_fields_for_page().
            lang: Language string.
        """
        super().__init__(
            title=get_text("fill_form", lang),
            transient_for=parent,
            modal=True,
        )
        self.field_info = field_info
        self.set_default_size(320, 140)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(8)
        content.set_margin_bottom(8)

        field_type = field_info["type"]

        if field_type == Poppler.FormFieldType.TEXT:
            lbl = Gtk.Label(label=get_text("fill_form", lang))
            lbl.set_halign(Gtk.Align.START)
            content.pack_start(lbl, False, False, 0)

            self.entry = Gtk.Entry()
            if field_info.get("current_value"):
                self.entry.set_text(str(field_info["current_value"]))
            content.pack_start(self.entry, False, False, 0)
            self._widget_type = "text"

        elif field_type == Poppler.FormFieldType.BUTTON:
            self.check = Gtk.CheckButton(label=get_text("form_fields", lang))
            if field_info.get("current_value"):
                self.check.set_active(bool(field_info["current_value"]))
            content.pack_start(self.check, False, False, 0)
            self._widget_type = "button"

        else:
            lbl = Gtk.Label(label="Field type not editable")
            content.pack_start(lbl, False, False, 0)
            self._widget_type = "unknown"

        self.show_all()

    def get_value(self):
        """Return the user-entered value."""
        if self._widget_type == "text":
            return self.entry.get_text()
        elif self._widget_type == "button":
            return self.check.get_active()
        return None
