#!/bin/bash
# madOS Installer - TUI Edition
# An AI-orchestrated Arch Linux system with Claude Code
# Hardware: Intel Atom / 1.9GB RAM optimized

set -e

# Colors for dialog
export DIALOGRC="/tmp/.dialogrc"
cat > "$DIALOGRC" <<'EOF'
use_shadow = ON
use_colors = ON
screen_color = (WHITE,BLUE,ON)
shadow_color = (BLACK,BLACK,ON)
dialog_color = (BLACK,WHITE,OFF)
title_color = (BLUE,WHITE,ON)
border_color = (WHITE,WHITE,ON)
button_active_color = (WHITE,BLUE,ON)
button_inactive_color = (BLACK,WHITE,OFF)
button_key_active_color = (WHITE,RED,ON)
button_key_inactive_color = (RED,WHITE,OFF)
button_label_active_color = (YELLOW,BLUE,ON)
button_label_inactive_color = (BLACK,WHITE,ON)
inputbox_color = (BLACK,WHITE,OFF)
inputbox_border_color = (BLACK,WHITE,OFF)
searchbox_color = (BLACK,WHITE,OFF)
searchbox_title_color = (BLUE,WHITE,ON)
searchbox_border_color = (WHITE,WHITE,ON)
position_indicator_color = (BLUE,WHITE,ON)
menubox_color = (BLACK,WHITE,OFF)
menubox_border_color = (WHITE,WHITE,ON)
item_color = (BLACK,WHITE,OFF)
item_selected_color = (WHITE,BLUE,ON)
tag_color = (BLUE,WHITE,ON)
tag_selected_color = (YELLOW,BLUE,ON)
tag_key_color = (RED,WHITE,OFF)
tag_key_selected_color = (RED,BLUE,ON)
check_color = (BLACK,WHITE,OFF)
check_selected_color = (WHITE,BLUE,ON)
uarrow_color = (GREEN,WHITE,ON)
darrow_color = (GREEN,WHITE,ON)
itemhelp_color = (WHITE,BLACK,OFF)
form_active_text_color = (WHITE,BLUE,ON)
form_text_color = (WHITE,CYAN,ON)
form_item_readonly_color = (CYAN,WHITE,ON)
gauge_color = (BLUE,WHITE,ON)
EOF

DIALOG_HEIGHT=20
DIALOG_WIDTH=70

# Función de error
error_exit() {
    dialog --title "❌ Error" \
           --msgbox "\n$1\n\nPress OK to exit." 10 50
    clear
    exit 1
}

# Verificar root
if [[ $(id -u) != "0" ]]; then
    error_exit "This installer must be run as root.\n\nPlease use: sudo $0"
fi

# Pantalla de bienvenida
show_welcome() {
    dialog --title "Welcome to madOS Installer" \
           --colors \
           --yes-label "Install" \
           --no-label "Exit" \
           --yesno "\n\
\Z4╔═══════════════════════════════════════════════════╗\Zn
\Z4║                                                   ║\Zn
\Z4║\Zn     \Z1███╗   ███╗ █████╗ ██████╗  ██████╗ ███████╗\Zn    \Z4║\Zn
\Z4║\Zn     \Z1████╗ ████║██╔══██╗██╔══██╗██╔═══██╗██╔════╝\Zn    \Z4║\Zn
\Z4║\Zn     \Z1██╔████╔██║███████║██║  ██║██║   ██║███████╗\Zn    \Z4║\Zn
\Z4║\Zn     \Z1██║╚██╔╝██║██╔══██║██║  ██║██║   ██║╚════██║\Zn    \Z4║\Zn
\Z4║\Zn     \Z1██║ ╚═╝ ██║██║  ██║██████╔╝╚██████╔╝███████║\Zn    \Z4║\Zn
\Z4║\Zn     \Z1╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝\Zn    \Z4║\Zn
\Z4║                                                   ║\Zn
\Z4║\Zn         \Z6AI-Orchestrated Arch Linux System\Zn         \Z4║\Zn
\Z4║\Zn              \Z2Powered by Claude Code\Zn               \Z4║\Zn
\Z4║                                                   ║\Zn
\Z4╚═══════════════════════════════════════════════════╝\Zn

\Z7Optimized for:\Zn
  • Intel Atom / Low-RAM systems (1.9GB)
  • Sway Wayland compositor
  • AI-assisted system management
  • Developer-ready environment

\Z3Ready to install madOS?\Zn" 26 60

    if [ $? -ne 0 ]; then
        clear
        echo "Installation cancelled. Goodbye!"
        exit 0
    fi
}

# Selección de disco
select_disk() {
    # Obtener lista de discos
    mapfile -t disks < <(lsblk -d -n -o NAME,SIZE,TYPE | grep disk)

    if [ ${#disks[@]} -eq 0 ]; then
        error_exit "No disks found on this system."
    fi

    # Crear opciones para dialog
    disk_options=()
    for disk in "${disks[@]}"; do
        name=$(echo "$disk" | awk '{print $1}')
        size=$(echo "$disk" | awk '{print $2}')
        disk_options+=("$name" "$size")
    done

    DISK=$(dialog --stdout \
                  --title "💾 Disk Selection" \
                  --menu "\nSelect the disk where madOS will be installed.\n\n⚠️  WARNING: ALL DATA ON THE SELECTED DISK WILL BE ERASED!\n\nAvailable disks:" \
                  18 60 10 \
                  "${disk_options[@]}")

    if [ $? -ne 0 ] || [ -z "$DISK" ]; then
        clear
        echo "Installation cancelled."
        exit 0
    fi

    DISK="/dev/$DISK"
}

# Confirmación de disco
confirm_disk() {
    local disk_info=$(lsblk -o NAME,SIZE,TYPE,MODEL "$DISK" 2>/dev/null)

    dialog --title "⚠️  Final Warning" \
           --colors \
           --yes-label "ERASE & INSTALL" \
           --no-label "Go Back" \
           --defaultno \
           --yesno "\n\Z1ALL DATA ON THIS DISK WILL BE PERMANENTLY ERASED!\Zn\n\n\
Disk: \Z4$DISK\Zn\n\n\
$disk_info\n\n\
Partition layout:\n\
  • 1GB    - EFI System Partition\n\
  • 32GB   - Root filesystem (madOS)\n\
  • Rest   - Home partition (your data)\n\n\
\Z3Are you absolutely sure?\Zn" 22 65

    if [ $? -ne 0 ]; then
        return 1
    fi
    return 0
}

# Información del usuario
get_user_info() {
    USERNAME=$(dialog --stdout \
                      --title "👤 User Account" \
                      --inputbox "\nEnter your username:\n(lowercase, no spaces)" \
                      10 50)

    if [ $? -ne 0 ] || [ -z "$USERNAME" ]; then
        clear
        echo "Installation cancelled."
        exit 0
    fi

    # Validar username
    if ! [[ "$USERNAME" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
        dialog --msgbox "Invalid username. Use lowercase letters, numbers, - and _" 8 50
        get_user_info
        return
    fi

    PASSWORD=$(dialog --stdout \
                      --title "🔒 Password" \
                      --insecure \
                      --passwordbox "\nEnter password for $USERNAME:" \
                      10 50)

    if [ $? -ne 0 ] || [ -z "$PASSWORD" ]; then
        clear
        echo "Installation cancelled."
        exit 0
    fi

    PASSWORD2=$(dialog --stdout \
                       --title "🔒 Password Confirmation" \
                       --insecure \
                       --passwordbox "\nConfirm password:" \
                       10 50)

    if [ "$PASSWORD" != "$PASSWORD2" ]; then
        dialog --msgbox "Passwords do not match! Try again." 8 40
        get_user_info
        return
    fi

    HOSTNAME=$(dialog --stdout \
                      --title "🖥️  Hostname" \
                      --inputbox "\nEnter hostname for this computer:\n(e.g., mados-laptop)" \
                      10 50 \
                      "mados-$(tr -dc 'a-z0-9' < /dev/urandom | head -c 4)")

    if [ $? -ne 0 ] || [ -z "$HOSTNAME" ]; then
        clear
        echo "Installation cancelled."
        exit 0
    fi
}

# Configuración regional
get_locale_config() {
    TIMEZONE=$(dialog --stdout \
                      --title "🌍 Timezone" \
                      --menu "\nSelect your timezone:" \
                      15 60 8 \
                      "UTC" "Coordinated Universal Time" \
                      "America/Santiago" "Chile" \
                      "America/New_York" "US Eastern" \
                      "America/Los_Angeles" "US Pacific" \
                      "America/Chicago" "US Central" \
                      "Europe/London" "United Kingdom" \
                      "Europe/Paris" "Central Europe" \
                      "Asia/Tokyo" "Japan")

    [ $? -ne 0 ] && TIMEZONE="UTC"

    LOCALE=$(dialog --stdout \
                    --title "🌐 Language" \
                    --menu "\nSelect system language:" \
                    12 60 5 \
                    "en_US.UTF-8" "English (US)" \
                    "es_CL.UTF-8" "Español (Chile)" \
                    "es_ES.UTF-8" "Español (España)")

    [ $? -ne 0 ] && LOCALE="en_US.UTF-8"
}

# Resumen de instalación
show_summary() {
    # Calculate partition sizes
    local disk_size=$(lsblk -b -d -n -o SIZE "$DISK" 2>/dev/null)
    local disk_size_gb=$((disk_size / 1024 / 1024 / 1024))

    # Determine partition naming for display
    local pp
    if [[ "$DISK" == *"nvme"* ]] || [[ "$DISK" == *"mmcblk"* ]]; then
        pp="${DISK}p"
    else
        pp="$DISK"
    fi

    local partition_info
    if [ "$SEPARATE_HOME" = "yes" ]; then
        if [ $disk_size_gb -lt 128 ]; then
            partition_info="  ${pp}1   1GB     EFI
  ${pp}2   50GB    Root (/)
  ${pp}3   Rest    Home (/home)"
        else
            partition_info="  ${pp}1   1GB     EFI
  ${pp}2   60GB    Root (/)
  ${pp}3   Rest    Home (/home)"
        fi
    else
        partition_info="  ${pp}1   1GB     EFI
  ${pp}2   All     Root (/) - /home as directory"
    fi

    dialog --title "📋 Installation Summary" \
           --colors \
           --yes-label "Start Installation" \
           --no-label "Cancel" \
           --yesno "\n\
\Z4System Configuration:\Zn

  Disk:       \Z6$DISK ($disk_size_gb GB)\Zn
  Username:   \Z6$USERNAME\Zn
  Hostname:   \Z6$HOSTNAME\Zn
  Timezone:   \Z6$TIMEZONE\Zn
  Language:   \Z6$LOCALE\Zn

\Z4Partitions:\Zn
$partition_info

\Z4Included Software:\Zn
  • Sway Wayland compositor
  • Claude Code AI assistant
  • Chromium, VS Code, Git
  • Development tools (Node.js, npm)
  • Optimized for 1.9GB RAM

\Z3Proceed with installation?\Zn" 28 65

    if [ $? -ne 0 ]; then
        clear
        echo "Installation cancelled."
        exit 0
    fi
}

# Barra de progreso
progress() {
    local percent=$1
    local message=$2
    echo "$percent"
    echo "XXX"
    echo "$message"
    echo "XXX"
}

# Instalación principal
perform_installation() {
    (
        # Paso 1: Particionado inteligente
        progress 5 "Partitioning disk $DISK..."
        # Unmount existing partitions and deactivate swap on target disk
        swapoff ${DISK}* 2>/dev/null || true
        umount -l ${DISK}* 2>/dev/null || true
        # For NVMe/MMC disks with 'p' separator
        swapoff ${DISK}p* 2>/dev/null || true
        umount -l ${DISK}p* 2>/dev/null || true
        sleep 1
        wipefs -a "$DISK" >/dev/null 2>&1
        parted -s "$DISK" mklabel gpt >/dev/null 2>&1
        parted -s "$DISK" mkpart "EFI" fat32 1MiB 1GiB >/dev/null 2>&1
        parted -s "$DISK" set 1 esp on >/dev/null 2>&1

        # Calcular tamaño de Root según disco
        local disk_size=$(lsblk -b -d -n -o SIZE "$DISK" 2>/dev/null)
        local disk_size_gb=$((disk_size / 1024 / 1024 / 1024))

        # Determine partition naming (NVMe/MMC use 'p' separator)
        if [[ "$DISK" == *"nvme"* ]] || [[ "$DISK" == *"mmcblk"* ]]; then
            PART_PREFIX="${DISK}p"
        else
            PART_PREFIX="$DISK"
        fi

        if [ "$SEPARATE_HOME" = "yes" ]; then
            # /home separado
            if [ $disk_size_gb -lt 128 ]; then
                # Disco pequeño: 50GB root
                parted -s "$DISK" mkpart "root" ext4 1GiB 51GiB >/dev/null 2>&1
                parted -s "$DISK" mkpart "home" ext4 51GiB 100% >/dev/null 2>&1
            else
                # Disco grande: 60GB root
                parted -s "$DISK" mkpart "root" ext4 1GiB 61GiB >/dev/null 2>&1
                parted -s "$DISK" mkpart "home" ext4 61GiB 100% >/dev/null 2>&1
            fi
            HOME_PART="${PART_PREFIX}3"
        else
            # Todo en root
            parted -s "$DISK" mkpart "root" ext4 1GiB 100% >/dev/null 2>&1
            HOME_PART=""
        fi

        sleep 2

        BOOT_PART="${PART_PREFIX}1"
        ROOT_PART="${PART_PREFIX}2"

        # Paso 2: Formateo
        progress 15 "Formatting partitions..."
        mkfs.fat -F32 "$BOOT_PART" >/dev/null 2>&1
        mkfs.ext4 -F "$ROOT_PART" >/dev/null 2>&1

        if [ -n "$HOME_PART" ]; then
            mkfs.ext4 -F "$HOME_PART" >/dev/null 2>&1
        fi

        # Paso 3: Montaje
        progress 20 "Mounting filesystems..."
        mount "$ROOT_PART" /mnt
        mkdir -p /mnt/boot
        mount "$BOOT_PART" /mnt/boot

        if [ -n "$HOME_PART" ]; then
            mkdir -p /mnt/home
            mount "$HOME_PART" /mnt/home
        fi

        # Paso 4: Instalación base
        progress 25 "Installing madOS base system (this may take a while)..."
        pacstrap /mnt base base-devel linux linux-firmware intel-ucode \
            sway swaybg swayidle swaylock waybar wofi mako xorg-xwayland \
            foot chromium code vim nano git htop openssh wget jq \
            grim slurp wl-clipboard xdg-desktop-portal-wlr \
            earlyoom zram-generator iwd pipewire pipewire-pulse wireplumber \
            intel-media-driver vulkan-intel mesa-utils \
            ttf-jetbrains-mono-nerd papirus-icon-theme \
            pcmanfm lxappearance plymouth \
            grub efibootmgr networkmanager sudo \
            nodejs npm rsync >/dev/null 2>&1

        progress 50 "Generating filesystem table..."
        genfstab -U /mnt >> /mnt/etc/fstab

        # Paso 5: Configuración del sistema
        progress 55 "Configuring system..."

        cat > /mnt/root/configure.sh <<EOFCHROOT
#!/bin/bash
# Exit on error for critical commands only

# Timezone
ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime
hwclock --systohc 2>/dev/null || true

# Locale
echo "$LOCALE UTF-8" >> /etc/locale.gen
locale-gen >/dev/null 2>&1
echo "LANG=$LOCALE" > /etc/locale.conf

# Teclado
echo "KEYMAP=es" > /etc/vconsole.conf

# Hostname
echo "$HOSTNAME" > /etc/hostname
cat > /etc/hosts <<EOFHOSTS
127.0.0.1   localhost
::1         localhost
127.0.1.1   $HOSTNAME.localdomain $HOSTNAME
EOFHOSTS

# Usuario
useradd -m -G wheel,audio,video,storage -s /bin/bash $USERNAME
echo "$USERNAME:$PASSWORD" | chpasswd

# Sudo
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
echo "$USERNAME ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/claude-nopasswd
chmod 440 /etc/sudoers.d/claude-nopasswd

# GRUB - Auto-detect UEFI or BIOS
if [ -d /sys/firmware/efi/efivars ]; then
    # UEFI mode
    grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=madOS --recheck >/dev/null 2>&1
else
    # BIOS mode
    grub-install --target=i386-pc --recheck $DISK >/dev/null 2>&1
fi

# Configure GRUB
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg >/dev/null 2>&1

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
for (i = 0; i < NUM_DOTS; i++) {
    dot[i].image = Image.Text(".", 0.533, 0.753, 0.816);
    dot[i].sprite = Sprite(dot[i].image);
    dot[i].sprite.SetZ(10);
    angle = i * 2 * 3.14159 / NUM_DOTS;
    dot[i].sprite.SetX(spinner_x + SPINNER_RADIUS * Math.Sin(angle) - dot[i].image.GetWidth() / 2);
    dot[i].sprite.SetY(spinner_y - SPINNER_RADIUS * Math.Cos(angle) - dot[i].image.GetHeight() / 2);
    dot[i].sprite.SetOpacity(0.2);
}
frame = 0;
fun refresh_callback() {
    frame++;
    active_dot = Math.Int(frame / 4) % NUM_DOTS;
    for (i = 0; i < NUM_DOTS; i++) {
        dist = active_dot - i;
        if (dist < 0) dist = dist + NUM_DOTS;
        if (dist == 0) opacity = 1.0;
        else if (dist == 1) opacity = 0.7;
        else if (dist == 2) opacity = 0.45;
        else if (dist == 3) opacity = 0.25;
        else opacity = 0.12;
        dot[i].sprite.SetOpacity(opacity);
    }
    pulse = Math.Abs(Math.Sin(frame * 0.02)) * 0.08 + 0.92;
    logo.sprite.SetOpacity(pulse);
}
Plymouth.SetRefreshFunction(refresh_callback);
fun display_normal_callback(text) {}
fun display_message_callback(text) {}
Plymouth.SetDisplayNormalFunction(display_normal_callback);
Plymouth.SetMessageFunction(display_message_callback);
fun quit_callback() {
    for (i = 0; i < NUM_DOTS; i++) { dot[i].sprite.SetOpacity(0); }
    logo.sprite.SetOpacity(1);
}
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

# Rebuild initramfs with plymouth hook
sed -i 's/^HOOKS=.*/HOOKS=(base udev plymouth autodetect modconf kms block filesystems keyboard fsck)/' /etc/mkinitcpio.conf
mkinitcpio -P >/dev/null 2>&1 || true

# Servicios
systemctl enable earlyoom >/dev/null 2>&1
systemctl enable iwd >/dev/null 2>&1
systemctl enable systemd-timesyncd >/dev/null 2>&1

# Kernel optimizations
cat > /etc/sysctl.d/99-extreme-low-ram.conf <<EOFSYSCTL
vm.vfs_cache_pressure = 200
vm.swappiness = 5
vm.dirty_ratio = 5
vm.dirty_background_ratio = 3
vm.min_free_kbytes = 16384
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
net.core.rmem_max = 262144
net.core.wmem_max = 262144
EOFSYSCTL

# ZRAM
cat > /etc/systemd/zram-generator.conf <<EOFZRAM
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOFZRAM

# Autologin
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOFAUTOLOGIN
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\\\u' --noclear --autologin $USERNAME %I \\\$TERM
EOFAUTOLOGIN

# Copiar configuraciones
su - $USERNAME -c "mkdir -p ~/.config/{sway,waybar,foot,wofi,alacritty}"
su - $USERNAME -c "mkdir -p ~/Pictures/{Wallpapers,Screenshots}"

cp -r /etc/skel/.config/* /home/$USERNAME/.config/ 2>/dev/null || true
cp -r /etc/skel/Pictures/* /home/$USERNAME/Pictures/ 2>/dev/null || true
cp /etc/skel/toggle-audio.sh /home/$USERNAME/ 2>/dev/null || true
chown -R $USERNAME:$USERNAME /home/$USERNAME

# Bash profile
cat > /home/$USERNAME/.bash_profile <<EOFBASH
[[ -f ~/.bashrc ]] && . ~/.bashrc

if [ -z "\\\$DISPLAY" ] && [ "\\\$(tty)" = "/dev/tty1" ]; then
  exec sway
fi
EOFBASH

chown $USERNAME:$USERNAME /home/$USERNAME/.bash_profile

# Instalar Claude Code (non-fatal if no network)
npm install -g @anthropic-ai/claude-code >/dev/null 2>&1 || echo "Warning: Could not install Claude Code"

# Mensaje de bienvenida
cat > /etc/motd <<EOFMOTD

╔═══════════════════════════════════════════════════╗
║                                                   ║
║     ███╗   ███╗ █████╗ ██████╗  ██████╗ ███████╗ ║
║     ████╗ ████║██╔══██╗██╔══██╗██╔═══██╗██╔════╝ ║
║     ██╔████╔██║███████║██║  ██║██║   ██║███████╗ ║
║     ██║╚██╔╝██║██╔══██║██║  ██║██║   ██║╚════██║ ║
║     ██║ ╚═╝ ██║██║  ██║██████╔╝╚██████╔╝███████║ ║
║     ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝ ║
║                                                   ║
║         AI-Orchestrated Arch Linux System        ║
║              Powered by Claude Code              ║
║                                                   ║
╚═══════════════════════════════════════════════════╝

Welcome to madOS! Type 'claude' to start the AI assistant.

EOFMOTD

EOFCHROOT

        progress 70 "Applying configurations..."
        chmod +x /mnt/root/configure.sh

        # Copy Plymouth logo to installed system before chroot
        mkdir -p /mnt/usr/share/plymouth/themes/mados
        cp /usr/share/plymouth/themes/mados/logo.png /mnt/usr/share/plymouth/themes/mados/logo.png 2>/dev/null || true

        arch-chroot /mnt /root/configure.sh

        progress 90 "Cleaning up..."
        rm /mnt/root/configure.sh

        progress 100 "Installation complete!"
        sleep 2

    ) | dialog --title "🚀 Installing madOS" \
               --gauge "\nPreparing installation..." \
               10 70 0
}

# Pantalla de finalización
show_completion() {
    dialog --title "✅ Installation Complete!" \
           --colors \
           --msgbox "\n\
\Z2madOS has been successfully installed!\Zn

\Z4Next steps:\Zn

  1. Remove the installation media
  2. Reboot your computer
  3. Log in with your credentials
  4. Sway will start automatically
  5. Open terminal and type: \Z6claude\Zn

\Z4What's included:\Zn

  • Sway Wayland compositor (optimized)
  • Claude Code AI assistant
  • ZRAM swap (compressed)
  • EarlyOOM protection
  • Developer tools ready

\Z3Press OK to reboot now.\Zn" 24 60

    clear
    echo ""
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║          madOS Installation Complete!            ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo ""
    echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
    sleep 5
    reboot
}

# Elegir esquema de particionado
choose_partitioning() {
    local disk_size=$(lsblk -b -d -n -o SIZE "$DISK" 2>/dev/null)
    local disk_size_gb=$((disk_size / 1024 / 1024 / 1024))

    dialog --title "💾 Particionado del Sistema" \
           --colors \
           --yes-label "Sí, separar /home" \
           --no-label "No, todo en /" \
           --yesno "\n\
\Z4¿Desea una partición /home separada?\Zn

Disco: \Z6$DISK ($disk_size_gb GB)\Zn

\Z2✓ Sí - /home en partición separada\Zn
  • Reinstalar SO sin perder datos
  • Mejor para backups
  • Menos flexible con espacio

\Z3✓ No - Todo en / (recomendado para discos <128GB)\Zn
  • Máxima flexibilidad de espacio
  • Mejor para discos pequeños
  • Reinstalar requiere backup

\Z7Esquema resultante:\Zn
  Sí: EFI 1GB | Root 50-60GB | Home resto
  No: EFI 1GB | Root todo resto" 24 65

    if [ $? -eq 0 ]; then
        SEPARATE_HOME="yes"
    else
        SEPARATE_HOME="no"
    fi
}

# Flujo principal
main() {
    show_welcome

    while true; do
        select_disk
        if confirm_disk; then
            break
        fi
    done

    choose_partitioning
    get_user_info
    get_locale_config
    show_summary

    perform_installation

    show_completion
}

# Ejecutar instalador
main
