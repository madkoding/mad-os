#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc

# Auto-start Sway on TTY1
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  export XDG_SESSION_TYPE=wayland
  export XDG_CURRENT_DESKTOP=sway
  export MOZ_ENABLE_WAYLAND=1

  # Detectar hardware antiguo (VMs sin 3D, CPUs/GPUs antiguas, RAM baja) y usar renderizado por software
  # VMs con aceleración 3D usarán hardware rendering con workarounds DRM
  # Hardware moderno usará aceleración por hardware automáticamente
  if [ -x /usr/local/bin/detect-legacy-hardware ]; then
      if /usr/local/bin/detect-legacy-hardware >/dev/null 2>&1; then
          echo "Software rendering enabled for legacy/low-spec hardware"
          export WLR_RENDERER=pixman
          export WLR_NO_HARDWARE_CURSORS=1
          export LIBGL_ALWAYS_SOFTWARE=1
          export MESA_GL_VERSION_OVERRIDE=3.3
          # Chromium: force software rendering on legacy hardware
          export CHROMIUM_FLAGS="${CHROMIUM_FLAGS} --disable-gpu"
      else
          echo "Hardware rendering enabled for modern hardware"
      fi
  else
      # Fallback a la detección anterior si el script no existe
      if systemd-detect-virt --vm --quiet 2>/dev/null; then
          export WLR_RENDERER=pixman
          export WLR_NO_HARDWARE_CURSORS=1
          export LIBGL_ALWAYS_SOFTWARE=1
          export MESA_GL_VERSION_OVERRIDE=3.3
          # Chromium: force software rendering in VMs without 3D
          export CHROMIUM_FLAGS="${CHROMIUM_FLAGS} --disable-gpu"
      fi
  fi

  # VM DRM workarounds: disable atomic modesetting and modifiers for VM GPU drivers
  if systemd-detect-virt --vm --quiet 2>/dev/null; then
      export WLR_DRM_NO_ATOMIC=1
      export WLR_DRM_NO_MODIFIERS=1
      export WLR_NO_HARDWARE_CURSORS=1
  fi

  exec sway
fi
