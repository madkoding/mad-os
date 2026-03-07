"""
madOS Installer - Configuration Generator Module

Handles chroot configuration and system setup script generation.
"""

import glob as globmod
import os
import re
import subprocess

from gi.repository import Gtk

from ..config import TIMEZONES, LOCALE_MAP, LOCALE_KB_MAP, SCRIPTS_DIR
from ..utils import log_message, set_progress


def build_config_script(data):
    """Build the chroot configuration shell script."""
    disk = data["disk"]

    timezone = data["timezone"]
    if timezone not in TIMEZONES:
        raise ValueError(f"Invalid timezone: {timezone}")

    locale = data["locale"]
    valid_locales = list(LOCALE_MAP.values())
    if locale not in valid_locales:
        raise ValueError(f"Invalid locale: {locale}")

    if not re.match(r"^/dev/[a-zA-Z0-9]+$", disk):
        raise ValueError(f"Invalid disk path: {disk}")

    username = data["username"]
    if not re.match(r"^[a-z_][a-z0-9_-]*$", username):
        raise ValueError(f"Invalid username: {username}")

    ventoy_size = data.get("ventoy_persist_size", 4096)

    return f'''#!/bin/bash
set -e
exec {SCRIPTS_DIR}/configure-system.sh "{username}" "{timezone}" "{locale}" "{data["hostname"]}" "{disk}" "{ventoy_size}"
'''


def run_chroot_with_progress(app):
    """Run arch-chroot configure.sh while streaming output and updating progress."""
    progress_start = 0.55
    progress_end = 0.90

    script_path = "/mnt/root/configure.sh"
    if not os.path.isfile(script_path):
        raise FileNotFoundError(
            f"Configuration script not found at {script_path} — disk may be full or write failed"
        )
    if os.path.getsize(script_path) == 0:
        raise ValueError(f"Configuration script at {script_path} is empty — write may have failed")

    proc = subprocess.Popen(
        ["arch-chroot", "/mnt", "/root/configure.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    progress_pattern = re.compile(r"\[PROGRESS\s+(\d+)/(\d+)\]\s+(.+)")

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            continue

        progress_match = progress_pattern.search(line)
        if progress_match:
            step = int(progress_match.group(1))
            total = int(progress_match.group(2))
            description = progress_match.group(3)
            progress = progress_start + (progress_end - progress_start) * (step / max(total, 1))
            progress = min(progress, progress_end)
            set_progress(app, progress, description)
            log_message(app, f"  {description}")
            continue

        log_message(app, f"  {line}")

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, "arch-chroot")

    set_progress(app, progress_end, "System configured")
    log_message(app, "System configuration complete")
