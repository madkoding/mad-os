#!/bin/bash
# Script de prueba rápido para verificar Docker funcionando
# Solo verifica que Python y las dependencias estén instaladas

echo "🧪 Verificando ambiente Docker..."
echo "================================"

echo -n "✓ Python: "
python3 --version

echo -n "✓ Python-gobject: "
python3 -c "from gi.repository import Gtk, GLib; print('OK')" 2>&1 || echo "MISSING"

echo -n "✓ BlueZ: "
which bluetoothctl || echo "MISSING"

echo -n "✓ GTK3: "
python3 -c "from gi.repository import Gtk; print('OK')" 2>&1 || echo "MISSING"

echo ""
echo "📋 Archivos verificados:"
ls -la tests/*.py 2>/dev/null | head -5 || echo "Tests folder empty"

echo ""
echo "🚀 Preparado para ejecutar pruebas en Docker!"
echo ""
echo "Usa:"
echo "  docker build -t mados-bluetooth-tests -f docker/Dockerfile ."
echo "  docker run --rm -it mados-bluetooth-tests"
