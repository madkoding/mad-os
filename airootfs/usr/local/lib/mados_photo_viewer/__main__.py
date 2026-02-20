#!/usr/bin/env python3
"""madOS Photo Viewer - Entry point

Launch the photo viewer application. Optionally pass an image or video
file path as the first command-line argument to open it immediately.

Usage:
    python3 -m mados_photo_viewer [filepath]
"""

import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from .app import PhotoViewerApp


def main():
    """Parse arguments and launch the GTK application."""
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None
    PhotoViewerApp(initial_file)
    Gtk.main()


if __name__ == "__main__":
    main()
