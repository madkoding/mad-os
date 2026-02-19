#!/bin/bash
# Script simplificado para ejecutar pruebas sin Docker (localmente)

set -e

# Verificar dependencias locales
echo "🔍 Verificando dependencias locales..."

for pkg in python python-gobject gtk3 blueZ blueZ-utils; do
    if ! pacman -Qs "$pkg" > /dev/null 2>&1; then
        echo "⚠️  Instalando $pkg..."
        sudo pacman -S --noconfirm --needed "$pkg"
    fi
done

# Configurar entorno
export MADOS_BT_CONFIG_MODE=test
export PYTHONPATH="airootfs/usr/local/lib:$PYTHONPATH"

# Ejecutar tests con unittest
echo "🚀 Ejecutando pruebas..."
python3 -m unittest tests.test_bluetooth_backend tests.test_bluetooth_frontend tests.test_bluetooth_integration -v
