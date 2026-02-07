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
    exec sway
fi
