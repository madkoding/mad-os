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
      fi

      exec sway
  else
      # Hardware rendering: use Hyprland
      export XDG_CURRENT_DESKTOP=Hyprland
      echo "Hardware rendering enabled - using Hyprland"
      exec Hyprland
  fi
fi
