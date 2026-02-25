"""
madOS Installer - Partitioning scheme page
"""

from gi.repository import Gtk, GLib

from ..config import (
    NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_AURORA,
    MIN_DISK_SIZE_GB, EFI_SIZE_MB,
)
from ..utils import show_error
from .base import create_page_header, create_nav_buttons


def create_partitioning_page(app):
    """Partitioning scheme selection (separate /home vs all-in-root)"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)

    # Page header
    header = create_page_header(app, app.t('partitioning'), 3)
    content.pack_start(header, False, False, 0)

    # Disk info
    disk_info = Gtk.Label()
    disk_info.set_markup(
        f'<span size="10000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f'{app.t("disk_info")} <b>{app.install_data["disk"] or "N/A"}</b> '
        f'({app.install_data["disk_size_gb"]} GB)</span>'
    )
    disk_info.set_halign(Gtk.Align.CENTER)
    disk_info.set_margin_top(6)
    disk_info.set_margin_bottom(8)
    content.pack_start(disk_info, False, False, 0)

    # ── Option 1: Separate /home ──
    card1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    card1.get_style_context().add_class('partition-card')
    card1.set_margin_bottom(8)

    app.radio_separate = Gtk.RadioButton.new_with_label_from_widget(None, '')
    radio_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    radio_box1.pack_start(app.radio_separate, False, False, 0)
    title1 = Gtk.Label()
    title1.set_markup(
        f'<span weight="bold" size="11000">{GLib.markup_escape_text(app.t("sep_home_radio"))}</span>'
    )
    radio_box1.pack_start(title1, False, False, 0)
    card1.pack_start(radio_box1, False, False, 0)
    app.radio_separate.set_active(True)

    pros1 = Gtk.Label()
    pros1.set_markup(
        f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {app.t("sep_home_pro1")}</span>\n'
        f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {app.t("sep_home_pro2")}</span>\n'
        f'<span size="9000" foreground="{NORD_AURORA["nord11"]}">  ✗ {app.t("sep_home_con")}</span>'
    )
    pros1.set_halign(Gtk.Align.START)
    pros1.set_margin_start(28)
    card1.pack_start(pros1, False, False, 0)

    # Partition bar
    root_size = '50GB' if app.install_data["disk_size_gb"] < 128 else '60GB'
    efi_label = f'{EFI_SIZE_MB}M'
    bar1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
    bar1.set_margin_start(28)
    bar1.set_margin_end(8)
    bar1.set_margin_top(4)

    efi_bar = Gtk.Label()
    efi_bar.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> EFI {efi_label} </span>')
    efi_bar.get_style_context().add_class('partition-bar-efi')
    bar1.pack_start(efi_bar, False, False, 0)

    root_bar = Gtk.Label()
    root_bar.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> Root {root_size} </span>')
    root_bar.get_style_context().add_class('partition-bar-root')
    bar1.pack_start(root_bar, True, True, 0)

    home_bar = Gtk.Label()
    home_bar.set_markup(
        f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> Home {app.t("rest_label")} </span>'
    )
    home_bar.get_style_context().add_class('partition-bar-home')
    bar1.pack_start(home_bar, True, True, 0)

    card1.pack_start(bar1, False, False, 0)
    content.pack_start(card1, False, False, 0)

    # ── Option 2: All in root ──
    card2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    card2.get_style_context().add_class('partition-card')
    card2.set_margin_bottom(8)

    app.radio_all_root = Gtk.RadioButton.new_with_label_from_widget(app.radio_separate, '')
    radio_box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    radio_box2.pack_start(app.radio_all_root, False, False, 0)
    title2 = Gtk.Label()
    title2.set_markup(
        f'<span weight="bold" size="11000">{GLib.markup_escape_text(app.t("all_root_radio"))}</span>'
    )
    radio_box2.pack_start(title2, False, False, 0)
    card2.pack_start(radio_box2, False, False, 0)

    pros2 = Gtk.Label()
    pros2.set_markup(
        f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {app.t("all_root_pro1")}</span>\n'
        f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {app.t("all_root_pro2")}</span>\n'
        f'<span size="9000" foreground="{NORD_AURORA["nord11"]}">  ✗ {app.t("all_root_con")}</span>'
    )
    pros2.set_halign(Gtk.Align.START)
    pros2.set_margin_start(28)
    card2.pack_start(pros2, False, False, 0)

    bar2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
    bar2.set_margin_start(28)
    bar2.set_margin_end(8)
    bar2.set_margin_top(6)

    efi_bar2 = Gtk.Label()
    efi_bar2.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> EFI {efi_label} </span>')
    efi_bar2.get_style_context().add_class('partition-bar-efi')
    bar2.pack_start(efi_bar2, False, False, 0)

    root_bar2 = Gtk.Label()
    root_bar2.set_markup(
        f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> Root {app.t("all_rest_label")} '
        f'– {app.t("home_dir_label")} </span>'
    )
    root_bar2.get_style_context().add_class('partition-bar-root-only')
    bar2.pack_start(root_bar2, True, True, 0)

    card2.pack_start(bar2, False, False, 0)
    content.pack_start(card2, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: _on_partitioning_next(app)
    )
    content.pack_start(nav, False, False, 0)

    scroll.add(content)
    page.pack_start(scroll, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Partitioning"))


def _on_partitioning_next(app):
    """Save partitioning choice and advance"""
    app.install_data['separate_home'] = app.radio_separate.get_active()

    disk_size = app.install_data['disk_size_gb']

    # Validate minimum disk size for any installation mode
    if disk_size < MIN_DISK_SIZE_GB:
        show_error(
            app,
            "Disk Too Small",
            f"madOS requires at least {MIN_DISK_SIZE_GB} GB "
            f"({EFI_SIZE_MB} MB EFI + system files + space for updates). "
            f"Your disk is {disk_size} GB. "
            f"Please use a larger disk."
        )
        return

    # Validate minimum disk size for separate /home
    if app.install_data['separate_home'] and disk_size < 52:
        show_error(
            app,
            "Disk Too Small",
            f"Separate /home requires at least 52 GB ({EFI_SIZE_MB} MB EFI + 50 GB root + home). "
            f"Your disk is {disk_size} GB. "
            f"Please select 'All in root' or use a larger disk."
        )
        return

    app.notebook.next_page()
