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

# Packages to install with pacstrap
PACKAGES = [
    'base', 'base-devel', 'linux', 'linux-firmware', 'intel-ucode', 'amd-ucode',
    'sway', 'swaybg', 'swayidle', 'swaylock', 'waybar', 'wofi', 'mako', 'xorg-xwayland',
    'foot', 'chromium', 'code', 'vim', 'nano', 'git', 'htop', 'openssh', 'wget', 'jq',
    'grim', 'slurp', 'wl-clipboard', 'xdg-desktop-portal-wlr',
    'earlyoom', 'zram-generator', 'iwd', 'pipewire', 'pipewire-pulse', 'wireplumber',
    'intel-media-driver', 'vulkan-intel', 'mesa-utils',
    'ttf-jetbrains-mono-nerd', 'papirus-icon-theme', 'noto-fonts-emoji', 'noto-fonts-cjk',
    'pcmanfm', 'lxappearance', 'plymouth',
    'grub', 'efibootmgr', 'os-prober', 'dosfstools', 'networkmanager', 'sudo',
    'brightnessctl',
    'nodejs', 'npm', 'python', 'python-gobject', 'gtk3', 'rsync'
]

# Locale to keyboard layout mapping for Sway
LOCALE_KB_MAP = {
    'en_US.UTF-8': 'us',
    'es_ES.UTF-8': 'es',
    'fr_FR.UTF-8': 'fr',
    'de_DE.UTF-8': 'de',
    'zh_CN.UTF-8': 'us',
    'ja_JP.UTF-8': 'jp',
}
