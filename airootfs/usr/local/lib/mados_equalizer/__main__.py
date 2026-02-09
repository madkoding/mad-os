#!/usr/bin/env python3
"""madOS Audio Equalizer - Entry point.

This module serves as the entry point for the madOS Audio Equalizer
application. It initializes GTK3, creates the main application window,
and starts the GTK main loop.

Usage:
    python3 -m mados_equalizer
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from .app import EqualizerApp


def main():
    """Initialize and run the madOS Audio Equalizer application."""
    app = EqualizerApp()
    Gtk.main()


if __name__ == '__main__':
    main()
