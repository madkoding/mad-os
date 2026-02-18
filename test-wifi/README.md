# mados-wifi Docker Tests

Tests para verificar que `mados-wifi` funciona correctamente en un entorno Arch Linux.

## Estructura

```
test-wifi/
├── Dockerfile.unit          # Dockerfile para tests (sin GTK)
├── test_unit.py             # Tests unitarios del backend
├── run-unit-tests.sh        # Script para ejecutar tests
├── Makefile                 # Atajos para ejecutar tests
├── README.md                # Este archivo
├── DIAGNOSTIC.md            # Diagnóstico del código
└── LAUNCHER_FIX.md          # Fix aplicado al launcher
```

## Tests

### Unitarios (5/5 PASS):

1. **`_run_command`** - Ejecuta comandos subprocess
2. **`_strip_ansi`** - Elimina códigos ANSI de texto
3. **`_parse_iwctl_table`** - Parsea tablas iwctl
4. **`_cidr_to_netmask`** - Convierte CIDR a máscara de subred
5. **`_split_nmcli_line`** - Parsea líneas nmcli

### Ejecutar tests:

```bash
cd test-wifi
./run-unit-tests.sh

# O usando Makefile:
make test-unit
```

## Desacoplamiento del Código

El código ahora está separado en módulos:

```
mados_wifi/
├── core/          ← Backend SIN GTK
│   ├── __init__.py
│   └── backend.py
├── cli/           ← CLI sin GTK
│   ├── __init__.py
│   ├── manager.py
│   └── command.py
├── app.py         ← GUI GTK
└── __init__.py
```

### Uso:

```python
# Solo backend (sin GTK):
from mados_wifi.core import scan_networks, connect_to_network

# CLI (sin GTK):
mados-wifi-cli scan
mados-wifi-cli connect MyNetwork password123

# GUI (con GTK):
from mados_wifi import WiFiApp
```

## Problemas Encontrados y Corregidos

### 1. Launcher con systemctl
**Problema**: El launcher intentaba usar `systemctl` que no funciona en Docker.

**Fix**: Añadir fallbacks para cuando systemctl no está disponible y usar `|| true` para evitar fallos.

### 2. Permisos de ejecución
**Problema**: El archivo `mados-wifi` no tenía permisos de ejecución.

**Fix**: `chmod +x` aplicado al archivo.

## Resultados

```
Total: 5/5 tests passed

PASS: _run_command
PASS: _strip_ansi
PASS: _parse_iwctl_table
PASS: _cidr_to_netmask
PASS: _split_nmcli_line
```

## Limitaciones

- No se puede probar escaneo/conexión WiFi sin hardware real
- Los tests unitarios verifican la lógica del backend, no el hardware
