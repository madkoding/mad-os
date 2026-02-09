"""
madOS PDF Viewer - Main Application Window

Assembles the full GTK3 application: toolbar, PDF canvas with scrolling,
annotation overlays, signature placement, form-field interaction, save/print.
"""

import os
import math
import cairo

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Poppler', '0.18')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Poppler

from .renderer import PDFDocument, PageRenderer
from .annotations import (
    TextAnnotation, SignaturePlacement, SignaturePad,
    SignatureDialog, TextAnnotationDialog,
    FormFieldManager, FormFieldDialog,
)
from .translations import get_text, available_languages, DEFAULT_LANGUAGE
from .theme import apply_theme, hex_to_rgb_float

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_ZOOM = 0.1
MAX_ZOOM = 5.0
ZOOM_STEP = 0.15
PAGE_GAP = 12  # pixels between pages in continuous view


class InteractionMode:
    """Enumeration of mouse interaction modes."""
    NORMAL = 'normal'
    ADD_TEXT = 'add_text'
    PLACE_SIGNATURE = 'place_signature'
    FILL_FORM = 'fill_form'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PDFViewerApp
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PDFViewerApp:
    """
    The main madOS PDF Viewer application.

    Creates the GTK window, toolbar, drawing canvas, and orchestrates all
    interactions between the rendering engine, annotations, and user input.
    """

    def __init__(self, filepath=None):
        """
        Initialize the PDF Viewer application.

        Args:
            filepath: Optional path to a PDF file to open on startup.
        """
        # ── State ─────────────────────────────────────────────────────────
        self.lang = DEFAULT_LANGUAGE
        self.pdf_doc = PDFDocument()
        self.renderer = PageRenderer(self.pdf_doc)
        self.form_manager = FormFieldManager(self.pdf_doc)

        self.current_page = 0
        self.zoom = 1.0
        self.fit_mode = None  # None, 'width', or 'page'

        # Annotations per page: {page_index: [TextAnnotation, ...]}
        self.annotations = {}
        # Signatures per page: {page_index: [SignaturePlacement, ...]}
        self.signatures = {}

        # Interaction
        self.mode = InteractionMode.NORMAL
        self._pending_signature_surface = None
        self._dragging_annotation = None
        self._dragging_signature = None
        self._resizing_signature = None
        self._has_unsaved_changes = False

        # Page surface cache: {page_index: cairo.ImageSurface}
        self._page_cache = {}

        # ── Apply theme ───────────────────────────────────────────────────
        apply_theme()

        # ── Build UI ──────────────────────────────────────────────────────
        self._build_window()
        self._build_toolbar()
        self._build_canvas()
        self._build_statusbar()

        self.window.show_all()

        # ── Open file if provided ─────────────────────────────────────────
        if filepath:
            GLib.idle_add(self._open_file, filepath)

    # ══════════════════════════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════════════════════════

    def _build_window(self):
        """Create the main application window."""
        self.window = Gtk.Window(title=get_text('title', self.lang))
        self.window.set_default_size(900, 700)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Set Sway app_id via WM_CLASS
        self.window.set_wmclass("mados-pdf-viewer", "mados-pdf-viewer")
        # Also set the application name for Wayland
        self.window.set_role("mados-pdf-viewer")

        self.window.connect('delete-event', self._on_delete_event)
        self.window.connect('key-press-event', self._on_key_press)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(self.main_box)

    def _build_toolbar(self):
        """Create the toolbar with all buttons and controls."""
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)
        self.main_box.pack_start(toolbar, False, False, 0)

        # ── File operations ───────────────────────────────────────────────
        self._add_tool_button(toolbar, 'document-open', 'open', self._on_open)
        self._add_tool_button(toolbar, 'document-save', 'save', self._on_save)
        self._add_tool_button(toolbar, 'document-save-as', 'save_as', self._on_save_as)
        self._add_tool_button(toolbar, 'document-print', 'print_doc', self._on_print)
        self._add_tool_button(toolbar, 'image-x-generic', 'export_images', self._on_export_images)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        # ── Navigation ────────────────────────────────────────────────────
        self._add_tool_button(toolbar, 'go-first', 'first_page', self._on_first_page)
        self._add_tool_button(toolbar, 'go-previous', 'prev_page', self._on_prev_page)

        # Page indicator
        ti_page = Gtk.ToolItem()
        page_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        page_box.set_margin_start(4)
        page_box.set_margin_end(4)

        self.page_entry = Gtk.Entry()
        self.page_entry.set_width_chars(4)
        self.page_entry.set_alignment(0.5)
        self.page_entry.set_text("0")
        self.page_entry.connect('activate', self._on_page_entry_activate)
        page_box.pack_start(self.page_entry, False, False, 0)

        self.page_label = Gtk.Label()
        self.page_label.get_style_context().add_class('page-indicator')
        page_box.pack_start(self.page_label, False, False, 0)

        ti_page.add(page_box)
        toolbar.insert(ti_page, -1)

        self._add_tool_button(toolbar, 'go-next', 'next_page', self._on_next_page)
        self._add_tool_button(toolbar, 'go-last', 'last_page', self._on_last_page)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        # ── Zoom ──────────────────────────────────────────────────────────
        self._add_tool_button(toolbar, 'zoom-out', 'zoom_out', self._on_zoom_out)
        self._add_tool_button(toolbar, 'zoom-in', 'zoom_in', self._on_zoom_in)
        self._add_tool_button(toolbar, 'zoom-fit-best', 'fit_page', self._on_fit_page)
        self._add_tool_button(toolbar, 'zoom-original', 'actual_size', self._on_actual_size)

        # Zoom label
        ti_zoom = Gtk.ToolItem()
        self.zoom_label = Gtk.Label(label="100%")
        self.zoom_label.get_style_context().add_class('zoom-indicator')
        self.zoom_label.set_margin_start(4)
        self.zoom_label.set_margin_end(4)
        ti_zoom.add(self.zoom_label)
        toolbar.insert(ti_zoom, -1)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        # ── Annotations ───────────────────────────────────────────────────
        self._add_tool_button(toolbar, 'format-text-bold', 'add_text', self._on_add_text_mode)
        self._add_tool_button(toolbar, 'edit-clear', 'clear_annotations', self._on_clear_annotations)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        # ── Signature ─────────────────────────────────────────────────────
        self._add_tool_button(toolbar, 'document-edit', 'draw_signature', self._on_draw_signature)
        self._add_tool_button(toolbar, 'insert-image', 'place_signature', self._on_place_signature_mode)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        # ── Form fields ───────────────────────────────────────────────────
        self.highlight_fields_btn = Gtk.ToggleToolButton()
        self.highlight_fields_btn.set_icon_name('edit-find')
        self.highlight_fields_btn.set_tooltip_text(get_text('highlight_fields', self.lang))
        self.highlight_fields_btn.connect('toggled', self._on_toggle_highlight_fields)
        toolbar.insert(self.highlight_fields_btn, -1)

        self._add_tool_button(toolbar, 'accessories-text-editor', 'fill_form', self._on_fill_form_mode)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        # ── Fit Width button ──────────────────────────────────────────────
        self._add_tool_button(toolbar, 'view-fullscreen', 'fit_width', self._on_fit_width)

        # ── Language selector ─────────────────────────────────────────────
        # Push to right side
        sep_expand = Gtk.SeparatorToolItem()
        sep_expand.set_draw(False)
        sep_expand.set_expand(True)
        toolbar.insert(sep_expand, -1)

        ti_lang = Gtk.ToolItem()
        self.lang_combo = Gtk.ComboBoxText()
        for lang_name in available_languages():
            self.lang_combo.append_text(lang_name)
        self.lang_combo.set_active(0)
        self.lang_combo.connect('changed', self._on_language_changed)
        ti_lang.add(self.lang_combo)
        toolbar.insert(ti_lang, -1)

    def _build_canvas(self):
        """Create the scrollable PDF drawing canvas."""
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.scrolled.set_kinetic_scrolling(True)
        self.main_box.pack_start(self.scrolled, True, True, 0)

        self.canvas = Gtk.DrawingArea()
        self.canvas.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.canvas.connect('draw', self._on_canvas_draw)
        self.canvas.connect('button-press-event', self._on_canvas_button_press)
        self.canvas.connect('button-release-event', self._on_canvas_button_release)
        self.canvas.connect('motion-notify-event', self._on_canvas_motion)
        self.canvas.connect('scroll-event', self._on_canvas_scroll)

        self.scrolled.add(self.canvas)

    def _build_statusbar(self):
        """Create the status bar at the bottom."""
        self.statusbar = Gtk.Label()
        self.statusbar.set_halign(Gtk.Align.START)
        self.statusbar.set_margin_start(8)
        self.statusbar.set_margin_end(8)
        self.statusbar.set_margin_top(2)
        self.statusbar.set_margin_bottom(2)
        self.statusbar.get_style_context().add_class('statusbar')
        self.main_box.pack_start(self.statusbar, False, False, 0)
        self._update_status(get_text('no_file', self.lang))

    def _add_tool_button(self, toolbar, icon_name, tooltip_key, callback):
        """Helper to add a toolbar button with icon and translated tooltip."""
        btn = Gtk.ToolButton()
        btn.set_icon_name(icon_name)
        btn.set_tooltip_text(get_text(tooltip_key, self.lang))
        btn.connect('clicked', callback)
        toolbar.insert(btn, -1)
        return btn

    # ══════════════════════════════════════════════════════════════════════════
    #  File Operations
    # ══════════════════════════════════════════════════════════════════════════

    def _open_file(self, filepath):
        """
        Open a PDF file and display the first page.

        Args:
            filepath: Path to the PDF file.
        """
        try:
            self.pdf_doc.load(filepath)
        except (FileNotFoundError, RuntimeError) as exc:
            self._show_error(str(exc))
            return

        # Reset state
        self.current_page = 0
        self.annotations.clear()
        self.signatures.clear()
        self.form_manager = FormFieldManager(self.pdf_doc)
        self._page_cache.clear()
        self._has_unsaved_changes = False
        self.mode = InteractionMode.NORMAL

        # Update renderer
        self.renderer = PageRenderer(self.pdf_doc)

        # Update UI
        self._update_page_controls()
        self._update_canvas_size()
        self.canvas.queue_draw()

        title = self.pdf_doc.get_title()
        self.window.set_title(f"{title} - {get_text('title', self.lang)}")
        self._update_status(f"{get_text('open_file', self.lang)}: {filepath}")

    def _on_open(self, widget):
        """Handle the Open button click."""
        chooser = Gtk.FileChooserDialog(
            title=get_text('open_file', self.lang),
            parent=self.window,
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button(get_text('open', self.lang), Gtk.ResponseType.OK)

        ff = Gtk.FileFilter()
        ff.set_name("PDF files (*.pdf)")
        ff.add_mime_type("application/pdf")
        ff.add_pattern("*.pdf")
        chooser.add_filter(ff)

        ff_all = Gtk.FileFilter()
        ff_all.set_name("All files")
        ff_all.add_pattern("*")
        chooser.add_filter(ff_all)

        if chooser.run() == Gtk.ResponseType.OK:
            self._open_file(chooser.get_filename())
        chooser.destroy()

    def _on_save(self, widget):
        """Save the annotated PDF (overwrite or Save As if new)."""
        if self.pdf_doc.document is None:
            self._show_error(get_text('no_file', self.lang))
            return

        # If we have the original filepath, save alongside it
        if self.pdf_doc.filepath:
            base, ext = os.path.splitext(self.pdf_doc.filepath)
            output = base + '_annotated' + ext
            self._do_save(output)
        else:
            self._on_save_as(widget)

    def _on_save_as(self, widget):
        """Save As with file chooser."""
        if self.pdf_doc.document is None:
            self._show_error(get_text('no_file', self.lang))
            return

        chooser = Gtk.FileChooserDialog(
            title=get_text('save_file', self.lang),
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE,
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button(get_text('save', self.lang), Gtk.ResponseType.OK)
        chooser.set_do_overwrite_confirmation(True)

        ff = Gtk.FileFilter()
        ff.set_name("PDF files (*.pdf)")
        ff.add_pattern("*.pdf")
        chooser.add_filter(ff)

        if self.pdf_doc.filepath:
            base, ext = os.path.splitext(
                os.path.basename(self.pdf_doc.filepath)
            )
            chooser.set_current_name(base + '_annotated.pdf')

        if chooser.run() == Gtk.ResponseType.OK:
            self._do_save(chooser.get_filename())
        chooser.destroy()

    def _do_save(self, output_path):
        """
        Perform the actual save operation.

        Args:
            output_path: Destination file path.
        """
        try:
            self.renderer.save_annotated_pdf(
                output_path,
                annotations_by_page=self.annotations,
                signatures_by_page=self.signatures,
                form_data_by_page=self.form_manager.get_all_data(),
            )
            self._has_unsaved_changes = False
            self._update_status(
                f"{get_text('success', self.lang)}: {output_path}"
            )
        except Exception as exc:
            self._show_error(f"{get_text('error', self.lang)}: {exc}")

    def _on_print(self, widget):
        """Print the document using Gtk.PrintOperation."""
        if self.pdf_doc.document is None:
            self._show_error(get_text('no_file', self.lang))
            return

        print_op = Gtk.PrintOperation()
        print_op.set_n_pages(self.pdf_doc.n_pages)
        print_op.set_job_name(self.pdf_doc.get_title() or "madOS PDF")
        print_op.set_embed_page_setup(True)

        # Configure page setup based on first page
        page_setup = Gtk.PageSetup()
        w, h = self.pdf_doc.get_page_size(0)
        # PDF points to mm: 1 point = 0.352778 mm
        paper = Gtk.PaperSize.new_custom(
            "pdf-page", "PDF Page",
            w * 0.352778, h * 0.352778, Gtk.Unit.MM,
        )
        page_setup.set_paper_size(paper)
        print_op.set_default_page_setup(page_setup)

        print_op.connect('draw-page', self._on_print_draw_page)

        self._update_status(get_text('printing', self.lang))
        try:
            result = print_op.run(
                Gtk.PrintOperationAction.PRINT_DIALOG, self.window
            )
            if result == Gtk.PrintOperationResult.APPLY:
                self._update_status(get_text('print_complete', self.lang))
        except GLib.Error as exc:
            self._show_error(f"{get_text('error', self.lang)}: {exc.message}")

    def _on_print_draw_page(self, operation, context, page_nr):
        """
        Render a page for printing.

        Args:
            operation: Gtk.PrintOperation.
            context: Gtk.PrintContext.
            page_nr: 0-based page number.
        """
        ctx = context.get_cairo_context()
        page = self.pdf_doc.get_page(page_nr)
        if page is None:
            return

        pw, ph = page.get_size()
        print_w = context.get_width()
        print_h = context.get_height()

        # Scale to fit the print area
        scale_x = print_w / pw
        scale_y = print_h / ph
        scale = min(scale_x, scale_y)

        ctx.scale(scale, scale)
        page.render_for_printing(ctx)

        # Draw annotations
        page_anns = self.annotations.get(page_nr, [])
        for ann in page_anns:
            self.renderer._draw_text_annotation(ctx, ann, 1.0)

        page_sigs = self.signatures.get(page_nr, [])
        for sig in page_sigs:
            self.renderer._draw_signature(ctx, sig, 1.0)

        form_data = self.form_manager.get_data_for_page(page_nr)
        if form_data:
            self.renderer._draw_form_data(ctx, page_nr, 1.0, form_data)

    def _on_export_images(self, widget):
        """Export all pages as PNG images into a chosen directory."""
        if self.pdf_doc.document is None:
            self._show_error(get_text('no_file', self.lang))
            return

        chooser = Gtk.FileChooserDialog(
            title=get_text('export_images', self.lang),
            parent=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button(get_text('export_images', self.lang), Gtk.ResponseType.OK)

        if chooser.run() == Gtk.ResponseType.OK:
            folder = chooser.get_filename()
            base_name = os.path.splitext(
                os.path.basename(self.pdf_doc.filepath or 'page')
            )[0]
            for i in range(self.pdf_doc.n_pages):
                path = os.path.join(folder, f"{base_name}_page_{i + 1:04d}.png")
                self.renderer.export_page_as_image(i, scale=2.0, filepath=path)
            self._update_status(
                f"{get_text('success', self.lang)}: "
                f"{self.pdf_doc.n_pages} images exported to {folder}"
            )
        chooser.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    #  Page Navigation
    # ══════════════════════════════════════════════════════════════════════════

    def _go_to_page(self, index):
        """Navigate to a specific page (0-based)."""
        if self.pdf_doc.document is None:
            return
        index = max(0, min(index, self.pdf_doc.n_pages - 1))
        self.current_page = index
        self._update_page_controls()
        self._scroll_to_page(index)
        self.canvas.queue_draw()

    def _on_prev_page(self, widget):
        self._go_to_page(self.current_page - 1)

    def _on_next_page(self, widget):
        self._go_to_page(self.current_page + 1)

    def _on_first_page(self, widget):
        self._go_to_page(0)

    def _on_last_page(self, widget):
        self._go_to_page(self.pdf_doc.n_pages - 1)

    def _on_page_entry_activate(self, widget):
        """Handle user pressing Enter in the page number entry."""
        try:
            page_num = int(widget.get_text()) - 1  # User sees 1-based
            self._go_to_page(page_num)
        except ValueError:
            self._update_page_controls()

    def _update_page_controls(self):
        """Update the page entry and label to reflect current state."""
        if self.pdf_doc.document is None:
            self.page_entry.set_text("0")
            self.page_label.set_text(f" {get_text('of_pages', self.lang)} 0")
            return

        self.page_entry.set_text(str(self.current_page + 1))
        self.page_label.set_text(
            f" {get_text('of_pages', self.lang)} {self.pdf_doc.n_pages}"
        )

    def _scroll_to_page(self, page_index):
        """Scroll the view so that the given page is visible."""
        if self.pdf_doc.document is None:
            return

        # Calculate the Y offset of the target page
        y_offset = 0
        for i in range(page_index):
            _, ph = self.pdf_doc.get_page_size(i)
            y_offset += int(math.ceil(ph * self.zoom)) + PAGE_GAP

        vadj = self.scrolled.get_vadjustment()
        vadj.set_value(y_offset)

    # ══════════════════════════════════════════════════════════════════════════
    #  Zoom
    # ══════════════════════════════════════════════════════════════════════════

    def _set_zoom(self, new_zoom):
        """Set zoom level and refresh the canvas."""
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
        self.zoom = new_zoom
        self.fit_mode = None
        self._page_cache.clear()
        self._update_canvas_size()
        self._update_zoom_label()
        self.canvas.queue_draw()

    def _on_zoom_in(self, widget):
        self._set_zoom(self.zoom + ZOOM_STEP)

    def _on_zoom_out(self, widget):
        self._set_zoom(self.zoom - ZOOM_STEP)

    def _on_fit_width(self, widget):
        """Fit the page width to the viewport width."""
        if self.pdf_doc.document is None:
            return
        pw, _ = self.pdf_doc.get_page_size(self.current_page)
        if pw <= 0:
            return

        alloc = self.scrolled.get_allocation()
        # Subtract scrollbar width estimate
        view_w = alloc.width - 20
        if view_w <= 0:
            view_w = 800

        self.zoom = view_w / pw
        self.fit_mode = 'width'
        self._page_cache.clear()
        self._update_canvas_size()
        self._update_zoom_label()
        self.canvas.queue_draw()

    def _on_fit_page(self, widget):
        """Fit the entire page into the viewport."""
        if self.pdf_doc.document is None:
            return
        pw, ph = self.pdf_doc.get_page_size(self.current_page)
        if pw <= 0 or ph <= 0:
            return

        alloc = self.scrolled.get_allocation()
        view_w = alloc.width - 20
        view_h = alloc.height - 20
        if view_w <= 0:
            view_w = 800
        if view_h <= 0:
            view_h = 600

        scale_w = view_w / pw
        scale_h = view_h / ph
        self.zoom = min(scale_w, scale_h)
        self.fit_mode = 'page'
        self._page_cache.clear()
        self._update_canvas_size()
        self._update_zoom_label()
        self.canvas.queue_draw()

    def _on_actual_size(self, widget):
        """Reset zoom to 100%."""
        self._set_zoom(1.0)

    def _update_zoom_label(self):
        """Update the zoom percentage display."""
        self.zoom_label.set_text(f"{int(self.zoom * 100)}%")

    # ══════════════════════════════════════════════════════════════════════════
    #  Canvas Drawing (Continuous Scroll)
    # ══════════════════════════════════════════════════════════════════════════

    def _update_canvas_size(self):
        """
        Recalculate the canvas size for continuous page layout.

        All pages are stacked vertically with PAGE_GAP spacing.
        """
        if self.pdf_doc.document is None:
            self.canvas.set_size_request(100, 100)
            return

        total_h = 0
        max_w = 0
        for i in range(self.pdf_doc.n_pages):
            pw, ph = self.pdf_doc.get_page_size(i)
            sw = int(math.ceil(pw * self.zoom))
            sh = int(math.ceil(ph * self.zoom))
            max_w = max(max_w, sw)
            total_h += sh + PAGE_GAP

        self.canvas.set_size_request(max_w, total_h)

    def _get_page_layout(self):
        """
        Compute the vertical layout of all pages.

        Returns:
            List of (page_index, x, y, width, height) tuples in display coords.
        """
        if self.pdf_doc.document is None:
            return []

        layout = []
        # Find the maximum page width for centering
        max_w = 0
        page_dims = []
        for i in range(self.pdf_doc.n_pages):
            pw, ph = self.pdf_doc.get_page_size(i)
            sw = int(math.ceil(pw * self.zoom))
            sh = int(math.ceil(ph * self.zoom))
            page_dims.append((sw, sh))
            max_w = max(max_w, sw)

        y_pos = PAGE_GAP // 2
        for i, (sw, sh) in enumerate(page_dims):
            x_pos = max((max_w - sw) // 2, 0)
            layout.append((i, x_pos, y_pos, sw, sh))
            y_pos += sh + PAGE_GAP

        return layout

    def _on_canvas_draw(self, widget, ctx):
        """
        Draw all visible pages on the canvas.

        Uses a layout system to position pages vertically with centering.
        """
        if self.pdf_doc.document is None:
            # Draw empty state
            alloc = widget.get_allocation()
            r, g, b = hex_to_rgb_float('#2E3440')
            ctx.set_source_rgb(r, g, b)
            ctx.rectangle(0, 0, alloc.width, alloc.height)
            ctx.fill()

            ctx.set_source_rgb(*hex_to_rgb_float('#4C566A'))
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(16)
            text = get_text('no_file', self.lang)
            extents = ctx.text_extents(text)
            ctx.move_to(
                (alloc.width - extents.width) / 2,
                (alloc.height + extents.height) / 2,
            )
            ctx.show_text(text)
            return

        # Background
        alloc = widget.get_allocation()
        r, g, b = hex_to_rgb_float('#434C5E')
        ctx.set_source_rgb(r, g, b)
        ctx.rectangle(0, 0, alloc.width, alloc.height)
        ctx.fill()

        # Determine visible region
        vadj = self.scrolled.get_vadjustment()
        hadj = self.scrolled.get_hadjustment()
        vis_y = vadj.get_value()
        vis_h = vadj.get_page_size()
        vis_x = hadj.get_value()
        vis_w = hadj.get_page_size()

        layout = self._get_page_layout()

        for page_idx, x, y, w, h in layout:
            # Skip pages that are not visible
            if y + h < vis_y - 50 or y > vis_y + vis_h + 50:
                continue

            # Drop shadow
            ctx.set_source_rgba(0, 0, 0, 0.3)
            ctx.rectangle(x + 3, y + 3, w, h)
            ctx.fill()

            # Render page
            surface = self._get_page_surface(page_idx)
            if surface is not None:
                ctx.set_source_surface(surface, x, y)
                ctx.paint()
            else:
                # Fallback: white rectangle
                ctx.set_source_rgb(1, 1, 1)
                ctx.rectangle(x, y, w, h)
                ctx.fill()

            # Draw annotations
            ctx.save()
            ctx.translate(x, y)

            page_anns = self.annotations.get(page_idx, [])
            for ann in page_anns:
                self.renderer._draw_text_annotation(ctx, ann, self.zoom)

            page_sigs = self.signatures.get(page_idx, [])
            for sig in page_sigs:
                self.renderer._draw_signature(ctx, sig, self.zoom)

                # Draw resize handle for signatures
                hx = (sig.x + sig.width) * self.zoom
                hy = (sig.y + sig.height) * self.zoom
                ctx.set_source_rgba(*hex_to_rgb_float('#88C0D0'), 0.8)
                ctx.rectangle(hx - 5, hy - 5, 10, 10)
                ctx.fill()

            # Form field highlights
            if self.form_manager.highlight_enabled:
                self.renderer._draw_form_field_highlights(
                    ctx, page_idx, self.zoom
                )

            # Form data overlays
            form_data = self.form_manager.get_data_for_page(page_idx)
            if form_data:
                self.renderer._draw_form_data(
                    ctx, page_idx, self.zoom, form_data
                )

            ctx.restore()

        # Update current page based on scroll position
        self._update_current_page_from_scroll(layout, vis_y, vis_h)

    def _get_page_surface(self, page_index):
        """
        Get a cached rendered surface for the page, or render and cache it.

        Args:
            page_index: 0-based page number.

        Returns:
            cairo.ImageSurface or None.
        """
        if page_index in self._page_cache:
            return self._page_cache[page_index]

        surface = self.renderer.render_page(page_index, self.zoom)
        if surface is not None:
            self._page_cache[page_index] = surface
        return surface

    def _update_current_page_from_scroll(self, layout, vis_y, vis_h):
        """Determine which page is most visible and update current_page."""
        if not layout:
            return

        mid_y = vis_y + vis_h / 2
        best_page = 0
        best_dist = float('inf')

        for page_idx, x, y, w, h in layout:
            page_mid = y + h / 2
            dist = abs(page_mid - mid_y)
            if dist < best_dist:
                best_dist = dist
                best_page = page_idx

        if best_page != self.current_page:
            self.current_page = best_page
            self._update_page_controls()

    # ══════════════════════════════════════════════════════════════════════════
    #  Canvas Interaction (Mouse events)
    # ══════════════════════════════════════════════════════════════════════════

    def _canvas_coords_to_page(self, cx, cy):
        """
        Convert canvas coordinates to (page_index, local_x, local_y).

        Returns (page_index, lx, ly) or (None, 0, 0) if outside any page.
        """
        layout = self._get_page_layout()
        for page_idx, px, py, pw, ph in layout:
            if px <= cx <= px + pw and py <= cy <= py + ph:
                return (page_idx, cx - px, cy - py)
        return (None, 0, 0)

    def _on_canvas_button_press(self, widget, event):
        """Handle mouse button press on the canvas."""
        if self.pdf_doc.document is None:
            return

        if event.button != 1:
            return

        cx, cy = event.x, event.y
        page_idx, lx, ly = self._canvas_coords_to_page(cx, cy)
        if page_idx is None:
            return

        # ── Mode: Add Text ────────────────────────────────────────────────
        if self.mode == InteractionMode.ADD_TEXT:
            self._place_text_annotation(page_idx, lx, ly)
            return

        # ── Mode: Place Signature ─────────────────────────────────────────
        if self.mode == InteractionMode.PLACE_SIGNATURE:
            self._place_signature(page_idx, lx, ly)
            return

        # ── Mode: Fill Form ───────────────────────────────────────────────
        if self.mode == InteractionMode.FILL_FORM:
            self._handle_form_click(page_idx, lx, ly)
            return

        # ── Normal mode: check for dragging annotations / signatures ──────
        # Check signature resize handles first
        for sig in self.signatures.get(page_idx, []):
            if sig.hit_test_resize_handle(lx, ly, self.zoom):
                sig.start_resize(lx, ly, self.zoom)
                self._resizing_signature = sig
                return

        # Check signature drag
        for sig in self.signatures.get(page_idx, []):
            if sig.hit_test(lx, ly, self.zoom):
                sig.start_drag(lx, ly, self.zoom)
                self._dragging_signature = sig
                return

        # Check annotation drag
        for ann in self.annotations.get(page_idx, []):
            if ann.hit_test(lx, ly, self.zoom):
                ann.start_drag(lx, ly, self.zoom)
                self._dragging_annotation = ann
                return

    def _on_canvas_button_release(self, widget, event):
        """Handle mouse button release."""
        if self._dragging_annotation:
            self._dragging_annotation.end_drag()
            self._dragging_annotation = None
            self._has_unsaved_changes = True
            self.canvas.queue_draw()

        if self._dragging_signature:
            self._dragging_signature.end_drag()
            self._dragging_signature = None
            self._has_unsaved_changes = True
            self.canvas.queue_draw()

        if self._resizing_signature:
            self._resizing_signature.end_resize()
            self._resizing_signature = None
            self._has_unsaved_changes = True
            self.canvas.queue_draw()

    def _on_canvas_motion(self, widget, event):
        """Handle mouse motion for dragging annotations and signatures."""
        if self.pdf_doc.document is None:
            return

        cx, cy = event.x, event.y
        page_idx, lx, ly = self._canvas_coords_to_page(cx, cy)

        if self._dragging_annotation:
            self._dragging_annotation.update_drag(lx, ly, self.zoom)
            self.canvas.queue_draw()
            return

        if self._dragging_signature:
            self._dragging_signature.update_drag(lx, ly, self.zoom)
            self.canvas.queue_draw()
            return

        if self._resizing_signature:
            self._resizing_signature.update_resize(lx, ly, self.zoom)
            self.canvas.queue_draw()
            return

        # Update cursor based on what's under the pointer
        if page_idx is not None and self.mode == InteractionMode.NORMAL:
            # Check for signature resize handles
            for sig in self.signatures.get(page_idx, []):
                if sig.hit_test_resize_handle(lx, ly, self.zoom):
                    cursor = Gdk.Cursor.new_from_name(
                        widget.get_display(), 'se-resize'
                    )
                    widget.get_window().set_cursor(cursor)
                    return
            # Check for draggable items
            for sig in self.signatures.get(page_idx, []):
                if sig.hit_test(lx, ly, self.zoom):
                    cursor = Gdk.Cursor.new_from_name(
                        widget.get_display(), 'grab'
                    )
                    widget.get_window().set_cursor(cursor)
                    return
            for ann in self.annotations.get(page_idx, []):
                if ann.hit_test(lx, ly, self.zoom):
                    cursor = Gdk.Cursor.new_from_name(
                        widget.get_display(), 'grab'
                    )
                    widget.get_window().set_cursor(cursor)
                    return

        # Default cursor
        if widget.get_window():
            if self.mode == InteractionMode.ADD_TEXT:
                cursor = Gdk.Cursor.new_from_name(
                    widget.get_display(), 'text'
                )
            elif self.mode == InteractionMode.PLACE_SIGNATURE:
                cursor = Gdk.Cursor.new_from_name(
                    widget.get_display(), 'crosshair'
                )
            elif self.mode == InteractionMode.FILL_FORM:
                cursor = Gdk.Cursor.new_from_name(
                    widget.get_display(), 'pointer'
                )
            else:
                cursor = None
            widget.get_window().set_cursor(cursor)

    def _on_canvas_scroll(self, widget, event):
        """Handle scroll events for zooming (Ctrl+scroll) and page scrolling."""
        # Ctrl + scroll = zoom
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self._set_zoom(self.zoom + ZOOM_STEP)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self._set_zoom(self.zoom - ZOOM_STEP)
            elif event.direction == Gdk.ScrollDirection.SMOOTH:
                _, dy = event.get_scroll_deltas()
                self._set_zoom(self.zoom - dy * ZOOM_STEP * 0.3)
            return True  # Consume the event

        return False  # Let default scroll handling proceed

    # ══════════════════════════════════════════════════════════════════════════
    #  Text Annotations
    # ══════════════════════════════════════════════════════════════════════════

    def _on_add_text_mode(self, widget):
        """Toggle the Add Text annotation mode."""
        if self.mode == InteractionMode.ADD_TEXT:
            self.mode = InteractionMode.NORMAL
            self._update_status(get_text('annotations', self.lang))
        else:
            self.mode = InteractionMode.ADD_TEXT
            self._update_status(
                f"{get_text('add_text', self.lang)}: "
                "Click on the page to place text."
            )

    def _place_text_annotation(self, page_idx, lx, ly):
        """Open the text annotation dialog and place the result."""
        dialog = TextAnnotationDialog(self.window, self.lang)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            data = dialog.get_annotation_data()
            if data['text'].strip():
                ann = TextAnnotation(
                    page_index=page_idx,
                    x=lx / self.zoom,
                    y=ly / self.zoom,
                    text=data['text'],
                    font_size=data['font_size'],
                    color=data['color'],
                )
                if page_idx not in self.annotations:
                    self.annotations[page_idx] = []
                self.annotations[page_idx].append(ann)
                self._has_unsaved_changes = True
                self.canvas.queue_draw()

        dialog.destroy()
        self.mode = InteractionMode.NORMAL

    def _on_clear_annotations(self, widget):
        """Clear all annotations (text and signatures) from all pages."""
        if not self.annotations and not self.signatures:
            return

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=get_text('clear_annotations', self.lang) + "?",
        )
        if dialog.run() == Gtk.ResponseType.YES:
            self.annotations.clear()
            self.signatures.clear()
            self._has_unsaved_changes = True
            self.canvas.queue_draw()
        dialog.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    #  Signatures
    # ══════════════════════════════════════════════════════════════════════════

    def _on_draw_signature(self, widget):
        """Open the signature drawing dialog."""
        dialog = SignatureDialog(self.window, self.lang)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            surface = dialog.get_signature_surface()
            if surface:
                self._pending_signature_surface = surface
                self._update_status(
                    f"{get_text('place_signature', self.lang)}: "
                    "Click on the page to place the signature."
                )
                self.mode = InteractionMode.PLACE_SIGNATURE

        dialog.destroy()

    def _on_place_signature_mode(self, widget):
        """Enter signature placement mode if a signature is pending."""
        if self._pending_signature_surface is None:
            self._update_status(
                f"{get_text('draw_signature', self.lang)} first."
            )
            return
        self.mode = InteractionMode.PLACE_SIGNATURE
        self._update_status(
            f"{get_text('place_signature', self.lang)}: "
            "Click on the page."
        )

    def _place_signature(self, page_idx, lx, ly):
        """Place the pending signature surface at the clicked location."""
        if self._pending_signature_surface is None:
            self.mode = InteractionMode.NORMAL
            return

        sig = SignaturePlacement(
            page_index=page_idx,
            x=lx / self.zoom,
            y=ly / self.zoom,
            surface=self._pending_signature_surface,
        )

        if page_idx not in self.signatures:
            self.signatures[page_idx] = []
        self.signatures[page_idx].append(sig)
        self._has_unsaved_changes = True
        self.canvas.queue_draw()

        self.mode = InteractionMode.NORMAL
        self._update_status(get_text('success', self.lang))

    # ══════════════════════════════════════════════════════════════════════════
    #  Form Fields
    # ══════════════════════════════════════════════════════════════════════════

    def _on_toggle_highlight_fields(self, widget):
        """Toggle form field highlighting."""
        self.form_manager.highlight_enabled = widget.get_active()
        self.canvas.queue_draw()

    def _on_fill_form_mode(self, widget):
        """Toggle form fill mode."""
        if self.mode == InteractionMode.FILL_FORM:
            self.mode = InteractionMode.NORMAL
            self._update_status(get_text('form_fields', self.lang))
        else:
            self.mode = InteractionMode.FILL_FORM
            self._update_status(
                f"{get_text('fill_form', self.lang)}: "
                "Click on a form field to edit it."
            )

    def _handle_form_click(self, page_idx, lx, ly):
        """Handle clicking on a form field in fill mode."""
        field_info = self.form_manager.hit_test_field(
            page_idx, lx, ly, self.zoom
        )
        if field_info is None:
            return

        dialog = FormFieldDialog(self.window, field_info, self.lang)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            value = dialog.get_value()
            if value is not None:
                self.form_manager.set_field_value(
                    page_idx, field_info['id'], value
                )
                self._has_unsaved_changes = True
                self.canvas.queue_draw()

        dialog.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    #  Language
    # ══════════════════════════════════════════════════════════════════════════

    def _on_language_changed(self, combo):
        """Handle language selection change."""
        text = combo.get_active_text()
        if text and text in available_languages():
            self.lang = text
            self._refresh_ui_strings()

    def _refresh_ui_strings(self):
        """Update all translatable UI text to the current language."""
        if self.pdf_doc.document:
            title = self.pdf_doc.get_title()
            self.window.set_title(f"{title} - {get_text('title', self.lang)}")
        else:
            self.window.set_title(get_text('title', self.lang))
        self._update_page_controls()

    # ══════════════════════════════════════════════════════════════════════════
    #  Keyboard Shortcuts
    # ══════════════════════════════════════════════════════════════════════════

    def _on_key_press(self, widget, event):
        """Handle global keyboard shortcuts."""
        key = event.keyval
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK) != 0

        if ctrl:
            if key == Gdk.KEY_o:
                self._on_open(None)
                return True
            elif key == Gdk.KEY_s:
                if state & Gdk.ModifierType.SHIFT_MASK:
                    self._on_save_as(None)
                else:
                    self._on_save(None)
                return True
            elif key == Gdk.KEY_p:
                self._on_print(None)
                return True
            elif key == Gdk.KEY_plus or key == Gdk.KEY_equal:
                self._on_zoom_in(None)
                return True
            elif key == Gdk.KEY_minus:
                self._on_zoom_out(None)
                return True
            elif key == Gdk.KEY_0:
                self._on_actual_size(None)
                return True
            elif key == Gdk.KEY_1:
                self._on_fit_width(None)
                return True
            elif key == Gdk.KEY_2:
                self._on_fit_page(None)
                return True
        else:
            if key == Gdk.KEY_Page_Up:
                self._on_prev_page(None)
                return True
            elif key == Gdk.KEY_Page_Down:
                self._on_next_page(None)
                return True
            elif key == Gdk.KEY_Home:
                self._on_first_page(None)
                return True
            elif key == Gdk.KEY_End:
                self._on_last_page(None)
                return True
            elif key == Gdk.KEY_Escape:
                self.mode = InteractionMode.NORMAL
                self._update_status("")
                return True

        return False

    # ══════════════════════════════════════════════════════════════════════════
    #  Window Close / Unsaved Changes
    # ══════════════════════════════════════════════════════════════════════════

    def _on_delete_event(self, widget, event):
        """Handle window close, checking for unsaved changes."""
        if self._has_unsaved_changes:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=get_text('unsaved_changes', self.lang),
            )
            dialog.add_button(get_text('save', self.lang), Gtk.ResponseType.YES)
            dialog.add_button("Discard", Gtk.ResponseType.NO)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)

            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                self._on_save(None)
                Gtk.main_quit()
                return False
            elif response == Gtk.ResponseType.NO:
                Gtk.main_quit()
                return False
            else:
                # Cancel close
                return True

        Gtk.main_quit()
        return False

    # ══════════════════════════════════════════════════════════════════════════
    #  Utility
    # ══════════════════════════════════════════════════════════════════════════

    def _update_status(self, text):
        """Update the status bar text."""
        self.statusbar.set_text(text)

    def _show_error(self, message):
        """Show an error message dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=get_text('error', self.lang),
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
