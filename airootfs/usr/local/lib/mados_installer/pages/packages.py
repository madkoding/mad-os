"""
madOS Installer - Package Selection Page

Allows users to select optional package groups:
- Development Tools
- AI/ML Tools
- Multimedia Production
"""

import os
from gi.repository import Gtk

from .base import create_page_header, create_nav_buttons
from ..config import NORD_SNOW_STORM, NORD_FROST, NORD_POLAR_NIGHT

# Package groups with descriptions and individual packages
PACKAGE_GROUPS = {
    "dev_tools": {
        "name": "Development Tools",
        "description": "Complete development environment with IDEs, compilers, and DevOps tools",
        "icon": "🛠️",
        "packages": [
            {"id": "base-devel", "name": "Base Development Tools", "default": True},
            {"id": "git", "name": "Git", "default": True},
            {"id": "code", "name": "Visual Studio Code", "default": False},
            {"id": "neovim", "name": "Neovim", "default": False},
            {"id": "docker", "name": "Docker & Docker Compose", "default": False},
            {"id": "podman", "name": "Podman", "default": False},
            {"id": "terraform", "name": "Terraform", "default": False},
            {"id": "ansible", "name": "Ansible", "default": False},
            {"id": "kubectl", "name": "Kubernetes CLI", "default": False},
        ],
    },
    "ai_ml": {
        "name": "AI/ML Tools",
        "description": "Artificial Intelligence and Machine Learning frameworks",
        "icon": "🤖",
        "packages": [
            {"id": "ollama", "name": "Ollama", "default": True},
            {"id": "opencode", "name": "OpenCode", "default": True},
            {"id": "python-transformers", "name": "HuggingFace Transformers", "default": False},
            {"id": "python-pytorch", "name": "PyTorch", "default": False},
            {"id": "python-tensorflow", "name": "TensorFlow", "default": False},
            {"id": "python-scikit-learn", "name": "Scikit-learn", "default": False},
            {"id": "jupyterlab", "name": "JupyterLab", "default": False},
            {"id": "python-matplotlib", "name": "Matplotlib", "default": False},
        ],
    },
    "multimedia": {
        "name": "Multimedia Production",
        "description": "Audio, video, and image editing tools",
        "icon": "🎨",
        "packages": [
            {"id": "kdenlive", "name": "Kdenlive (Video Editor)", "default": False},
            {"id": "obs-studio", "name": "OBS Studio", "default": False},
            {"id": "blender", "name": "Blender (3D)", "default": False},
            {"id": "gimp", "name": "GIMP (Image Editor)", "default": False},
            {"id": "inkscape", "name": "Inkscape (Vector)", "default": False},
            {"id": "krita", "name": "Krita (Digital Painting)", "default": False},
            {"id": "darktable", "name": "Darktable (RAW Photo)", "default": False},
            {"id": "ardour", "name": "Ardour (Audio DAW)", "default": False},
            {"id": "audacity", "name": "Audacity", "default": False},
            {"id": "lmms", "name": "LMMS (Music Production)", "default": False},
        ],
    },
}


class PackageSelectionPage(Gtk.Box):
    """Package selection page with grouped checkboxes."""

    def __init__(self, app, parent_box):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.app = app
        self.parent_box = parent_box

        # Store selected packages
        self.selected_packages = set()
        self.package_checkboxes = {}  # group_id -> {package_id -> checkbox}

        self._build_ui()

    def _build_ui(self):
        """Build the package selection UI."""
        # Header
        header = create_page_header(self.app, "Select Additional Packages", step_num=5, total_steps=8)
        self.pack_start(header, False, False, 0)

        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_margin_start(20)
        scroll.set_margin_end(20)
        scroll.set_margin_top(10)
        scroll.set_margin_bottom(10)
        self.pack_start(scroll, True, True, 0)

        # Main content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(20)
        content.set_margin_end(20)
        scroll.add(content)

        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup(
            f'<span size="11000" foreground="{NORD_SNOW_STORM["nord6"]}">'
            "Choose optional package groups to install. All packages are free and open-source."
            "</span>"
        )
        desc_label.set_line_wrap(True)
        desc_label.set_halign(Gtk.Align.CENTER)
        content.pack_start(desc_label, False, False, 0)

        # Package groups
        for group_id, group_data in PACKAGE_GROUPS.items():
            group_frame = self._create_group_frame(group_id, group_data)
            content.pack_start(group_frame, False, False, 0)

        # Navigation buttons
        nav_box = create_nav_buttons(
            self.app,
            self._on_back,
            self._on_next,
            next_label=self.app.t("next"),
            next_class="success-button",
        )
        nav_box.set_margin_top(10)
        nav_box.set_margin_bottom(20)
        nav_box.set_margin_end(20)
        self.pack_start(nav_box, False, False, 0)

        # Initialize with defaults
        self._apply_defaults()

    def _create_group_frame(self, group_id, group_data):
        """Create a frame for a package group."""
        frame = Gtk.Frame()
        frame.get_style_context().add_class("package-group-frame")
        frame.set_margin_bottom(8)

        # Frame content box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        frame.add(box)

        # Group header with icon and name
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_bottom(8)
        box.pack_start(header_box, False, False, 0)

        icon_label = Gtk.Label()
        icon_label.set_markup(f'<span size="16000">{group_data["icon"]}</span>')
        header_box.pack_start(icon_label, False, False, 0)

        name_label = Gtk.Label()
        name_label.set_markup(
            f'<span size="12000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
            f'{group_data["name"]}'
            "</span>"
        )
        name_label.set_halign(Gtk.Align.START)
        header_box.pack_start(name_label, False, False, 0)

        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup(
            f'<span size="9500" foreground="{NORD_SNOW_STORM["nord5"]}">'
            f'{group_data["description"]}'
            "</span>"
        )
        desc_label.set_line_wrap(True)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_margin_start(26)
        box.pack_start(desc_label, False, False, 0)

        # Package checkboxes
        packages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        packages_box.set_margin_start(26)
        packages_box.set_margin_top(8)
        box.pack_start(packages_box, False, False, 0)

        self.package_checkboxes[group_id] = {}

        for pkg in group_data["packages"]:
            checkbox = Gtk.CheckButton()
            checkbox.set_label(pkg["name"])
            checkbox.package_id = pkg["id"]
            checkbox.group_id = group_id
            checkbox.set_active(pkg["default"])
            checkbox.get_style_context().add_class("package-checkbox")
            packages_box.pack_start(checkbox, False, False, 0)

            self.package_checkboxes[group_id][pkg["id"]] = checkbox

        # Separator after group
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(8)
        box.pack_start(separator, False, False, 0)

        return frame

    def _apply_defaults(self):
        """Apply default package selections."""
        for group_id, group_data in PACKAGE_GROUPS.items():
            for pkg in group_data["packages"]:
                if pkg["default"]:
                    checkbox = self.package_checkboxes[group_id][pkg["id"]]
                    checkbox.set_active(True)
                    self.selected_packages.add(pkg["id"])

    def _on_back(self, button):
        """Handle back button click."""
        self.app.show_page("wifi")

    def _on_next(self, button):
        """Handle next button click."""
        # Update selected packages from checkboxes
        self._update_selection()

        # Store in app for use during installation
        self.app.package_selection = sorted(list(self.selected_packages))

        self.app.show_page("summary")

    def _update_selection(self):
        """Update selected_packages from checkbox states."""
        self.selected_packages.clear()

        for group_id, checkboxes in self.package_checkboxes.items():
            for pkg_id, checkbox in checkboxes.items():
                if checkbox.get_active():
                    self.selected_packages.add(pkg_id)

    def get_selected_summary(self):
        """Get human-readable summary of selected packages."""
        self._update_selection()

        if not self.selected_packages:
            return "No additional packages selected"

        selected = []
        for group_id, group_data in PACKAGE_GROUPS.items():
            group_selected = []
            for pkg in group_data["packages"]:
                if pkg["id"] in self.selected_packages:
                    group_selected.append(pkg["name"])

            if group_selected:
                selected.append(f"{group_data['icon']} {group_data['name']}: {len(group_selected)} packages")

        return "\n".join(selected) if selected else "No additional packages"
