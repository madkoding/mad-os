"""
madOS Installer - GTK Edition
An AI-orchestrated Arch Linux system installer
Beautiful GUI installer with Nord theme and i18n support
"""

from .app import MadOSInstaller

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


def main():
    """Main entry point"""
    app = MadOSInstaller()
    app.connect('destroy', Gtk.main_quit)
    Gtk.main()
