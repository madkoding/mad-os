#!/bin/bash
# Setup OpenCode - instala si no está disponible
# Usado como fallback si no se instaló durante el build de la ISO

set -euo pipefail

OPENCODE_CMD="opencode"

if command -v "$OPENCODE_CMD" &>/dev/null; then
    echo "✓ OpenCode ya está instalado:"
    "$OPENCODE_CMD" --version
    exit 0
fi

# Verificar que npm esté disponible
if ! command -v npm &>/dev/null; then
    echo "✗ Error: npm no está instalado. No se puede instalar OpenCode."
    exit 1
fi

# Verificar conectividad
if ! curl -sf --connect-timeout 5 https://registry.npmjs.org/ >/dev/null 2>&1; then
    echo "⚠ No hay conexión a Internet."
    echo "  Conecta a la red primero:"
    echo "    WiFi:     iwctl station wlan0 connect <SSID>"
    echo "    Ethernet: debería conectarse automáticamente"
    echo ""
    echo "  Luego ejecuta de nuevo: setup-opencode.sh"
    # Exit 0 to not fail the systemd service when run at boot without network
    exit 0
fi

echo "Instalando OpenCode..."
if npm install -g opencode-ai; then
    echo ""
    echo "✓ OpenCode instalado correctamente."
    "$OPENCODE_CMD" --version
else
    echo "⚠ Error al instalar OpenCode."
    echo "  Intenta manualmente: setup-opencode.sh"
    # Exit 0 to not fail the service
    exit 0
fi
