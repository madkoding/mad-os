"""
madOS Installer - Installation summary page
"""

from gi.repository import Gtk

from ..config import (
    NORD_FROST, NORD_AURORA, NORD_SNOW_STORM,
    OPTIONAL_DEV_LANGUAGES, OPTIONAL_SERVERS,
    OPTIONAL_CONTAINERS, OPTIONAL_EDITORS, OPTIONAL_AI_TOOLS
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
    header = create_page_header(app, app.t('summary'), 8)
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
    sw_card.pack_start(sw_info, False, False, 0)
    app.summary_container.pack_start(sw_card, False, False, 0)

    # ── Environment & AI row ──
    env_ai_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    # Environment card
    env_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    env_card.get_style_context().add_class('summary-card-system')

    env_title = Gtk.Label()
    env_title.set_markup(
        f'<span weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f'{app.t("selected_env").rstrip(":")}</span>'
    )
    env_title.set_halign(Gtk.Align.START)
    env_card.pack_start(env_title, False, False, 0)

    env_names = _get_selected_names(app.install_data.get('selected_env', []))
    env_text = ', '.join(env_names) if env_names else app.t('none_selected')
    env_info = Gtk.Label()
    env_info.set_markup(f'<span size="9000">  {env_text}</span>')
    env_info.set_halign(Gtk.Align.START)
    env_info.set_line_wrap(True)
    env_info.set_max_width_chars(40)
    env_card.pack_start(env_info, False, False, 0)
    env_ai_row.pack_start(env_card, True, True, 0)

    # AI tools card
    ai_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    ai_card.get_style_context().add_class('summary-card-account')

    ai_title = Gtk.Label()
    ai_title.set_markup(
        f'<span weight="bold" foreground="{NORD_AURORA["nord15"]}">'
        f'{app.t("selected_ai").rstrip(":")}</span>'
    )
    ai_title.set_halign(Gtk.Align.START)
    ai_card.pack_start(ai_title, False, False, 0)

    ai_names = _get_selected_ai_names(app.install_data.get('selected_ai', []))
    ai_text = ', '.join(ai_names) if ai_names else app.t('none_selected')
    ai_info = Gtk.Label()
    ai_info.set_markup(f'<span size="9000">  {ai_text}</span>')
    ai_info.set_halign(Gtk.Align.START)
    ai_info.set_line_wrap(True)
    ai_info.set_max_width_chars(40)
    ai_card.pack_start(ai_info, False, False, 0)
    env_ai_row.pack_start(ai_card, True, True, 0)

    app.summary_container.pack_start(env_ai_row, False, False, 0)

    app.summary_container.show_all()


def _get_selected_names(selected_keys):
    """Resolve selected env keys to display names"""
    all_items = (
        [('lang', item) for item in OPTIONAL_DEV_LANGUAGES] +
        [('srv', item) for item in OPTIONAL_SERVERS] +
        [('cnt', item) for item in OPTIONAL_CONTAINERS] +
        [('edt', item) for item in OPTIONAL_EDITORS]
    )
    lookup = {f"{prefix}_{item['key']}": item['name'] for prefix, item in all_items}
    return [lookup[k] for k in selected_keys if k in lookup and not _is_included(k, all_items)]


def _get_selected_ai_names(selected_keys):
    """Resolve selected AI tool keys to display names"""
    lookup = {f"ai_{item['key']}": item['name'] for item in OPTIONAL_AI_TOOLS}
    included = {f"ai_{item['key']}" for item in OPTIONAL_AI_TOOLS if item.get('included')}
    return [lookup[k] for k in selected_keys if k in lookup and k not in included]


def _is_included(key, all_items):
    """Check if an item is already included in base"""
    for prefix, item in all_items:
        if f"{prefix}_{item['key']}" == key and item.get('included'):
            return True
    return False
