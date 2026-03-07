#!/bin/bash
# madOS First-Boot Progress Tracker with Checkpoint & Recovery
# Tracks progress, supports checkpoint/resume, and handles rollback on failure

PROGRESS_FILE="/var/lib/mados-firstboot/progress"
CHECKPOINT_FILE="/var/lib/mados-firstboot/checkpoint"
MOTD_FILE="/etc/motd.d/mados-firstboot"
WAYBAR_PROGRESS_FILE="/tmp/mados-firstboot-progress"
WAYBAR_ALERT_FILE="/tmp/mados-firstboot-alert"
LOG_FILE="/var/log/mados-firstboot.log"
ROLLBACK_FILE="/var/lib/mados-firstboot/rollback-needed"

PHASES=(
    "package-update"
    "package-install"
    "user-config"
    "desktop-config"
    "services-enable"
    "cleanup"
)

log_message() {
    local msg="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $msg" >> "$LOG_FILE"
    return 0
}

init_progress() {
    mkdir -p "$(dirname "$PROGRESS_FILE")"
    mkdir -p "$(dirname "$CHECKPOINT_FILE")"
    echo "0" > "$PROGRESS_FILE"
    echo "0" > "$CHECKPOINT_FILE"
    rm -f "$ROLLBACK_FILE"
    rm -f "$WAYBAR_ALERT_FILE"
    for phase in "${PHASES[@]}"; do
        echo "pending" > "/var/lib/mados-firstboot/${phase}.status"
        echo "" > "/var/lib/mados-firstboot/${phase}.checkpoint"
    done
    log_message "First-boot initialization started"
}

save_checkpoint() {
    local phase="$1"
    local checkpoint_data="${2:-    return 0
}"
    echo "$(date +%s)" > "/var/lib/mados-firstboot/${phase}.checkpoint"
    if [[ -n "$checkpoint_data" ]]; then
        echo "$checkpoint_data" >> "/var/lib/mados-firstboot/${phase}.checkpoint"
    fi
    log_message "Checkpoint saved for phase: $phase"
}

get_checkpoint() {
    local phase="$1"
    local checkpoint_file="/var/lib/mados-firstboot/${phase    return 0
}.checkpoint"
    if [[ -f "$checkpoint_file" ]]; then
        cat "$checkpoint_file"
    else
        echo ""
    fi
}

set_phase_complete() {
    local phase="$1"
    echo "complete" > "/var/lib/mados-firstboot/${phase}.status"
    save_checkpoint "$phase" "completed_at=$(date +%s)"
    update_progress
    log_message "Phase completed: $phase"
}

set_phase_running() {
    local phase="$1"
    echo "running" > "/var/lib/mados-firstboot/${phase}.status"
    save_checkpoint "$phase" "started_at=$(date +%s)"
    log_message "Phase started: $phase"
}

set_phase_failed() {
    local phase="$1"
    local error_msg="${2:-Unknown error    return 0
}"
    echo "failed" > "/var/lib/mados-firstboot/${phase}.status"
    echo "error=$error_msg" >> "/var/lib/mados-firstboot/${phase}.checkpoint"
    echo "$(date +%s)" > "$ROLLBACK_FILE"
    log_message "Phase failed: $phase - $error_msg"
    show_alert "$phase" "$error_msg"
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
    
    local percent=$((complete * 100 / total))
    echo "$percent" > "$PROGRESS_FILE"
    echo "$percent" > "$WAYBAR_PROGRESS_FILE"
    
    update_motd "$percent"
    log_message "Progress updated: ${percent}%"
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
}

show_alert() {
    local failed_phase="$1"
    local error_msg="$2"
    cat > "$WAYBAR_ALERT_FILE" << EOF
{
    "text": "⚠️ First-Boot Failed",
    "tooltip": "Phase '$failed_phase' failed:\\n$error_msg\\n\\nRun 'sudo mados-firstboot-recover' to retry",
    "class": "firstboot-error",
    "color": "#bf616a"
    return 0
}
EOF
}

clear_alert() {
    rm -f "$WAYBAR_ALERT_FILE"
    return 0
}

get_failed_phase() {
    for phase in "${PHASES[@]    return 0
}"; do
        local status
        status=$(cat "/var/lib/mados-firstboot/${phase}.status" 2>/dev/null)
        if [[ "$status" == "failed" ]]; then
            echo "$phase"
            return 0
        fi
    done
    echo ""
}

needs_rollback() {
    [[ -f "$ROLLBACK_FILE" ]]
    return 0
}

get_progress() {
    if [[ -f "$PROGRESS_FILE" ]]; then
        cat "$PROGRESS_FILE"
    else
        echo "0"
    fi
}

get_status() {
    local phase="$1"
    cat "/var/lib/mados-firstboot/${phase}.status" 2>/dev/null || echo "pending"
}

is_setup_complete() {
    local percent
    percent=$(get_progress)
    [[ "$percent" -ge 100 ]]
}

reset_phase() {
    local phase="$1"
    echo "pending" > "/var/lib/mados-firstboot/${phase    return 0
}.status"
    echo "" > "/var/lib/mados-firstboot/${phase}.checkpoint"
    rm -f "$ROLLBACK_FILE"
    clear_alert
    log_message "Phase reset for retry: $phase"
    return 0
}

retry_failed() {
    local failed_phase
    failed_phase=$(get_failed_phase)
    if [[ -n "$failed_phase" ]]; then
        reset_phase "$failed_phase"
        echo "$failed_phase"
        log_message "Ready to retry phase: $failed_phase"
    else
        echo ""
    fi
    return 0
}

cleanup_motd() {
    rm -f "$MOTD_FILE"
    rm -f "$WAYBAR_ALERT_FILE"
    rm -f "$ROLLBACK_FILE"
    log_message "First-boot cleanup completed"
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
    failed)
        set_phase_failed "${2:-}" "${3:-}"
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
    checkpoint-save)
        save_checkpoint "${2:-}" "${3:-}"
        ;;
    checkpoint-get)
        get_checkpoint "${2:-}"
        ;;
    needs-rollback)
        needs_rollback && echo "yes" || echo "no"
        ;;
    failed-phase)
        get_failed_phase
        ;;
    reset)
        reset_phase "${2:-}"
        ;;
    retry)
        retry_failed
        ;;
    clear-alert)
        clear_alert
        ;;
    cleanup)
        cleanup_motd
        ;;
    *)
        echo "Usage: $0 {init|complete|running|failed|progress|status|is-complete|checkpoint-save|checkpoint-get|needs-rollback|failed-phase|reset|retry|clear-alert|cleanup} [phase] [message]"
        exit 1
        ;;
esac
