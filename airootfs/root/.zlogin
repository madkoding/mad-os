# fix for screen readers
if grep -Fqa 'accessibility=' /proc/cmdline &> /dev/null; then
    setopt SINGLE_LINE_ZLE
fi

~/.automated_script.sh

# Auto-start Sway on TTY1 for live environment
if [ -z "${WAYLAND_DISPLAY}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    # Copy skel configs to root on first boot (if not already present)
    if [ ! -d ~/.config/sway ]; then
        cp -r /etc/skel/.config ~/ 2>/dev/null
    fi
    if [ ! -d ~/Pictures ]; then
        cp -r /etc/skel/Pictures ~/ 2>/dev/null
    fi
    # Export environment for Wayland/Sway
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

    # Detectar nomodeset (safe graphics) y forzar renderizado software
    if grep -q 'nomodeset' /proc/cmdline 2>/dev/null; then
        export WLR_RENDERER=pixman
        export WLR_NO_HARDWARE_CURSORS=1
        export LIBGL_ALWAYS_SOFTWARE=1
        export MESA_GL_VERSION_OVERRIDE=3.3
    fi

    exec sway
fi
