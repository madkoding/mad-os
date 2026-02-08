"""
madOS Installer - Regional settings (locale/timezone) page
"""

from gi.repository import Gtk

from ..config import (
    TIMEZONES,
    NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_FROST
)
from .base import create_page_header, create_nav_buttons


def create_locale_page(app):
    """Locale page with timezone selector (language already chosen on welcome)"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.CENTER)

    # Page header
    header = create_page_header(app, app.t('regional'), 5)
    content.pack_start(header, False, False, 0)

    # Language info card (read-only, set on welcome page)
    lang_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    lang_card.get_style_context().add_class('content-card')
    lang_card.set_margin_top(10)
    lang_card.set_size_request(380, -1)

    lang_icon_label = Gtk.Label()
    lang_icon_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f'{app.t("locale_label").rstrip(":")}</span>'
    )
    lang_icon_label.set_halign(Gtk.Align.START)
    lang_card.pack_start(lang_icon_label, False, False, 0)

    lang_value = Gtk.Label()
    lang_value.set_markup(
        f'<span size="11000" weight="bold">{app.current_lang}</span>  '
        f'<span size="9000" foreground="{NORD_SNOW_STORM["nord4"]}">({app.install_data["locale"]})</span>'
    )
    lang_value.set_halign(Gtk.Align.START)
    lang_value.set_margin_start(24)
    lang_card.pack_start(lang_value, False, False, 0)

    hint = Gtk.Label()
    hint.set_markup(
        f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord3"]}">← Configured on welcome page</span>'
    )
    hint.set_halign(Gtk.Align.START)
    hint.set_margin_start(24)
    lang_card.pack_start(hint, False, False, 0)

    content.pack_start(lang_card, False, False, 0)

    # Timezone card
    tz_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    tz_card.get_style_context().add_class('content-card')
    tz_card.set_margin_top(8)
    tz_card.set_size_request(380, -1)

    tz_label = Gtk.Label()
    tz_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f'{app.t("timezone").rstrip(":")}</span>'
    )
    tz_label.set_halign(Gtk.Align.START)
    tz_card.pack_start(tz_label, False, False, 0)

    app.timezone_combo = Gtk.ComboBoxText()
    for tz in TIMEZONES:
        app.timezone_combo.append_text(tz)
    app.timezone_combo.set_active(0)
    app.timezone_combo.set_margin_start(24)
    app.timezone_combo.set_margin_end(8)
    tz_card.pack_start(app.timezone_combo, False, False, 0)

    content.pack_start(tz_card, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: _on_locale_next(app)
    )
    nav.set_size_request(380, -1)
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, False, 0)
    app.notebook.append_page(page, Gtk.Label(label="Locale"))


def _on_locale_next(app):
    """Save locale data and advance to summary"""
    app.install_data['timezone'] = app.timezone_combo.get_active_text()
    # Trigger summary update before showing the page
    from .summary import update_summary
    update_summary(app)
    app.notebook.next_page()
