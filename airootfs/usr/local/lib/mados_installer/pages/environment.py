"""
madOS Installer - Development environment selection page
"""

from gi.repository import Gtk

from ..config import (
    OPTIONAL_DEV_LANGUAGES, OPTIONAL_SERVERS,
    OPTIONAL_CONTAINERS, OPTIONAL_EDITORS,
    NORD_FROST, NORD_AURORA, NORD_SNOW_STORM, NORD_POLAR_NIGHT
)
from .base import create_page_header, create_nav_buttons


def _make_category_card(app, title, color, items, checkbox_dict, key_prefix):
    """Create a category card with checkboxes for each item"""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    card.get_style_context().add_class('content-card')
    card.set_margin_top(6)

    # Category title
    cat_label = Gtk.Label()
    cat_label.set_markup(
        f'<span size="10000" weight="bold" foreground="{color}">{title}</span>'
    )
    cat_label.set_halign(Gtk.Align.START)
    card.pack_start(cat_label, False, False, 0)

    for item in items:
        key = f"{key_prefix}_{item['key']}"
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_margin_start(8)
        row.set_margin_top(2)

        cb = Gtk.CheckButton()
        if item.get('included'):
            cb.set_active(True)
            cb.set_sensitive(False)

        # Restore previous selection if page is rebuilt (language change)
        prev = app.install_data.get('selected_env', [])
        if key in prev:
            cb.set_active(True)

        checkbox_dict[key] = cb
        row.pack_start(cb, False, False, 0)

        name_label = Gtk.Label()
        if item.get('included'):
            name_label.set_markup(
                f'<span weight="bold">{item["name"]}</span>  '
                f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord3"]}">'
                f'({app.t("included_base")})</span>'
            )
        else:
            name_label.set_markup(
                f'<span weight="bold">{item["name"]}</span>  '
                f'<span size="8000" foreground="{NORD_SNOW_STORM["nord4"]}">'
                f'{item["desc"]}</span>'
            )
        name_label.set_halign(Gtk.Align.START)
        row.pack_start(name_label, False, False, 0)

        card.pack_start(row, False, False, 0)

    return card


def create_environment_page(app):
    """Development environment selection page"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)

    # Page header
    header = create_page_header(app, app.t('dev_environment'), 6)
    content.pack_start(header, False, False, 0)

    # Subtitle
    subtitle = Gtk.Label()
    subtitle.set_markup(
        f'<span size="9000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f'{app.t("select_dev_desc")}</span>'
    )
    subtitle.set_halign(Gtk.Align.CENTER)
    subtitle.set_margin_top(4)
    content.pack_start(subtitle, False, False, 0)

    # Store checkbox references
    app.env_checkboxes = {}

    # Grid layout: 2 columns
    grid = Gtk.Grid()
    grid.set_column_spacing(12)
    grid.set_row_spacing(6)
    grid.set_margin_top(6)
    grid.set_halign(Gtk.Align.CENTER)

    # Left column: Languages + Containers
    lang_card = _make_category_card(
        app, app.t('dev_languages'), NORD_FROST['nord8'],
        OPTIONAL_DEV_LANGUAGES, app.env_checkboxes, 'lang'
    )
    grid.attach(lang_card, 0, 0, 1, 1)

    cnt_card = _make_category_card(
        app, app.t('dev_containers'), NORD_AURORA['nord12'],
        OPTIONAL_CONTAINERS, app.env_checkboxes, 'cnt'
    )
    grid.attach(cnt_card, 0, 1, 1, 1)

    # Right column: Servers + Editors
    srv_card = _make_category_card(
        app, app.t('dev_servers'), NORD_AURORA['nord13'],
        OPTIONAL_SERVERS, app.env_checkboxes, 'srv'
    )
    grid.attach(srv_card, 1, 0, 1, 1)

    edt_card = _make_category_card(
        app, app.t('dev_editors'), NORD_AURORA['nord15'],
        OPTIONAL_EDITORS, app.env_checkboxes, 'edt'
    )
    grid.attach(edt_card, 1, 1, 1, 1)

    content.pack_start(grid, True, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: _on_environment_next(app)
    )
    content.pack_start(nav, False, False, 0)

    scroll.add(content)
    page.pack_start(scroll, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Environment"))


def _on_environment_next(app):
    """Save environment selections and advance to AI tools page"""
    selected = [k for k, cb in app.env_checkboxes.items() if cb.get_active()]
    app.install_data['selected_env'] = selected
    app.notebook.next_page()
