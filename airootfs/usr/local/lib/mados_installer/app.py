"""
madOS Installer - Main application window
"""

import os
import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from .config import DEMO_MODE, LOCALE_MAP
from .translations import TRANSLATIONS
from .theme import apply_theme
from .utils import random_suffix, show_error
from .pages import (
    create_welcome_page,
    create_wifi_page,
    create_disk_page,
    create_partitioning_page,
    create_user_page,
    create_locale_page,
    create_summary_page,
    create_installation_page,
    create_completion_page,
)


class MadOSInstaller(Gtk.Window):
    """Main installer window — orchestrates pages and holds shared state."""

    def __init__(self):
        super().__init__(title="madOS Installer" + (" (DEMO MODE)" if DEMO_MODE else ""))

        # Check root (skip in demo mode)
        if not DEMO_MODE and os.geteuid() != 0:
            show_error(self, "Root Required",
                       "This installer must be run as root.\n\nPlease use: sudo install-mados")
            sys.exit(1)

        self.set_default_size(1024, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)

        # Apply theme
        apply_theme()

        # Current language
        self.current_lang = 'English'

        # Installation data (shared across all pages)
        self.install_data = {
            'disk': None,
            'disk_size_gb': 0,
            'separate_home': True,
            'username': '',
            'password': '',
            'hostname': 'mados-' + random_suffix(),
            'timezone': 'UTC',
            'locale': 'en_US.UTF-8'
        }

        # Create notebook (page container)
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(False)

        # Add demo banner if in demo mode
        if DEMO_MODE:
            overlay = Gtk.Overlay()
            overlay.add(self.notebook)

            demo_banner = Gtk.Label()
            demo_banner.set_markup(
                '<span size="small" weight="bold">  DEMO MODE — No Installation Will Occur  </span>'
            )
            demo_banner.get_style_context().add_class('demo-banner')
            demo_banner.set_halign(Gtk.Align.CENTER)
            demo_banner.set_valign(Gtk.Align.START)
            demo_banner.set_margin_top(5)
            overlay.add_overlay(demo_banner)
            self.add(overlay)
        else:
            self.add(self.notebook)

        # Build all pages
        self._build_pages()
        self.show_all()

    # ── Translation helper ──────────────────────────────────────────────

    def t(self, key):
        """Translate key to current language"""
        return TRANSLATIONS[self.current_lang].get(key, key)

    # ── Language change ─────────────────────────────────────────────────

    def on_language_changed(self, combo):
        """Rebuild all pages with the newly selected language"""
        self.current_lang = combo.get_active_text()
        self.install_data['locale'] = LOCALE_MAP[self.current_lang]

        current_page = self.notebook.get_current_page()

        # Remove all pages
        while self.notebook.get_n_pages() > 0:
            self.notebook.remove_page(0)

        # Recreate
        self._build_pages()

        self.notebook.set_current_page(min(current_page, self.notebook.get_n_pages() - 1))
        self.show_all()

    # ── Page construction ───────────────────────────────────────────────

    def _build_pages(self):
        """Create all installer pages in order"""
        create_welcome_page(self)
        create_wifi_page(self)
        create_disk_page(self)
        create_partitioning_page(self)
        create_user_page(self)
        create_locale_page(self)
        create_summary_page(self)
        create_installation_page(self)
        create_completion_page(self)
