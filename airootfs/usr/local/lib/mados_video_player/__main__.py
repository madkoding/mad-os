#!/usr/bin/env python3
"""madOS Video Player - Entry point

Launch the video player application. Optionally pass one or more
video file paths as arguments to add them to the playlist.

Usage:
    python3 -m mados_video_player [file1 file2 ...]
"""

import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from .app import VideoPlayerApp


def main():
    """Parse arguments and launch the GTK application."""
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    VideoPlayerApp(files)
    Gtk.main()


if __name__ == "__main__":
    main()
