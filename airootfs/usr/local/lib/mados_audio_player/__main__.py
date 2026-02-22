#!/usr/bin/env python3
"""madOS Audio Player - Entry point.

This module serves as the entry point for the madOS Audio Player
application. It initializes GTK3, creates the main application window,
and starts the GTK main loop.

Usage:
    python3 -m mados_audio_player [file1.mp3 file2.flac ...]
"""

import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from .app import AudioPlayerApp


def main():
    """Initialize and run the madOS Audio Player application."""
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    AudioPlayerApp(files=files)
    Gtk.main()


if __name__ == "__main__":
    main()
