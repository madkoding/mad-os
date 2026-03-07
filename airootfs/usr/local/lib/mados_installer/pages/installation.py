"""
madOS Installer - Installation progress page and install logic

This is the main orchestrator module that coordinates the installation process
using the modular components from mados_installer.modules.
"""

import os
import subprocess
import time
import threading

from gi.repository import Gtk, GLib

from ..config import DEMO_MODE, NORD_FROST
from ..utils import log_message, set_progress, show_error, save_log_to_file

from ..modules import (
    step_partition_disk,
    step_format_partitions,
    step_mount_filesystems,
    ensure_kernel_in_target,
    step_copy_live_files,
    rsync_rootfs_with_progress,
    run_chroot_with_progress,
    build_config_script,
)

from .base import create_page_header


def create_installation_page(app):
    """Installation progress page with spinner, progress bar and log"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")
    page.set_valign(Gtk.Align.CENTER)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_top(10)
    content.set_margin_bottom(14)

    app.install_spinner = Gtk.Spinner()
    app.install_spinner.get_style_context().add_class("install-spinner")
    app.install_spinner.set_halign(Gtk.Align.CENTER)
    app.install_spinner.set_margin_top(8)
    content.pack_start(app.install_spinner, False, False, 0)

    title = Gtk.Label()
    title.set_markup(f'<span size="15000" weight="bold">{app.t("installing")}</span>')
    title.set_halign(Gtk.Align.CENTER)
    content.pack_start(title, False, False, 0)

    app.status_label = Gtk.Label()
    app.status_label.set_markup(
        f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{app.t("preparing")}</span>'
    )
    app.status_label.set_halign(Gtk.Align.CENTER)
    content.pack_start(app.status_label, False, False, 0)

    app.progress_bar = Gtk.ProgressBar()
    app.progress_bar.set_show_text(True)
    app.progress_bar.set_margin_top(4)
    app.progress_bar.set_margin_start(16)
    app.progress_bar.set_margin_end(16)
    content.pack_start(app.progress_bar, False, False, 0)

    app.log_toggle = Gtk.EventBox()
    app.log_toggle.set_halign(Gtk.Align.CENTER)
    app.log_toggle.set_margin_top(8)
    toggle_label = Gtk.Label()
    toggle_label.set_markup(
        f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("show_log")}</span>'
    )
    toggle_label.get_style_context().add_class("log-toggle")
    app.log_toggle.add(toggle_label)
    app.log_toggle.connect("button-press-event", lambda w, e: _toggle_log(app))
    content.pack_start(app.log_toggle, False, False, 0)

    log_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    log_card.get_style_context().add_class("content-card")
    log_card.set_margin_top(4)
    log_card.set_no_show_all(True)
    app.log_card = log_card

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_min_content_height(120)
    scrolled.set_max_content_height(180)
    app.log_scrolled = scrolled

    app.log_buffer = Gtk.TextBuffer()
    log_view = Gtk.TextView(buffer=app.log_buffer)
    log_view.set_editable(False)
    log_view.set_monospace(True)
    log_view.set_left_margin(12)
    log_view.set_right_margin(12)
    log_view.set_top_margin(8)
    log_view.set_bottom_margin(8)
    scrolled.add(log_view)

    log_card.pack_start(scrolled, True, True, 0)
    content.pack_start(log_card, True, True, 0)

    page.pack_start(content, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Installing"))


def _toggle_log(app):
    """Toggle visibility of the log console"""
    if app.log_card.get_visible():
        app.log_card.hide()
        label = app.log_toggle.get_child()
        label.set_markup(
            f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("show_log")}</span>'
        )
    else:
        app.log_card.show()
        app.log_card.foreach(lambda w: w.show_all())
        label = app.log_toggle.get_child()
        label.set_markup(
            f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("hide_log")}</span>'
        )


def on_start_installation(app):
    """Start the installation process"""
    app.notebook.next_page()
    app.install_spinner.start()

    thread = threading.Thread(target=_run_installation, args=(app,))
    thread.daemon = True
    thread.start()


def _run_installation(app):
    """Perform installation (runs in background thread).

    Orchestrates the installation process using modular components:
    1. Partition disk
    2. Format partitions
    3. Mount filesystems
    4. Copy live system (rsync)
    5. Generate fstab
    6. Configure system
    """
    try:
        data = app.install_data
        disk = data["disk"]
        separate_home = data["separate_home"]
        disk_size_gb = data["disk_size_gb"]

        # Step 1: Partition
        boot_part, root_part, home_part = step_partition_disk(
            app, disk, separate_home, disk_size_gb
        )

        # Step 2: Format
        step_format_partitions(app, boot_part, root_part, home_part, separate_home)

        # Step 3: Mount
        step_mount_filesystems(app, boot_part, root_part, home_part, separate_home)

        # Step 4: Copy live system
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating system copy from live ISO...")
            set_progress(app, 0.21, "Copying system files...")
            time.sleep(0.5)
        else:
            rsync_rootfs_with_progress(app)

        # Step 4b: Ensure kernel exists
        if not DEMO_MODE:
            ensure_kernel_in_target(app)

        # Step 5: Generate fstab
        set_progress(app, 0.49, "Generating filesystem table...")
        log_message(app, "Generating fstab...")
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating genfstab -U /mnt...")
            time.sleep(0.5)
        else:
            result = subprocess.run(
                ["genfstab", "-U", "/mnt"], capture_output=True, text=True, check=True
            )
            with open("/mnt/etc/fstab", "w") as f:
                f.write(result.stdout)

        # Step 6: Prepare configuration
        set_progress(app, 0.50, "Preparing system configuration...")
        log_message(app, "Preparing Phase 1 configuration...")

        config_script = build_config_script(data)

        if DEMO_MODE:
            log_message(app, "[DEMO] Would write configuration script")
            time.sleep(0.5)
        else:
            with open("/mnt/root/configure.sh", "w") as f:
                f.write(config_script)
            step_copy_live_files(app)

        # Step 7: Run chroot configuration
        set_progress(app, 0.55, "Applying configurations...")
        log_message(app, "Running chroot configuration...")
        if DEMO_MODE:
            demo_steps = [
                (0.58, "Installing GRUB bootloader"),
                (0.64, "Enabling essential services..."),
                (0.70, "Rebuilding initramfs..."),
                (0.76, "Verifying graphical environment..."),
            ]
            for progress, desc in demo_steps:
                set_progress(app, progress, desc)
                time.sleep(0.5)
        else:
            run_chroot_with_progress(app)

        # Step 8: Cleanup
        set_progress(app, 0.90, "Cleaning up...")
        log_message(app, "Cleaning up...")
        if DEMO_MODE:
            time.sleep(0.8)
        else:
            subprocess.run(["rm", "/mnt/root/configure.sh"], check=True)
            subprocess.run(["sync"], check=False)
            subprocess.run(["umount", "-R", "/mnt"], check=False)

        set_progress(app, 1.0, "Installation complete!")
        log_message(app, "\n[OK] Installation completed successfully!")
        
        GLib.idle_add(_finish_installation, app)

    except Exception as e:
        log_message(app, f"\n[ERROR] {str(e)}")
        if not DEMO_MODE:
            log_message(app, "Cleaning up after error...")
            subprocess.run(["umount", "-R", "/mnt"], capture_output=True)
        GLib.idle_add(app.install_spinner.stop)
        GLib.idle_add(_handle_installation_error, app, str(e))


def _handle_installation_error(app, error_msg):
    """Save log to file, show error dialog, then quit the installer."""
    log_path = save_log_to_file(app)
    if log_path:
        message = (
            f"{error_msg}\n\n"
            f"The installation log has been saved to:\n{log_path}\n\n"
            "The installer will now close."
        )
    else:
        message = f"{error_msg}\n\nThe installer will now close."
    show_error(app, "Installation Failed", message)
    Gtk.main_quit()
    return False


def _finish_installation(app):
    """Stop spinner and move to completion page"""
    app.install_spinner.stop()
    app.notebook.next_page()
    return False
