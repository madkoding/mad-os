#!/usr/bin/env python3
"""madOS PDF Viewer - Entry point"""

import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from .app import PDFViewerApp


def main():
    PDFViewerApp(sys.argv[1] if len(sys.argv) > 1 else None)
    Gtk.main()


if __name__ == "__main__":
    main()
