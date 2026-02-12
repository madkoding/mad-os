"""madOS Bluetooth Configuration - Main application window.

Provides a GTK3 interface for managing Bluetooth connections,
including scanning, pairing, connecting, and device details.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from .theme import apply_theme
from .translations import get_text, detect_system_language
from .backend import (
    BluetoothDevice,
    check_bluetooth_available, is_adapter_powered, set_adapter_power,
    async_scan, async_pair, async_connect, async_disconnect, async_remove,
    async_set_power, async_get_adapter_state,
    trust_device, get_devices,
)


# Device icon mapping from bluetoothctl icon names to Unicode
_DEVICE_ICONS = {
    'audio-card': '\U0001F3B5',        # Musical note
    'audio-headphones': '\U0001F3A7',  # Headphones
    'audio-headset': '\U0001F3A7',     # Headphones
    'input-keyboard': '\u2328',        # Keyboard
    'input-mouse': '\U0001F5B1',       # Mouse
    'input-gaming': '\U0001F3AE',      # Game controller
    'phone': '\U0001F4F1',             # Phone
    'computer': '\U0001F4BB',          # Laptop
    'camera-photo': '\U0001F4F7',      # Camera
    'printer': '\U0001F5A8',           # Printer
}

_DEFAULT_ICON = '\U0001F4E1'  # Satellite antenna


def _icon_for_device(device: BluetoothDevice) -> str:
    """Return a Unicode icon for the device type."""
    return _DEVICE_ICONS.get(device.icon, _DEFAULT_ICON)


class BluetoothApp(Gtk.Window):
    """Main Bluetooth configuration window."""

    def __init__(self):
        super().__init__(title="madOS Bluetooth")
        self.set_wmclass("mados-bluetooth", "mados-bluetooth")
        self.set_default_size(700, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        self._lang = detect_system_language()
        self._devices = []
        self._selected_device = None
        self._auto_refresh_id = None
        self._refresh_in_flight = False
        self._adapter_available = False
        self._adapter_powered = False

        apply_theme()
        self._build_ui()
        self.show_all()

        # Initial refresh
        self._on_scan_clicked(None)
        # Auto-refresh every 15 seconds
        self._auto_refresh_id = GLib.timeout_add_seconds(15, self._auto_refresh)

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

        # Content area: device list (left) + detail panel (right)
        self._paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._paned.set_position(350)
        main_box.pack_start(self._paned, True, True, 0)

        self._paned.pack1(self._build_device_panel(), True, False)
        self._paned.pack2(self._build_detail_panel(), True, False)

        # Status bar
        main_box.pack_start(self._build_status_bar(), False, False, 0)

    def _build_header(self):
        """Build the header bar with title, power switch, and scan button."""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.set_margin_top(8)
        header.set_margin_bottom(8)

        # Title
        self._title_label = Gtk.Label()
        self._title_label.set_markup(
            f'<b>{self.t("bt_config")}</b>'
        )
        self._title_label.set_halign(Gtk.Align.START)
        header.pack_start(self._title_label, True, True, 0)

        # Power switch
        power_label = Gtk.Label(label=self.t("power"))
        header.pack_end(power_label, False, False, 0)

        self._power_switch = Gtk.Switch()
        self._power_switch.set_active(is_adapter_powered())
        self._power_switch.connect("notify::active", self._on_power_toggled)
        header.pack_end(self._power_switch, False, False, 4)

        # Scan button
        self._scan_btn = Gtk.Button(label=self.t("scan"))
        self._scan_btn.connect("clicked", self._on_scan_clicked)
        header.pack_end(self._scan_btn, False, False, 8)

        return header

    def _build_device_panel(self):
        """Build the left panel with the list of Bluetooth devices."""
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Section label
        self._devices_label = Gtk.Label()
        self._devices_label.set_markup(
            f'<b>{self.t("available_devices")}</b>'
        )
        self._devices_label.set_halign(Gtk.Align.START)
        self._devices_label.set_margin_start(12)
        self._devices_label.set_margin_top(8)
        self._devices_label.set_margin_bottom(4)
        panel.pack_start(self._devices_label, False, False, 0)

        # Scrolled list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._device_list = Gtk.ListBox()
        self._device_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._device_list.connect("row-selected", self._on_device_selected)
        scroll.add(self._device_list)
        panel.pack_start(scroll, True, True, 0)

        # Spinner for scanning
        self._scan_spinner = Gtk.Spinner()
        self._scan_spinner.set_margin_top(4)
        self._scan_spinner.set_margin_bottom(4)
        panel.pack_start(self._scan_spinner, False, False, 0)

        return panel

    def _build_detail_panel(self):
        """Build the right panel with device details and actions."""
        self._detail_stack = Gtk.Stack()
        self._detail_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # Empty state
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty.set_valign(Gtk.Align.CENTER)
        empty.set_halign(Gtk.Align.CENTER)
        icon = Gtk.Label()
        icon.set_markup('<span size="xx-large">\U0001F4E1</span>')
        empty.pack_start(icon, False, False, 0)
        self._empty_label = Gtk.Label(label=self.t("no_devices"))
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

        return bar

    # -- Device List Rows --------------------------------------------------

    def _populate_device_list(self, devices):
        """Populate the ListBox with Bluetooth device rows."""
        self._devices = devices

        for child in self._device_list.get_children():
            self._device_list.remove(child)

        if not devices:
            label = Gtk.Label(label=self.t("no_devices"))
            label.set_margin_top(20)
            row = Gtk.ListBoxRow()
            row.add(label)
            row.device = None
            self._device_list.add(row)
            self._device_list.show_all()
            return

        for dev in devices:
            row = self._create_device_row(dev)
            self._device_list.add(row)

        self._device_list.show_all()

    def _create_device_row(self, device):
        """Create a ListBox row for a single Bluetooth device."""
        row = Gtk.ListBoxRow()
        row.device = device
        row.get_style_context().add_class("network-row")
        if device.connected:
            row.get_style_context().add_class("network-row-connected")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        # Device icon
        icon_label = Gtk.Label(label=_icon_for_device(device))
        hbox.pack_start(icon_label, False, False, 4)

        # Name and status
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_label = Gtk.Label(label=device.display_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.get_style_context().add_class("ssid-label")
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.pack_start(name_label, False, False, 0)

        status_parts = []
        if device.paired:
            status_parts.append(self.t("paired"))
        if device.trusted:
            status_parts.append(self.t("trusted"))
        status_text = ', '.join(status_parts) if status_parts else self.t("not_paired")

        status_label = Gtk.Label(label=status_text)
        status_label.set_halign(Gtk.Align.START)
        status_label.get_style_context().add_class("security-label")
        vbox.pack_start(status_label, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)

        # Connected indicator
        if device.connected:
            connected_label = Gtk.Label(label=self.t("connected"))
            connected_label.get_style_context().add_class("connected-label")
            hbox.pack_end(connected_label, False, False, 4)

        row.add(hbox)
        return row

    # -- Detail Panel Content ----------------------------------------------

    def _show_device_details(self, device):
        """Display details and action buttons for the selected device."""
        for child in self._detail_box.get_children():
            self._detail_box.remove(child)

        # Device name header
        name_label = Gtk.Label()
        name_label.set_markup(
            f'<b><big>{GLib.markup_escape_text(device.display_name)}</big></b>'
        )
        name_label.set_halign(Gtk.Align.START)
        self._detail_box.pack_start(name_label, False, False, 0)

        sep = Gtk.Separator()
        self._detail_box.pack_start(sep, False, False, 4)

        # Info grid
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(6)
        row_idx = 0

        info_items = [
            (self.t("address"), device.address),
            (self.t("status"),
             self.t("connected") if device.connected
             else (self.t("paired") if device.paired
                   else self.t("not_paired"))),
            (self.t("type"), device.icon if device.icon else '-'),
        ]
        if device.trusted:
            info_items.append((self.t("trusted"), '\u2705'))

        for key, val in info_items:
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

        if device.connected:
            dc_btn = Gtk.Button(label=self.t("disconnect"))
            dc_btn.get_style_context().add_class("destructive-action")
            dc_btn.connect("clicked", self._on_disconnect_clicked, device)
            btn_box.pack_start(dc_btn, True, True, 0)
        elif device.paired:
            conn_btn = Gtk.Button(label=self.t("connect"))
            conn_btn.get_style_context().add_class("suggested-action")
            conn_btn.connect("clicked", self._on_connect_clicked, device)
            btn_box.pack_start(conn_btn, True, True, 0)
        else:
            pair_btn = Gtk.Button(label=self.t("pair"))
            pair_btn.get_style_context().add_class("suggested-action")
            pair_btn.connect("clicked", self._on_pair_clicked, device)
            btn_box.pack_start(pair_btn, True, True, 0)

        # Trust/Untrust toggle
        if device.paired:
            trust_label = self.t("untrust") if device.trusted else self.t("trust")
            trust_btn = Gtk.Button(label=trust_label)
            trust_btn.connect("clicked", self._on_trust_clicked, device)
            btn_box.pack_start(trust_btn, False, False, 0)

        # Remove button (if paired)
        if device.paired:
            remove_btn = Gtk.Button(label=self.t("remove"))
            remove_btn.get_style_context().add_class("destructive-action")
            remove_btn.connect("clicked", self._on_remove_clicked, device)
            btn_box.pack_start(remove_btn, False, False, 0)

        self._detail_box.pack_start(btn_box, False, False, 0)

        # Action spinner and status
        self._action_spinner = Gtk.Spinner()
        self._detail_box.pack_start(self._action_spinner, False, False, 4)

        self._action_status_label = Gtk.Label()
        self._detail_box.pack_start(self._action_status_label, False, False, 0)

        self._detail_stack.set_visible_child_name("details")
        self._detail_box.show_all()

    # -- Event Handlers ----------------------------------------------------

    def _on_power_toggled(self, switch, gparam):
        """Handle power switch toggle."""
        on = switch.get_active()
        switch.set_sensitive(False)

        def _on_power_done(success):
            switch.set_sensitive(True)
            if on and success:
                self._on_scan_clicked(None)
            self._refresh_adapter_state()

        async_set_power(on, _on_power_done)

    def _on_scan_clicked(self, button):
        """Start a Bluetooth scan."""
        self._scan_spinner.start()
        if button:
            button.set_sensitive(False)
        async_scan(self._on_scan_complete)

    def _on_scan_complete(self, devices):
        """Handle scan results."""
        self._scan_spinner.stop()
        self._scan_btn.set_sensitive(True)
        self._populate_device_list(devices)
        self._refresh_adapter_state()

    def _auto_refresh(self):
        """Auto-refresh device list (without full scan).

        Skips if a previous refresh is still in flight to avoid
        piling up background threads under slow conditions.
        """
        if self._refresh_in_flight:
            return True  # Skip this cycle, try again next time

        self._refresh_in_flight = True

        def _quick_refresh(devices):
            self._populate_device_list(devices)
            self._update_status_bar()
            self._refresh_in_flight = False

        def _worker():
            devices = get_devices()
            GLib.idle_add(_quick_refresh, devices)

        import threading
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True  # Continue the timer

    def _on_device_selected(self, listbox, row):
        """Handle device selection in the list."""
        if row is None or not hasattr(row, 'device') or row.device is None:
            self._detail_stack.set_visible_child_name("empty")
            return
        self._selected_device = row.device
        self._show_device_details(row.device)

    def _on_pair_clicked(self, button, device):
        """Handle pair button click."""
        self._action_spinner.start()
        self._action_status_label.set_text(self.t("pairing"))
        button.set_sensitive(False)
        async_pair(device.address, self._on_pair_result)

    def _on_pair_result(self, status):
        """Handle pair result."""
        self._action_spinner.stop()
        if status == 'paired':
            self._action_status_label.set_text(self.t("paired"))
            self._action_status_label.get_style_context().add_class("status-connected")
        else:
            self._action_status_label.set_text(f'{self.t("pair_failed")}: {status}')
            self._action_status_label.get_style_context().add_class("status-error")
        # Refresh device list
        async_scan(self._on_scan_complete, scan_duration=1)

    def _on_connect_clicked(self, button, device):
        """Handle connect button click."""
        self._action_spinner.start()
        self._action_status_label.set_text(self.t("connecting"))
        button.set_sensitive(False)
        async_connect(device.address, self._on_connect_result)

    def _on_connect_result(self, status):
        """Handle connect result."""
        self._action_spinner.stop()
        if status == 'connected':
            self._action_status_label.set_text(self.t("connected"))
            self._action_status_label.get_style_context().add_class("status-connected")
        else:
            self._action_status_label.set_text(f'{self.t("connect_failed")}: {status}')
            self._action_status_label.get_style_context().add_class("status-error")
        async_scan(self._on_scan_complete, scan_duration=1)

    def _on_disconnect_clicked(self, button, device):
        """Handle disconnect button click."""
        button.set_sensitive(False)
        async_disconnect(device.address, self._on_disconnect_result)

    def _on_disconnect_result(self, success):
        """Handle disconnect result."""
        async_scan(self._on_scan_complete, scan_duration=1)

    def _on_trust_clicked(self, button, device):
        """Handle trust toggle."""
        new_trust = not device.trusted
        trust_device(device.address, new_trust)
        async_scan(self._on_scan_complete, scan_duration=1)

    def _on_remove_clicked(self, button, device):
        """Handle remove device button click."""
        dialog = Gtk.MessageDialog(
            parent=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f'{self.t("confirm_remove")}\n{device.display_name}',
        )
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            async_remove(device.address,
                         lambda ok: async_scan(self._on_scan_complete, scan_duration=1))

    # -- Status Bar Update -------------------------------------------------

    def _refresh_adapter_state(self):
        """Fetch adapter state asynchronously, then update the status bar."""
        def _on_state(available, powered):
            self._adapter_available = available
            self._adapter_powered = powered
            self._update_status_bar()

        async_get_adapter_state(_on_state)

    def _update_status_bar(self):
        """Update the status bar with cached Bluetooth status."""
        if not self._adapter_available:
            self._status_icon.set_text("\u274C")
            self._status_label.set_text(self.t("no_adapter"))
            return

        if not self._adapter_powered:
            self._status_icon.set_text("\u26AA")
            self._status_label.set_text(self.t("adapter_off"))
            return

        # Check for connected devices
        connected = [d for d in self._devices if d.connected]
        if connected:
            names = ', '.join(d.display_name for d in connected)
            self._status_icon.set_text("\u2705")
            self._status_label.set_text(f"{self.t('connected')}: {names}")
        else:
            self._status_icon.set_text("\U0001F4E1")
            self._status_label.set_text(self.t("disconnected"))
