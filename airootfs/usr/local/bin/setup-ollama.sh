#!/bin/bash
# Setup Ollama - instala si no está disponible
# Usado como fallback si no se instaló durante el build de la ISO

OLLAMA_CMD="ollama"
MEDIA_HELPER="/usr/local/lib/mados-media-helper.sh"

# Check if running on read-only media (DVD/CD)
if [[ -f "$MEDIA_HELPER" ]]; then
    # shellcheck source=/dev/null
    source "$MEDIA_HELPER"
    if ! can_install_software; then
        echo "⚠ Medio óptico (DVD/CD) detectado."
        echo "  Las instalaciones no sobrevivirán un reinicio."
        echo "  Para usar Ollama, instala madOS en disco con: sudo install-mados"
        exit 0
    fi
fi

if command -v "$OLLAMA_CMD" &>/dev/null; then
    echo "✓ Ollama ya está instalado:"
    "$OLLAMA_CMD" --version 2>/dev/null || true
    exit 0
fi

# Verificar conectividad
if ! curl -sf --connect-timeout 5 https://ollama.com/ >/dev/null 2>&1; then
    echo "⚠ No hay conexión a Internet."
    echo "  Conecta a la red primero:"
    echo "    WiFi:     nmtui  o  iwctl station wlan0 connect <SSID>"
    echo "    Ethernet: debería conectarse automáticamente"
    echo ""
    echo "  Luego ejecuta de nuevo: setup-ollama.sh"
    # Exit 0 to not fail the systemd service when run at boot without network
    exit 0
fi

echo "Instalando Ollama..."

# Method: curl install script (official installer from ollama.com)
if curl -fsSL https://ollama.com/install.sh | sh && command -v "$OLLAMA_CMD" &>/dev/null; then
    echo ""
    echo "✓ Ollama instalado correctamente."
    "$OLLAMA_CMD" --version 2>/dev/null || true
    exit 0
fi

echo "⚠ No se pudo instalar Ollama."
echo "  Intenta manualmente: setup-ollama.sh"
# Exit 0 to not fail the service
exit 0
