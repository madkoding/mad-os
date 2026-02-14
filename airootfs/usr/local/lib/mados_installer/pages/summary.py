"""
madOS Installer - Installation summary page
"""

from gi.repository import Gtk

from ..config import (
    NORD_FROST, NORD_AURORA, NORD_SNOW_STORM
)
from .base import create_page_header, create_nav_buttons


def create_summary_page(app):
    """Summary page showing all selected options before install"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)

    # Page header
    header = create_page_header(app, app.t('summary'), 6)
    content.pack_start(header, False, False, 0)

    # Summary container (filled by update_summary)
    app.summary_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    app.summary_container.set_margin_top(10)
    content.pack_start(app.summary_container, True, False, 0)

    # Navigation
    from .installation import on_start_installation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: on_start_installation(app),
        next_label=app.t('start_install_btn'),
        next_class='start-button'
    )
    content.pack_start(nav, False, False, 0)

    scroll.add(content)
    page.pack_start(scroll, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Summary"))


def update_summary(app):
    """Populate summary cards with current install_data"""
    for child in app.summary_container.get_children():
        app.summary_container.remove(child)

    disk = app.install_data['disk'] or 'N/A'

    # Partition naming (NVMe/MMC use 'p' separator)
    if 'nvme' in disk or 'mmcblk' in disk:
        part_prefix = f"{disk}p"
    else:
        part_prefix = disk

    # ── Top row: System + Account ──
    top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    # System card
    sys_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    sys_card.get_style_context().add_class('summary-card-system')

    sys_title = Gtk.Label()
    sys_title.set_markup(
        f'<span weight="bold" foreground="{NORD_FROST["nord8"]}">{app.t("sys_config").rstrip(":")}</span>'
    )
    sys_title.set_halign(Gtk.Align.START)
    sys_card.pack_start(sys_title, False, False, 0)

    sys_info = Gtk.Label()
    sys_info.set_markup(
        f'<span size="9000">'
        f'  {app.t("disk")}  <b>{disk}</b>\n'
        f'  {app.t("timezone")}  <b>{app.install_data["timezone"]}</b>\n'
        f'  Locale:  <b>{app.install_data["locale"]}</b>'
        f'</span>'
    )
    sys_info.set_halign(Gtk.Align.START)
    sys_card.pack_start(sys_info, False, False, 0)
    top_row.pack_start(sys_card, True, True, 0)

    # Account card
    acct_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    acct_card.get_style_context().add_class('summary-card-account')

    acct_title = Gtk.Label()
    acct_title.set_markup(f'<span weight="bold" foreground="{NORD_AURORA["nord15"]}">Account</span>')
    acct_title.set_halign(Gtk.Align.START)
    acct_card.pack_start(acct_title, False, False, 0)

    acct_info = Gtk.Label()
    acct_info.set_markup(
        f'<span size="9000">'
        f'  {app.t("username")}  <b>{app.install_data["username"]}</b>\n'
        f'  {app.t("hostname")}  <b>{app.install_data["hostname"]}</b>\n'
        f'  Password:  <b>{"●" * min(len(app.install_data["password"]), 8)}</b>'
        f'</span>'
    )
    acct_info.set_halign(Gtk.Align.START)
    acct_card.pack_start(acct_info, False, False, 0)
    top_row.pack_start(acct_card, True, True, 0)

    app.summary_container.pack_start(top_row, False, False, 0)

    # ── Partitions card ──
    part_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    part_card.get_style_context().add_class('summary-card-partitions')

    part_title = Gtk.Label()
    part_title.set_markup(
        f'<span weight="bold" foreground="{NORD_AURORA["nord13"]}">{app.t("partitions")}</span>'
    )
    part_title.set_halign(Gtk.Align.START)
    part_card.pack_start(part_title, False, False, 0)

    if app.install_data['separate_home']:
        root_size = '50GB' if app.install_data['disk_size_gb'] < 128 else '60GB'
        part_text = (
            f'  {part_prefix}1   <b>1MB</b>      BIOS boot\n'
            f'  {part_prefix}2   <b>1GB</b>      {app.t("efi_label")}  (FAT32)\n'
            f'  {part_prefix}3   <b>{root_size}</b>   {app.t("root_label")}  (/)  ext4\n'
            f'  {part_prefix}4   <b>{app.t("rest_label")}</b>     {app.t("home_label")}  (/home)  ext4'
        )
    else:
        part_text = (
            f'  {part_prefix}1   <b>1MB</b>        BIOS boot\n'
            f'  {part_prefix}2   <b>1GB</b>        {app.t("efi_label")}  (FAT32)\n'
            f'  {part_prefix}3   <b>{app.t("all_rest_label")}</b>   {app.t("root_label")}  (/)  ext4 '
            f'– {app.t("home_dir_label")}'
        )

    part_info = Gtk.Label()
    part_info.set_markup(f'<span size="9000" font_family="monospace">{part_text}</span>')
    part_info.set_halign(Gtk.Align.START)
    part_info.set_line_wrap(True)
    part_card.pack_start(part_info, False, False, 0)
    app.summary_container.pack_start(part_card, False, False, 0)

    # ── Software card ──
    sw_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    sw_card.get_style_context().add_class('summary-card-software')

    sw_title = Gtk.Label()
    sw_title.set_markup(
        f'<span weight="bold" foreground="{NORD_AURORA["nord14"]}">{app.t("software")}</span>'
    )
    sw_title.set_halign(Gtk.Align.START)
    sw_card.pack_start(sw_title, False, False, 0)

    sw_info = Gtk.Label()
    sw_info.set_markup(f'<span size="9000">{app.t("software_list")}</span>')
    sw_info.set_halign(Gtk.Align.START)
    sw_info.set_line_wrap(True)
    sw_card.pack_start(sw_info, False, False, 0)
    app.summary_container.pack_start(sw_card, False, False, 0)

    app.summary_container.show_all()
