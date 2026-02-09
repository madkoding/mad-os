"""
madOS PDF Viewer - PDF Rendering Engine

Uses poppler-glib (gi.repository.Poppler) to load and render PDF pages,
and cairo for compositing annotations on top of rendered pages.

Provides:
  - PDFDocument: loads a PDF, exposes pages, metadata, form fields.
  - PageRenderer: renders a single page at a given scale to a cairo surface.
"""

import os
import math
import cairo

import gi
gi.require_version('Poppler', '0.18')
gi.require_version('Gtk', '3.0')
from gi.repository import Poppler, GLib


class PDFDocument:
    """
    Wrapper around a Poppler.Document with convenience accessors.

    Attributes:
        uri:        The file URI of the loaded document.
        filepath:   The filesystem path of the loaded document.
        document:   The underlying Poppler.Document.
        n_pages:    Number of pages in the document.
    """

    def __init__(self):
        self.uri = None
        self.filepath = None
        self.document = None
        self.n_pages = 0

    def load(self, filepath):
        """
        Load a PDF file from disk.

        Args:
            filepath: Absolute or relative path to a PDF file.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If Poppler cannot parse the file.
        """
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"PDF file not found: {filepath}")

        uri = GLib.filename_to_uri(filepath, None)
        try:
            doc = Poppler.Document.new_from_file(uri, None)
        except GLib.Error as exc:
            raise RuntimeError(f"Failed to open PDF: {exc.message}") from exc

        self.uri = uri
        self.filepath = filepath
        self.document = doc
        self.n_pages = doc.get_n_pages()

    def get_page(self, index):
        """
        Return the Poppler.Page at the given 0-based index.

        Args:
            index: Page number (0-based).

        Returns:
            Poppler.Page or None if index is out of range.
        """
        if self.document is None or index < 0 or index >= self.n_pages:
            return None
        return self.document.get_page(index)

    def get_page_size(self, index):
        """
        Return (width, height) in PDF points for the given page.

        Args:
            index: Page number (0-based).

        Returns:
            Tuple (width, height) in points, or (0, 0) if invalid.
        """
        page = self.get_page(index)
        if page is None:
            return (0.0, 0.0)
        return page.get_size()

    def get_form_fields(self, index):
        """
        Return a list of form field mappings for the given page.

        Each mapping has .area (PopplerRectangle) and .field (PopplerFormField).
        The field's type can be queried with field.get_field_type().

        Args:
            index: Page number (0-based).

        Returns:
            List of Poppler.FormFieldMapping objects, or empty list.
        """
        page = self.get_page(index)
        if page is None:
            return []
        mappings = page.get_form_field_mapping()
        return mappings if mappings else []

    def get_title(self):
        """Return the document title or the filename."""
        if self.document is None:
            return ""
        title = self.document.get_property('title')
        if title:
            return title
        if self.filepath:
            return os.path.basename(self.filepath)
        return ""

    def get_metadata(self):
        """
        Return a dict of document metadata.

        Keys: title, author, subject, creator, producer, n_pages, filepath.
        """
        if self.document is None:
            return {}
        return {
            'title': self.document.get_property('title') or '',
            'author': self.document.get_property('author') or '',
            'subject': self.document.get_property('subject') or '',
            'creator': self.document.get_property('creator') or '',
            'producer': self.document.get_property('producer') or '',
            'n_pages': self.n_pages,
            'filepath': self.filepath or '',
        }


class PageRenderer:
    """
    Renders a PDF page to a cairo ImageSurface at a given scale.

    Optionally composites text annotations, signatures, and form-field
    overlays on top of the rendered page.
    """

    def __init__(self, pdf_document):
        """
        Args:
            pdf_document: A PDFDocument instance.
        """
        self.pdf_doc = pdf_document

    def render_page(self, page_index, scale=1.0):
        """
        Render a single page to a cairo ImageSurface.

        Args:
            page_index: 0-based page number.
            scale: Zoom factor (1.0 = 100%).

        Returns:
            A cairo.ImageSurface with the rendered page, or None.
        """
        page = self.pdf_doc.get_page(page_index)
        if page is None:
            return None

        pw, ph = page.get_size()
        surface_w = int(math.ceil(pw * scale))
        surface_h = int(math.ceil(ph * scale))

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, surface_w, surface_h)
        ctx = cairo.Context(surface)

        # White background
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.rectangle(0, 0, surface_w, surface_h)
        ctx.fill()

        # Scale and render
        ctx.scale(scale, scale)
        page.render(ctx)

        return surface

    def render_page_with_annotations(self, page_index, scale, annotations,
                                     signatures, form_data, highlight_fields):
        """
        Render a page with all overlays composited on top.

        Args:
            page_index: 0-based page number.
            scale: Zoom factor.
            annotations: List of TextAnnotation objects for this page.
            signatures: List of SignaturePlacement objects for this page.
            form_data: Dict mapping field_id -> value for form fields.
            highlight_fields: Whether to draw form-field highlight overlays.

        Returns:
            A cairo.ImageSurface with everything composited.
        """
        surface = self.render_page(page_index, scale)
        if surface is None:
            return None

        ctx = cairo.Context(surface)

        # Draw text annotations
        for ann in annotations:
            self._draw_text_annotation(ctx, ann, scale)

        # Draw signature placements
        for sig in signatures:
            self._draw_signature(ctx, sig, scale)

        # Draw form field overlays
        if highlight_fields:
            self._draw_form_field_highlights(ctx, page_index, scale)

        # Draw form field data
        if form_data:
            self._draw_form_data(ctx, page_index, scale, form_data)

        return surface

    def _draw_text_annotation(self, ctx, annotation, scale):
        """
        Draw a single text annotation on the cairo context.

        Args:
            ctx: cairo.Context.
            annotation: A TextAnnotation object.
            scale: Current zoom scale.
        """
        ctx.save()

        x = annotation.x * scale
        y = annotation.y * scale
        font_size = annotation.font_size * scale

        # Parse color
        r, g, b = _hex_to_rgb(annotation.color)

        ctx.set_source_rgba(r, g, b, annotation.opacity)
        ctx.select_font_face(
            "Sans",
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_NORMAL,
        )
        ctx.set_font_size(font_size)

        # Draw each line of text
        lines = annotation.text.split('\n')
        for i, line in enumerate(lines):
            ctx.move_to(x, y + font_size + i * font_size * 1.3)
            ctx.show_text(line)

        ctx.restore()

    def _draw_signature(self, ctx, sig_placement, scale):
        """
        Draw a signature image (from stored strokes) on the context.

        Args:
            ctx: cairo.Context.
            sig_placement: A SignaturePlacement object.
            scale: Current zoom scale.
        """
        if not sig_placement.surface:
            return

        ctx.save()

        x = sig_placement.x * scale
        y = sig_placement.y * scale
        w = sig_placement.width * scale
        h = sig_placement.height * scale

        # Scale the signature surface to fit the placement rectangle
        sig_w = sig_placement.surface.get_width()
        sig_h = sig_placement.surface.get_height()
        if sig_w <= 0 or sig_h <= 0:
            ctx.restore()
            return

        sx = w / sig_w
        sy = h / sig_h

        ctx.translate(x, y)
        ctx.scale(sx, sy)
        ctx.set_source_surface(sig_placement.surface, 0, 0)
        ctx.paint_with_alpha(sig_placement.opacity)

        ctx.restore()

    def _draw_form_field_highlights(self, ctx, page_index, scale):
        """
        Draw subtle highlight rectangles over detected form fields.

        Args:
            ctx: cairo.Context.
            page_index: 0-based page index.
            scale: Current zoom scale.
        """
        mappings = self.pdf_doc.get_form_fields(page_index)
        page = self.pdf_doc.get_page(page_index)
        if page is None:
            return
        _, page_height = page.get_size()

        for mapping in mappings:
            area = mapping.area
            field = mapping.field

            # Poppler coordinates: origin at bottom-left; cairo: top-left.
            x1 = area.x1 * scale
            y1 = (page_height - area.y2) * scale
            x2 = area.x2 * scale
            y2 = (page_height - area.y1) * scale

            w = x2 - x1
            h = y2 - y1

            field_type = field.get_field_type()

            # Color by type
            if field_type == Poppler.FormFieldType.TEXT:
                ctx.set_source_rgba(0.37, 0.51, 0.67, 0.2)  # nord10-ish
            elif field_type == Poppler.FormFieldType.BUTTON:
                ctx.set_source_rgba(0.64, 0.75, 0.55, 0.2)  # nord14-ish
            elif field_type == Poppler.FormFieldType.CHOICE:
                ctx.set_source_rgba(0.71, 0.56, 0.68, 0.2)  # nord15-ish
            else:
                ctx.set_source_rgba(0.56, 0.74, 0.73, 0.2)  # nord7-ish

            ctx.rectangle(x1, y1, w, h)
            ctx.fill()

            # Border
            ctx.set_source_rgba(0.53, 0.75, 0.82, 0.5)  # nord8-ish
            ctx.set_line_width(1.0)
            ctx.rectangle(x1, y1, w, h)
            ctx.stroke()

    def _draw_form_data(self, ctx, page_index, scale, form_data):
        """
        Render user-filled form data over the form fields.

        Args:
            ctx: cairo.Context.
            page_index: 0-based page index.
            scale: Current zoom scale.
            form_data: Dict of {field_id: value}.
        """
        mappings = self.pdf_doc.get_form_fields(page_index)
        page = self.pdf_doc.get_page(page_index)
        if page is None:
            return
        _, page_height = page.get_size()

        for mapping in mappings:
            area = mapping.area
            field = mapping.field
            field_id = field.get_id()

            if field_id not in form_data:
                continue

            value = form_data[field_id]
            field_type = field.get_field_type()

            x1 = area.x1 * scale
            y1 = (page_height - area.y2) * scale
            x2 = area.x2 * scale
            y2 = (page_height - area.y1) * scale
            w = x2 - x1
            h = y2 - y1

            ctx.save()

            if field_type == Poppler.FormFieldType.TEXT and isinstance(value, str):
                # Render text inside the field rectangle
                font_size = min(h * 0.7, 12.0 * scale)
                ctx.set_source_rgb(0.18, 0.20, 0.25)  # nord0-ish
                ctx.select_font_face(
                    "Sans",
                    cairo.FONT_SLANT_NORMAL,
                    cairo.FONT_WEIGHT_NORMAL,
                )
                ctx.set_font_size(font_size)
                ctx.move_to(x1 + 2 * scale, y1 + h * 0.75)
                ctx.show_text(value)

            elif field_type == Poppler.FormFieldType.BUTTON and isinstance(value, bool):
                # Draw checkmark if checked
                if value:
                    ctx.set_source_rgb(0.37, 0.51, 0.67)  # nord10
                    ctx.set_line_width(2.0 * scale)
                    # Simple checkmark
                    cx = x1 + w * 0.25
                    cy = y1 + h * 0.55
                    ctx.move_to(cx, cy)
                    ctx.line_to(x1 + w * 0.45, y1 + h * 0.75)
                    ctx.line_to(x1 + w * 0.75, y1 + h * 0.25)
                    ctx.stroke()

            ctx.restore()

    def export_page_as_image(self, page_index, scale=2.0, filepath=None):
        """
        Export a single page as a PNG image.

        Args:
            page_index: 0-based page number.
            scale: Resolution multiplier (2.0 = 144 DPI).
            filepath: Output file path. If None, returns the surface.

        Returns:
            The filepath written, or the cairo.ImageSurface if filepath is None.
        """
        surface = self.render_page(page_index, scale)
        if surface is None:
            return None

        if filepath:
            surface.write_to_png(filepath)
            return filepath
        return surface

    def save_annotated_pdf(self, output_path, annotations_by_page,
                           signatures_by_page, form_data_by_page,
                           progress_callback=None):
        """
        Save the document as a new PDF with all annotations baked in.

        Uses cairo.PDFSurface to re-render each page with overlays.

        Args:
            output_path: Destination file path.
            annotations_by_page: Dict {page_index: [TextAnnotation, ...]}.
            signatures_by_page: Dict {page_index: [SignaturePlacement, ...]}.
            form_data_by_page: Dict {page_index: {field_id: value}}.
            progress_callback: Optional callable(page_index, total) for progress.
        """
        if self.pdf_doc.document is None:
            raise RuntimeError("No document loaded.")

        # Determine the page size from the first page (use per-page sizes below)
        first_w, first_h = self.pdf_doc.get_page_size(0)

        pdf_surface = cairo.PDFSurface(output_path, first_w, first_h)

        for i in range(self.pdf_doc.n_pages):
            pw, ph = self.pdf_doc.get_page_size(i)
            pdf_surface.set_size(pw, ph)

            ctx = cairo.Context(pdf_surface)

            # Render original page at scale 1.0
            page = self.pdf_doc.get_page(i)
            if page:
                page.render_for_printing(ctx)

            # Overlay text annotations
            page_anns = annotations_by_page.get(i, [])
            for ann in page_anns:
                self._draw_text_annotation(ctx, ann, 1.0)

            # Overlay signatures
            page_sigs = signatures_by_page.get(i, [])
            for sig in page_sigs:
                self._draw_signature(ctx, sig, 1.0)

            # Overlay form data
            page_form = form_data_by_page.get(i, {})
            if page_form:
                self._draw_form_data(ctx, i, 1.0, page_form)

            ctx.show_page()

            if progress_callback:
                progress_callback(i, self.pdf_doc.n_pages)

        pdf_surface.finish()


def _hex_to_rgb(hex_color):
    """
    Convert a hex color string to (r, g, b) floats in [0..1].

    Args:
        hex_color: e.g. '#BF616A' or 'BF616A'.

    Returns:
        Tuple of (r, g, b) floats.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (0.0, 0.0, 0.0)
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)
