#!/bin/bash
# setup-opencode.sh - Instala OpenCode AI Assistant
# Requiere conexión a Internet. Instala en persistencia si está disponible,
# de lo contrario instala en /usr/local/bin

set -euo pipefail

OPENCODE_CMD="opencode"
INSTALL_DIR="/usr/local/bin"
PERSIST_DIR="/mnt/persistence/usr/local/bin"
NPM_INSTALL_DIR="/usr/local/lib/opencode"
MEDIA_HELPER="/usr/local/lib/mados-media-helper.sh"

log_info() {
    echo "  $*"
    logger -p user.info -t setup-opencode "$*" 2>/dev/null || true
}

log_warn() {
    echo "  ⚠ $*"
    logger -p user.warning -t setup-opencode "$*" 2>/dev/null || true
}

log_error() {
    echo "  ✗ $*"
    logger -p user.error -t setup-opencode "$*" 2>/dev/null || true
}

log_ok() {
    echo "  ✓ $*"
    logger -p user.info -t setup-opencode "$*" 2>/dev/null || true
}

check_already_installed() {
    if command -v "$OPENCODE_CMD" &>/dev/null; then
        return 0
    fi
    if [[ -x "$INSTALL_DIR/$OPENCODE_CMD" ]]; then
        return 0
    fi
    if [[ -x "$PERSIST_DIR/$OPENCODE_CMD" ]]; then
        # Ensure symlink exists if using persistence
        if [[ ! -e "$INSTALL_DIR/$OPENCODE_CMD" ]]; then
            ln -sf "$PERSIST_DIR/$OPENCODE_CMD" "$INSTALL_DIR/$OPENCODE_CMD" 2>/dev/null || true
        fi
        return 0
    fi
    return 1
}

ensure_opencode_available() {
    # Ensure opencode is in PATH by creating necessary symlinks
    local found_opencode=""
    
    # Find opencode binary
    if [[ -x "$INSTALL_DIR/$OPENCODE_CMD" ]]; then
        found_opencode="$INSTALL_DIR/$OPENCODE_CMD"
    elif [[ -x "$PERSIST_DIR/$OPENCODE_CMD" ]]; then
        found_opencode="$PERSIST_DIR/$OPENCODE_CMD"
    else
        # Search for it
        found_opencode=$(find "$INSTALL_DIR" "$PERSIST_DIR" /usr/local/lib/opencode -name "opencode" -type f -executable 2>/dev/null | head -1 || true)
    fi
    
    if [[ -n "$found_opencode" ]]; then
        # Ensure it's symlinked to INSTALL_DIR
        if [[ "$found_opencode" != "$INSTALL_DIR/$OPENCODE_CMD" ]]; then
            ln -sf "$found_opencode" "$INSTALL_DIR/$OPENCODE_CMD" 2>/dev/null || true
        fi
        return 0
    fi
    
    return 1
}

install_via_curl() {
    log_info "Instalando OpenCode via curl..."

    local target_dir="$INSTALL_DIR"
    local using_persistence=false

    if [[ -d "/mnt/persistence" ]] && [[ -w "/mnt/persistence/usr/local/bin" ]]; then
        target_dir="$PERSIST_DIR"
        using_persistence=true
        mkdir -p "$target_dir"
    elif [[ -d "/mnt/persistence" ]] && [[ -w "/mnt/persistence" ]]; then
        target_dir="$PERSIST_DIR"
        using_persistence=true
        mkdir -p "$target_dir"
    fi

    # Create temp directory for installation
    local temp_dir
    temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    if curl -fsSL https://opencode.ai/install | INSTALL_DIR="$temp_dir" bash 2>&1; then
        # Find the installed binary
        local opencode_binary
        opencode_binary=$(find "$temp_dir" -name "opencode" -type f -executable 2>/dev/null | head -1 || true)
        
        if [[ -n "$opencode_binary" ]]; then
            # Copy to target location
            cp "$opencode_binary" "$target_dir/$OPENCODE_CMD"
            chmod +x "$target_dir/$OPENCODE_CMD"
            
            # Clean up temp dir
            rm -rf "$temp_dir"
            
            log_ok "OpenCode instalado via curl"

            if [[ "$using_persistence" == true ]]; then
                ln -sf "$target_dir/$OPENCODE_CMD" "$INSTALL_DIR/$OPENCODE_CMD" 2>/dev/null || true
            fi
            return 0
        fi
    fi
    
    # Clean up on failure
    rm -rf "$temp_dir"
    return 1
}

install_via_npm() {
    log_info "Intentando instalación via npm..."

    if ! command -v npm &>/dev/null; then
        log_warn "npm no está disponible"
        return 1
    fi

    local target_dir="$NPM_INSTALL_DIR"
    local using_persistence=false

    if [[ -d "/mnt/persistence" ]] && [[ -w "/mnt/persistence/usr/local/lib" ]]; then
        target_dir="$PERSIST_DIR"
        using_persistence=true
        mkdir -p "$target_dir"
    elif [[ -d "/mnt/persistence" ]] && [[ -w "/mnt/persistence" ]]; then
        target_dir="$PERSIST_DIR"
        using_persistence=true
        mkdir -p "$target_dir"
    fi

    mkdir -p "$target_dir"

    if npm install -g opencode-ai --prefix "$target_dir" 2>&1; then
        local npm_bin="$target_dir/node_modules/.bin"

        if [[ -x "$npm_bin/opencode" ]]; then
            ln -sf "$npm_bin/opencode" "$INSTALL_DIR/$OPENCODE_CMD" 2>/dev/null || true
            log_ok "OpenCode instalado via npm"
            return 0
        fi
    fi

    return 1
}

main() {
    echo ""
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║       OpenCode AI - Instalador          ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo ""

    # First ensure any existing opencode is properly linked
    ensure_opencode_available

    if check_already_installed; then
        local version
        version=$("$INSTALL_DIR/$OPENCODE_CMD" --version 2>/dev/null || echo "desconocida")
        log_ok "OpenCode ya está instalado (versión: $version)"
        return 0
    fi

    if [[ -f "$MEDIA_HELPER" ]]; then
        source "$MEDIA_HELPER"
        if ! can_install_software; then
            log_warn "Medio óptico (DVD/CD) detectado."
            log_info "No se puede instalar OpenCode en medio de solo lectura."
            log_info "Instala madOS en disco con: sudo install-mados"
            return 0
        fi
    fi

    log_info "Verificando conexión a Internet..."
    if ! curl -sf --connect-timeout 5 https://opencode.ai/ >/dev/null 2>&1; then
        log_warn "No hay conexión a Internet."
        log_info "Conecta a la red primero:"
        log_info "  WiFi:     nmtui  o  iwctl station wlan0 connect <SSID>"
        log_info "  Ethernet: debería conectarse automáticamente"
        log_info ""
        log_info "Luego ejecuta de nuevo: setup-opencode.sh"
        return 0
    fi
    log_ok "Conexión a Internet disponible."

    if install_via_curl; then
        :
    elif install_via_npm; then
        :
    else
        log_error "No se pudo instalar OpenCode."
        log_info "Métodos intentados:"
        log_info "  1. curl -fsSL https://opencode.ai/install | bash"
        log_info "  2. npm install -g opencode-ai"
        log_info ""
        log_info "Intenta instalar manualmente y reporta el error."
        return 1
    fi
    
    # Ensure it's available after installation
    ensure_opencode_available

    echo ""
    local final_version
    final_version=$("$INSTALL_DIR/$OPENCODE_CMD" --version 2>/dev/null || echo "desconocida")
    log_ok "OpenCode instalado correctamente (versión: $final_version)"
    echo ""
    log_info "Para usar OpenCode, ejecuta: opencode"
    echo ""

    return 0
}

main "$@"
