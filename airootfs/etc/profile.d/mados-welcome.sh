#!/usr/bin/env bash
# Show madOS welcome info on first login

WELCOME_INFO_SHOWN="/tmp/.mados-welcome-info-shown"

# Only show once per boot
if [[ -f "$WELCOME_INFO_SHOWN" ]]; then
    exit 0
fi

if [[ ! -d /run/archiso ]]; then
    exit 0
fi

if [[ -t 0 && -t 1 ]]; then
    cat << 'INNER_EOF'

╔════════════════════════════════════════════════════════════════╗
║                    madOS Live Environment                      ║
╚════════════════════════════════════════════════════════════════╝

🔧 Quick Commands:
   • Install madOS:     sudo install-mados
   • AI Assistant:      opencode
   • Package Manager:   sudo pacman -S <package>

INNER_EOF
    
    # Mark as shown
    touch "$WELCOME_INFO_SHOWN"
fi
