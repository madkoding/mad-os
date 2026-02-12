#!/usr/bin/env bash
# Show persistence info on first login

PERSIST_INFO_SHOWN="/tmp/.mados-persistence-info-shown"

# Only show once per boot
if [ -f "$PERSIST_INFO_SHOWN" ]; then
    exit 0
fi

# Only in live environment
if [ ! -d /run/archiso ]; then
    exit 0
fi

# Check if we're on a TTY
if [ -t 0 ] && [ -t 1 ]; then
    cat << 'INNER_EOF'

╔════════════════════════════════════════════════════════════════╗
║                    madOS Live Environment                      ║
╚════════════════════════════════════════════════════════════════╝

💾 Persistent Storage: Automatically configured if USB has free space

   Check status:        mados-persistence status
   Enable manually:     sudo mados-persistence enable
   View documentation:  less /usr/share/doc/madOS/PERSISTENCE.md

🔧 Quick Commands:
   • Install madOS:     sudo install-mados
   • AI Assistant:      opencode
   • Package Manager:   sudo pacman -S <package>

INNER_EOF
    
    # Show persistence status if configured
    if command -v mados-persistence >/dev/null 2>&1; then
        if lsblk -nlo LABEL 2>/dev/null | grep -q "persistence"; then
            echo "✓ Persistent storage is enabled"
            echo ""
        fi
    fi
    
    # Mark as shown
    touch "$PERSIST_INFO_SHOWN"
fi
