#!/usr/bin/env python3
"""madOS WiFi Configuration - Entry point."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .app import WiFiApp


def main():
    """Launch the madOS WiFi Configuration application."""
    app = WiFiApp()
    Gtk.main()


if __name__ == '__main__':
    main()
