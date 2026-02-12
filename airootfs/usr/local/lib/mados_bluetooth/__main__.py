#!/usr/bin/env python3
"""madOS Bluetooth Configuration - Entry point."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .app import BluetoothApp


def main():
    """Launch the madOS Bluetooth Configuration application."""
    app = BluetoothApp()
    Gtk.main()


if __name__ == '__main__':
    main()
