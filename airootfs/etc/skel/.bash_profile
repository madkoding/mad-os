#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc

# Auto-start Sway on TTY1
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  export XDG_SESSION_TYPE=wayland
  export XDG_CURRENT_DESKTOP=sway
  export MOZ_ENABLE_WAYLAND=1

  # Detectar si estamos en una máquina virtual y configurar renderizado software
  if systemd-detect-virt --vm --quiet 2>/dev/null; then
      export WLR_RENDERER=pixman
      export WLR_NO_HARDWARE_CURSORS=1
      export LIBGL_ALWAYS_SOFTWARE=1
      export MESA_GL_VERSION_OVERRIDE=3.3
  fi

  exec sway
fi
