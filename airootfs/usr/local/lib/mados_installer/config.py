"""
madOS Installer - Configuration constants
"""

# ========== DEMO MODE ==========
# Set to True to run installer in demo mode (no actual disk changes)
# Set to False for real installation
DEMO_MODE = False
# ================================

# Language to locale mapping
LOCALE_MAP = {
    'English': 'en_US.UTF-8',
    'Español': 'es_ES.UTF-8',
    'Français': 'fr_FR.UTF-8',
    'Deutsch': 'de_DE.UTF-8',
    '中文': 'zh_CN.UTF-8',
    '日本語': 'ja_JP.UTF-8'
}

# All available timezones
TIMEZONES = [
    'UTC',
    'Africa/Cairo', 'Africa/Johannesburg', 'Africa/Lagos', 'Africa/Nairobi',
    'America/Anchorage', 'America/Argentina/Buenos_Aires', 'America/Bogota',
    'America/Caracas', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Mexico_City', 'America/New_York', 'America/Santiago', 'America/Sao_Paulo',
    'America/Toronto', 'America/Vancouver',
    'Asia/Bangkok', 'Asia/Dubai', 'Asia/Hong_Kong', 'Asia/Jakarta', 'Asia/Kolkata',
    'Asia/Manila', 'Asia/Seoul', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Tokyo',
    'Australia/Melbourne', 'Australia/Perth', 'Australia/Sydney',
    'Europe/Amsterdam', 'Europe/Athens', 'Europe/Berlin', 'Europe/Brussels',
    'Europe/Budapest', 'Europe/Dublin', 'Europe/Istanbul', 'Europe/Lisbon',
    'Europe/London', 'Europe/Madrid', 'Europe/Moscow', 'Europe/Paris',
    'Europe/Rome', 'Europe/Stockholm', 'Europe/Vienna', 'Europe/Warsaw',
    'Pacific/Auckland', 'Pacific/Fiji', 'Pacific/Honolulu'
]

# Nord color palette
NORD_POLAR_NIGHT = {
    'nord0': '#2E3440',
    'nord1': '#3B4252',
    'nord2': '#434C5E',
    'nord3': '#4C566A'
}

NORD_SNOW_STORM = {
    'nord4': '#D8DEE9',
    'nord5': '#E5E9F0',
    'nord6': '#ECEFF4'
}

NORD_FROST = {
    'nord7': '#8FBCBB',
    'nord8': '#88C0D0',
    'nord9': '#81A1C1',
    'nord10': '#5E81AC'
}

NORD_AURORA = {
    'nord11': '#BF616A',
    'nord12': '#D08770',
    'nord13': '#EBCB8B',
    'nord14': '#A3BE8C',
    'nord15': '#B48EAD'
}

# Phase 1 packages: core system packages (categorisation only — ALL packages
# are included in the live ISO and copied to the target via rsync during
# installation; no packages are downloaded during Phase 1).
PACKAGES_PHASE1 = [
    'base', 'base-devel', 'linux', 'linux-firmware', 'intel-ucode', 'amd-ucode',
    'grub', 'efibootmgr', 'os-prober', 'dosfstools', 'sbctl',
    'networkmanager', 'sudo', 'zsh', 'curl', 'iwd',
    'earlyoom', 'zram-generator',
    'plymouth',
    'greetd', 'greetd-regreet', 'cage',
    'sway', 'swaybg', 'foot', 'xorg-xwayland',
    'hyprland',
    'mesa',
    'python', 'python-gobject', 'gtk3',
    'nodejs', 'npm',
]

# Phase 2 packages: desktop and application packages (categorisation only —
# these are also included in the live ISO and copied via rsync, so they are
# already present on the installed system after Phase 1).
# NOTE: GPU compute packages (nvidia-utils, cuda, rocm-*) are NOT here;
# they are tracked separately in GPU_COMPUTE_PACKAGES because they are too
# large for the ISO and are only downloaded on first boot when matching
# hardware is detected.
PACKAGES_PHASE2 = [
    'swayidle', 'swaylock', 'waybar', 'wofi', 'mako',
    'chromium', 'code', 'vim', 'nano', 'git', 'htop', 'fastfetch', 'openssh', 'wget', 'jq',
    'grim', 'slurp', 'wl-clipboard', 'xdg-desktop-portal-wlr',
    'xdg-desktop-portal-hyprland',
    'bluez', 'bluez-utils',
    'pipewire', 'pipewire-pulse', 'pipewire-alsa', 'wireplumber',
    'alsa-utils', 'pavucontrol',
    'intel-media-driver', 'vulkan-intel', 'mesa-utils',
    'xf86-video-amdgpu', 'vulkan-radeon',
    'xf86-video-nouveau',
    'ttf-jetbrains-mono-nerd', 'noto-fonts-emoji',
    'pcmanfm', 'gvfs', 'tumbler', 'ffmpegthumbnailer', 'lxappearance',
    'brightnessctl',
    'python-cairo', 'gdk-pixbuf2', 'rsync',
    # Reproductores multimedia
    'mpv',
    'fftw', 'chafa', 'taglib', 'faad2', 'opus', 'opusfile', 'libvorbis', 'libogg',
    # madOS Native Apps Dependencies
    'python-pillow', 'poppler-glib',
    'gstreamer', 'gst-plugins-base', 'gst-plugins-good', 'gst-python',
    'gst-plugins-ugly', 'gst-plugins-bad', 'gst-libav', 'gst-plugin-gtk',
]

# Combined package list (all ISO packages in both categories)
PACKAGES = PACKAGES_PHASE1 + PACKAGES_PHASE2

# Paths to exclude when copying the live rootfs to the target via rsync.
# Virtual filesystems, caches, and archiso-specific content are skipped.
# Note: /tmp/* and /run/* are publicly writable directories excluded
# intentionally — they must not be copied to the installed system.
RSYNC_EXCLUDES = [
    '/dev/*',
    '/proc/*',
    '/sys/*',
    '/run/*',  # NOSONAR - rsync exclude pattern, not directory access
    '/tmp/*',  # NOSONAR - rsync exclude pattern, not directory access  # noqa: S5443
    '/mnt/*',
    '/var/cache/pacman/pkg/*',
    '/var/lib/pacman/sync/*',
    '/var/log/*',
    '/var/tmp/*',  # NOSONAR - rsync exclude pattern, not directory access
    '/lost+found',
    '/swapfile',
    '/etc/fstab',
    '/etc/machine-id',
]

# Archiso-specific packages to remove after copying the live rootfs.
# These provide initcpio hooks and configs only needed for the live ISO.
ARCHISO_PACKAGES = ['mkinitcpio-archiso']

# Locale to keyboard layout mapping for Sway/Hyprland
LOCALE_KB_MAP = {
    'en_US.UTF-8': 'us',
    'es_ES.UTF-8': 'es',
    'fr_FR.UTF-8': 'fr',
    'de_DE.UTF-8': 'de',
    'zh_CN.UTF-8': 'us',
    'ja_JP.UTF-8': 'jp',
}
