#!/bin/bash
# Setup Claude Code - instala si no está disponible
# Usado como fallback si no se instaló durante el build de la ISO

set -euo pipefail

CLAUDE_CMD="claude"

if command -v "$CLAUDE_CMD" &>/dev/null; then
    echo "✓ Claude Code ya está instalado:"
    "$CLAUDE_CMD" --version
    exit 0
fi

# Verificar que npm esté disponible
if ! command -v npm &>/dev/null; then
    echo "✗ Error: npm no está instalado. No se puede instalar Claude Code."
    exit 1
fi

# Verificar conectividad
if ! curl -sf --connect-timeout 5 https://registry.npmjs.org/ >/dev/null 2>&1; then
    echo "✗ Error: No hay conexión a Internet."
    echo "  Conecta a la red primero:"
    echo "    WiFi:     iwctl station wlan0 connect <SSID>"
    echo "    Ethernet: debería conectarse automáticamente"
    echo ""
    echo "  Luego ejecuta de nuevo: setup-claude-code.sh"
    exit 1
fi

echo "Instalando Claude Code..."
if npm install -g @anthropic-ai/claude-code; then
    echo ""
    echo "✓ Claude Code instalado correctamente."
    "$CLAUDE_CMD" --version
else
    echo "✗ Error al instalar Claude Code."
    echo "  Intenta manualmente: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
