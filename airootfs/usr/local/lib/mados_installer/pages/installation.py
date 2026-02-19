"""
madOS Installer - Installation progress page and install logic
"""

import glob as globmod
import os
import re
import subprocess
import time
import threading

from gi.repository import Gtk, GLib

from ..config import DEMO_MODE, PACKAGES, PACKAGES_PHASE1, PACKAGES_PHASE2, NORD_FROST, LOCALE_KB_MAP, TIMEZONES, LOCALE_MAP
from ..utils import log_message, set_progress, show_error


def _escape_shell(s):
    """Escape a string for safe use inside single quotes in shell"""
    return s.replace("'", "'\\''")
from .base import create_page_header


def create_installation_page(app):
    """Installation progress page with spinner, progress bar and log"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class('page-container')
    page.set_valign(Gtk.Align.CENTER)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_top(10)
    content.set_margin_bottom(14)

    # Spinner
    app.install_spinner = Gtk.Spinner()
    app.install_spinner.get_style_context().add_class('install-spinner')
    app.install_spinner.set_halign(Gtk.Align.CENTER)
    app.install_spinner.set_margin_top(8)
    content.pack_start(app.install_spinner, False, False, 0)

    # Title
    title = Gtk.Label()
    title.set_markup(f'<span size="15000" weight="bold">{app.t("installing")}</span>')
    title.set_halign(Gtk.Align.CENTER)
    content.pack_start(title, False, False, 0)

    # Status
    app.status_label = Gtk.Label()
    app.status_label.set_markup(
        f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{app.t("preparing")}</span>'
    )
    app.status_label.set_halign(Gtk.Align.CENTER)
    content.pack_start(app.status_label, False, False, 0)

    # Progress bar
    app.progress_bar = Gtk.ProgressBar()
    app.progress_bar.set_show_text(True)
    app.progress_bar.set_margin_top(4)
    app.progress_bar.set_margin_start(16)
    app.progress_bar.set_margin_end(16)
    content.pack_start(app.progress_bar, False, False, 0)

    # Log toggle link
    app.log_toggle = Gtk.EventBox()
    app.log_toggle.set_halign(Gtk.Align.CENTER)
    app.log_toggle.set_margin_top(8)
    toggle_label = Gtk.Label()
    toggle_label.set_markup(
        f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("show_log")}</span>'
    )
    toggle_label.get_style_context().add_class('log-toggle')
    app.log_toggle.add(toggle_label)
    app.log_toggle.connect('button-press-event', lambda w, e: _toggle_log(app))
    content.pack_start(app.log_toggle, False, False, 0)

    # Log viewer (hidden by default)
    log_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    log_card.get_style_context().add_class('content-card')
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
        # show() bypasses no_show_all; then show children that were never shown
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
    """Perform Phase 1 installation (runs in background thread).

    Phase 1 (from USB): partition, format, install minimal packages, configure
    bootloader and essential services, set up first-boot service for Phase 2.

    Phase 2 (first boot from installed disk): handled by mados-first-boot.sh
    which installs remaining packages, desktop config, and services.
    """
    try:
        data = app.install_data
        disk = data['disk']
        separate_home = data['separate_home']
        disk_size_gb = data['disk_size_gb']

        # Step 1: Partition
        set_progress(app, 0.05, "Partitioning disk...")
        log_message(app, f"Partitioning {disk}...")
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating unmount/swapoff...")
            time.sleep(0.3)
            log_message(app, "[DEMO] Simulating wipefs...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Simulating parted mklabel gpt...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Simulating parted mkpart bios_boot 1MiB-2MiB...")
            time.sleep(0.3)
            log_message(app, "[DEMO] Simulating parted set bios_grub on...")
            time.sleep(0.3)
            log_message(app, "[DEMO] Simulating parted mkpart EFI 2MiB-1GiB...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Simulating parted set esp on...")
            time.sleep(0.5)
        else:
            log_message(app, f"Unmounting existing partitions on {disk}...")
            for part in globmod.glob(f'{disk}[0-9]*') + globmod.glob(f'{disk}p[0-9]*'):
                subprocess.run(['swapoff', part], stderr=subprocess.DEVNULL, check=False)
                subprocess.run(['umount', '-l', part], stderr=subprocess.DEVNULL, check=False)
            time.sleep(1)
            # Thorough disk cleanup: remove GPT/MBR structures + all filesystem signatures
            subprocess.run(['sgdisk', '--zap-all', disk], check=False)
            subprocess.run(['wipefs', '-a', '-f', disk], check=True)
            subprocess.run(['parted', '-s', disk, 'mklabel', 'gpt'], check=True)
            # BIOS boot partition (required by grub-install --target=i386-pc on GPT disks)
            subprocess.run(['parted', '-s', disk, 'mkpart', 'bios_boot', '1MiB', '2MiB'], check=True)
            subprocess.run(['parted', '-s', disk, 'set', '1', 'bios_grub', 'on'], check=True)
            # EFI System Partition for UEFI boot
            subprocess.run(['parted', '-s', disk, 'mkpart', 'EFI', 'fat32', '2MiB', '1GiB'], check=True)
            subprocess.run(['parted', '-s', disk, 'set', '2', 'esp', 'on'], check=True)

        if separate_home:
            if disk_size_gb < 128:
                if DEMO_MODE:
                    log_message(app, "[DEMO] Simulating parted mkpart root 1GiB-51GiB...")
                    time.sleep(0.5)
                    log_message(app, "[DEMO] Simulating parted mkpart home 51GiB-100%...")
                    time.sleep(0.5)
                else:
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '51GiB'], check=True)
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'home', 'ext4', '51GiB', '100%'], check=True)
            else:
                if DEMO_MODE:
                    log_message(app, "[DEMO] Simulating parted mkpart root 1GiB-61GiB...")
                    time.sleep(0.5)
                    log_message(app, "[DEMO] Simulating parted mkpart home 61GiB-100%...")
                    time.sleep(0.5)
                else:
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '61GiB'], check=True)
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'home', 'ext4', '61GiB', '100%'], check=True)
        else:
            if DEMO_MODE:
                log_message(app, "[DEMO] Simulating parted mkpart root 1GiB-100%...")
                time.sleep(0.5)
            else:
                subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '100%'], check=True)

        if not DEMO_MODE:
            # Force kernel to re-read partition table and wait for device nodes
            log_message(app, "Waiting for partition devices...")
            subprocess.run(['partprobe', disk], check=False)
            subprocess.run(['udevadm', 'settle', '--timeout=10'], check=False)
            time.sleep(2)
        else:
            time.sleep(0.5)

        # Partition naming (NVMe/MMC use 'p' separator)
        if 'nvme' in disk or 'mmcblk' in disk:
            part_prefix = f"{disk}p"
        else:
            part_prefix = disk

        # Partition 1 = BIOS boot (no filesystem), Partition 2 = EFI, Partition 3 = root, Partition 4 = home
        boot_part = f"{part_prefix}2"
        root_part = f"{part_prefix}3"
        home_part = f"{part_prefix}4" if separate_home else None

        # Step 2: Format
        set_progress(app, 0.15, "Formatting partitions...")
        log_message(app, "Formatting partitions...")
        if DEMO_MODE:
            log_message(app, f"[DEMO] Simulating mkfs.fat {boot_part}...")
            time.sleep(0.5)
            log_message(app, f"[DEMO] Simulating mkfs.ext4 {root_part}...")
            time.sleep(0.5)
            if separate_home:
                log_message(app, f"[DEMO] Simulating mkfs.ext4 {home_part}...")
                time.sleep(0.5)
        else:
            # Verify partition device nodes exist before formatting
            for part_name, part_dev in [('EFI', boot_part), ('root', root_part)] + ([('home', home_part)] if separate_home else []):
                if not os.path.exists(part_dev):
                    raise RuntimeError(f"Partition device {part_dev} ({part_name}) does not exist! Partitioning may have failed.")
            subprocess.run(['mkfs.fat', '-F32', boot_part], check=True)
            subprocess.run(['mkfs.ext4', '-F', root_part], check=True)
            if separate_home:
                subprocess.run(['mkfs.ext4', '-F', home_part], check=True)

        # Step 3: Mount
        set_progress(app, 0.20, "Mounting filesystems...")
        log_message(app, "Mounting filesystems...")
        if DEMO_MODE:
            log_message(app, f"[DEMO] Simulating mount {root_part} /mnt...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Simulating mkdir /mnt/boot...")
            time.sleep(0.3)
            log_message(app, f"[DEMO] Simulating mount {boot_part} /mnt/boot...")
            time.sleep(0.5)
            if separate_home:
                log_message(app, "[DEMO] Simulating mkdir /mnt/home...")
                time.sleep(0.3)
                log_message(app, f"[DEMO] Simulating mount {home_part} /mnt/home...")
                time.sleep(0.5)
        else:
            subprocess.run(['mount', root_part, '/mnt'], check=True)
            subprocess.run(['mkdir', '-p', '/mnt/boot'], check=True)
            subprocess.run(['mount', boot_part, '/mnt/boot'], check=True)
            if separate_home:
                subprocess.run(['mkdir', '-p', '/mnt/home'], check=True)
                subprocess.run(['mount', home_part, '/mnt/home'], check=True)

        # Step 4: Prepare package manager and install Phase 1 packages
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating pacman keyring check...")
            set_progress(app, 0.21, "Checking package manager keyring...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Simulating database sync...")
            set_progress(app, 0.23, "Synchronizing package databases...")
            time.sleep(0.5)
        else:
            _prepare_pacman(app)

        # Phase 1: only install essential packages (remaining installed on first boot)
        packages = list(PACKAGES_PHASE1)

        # Step 4a: Download Phase 1 packages in groups (progress stays alive)
        set_progress(app, 0.25, "Downloading packages...")
        log_message(app, f"Downloading {len(packages)} essential packages (Phase 1)...")

        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating package downloads in groups:")
            group_size = 10
            for i in range(0, len(packages), group_size):
                group = packages[i:i + group_size]
                end = min(i + group_size, len(packages))
                progress = 0.25 + (0.11 * end / len(packages))
                set_progress(app, progress, f"Downloading packages ({end}/{len(packages)})...")
                for pkg in group:
                    log_message(app, f"[DEMO] Downloading {pkg}...")
                time.sleep(0.3)
            time.sleep(0.3)
        else:
            _download_packages_with_progress(app, packages)

        # Step 4b: Install Phase 1 packages (already cached from download step)
        set_progress(app, 0.36, "Installing base system...")
        log_message(app, "Installing base system (Phase 1)...")

        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating pacstrap with cached packages:")
            for i, pkg in enumerate(packages):
                progress = 0.36 + (0.12 * (i + 1) / len(packages))
                set_progress(app, progress, f"Installing {pkg}...")
                log_message(app, f"[DEMO] Installing {pkg}...")
                time.sleep(0.1)
            time.sleep(0.3)
        else:
            _run_pacstrap_with_progress(app, packages)

        # Step 5: Generate fstab
        set_progress(app, 0.49, "Generating filesystem table...")
        log_message(app, "Generating fstab...")
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating genfstab -U /mnt...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Would write fstab to /mnt/etc/fstab")
            time.sleep(0.5)
        else:
            result = subprocess.run(['genfstab', '-U', '/mnt'], capture_output=True, text=True, check=True)
            with open('/mnt/etc/fstab', 'w') as f:
                f.write(result.stdout)

        # Step 6: Configure system (Phase 1 only)
        set_progress(app, 0.50, "Preparing system configuration...")
        log_message(app, "Preparing Phase 1 configuration...")

        config_script = _build_config_script(data)

        if DEMO_MODE:
            log_message(app, "[DEMO] Would write configuration script to /mnt/root/configure.sh")
            time.sleep(0.5)
            log_message(app, "[DEMO] Configuration would include:")
            log_message(app, "[DEMO]   - Timezone setup")
            log_message(app, "[DEMO]   - Locale generation")
            log_message(app, "[DEMO]   - Hostname configuration")
            log_message(app, "[DEMO]   - User creation")
            log_message(app, "[DEMO]   - GRUB bootloader")
            log_message(app, "[DEMO]   - First-boot service for Phase 2")
            time.sleep(1)
        else:
            fd = os.open('/mnt/root/configure.sh', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700)
            with os.fdopen(fd, 'w') as f:
                f.write(config_script)

            # Copy Plymouth assets
            set_progress(app, 0.51, "Copying boot splash assets...")
            log_message(app, "Copying Plymouth boot splash assets...")
            subprocess.run(['mkdir', '-p', '/mnt/usr/share/plymouth/themes/mados'], check=True)
            subprocess.run(['cp', '/usr/share/plymouth/themes/mados/logo.png',
                            '/mnt/usr/share/plymouth/themes/mados/logo.png'], check=False)
            subprocess.run(['cp', '/usr/share/plymouth/themes/mados/dot.png',
                            '/mnt/usr/share/plymouth/themes/mados/dot.png'], check=False)

            # Copy skel configs from live ISO to installed system
            set_progress(app, 0.52, "Copying desktop configuration files...")
            log_message(app, "Copying desktop configuration files...")
            subprocess.run(['cp', '-a', '/etc/skel/.config', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/Pictures', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/.bash_profile', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/.zshrc', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/.bashrc', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/.gtkrc-2.0', '/mnt/etc/skel/'], check=False)

            # Copy system-wide GTK settings for dark theme
            subprocess.run(['mkdir', '-p', '/mnt/etc/gtk-3.0'], check=False)
            subprocess.run(['cp', '-a', '/etc/gtk-3.0/settings.ini', '/mnt/etc/gtk-3.0/'], check=False)

            # Copy Nordic GTK theme from live ISO if installed
            if os.path.isdir('/usr/share/themes/Nordic'):
                log_message(app, "Copying Nordic GTK theme from live environment...")
                subprocess.run(['mkdir', '-p', '/mnt/usr/share/themes'], check=False)
                subprocess.run(['cp', '-a', '/usr/share/themes/Nordic',
                                '/mnt/usr/share/themes/'], check=False)

            # Copy Oh My Zsh from live ISO if already installed
            if os.path.isdir('/etc/skel/.oh-my-zsh'):
                log_message(app, "Copying Oh My Zsh from live environment...")
                subprocess.run(['cp', '-a', '/etc/skel/.oh-my-zsh', '/mnt/etc/skel/'], check=False)

            # Copy OpenCode binary from live ISO if already installed
            if os.path.isfile('/usr/local/bin/opencode'):
                log_message(app, "Copying OpenCode from live environment...")
                subprocess.run(['cp', '-a', '/usr/local/bin/opencode',
                                '/mnt/usr/local/bin/opencode'], check=False)

            # Copy kew binary from live ISO if already installed
            if os.path.isfile('/usr/local/bin/kew'):
                log_message(app, "Copying kew from live environment...")
                subprocess.run(['cp', '-a', '/usr/local/bin/kew',
                                '/mnt/usr/local/bin/kew'], check=False)

            # Copy setup-ohmyzsh.sh script for first-boot fallback
            set_progress(app, 0.53, "Copying system scripts...")
            log_message(app, "Copying system scripts...")
            subprocess.run(['mkdir', '-p', '/mnt/usr/local/bin'], check=False)
            subprocess.run(['cp', '-a', '/usr/local/bin/setup-ohmyzsh.sh',
                            '/mnt/usr/local/bin/setup-ohmyzsh.sh'], check=False)

            # Copy detect-legacy-hardware script for software rendering fallback
            subprocess.run(['cp', '-a', '/usr/local/bin/detect-legacy-hardware',
                            '/mnt/usr/local/bin/detect-legacy-hardware'], check=False)

            # Copy cage-greeter, sway-session, hyprland-session and select-compositor wrappers
            subprocess.run(['cp', '-a', '/usr/local/bin/cage-greeter',
                            '/mnt/usr/local/bin/cage-greeter'], check=False)
            subprocess.run(['cp', '-a', '/usr/local/bin/sway-session',
                            '/mnt/usr/local/bin/sway-session'], check=False)
            subprocess.run(['cp', '-a', '/usr/local/bin/hyprland-session',
                            '/mnt/usr/local/bin/hyprland-session'], check=False)
            subprocess.run(['cp', '-a', '/usr/local/bin/select-compositor',
                            '/mnt/usr/local/bin/select-compositor'], check=False)

            # Copy audio quality auto-detection script
            subprocess.run(['cp', '-a', '/usr/local/bin/mados-audio-quality.sh',
                            '/mnt/usr/local/bin/mados-audio-quality.sh'], check=False)

            # Copy custom Python application launchers
            for launcher in ['mados-photo-viewer', 'mados-pdf-viewer',
                             'mados-equalizer',
                             'mados-debug']:
                subprocess.run(['cp', '-a', f'/usr/local/bin/{launcher}',
                                f'/mnt/usr/local/bin/{launcher}'], check=False)

            # Copy custom Python application libraries
            subprocess.run(['mkdir', '-p', '/mnt/usr/local/lib'], check=False)
            for lib in ['mados_photo_viewer', 'mados_pdf_viewer',
                        'mados_equalizer']:
                if os.path.isdir(f'/usr/local/lib/{lib}'):
                    subprocess.run(['cp', '-a', f'/usr/local/lib/{lib}',
                                    '/mnt/usr/local/lib/'], check=False)

            # Ensure copied scripts are executable in the installed system
            for script in ['detect-legacy-hardware', 'cage-greeter', 'sway-session',
                           'hyprland-session', 'select-compositor',
                           'mados-photo-viewer', 'mados-pdf-viewer',
                           'mados-equalizer',
                           'mados-debug']:
                subprocess.run(['chmod', '+x', f'/mnt/usr/local/bin/{script}'], check=False)

            # Copy madOS session desktop files for ReGreet
            set_progress(app, 0.54, "Copying session files...")
            log_message(app, "Copying session files...")
            subprocess.run(['mkdir', '-p', '/mnt/usr/share/wayland-sessions'], check=False)
            subprocess.run(['cp', '-a', '/usr/share/wayland-sessions/sway.desktop',
                            '/mnt/usr/share/wayland-sessions/sway.desktop'], check=False)
            if os.path.isfile('/usr/share/wayland-sessions/hyprland.desktop'):
                subprocess.run(['cp', '-a', '/usr/share/wayland-sessions/hyprland.desktop',
                                '/mnt/usr/share/wayland-sessions/hyprland.desktop'], check=False)

            # Copy greeter wallpaper (same as session wallpaper)
            subprocess.run(['mkdir', '-p', '/mnt/usr/share/backgrounds'], check=False)
            subprocess.run(['cp', '-a', '/usr/share/backgrounds/mad-os-wallpaper.jpg',
                            '/mnt/usr/share/backgrounds/mad-os-wallpaper.jpg'], check=False)

            # Copy custom application desktop entries
            subprocess.run(['mkdir', '-p', '/mnt/usr/share/applications'], check=False)
            for desktop in ['mados-photo-viewer.desktop', 'mados-pdf-viewer.desktop',
                            'mados-equalizer.desktop']:
                if os.path.isfile(f'/usr/share/applications/{desktop}'):
                    subprocess.run(['cp', '-a', f'/usr/share/applications/{desktop}',
                                    f'/mnt/usr/share/applications/{desktop}'], check=False)

            # Copy custom fonts (DSEG7 for waybar LED theme)
            if os.path.isdir('/usr/share/fonts/dseg'):
                subprocess.run(['mkdir', '-p', '/mnt/usr/share/fonts/dseg'], check=False)
                subprocess.run(['cp', '-a', '/usr/share/fonts/dseg/', '/mnt/usr/share/fonts/'], check=False)

        # Step 7: Run Phase 1 chroot configuration
        set_progress(app, 0.55, "Applying configurations...")
        log_message(app, "Running Phase 1 configuration...")
        if DEMO_MODE:
            demo_steps = [
                (0.58, "Installing GRUB bootloader"),
                (0.64, "Enabling essential services..."),
                (0.70, "Rebuilding initramfs..."),
                (0.76, "Setting up first-boot service..."),
                (0.82, "Preparing Phase 2 setup..."),
            ]
            log_message(app, "[DEMO] Simulating arch-chroot configuration...")
            for progress, desc in demo_steps:
                set_progress(app, progress, desc)
                log_message(app, f"[DEMO]   - {desc}")
                time.sleep(0.5)
        else:
            _run_chroot_with_progress(app)

        set_progress(app, 0.90, "Cleaning up...")
        log_message(app, "Cleaning up...")
        if DEMO_MODE:
            log_message(app, "[DEMO] Would remove configuration script")
            time.sleep(0.3)
            log_message(app, "[DEMO] Would unmount filesystems")
            time.sleep(0.5)
        else:
            subprocess.run(['rm', '/mnt/root/configure.sh'], check=True)
            # Sync and unmount all filesystems cleanly
            log_message(app, "Syncing and unmounting filesystems...")
            subprocess.run(['sync'], check=False)
            subprocess.run(['umount', '-R', '/mnt'], check=False)

        set_progress(app, 1.0, "Installation complete!")
        if DEMO_MODE:
            log_message(app, "\n[OK] Demo Phase 1 installation completed successfully!")
            log_message(app, "\n[DEMO] No actual changes were made to your system.")
            log_message(app, "[DEMO] Set DEMO_MODE = False for real installation.")
        else:
            log_message(app, "\n[OK] Phase 1 installation completed successfully!")
            log_message(app, "Remaining packages and configuration will be installed on first boot.")

        GLib.idle_add(_finish_installation, app)

    except Exception as e:
        log_message(app, f"\n[ERROR] {str(e)}")
        # Cleanup: try to unmount filesystems on failure
        if not DEMO_MODE:
            log_message(app, "Cleaning up after error...")
            subprocess.run(['umount', '-R', '/mnt'], capture_output=True)
        GLib.idle_add(app.install_spinner.stop)
        GLib.idle_add(show_error, app, "Installation Failed", str(e))


def _finish_installation(app):
    """Stop spinner and move to completion page"""
    app.install_spinner.stop()
    app.notebook.next_page()
    return False



def _prepare_pacman(app):
    """Ensure pacman keyring is ready and databases are synced before pacstrap.

    On the live ISO, pacman-init.service initializes the keyring on a tmpfs at
    boot.  On slow hardware (Intel Atom, limited entropy) this can take 10-20
    minutes.  If pacstrap starts before it finishes, it blocks silently while
    waiting for the keyring — the user sees no progress at all.

    This function:
    1. Waits for pacman-init.service to finish (with progress feedback).
    2. Syncs the package databases so pacstrap can skip that step.
    """
    # --- Wait for pacman-init.service ---
    set_progress(app, 0.21, "Checking package manager keyring...")
    log_message(app, "Checking pacman keyring status...")

    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'pacman-init.service'],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
    except Exception:
        status = 'unknown'

    if status == 'activating':
        log_message(app, "  Pacman keyring is still being initialized, waiting...")
        log_message(app, "  (This can take several minutes on slow hardware)")
        poll_count = 0
        while True:
            time.sleep(5)
            poll_count += 1
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', 'pacman-init.service'],
                    capture_output=True, text=True
                )
                status = result.stdout.strip()
            except Exception:
                status = 'unknown'
                break
            if status != 'activating':
                break
            # Show periodic feedback so the user knows it's not stuck
            if poll_count % 6 == 0:  # every ~30 seconds
                elapsed = poll_count * 5
                log_message(app, f"  Still initializing keyring... ({elapsed}s elapsed)")

    if status == 'failed':
        log_message(app, "  Keyring service failed, re-initializing manually...")
        subprocess.run(['pacman-key', '--init'], check=True)
        subprocess.run(['pacman-key', '--populate'], check=True)

    log_message(app, "  Pacman keyring is ready")

    # --- Sync package databases ---
    set_progress(app, 0.23, "Synchronizing package databases...")
    log_message(app, "Synchronizing package databases...")
    proc = subprocess.Popen(
        ['pacman', '-Sy', '--noconfirm'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if line:
            log_message(app, f"  {line}")
    proc.wait()
    if proc.returncode != 0:
        log_message(app, "  Warning: database sync returned non-zero, pacstrap will retry")
    else:
        log_message(app, "  Package databases synchronized")


def _download_packages_with_progress(app, packages):
    """Pre-download packages in small groups so the progress bar stays alive.

    Downloads packages to the host pacman cache using ``pacman -Sw``.
    pacstrap will then find them already cached and skip re-downloading,
    which keeps the subsequent install phase fast and responsive.

    The progress bar advances from 0.25 to 0.36 during this phase.
    """
    total = len(packages)
    progress_start = 0.25
    progress_end = 0.36
    group_size = 10

    downloaded = 0
    for i in range(0, total, group_size):
        group = packages[i:i + group_size]
        end = min(i + group_size, total)
        progress = progress_start + (progress_end - progress_start) * (i / total)
        set_progress(app, progress, f"Downloading packages ({downloaded}/{total})...")

        group_preview = ', '.join(group[:3]) + ('...' if len(group) > 3 else '')
        log_message(app, f"  Downloading group: {group_preview}")

        proc = subprocess.Popen(
            ['pacman', '-Sw', '--noconfirm'] + group,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            if not line:
                continue
            # Skip noisy progress-bar lines (e.g. "  100%  [####...]" or "---")
            if re.match(r'^\s*\d+%\s*\[|^\s*[-#]+\s*$', line):
                continue
            log_message(app, f"    {line}")

        proc.wait()
        if proc.returncode != 0:
            log_message(app, f"  Warning: download failed for group {i // group_size + 1} "
                             f"(exit code {proc.returncode}), pacstrap will retry")

        downloaded = end
        progress = progress_start + (progress_end - progress_start) * (downloaded / total)
        set_progress(app, progress, f"Downloading packages ({downloaded}/{total})...")

    set_progress(app, progress_end, "All packages downloaded")
    log_message(app, f"  All {total} packages downloaded to cache")


def _run_pacstrap_with_progress(app, packages):
    """Run pacstrap while parsing output to update progress bar and log"""
    total_packages = len(packages)
    installed_count = 0

    # Progress range: 0.36 to 0.48 for pacstrap (packages already cached)
    progress_start = 0.36
    progress_end = 0.48

    proc = subprocess.Popen(
        ['pacstrap', '/mnt'] + packages,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Patterns to detect package installation progress from pacman output
    # Match "(N/M) installing pkg-name" format used by pacman
    numbered_pkg_pattern = re.compile(r'\((\d+)/(\d+)\)\s+installing\s+(\S+)', re.IGNORECASE)
    pkg_pattern = re.compile(r'installing\s+(\S+)', re.IGNORECASE)
    downloading_pattern = re.compile(r'downloading\s+(\S+)', re.IGNORECASE)
    resolving_pattern = re.compile(r'resolving dependencies|looking for conflicting', re.IGNORECASE)
    total_pattern = re.compile(r'Packages\s+\((\d+)\)', re.IGNORECASE)
    # Detect section markers like ":: Processing package changes..."
    section_pattern = re.compile(r'^::')
    # Detect hook lines like "(1/5) Arming ConditionNeedsUpdate..."
    hook_pattern = re.compile(r'^\((\d+)/(\d+)\)\s+(?!installing)', re.IGNORECASE)
    # Detect early-phase output: keyring checks, integrity verification, syncing
    keyring_pattern = re.compile(
        r'checking keyring|checking keys|checking integrity|'
        r'checking package integrity|checking available disk|'
        r'synchronizing package|loading package|'
        r'checking for file conflicts|upgrading|retrieving',
        re.IGNORECASE
    )
    # Skip noisy progress-bar lines (e.g. "  100%  [####...]")
    progress_bar_pattern = re.compile(r'^\s*\d+%\s*\[|^\s*[-#]+\s*$|^$')

    # Use readline() instead of iterator to avoid Python's internal
    # read-ahead buffering which delays output on piped subprocesses
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            continue

        # Try to detect total package count from pacman
        total_match = total_pattern.search(line)
        if total_match:
            total_packages = int(total_match.group(1))
            log_message(app, f"Total packages to install: {total_packages}")
            continue

        # Detect "(N/M) installing pkg" format (most reliable)
        numbered_match = numbered_pkg_pattern.search(line)
        if numbered_match:
            installed_count = int(numbered_match.group(1))
            total_from_line = int(numbered_match.group(2))
            current_pkg = numbered_match.group(3).rstrip('.')
            if total_from_line > 0:
                total_packages = total_from_line
            progress = progress_start + (progress_end - progress_start) * (installed_count / max(total_packages, 1))
            progress = min(progress, progress_end)
            set_progress(app, progress, f"Installing packages ({installed_count}/{total_packages})...")
            log_message(app, f"  Installing {current_pkg}...")
            continue

        # Fallback: detect "installing pkg" without numbering
        pkg_match = pkg_pattern.search(line)
        if pkg_match:
            current_pkg = pkg_match.group(1).rstrip('.')
            installed_count += 1
            progress = progress_start + (progress_end - progress_start) * (installed_count / max(total_packages, 1))
            progress = min(progress, progress_end)
            set_progress(app, progress, f"Installing packages ({installed_count}/{total_packages})...")
            log_message(app, f"  Installing {current_pkg}...")
            continue

        # Show download progress
        dl_match = downloading_pattern.search(line)
        if dl_match:
            log_message(app, f"  Downloading {dl_match.group(1)}...")
            continue

        # Show resolving phase
        if resolving_pattern.search(line):
            log_message(app, f"  {line.strip()}")
            continue

        # Show section markers (e.g. ":: Processing package changes...")
        if section_pattern.search(line):
            log_message(app, line.strip())
            continue

        # Show post-transaction hooks
        if hook_pattern.search(line):
            log_message(app, f"  {line.strip()}")
            continue

        # Show early-phase output (keyring, integrity, sync, etc.)
        if keyring_pattern.search(line):
            set_progress(app, progress_start, f"{line.strip()}...")
            log_message(app, f"  {line.strip()}")
            continue

        # Skip noisy progress-bar lines
        if progress_bar_pattern.search(line):
            continue

        # Fallback: log any other non-empty output so nothing appears silent
        log_message(app, f"  {line.strip()}")

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, 'pacstrap')

    set_progress(app, progress_end, "Base system installed")
    log_message(app, f"Base system installed ({installed_count} packages)")


def _run_chroot_with_progress(app):
    """Run arch-chroot configure.sh while streaming output and updating progress"""
    # Progress range: 0.55 to 0.90 for chroot configuration
    progress_start = 0.55
    progress_end = 0.90

    proc = subprocess.Popen(
        ['arch-chroot', '/mnt', '/root/configure.sh'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Pattern to detect progress markers: [PROGRESS N/M] description
    progress_pattern = re.compile(r'\[PROGRESS\s+(\d+)/(\d+)\]\s+(.*)')

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            continue

        # Check for progress markers
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

        # Log all other output
        log_message(app, f"  {line}")

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, 'arch-chroot')

    set_progress(app, progress_end, "System configured")
    log_message(app, "System configuration complete")


def _build_config_script(data):
    """Build the Phase 1 chroot configuration shell script.

    Phase 1 handles: timezone, locale, hostname, user account, GRUB bootloader,
    Plymouth, initramfs, essential services, system optimizations, desktop
    environment basics, and sets up the first-boot service for Phase 2.
    """
    disk = data['disk']

    # Validate timezone against whitelist to prevent path traversal
    timezone = data['timezone']
    if timezone not in TIMEZONES:
        raise ValueError(f"Invalid timezone: {timezone}")

    # Validate locale against whitelist
    locale = data['locale']
    valid_locales = list(LOCALE_MAP.values())
    if locale not in valid_locales:
        raise ValueError(f"Invalid locale: {locale}")

    # Validate disk path (must be a simple block device path like /dev/sda or /dev/nvme0n1)
    if not re.match(r'^/dev/[a-zA-Z0-9]+$', disk):
        raise ValueError(f"Invalid disk path: {disk}")

    # Validate username (defense-in-depth, also checked in user.py)
    username = data['username']
    if not re.match(r'^[a-z_][a-z0-9_-]*$', username):
        raise ValueError(f"Invalid username: {username}")

    # Build the Phase 2 first-boot script content
    first_boot_script = _build_first_boot_script(data)

    return f'''#!/bin/bash
set -e

echo "[PROGRESS 1/9] Setting timezone and locale..."
# Timezone
ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc 2>/dev/null || true

# Locale
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
echo "{locale} UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG={locale}" > /etc/locale.conf

echo '[PROGRESS 2/9] Creating user account...'
# Hostname
echo '{_escape_shell(data['hostname'])}' > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   {_escape_shell(data['hostname'])}.localdomain {_escape_shell(data['hostname'])}
EOF

# User
useradd -m -G wheel,audio,video,storage -s /bin/zsh {username}
echo '{username}:{_escape_shell(data['password'])}' | chpasswd

# Sudo
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
echo "{username} ALL=(ALL:ALL) NOPASSWD: /usr/bin/npm,/usr/bin/node,/usr/bin/opencode,/usr/local/bin/opencode,/usr/bin/pacman,/usr/bin/systemctl" > /etc/sudoers.d/opencode-nopasswd
chmod 440 /etc/sudoers.d/opencode-nopasswd

echo '[PROGRESS 3/9] Installing GRUB bootloader...'
# GRUB - Auto-detect UEFI or BIOS
if [ -d /sys/firmware/efi ]; then
    echo "==> Detected UEFI boot mode"
    # Ensure efivarfs is mounted for NVRAM access
    if ! mountpoint -q /sys/firmware/efi/efivars 2>/dev/null; then
        mount -t efivarfs efivarfs /sys/firmware/efi/efivars 2>/dev/null || true
    fi

    # Disable GRUB's shim_lock verifier so it works without shim
    echo 'GRUB_DISABLE_SHIM_LOCK=true' >> /etc/default/grub

    # Install GRUB with custom bootloader-id (writes NVRAM entry)
    if ! grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=madOS --recheck 2>&1; then
        echo "WARN: grub-install bootloader-id failed (NVRAM may be read-only)"
    fi
    # Also install to the standard fallback path EFI/BOOT/BOOTX64.EFI for maximum compatibility
    if ! grub-install --target=x86_64-efi --efi-directory=/boot --removable --recheck 2>&1; then
        echo "ERROR: GRUB UEFI --removable install failed!"
        exit 1
    fi
    # Verify EFI binary exists
    if [ ! -f /boot/EFI/BOOT/BOOTX64.EFI ]; then
        echo "ERROR: /boot/EFI/BOOT/BOOTX64.EFI was not created!"
        exit 1
    fi

    # --- Secure Boot support via sbctl ---
    SECURE_BOOT=0
    if [ -f /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c ]; then
        SB_VAL=$(od -An -t u1 -j4 -N1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | tr -d ' ')
        [ "$SB_VAL" = "1" ] && SECURE_BOOT=1
    fi

    if [ "$SECURE_BOOT" = "1" ]; then
        echo "==> Secure Boot is ENABLED – setting up sbctl signing"

        # Create signing keys
        sbctl create-keys 2>/dev/null || echo "WARN: sbctl keys may already exist"

        # Try to enroll keys (works only in Setup Mode)
        SETUP_MODE=0
        if [ -f /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c ]; then
            SM_VAL=$(od -An -t u1 -j4 -N1 /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | tr -d ' ')
            [ "$SM_VAL" = "1" ] && SETUP_MODE=1
        fi

        if [ "$SETUP_MODE" = "1" ]; then
            echo "==> Firmware is in Setup Mode – enrolling Secure Boot keys"
            sbctl enroll-keys --microsoft 2>&1 || echo "WARN: Could not enroll keys automatically"
        else
            echo "==> Firmware is NOT in Setup Mode"
            echo "    After first reboot, enter UEFI firmware settings and either:"
            echo "    1) Disable Secure Boot, or"
            echo "    2) Put firmware in Setup Mode, reboot to madOS, then run: sudo sbctl enroll-keys --microsoft"
        fi

        # Sign all EFI binaries and kernel (with -s to save in sbctl database for re-signing)
        for f in /boot/EFI/BOOT/BOOTX64.EFI /boot/EFI/madOS/grubx64.efi /boot/vmlinuz-linux; do
            if [ -f "$f" ]; then
                echo "    Signing $f"
                sbctl sign -s "$f" 2>&1 || echo "WARN: Could not sign $f"
            fi
        done

        # Create pacman hook to auto-sign after kernel/grub updates
        mkdir -p /etc/pacman.d/hooks
        cat > /etc/pacman.d/hooks/99-sbctl-sign.hook <<'EOFHOOK'
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = linux
Target = linux-lts
Target = linux-zen
Target = grub

[Action]
Description = Signing EFI binaries for Secure Boot...
When = PostTransaction
Exec = /usr/bin/sbctl sign-all
Depends = sbctl
EOFHOOK
    else
        echo "==> Secure Boot is disabled – skipping sbctl signing"
    fi
else
    echo "==> Detected BIOS boot mode"
    # BIOS boot uses the bios_grub partition on GPT disk
    if ! grub-install --target=i386-pc --recheck {disk} 2>&1; then
        echo "ERROR: GRUB BIOS install failed!"
        exit 1
    fi
fi

echo '[PROGRESS 4/9] Configuring GRUB...'
# Configure GRUB
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg
if [ ! -f /boot/grub/grub.cfg ]; then
    echo "ERROR: grub.cfg was not generated!"
    exit 1
fi

echo '[PROGRESS 5/9] Setting up Plymouth boot splash...'
# Plymouth theme
mkdir -p /usr/share/plymouth/themes/mados
cat > /usr/share/plymouth/themes/mados/mados.plymouth <<EOFPLY
[Plymouth Theme]
Name=madOS
Description=madOS boot splash with Nord theme
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/mados
ScriptFile=/usr/share/plymouth/themes/mados/mados.script
EOFPLY

cat > /usr/share/plymouth/themes/mados/mados.script <<'EOFSCRIPT'
Window.SetBackgroundTopColor(0.18, 0.20, 0.25);
Window.SetBackgroundBottomColor(0.13, 0.15, 0.19);
logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
logo.sprite.SetX(Window.GetWidth() / 2 - logo.image.GetWidth() / 2);
logo.sprite.SetY(Window.GetHeight() / 2 - logo.image.GetHeight() / 2 - 50);
logo.sprite.SetZ(10);
logo.sprite.SetOpacity(1);
NUM_DOTS = 8;
SPINNER_RADIUS = 25;
spinner_x = Window.GetWidth() / 2;
spinner_y = Window.GetHeight() / 2 + logo.image.GetHeight() / 2;
dot_image = Image("dot.png");
for (i = 0; i < NUM_DOTS; i++) {{
    dot[i].sprite = Sprite(dot_image);
    dot[i].sprite.SetZ(10);
    angle = i * 2 * 3.14159 / NUM_DOTS;
    dot[i].sprite.SetX(spinner_x + SPINNER_RADIUS * Math.Sin(angle) - dot_image.GetWidth() / 2);
    dot[i].sprite.SetY(spinner_y - SPINNER_RADIUS * Math.Cos(angle) - dot_image.GetHeight() / 2);
    dot[i].sprite.SetOpacity(0.2);
}}
frame = 0;
fun refresh_callback() {{
    frame++;
    active_dot = Math.Int(frame / 4) % NUM_DOTS;
    for (i = 0; i < NUM_DOTS; i++) {{
        dist = active_dot - i;
        if (dist < 0) dist = dist + NUM_DOTS;
        if (dist == 0) opacity = 1.0;
        else if (dist == 1) opacity = 0.7;
        else if (dist == 2) opacity = 0.45;
        else if (dist == 3) opacity = 0.25;
        else opacity = 0.12;
        dot[i].sprite.SetOpacity(opacity);
    }}
    pulse = Math.Abs(Math.Sin(frame * 0.02)) * 0.08 + 0.92;
    logo.sprite.SetOpacity(pulse);
}}
Plymouth.SetRefreshFunction(refresh_callback);
fun display_normal_callback(text) {{}}
fun display_message_callback(text) {{}}
Plymouth.SetDisplayNormalFunction(display_normal_callback);
Plymouth.SetMessageFunction(display_message_callback);
fun quit_callback() {{
    for (i = 0; i < NUM_DOTS; i++) {{ dot[i].sprite.SetOpacity(0); }}
    logo.sprite.SetOpacity(1);
}}
Plymouth.SetQuitFunction(quit_callback);
EOFSCRIPT

# Configure Plymouth
plymouth-set-default-theme mados 2>/dev/null || true
mkdir -p /etc/plymouth
cat > /etc/plymouth/plymouthd.conf <<EOFPLYCONF
[Daemon]
Theme=mados
ShowDelay=0
DeviceTimeout=8
EOFPLYCONF

echo '[PROGRESS 6/9] Rebuilding initramfs (this takes a while)...'
# Rebuild initramfs with plymouth hook
sed -i 's/^HOOKS=.*/HOOKS=(base udev plymouth autodetect modconf kms block filesystems keyboard fsck)/' /etc/mkinitcpio.conf
mkinitcpio -P

echo '[PROGRESS 7/9] Enabling essential services...'
# Lock root account (security: users should use sudo)
passwd -l root

# Essential services only (remaining services enabled by first-boot)
systemctl enable NetworkManager
systemctl enable systemd-resolved
systemctl enable earlyoom
systemctl enable systemd-timesyncd
systemctl enable greetd
systemctl enable iwd

echo '[PROGRESS 8/9] Applying system configuration...'
# --- Non-critical section: errors below should not abort installation ---
set +e

# madOS branding - custom os-release
cat > /etc/os-release <<EOF
NAME="madOS"
PRETTY_NAME="madOS (Arch Linux)"
ID=mados
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://github.com/madkoding/mad-os"
DOCUMENTATION_URL="https://wiki.archlinux.org/"
SUPPORT_URL="https://bbs.archlinux.org/"
BUG_REPORT_URL="https://gitlab.archlinux.org/groups/archlinux/-/issues"
PRIVACY_POLICY_URL="https://terms.archlinux.org/docs/privacy-policy/"
LOGO=archlinux-logo
EOF

# Configure NetworkManager to use iwd as Wi-Fi backend
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/wifi-backend.conf <<EOF
[device]
wifi.backend=iwd
EOF

# Kernel optimizations
cat > /etc/sysctl.d/99-extreme-low-ram.conf <<EOF
vm.vfs_cache_pressure = 200
vm.swappiness = 5
vm.dirty_ratio = 5
vm.dirty_background_ratio = 3
vm.min_free_kbytes = 16384
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
net.core.rmem_max = 262144
net.core.wmem_max = 262144
EOF

# ZRAM
cat > /etc/systemd/zram-generator.conf <<EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF

# greetd + ReGreet greeter configuration
mkdir -p /etc/greetd
cat > /etc/greetd/config.toml <<'EOFGREETD'
[terminal]
vt = 1

[default_session]
command = "/usr/local/bin/cage-greeter"
user = "greeter"
EOFGREETD

# ReGreet configuration
cat > /etc/greetd/regreet.toml <<'EOFREGREET'
[background]
path = "/usr/share/backgrounds/mad-os-wallpaper.jpg"
fit = "Cover"

[env]
LIBSEAT_BACKEND = "logind"

[GTK]
application_prefer_dark_theme = true

[commands]
reboot = [ "systemctl", "reboot" ]
poweroff = [ "systemctl", "poweroff" ]
EOFREGREET

# Ensure greetd config directory and files are accessible by greeter user
chown -R greeter:greeter /etc/greetd
chmod 755 /etc/greetd
chmod 644 /etc/greetd/config.toml /etc/greetd/regreet.toml

# Ensure greeter user has video and input group access for cage
usermod -aG video,input greeter 2>/dev/null || echo "Note: greeter user group modification skipped"

# Create regreet cache directory and ensure greeter home is writable
mkdir -p /var/cache/regreet
chown greeter:greeter /var/cache/regreet
chmod 750 /var/cache/regreet
mkdir -p /var/lib/greetd
chown greeter:greeter /var/lib/greetd

# Ensure greetd starts after systemd-logind and doesn't conflict with getty on VT1
mkdir -p /etc/systemd/system/greetd.service.d
cat > /etc/systemd/system/greetd.service.d/override.conf <<'EOFOVERRIDE'
[Unit]
After=systemd-logind.service
Wants=systemd-logind.service
Conflicts=getty@tty1.service
After=getty@tty1.service
EOFOVERRIDE

# Copy configs to user home
su - {username} -c "mkdir -p ~/.config/{{sway,hypr,waybar,foot,wofi,gtk-3.0,gtk-4.0}}"
su - {username} -c "mkdir -p ~/{{Documents,Downloads,Music,Videos,Desktop,Templates,Public}}"
su - {username} -c "mkdir -p ~/Pictures/{{Wallpapers,Screenshots}}"
cp -r /etc/skel/.config/* /home/{username}/.config/ 2>/dev/null || true
cp -r /etc/skel/Pictures/* /home/{username}/Pictures/ 2>/dev/null || true
cp /etc/skel/.gtkrc-2.0 /home/{username}/.gtkrc-2.0 2>/dev/null || true
chown -R {username}:{username} /home/{username}

# Set keyboard layout in Sway and Hyprland configs based on locale
KB_LAYOUT="{LOCALE_KB_MAP.get(locale, 'us')}"
if [ -f /home/{username}/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /home/{username}/.config/sway/config
elif [ -f /etc/skel/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /etc/skel/.config/sway/config
fi
if [ -f /home/{username}/.config/hypr/hyprland.conf ]; then
    sed -i "s/kb_layout = es/kb_layout = $KB_LAYOUT/" /home/{username}/.config/hypr/hyprland.conf
elif [ -f /etc/skel/.config/hypr/hyprland.conf ]; then
    sed -i "s/kb_layout = es/kb_layout = $KB_LAYOUT/" /etc/skel/.config/hypr/hyprland.conf
fi

# Ensure .bash_profile from skel was copied correctly
if [ ! -f /home/{username}/.bash_profile ]; then
    cp /etc/skel/.bash_profile /home/{username}/.bash_profile 2>/dev/null || true
fi
chown {username}:{username} /home/{username}/.bash_profile

# Copy .zshrc for zsh users
if [ -f /etc/skel/.zshrc ]; then
    cp /etc/skel/.zshrc /home/{username}/.zshrc 2>/dev/null || true
    chown {username}:{username} /home/{username}/.zshrc
fi

echo '[PROGRESS 9/9] Setting up first-boot service for Phase 2...'
# Write the Phase 2 first-boot script
mkdir -p /usr/local/bin
cat > /usr/local/bin/mados-first-boot.sh <<'EOFFIRSTBOOT'
{first_boot_script}
EOFFIRSTBOOT
chmod 755 /usr/local/bin/mados-first-boot.sh

# Create the systemd service for Phase 2 first-boot setup
cat > /etc/systemd/system/mados-first-boot.service <<'EOFSVC'
[Unit]
Description=madOS First Boot Setup (Phase 2) - Install packages and configure system
After=network-online.target
Wants=network-online.target
ConditionPathExists=/usr/local/bin/mados-first-boot.sh

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/mados-first-boot.sh
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=1800

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable mados-first-boot.service
echo "Phase 2 first-boot service installed and enabled"
'''


def _build_first_boot_script(data):
    """Build the Phase 2 first-boot shell script.

    This script runs on the first boot from the installed disk. It installs
    remaining packages, configures audio/bluetooth/desktop services, installs
    Oh My Zsh and OpenCode, then disables itself.
    """
    username = data['username']
    locale = data['locale']

    # Build the Phase 2 package list as a shell array
    phase2_packages = list(PACKAGES_PHASE2)
    if locale in ('zh_CN.UTF-8', 'ja_JP.UTF-8'):
        phase2_packages.append('noto-fonts-cjk')

    packages_str = ' '.join(phase2_packages)

    return f'''#!/bin/bash
# madOS First Boot Setup (Phase 2)
# Installs remaining packages and configures services
# This script runs once on first boot and then disables itself
set -euo pipefail

LOG_TAG="mados-first-boot"
log() {{ echo "[Phase 2] $1"; systemd-cat -t "$LOG_TAG" printf "%s\\n" "$1" 2>/dev/null || true; }}

log "Starting madOS Phase 2 setup..."

# ── Step 1: Install remaining packages ──────────────────────────────────
log "Installing additional packages..."
PACKAGES=({packages_str})

# Sync databases and install Phase 2 packages in one step
if pacman -Syu --noconfirm --needed "${{PACKAGES[@]}}" 2>&1; then
    log "All Phase 2 packages installed successfully"
else
    log "Warning: Some packages may have failed to install"
fi

# ── Step 2: Enable additional services ──────────────────────────────────
log "Enabling additional services..."
systemctl enable bluetooth 2>/dev/null || true

# GPU Compute: Enable auto-detection and activation of CUDA/ROCm drivers
systemctl enable mados-gpu-compute.service 2>/dev/null || true

# Audio: Enable PipeWire for all user sessions (socket-activated)
systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service 2>/dev/null || true

# Audio: Create and enable ALSA unmute service
cat > /usr/local/bin/mados-audio-init.sh <<'EOFAUDIO'
#!/usr/bin/env bash
# mados-audio-init.sh - Unmute ALSA controls and set default volumes
set -euo pipefail
LOG_TAG="mados-audio-init"
log() {{ systemd-cat -t "$LOG_TAG" printf "%s\\n" "$1"; }}
get_card_indices() {{
    if [[ -f /proc/asound/cards ]]; then
        sed -n -e 's/^[[:space:]]*\\([0-9]\\+\\)[[:space:]].*/\\1/p' /proc/asound/cards
    fi
}}
set_control() {{ amixer -c "$1" set "$2" "$3" unmute 2>/dev/null || true; }}
mute_control() {{ amixer -c "$1" set "$2" "0%" mute 2>/dev/null || true; }}
switch_control() {{ amixer -c "$1" set "$2" "$3" 2>/dev/null || true; }}
init_card() {{
    local card="$1"
    log "Initializing audio on card $card"
    set_control "$card" "Master" "80%"
    set_control "$card" "Front" "80%"
    set_control "$card" "Master Mono" "80%"
    set_control "$card" "Master Digital" "80%"
    set_control "$card" "Playback" "80%"
    set_control "$card" "Headphone" "100%"
    set_control "$card" "Speaker" "80%"
    set_control "$card" "PCM" "80%"
    set_control "$card" "PCM,1" "80%"
    set_control "$card" "DAC" "80%"
    set_control "$card" "DAC,0" "80%"
    set_control "$card" "DAC,1" "80%"
    set_control "$card" "Digital" "80%"
    set_control "$card" "Wave" "80%"
    set_control "$card" "Music" "80%"
    set_control "$card" "AC97" "80%"
    set_control "$card" "Analog Front" "80%"
    set_control "$card" "Synth" "80%"
    switch_control "$card" "Master Playback Switch" "on"
    switch_control "$card" "Master Surround" "on"
    switch_control "$card" "Speaker" "on"
    switch_control "$card" "Headphone" "on"
    set_control "$card" "VIA DXS,0" "80%"
    set_control "$card" "VIA DXS,1" "80%"
    set_control "$card" "VIA DXS,2" "80%"
    set_control "$card" "VIA DXS,3" "80%"
    set_control "$card" "Dynamic Range Compression" "80%"
    mute_control "$card" "Mic"
    mute_control "$card" "Internal Mic"
    mute_control "$card" "Rear Mic"
    mute_control "$card" "IEC958"
    switch_control "$card" "IEC958 Capture Monitor" "off"
    switch_control "$card" "Headphone Jack Sense" "off"
    switch_control "$card" "Line Jack Sense" "off"
}}
log "Starting madOS audio initialization"
cards=$(get_card_indices)
if [[ -z "$cards" ]]; then log "No sound cards detected"; exit 0; fi
for card in $cards; do init_card "$card"; done
if command -v alsactl &>/dev/null && alsactl store 2>/dev/null; then log "ALSA state saved"; fi
log "Audio initialization complete"
EOFAUDIO
chmod 755 /usr/local/bin/mados-audio-init.sh

cat > /etc/systemd/system/mados-audio-init.service <<'EOFSVC'
[Unit]
Description=madOS Audio Initialization - Unmute ALSA Controls
Wants=systemd-udev-settle.service
After=systemd-udev-settle.service sound.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/mados-audio-init.sh

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable mados-audio-init.service 2>/dev/null || true

# Audio: Create and enable high-quality audio auto-detection service
cat > /etc/systemd/system/mados-audio-quality.service <<'EOFSVC'
[Unit]
Description=madOS Audio Quality Auto-Configuration
Documentation=man:pipewire(1)
Wants=systemd-udev-settle.service sound.target
After=systemd-udev-settle.service sound.target mados-audio-init.service
Before=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/mados-audio-quality.sh
Nice=-5

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable mados-audio-quality.service 2>/dev/null || true

# Audio: Set up user-level audio quality service
mkdir -p /home/{username}/.config/systemd/user/default.target.wants
cat > /home/{username}/.config/systemd/user/mados-audio-quality.service <<'EOFUSRSVC'
[Unit]
Description=madOS Audio Quality User Configuration
Documentation=man:pipewire(1)
Before=pipewire.service pipewire-pulse.service wireplumber.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/mados-audio-quality.sh

[Install]
WantedBy=default.target
EOFUSRSVC
ln -sf ../mados-audio-quality.service /home/{username}/.config/systemd/user/default.target.wants/mados-audio-quality.service
chown -R {username}:{username} /home/{username}/.config/systemd

# ── Step 3: Configure Chromium ──────────────────────────────────────────
log "Configuring Chromium..."
cat > /etc/chromium-flags.conf <<'EOFCHROMIUM'
# Wayland native support
--ozone-platform-hint=auto
--enable-features=WaylandWindowDecorations
# Disable Vulkan (not supported on Intel Atom / legacy GPUs)
--disable-vulkan
# Disable VA-API hardware video decode/encode (fails on Intel Atom)
--disable-features=VaapiVideoDecoder,VaapiVideoEncoder,UseChromeOSDirectVideoDecoder
# Memory optimizations for low-RAM systems
--renderer-process-limit=3
--disable-gpu-memory-buffer-compositor-resources
EOFCHROMIUM

# Chromium homepage policy
mkdir -p /etc/chromium/policies/managed
cat > /etc/chromium/policies/managed/mados-homepage.json <<'EOFPOLICY'
{{
  "HomepageLocation": "https://www.kodingvibes.com",
  "HomepageIsNewTabPage": true,
  "RestoreOnStartup": 4,
  "RestoreOnStartupURLs": ["https://www.kodingvibes.com"]
}}
EOFPOLICY

# ── Step 3b: Install Nordic GTK Theme ──────────────────────────────────
if [ -d /usr/share/themes/Nordic ]; then
    log "Nordic GTK theme already installed"
else
    log "Installing Nordic GTK theme..."
    if command -v git &>/dev/null; then
        if curl -sf --connect-timeout 5 https://github.com >/dev/null 2>&1; then
            NORDIC_TMP=$(mktemp -d)
            if git clone --depth=1 https://github.com/EliverLara/Nordic.git "$NORDIC_TMP/Nordic" 2>&1; then
                mkdir -p /usr/share/themes
                cp -a "$NORDIC_TMP/Nordic" /usr/share/themes/Nordic
                rm -rf /usr/share/themes/Nordic/.git /usr/share/themes/Nordic/.gitignore /usr/share/themes/Nordic/Art /usr/share/themes/Nordic/LICENSE /usr/share/themes/Nordic/README.md /usr/share/themes/Nordic/KDE /usr/share/themes/Nordic/Wallpaper
                log "Nordic GTK theme installed"
            else
                log "Warning: Failed to clone Nordic GTK theme"
            fi
            [ -n "$NORDIC_TMP" ] && rm -rf "$NORDIC_TMP"
        else
            log "No internet - Nordic GTK theme skipped"
        fi
    fi
fi

# ── Step 4: Install Oh My Zsh ──────────────────────────────────────────
log "Setting up Oh My Zsh..."
if [ ! -d /etc/skel/.oh-my-zsh ]; then
    if command -v git &>/dev/null; then
        if curl -sf --connect-timeout 5 https://github.com >/dev/null 2>&1; then
            git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git /etc/skel/.oh-my-zsh 2>&1 || true
            if [ -d /etc/skel/.oh-my-zsh ]; then
                log "Oh My Zsh installed to /etc/skel"
            fi
        else
            log "No internet - Oh My Zsh skipped"
        fi
    fi
fi

# Copy to user home if available
if [ -d /etc/skel/.oh-my-zsh ] && [ ! -d /home/{username}/.oh-my-zsh ]; then
    cp -a /etc/skel/.oh-my-zsh /home/{username}/.oh-my-zsh
    chown -R {username}:{username} /home/{username}/.oh-my-zsh
    log "Oh My Zsh copied to {username} home"
fi

# Oh My Zsh fallback service (for future users or if clone failed)
cat > /etc/systemd/system/setup-ohmyzsh.service <<'EOFSVC'
[Unit]
Description=Install Oh My Zsh if not already present
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/etc/skel/.oh-my-zsh

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/setup-ohmyzsh.sh
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable setup-ohmyzsh.service 2>/dev/null || true

# ── Step 5: Install OpenCode ─────────────────────────────────────────
log "Installing OpenCode..."
OPENCODE_INSTALL_DIR="/usr/local/bin"
export OPENCODE_INSTALL_DIR
# Method 1: curl install script (downloads binary directly, most reliable)
if curl -fsSL https://opencode.ai/install | bash; then
    if command -v opencode &>/dev/null; then
        log "OpenCode installed successfully"
    else
        log "Warning: curl install completed but opencode not found in PATH"
    fi
else
    log "Warning: curl install failed"
fi
# Method 2: npm fallback
if ! command -v opencode &>/dev/null; then
    if command -v npm &>/dev/null; then
        if npm install -g --unsafe-perm opencode-ai 2>&1; then
            log "OpenCode installed via npm"
        else
            log "Warning: npm install also failed"
        fi
    fi
fi

# Copy setup script for manual retry
cat > /usr/local/bin/setup-opencode.sh <<'EOFSETUP'
#!/bin/bash
OPENCODE_CMD="opencode"
INSTALL_DIR="/usr/local/bin"
if command -v "$OPENCODE_CMD" &>/dev/null; then
    echo "✓ OpenCode ya está instalado:"
    "$OPENCODE_CMD" --version 2>/dev/null || true
    exit 0
fi
if ! curl -sf --connect-timeout 5 https://opencode.ai/ >/dev/null 2>&1; then
    echo "⚠ No hay conexión a Internet."
    echo "  Conecta a la red y ejecuta de nuevo: sudo setup-opencode.sh"
    exit 0
fi
echo "Instalando OpenCode..."
if curl -fsSL https://opencode.ai/install | OPENCODE_INSTALL_DIR="$INSTALL_DIR" bash; then
    if command -v "$OPENCODE_CMD" &>/dev/null; then
        echo "✓ OpenCode instalado correctamente."
        "$OPENCODE_CMD" --version 2>/dev/null || true
        exit 0
    fi
fi
echo "⚠ Método curl falló, intentando con npm..."
if command -v npm &>/dev/null; then
    if npm install -g --unsafe-perm opencode-ai; then
        if command -v "$OPENCODE_CMD" &>/dev/null; then
            echo "✓ OpenCode instalado correctamente via npm."
            exit 0
        fi
    fi
fi
echo "⚠ No se pudo instalar OpenCode."
exit 0
EOFSETUP
chmod 755 /usr/local/bin/setup-opencode.sh

# OpenCode fallback service
cat > /etc/systemd/system/setup-opencode.service <<'EOFSVC'
[Unit]
Description=Install OpenCode if not already present
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=HOME=/root
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=/usr/local/bin/setup-opencode.sh
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable setup-opencode.service 2>/dev/null || true

# ── Step 5b: Install kew (terminal music player) ────────────────────
if command -v kew &>/dev/null; then
    log "kew already installed"
else
    log "Building kew from source..."
    KEW_BUILD_DIR=$(mktemp -d)
    if git clone --depth=1 https://github.com/ravachol/kew.git "$KEW_BUILD_DIR/kew" 2>&1; then
        cd "$KEW_BUILD_DIR/kew"
        if make -j"$(nproc)" 2>&1 && make install 2>&1; then
            log "kew installed from source"
        else
            log "Warning: Failed to build kew"
        fi
        cd /
    else
        log "Warning: Failed to clone kew"
    fi
    [ -n "$KEW_BUILD_DIR" ] && rm -rf "$KEW_BUILD_DIR"
fi

# ── Step 6: Install Ollama ───────────────────────────────────────────
log "Installing Ollama..."

# Method: curl install script (official installer from ollama.com)
if curl -fsSL https://ollama.com/install.sh | sh; then
    if command -v ollama &>/dev/null; then
        log "Ollama installed successfully"
    else
        log "Warning: curl install completed but ollama not found in PATH"
    fi
else
    log "Warning: Ollama install failed"
fi

# Copy setup script for manual retry
cat > /usr/local/bin/setup-ollama.sh <<'EOFSETUP'
#!/bin/bash
OLLAMA_CMD="ollama"
if command -v "$OLLAMA_CMD" &>/dev/null; then
    echo "✓ Ollama ya está instalado:"
    "$OLLAMA_CMD" --version 2>/dev/null || true
    exit 0
fi
if ! curl -sf --connect-timeout 5 https://ollama.com/ >/dev/null 2>&1; then
    echo "⚠ No hay conexión a Internet."
    echo "  Conecta a la red y ejecuta de nuevo: sudo setup-ollama.sh"
    exit 0
fi
echo "Instalando Ollama..."
if curl -fsSL https://ollama.com/install.sh | sh; then
    if command -v "$OLLAMA_CMD" &>/dev/null; then
        echo "✓ Ollama instalado correctamente."
        "$OLLAMA_CMD" --version 2>/dev/null || true
        exit 0
    fi
fi
echo "⚠ No se pudo instalar Ollama."
exit 0
EOFSETUP
chmod 755 /usr/local/bin/setup-ollama.sh

# Ollama fallback service
cat > /etc/systemd/system/setup-ollama.service <<'EOFSVC'
[Unit]
Description=Install Ollama if not already present
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=HOME=/root
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=/usr/local/bin/setup-ollama.sh
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable setup-ollama.service 2>/dev/null || true

# ── Step 7: Cleanup ─────────────────────────────────────────────────────
log "Phase 2 setup complete! Disabling first-boot service..."
systemctl disable mados-first-boot.service 2>/dev/null || true
rm -f /usr/local/bin/mados-first-boot.sh

log "madOS is fully configured. Enjoy!"
'''
