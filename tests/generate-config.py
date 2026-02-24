#!/usr/bin/env python3
"""
Generate the madOS chroot configuration script using the real installer code.

This script mocks GTK/GI dependencies so _build_config_script() can run in a
headless CI environment.  Output goes to stdout; the caller (test-installation.sh)
captures it to validate bash syntax and run it inside an arch-chroot.
"""

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so the installer modules can be imported without
# a display server or GTK libraries installed.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks()

# ---------------------------------------------------------------------------
# Now safe to import the installer's config-script builder.
# ---------------------------------------------------------------------------

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else ".")

from mados_installer.pages.installation import _build_config_script  # noqa: E402

# ---------------------------------------------------------------------------
# Generate and print the script.
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Generate madOS config script")
parser.add_argument("lib_path", help="Path to the mados_installer library")
parser.add_argument("--disk", default="/dev/loop0")
parser.add_argument("--username", default="testuser")
parser.add_argument("--password", default="testpass123")
parser.add_argument("--hostname", default="mados-test")
parser.add_argument("--timezone", default="America/New_York")
parser.add_argument("--locale", default="en_US.UTF-8")

args = parser.parse_args()

data = {
    "disk": args.disk,
    "disk_size_gb": 60,
    "separate_home": True,
    "username": args.username,
    "password": args.password,
    "hostname": args.hostname,
    "timezone": args.timezone,
    "locale": args.locale,
}

print(_build_config_script(data))
