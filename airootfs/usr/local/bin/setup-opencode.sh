#!/bin/bash
# Setup OpenCode - instala si no está disponible
# Usado como fallback si no se instaló durante el build de la ISO

OPENCODE_CMD="opencode"
INSTALL_DIR="/usr/local/bin"

if command -v "$OPENCODE_CMD" &>/dev/null; then
    echo "✓ OpenCode ya está instalado:"
    "$OPENCODE_CMD" --version 2>/dev/null || true
    exit 0
fi

# Verificar conectividad
if ! curl -sf --connect-timeout 5 https://opencode.ai/ >/dev/null 2>&1; then
    echo "⚠ No hay conexión a Internet."
    echo "  Conecta a la red primero:"
    echo "    WiFi:     nmtui  o  iwctl station wlan0 connect <SSID>"
    echo "    Ethernet: debería conectarse automáticamente"
    echo ""
    echo "  Luego ejecuta de nuevo: setup-opencode.sh"
    # Exit 0 to not fail the systemd service when run at boot without network
    exit 0
fi

echo "Instalando OpenCode..."

# Method 1: curl install script (most reliable, downloads binary directly)
if curl -fsSL https://opencode.ai/install | OPENCODE_INSTALL_DIR="$INSTALL_DIR" bash; then
    if command -v "$OPENCODE_CMD" &>/dev/null; then
        echo ""
        echo "✓ OpenCode instalado correctamente."
        "$OPENCODE_CMD" --version 2>/dev/null || true
        exit 0
    fi
fi

echo "⚠ Método curl falló, intentando con npm..."

# Method 2: npm install (fallback)
if command -v npm &>/dev/null; then
    if npm install -g --unsafe-perm opencode-ai; then
        if command -v "$OPENCODE_CMD" &>/dev/null; then
            echo ""
            echo "✓ OpenCode instalado correctamente via npm."
            "$OPENCODE_CMD" --version 2>/dev/null || true
            exit 0
        fi
    fi
fi

echo "⚠ No se pudo instalar OpenCode."
echo "  Intenta manualmente: setup-opencode.sh"
# Exit 0 to not fail the service
exit 0
