#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="madOS"
iso_label="MADOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="madOS Project"
iso_application="madOS - AI-Orchestrated Arch Linux"
_iso_tag="$(git -C "$(dirname "$0")" tag -l --sort=-version:refname 'v*' 2>/dev/null | head -1)"
_iso_tag="${_iso_tag:-dev}"
iso_version="${_iso_tag}"
install_dir="arch"
buildmodes=('iso')
bootmodes=('bios.syslinux'
            'uefi.systemd-boot')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '17')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '-zstd-level=17')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/profile.d/mados-welcome.sh"]="0:0:755"
  ["/etc/profile.d/mados-media-links.sh"]="0:0:755"
  ["/etc/sudoers.d/99-opencode-nopasswd"]="0:0:440"
  ["/root"]="0:0:750"
  ["/root/customize_airootfs.sh"]="0:0:755"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.zlogin"]="0:0:644"
  ["/root/.gnupg"]="0:0:700"
  ["/home/mados"]="1000:1000:750"
  ["/home/mados/.zlogin"]="1000:1000:644"
  ["/home/mados/.automated_script.sh"]="1000:1000:700"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
  ["/usr/local/bin/mados-audio-init.sh"]="0:0:755"
  ["/usr/local/bin/mados-audio-quality.sh"]="0:0:755"
  ["/usr/local/bin/setup-opencode.sh"]="0:0:755"
  ["/usr/local/bin/setup-nvm.sh"]="0:0:755"
  ["/usr/local/bin/setup-ollama.sh"]="0:0:755"
  ["/usr/local/bin/toggle-demo-mode.sh"]="0:0:755"

  ["/usr/local/bin/mados-debug"]="0:0:755"
  ["/usr/local/bin/detect-legacy-hardware"]="0:0:755"
  ["/usr/local/bin/cage-greeter"]="0:0:755"
  ["/usr/local/bin/sway-session"]="0:0:755"
  ["/usr/local/bin/hyprland-session"]="0:0:755"
  ["/usr/local/bin/start-hyprland"]="0:0:755"
  ["/usr/local/bin/select-compositor"]="0:0:755"
  ["/usr/local/bin/mados-logs"]="0:0:755"
  ["/usr/local/bin/mados-wallpaper-glitch"]="0:0:755"
  ["/usr/local/bin/mados-sway-wallpapers"]="0:0:755"
  ["/usr/local/bin/mados-sway-wallpaper-set"]="0:0:755"
  ["/usr/local/bin/mados-sway-workspace-cycle"]="0:0:755"
  ["/usr/local/bin/mados-hyprland-wallpaper-set"]="0:0:755"
  ["/usr/local/bin/mados-hyprland-wallpaper"]="0:0:755"
  ["/usr/local/bin/mados-sway-wallpaper"]="0:0:755"
  ["/usr/local/bin/mados-wallpaperd"]="0:0:755"
  ["/usr/local/bin/gufw"]="0:0:755"
  ["/usr/local/bin/mados-hyprland-workspace-cycle"]="0:0:755"
  ["/usr/local/lib/mados-media-helper.sh"]="0:0:755"
  ["/usr/local/bin/mados-persistence"]="0:0:755"
  ["/usr/local/bin/mados-installer-autostart"]="0:0:755"
  ["/usr/local/bin/mados-vbox-guest"]="0:0:755"
  ["/usr/local/bin/mados-persist-sync.sh"]="0:0:755"
  ["/usr/local/bin/mados-persist-detect.sh"]="0:0:755"
  ["/usr/local/bin/mados-ventoy-setup.sh"]="0:0:755"
  ["/usr/local/bin/mados-timezone-detect.sh"]="0:0:755"
  ["/usr/local/bin/mados-gamepad-wm"]="0:0:755"
  ["/usr/local/bin/mados-squeekboard"]="0:0:755"
  ["/usr/local/bin/mados-firstboot-recover"]="0:0:755"
  ["/usr/local/bin/mados-health-check"]="0:0:755"
  ["/usr/local/bin/mados-help"]="0:0:755"
  ["/usr/local/bin/mados-power"]="0:0:755"
  ["/usr/local/bin/mados-logs"]="0:0:755"
  ["/usr/local/bin/mados-update"]="0:0:755"
  ["/usr/local/bin/mados-ota"]="0:0:755"
  ["/usr/local/lib/mados_update/"]="0:0:755"

  ["/etc/mados/"]="0:0:755"
  ["/etc/mados/version.json"]="0:0:644"
  ["/etc/mados/ventoy-persist.conf"]="0:0:644"
  ["/etc/systemd/system/mados-apps-update.service"]="0:0:644"
  ["/etc/systemd/system/mados-apps-update.timer"]="0:0:644"
  ["/etc/systemd/system/mados-ota.service"]="0:0:644"
  ["/etc/systemd/system/mados-ota.timer"]="0:0:644"
  ["/usr/share/grub/themes/mados"]="0:0:755"
  ["/usr/share/grub/themes/mados/theme.txt"]="0:0:644"
  ["/usr/share/grub/themes/mados/logo.png"]="0:0:644"

  # UFW Firewall
  ["/etc/ufw/ufw.conf"]="0:0:644"
  ["/etc/ufw/user.rules"]="0:0:600"
  ["/etc/ufw/user6.rules"]="0:0:600"
  ["/etc/systemd/system/ufw.service"]="0:0:644"
  ["/etc/systemd/system/multi-user.target.wants/ufw.service"]="0:0:644"

  # Security hardening
  ["/etc/sysctl.d/99-security.conf"]="0:0:644"

  # USBGuard
  ["/etc/usbguard/usbguard-daemon.conf"]="0:0:644"
  ["/etc/usbguard/rules.conf"]="0:0:600"
  ["/etc/usbguard/usbguard-notify.sh"]="0:0:755"
  ["/etc/systemd/system/usbguard.service"]="0:0:644"

  # RKHunter
  ["/etc/rkhunter.conf"]="0:0:644"
  ["/etc/systemd/system/rkhunter.service"]="0:0:644"
  ["/etc/systemd/system/rkhunter.timer"]="0:0:644"

  # Fail2Ban
  ["/etc/fail2ban/jail.local"]="0:0:644"

  # Security notifications
  ["/etc/profile.d/mados-security-notify.sh"]="0:0:755"

  # ClamAV
  ["/etc/systemd/system/clamav-scan.service"]="0:0:644"
  ["/etc/systemd/system/clamav-scan.timer"]="0:0:644"
)
