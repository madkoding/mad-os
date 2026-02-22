"""Scanner and parser for .desktop application entries."""

import os
import re
import shlex
import subprocess
from collections import OrderedDict
from configparser import ConfigParser

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

from .config import EXCLUDED_DESKTOP, ICON_SIZE
from . import config as _config


# Regex to strip field codes from Exec values (%f, %F, %u, %U, %d, %D, %n, %N, %i, %c, %k, %v, %m)
# Uses a possessive-style pattern (atomic via fixed-width match) to avoid backtracking issues.
_FIELD_CODE_RE = re.compile(r' ?%[fFuUdDnNickvm](?:\s|$)')


class DesktopEntry:
    """Represents a parsed .desktop application entry."""

    __slots__ = ("name", "icon_name", "exec_cmd", "comment", "categories", "filename", "pixbuf")

    def __init__(self, name, icon_name, exec_cmd, comment, categories, filename, pixbuf=None):
        self.name = name
        self.icon_name = icon_name
        self.exec_cmd = exec_cmd
        self.comment = comment
        self.categories = categories
        self.filename = filename
        self.pixbuf = pixbuf


class EntryGroup:
    """A group of DesktopEntry items sharing the same icon."""

    __slots__ = ("group_name", "entries", "representative")

    def __init__(self, group_name, entries):
        self.group_name = group_name
        self.entries = entries          # list of DesktopEntry
        self.representative = entries[0]  # icon/pixbuf comes from first entry


def _clean_exec(raw_exec):
    """Remove field codes (%u, %f, etc.) and env prefixes from Exec value."""
    cleaned = _FIELD_CODE_RE.sub("", raw_exec).strip()
    return cleaned


def _resolve_icon(icon_name, size=ICON_SIZE):
    """Resolve an icon name to a GdkPixbuf, returning None on failure."""
    if not icon_name:
        return _fallback_icon(size)

    # Absolute path to icon file
    if os.path.isabs(icon_name) and os.path.isfile(icon_name):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_name, size, size, True)
        except Exception:
            return _fallback_icon(size)

    # Icon theme lookup
    theme = Gtk.IconTheme.get_default()
    try:
        icon_info = theme.lookup_icon(icon_name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        if icon_info:
            return icon_info.load_icon()
    except Exception:
        pass

    # Try without extension
    name_no_ext = os.path.splitext(icon_name)[0] if "." in icon_name else None
    if name_no_ext:
        try:
            icon_info = theme.lookup_icon(name_no_ext, size, Gtk.IconLookupFlags.FORCE_SIZE)
            if icon_info:
                return icon_info.load_icon()
        except Exception:
            pass

    return _fallback_icon(size)


def _fallback_icon(size=ICON_SIZE):
    """Return a generic application icon as fallback."""
    theme = Gtk.IconTheme.get_default()
    for fallback in ("application-x-executable", "application-default-icon", "exec"):
        try:
            icon_info = theme.lookup_icon(fallback, size, Gtk.IconLookupFlags.FORCE_SIZE)
            if icon_info:
                return icon_info.load_icon()
        except Exception:
            continue
    return None


def scan_desktop_entries():
    """Scan standard directories for .desktop files and return sorted list of DesktopEntry."""
    entries = {}

    for directory in _config.DESKTOP_DIRS:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if not fname.endswith(".desktop"):
                continue
            if fname in EXCLUDED_DESKTOP:
                continue
            if fname in entries:
                continue

            filepath = os.path.join(directory, fname)
            entry = _parse_desktop_file(filepath, fname)
            if entry:
                entries[fname] = entry

    # Sort alphabetically by display name
    sorted_entries = sorted(entries.values(), key=lambda e: e.name.lower())
    return sorted_entries


def _parse_desktop_file(filepath, filename):
    """Parse a single .desktop file and return a DesktopEntry or None."""
    parser = ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str  # Preserve case of keys

    try:
        parser.read(filepath, encoding="utf-8")
    except Exception:
        return None

    section = "Desktop Entry"
    if not parser.has_section(section):
        return None

    def get(key, default=""):
        return parser.get(section, key, fallback=default)

    # Filter out non-application entries
    entry_type = get("Type")
    if entry_type != "Application":
        return None

    # Skip hidden or no-display entries
    if get("NoDisplay", "false").lower() == "true":
        return None
    if get("Hidden", "false").lower() == "true":
        return None

    # Must have Exec
    raw_exec = get("Exec")
    if not raw_exec:
        return None

    name = get("Name", filename)
    icon_name = get("Icon", "")
    comment = get("Comment", "")
    categories = get("Categories", "")
    exec_cmd = _clean_exec(raw_exec)

    # Resolve icon
    pixbuf = _resolve_icon(icon_name)

    return DesktopEntry(
        name=name,
        icon_name=icon_name,
        exec_cmd=exec_cmd,
        comment=comment,
        categories=categories,
        filename=filename,
        pixbuf=pixbuf,
    )


def launch_application(exec_cmd):
    """Launch an application from its Exec command string."""
    try:
        args = shlex.split(exec_cmd)
        subprocess.Popen(
            args,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[mados-launcher] Failed to launch '{exec_cmd}': {e}")


def _icon_group_key(entry):
    """Return the grouping key for an entry based on its icon name.

    Entries with the same icon_name (normalized) will be grouped together.
    Entries with no icon or the generic fallback icon are not grouped.
    """
    icon = (entry.icon_name or "").strip()
    if not icon:
        return None
    # Normalize: lowercase, strip path and extension for comparison
    key = os.path.basename(icon).lower()
    key = os.path.splitext(key)[0] if "." in key else key
    # Don't group under generic fallback icons
    if key in ("application-x-executable", "application-default-icon", "exec", ""):
        return None
    return key


def group_entries(entries):
    """Group entries that share the same icon into a single dock slot.

    Returns a list of items where each item is either:
    - A single DesktopEntry (unique icon), or
    - An EntryGroup (2+ entries sharing the same icon).

    Items are sorted alphabetically: groups by first entry name, singles by name.
    """
    icon_groups = OrderedDict()   # icon_key -> [DesktopEntry]
    ungrouped = []

    for entry in entries:
        key = _icon_group_key(entry)
        if key:
            icon_groups.setdefault(key, []).append(entry)
        else:
            ungrouped.append(entry)

    result = []

    # Groups with 2+ entries become EntryGroup; singletons stay as DesktopEntry
    for icon_key, members in icon_groups.items():
        if len(members) >= 2:
            group_name = members[0].name  # Use first entry's name as label
            result.append(EntryGroup(group_name, members))
        else:
            result.append(members[0])

    # Add ungrouped entries
    result.extend(ungrouped)

    # Sort alphabetically
    def sort_key(item):
        if isinstance(item, EntryGroup):
            return item.representative.name.lower()
        return item.name.lower()

    result.sort(key=sort_key)
    return result
