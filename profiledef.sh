#!/usr/bin/env bash
# shellcheck disable=SC2034

readonly PERMS_755="$PERMS_755"

iso_name="madOS"
iso_label="MADOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="madOS Project"
iso_application="madOS - AI-Orchestrated Arch Linux"
_iso_date="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d-%H%M)"
_iso_tag="$(git -C "$(dirname "$0")" tag -l --sort=-version:refname 'v*' 2>/dev/null | head -1)"
_iso_tag="${_iso_tag:-dev}"
iso_version="${_iso_tag}-${_iso_date}"
install_dir="arch"
buildmodes=('iso')
bootmodes=('bios.syslinux.mbr'
            'bios.syslinux.eltorito'
            'uefi-x64.systemd-boot.esp'
            'uefi-x64.systemd-boot.eltorito')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15' '-b' '1M')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/profile.d/mados-welcome.sh"]="$PERMS_755"
  ["/etc/sudoers.d/99-opencode-nopasswd"]="0:0:440"
  ["/root"]="0:0:750"
  ["/root/customize_airootfs.sh"]="$PERMS_755"
  ["/root/.automated_script.sh"]="$PERMS_755"
  ["/root/.zlogin"]="0:0:644"
  ["/root/.gnupg"]="0:0:700"
  ["/home/mados"]="1000:1000:750"
  ["/home/mados/.zlogin"]="1000:1000:644"
  ["/home/mados/.automated_script.sh"]="1000:1000:700"
  ["/usr/local/bin/choose-mirror"]="$PERMS_755"
  ["/usr/local/bin/Installation_guide"]="$PERMS_755"
  ["/usr/local/bin/livecd-sound"]="$PERMS_755"
  ["/usr/local/bin/mados-audio-init.sh"]="$PERMS_755"
  ["/usr/local/bin/mados-audio-quality.sh"]="$PERMS_755"
  ["/usr/local/bin/install-mados-gtk.py"]="$PERMS_755"
  ["/usr/local/bin/install-mados"]="$PERMS_755"
  ["/usr/local/lib/mados_installer/"]="$PERMS_755"
  ["/usr/local/bin/setup-opencode.sh"]="$PERMS_755"
  ["/usr/local/bin/setup-ollama.sh"]="$PERMS_755"
  ["/usr/local/bin/setup-ohmyzsh.sh"]="$PERMS_755"
  ["/usr/local/bin/setup-persistence.sh"]="$PERMS_755"
  ["/usr/local/bin/toggle-demo-mode.sh"]="$PERMS_755"
  ["/usr/local/bin/mados-photo-viewer"]="$PERMS_755"
  ["/usr/local/bin/mados-pdf-viewer"]="$PERMS_755"
  ["/usr/local/bin/mados-persistence"]="$PERMS_755"
  ["/usr/local/bin/diagnose-persistence"]="$PERMS_755"
  ["/usr/local/bin/mados-equalizer"]="$PERMS_755"
  ["/usr/local/lib/mados_photo_viewer/"]="$PERMS_755"
  ["/usr/local/lib/mados_pdf_viewer/"]="$PERMS_755"
  ["/usr/local/lib/mados_equalizer/"]="$PERMS_755"
  ["/usr/local/bin/mados-debug"]="$PERMS_755"
  ["/usr/local/bin/detect-legacy-hardware"]="$PERMS_755"
  ["/usr/local/bin/cage-greeter"]="$PERMS_755"
  ["/usr/local/bin/sway-session"]="$PERMS_755"
  ["/usr/local/bin/hyprland-session"]="$PERMS_755"
  ["/usr/local/bin/select-compositor"]="$PERMS_755"
  ["/usr/local/bin/setup-gpu-compute"]="$PERMS_755"
  ["/usr/local/bin/mados-logs"]="$PERMS_755"
  ["/usr/local/bin/mados-wallpaper-glitch"]="$PERMS_755"
  ["/usr/local/lib/mados-media-helper.sh"]="$PERMS_755"
)
