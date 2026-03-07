#!/bin/bash
# madOS First-Boot Progress Tracker
# Tracks and reports the progress of first-boot setup tasks

PROGRESS_FILE="/var/lib/mados-firstboot/progress"
MOTD_FILE="/etc/motd.d/mados-firstboot"
WAYBAR_PROGRESS_FILE="/tmp/mados-firstboot-progress"

PHASES=(
    "package-update"
    "package-install"
    "user-config"
    "desktop-config"
    "services-enable"
    "cleanup"
)

init_progress() {
    mkdir -p "$(dirname "$PROGRESS_FILE")"
    echo "0" > "$PROGRESS_FILE"
    for phase in "${PHASES[@]}"; do
        echo "pending" > "/var/lib/mados-firstboot/${phase}.status"
    done
    return 0
}

set_phase_complete() {
    local phase="$1"
    echo "complete" > "/var/lib/mados-firstboot/${phase}.status"
    update_progress
    return 0
}

set_phase_running() {
    local phase="$1"
    echo "running" > "/var/lib/mados-firstboot/${phase}.status"
    return 0
}

update_progress() {
    local total=${#PHASES[@]}
    local complete=0
    
    for phase in "${PHASES[@]}"; do
        local status
        status=$(cat "/var/lib/mados-firstboot/${phase}.status" 2>/dev/null)
        if [[ "$status" == "complete" ]]; then
            ((complete++))
        fi
    done
    
    local percent
    percent=$((complete * 100 / total))
    echo "$percent" > "$PROGRESS_FILE"
    echo "$percent" > "$WAYBAR_PROGRESS_FILE"
    
    update_motd "$percent"
    return 0
}

update_motd() {
    local percent="$1"
    cat > "$MOTD_FILE" << EOF
╔══════════════════════════════════════════════════════════╗
║  madOS First-Boot Setup in Progress                      ║
║  Progress: ${percent}% complete                                  ║
║                                                          ║
║  Please wait while the system completes setup...         ║
║  You will be able to log in when setup is complete.      ║
╚══════════════════════════════════════════════════════════╝
EOF
    return 0
}

get_progress() {
    if [[ -f "$PROGRESS_FILE" ]]; then
        cat "$PROGRESS_FILE"
    else
        echo "0"
    fi
    return 0
}

get_status() {
    local phase="$1"
    cat "/var/lib/mados-firstboot/${phase}.status" 2>/dev/null || echo "pending"
    return 0
}

is_setup_complete() {
    local percent
    percent=$(get_progress)
    [[ "$percent" -ge 100 ]]
    return $?
}

cleanup_motd() {
    rm -f "$MOTD_FILE"
    return 0
}

case "${1:-}" in
    init)
        init_progress
        ;;
    complete)
        set_phase_complete "${2:-}"
        ;;
    running)
        set_phase_running "${2:-}"
        ;;
    progress)
        get_progress
        ;;
    status)
        get_status "${2:-}"
        ;;
    is-complete)
        is_setup_complete
        ;;
    cleanup)
        cleanup_motd
        ;;
    *)
        echo "Usage: $0 {init|complete|running|progress|status|is-complete|cleanup} [phase]"
        exit 1
        ;;
esac
