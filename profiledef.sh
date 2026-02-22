#!/usr/bin/env bash
# shellcheck disable=SC2034

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
  ["/etc/profile.d/mados-welcome.sh"]="0:0:755"
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
  ["/usr/local/bin/install-mados-gtk.py"]="0:0:755"
  ["/usr/local/bin/install-mados"]="0:0:755"
  ["/usr/local/lib/mados_installer/"]="0:0:755"
  ["/usr/local/bin/setup-opencode.sh"]="0:0:755"
  ["/usr/local/bin/setup-ollama.sh"]="0:0:755"
  ["/usr/local/bin/setup-ohmyzsh.sh"]="0:0:755"
  ["/usr/local/bin/toggle-demo-mode.sh"]="0:0:755"
  ["/usr/local/bin/mados-photo-viewer"]="0:0:755"
  ["/usr/local/bin/mados-pdf-viewer"]="0:0:755"

  ["/usr/local/bin/mados-equalizer"]="0:0:755"
  ["/usr/local/lib/mados_photo_viewer/"]="0:0:755"
  ["/usr/local/lib/mados_pdf_viewer/"]="0:0:755"
  ["/usr/local/lib/mados_equalizer/"]="0:0:755"
  ["/usr/local/bin/mados-debug"]="0:0:755"
  ["/usr/local/bin/detect-legacy-hardware"]="0:0:755"
  ["/usr/local/bin/cage-greeter"]="0:0:755"
  ["/usr/local/bin/sway-session"]="0:0:755"
  ["/usr/local/bin/hyprland-session"]="0:0:755"
  ["/usr/local/bin/select-compositor"]="0:0:755"
  ["/usr/local/bin/setup-gpu-compute"]="0:0:755"
  ["/usr/local/bin/mados-logs"]="0:0:755"
  ["/usr/local/bin/mados-wallpaper-glitch"]="0:0:755"
  ["/usr/local/lib/mados-media-helper.sh"]="0:0:755"
  ["/usr/local/bin/mados-persistence"]="0:0:755"
  ["/usr/local/bin/mados-persist-sync.sh"]="0:0:755"
  ["/usr/local/bin/mados-persist-detect.sh"]="0:0:755"
)
