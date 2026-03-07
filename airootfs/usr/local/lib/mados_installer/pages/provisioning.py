"""
madOS Installer - Automated Provisioning Page

Allows users to load a mados-config.yaml file for unattended installation.
"""

import os
from gi.repository import Gtk

from .base import create_page_header, create_nav_buttons
from ..config import NORD_SNOW_STORM, NORD_FROST, NORD_AURORA, NORD_POLAR_NIGHT


class ProvisioningPage(Gtk.Box):
    """Provisioning configuration page."""

    def __init__(self, app, parent_box):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.app = app
        self.parent_box = parent_box
        self.loaded_config = None
        self.config_file_path = None

        self._build_ui()

    def _build_ui(self):
        """Build the provisioning page UI."""
        # Header
        header = create_page_header(self.app, "Automated Provisioning", step_num=2, total_steps=8)
        self.pack_start(header, False, False, 0)

        # Main content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        self.pack_start(content, True, True, 0)

        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup(
            f'<span size="11000" foreground="{NORD_SNOW_STORM["nord6"]}">'
            "Load a <b>mados-config.yaml</b> file to automate installation.\n"
            "Skip this step for manual configuration."
            "</span>"
        )
        desc_label.set_line_wrap(True)
        desc_label.set_halign(Gtk.Align.CENTER)
        content.pack_start(desc_label, False, False, 0)

        # File selection box
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        file_box.set_halign(Gtk.Align.CENTER)
        content.pack_start(file_box, False, False, 0)

        # File chooser button
        self.file_chooser = Gtk.FileChooserButton()
        self.file_chooser.set_title("Select Provisioning Config")
        self.file_chooser.set_width_chars(40)
        
        # Filter for YAML files
        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name("YAML files")
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")
        self.file_chooser.add_filter(filter_yaml)
        
        # All files filter
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        self.file_chooser.add_filter(filter_all)
        
        self.file_chooser.connect("file-set", self._on_file_selected)
        file_box.pack_start(self.file_chooser, False, False, 0)

        # Load button
        load_btn = Gtk.Button(label="Load Configuration")
        load_btn.get_style_context().add_class("success-button")
        load_btn.connect("clicked", self._on_load_clicked)
        file_box.pack_start(load_btn, False, False, 0)

        # Status area (initially hidden)
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.status_box.set_margin_top(10)
        self.status_box.set_margin_start(30)
        self.status_box.set_margin_end(30)
        content.pack_start(self.status_box, False, False, 0)

        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        self.status_box.pack_start(self.status_label, False, False, 0)

        # Config summary
        self.summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.summary_box.set_margin_start(12)
        self.status_box.pack_start(self.summary_box, False, False, 0)

        # Configuration info (hidden until loaded)
        self.status_box.set_no_show_all(True)

        # Navigation
        nav_box = create_nav_buttons(
            self.app,
            self._on_back,
            self._on_next,
            next_label=self.app.t("next"),
            next_class="nav-back-button",
        )
        nav_box.set_margin_top(10)
        nav_box.set_margin_bottom(20)
        nav_box.set_margin_end(20)
        self.pack_start(nav_box, False, False, 0)

        # Info about config format
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_margin_top(20)
        info_box.set_margin_start(30)
        info_box.set_margin_end(30)
        content.pack_start(info_box, False, False, 0)

        info_label = Gtk.Label()
        info_label.set_markup(
            f'<span size="9000" foreground="{NORD_POLAR_NIGHT["nord3"]}">'
            f'<b>Required fields:</b> username, password, hostname, timezone, locale\n'
            f'<b>Optional:</b> disk layout, partitioning, package groups, post-install scripts\n\n'
            f'Example: mados-config-example.yaml in the installation media root'
            "</span>"
        )
        info_label.set_line_wrap(True)
        info_label.set_halign(Gtk.Align.CENTER)
        info_box.pack_start(info_label, False, False, 0)

    def _on_file_selected(self, widget):
        """Handle file selection."""
        self.config_file_path = widget.get_filename()

    def _on_load_clicked(self, button):
        """Load and validate the selected configuration."""
        if not self.config_file_path:
            self._show_error("Please select a configuration file first.")
            return

        # Clear previous status
        for child in self.status_box.get_children():
            self.status_box.remove(child)

        # Load configuration
        from ..provisioning import load_config_from_file
        
        config, errors = load_config_from_file(self.config_file_path)

        if errors:
            self._show_error("\n".join(errors))
            return

        self.loaded_config = config
        self._show_success(config)

    def _show_error(self, message):
        """Show error message."""
        for child in self.status_box.get_children():
            self.status_box.remove(child)

        error_label = Gtk.Label()
        error_label.set_markup(
            f'<span foreground="#BF616A">❌ {message}</span>'
        )
        error_label.set_halign(Gtk.Align.START)
        error_label.set_line_wrap(True)
        self.status_box.pack_start(error_label, False, False, 0)

        self.status_box.set_no_show_all(False)
        self.status_box.show_all()

    def _show_success(self, config):
        """Show successful configuration load."""
        for child in self.status_box.get_children():
            self.status_box.remove(child)

        # Success message
        success_label = Gtk.Label()
        success_label.set_markup(
            f'<span foreground="#A3BE8C" size="11000" weight="bold">'
            f'✓ Configuration loaded successfully!</span>'
        )
        success_label.set_halign(Gtk.Align.START)
        self.status_box.pack_start(success_label, False, False, 0)

        # Configuration summary
        summary_data = [
            ("Username", config.username),
            ("Hostname", config.hostname),
            ("Disk", config.disk_device),
            ("Partitioning", config.partitioning),
            ("Timezone", config.timezone),
            ("Locale", config.locale),
        ]

        for label, value in summary_data:
            summary_label = Gtk.Label()
            summary_label.set_markup(
                f'<span foreground="{NORD_SNOW_STORM["nord6"]}">'
                f'  • <b>{label}:</b> {value}'
                "</span>"
            )
            summary_label.set_halign(Gtk.Align.START)
            self.summary_box.pack_start(summary_label, False, False, 0)

        # Package groups
        pkg_groups = []
        if config.dev_tools:
            pkg_groups.append("Dev Tools")
        if config.ai_ml:
            pkg_groups.append("AI/ML")
        if config.multimedia:
            pkg_groups.append("Multimedia")

        if pkg_groups:
            pkg_label = Gtk.Label()
            pkg_label.set_markup(
                f'<span foreground="{NORD_SNOW_STORM["nord6"]}">'
                f'  • <b>Packages:</b> {", ".join(pkg_groups)}'
                "</span>"
            )
            pkg_label.set_halign(Gtk.Align.START)
            self.summary_box.pack_start(pkg_label, False, False, 0)

        # Post-install commands
        if config.post_install_commands:
            cmd_label = Gtk.Label()
            cmd_label.set_markup(
                f'<span foreground="{NORD_SNOW_STORM["nord6"]}">'
                f'  • <b>Post-install:</b> {len(config.post_install_commands)} commands'
                "</span>"
            )
            cmd_label.set_halign(Gtk.Align.START)
            self.summary_box.pack_start(cmd_label, False, False, 0)

        self.status_box.set_no_show_all(False)
        self.status_box.show_all()

    def _on_back(self, button):
        """Handle back button click."""
        self.app.show_page("wifi")

    def _on_next(self, button):
        """Handle next button click."""
        # Store loaded config in app if available
        if self.loaded_config:
            self.app.provisioning_config = self.loaded_config
            # Apply config to install_data
            self.app.install_data.update(self.loaded_config.to_install_data())
            # Set package selection
            self.app.package_selection = self.loaded_config._get_package_list()

        self.app.show_page("disk")


def create_provisioning_page(app, parent_box):
    """Create and register the provisioning page."""
    page = ProvisioningPage(app, parent_box)
    app.notebook.append_page(page, Gtk.Label(label="Provisioning"))
    return page
