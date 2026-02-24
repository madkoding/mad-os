#!/bin/bash
# setup-onlyoffice.sh - Descarga e instala ONLYOFFICE Desktop Editors (AppImage)
# Usado como servicio de primer arranque o ejecutado manualmente.

set -euo pipefail

APPIMAGE_NAME="DesktopEditors-x86_64.AppImage"
DOWNLOAD_URL="https://github.com/ONLYOFFICE/DesktopEditors/releases/latest/download/${APPIMAGE_NAME}"
INSTALL_DIR="/opt/onlyoffice"
APPIMAGE_PATH="${INSTALL_DIR}/${APPIMAGE_NAME}"
WRAPPER_PATH="/usr/local/bin/onlyoffice"
DESKTOP_FILE="/usr/share/applications/onlyoffice-desktopeditors.desktop"
ICON_PATH="/usr/share/pixmaps/onlyoffice-desktopeditors.png"
MEDIA_HELPER="/usr/local/lib/mados-media-helper.sh"

# Check if running on read-only media (DVD/CD)
if [[ -f "$MEDIA_HELPER" ]]; then
    # shellcheck source=/dev/null
    source "$MEDIA_HELPER"
    if ! can_install_software; then
        echo "⚠ Medio óptico (DVD/CD) detectado."
        echo "  Las instalaciones no sobrevivirán un reinicio."
        echo "  Para usar ONLYOFFICE, instala madOS en disco con: sudo install-mados"
        exit 0
    fi
fi

# Check if already installed
if [[ -x "$APPIMAGE_PATH" ]]; then
    echo "✓ ONLYOFFICE Desktop Editors ya está instalado."
    exit 0
fi

# Verify network connectivity
if ! curl -sf --connect-timeout 5 https://github.com/ >/dev/null 2>&1; then
    echo "⚠ No hay conexión a Internet."
    echo "  Conecta a la red primero:"
    echo "    WiFi:     nmtui  o  iwctl station wlan0 connect <SSID>"
    echo "    Ethernet: debería conectarse automáticamente"
    echo ""
    echo "  Luego ejecuta de nuevo: sudo setup-onlyoffice.sh"
    # Exit 0 to not fail the systemd service when run at boot without network
    exit 0
fi

echo "Instalando ONLYOFFICE Desktop Editors..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Download AppImage
echo "Descargando desde GitHub (esto puede tardar unos minutos)..."
if curl -fSL --progress-bar -o "$APPIMAGE_PATH" "$DOWNLOAD_URL"; then
    chmod +x "$APPIMAGE_PATH"
    echo "✓ AppImage descargado correctamente."
else
    echo "⚠ No se pudo descargar ONLYOFFICE."
    echo "  Intenta manualmente: sudo setup-onlyoffice.sh"
    rm -f "$APPIMAGE_PATH"
    exit 0
fi

# Create wrapper script
cat > "$WRAPPER_PATH" <<'EOFWRAPPER'
#!/bin/bash
exec /opt/onlyoffice/DesktopEditors-x86_64.AppImage --no-sandbox "$@"
EOFWRAPPER
chmod 755 "$WRAPPER_PATH"

# Extract icon from AppImage (if possible), otherwise use a placeholder
if "$APPIMAGE_PATH" --appimage-extract "*.png" >/dev/null 2>&1; then
    EXTRACTED_ICON=$(find squashfs-root -maxdepth 2 -name "*.png" -type f 2>/dev/null | head -1)
    if [[ -n "$EXTRACTED_ICON" ]]; then
        mkdir -p "$(dirname "$ICON_PATH")"
        cp "$EXTRACTED_ICON" "$ICON_PATH"
    fi
    rm -rf squashfs-root
fi

# Create .desktop entry
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=ONLYOFFICE Desktop Editors
Comment=Edit office documents (text, spreadsheets, presentations)
Comment[es]=Editar documentos de oficina (texto, hojas de cálculo, presentaciones)
Exec=/usr/local/bin/onlyoffice %U
Icon=onlyoffice-desktopeditors
Terminal=false
Type=Application
Categories=Office;WordProcessor;Spreadsheet;Presentation;
MimeType=application/vnd.oasis.opendocument.text;application/vnd.oasis.opendocument.spreadsheet;application/vnd.oasis.opendocument.presentation;application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;application/vnd.openxmlformats-officedocument.presentationml.presentation;application/msword;application/vnd.ms-excel;application/vnd.ms-powerpoint;
StartupWMClass=DesktopEditors
EOF

echo ""
echo "✓ ONLYOFFICE Desktop Editors instalado correctamente."
echo "  Ejecutar: onlyoffice"
echo "  También disponible en el menú de aplicaciones."
exit 0
