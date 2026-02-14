"""
madOS Installer - Disk selection page
"""

import subprocess

from gi.repository import Gtk

from ..config import (
    DEMO_MODE,
    NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_FROST, NORD_AURORA
)
from ..utils import show_error, style_dialog
from .base import create_page_header, create_nav_buttons


def create_disk_page(app):
    """Disk selection page with clickable button cards"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)

    # Page header
    header = create_page_header(app, app.t('select_disk'), 2)
    content.pack_start(header, False, False, 0)

    # Warning banner
    warn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    warn_box.get_style_context().add_class('warning-banner')
    warn_box.set_margin_top(8)
    warn_box.set_margin_bottom(8)

    warn_text = Gtk.Label()
    warn_text.set_markup(
        f'<span weight="bold" foreground="{NORD_AURORA["nord11"]}">'
        f'  {app.t("warning")}</span>'
    )
    warn_text.set_halign(Gtk.Align.CENTER)
    warn_box.pack_start(warn_text, True, True, 0)
    content.pack_start(warn_box, False, False, 0)

    # Disk buttons container
    app.disk_buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    app.disk_buttons_box.set_margin_top(4)
    app.disk_buttons = []
    app.selected_disk_info = None

    _populate_disks(app)

    content.pack_start(app.disk_buttons_box, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: _on_disk_next(app)
    )
    content.pack_start(nav, False, False, 0)

    scroll.add(content)
    page.pack_start(scroll, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Disk"))


def _populate_disks(app):
    """Populate disk list with clickable button cards"""
    for child in app.disk_buttons_box.get_children():
        app.disk_buttons_box.remove(child)
    app.disk_buttons = []
    app.selected_disk_info = None

    def on_disk_click(button, name, size):
        for btn in app.disk_buttons:
            ctx = btn.get_style_context()
            ctx.remove_class('disk-card-selected')
            ctx.add_class('disk-card')
        ctx = button.get_style_context()
        ctx.remove_class('disk-card')
        ctx.add_class('disk-card-selected')
        app.selected_disk_info = {'name': name, 'size': size}

    def get_disk_type(name, model=''):
        name_lower = name.lower()
        model_lower = model.lower()
        if 'nvme' in name_lower:
            return 'NVMe'
        elif 'ssd' in model_lower or 'flash' in model_lower:
            return 'SSD'
        else:
            return 'HDD'

    try:
        if DEMO_MODE:
            disk_list = [
                ('sda', '256G', 'Samsung SSD 860 EVO'),
                ('nvme0n1', '512G', 'WD Black SN750'),
                ('sdb', '1T', 'Seagate BarraCuda HDD')
            ]
        else:
            disk_list = []
            result = subprocess.run(
                ['lsblk', '-d', '-n', '-o', 'NAME,SIZE,TYPE,MODEL'],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if 'disk' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        size = parts[1]
                        model = ' '.join(parts[3:]) if len(parts) > 3 else 'Unknown disk'
                        disk_list.append((name, size, model))

        for name, size, model in disk_list:
            disk_type = get_disk_type(name, model)

            btn = Gtk.Button()
            btn.get_style_context().add_class('disk-card')
            btn.connect('clicked', on_disk_click, name, size)

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)

            # Type badge
            badge = Gtk.Label()
            badge_class = f'disk-type-{disk_type.lower()}'
            if disk_type == 'NVMe':
                badge.set_markup(
                    f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">NVMe</span>'
                )
            elif disk_type == 'SSD':
                badge.set_markup(
                    f'<span size="9000" weight="bold" foreground="{NORD_AURORA["nord14"]}">SSD</span>'
                )
            else:
                badge.set_markup(
                    f'<span size="9000" weight="bold" foreground="{NORD_SNOW_STORM["nord4"]}">HDD</span>'
                )
            badge.get_style_context().add_class(badge_class)
            badge.set_size_request(50, -1)
            hbox.pack_start(badge, False, False, 0)

            # Device info
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            dev_label = Gtk.Label()
            dev_label.set_markup(
                f'<span weight="bold" size="11000" foreground="{NORD_SNOW_STORM["nord6"]}">'
                f'/dev/{name}</span>'
            )
            dev_label.set_halign(Gtk.Align.START)
            info_box.pack_start(dev_label, False, False, 0)

            model_label = Gtk.Label()
            model_label.set_markup(
                f'<span size="9500" foreground="{NORD_SNOW_STORM["nord4"]}">{model}</span>'
            )
            model_label.set_halign(Gtk.Align.START)
            info_box.pack_start(model_label, False, False, 0)
            hbox.pack_start(info_box, True, True, 0)

            # Size
            size_label = Gtk.Label()
            size_label.set_markup(
                f'<span weight="bold" size="14000" foreground="{NORD_FROST["nord8"]}">{size}</span>'
            )
            hbox.pack_start(size_label, False, False, 0)

            btn.add(hbox)
            app.disk_buttons.append(btn)
            app.disk_buttons_box.pack_start(btn, False, False, 0)

    except Exception as e:
        print(f"Error listing disks: {e}")


def _on_disk_next(app):
    """Handle disk selection next"""
    if app.selected_disk_info is None:
        show_error(app, "No Disk Selected", "Please select a disk to continue.")
        return

    name = app.selected_disk_info['name']
    size_str = app.selected_disk_info['size']
    app.install_data['disk'] = f"/dev/{name}"

    # Parse disk size
    try:
        if 'G' in size_str:
            app.install_data['disk_size_gb'] = int(float(size_str.replace('G', '')))
        elif 'T' in size_str:
            app.install_data['disk_size_gb'] = int(float(size_str.replace('T', '')) * 1024)
        else:
            app.install_data['disk_size_gb'] = 120
    except ValueError:
        app.install_data['disk_size_gb'] = 120

    if DEMO_MODE:
        dialog = Gtk.MessageDialog(
            transient_for=app,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="DEMO MODE"
        )
        dialog.format_secondary_text(
            f"Selected disk: {app.install_data['disk']}\n\n"
            "In real mode, all data would be erased.\n"
            "Demo mode: No actual changes will be made."
        )
        style_dialog(dialog)
        dialog.run()
        dialog.destroy()
        app.notebook.next_page()
    else:
        dialog = Gtk.MessageDialog(
            transient_for=app,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="CONFIRM DISK ERASURE"
        )
        dialog.format_secondary_text(
            f"ALL DATA on {app.install_data['disk']} will be PERMANENTLY ERASED!\n\n"
            "Are you absolutely sure you want to continue?"
        )
        style_dialog(dialog)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            app.notebook.next_page()
