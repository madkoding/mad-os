#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc

# Auto-start compositor on TTY1
# Uses Hyprland on modern hardware, Sway on legacy/software-rendering hardware
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  export XDG_SESSION_TYPE=wayland
  export MOZ_ENABLE_WAYLAND=1

  # Select compositor based on hardware capabilities
  COMPOSITOR="hyprland"
  if [ -x /usr/local/bin/select-compositor ]; then
      COMPOSITOR=$(/usr/local/bin/select-compositor)
  fi

  if [ "$COMPOSITOR" = "sway" ]; then
      # Software rendering: use Sway with pixman renderer
      export XDG_CURRENT_DESKTOP=sway
      echo "Software rendering enabled - using Sway"
      logger -p user.info -t mados-session "Compositor selected: sway (software rendering)"
      export WLR_RENDERER=pixman
      export WLR_NO_HARDWARE_CURSORS=1
      export LIBGL_ALWAYS_SOFTWARE=1
      export MESA_GL_VERSION_OVERRIDE=3.3
      # Chromium: force software rendering on legacy hardware
      export CHROMIUM_FLAGS="${CHROMIUM_FLAGS:-} --disable-gpu"

      # VM DRM workarounds
      if systemd-detect-virt --vm --quiet 2>/dev/null; then
          export WLR_DRM_NO_ATOMIC=1
          export WLR_DRM_NO_MODIFIERS=1
          export WLR_NO_HARDWARE_CURSORS=1
          # VM performance: generate optimized sway config drop-in
          VM_CONF="/etc/sway/config.d/99-vm-performance.conf"
          if [ ! -f "$VM_CONF" ]; then
              sudo mkdir -p /etc/sway/config.d
              sudo tee "$VM_CONF" > /dev/null << 'VMCONF'
# Auto-generated VM performance optimizations
output * bg #2E3440 solid_color
gaps inner 0
gaps outer 0
VMCONF
          fi
      fi

      exec sway
  else
      # Hardware rendering: use Hyprland
      export XDG_CURRENT_DESKTOP=Hyprland
      echo "Hardware rendering enabled - using Hyprland"
      logger -p user.info -t mados-session "Compositor selected: hyprland (hardware rendering)"
      # VM with 3D acceleration: generate Hyprland optimizations for smoother input
      if systemd-detect-virt --vm --quiet 2>/dev/null; then
          cat > ~/.config/hypr/vm-performance.conf << 'VMCONF'
# Auto-generated VM performance optimizations
# Disables animations and effects for smoother mouse/input in VirtualBox/VMware/QEMU
cursor {
    no_hardware_cursors = true
}
animations {
    enabled = false
}
decoration {
    blur {
        enabled = false
    }
    shadow {
        enabled = false
    }
    rounding = 0
}
misc {
    vfr = true
}
render {
    direct_scanout = false
}
VMCONF
      fi
      # Try Hyprland via start-hyprland wrapper, fall back to Sway if it fails
      start-hyprland || {
          logger -p user.warning -t mados-session "Hyprland failed, falling back to Sway"
          echo "Hyprland failed - falling back to Sway with software rendering"
          export XDG_CURRENT_DESKTOP=sway
          export WLR_RENDERER=pixman
          export WLR_NO_HARDWARE_CURSORS=1
          export LIBGL_ALWAYS_SOFTWARE=1
          export MESA_GL_VERSION_OVERRIDE=3.3
          export CHROMIUM_FLAGS="${CHROMIUM_FLAGS:-} --disable-gpu"
          if systemd-detect-virt --vm --quiet 2>/dev/null; then
              export WLR_DRM_NO_ATOMIC=1
              export WLR_DRM_NO_MODIFIERS=1
              # VM performance: generate optimized sway config drop-in
              VM_CONF="/etc/sway/config.d/99-vm-performance.conf"
              if [ ! -f "$VM_CONF" ]; then
                  sudo mkdir -p /etc/sway/config.d
                  sudo tee "$VM_CONF" > /dev/null << 'VMCONF'
# Auto-generated VM performance optimizations
output * bg #2E3440 solid_color
gaps inner 0
gaps outer 0
VMCONF
              fi
          fi
          exec sway
      }
  fi
fi
