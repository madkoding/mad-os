"""
madOS Installer - WiFi configuration page
Shown only when no wired internet connection is detected.
"""

import subprocess
import threading
import time

from gi.repository import Gtk, GLib

from ..config import (
    DEMO_MODE,
    NORD_POLAR_NIGHT,
    NORD_SNOW_STORM,
    NORD_FROST,
    NORD_AURORA,
)
from .base import create_page_header, create_nav_buttons


def _has_internet():
    """Check if there is a working internet connection"""
    if DEMO_MODE:
        return False  # Show WiFi page in demo mode for testing
    try:
        # 8.8.8.8 is Google's public DNS server - standard for connectivity checks
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "8.8.8.8"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_wifi_interfaces():
    """Get list of wireless interfaces"""
    if DEMO_MODE:
        return ["wlan0"]
    try:
        result = subprocess.run(
            ["iw", "dev"], capture_output=True, text=True, timeout=5
        )
        interfaces = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Interface "):
                interfaces.append(line.split()[1])
        return interfaces
    except Exception:
        return []


SECURITY_TYPES = (
    "open",
    "wep",
    "psk",
    "wpa2-personal",
    "wpa1-personal",
    "wpa2-enterprise",
    "wpa1-enterprise",
    "8021x",
)


def _parse_security_type(part):
    """Parse security type from iwd output."""
    if part not in SECURITY_TYPES:
        return None
    return (
        part.upper()
        .replace("PSK", "WPA2")
        .replace("WPA2-PERSONAL", "WPA2")
        .replace("WPA1-PERSONAL", "WPA1")
    )


def _parse_network_line(line):
    """Parse a single network line from iwd output."""
    parts = line.split()
    if len(parts) < 2:
        return None

    signal = ""
    security = "Open"
    ssid_parts = []

    for part in parts:
        if all(c == "*" for c in part) and len(part) <= 4 and part:
            signal = part
        else:
            parsed_sec = _parse_security_type(part)
            if parsed_sec:
                security = parsed_sec
            else:
                ssid_parts.append(part)

    ssid = " ".join(ssid_parts).strip()
    if not ssid or ssid in ("Network", "name"):
        return None

    return {"ssid": ssid, "signal": signal or "?", "security": security}


def _scan_networks(interface):
    """Scan for available WiFi networks using iwd (iwctl)"""
    if DEMO_MODE:
        return [
            {"ssid": "Home-WiFi-5G", "signal": "****", "security": "WPA2"},
            {"ssid": "Office-Network", "signal": "***", "security": "WPA2"},
            {"ssid": "CafeLibre", "signal": "**", "security": "WPA2"},
            {"ssid": "OpenNet", "signal": "*", "security": "Open"},
        ]

    networks = []
    try:
        subprocess.run(
            ["iwctl", "station", interface, "scan"], capture_output=True, timeout=10
        )
        time.sleep(3)

        result = subprocess.run(
            ["iwctl", "station", interface, "get-networks"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        for line in result.stdout.splitlines():
            line_stripped = line.strip()
            if (
                not line_stripped
                or "---" in line_stripped
                or "Available" in line_stripped
            ):
                continue
            network = _parse_network_line(line_stripped)
            if network:
                networks.append(network)
    except Exception:
        pass

    return networks


def create_wifi_page(app):
    """WiFi configuration page - lets user connect to a wireless network"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)

    # Page header (step 0 - before disk selection)
    header = create_page_header(app, app.t("wifi_setup"), 1)
    content.pack_start(header, False, False, 0)

    # Status banner
    app.wifi_status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    app.wifi_status_box.set_margin_top(8)

    app.wifi_status_label = Gtk.Label()
    app.wifi_status_label.set_halign(Gtk.Align.CENTER)
    app.wifi_status_box.pack_start(app.wifi_status_label, False, False, 0)
    content.pack_start(app.wifi_status_box, False, False, 0)

    # Network list card
    net_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    net_card.get_style_context().add_class("content-card")
    net_card.set_margin_top(8)

    net_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    net_title = Gtk.Label()
    net_title.set_markup(
        f'<span weight="bold" foreground="{NORD_FROST["nord8"]}">{app.t("wifi_networks")}</span>'
    )
    net_title.set_halign(Gtk.Align.START)
    net_title_box.pack_start(net_title, True, True, 0)

    # Scan button
    app.wifi_scan_btn = Gtk.Button(label=app.t("wifi_scan"))
    app.wifi_scan_btn.get_style_context().add_class("nav-back-button")
    app.wifi_scan_btn.connect("clicked", lambda x: _do_scan(app))
    net_title_box.pack_end(app.wifi_scan_btn, False, False, 0)

    net_card.pack_start(net_title_box, False, False, 0)

    # Scrollable network list
    net_scroll = Gtk.ScrolledWindow()
    net_scroll.set_min_content_height(140)
    net_scroll.set_max_content_height(200)

    # ListBox for networks
    app.wifi_listbox = Gtk.ListBox()
    app.wifi_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    app.wifi_listbox.get_style_context().add_class("wifi-listbox")
    app.wifi_listbox.connect(
        "row-selected", lambda lb, row: _on_network_selected(app, row)
    )
    net_scroll.add(app.wifi_listbox)

    net_card.pack_start(net_scroll, True, True, 0)
    content.pack_start(net_card, True, True, 0)

    # Password entry card
    app.wifi_pass_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    app.wifi_pass_box.get_style_context().add_class("content-card")
    app.wifi_pass_box.set_margin_top(8)

    pass_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    pass_label = Gtk.Label()
    pass_label.set_markup(
        f'<span foreground="{NORD_SNOW_STORM["nord4"]}">{app.t("wifi_password")}</span>'
    )
    pass_row.pack_start(pass_label, False, False, 0)

    app.wifi_pass_entry = Gtk.Entry()
    app.wifi_pass_entry.set_visibility(False)
    app.wifi_pass_entry.set_placeholder_text(app.t("wifi_pass_placeholder"))
    app.wifi_pass_entry.set_hexpand(True)
    app.wifi_pass_entry.connect("activate", lambda x: _do_connect(app))
    pass_row.pack_start(app.wifi_pass_entry, True, True, 0)

    # Show/hide password toggle
    show_pass_btn = Gtk.ToggleButton(label="👁")
    show_pass_btn.set_tooltip_text("Show/Hide password")
    show_pass_btn.connect(
        "toggled", lambda b: app.wifi_pass_entry.set_visibility(b.get_active())
    )
    pass_row.pack_start(show_pass_btn, False, False, 0)

    app.wifi_pass_box.pack_start(pass_row, False, False, 0)

    # Connect button
    app.wifi_connect_btn = Gtk.Button(label=app.t("wifi_connect"))
    app.wifi_connect_btn.get_style_context().add_class("success-button")
    app.wifi_connect_btn.connect("clicked", lambda x: _do_connect(app))
    app.wifi_connect_btn.set_halign(Gtk.Align.END)
    app.wifi_connect_btn.set_margin_top(4)
    app.wifi_pass_box.pack_start(app.wifi_connect_btn, False, False, 0)

    app.wifi_pass_box.set_sensitive(False)
    content.pack_start(app.wifi_pass_box, False, False, 0)

    # Connection result
    app.wifi_result_label = Gtk.Label()
    app.wifi_result_label.set_halign(Gtk.Align.CENTER)
    app.wifi_result_label.set_margin_top(6)
    content.pack_start(app.wifi_result_label, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: _on_wifi_next(app),
        next_label=app.t("wifi_skip"),
    )
    content.pack_start(nav, False, False, 0)

    scroll.add(content)
    page.pack_start(scroll, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="WiFi"))

    # Store state
    app.wifi_selected_ssid = None
    app.wifi_selected_security = "Open"
    app.wifi_interface = None
    app.wifi_connected = False

    # Initial scan on page creation
    GLib.idle_add(_init_wifi_page, app)


def _init_wifi_page(app):
    """Initialize WiFi page - detect interface and start scan"""
    interfaces = _get_wifi_interfaces()
    if interfaces:
        app.wifi_interface = interfaces[0]
        app.wifi_status_label.set_markup(
            f'<span foreground="{NORD_FROST["nord8"]}">{app.t("wifi_detecting")} ({app.wifi_interface})</span>'
        )
        _do_scan(app)
    else:
        app.wifi_status_label.set_markup(
            f'<span foreground="{NORD_AURORA["nord13"]}">{app.t("wifi_no_adapter")}</span>'
        )
        app.wifi_scan_btn.set_sensitive(False)
    return False


def _do_scan(app):
    """Scan for networks in background thread"""
    if not app.wifi_interface:
        return

    app.wifi_scan_btn.set_sensitive(False)
    app.wifi_scan_btn.set_label(app.t("wifi_scanning"))

    # Clear current list
    for child in app.wifi_listbox.get_children():
        app.wifi_listbox.remove(child)

    # Add scanning indicator
    scanning_row = Gtk.ListBoxRow()
    scanning_label = Gtk.Label()
    scanning_label.set_markup(
        f'<span foreground="{NORD_SNOW_STORM["nord4"]}">{app.t("wifi_scanning")}...</span>'
    )
    scanning_label.set_margin_top(8)
    scanning_label.set_margin_bottom(8)
    scanning_row.add(scanning_label)
    app.wifi_listbox.add(scanning_row)
    app.wifi_listbox.show_all()

    def _scan_thread():
        networks = _scan_networks(app.wifi_interface)
        GLib.idle_add(_populate_networks, app, networks)

    thread = threading.Thread(target=_scan_thread)
    thread.daemon = True
    thread.start()


def _populate_networks(app, networks):
    """Populate the network list with scan results"""
    # Clear list
    for child in app.wifi_listbox.get_children():
        app.wifi_listbox.remove(child)

    if not networks:
        empty_row = Gtk.ListBoxRow()
        empty_label = Gtk.Label()
        empty_label.set_markup(
            f'<span foreground="{NORD_AURORA["nord13"]}">{app.t("wifi_no_networks")}</span>'
        )
        empty_label.set_margin_top(8)
        empty_label.set_margin_bottom(8)
        empty_row.add(empty_label)
        app.wifi_listbox.add(empty_row)
    else:
        for net in networks:
            row = Gtk.ListBoxRow()
            row.network_data = net  # Attach data to row

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_top(4)
            row_box.set_margin_bottom(4)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            # Signal strength icon
            signal_str = net.get("signal", "")
            signal_bars = len(signal_str) if signal_str != "?" else 0
            if signal_bars >= 4:
                signal_icon = "█▆▄▂"
            elif signal_bars >= 3:
                signal_icon = "█▆▄░"
            elif signal_bars >= 2:
                signal_icon = "█▆░░"
            else:
                signal_icon = "█░░░"

            signal_label = Gtk.Label()
            signal_label.set_markup(
                f'<span font_family="monospace" foreground="{NORD_FROST["nord7"]}">{signal_icon}</span>'
            )
            row_box.pack_start(signal_label, False, False, 0)

            # SSID
            ssid_label = Gtk.Label()
            ssid_label.set_markup(
                f'<span foreground="{NORD_SNOW_STORM["nord6"]}">{GLib.markup_escape_text(net["ssid"])}</span>'
            )
            ssid_label.set_halign(Gtk.Align.START)
            row_box.pack_start(ssid_label, True, True, 0)

            # Security indicator
            sec = net.get("security", "Open")
            if sec.upper() == "OPEN":
                sec_icon = "🔓"
                sec_color = NORD_AURORA["nord13"]
            else:
                sec_icon = "🔒"
                sec_color = NORD_FROST["nord9"]
            sec_label = Gtk.Label()
            sec_label.set_markup(
                f'<span foreground="{sec_color}" size="small">{sec_icon} {GLib.markup_escape_text(sec)}</span>'
            )
            row_box.pack_end(sec_label, False, False, 0)

            row.add(row_box)
            app.wifi_listbox.add(row)

    app.wifi_listbox.show_all()
    app.wifi_scan_btn.set_label(app.t("wifi_scan"))
    app.wifi_scan_btn.set_sensitive(True)
    return False


def _on_network_selected(app, row):
    """Handle network selection"""
    if row is None or not hasattr(row, "network_data"):
        app.wifi_pass_box.set_sensitive(False)
        app.wifi_selected_ssid = None
        return

    net = row.network_data
    app.wifi_selected_ssid = net["ssid"]
    app.wifi_selected_security = net.get("security", "Open")

    # Enable password box for secured networks, auto-connect for open
    if app.wifi_selected_security.upper() == "OPEN":
        app.wifi_pass_box.set_sensitive(False)
        app.wifi_pass_entry.set_text("")
    else:
        app.wifi_pass_box.set_sensitive(True)
        app.wifi_pass_entry.grab_focus()


def _do_connect(app):
    """Connect to the selected network"""
    if not app.wifi_selected_ssid or not app.wifi_interface:
        return

    ssid = app.wifi_selected_ssid
    password = app.wifi_pass_entry.get_text()
    is_open = app.wifi_selected_security.upper() == "OPEN"

    if not is_open and not password:
        app.wifi_result_label.set_markup(
            f'<span foreground="{NORD_AURORA["nord11"]}">{app.t("wifi_enter_password")}</span>'
        )
        return

    app.wifi_connect_btn.set_sensitive(False)
    app.wifi_result_label.set_markup(
        f'<span foreground="{NORD_FROST["nord8"]}">{app.t("wifi_connecting")} {GLib.markup_escape_text(ssid)}...</span>'
    )

    def _connect_thread():
        success = False
        if DEMO_MODE:
            time.sleep(2)
            success = True
        else:
            try:
                if is_open:
                    result = subprocess.run(
                        ["iwctl", "station", app.wifi_interface, "connect", ssid],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                else:
                    result = subprocess.run(
                        [
                            "iwctl",
                            "--passphrase",
                            password,
                            "station",
                            app.wifi_interface,
                            "connect",
                            ssid,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                if result.returncode == 0:
                    # Wait a moment for DHCP
                    time.sleep(3)
                    success = _has_internet()
            except Exception:
                pass

        GLib.idle_add(_on_connect_result, app, success, ssid)

    thread = threading.Thread(target=_connect_thread)
    thread.daemon = True
    thread.start()


def _on_connect_result(app, success, ssid):
    """Handle connection result"""
    app.wifi_connect_btn.set_sensitive(True)
    if success:
        app.wifi_connected = True
        app.wifi_result_label.set_markup(
            f'<span foreground="{NORD_AURORA["nord14"]}" weight="bold">'
            f"✓ {app.t('wifi_connected')} {GLib.markup_escape_text(ssid)}</span>"
        )
        app.wifi_status_label.set_markup(
            f'<span foreground="{NORD_AURORA["nord14"]}" weight="bold">'
            f"✓ {app.t('wifi_connected')} {GLib.markup_escape_text(ssid)}</span>"
        )
    else:
        app.wifi_result_label.set_markup(
            f'<span foreground="{NORD_AURORA["nord11"]}">'
            f"✗ {app.t('wifi_failed')}</span>"
        )
    return False


def _on_wifi_next(app):
    """Advance to next page"""
    app.notebook.next_page()
