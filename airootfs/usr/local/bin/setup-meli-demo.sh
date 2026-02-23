#!/bin/bash
# setup-meli-demo.sh - Descarga e instala Meli Tech Demo desde itch.io
# Requiere conexión a Internet. Instala en persistencia si está disponible,
# de lo contrario instala en /opt/meli-demo (se perderá al reiniciar).

set -euo pipefail

GAME_URL="https://williamsmygl.itch.io/meli-a-tech-demo-by-williamsmygl"
GAME_NAME="Meli Tech Demo"
INSTALL_DIR="/opt/meli-demo"
PERSIST_DIR="/mnt/persistence/opt/meli-demo"
DOWNLOAD_TMP="/tmp/meli-demo-linux.zip"
EXECUTABLE_MARKER=".game-executable"
MEDIA_HELPER="/usr/local/lib/mados-media-helper.sh"
MIN_SPACE_MB=600  # Minimum free space needed (400MB zip + extraction)

# --- Helper functions ---

log_info() {
    echo "  $*"
    logger -p user.info -t setup-meli-demo "$*" 2>/dev/null || true
}

log_warn() {
    echo "  ⚠ $*"
    logger -p user.warning -t setup-meli-demo "$*" 2>/dev/null || true
}

log_error() {
    echo "  ✗ $*"
    logger -p user.error -t setup-meli-demo "$*" 2>/dev/null || true
}

log_ok() {
    echo "  ✓ $*"
    logger -p user.info -t setup-meli-demo "$*" 2>/dev/null || true
}

find_game_executable() {
    local dir="$1"

    # Check marker file first
    if [[ -f "$dir/$EXECUTABLE_MARKER" ]]; then
        local exe
        exe=$(cat "$dir/$EXECUTABLE_MARKER")
        if [[ -x "$exe" ]]; then
            echo "$exe"
            return 0
        fi
    fi

    # Search for common game executable patterns
    local exe=""

    # Pattern 1: Shell launcher script (Unreal Engine style)
    exe=$(find "$dir" -maxdepth 2 -name "*.sh" -executable -not -name "setup-*" 2>/dev/null | head -1)
    [[ -n "$exe" ]] && { echo "$exe"; return 0; }

    # Pattern 2: Godot/Unity x86_64 binary
    exe=$(find "$dir" -maxdepth 2 -name "*.x86_64" -executable 2>/dev/null | head -1)
    [[ -n "$exe" ]] && { echo "$exe"; return 0; }

    # Pattern 3: Binary named MeliDemo or similar
    exe=$(find "$dir" -maxdepth 3 -name "MeliDemo*" -executable -not -name "*.so" -not -name "*.debug" 2>/dev/null | head -1)
    [[ -n "$exe" ]] && { echo "$exe"; return 0; }

    # Pattern 4: Binary named Meli* (case insensitive)
    exe=$(find "$dir" -maxdepth 3 -iname "meli*" -executable -not -name "*.so" -not -name "*.debug" -not -name "*.sh" 2>/dev/null | head -1)
    [[ -n "$exe" ]] && { echo "$exe"; return 0; }

    # Pattern 5: Any ELF executable in Binaries/Linux/
    exe=$(find "$dir" -maxdepth 4 -path "*/Binaries/Linux/*" -executable -type f 2>/dev/null | head -1)
    [[ -n "$exe" ]] && { echo "$exe"; return 0; }

    # Pattern 6: Any executable in the top level (last resort)
    exe=$(find "$dir" -maxdepth 1 -executable -type f -not -name ".*" 2>/dev/null | head -1)
    [[ -n "$exe" ]] && { echo "$exe"; return 0; }

    return 1
}

check_already_installed() {
    # Check persistence location
    if [[ -f "$PERSIST_DIR/$EXECUTABLE_MARKER" ]]; then
        local exe
        exe=$(cat "$PERSIST_DIR/$EXECUTABLE_MARKER")
        if [[ -x "$exe" ]]; then
            return 0
        fi
    fi

    # Check standard location
    if [[ -f "$INSTALL_DIR/$EXECUTABLE_MARKER" ]]; then
        local exe
        exe=$(cat "$INSTALL_DIR/$EXECUTABLE_MARKER")
        if [[ -x "$exe" ]]; then
            return 0
        fi
    fi

    return 1
}

get_free_space_mb() {
    local dir="$1"
    df -BM "$dir" 2>/dev/null | awk 'NR==2 {gsub(/M/,"",$4); print $4}'
}

# --- Main logic ---

main() {
    echo ""
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║       Meli Tech Demo - Instalador        ║"
    echo "  ║     by WilliamsMyGL (itch.io)            ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo ""

    # Check if already installed
    if check_already_installed; then
        log_ok "$GAME_NAME ya está instalado."
        return 0
    fi

    # Check for read-only media (DVD/CD)
    if [[ -f "$MEDIA_HELPER" ]]; then
        # shellcheck source=/dev/null
        source "$MEDIA_HELPER"
        if ! can_install_software; then
            log_warn "Medio óptico (DVD/CD) detectado."
            log_info "No se puede instalar $GAME_NAME en medio de solo lectura."
            log_info "Instala madOS en disco con: sudo install-mados"
            return 0
        fi
    fi

    # Check network connectivity
    log_info "Verificando conexión a Internet..."
    if ! curl -sf --connect-timeout 5 https://itch.io/ >/dev/null 2>&1; then
        log_warn "No hay conexión a Internet."
        log_info "Conecta a la red primero:"
        log_info "  WiFi:     nmtui  o  iwctl station wlan0 connect <SSID>"
        log_info "  Ethernet: debería conectarse automáticamente"
        log_info ""
        log_info "Luego ejecuta de nuevo: setup-meli-demo.sh"
        return 0
    fi
    log_ok "Conexión a Internet disponible."

    # Determine install location (prefer persistence for disk space)
    local target_dir="$INSTALL_DIR"
    local using_persistence=false

    if [[ -d "/mnt/persistence" ]] && [[ -w "/mnt/persistence" ]]; then
        local persist_space
        persist_space=$(get_free_space_mb "/mnt/persistence")
        if [[ -n "$persist_space" ]] && [[ "$persist_space" -ge "$MIN_SPACE_MB" ]]; then
            target_dir="$PERSIST_DIR"
            using_persistence=true
            log_ok "Usando almacenamiento persistente (${persist_space}MB libre)."
        else
            log_warn "Persistencia disponible pero sin espacio suficiente (${persist_space:-?}MB < ${MIN_SPACE_MB}MB)."
        fi
    fi

    if [[ "$using_persistence" == false ]]; then
        # Check available RAM/overlay space
        local overlay_space
        overlay_space=$(get_free_space_mb "/opt")
        if [[ -n "$overlay_space" ]] && [[ "$overlay_space" -lt "$MIN_SPACE_MB" ]]; then
            log_error "Espacio insuficiente (${overlay_space}MB disponible, se necesitan ${MIN_SPACE_MB}MB)."
            log_info "Habilita persistencia USB o libera espacio."
            return 1
        fi
        log_warn "Sin persistencia: el juego se perderá al reiniciar."
    fi

    # Download the game
    log_info "Descargando $GAME_NAME desde itch.io..."
    log_info "URL: $GAME_URL"
    echo ""

    if ! python3 -c "from mados_meli_demo.download_itch import download_from_itch; exit(0 if download_from_itch('$GAME_URL', 'Linux', '$DOWNLOAD_TMP') else 1)"; then
        log_error "No se pudo descargar automáticamente."
        log_info ""
        log_info "Descarga manual:"
        log_info "  1. Abre: $GAME_URL"
        log_info "  2. Descarga la versión 'For Linux'"
        log_info "  3. Extrae el ZIP en $target_dir"
        log_info "  4. Ejecuta: setup-meli-demo.sh"
        return 1
    fi

    # Verify download exists
    if [[ ! -f "$DOWNLOAD_TMP" ]]; then
        log_error "Archivo descargado no encontrado."
        return 1
    fi

    local download_size
    download_size=$(du -m "$DOWNLOAD_TMP" | cut -f1)
    log_ok "Descarga completada (${download_size}MB)."

    # Extract the game
    log_info "Extrayendo $GAME_NAME..."
    mkdir -p "$target_dir"

    # Use bsdtar (always available on Arch) with fallback to unzip
    if command -v bsdtar >/dev/null 2>&1; then
        if ! bsdtar -xf "$DOWNLOAD_TMP" -C "$target_dir" 2>/dev/null; then
            log_warn "bsdtar falló, intentando con unzip..."
            if command -v unzip >/dev/null 2>&1; then
                unzip -o "$DOWNLOAD_TMP" -d "$target_dir" || {
                    log_error "No se pudo extraer el archivo ZIP."
                    rm -f "$DOWNLOAD_TMP"
                    return 1
                }
            else
                # Python fallback
                python3 -c "
import zipfile, sys
with zipfile.ZipFile('$DOWNLOAD_TMP', 'r') as z:
    z.extractall('$target_dir')
" || {
                    log_error "No se pudo extraer el archivo ZIP."
                    rm -f "$DOWNLOAD_TMP"
                    return 1
                }
            fi
        fi
    fi

    # Clean up download
    rm -f "$DOWNLOAD_TMP"

    # Make game files executable
    find "$target_dir" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
    find "$target_dir" -name "*.x86_64" -exec chmod +x {} \; 2>/dev/null || true
    find "$target_dir" -path "*/Binaries/Linux/*" -type f -exec chmod +x {} \; 2>/dev/null || true

    # Find and record the game executable
    local game_exe
    game_exe=$(find_game_executable "$target_dir")

    if [[ -z "$game_exe" ]]; then
        log_warn "No se encontró un ejecutable automáticamente."
        log_info "Contenido extraído en: $target_dir"
        log_info "Busca el ejecutable del juego manualmente:"
        log_info "  ls -la $target_dir"
        log_info "  find $target_dir -executable -type f"
        return 1
    fi

    # Save executable path
    echo "$game_exe" > "$target_dir/$EXECUTABLE_MARKER"
    chmod +x "$game_exe"

    # Create symlink from standard location if using persistence
    if [[ "$using_persistence" == true ]] && [[ "$target_dir" != "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        ln -sf "$target_dir" "$INSTALL_DIR"
    fi

    echo ""
    log_ok "$GAME_NAME instalado correctamente."
    log_info "Ejecutable: $game_exe"
    log_info "Ubicación: $target_dir"
    if [[ "$using_persistence" == true ]]; then
        log_ok "Instalado en persistencia (sobrevive reinicios)."
    else
        log_warn "Instalado en overlay (se perderá al reiniciar)."
    fi
    echo ""

    return 0
}

main "$@"
