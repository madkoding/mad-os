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
_perm_exec="$_perm_exec"
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/profile.d/mados-welcome.sh"]="$_perm_exec"
  ["/etc/sudoers.d/99-opencode-nopasswd"]="0:0:440"
  ["/root"]="0:0:750"
  ["/root/customize_airootfs.sh"]="$_perm_exec"
  ["/root/.automated_script.sh"]="$_perm_exec"
  ["/root/.zlogin"]="0:0:644"
  ["/root/.gnupg"]="0:0:700"
  ["/home/mados"]="1000:1000:750"
  ["/home/mados/.zlogin"]="1000:1000:644"
  ["/home/mados/.automated_script.sh"]="1000:1000:700"
  ["/usr/local/bin/choose-mirror"]="$_perm_exec"
  ["/usr/local/bin/Installation_guide"]="$_perm_exec"
  ["/usr/local/bin/livecd-sound"]="$_perm_exec"
  ["/usr/local/bin/mados-audio-init.sh"]="$_perm_exec"
  ["/usr/local/bin/mados-audio-quality.sh"]="$_perm_exec"
  ["/usr/local/bin/install-mados-gtk.py"]="$_perm_exec"
  ["/usr/local/bin/install-mados"]="$_perm_exec"
  ["/usr/local/lib/mados_installer/"]="$_perm_exec"
  ["/usr/local/bin/setup-opencode.sh"]="$_perm_exec"
  ["/usr/local/bin/setup-ollama.sh"]="$_perm_exec"
  ["/usr/local/bin/setup-ohmyzsh.sh"]="$_perm_exec"
  ["/usr/local/bin/toggle-demo-mode.sh"]="$_perm_exec"
  ["/usr/local/bin/mados-photo-viewer"]="$_perm_exec"
  ["/usr/local/bin/mados-pdf-viewer"]="$_perm_exec"

  ["/usr/local/bin/mados-equalizer"]="$_perm_exec"
  ["/usr/local/lib/mados_photo_viewer/"]="$_perm_exec"
  ["/usr/local/lib/mados_pdf_viewer/"]="$_perm_exec"
  ["/usr/local/lib/mados_equalizer/"]="$_perm_exec"
  ["/usr/local/bin/mados-debug"]="$_perm_exec"
  ["/usr/local/bin/detect-legacy-hardware"]="$_perm_exec"
  ["/usr/local/bin/cage-greeter"]="$_perm_exec"
  ["/usr/local/bin/sway-session"]="$_perm_exec"
  ["/usr/local/bin/hyprland-session"]="$_perm_exec"
  ["/usr/local/bin/select-compositor"]="$_perm_exec"
  ["/usr/local/bin/setup-gpu-compute"]="$_perm_exec"
  ["/usr/local/bin/mados-logs"]="$_perm_exec"
  ["/usr/local/bin/mados-wallpaper-glitch"]="$_perm_exec"
  ["/usr/local/lib/mados-media-helper.sh"]="$_perm_exec"
  ["/usr/local/bin/mados-persistence"]="$_perm_exec"
  ["/usr/local/bin/mados-persist-sync.sh"]="$_perm_exec"
  ["/usr/local/bin/mados-persist-detect.sh"]="$_perm_exec"
)
