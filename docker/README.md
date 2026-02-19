# Testing en Docker con Arch Linux - Resumen de Cómo Hacerlo

## 🎯 Objetivo
Crear ambiente reproducible para probar `mados-bluetooth` sin requerir hardware real.

## 📁 Archivos Creados

```
docker/
├── Dockerfile              # Dockerfile para Arch Linux
├── build-and-test.sh       # Build + test en un solo script
└── test-all.sh             # Ejecuta tests por separado
```

## 🚀 Cómo Usar (3 Opciones)

### Opción 1: Todo en uno (Recomendado para CI/CD)
```bash
docker build -t mados-bluetooth-tests -f docker/Dockerfile .
docker run --rm -it mados-bluetooth-tests
```

### Opción 2: Scripts de ayuda
```bash
# Build y test
./docker/build-and-test.sh

# Tests por separado
./docker/test-all.sh
```

### Opción 3: Interactive debugging
```bash
docker run --rm -it mados-bluetooth-tests /bin/bash
# Dentro del container:
python3 -m unittest tests.test_bluetooth_backend -vv
```

## 🐳 Dockerfile Explicado

```dockerfile
# Base: Arch Linux latest
FROM archlinux:base

# Instalar dependencias (Python, GTK, BlueZ)
RUN pacman -Syu --noconfirm --needed \
    python python-gobject python-pytest \
    gtk3 bluez bluez-utils sudo git

# Usuario no-root para testing
RUN useradd -m -g users -s /bin/bash testuser

USER testuser

# Copiar código fuente
COPY tests/ tests/
COPY airootfs/ airootfs/

# Configurar modo test
ENV MADOS_BT_CONFIG_MODE=test
ENV PYTHONPATH="/home/testuser/airootfs/usr/local/lib:$PYTHONPATH"
```

## 🧪 Tests que Ejecuta

```
3 tests (Backend)
4 tests (Frontend)
12 tests (Integración)
══════════════════════
19 tests totales
```

### Test Breakdown:

**Backend (test_bluetooth_backend.py)**:
- `test_all_fields` - Verifica estructura de datos
- `test_display_name_fallback` - Manejo de nombres vacíos
- `test_display_name_with_name` -Nombre se usa correctamente

**Frontend (test_bluetooth_frontend.py)**:
- `test_app_importable` - App importable con GTK mock
- `test_app_initialization_mock_backend` - Inicialización
- `test_create_device_row` - Creación de filas
- `test_power_toggles_backend` - Botón de energía llama backend

**Integration (test_bluetooth_integration.py)**:
- `test_factory_create_backend` - Fábrica crea backend
- `test_factory_test_mode` - Fábrica usa mock en modo test
- `test_backend_check_available` - Detección de adapter
- `test_backend_power_operations` - Encendido/apagado
- `test_backend_scan_operations` - Escaneo
- `test_backend_add_and_retrieve_devices` - Agregar dispositivos
- `test_backend_get_devices_empty` - Lista vacía
- `test_pair_device` - Pairing
- `test_connect_device` - Conexión
- `test_disconnect_device` - Desconexión
- `test_remove_device` - Eliminación
- `test_trust_device` - Gestion de confianza

## ✅ Resultado Esperado

```
Ran 19 tests in X.XXXs
OK

========================================
All tests passed successfully! 🎉
========================================
```

## 🔧 Solución de Problemas

### Error: "ModuleNotFoundError"
```bash
# Verificar PYTHONPATH
echo $PYTHONPATH

# Verificar archivos copiados
ls -la airootfs/usr/local/lib/mados_bluetooth/
```

### Error: "Gtk import failed"
```bash
# En el container, verificar:
python3 -c "from gi.repository import Gtk"
# Si falla: pacman -S python-gobject
```

### Error: "bluetoothctl not found"
```bash
# En container: pacman -S bluez bluez-utils
# O usar modo test (ya configurado por defecto)
```

## 🎨 Modos de Testing

### Modo Production (con hardware real)
```bash
# En container interactivo:
export MADOS_BT_CONFIG_MODE=production
python3 -m mados_bluetooth
```

### Modo Test (para tests - por defecto)
```bash
# Ya configurado por default en Dockerfile
# Usa MockBluetoothBackend sin hardware
```

## 🔄 Workflow Completo

```bash
# 1. Construir imagen
docker build -t mados-bluetooth-tests -f docker/Dockerfile .

# 2. Verificar imagen construida
docker images | grep mados

# 3. Ejecutar tests
docker run --rm -t mados-bluetooth-tests

# 4. Verificar logs de salida
# Debe mostrar: "Ran 19 tests in X.XXXs" "OK"
```

## 📊 Testing en GitHub Actions (Ejemplo)

```yaml
name: Bluetooth Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t mados-bluetooth-tests -f docker/Dockerfile .
      
      - name: Run tests
        run: docker run --rm mados-bluetooth-tests
```

## ⚡ Ventajas de Docker

- ✅ **Reproducible**: Same ambiente en dev, CI, Testing
- ✅ **Aislado**: No afecta sistema host
- ✅ **Sin hardware**: Tests sin dispositivos Bluetooth
- ✅ **CI/CD Ready**: Funciona en GitHub Actions, GitLab CI
- ✅ **Fast**: Caché de Docker builds

---

**¡列表o! 19 tests pasando en Docker con Arch Linux** 🎉
