"""
madOS Installer - Shared utility functions
"""

import os
import random
import string

from gi.repository import Gtk, GLib, GdkPixbuf

from .config import NORD_FROST


def random_suffix(length=4):
    """Generate random hostname suffix"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def load_logo(size=160):
    """Load logo from multiple possible paths, returns Gtk.Image or None"""
    logo_paths = [
        '/usr/share/pixmaps/mados-logo.png',
        'airootfs/usr/share/pixmaps/mados-logo.png',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../share/pixmaps/mados-logo.png')
    ]
    for logo_path in logo_paths:
        try:
            if os.path.exists(logo_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, size, size, True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception as e:
            print(f"Could not load logo from {logo_path}: {e}")
    return None


LOG_FILE = "/var/log/mados-install.log"


def save_log_to_file(app, path=None):
    """Save the installer log buffer contents to a file.

    Uses os.open with O_NOFOLLOW to prevent symlink attacks, since the
    installer runs as root.  Permissions are set to 0o644 so that the
    user can read the log from a terminal after the installer closes.

    Returns the path written to, or *None* on failure.
    """
    if path is None:
        path = LOG_FILE
    try:
        buf = app.log_buffer
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
            0o644,
        )
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        return path
    except Exception as exc:
        print(f"Warning: could not save install log to {path}: {exc}")
        return None


def show_error(parent, title, message):
    """Show error dialog with dark theme"""
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title
    )
    dialog.format_secondary_text(message)
    style_dialog(dialog)
    dialog.run()
    dialog.destroy()


def style_dialog(dialog):
    """Apply dark theme to a dialog"""
    dialog.get_content_area().foreach(
        lambda w: w.get_style_context().add_class('dialog-content')
        if hasattr(w, 'get_style_context') else None
    )


def log_message(app, message):
    """Add message to log buffer (thread-safe)"""
    GLib.idle_add(_log_idle, app, message)


def _log_idle(app, message):
    """Idle callback for logging"""
    app.log_buffer.insert_at_cursor(message + "\n")
    # Auto-scroll log viewer to the bottom using the built-in insert mark
    if hasattr(app, 'log_scrolled'):
        text_view = app.log_scrolled.get_child()
        if text_view:
            insert_mark = app.log_buffer.get_insert()
            text_view.scroll_to_mark(insert_mark, 0.0, True, 0.0, 1.0)
    return False


def set_progress(app, fraction, text):
    """Update progress bar (thread-safe)"""
    GLib.idle_add(_progress_idle, app, fraction, text)


def _progress_idle(app, fraction, text):
    """Idle callback for progress"""
    app.progress_bar.set_fraction(fraction)
    app.progress_bar.set_text(f"{int(fraction * 100)}%")
    app.status_label.set_markup(
        f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{text}</span>'
    )
    return False
