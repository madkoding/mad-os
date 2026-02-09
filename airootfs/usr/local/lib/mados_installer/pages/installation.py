"""
madOS Installer - Installation progress page and install logic
"""

import os
import re
import subprocess
import time
import threading

from gi.repository import Gtk, GLib

from ..config import DEMO_MODE, PACKAGES, NORD_FROST, LOCALE_KB_MAP
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

    # Log viewer
    log_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    log_card.get_style_context().add_class('content-card')
    log_card.set_margin_top(8)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_min_content_height(120)
    scrolled.set_max_content_height(180)

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


def on_start_installation(app):
    """Start the installation process"""
    app.notebook.next_page()
    app.install_spinner.start()

    thread = threading.Thread(target=_run_installation, args=(app,))
    thread.daemon = True
    thread.start()


def _run_installation(app):
    """Perform the actual installation (runs in background thread)"""
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
            subprocess.run(f'swapoff {disk}* 2>/dev/null || true', shell=True)
            subprocess.run(f'umount -l {disk}* 2>/dev/null || true', shell=True)
            subprocess.run(f'swapoff {disk}p* 2>/dev/null || true', shell=True)
            subprocess.run(f'umount -l {disk}p* 2>/dev/null || true', shell=True)
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

        # Step 4: Install base system
        set_progress(app, 0.25, "Installing base system (this may take a while)...")
        log_message(app, "Installing base system...")

        # Build package list with conditional CJK fonts
        packages = list(PACKAGES)
        if data['locale'] in ('zh_CN.UTF-8', 'ja_JP.UTF-8'):
            packages.append('noto-fonts-cjk')
            log_message(app, "Adding CJK fonts for selected locale...")

        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating pacstrap with packages:")
            for i, pkg in enumerate(packages):
                progress = 0.25 + (0.23 * (i + 1) / len(packages))
                set_progress(app, progress, f"Installing {pkg}...")
                log_message(app, f"[DEMO] Installing {pkg}...")
                time.sleep(0.2)
            time.sleep(0.5)
        else:
            _run_pacstrap_with_progress(app, packages)

        # Step 5: Generate fstab
        set_progress(app, 0.50, "Generating filesystem table...")
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

        # Step 6: Configure system
        set_progress(app, 0.55, "Configuring system...")
        log_message(app, "Configuring system...")

        config_script = _build_config_script(data)

        if DEMO_MODE:
            log_message(app, "[DEMO] Would write configuration script to /mnt/root/configure.sh")
            time.sleep(0.5)
            log_message(app, "[DEMO] Configuration would include:")
            log_message(app, "[DEMO]   - Timezone setup")
            log_message(app, "[DEMO]   - Locale generation")
            log_message(app, "[DEMO]   - Hostname configuration")
            log_message(app, "[DEMO]   - User creation")
            log_message(app, "[DEMO]   - Sudo setup")
            time.sleep(1)
        else:
            with open('/mnt/root/configure.sh', 'w') as f:
                f.write(config_script)
            subprocess.run(['chmod', '+x', '/mnt/root/configure.sh'], check=True)

            # Copy skel configs from live ISO to installed system
            log_message(app, "Copying desktop configuration files...")
            subprocess.run(['cp', '-a', '/etc/skel/.config', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/Pictures', '/mnt/etc/skel/'], check=False)
            subprocess.run(['cp', '-a', '/etc/skel/.bash_profile', '/mnt/etc/skel/'], check=False)

            # Copy custom fonts (DSEG7 for waybar LED theme)
            if os.path.isdir('/usr/share/fonts/dseg'):
                subprocess.run(['mkdir', '-p', '/mnt/usr/share/fonts/dseg'], check=False)
                subprocess.run(['cp', '-a', '/usr/share/fonts/dseg/', '/mnt/usr/share/fonts/'], check=False)

        set_progress(app, 0.70, "Applying configurations...")
        log_message(app, "Running configuration...")
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating arch-chroot configuration...")
            log_message(app, "[DEMO]   - Installing GRUB bootloader")
            time.sleep(0.5)
            log_message(app, "[DEMO]   - Enabling services (NetworkManager, earlyoom)...")
            time.sleep(0.5)
            log_message(app, "[DEMO]   - Configuring ZRAM...")
            time.sleep(0.5)
            log_message(app, "[DEMO]   - Setting up autologin...")
            time.sleep(0.5)
            log_message(app, "[DEMO]   - Installing Claude Code...")
            time.sleep(1)
        else:
            subprocess.run(['arch-chroot', '/mnt', '/root/configure.sh'], check=True)

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
            log_message(app, "\n[OK] Demo installation completed successfully!")
            log_message(app, "\n[DEMO] No actual changes were made to your system.")
            log_message(app, "[DEMO] Set DEMO_MODE = False for real installation.")
        else:
            log_message(app, "\n[OK] Installation completed successfully!")

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



def _run_pacstrap_with_progress(app, packages):
    """Run pacstrap while parsing output to update progress bar and log"""
    total_packages = len(packages)
    installed_count = 0
    current_pkg = ""

    # Progress range: 0.25 to 0.48 for pacstrap
    progress_start = 0.25
    progress_end = 0.48

    proc = subprocess.Popen(
        ['pacstrap', '/mnt'] + packages,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Patterns to detect package installation progress from pacman output
    pkg_pattern = re.compile(r'installing\s+(\S+)', re.IGNORECASE)
    downloading_pattern = re.compile(r'downloading\s+(\S+)', re.IGNORECASE)
    resolving_pattern = re.compile(r'resolving dependencies|looking for conflicting', re.IGNORECASE)
    total_pattern = re.compile(r'Packages\s+\((\d+)\)', re.IGNORECASE)

    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue

        # Try to detect total package count from pacman
        total_match = total_pattern.search(line)
        if total_match:
            total_packages = int(total_match.group(1))
            log_message(app, f"Total packages to install: {total_packages}")

        # Detect individual package installations
        pkg_match = pkg_pattern.search(line)
        if pkg_match:
            current_pkg = pkg_match.group(1)
            installed_count += 1
            progress = progress_start + (progress_end - progress_start) * (installed_count / total_packages)
            progress = min(progress, progress_end)
            set_progress(app, progress, f"Installing {current_pkg} ({installed_count}/{total_packages})...")
            log_message(app, f"  Installing {current_pkg}...")
            continue

        # Show download progress
        dl_match = downloading_pattern.search(line)
        if dl_match:
            log_message(app, f"  Downloading {dl_match.group(1)}...")
            continue

        # Show resolving phase
        if resolving_pattern.search(line):
            log_message(app, line.strip())
            continue

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, 'pacstrap')

    set_progress(app, progress_end, "Base system installed")
    log_message(app, f"Base system installed ({installed_count} packages)")


def _build_config_script(data):
    """Build the chroot configuration shell script"""
    disk = data['disk']
    return f'''#!/bin/bash
set -e

# Timezone
ln -sf /usr/share/zoneinfo/{data['timezone']} /etc/localtime
hwclock --systohc 2>/dev/null || true

# Locale
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
echo "{data['locale']} UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG={data['locale']}" > /etc/locale.conf

# Hostname
echo "{data['hostname']}" > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   {data['hostname']}.localdomain {data['hostname']}
EOF

# User
useradd -m -G wheel,audio,video,storage -s /bin/bash {data['username']}
echo '{data['username']}:{_escape_shell(data['password'])}' | chpasswd

# Sudo
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
echo "{data['username']} ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/claude-nopasswd
chmod 440 /etc/sudoers.d/claude-nopasswd

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

# Configure GRUB
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg
if [ ! -f /boot/grub/grub.cfg ]; then
    echo "ERROR: grub.cfg was not generated!"
    exit 1
fi

# Rebuild initramfs
mkinitcpio -P

# Lock root account (security: users should use sudo)
passwd -l root

# Services
systemctl enable NetworkManager
systemctl enable systemd-resolved
systemctl enable earlyoom
systemctl enable systemd-timesyncd

# Enable PipeWire audio for all user sessions (socket-activated)
systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service

# --- Non-critical section: errors below should not abort installation ---
set +e

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

# Autologin
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\\\u' --noclear --autologin {data['username']} %I \\$TERM
EOF

# Copy configs
su - {data['username']} -c "mkdir -p ~/.config/{{sway,waybar,foot,wofi,alacritty}}"
su - {data['username']} -c "mkdir -p ~/Pictures/{{Wallpapers,Screenshots}}"
cp -r /etc/skel/.config/* /home/{data['username']}/.config/ 2>/dev/null || true
cp -r /etc/skel/Pictures/* /home/{data['username']}/Pictures/ 2>/dev/null || true
chown -R {data['username']}:{data['username']} /home/{data['username']}

# Set keyboard layout in Sway config based on locale
KB_LAYOUT="{LOCALE_KB_MAP.get(data['locale'], 'us')}"
if [ -f /home/{data['username']}/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /home/{data['username']}/.config/sway/config
elif [ -f /etc/skel/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /etc/skel/.config/sway/config
fi

# Ensure .bash_profile from skel was copied correctly
if [ ! -f /home/{data['username']}/.bash_profile ]; then
    cp /etc/skel/.bash_profile /home/{data['username']}/.bash_profile 2>/dev/null || true
fi
chown {data['username']}:{data['username']} /home/{data['username']}/.bash_profile

# Install Claude Code globally (non-fatal if no network)
echo "Installing Claude Code..."
if npm install -g @anthropic-ai/claude-code; then
    echo "Claude Code installed successfully"
else
    echo "Warning: Could not install Claude Code during installation."
    echo "It will be installed automatically on first boot if network is available."
fi

# Create first-boot service to install Claude Code if not present
cat > /etc/systemd/system/setup-claude-code.service <<'EOFSVC'
[Unit]
Description=Install Claude Code if not already present
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/usr/bin/claude

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=HOME=/root
ExecStart=/bin/bash -c 'npm install -g @anthropic-ai/claude-code && echo "Claude Code installed successfully" || echo "Failed to install Claude Code"'
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOFSVC
systemctl enable setup-claude-code.service
'''
