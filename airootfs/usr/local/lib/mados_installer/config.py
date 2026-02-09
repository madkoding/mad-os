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
    'earlyoom', 'zram-generator', 'iwd',
    'pipewire', 'pipewire-pulse', 'pipewire-alsa', 'wireplumber',
    'alsa-utils', 'pavucontrol',
    'intel-media-driver', 'vulkan-intel', 'mesa-utils',
    'ttf-jetbrains-mono-nerd', 'noto-fonts-emoji',
    'pcmanfm', 'lxappearance', 'plymouth',
    'grub', 'efibootmgr', 'os-prober', 'dosfstools', 'sbctl', 'networkmanager', 'sudo',
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

# ── Optional software definitions ────────────────────────────────────────────
# Each item: key, display name, short description, pacman packages,
# post-install shell commands (run in chroot), systemd services to enable,
# whether it's already included in the base install.

OPTIONAL_DEV_LANGUAGES = [
    {'key': 'nodejs', 'name': 'Node.js', 'desc': 'JavaScript/TypeScript runtime (included)',
     'packages': [], 'post_install': [], 'services': [], 'included': True},
    {'key': 'php', 'name': 'PHP', 'desc': 'PHP 8.x + Composer',
     'packages': ['php', 'composer'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'elixir', 'name': 'Elixir', 'desc': 'Functional language on Erlang VM',
     'packages': ['elixir'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'java', 'name': 'Java (OpenJDK)', 'desc': 'JDK + Maven',
     'packages': ['jdk-openjdk', 'maven'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'c_cpp', 'name': 'C / C++', 'desc': 'GCC, Clang, CMake, GDB',
     'packages': ['gcc', 'cmake', 'gdb', 'clang'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'csharp', 'name': 'C# / .NET', 'desc': '.NET SDK',
     'packages': ['dotnet-sdk'], 'post_install': [], 'services': [], 'included': False},
]

OPTIONAL_SERVERS = [
    {'key': 'apache', 'name': 'Apache', 'desc': 'Apache HTTP Server',
     'packages': ['apache'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'nginx', 'name': 'Nginx', 'desc': 'High-performance web server',
     'packages': ['nginx'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'postgresql', 'name': 'PostgreSQL', 'desc': 'Advanced relational database',
     'packages': ['postgresql'], 'post_install': [], 'services': ['postgresql'], 'included': False},
    {'key': 'mariadb', 'name': 'MariaDB', 'desc': 'MySQL-compatible database',
     'packages': ['mariadb'], 'post_install': ['mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql || true'],
     'services': ['mariadb'], 'included': False},
    {'key': 'redis', 'name': 'Redis', 'desc': 'In-memory key-value store',
     'packages': ['redis'], 'post_install': [], 'services': ['redis'], 'included': False},
]

OPTIONAL_CONTAINERS = [
    {'key': 'docker', 'name': 'Docker', 'desc': 'Container runtime + Compose',
     'packages': ['docker', 'docker-compose', 'docker-buildx'], 'post_install': [],
     'services': ['docker'], 'included': False},
    {'key': 'kubernetes', 'name': 'Kubernetes', 'desc': 'kubectl CLI tool',
     'packages': ['kubectl'], 'post_install': [], 'services': [], 'included': False},
]

OPTIONAL_EDITORS = [
    {'key': 'vscode', 'name': 'VS Code', 'desc': 'Visual Studio Code (included)',
     'packages': [], 'post_install': [], 'services': [], 'included': True},
    {'key': 'neovim', 'name': 'Neovim', 'desc': 'Hyperextensible Vim-based editor',
     'packages': ['neovim'], 'post_install': [], 'services': [], 'included': False},
    {'key': 'emacs', 'name': 'Emacs', 'desc': 'Extensible text editor',
     'packages': ['emacs-nox'], 'post_install': [], 'services': [], 'included': False},
]

OPTIONAL_AI_TOOLS = [
    {'key': 'claude_code', 'name': 'Claude Code', 'desc': 'AI assistant by Anthropic (included)',
     'packages': [], 'post_install': [], 'services': [], 'included': True},
    {'key': 'ollama', 'name': 'Ollama', 'desc': 'Run LLMs locally (Llama, Mistral, etc.)',
     'packages': [], 'post_install': ['curl -fsSL https://ollama.ai/install.sh | sh || true'],
     'services': ['ollama'], 'included': False},
    {'key': 'opencode', 'name': 'OpenCode', 'desc': 'Open-source AI coding assistant',
     'packages': [], 'post_install': ['npm install -g opencode || true'],
     'services': [], 'included': False},
    {'key': 'openclaw', 'name': 'OpenClaw', 'desc': 'AI-powered code analysis tool',
     'packages': ['python-pip'], 'post_install': ['pip install openclaw || true'],
     'services': [], 'included': False},
    {'key': 'aider', 'name': 'Aider', 'desc': 'AI pair programming in terminal',
     'packages': ['python-pip'], 'post_install': ['pip install aider-chat || true'],
     'services': [], 'included': False},
]
