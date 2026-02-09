"""
madOS Installer - AI tools selection page
"""

from gi.repository import Gtk

from ..config import (
    OPTIONAL_AI_TOOLS,
    NORD_FROST, NORD_AURORA, NORD_SNOW_STORM, NORD_POLAR_NIGHT
)
from .base import create_page_header, create_nav_buttons


def create_ai_tools_page(app):
    """AI tools selection page"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.CENTER)

    # Page header
    header = create_page_header(app, app.t('ai_tools_title'), 7)
    content.pack_start(header, False, False, 0)

    # Subtitle
    subtitle = Gtk.Label()
    subtitle.set_markup(
        f'<span size="9000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f'{app.t("select_ai_desc")}</span>'
    )
    subtitle.set_halign(Gtk.Align.CENTER)
    subtitle.set_margin_top(4)
    content.pack_start(subtitle, False, False, 0)

    # AI tools card
    app.ai_checkboxes = {}

    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    card.get_style_context().add_class('content-card')
    card.set_margin_top(10)
    card.set_size_request(460, -1)

    card_title = Gtk.Label()
    card_title.set_markup(
        f'<span size="10000" weight="bold" foreground="{NORD_FROST["nord9"]}">'
        f'{app.t("ai_tools_title")}</span>'
    )
    card_title.set_halign(Gtk.Align.START)
    card.pack_start(card_title, False, False, 0)

    for item in OPTIONAL_AI_TOOLS:
        key = f"ai_{item['key']}"
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_margin_start(8)
        row.set_margin_top(4)

        cb = Gtk.CheckButton()
        if item.get('included'):
            cb.set_active(True)
            cb.set_sensitive(False)

        # Restore previous selection if page is rebuilt (language change)
        prev = app.install_data.get('selected_ai', [])
        if key in prev:
            cb.set_active(True)

        app.ai_checkboxes[key] = cb
        row.pack_start(cb, False, False, 0)

        # Name + description
        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        name_label = Gtk.Label()
        if item.get('included'):
            name_label.set_markup(
                f'<span weight="bold">{item["name"]}</span>  '
                f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord3"]}">'
                f'({app.t("included_base")})</span>'
            )
        else:
            name_label.set_markup(
                f'<span weight="bold">{item["name"]}</span>'
            )
        name_label.set_halign(Gtk.Align.START)
        label_box.pack_start(name_label, False, False, 0)

        desc_label = Gtk.Label()
        desc_label.set_markup(
            f'<span size="8000" foreground="{NORD_SNOW_STORM["nord4"]}">'
            f'{item["desc"]}</span>'
        )
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_margin_start(2)
        label_box.pack_start(desc_label, False, False, 0)

        row.pack_start(label_box, False, False, 0)
        card.pack_start(row, False, False, 0)

    content.pack_start(card, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: _on_ai_tools_next(app)
    )
    nav.set_size_request(460, -1)
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, False, 0)
    app.notebook.append_page(page, Gtk.Label(label="AI Tools"))


def _on_ai_tools_next(app):
    """Save AI tool selections and advance to summary"""
    selected = [k for k, cb in app.ai_checkboxes.items() if cb.get_active()]
    app.install_data['selected_ai'] = selected
    # Trigger summary update before showing the page
    from .summary import update_summary
    update_summary(app)
    app.notebook.next_page()
