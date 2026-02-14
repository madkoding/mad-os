"""madOS WiFi Configuration - Main application window.

Provides a complete GTK3 interface for managing WiFi connections,
including scanning, connecting, advanced settings, and network details.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from .theme import apply_theme
from .translations import get_text, detect_system_language
from .backend import (
    WiFiNetwork, ConnectionDetails,
    check_wifi_available, get_wifi_device,
    async_scan, async_connect, async_disconnect, async_forget,
    async_get_details, get_active_ssid, get_saved_connections,
    set_auto_connect, set_static_ip, set_dhcp, set_dns_override, set_proxy,
)


# Ratio of left panel width to total paned width on initial layout
_PANED_POSITION_RATIO = 0.55


class WiFiApp(Gtk.Window):
    """Main WiFi configuration window."""

    def __init__(self):
        super().__init__(title="madOS WiFi")
        self.set_wmclass("mados-wifi", "mados-wifi")
        self.set_default_size(700, 550)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        self._lang = detect_system_language()
        self._networks = []
        self._selected_network = None
        self._auto_refresh_id = None

        apply_theme()
        self._build_ui()
        self.show_all()

        # Initial scan
        self._on_scan_clicked(None)
        # Start auto-refresh every 10 seconds
        self._auto_refresh_id = GLib.timeout_add_seconds(10, self._auto_refresh)

    def destroy(self):
        """Clean up timers on destroy."""
        if self._auto_refresh_id:
            GLib.source_remove(self._auto_refresh_id)
            self._auto_refresh_id = None
        super().destroy()

    # -- Translation helper ------------------------------------------------

    def t(self, key):
        """Return translated text for the current language."""
        return get_text(key, self._lang)

    # -- UI Construction ---------------------------------------------------

    def _build_ui(self):
        """Build the complete user interface."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        # Header bar
        main_box.pack_start(self._build_header(), False, False, 0)

        # Content area: network list (left) + detail panel (right)
        self._paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._paned_initial = True
        self._paned.connect('size-allocate', self._on_paned_allocate)
        main_box.pack_start(self._paned, True, True, 0)

        self._paned.pack1(self._build_network_panel(), True, False)
        self._paned.pack2(self._build_detail_panel(), True, False)

        # Status bar
        main_box.pack_start(self._build_status_bar(), False, False, 0)

    def _build_header(self):
        """Build the header bar with title and scan button."""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.set_margin_top(8)
        header.set_margin_bottom(8)

        # Title
        self._title_label = Gtk.Label()
        self._title_label.set_markup(
            f'<b>{self.t("wifi_config")}</b>'
        )
        self._title_label.set_halign(Gtk.Align.START)
        header.pack_start(self._title_label, True, True, 0)

        # Scan button
        self._scan_btn = Gtk.Button(label=self.t("scan"))
        self._scan_btn.connect("clicked", self._on_scan_clicked)
        header.pack_end(self._scan_btn, False, False, 8)

        return header

    def _build_network_panel(self):
        """Build the left panel with the list of available networks."""
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Section label
        self._networks_label = Gtk.Label()
        self._networks_label.set_markup(
            f'<b>{self.t("available_networks")}</b>'
        )
        self._networks_label.set_halign(Gtk.Align.START)
        self._networks_label.set_margin_start(12)
        self._networks_label.set_margin_top(8)
        self._networks_label.set_margin_bottom(4)
        panel.pack_start(self._networks_label, False, False, 0)

        # Scrolled list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._network_list = Gtk.ListBox()
        self._network_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._network_list.connect("row-selected", self._on_network_selected)
        scroll.add(self._network_list)
        panel.pack_start(scroll, True, True, 0)

        # Hidden network button
        self._hidden_btn = Gtk.Button(label=self.t("hidden_network"))
        self._hidden_btn.get_style_context().add_class("flat")
        self._hidden_btn.connect("clicked", self._on_hidden_network)
        self._hidden_btn.set_margin_start(8)
        self._hidden_btn.set_margin_end(8)
        self._hidden_btn.set_margin_top(4)
        self._hidden_btn.set_margin_bottom(4)
        panel.pack_start(self._hidden_btn, False, False, 0)

        # Spinner for scanning
        self._scan_spinner = Gtk.Spinner()
        self._scan_spinner.set_margin_top(4)
        self._scan_spinner.set_margin_bottom(4)
        panel.pack_start(self._scan_spinner, False, False, 0)

        return panel

    def _build_detail_panel(self):
        """Build the right panel with connection details and actions."""
        self._detail_stack = Gtk.Stack()
        self._detail_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # Empty state
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty.set_valign(Gtk.Align.CENTER)
        empty.set_halign(Gtk.Align.CENTER)
        icon = Gtk.Label(label="\U0001F4F6")
        icon.set_markup('<span size="xx-large">\U0001F4F6</span>')
        empty.pack_start(icon, False, False, 0)
        self._empty_label = Gtk.Label(label=self.t("no_networks"))
        empty.pack_start(self._empty_label, False, False, 0)
        self._detail_stack.add_named(empty, "empty")

        # Detail view
        self._detail_scroll = Gtk.ScrolledWindow()
        self._detail_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._detail_box.set_margin_start(12)
        self._detail_box.set_margin_end(12)
        self._detail_box.set_margin_top(8)
        self._detail_box.set_margin_bottom(8)
        self._detail_scroll.add(self._detail_box)
        self._detail_stack.add_named(self._detail_scroll, "details")

        self._detail_stack.set_visible_child_name("empty")
        return self._detail_stack

    def _build_status_bar(self):
        """Build the bottom status bar."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.get_style_context().add_class("statusbar")

        self._status_icon = Gtk.Label()
        bar.pack_start(self._status_icon, False, False, 0)

        self._status_label = Gtk.Label(label=self.t("disconnected"))
        self._status_label.set_halign(Gtk.Align.START)
        bar.pack_start(self._status_label, True, True, 0)

        self._ip_label = Gtk.Label()
        self._ip_label.get_style_context().add_class("ip-label")
        bar.pack_end(self._ip_label, False, False, 0)

        return bar

    def _on_paned_allocate(self, widget, allocation):
        """Set initial paned position proportionally on first allocation."""
        if self._paned_initial and allocation.width > 1:
            self._paned.set_position(int(allocation.width * _PANED_POSITION_RATIO))
            self._paned_initial = False

    # -- Network List Rows -------------------------------------------------

    def _populate_network_list(self, networks):
        """Populate the ListBox with WiFi network rows."""
        self._networks = networks

        # Clear existing rows
        for child in self._network_list.get_children():
            self._network_list.remove(child)

        if not networks:
            label = Gtk.Label(label=self.t("no_networks"))
            label.set_margin_top(20)
            row = Gtk.ListBoxRow()
            row.add(label)
            row.network = None
            self._network_list.add(row)
            self._network_list.show_all()
            return

        for net in networks:
            row = self._create_network_row(net)
            self._network_list.add(row)

        self._network_list.show_all()

    def _create_network_row(self, network):
        """Create a ListBox row for a single WiFi network."""
        row = Gtk.ListBoxRow()
        row.network = network
        row.get_style_context().add_class("network-row")
        if network.in_use:
            row.get_style_context().add_class("network-row-connected")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        # Signal strength indicator
        signal_label = Gtk.Label(label=network.signal_bars)
        category = network.signal_category
        signal_label.get_style_context().add_class(f"signal-{category}")
        hbox.pack_start(signal_label, False, False, 4)

        # SSID and details
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ssid_label = Gtk.Label(label=network.ssid)
        ssid_label.set_halign(Gtk.Align.START)
        ssid_label.get_style_context().add_class("ssid-label")
        ssid_label.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.pack_start(ssid_label, False, False, 0)

        sec_label = Gtk.Label(label=network.security)
        sec_label.set_halign(Gtk.Align.START)
        sec_label.get_style_context().add_class("security-label")
        vbox.pack_start(sec_label, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)

        # Connected indicator
        if network.in_use:
            connected_label = Gtk.Label(label=self.t("connected"))
            connected_label.get_style_context().add_class("connected-label")
            hbox.pack_end(connected_label, False, False, 4)

        # Signal percentage
        pct_label = Gtk.Label(label=f"{network.signal}%")
        pct_label.get_style_context().add_class("caption")
        hbox.pack_end(pct_label, False, False, 4)

        row.add(hbox)
        return row

    # -- Detail Panel Content ----------------------------------------------

    def _show_network_details(self, network):
        """Display details and action buttons for the selected network."""
        # Clear previous content
        for child in self._detail_box.get_children():
            self._detail_box.remove(child)

        # Network name header
        name_label = Gtk.Label()
        name_label.set_markup(f'<b><big>{GLib.markup_escape_text(network.ssid)}</big></b>')
        name_label.set_halign(Gtk.Align.START)
        self._detail_box.pack_start(name_label, False, False, 0)

        sep = Gtk.Separator()
        self._detail_box.pack_start(sep, False, False, 4)

        # Basic info grid
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(6)
        row_idx = 0

        info_items = [
            (self.t("signal"), f"{network.signal}% ({network.signal_bars})"),
            (self.t("security"), network.security),
            (self.t("frequency"), network.frequency),
            (self.t("channel"), network.channel),
            (self.t("speed"), network.rate),
        ]

        for key, val in info_items:
            if val:
                k_lbl = Gtk.Label(label=key)
                k_lbl.set_halign(Gtk.Align.START)
                k_lbl.get_style_context().add_class("detail-key")
                v_lbl = Gtk.Label(label=val)
                v_lbl.set_halign(Gtk.Align.START)
                v_lbl.get_style_context().add_class("detail-value")
                v_lbl.set_selectable(True)
                grid.attach(k_lbl, 0, row_idx, 1, 1)
                grid.attach(v_lbl, 1, row_idx, 1, 1)
                row_idx += 1

        self._detail_box.pack_start(grid, False, False, 0)

        sep2 = Gtk.Separator()
        self._detail_box.pack_start(sep2, False, False, 8)

        # Action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        if network.in_use:
            # Disconnect button
            dc_btn = Gtk.Button(label=self.t("disconnect"))
            dc_btn.get_style_context().add_class("destructive-action")
            dc_btn.connect("clicked", self._on_disconnect_clicked)
            btn_box.pack_start(dc_btn, True, True, 0)
        else:
            # Connect button
            conn_btn = Gtk.Button(label=self.t("connect"))
            conn_btn.get_style_context().add_class("suggested-action")
            conn_btn.connect("clicked", self._on_connect_clicked, network)
            btn_box.pack_start(conn_btn, True, True, 0)

        # Forget button (if saved)
        saved = get_saved_connections()
        if network.ssid in saved:
            forget_btn = Gtk.Button(label=self.t("forget"))
            forget_btn.get_style_context().add_class("destructive-action")
            forget_btn.connect("clicked", self._on_forget_clicked, network.ssid)
            btn_box.pack_start(forget_btn, False, False, 0)

        self._detail_box.pack_start(btn_box, False, False, 0)

        # Connection spinner
        self._connect_spinner = Gtk.Spinner()
        self._detail_box.pack_start(self._connect_spinner, False, False, 4)

        self._connect_status_label = Gtk.Label()
        self._detail_box.pack_start(self._connect_status_label, False, False, 0)

        # If connected, show detailed connection info
        if network.in_use:
            async_get_details(self._on_details_received)

        # Advanced section (expander)
        if network.in_use or network.ssid in saved:
            self._build_advanced_section(network.ssid)

        self._detail_stack.set_visible_child_name("details")
        self._detail_box.show_all()

    def _on_details_received(self, details):
        """Callback when connection details are fetched."""
        if not details:
            return

        sep = Gtk.Separator()
        self._detail_box.pack_start(sep, False, False, 4)

        header = Gtk.Label()
        header.set_markup(f'<b>{self.t("connection_info")}</b>')
        header.set_halign(Gtk.Align.START)
        self._detail_box.pack_start(header, False, False, 4)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(4)
        row_idx = 0

        detail_items = [
            (self.t("ip_address"), details.ip4_address),
            (self.t("gateway"), details.ip4_gateway),
            (self.t("subnet"), details.ip4_subnet),
            (self.t("dns"), details.ip4_dns),
            (self.t("mac_address"), details.mac_address),
            (self.t("ipv6"), details.ip6_address),
            (self.t("link_speed"), details.link_speed),
        ]

        for key, val in detail_items:
            if val:
                k_lbl = Gtk.Label(label=key)
                k_lbl.set_halign(Gtk.Align.START)
                k_lbl.get_style_context().add_class("detail-key")
                v_lbl = Gtk.Label(label=val)
                v_lbl.set_halign(Gtk.Align.START)
                v_lbl.get_style_context().add_class("detail-value")
                v_lbl.set_selectable(True)
                grid.attach(k_lbl, 0, row_idx, 1, 1)
                grid.attach(v_lbl, 1, row_idx, 1, 1)
                row_idx += 1

        self._detail_box.pack_start(grid, False, False, 0)

        # Update status bar
        self._status_icon.set_text("\u2705")
        self._status_label.set_text(f"{self.t('connected')}: {details.ssid}")
        self._status_label.get_style_context().add_class("status-connected")
        self._ip_label.set_text(details.ip4_address or "")

        self._detail_box.show_all()

    def _build_advanced_section(self, connection_name):
        """Build the advanced settings expander."""
        expander = Gtk.Expander(label=self.t("advanced"))
        expander.set_margin_top(8)

        adv_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        adv_box.set_margin_start(8)
        adv_box.set_margin_top(8)

        # Auto-connect toggle
        auto_box = Gtk.Box(spacing=8)
        auto_label = Gtk.Label(label=self.t("auto_connect"))
        auto_box.pack_start(auto_label, False, False, 0)
        auto_switch = Gtk.Switch()
        auto_switch.set_active(True)
        auto_switch.connect("notify::active", self._on_auto_connect_toggled, connection_name)
        auto_box.pack_end(auto_switch, False, False, 0)
        adv_box.pack_start(auto_box, False, False, 0)

        # IP Configuration
        ip_frame = Gtk.Frame(label=self.t("static_ip"))
        ip_grid = Gtk.Grid()
        ip_grid.set_column_spacing(8)
        ip_grid.set_row_spacing(6)
        ip_grid.set_margin_start(8)
        ip_grid.set_margin_end(8)
        ip_grid.set_margin_top(8)
        ip_grid.set_margin_bottom(8)

        # DHCP / Static radio buttons
        dhcp_radio = Gtk.RadioButton.new_with_label(None, self.t("auto_dhcp"))
        static_radio = Gtk.RadioButton.new_with_label_from_widget(dhcp_radio, self.t("static_ip"))
        ip_grid.attach(dhcp_radio, 0, 0, 2, 1)
        ip_grid.attach(static_radio, 0, 1, 2, 1)

        # Static IP entries
        ip_label = Gtk.Label(label=self.t("ip_address"))
        ip_label.set_halign(Gtk.Align.START)
        self._static_ip_entry = Gtk.Entry()
        self._static_ip_entry.set_placeholder_text("192.168.1.100/24")
        self._static_ip_entry.set_sensitive(False)
        ip_grid.attach(ip_label, 0, 2, 1, 1)
        ip_grid.attach(self._static_ip_entry, 1, 2, 1, 1)

        gw_label = Gtk.Label(label=self.t("gateway"))
        gw_label.set_halign(Gtk.Align.START)
        self._static_gw_entry = Gtk.Entry()
        self._static_gw_entry.set_placeholder_text("192.168.1.1")
        self._static_gw_entry.set_sensitive(False)
        ip_grid.attach(gw_label, 0, 3, 1, 1)
        ip_grid.attach(self._static_gw_entry, 1, 3, 1, 1)

        dns_label = Gtk.Label(label=self.t("dns"))
        dns_label.set_halign(Gtk.Align.START)
        self._static_dns_entry = Gtk.Entry()
        self._static_dns_entry.set_placeholder_text("8.8.8.8 8.8.4.4")
        self._static_dns_entry.set_sensitive(False)
        ip_grid.attach(dns_label, 0, 4, 1, 1)
        ip_grid.attach(self._static_dns_entry, 1, 4, 1, 1)

        # Apply button
        apply_btn = Gtk.Button(label=self.t("apply"))
        apply_btn.set_sensitive(False)
        apply_btn.connect("clicked", self._on_apply_static_ip, connection_name)
        ip_grid.attach(apply_btn, 1, 5, 1, 1)

        self._static_apply_btn = apply_btn

        def on_radio_toggled(radio):
            is_static = static_radio.get_active()
            self._static_ip_entry.set_sensitive(is_static)
            self._static_gw_entry.set_sensitive(is_static)
            self._static_dns_entry.set_sensitive(is_static)
            apply_btn.set_sensitive(True)

        static_radio.connect("toggled", on_radio_toggled)
        dhcp_radio.connect("toggled", on_radio_toggled)
        self._dhcp_radio = dhcp_radio
        self._static_radio = static_radio

        ip_frame.add(ip_grid)
        adv_box.pack_start(ip_frame, False, False, 0)

        # Proxy settings
        proxy_frame = Gtk.Frame(label=self.t("proxy"))
        proxy_grid = Gtk.Grid()
        proxy_grid.set_column_spacing(8)
        proxy_grid.set_row_spacing(6)
        proxy_grid.set_margin_start(8)
        proxy_grid.set_margin_end(8)
        proxy_grid.set_margin_top(8)
        proxy_grid.set_margin_bottom(8)

        ph_label = Gtk.Label(label=self.t("proxy_host"))
        ph_label.set_halign(Gtk.Align.START)
        self._proxy_host_entry = Gtk.Entry()
        self._proxy_host_entry.set_placeholder_text("proxy.example.com")
        proxy_grid.attach(ph_label, 0, 0, 1, 1)
        proxy_grid.attach(self._proxy_host_entry, 1, 0, 1, 1)

        pp_label = Gtk.Label(label=self.t("proxy_port"))
        pp_label.set_halign(Gtk.Align.START)
        self._proxy_port_entry = Gtk.Entry()
        self._proxy_port_entry.set_placeholder_text("8080")
        proxy_grid.attach(pp_label, 0, 1, 1, 1)
        proxy_grid.attach(self._proxy_port_entry, 1, 1, 1, 1)

        proxy_apply = Gtk.Button(label=self.t("apply"))
        proxy_apply.connect("clicked", self._on_apply_proxy, connection_name)
        proxy_grid.attach(proxy_apply, 1, 2, 1, 1)

        proxy_frame.add(proxy_grid)
        adv_box.pack_start(proxy_frame, False, False, 0)

        expander.add(adv_box)
        self._detail_box.pack_start(expander, False, False, 0)

    # -- Event Handlers ----------------------------------------------------

    def _on_scan_clicked(self, button):
        """Start a network scan (auto-triggered)."""
        self._scan_spinner.start()
        self._scan_status_label.set_text(self.t("scanning"))
        async_scan(self._on_scan_complete)

    def _on_scan_complete(self, networks):
        """Handle scan results."""
        self._scan_spinner.stop()
        self._scan_status_label.set_text("")
        self._populate_network_list(networks)
        self._update_status_bar()

    def _auto_refresh(self):
        """Auto-refresh network list."""
        async_scan(self._on_scan_complete)
        return True  # Continue the timer

    def _on_network_selected(self, listbox, row):
        """Handle network selection in the list."""
        if row is None or not hasattr(row, 'network') or row.network is None:
            self._detail_stack.set_visible_child_name("empty")
            return
        self._selected_network = row.network
        self._show_network_details(row.network)

    def _on_connect_clicked(self, button, network):
        """Handle connect button click."""
        if network.security and network.security.lower() != 'open':
            self._show_password_dialog(network)
        else:
            self._do_connect(network.ssid, None)

    def _show_password_dialog(self, network):
        """Show password entry dialog for a secured network."""
        dialog = Gtk.Dialog(
            title=self.t("password"),
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.add_button(self.t("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self.t("connect"), Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        prompt = Gtk.Label()
        prompt.set_markup(
            f'{self.t("enter_password")} <b>{GLib.markup_escape_text(network.ssid)}</b>'
        )
        prompt.set_halign(Gtk.Align.START)
        content.pack_start(prompt, False, False, 0)

        pwd_entry = Gtk.Entry()
        pwd_entry.set_visibility(False)
        pwd_entry.set_invisible_char('\u2022')
        pwd_entry.set_placeholder_text(self.t("password"))
        pwd_entry.set_activates_default(True)
        content.pack_start(pwd_entry, False, False, 0)

        show_pwd = Gtk.CheckButton(label=self.t("show_password"))
        show_pwd.connect("toggled", lambda cb: pwd_entry.set_visibility(cb.get_active()))
        content.pack_start(show_pwd, False, False, 0)

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()

        response = dialog.run()
        password = pwd_entry.get_text()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and password:
            self._do_connect(network.ssid, password)

    def _do_connect(self, ssid, password):
        """Execute the connection attempt."""
        self._connect_spinner.start()
        self._connect_status_label.set_text(f'{self.t("connecting")}')
        self._connect_status_label.get_style_context().add_class("status-connecting")
        async_connect(ssid, password, self._on_connect_result)

    def _on_connect_result(self, status):
        """Handle connection result."""
        self._connect_spinner.stop()

        if status == 'connected':
            self._connect_status_label.set_text(self.t("connected"))
            self._connect_status_label.get_style_context().remove_class("status-connecting")
            self._connect_status_label.get_style_context().add_class("status-connected")
            # Refresh network list
            async_scan(self._on_scan_complete)
        elif status == 'wrong_password':
            self._connect_status_label.set_text(self.t("wrong_password"))
            self._connect_status_label.get_style_context().remove_class("status-connecting")
            self._connect_status_label.get_style_context().add_class("status-error")
        else:
            self._connect_status_label.set_text(f'{self.t("failed")}: {status}')
            self._connect_status_label.get_style_context().remove_class("status-connecting")
            self._connect_status_label.get_style_context().add_class("status-error")

        self._update_status_bar()

    def _on_disconnect_clicked(self, button):
        """Handle disconnect button click."""
        button.set_sensitive(False)
        async_disconnect(self._on_disconnect_result)

    def _on_disconnect_result(self, success):
        """Handle disconnect result."""
        async_scan(self._on_scan_complete)
        self._update_status_bar()

    def _on_forget_clicked(self, button, ssid):
        """Handle forget network button click."""
        dialog = Gtk.MessageDialog(
            parent=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f'{self.t("forget")} "{ssid}"?',
        )
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            async_forget(ssid, lambda ok: async_scan(self._on_scan_complete))

    def _on_hidden_network(self, button):
        """Show dialog to connect to a hidden network."""
        dialog = Gtk.Dialog(
            title=self.t("hidden_network"),
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.add_button(self.t("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self.t("connect"), Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        ssid_label = Gtk.Label(label=self.t("enter_ssid"))
        ssid_label.set_halign(Gtk.Align.START)
        content.pack_start(ssid_label, False, False, 0)

        ssid_entry = Gtk.Entry()
        ssid_entry.set_placeholder_text("SSID")
        content.pack_start(ssid_entry, False, False, 0)

        pwd_label = Gtk.Label(label=self.t("password"))
        pwd_label.set_halign(Gtk.Align.START)
        content.pack_start(pwd_label, False, False, 0)

        pwd_entry = Gtk.Entry()
        pwd_entry.set_visibility(False)
        pwd_entry.set_invisible_char('\u2022')
        content.pack_start(pwd_entry, False, False, 0)

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()

        response = dialog.run()
        ssid = ssid_entry.get_text().strip()
        password = pwd_entry.get_text()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and ssid:
            self._connect_spinner.start()
            async_connect(ssid, password or None, self._on_connect_result, hidden=True)

    def _on_auto_connect_toggled(self, switch, gparam, connection_name):
        """Handle auto-connect toggle."""
        set_auto_connect(connection_name, switch.get_active())

    def _on_apply_static_ip(self, button, connection_name):
        """Apply static IP or DHCP settings."""
        if self._dhcp_radio.get_active():
            set_dhcp(connection_name)
        else:
            ip_addr = self._static_ip_entry.get_text().strip()
            gateway = self._static_gw_entry.get_text().strip()
            dns = self._static_dns_entry.get_text().strip()
            if ip_addr and gateway:
                set_static_ip(connection_name, ip_addr, gateway, dns)
        # Refresh details
        if self._selected_network:
            GLib.timeout_add(1000, lambda: self._show_network_details(self._selected_network) or False)

    def _on_apply_proxy(self, button, connection_name):
        """Apply proxy settings."""
        host = self._proxy_host_entry.get_text().strip()
        port = self._proxy_port_entry.get_text().strip()
        set_proxy(connection_name, host, port)

    # -- Status Bar Update -------------------------------------------------

    def _update_status_bar(self):
        """Update the status bar with current connection info."""
        ssid = get_active_ssid()
        if ssid:
            self._status_icon.set_text("\u2705")
            self._status_label.set_text(f"{self.t('connected')}: {ssid}")
            for cls in ["status-disconnected", "status-error"]:
                self._status_label.get_style_context().remove_class(cls)
            self._status_label.get_style_context().add_class("status-connected")
            async_get_details(self._on_status_details)
        else:
            self._status_icon.set_text("\u274C")
            self._status_label.set_text(self.t("disconnected"))
            for cls in ["status-connected", "status-error"]:
                self._status_label.get_style_context().remove_class(cls)
            self._status_label.get_style_context().add_class("status-disconnected")
            self._ip_label.set_text("")

    def _on_status_details(self, details):
        """Update IP label in status bar."""
        if details and details.ip4_address:
            self._ip_label.set_text(details.ip4_address)
