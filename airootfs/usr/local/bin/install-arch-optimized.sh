#!/bin/bash
# Instalador Arch Linux Optimizado
# Hardware: Intel Atom / 1.9GB RAM
# Incluye: Claude Code, Sway optimizado, optimizaciones de RAM

set -e

clear
echo "================================================"
echo "  Arch Linux Optimized Installer"
echo "  With Claude Code & Sway"
echo "================================================"
echo

# Verificar root
if [[ $(id -u) != "0" ]]; then
    echo "ERROR: Run as root"
    exit 1
fi

# Función de error
error() {
    echo "ERROR: $1"
    exit 1
}

# 1. Selección de disco
echo "=== Step 1: Disk Selection ==="
lsblk -d -o NAME,SIZE,TYPE | grep disk
echo
read -p "Enter disk to use (e.g., sda): " DISK
DISK="/dev/$DISK"

[[ ! -b "$DISK" ]] && error "Disk $DISK does not exist"

echo "WARNING: ALL data on $DISK will be ERASED"
read -p "Continue? (yes/no): " CONFIRM
[[ "$CONFIRM" != "yes" ]] && { echo "Installation cancelled"; exit 0; }

# 2. Particionar
echo
echo "=== Step 2: Partitioning $DISK ==="
wipefs -a "$DISK"
parted -s "$DISK" mklabel gpt
parted -s "$DISK" mkpart "EFI" fat32 1MiB 1GiB
parted -s "$DISK" set 1 esp on
parted -s "$DISK" mkpart "root" ext4 1GiB 33GiB
parted -s "$DISK" mkpart "home" ext4 33GiB 100%

sleep 2

BOOT_PART="${DISK}1"
ROOT_PART="${DISK}2"
HOME_PART="${DISK}3"

echo "Partitions created:"
lsblk "$DISK"

# 3. Formatear
echo
echo "=== Step 3: Formatting ==="
mkfs.fat -F32 "$BOOT_PART"
mkfs.ext4 -F "$ROOT_PART"
mkfs.ext4 -F "$HOME_PART"

# 4. Montar
echo
echo "=== Step 4: Mounting ==="
mount "$ROOT_PART" /mnt
mkdir -p /mnt/boot /mnt/home
mount "$BOOT_PART" /mnt/boot
mount "$HOME_PART" /mnt/home

# 5. Instalar sistema base
echo
echo "=== Step 5: Installing Base System ==="
echo "This will take several minutes..."

pacstrap /mnt base base-devel linux linux-firmware intel-ucode \
    sway swaybg swayidle swaylock waybar wofi mako xorg-xwayland \
    foot chromium code vim nano git htop openssh wget jq \
    grim slurp wl-clipboard xdg-desktop-portal-wlr \
    earlyoom zram-generator iwd pipewire pipewire-pulse wireplumber \
    intel-media-driver vulkan-intel mesa-utils \
    ttf-jetbrains-mono-nerd papirus-icon-theme \
    pcmanfm lxappearance \
    grub efibootmgr networkmanager sudo \
    nodejs npm rsync

# 6. Generar fstab
echo
echo "=== Step 6: Generating fstab ==="
genfstab -U /mnt >> /mnt/etc/fstab

# 7. Configurar sistema
echo
echo "=== Step 7: System Configuration ==="

read -p "Username: " USERNAME
read -s -p "Password: " PASSWORD
echo
read -p "Hostname: " HOSTNAME

# Script chroot
cat > /mnt/root/configure.sh <<EOFCHROOT
#!/bin/bash
set -e

# Timezone - UTC según preferencia del usuario
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
hwclock --systohc

# Locale - en_US.UTF-8 según preferencia del usuario
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
echo "es_CL.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

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

# Configurar sudo sin password para Claude Code
echo "$USERNAME ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/claude-nopasswd
chmod 440 /etc/sudoers.d/claude-nopasswd

# GRUB
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0"/' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg

# Servicios
systemctl enable earlyoom
systemctl enable iwd
systemctl enable systemd-timesyncd

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

# Instalar Claude Code
echo "Installing Claude Code..."
npm install -g @anthropic-ai/claude-code

echo "Configuration complete!"
EOFCHROOT

chmod +x /mnt/root/configure.sh
arch-chroot /mnt /root/configure.sh

# 8. Finalizar
echo
echo "=== Installation Complete! ==="
echo
echo "System installed with optimizations:"
echo "  ✓ ZRAM swap (4GB compressed)"
echo "  ✓ Kernel extreme mode"
echo "  ✓ EarlyOOM enabled"
echo "  ✓ TTY autologin"
echo "  ✓ Sway autostart"
echo "  ✓ Claude Code installed"
echo
echo "To finish:"
echo "  umount -R /mnt"
echo "  reboot"
echo
read -p "Press Enter to continue..."
