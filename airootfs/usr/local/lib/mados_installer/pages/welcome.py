"""
madOS Installer - Welcome page
"""

from gi.repository import Gtk

from ..config import (
    NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_FROST
)
from ..translations import TRANSLATIONS
from ..utils import load_logo


def create_welcome_page(app):
    """Welcome page with centered design, logo, features and language selector"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('welcome-container')

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.CENTER)

    # ── Logo ──
    logo_image = load_logo(180)
    if logo_image:
        logo_image.set_halign(Gtk.Align.CENTER)
        logo_image.set_margin_bottom(4)
        content.pack_start(logo_image, False, False, 0)
    else:
        fallback = Gtk.Label()
        fallback.set_markup(
            f'<span size="40000" weight="bold" foreground="{NORD_FROST["nord8"]}">madOS</span>'
        )
        fallback.set_margin_bottom(4)
        content.pack_start(fallback, False, False, 0)

    # ── Subtitle ──
    subtitle = Gtk.Label()
    subtitle.set_markup(
        f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{app.t("subtitle")}</span>'
    )
    subtitle.set_halign(Gtk.Align.CENTER)
    subtitle.set_margin_top(2)
    subtitle.set_margin_bottom(10)
    content.pack_start(subtitle, False, False, 0)

    # ── Divider ──
    divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    divider.get_style_context().add_class('welcome-divider')
    divider.set_margin_start(40)
    divider.set_margin_end(40)
    divider.set_margin_bottom(10)
    content.pack_start(divider, False, False, 0)

    # ── Features grid ──
    features_box = Gtk.FlowBox()
    features_box.set_selection_mode(Gtk.SelectionMode.NONE)
    features_box.set_homogeneous(True)
    features_box.set_max_children_per_line(4)
    features_box.set_min_children_per_line(1)
    features_box.set_column_spacing(8)
    features_box.set_row_spacing(8)
    features_box.set_halign(Gtk.Align.CENTER)

    for f1, f2 in app.t('features'):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.get_style_context().add_class('feature-card')

        lbl1 = Gtk.Label()
        lbl1.set_markup(f'<span foreground="{NORD_FROST["nord8"]}" weight="bold">{f1}</span>')
        lbl1.set_halign(Gtk.Align.START)
        card.pack_start(lbl1, False, False, 0)

        lbl2 = Gtk.Label()
        lbl2.set_markup(f'<span size="small" foreground="{NORD_SNOW_STORM["nord4"]}">{f2}</span>')
        lbl2.set_halign(Gtk.Align.START)
        card.pack_start(lbl2, False, False, 0)

        features_box.insert(card, -1)

    content.pack_start(features_box, False, False, 0)

    # ── Language selector ──
    lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    lang_box.set_halign(Gtk.Align.CENTER)
    lang_box.set_margin_top(12)

    lang_label = Gtk.Label()
    lang_label.set_markup(
        f'<span size="small" foreground="{NORD_POLAR_NIGHT["nord3"]}">{app.t("language")}</span>'
    )
    lang_box.pack_start(lang_label, False, False, 0)

    app.lang_combo = Gtk.ComboBoxText()
    langs = list(TRANSLATIONS.keys())
    for lang in langs:
        app.lang_combo.append_text(lang)
    try:
        app.lang_combo.set_active(langs.index(app.current_lang))
    except ValueError:
        app.lang_combo.set_active(0)
    app.lang_combo.connect('changed', app.on_language_changed)
    lang_box.pack_start(app.lang_combo, False, False, 0)

    content.pack_start(lang_box, False, False, 0)

    # ── Buttons ──
    btn_box = Gtk.Box(spacing=12)
    btn_box.set_halign(Gtk.Align.CENTER)
    btn_box.set_margin_top(14)

    start_btn = Gtk.Button(label=app.t('start_install'))
    start_btn.get_style_context().add_class('start-button')
    start_btn.connect('clicked', lambda x: app.notebook.next_page())
    btn_box.pack_start(start_btn, False, False, 0)

    exit_btn = Gtk.Button(label=app.t('exit'))
    exit_btn.get_style_context().add_class('exit-button')
    exit_btn.connect('clicked', lambda x: Gtk.main_quit())
    btn_box.pack_start(exit_btn, False, False, 0)

    content.pack_start(btn_box, False, False, 0)

    # ── Version footer ──
    version = Gtk.Label()
    version.set_markup(
        f'<span size="small" foreground="{NORD_POLAR_NIGHT["nord3"]}">v1.0 • Arch Linux • x86_64</span>'
    )
    version.set_halign(Gtk.Align.CENTER)
    version.set_margin_top(10)
    content.pack_start(version, False, False, 0)

    page.pack_start(content, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Welcome"))
