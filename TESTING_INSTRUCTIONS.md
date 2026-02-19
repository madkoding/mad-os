# Instrucciones para pruebas en Docker con Arch Linux

## 🔄 Forma Rápida (Con Docker)

```bash
# Make executable
chmod +x run-tests-docker.sh

# Run tests in Docker
./run-tests-docker.sh
```

## 🏃 Forma Local (Sin Docker)

```bash
# Make executable  
chmod +x run-tests-local.sh

# Run tests locally
./run-tests-local.sh
```

## 🐳 Manual (Construcción Detallada)

### Paso 1: Construir la imagen
```bash
docker build -t mados-bluetooth-tests -f Dockerfile.tests .
```

### Paso 2: Ejecutar pruebas
```bash
docker run --rm -it mados-bluetooth-tests
```

### Paso 3: Ver resultados
La salida mostrará:
- ✅ 19 tests pasando
- 0 fallidas
- 0 errores

## 📊 Resultados Esperados

```
tests.test_bluetooth_backend.TestBluetoothDevice.test_all_fields ... ok
tests.test_bluetooth_backend.TestBluetoothDevice.test_display_name_fallback ... ok  
tests.test_bluetooth_backend.TestBluetoothDevice.test_display_name_with_name ... ok
tests.test_bluetooth_frontend.TestBluetoothAppMethods.test_power_toggles_backend ... ok
tests.test_bluetooth_frontend.TestBluetoothAppMethods.test_app_importable ... ok
tests.test_bluetooth_frontend.TestBluetoothAppMethods.test_app_initialization_mock_backend ... ok
tests.test_bluetooth_frontend.TestBluetoothAppMethods.test_create_device_row ... ok
tests.test_bluetooth_integration.TestBluetoothWorkflow.test_backend_check_available ... ok
tests.test_bluetooth_integration.TestBluetoothWorkflow.test_backend_power_operations ... ok
tests.test_bluetooth_integration.TestBluetoothWorkflow.test_backend_scan_operations ... ok
tests.test_bluetooth_integration.TestBluetoothWorkflow.test_factory_create_backend ... ok
tests.test_bluetooth_integration.TestBluetoothWorkflow.test_factory_test_mode ... ok
tests.test_bluetooth_integration.TestDeviceDiscovery.test_backend_add_and_retrieve_devices ... ok
tests.test_bluetooth_integration.TestDeviceDiscovery.test_backend_get_devices_empty ... ok
tests.test_bluetooth_integration.TestPairingConnection.test_connect_device ... ok
tests.test_bluetooth_integration.TestPairingConnection.test_disconnect_device ... ok
tests.test_bluetooth_integration.TestPairingConnection.test_pair_device ... ok
tests.test_bluetooth_integration.TestPairingConnection.test_remove_device ... ok
tests.test_bluetooth_integration.TestPairingConnection.test_trust_device ... ok

Ran 19 tests in X.XXXs
OK
```

## 🧪 Tests Unitarios

### Backend Tests (sin GTK)
```bash
python3 -m unittest tests.test_bluetooth_backend
```

### Frontend Tests (con mock)
```bash
python3 -m unittest tests.test_bluetooth_frontend
```

### Integration Tests (workflow)
```bash
python3 -m unittest tests.test_bluetooth_integration
```

## 🐛 Debugging

### Ver logs detallados
```bash
docker run --rm -it mados-bluetooth-tests python3 -m unittest tests.test_bluetooth_backend -vv
```

### Entrar al container y debuggear
```bash
docker run --rm -it mados-bluetooth-tests /bin/bash
# Dentro del container:
python3 -c "from tests.test_bluetooth_backend import *; import unittest; unittest.main()"
```

## 💡 Notas Importantes

1. **Modo Test por defecto**: Las pruebas usan `MockBluetoothBackend` automáticamente
2. **Sin hardware necesario**: No requiere dispositivo Bluetooth real
3. **Reproducible**: Docker garantiza ambiente consistente
4. **CI/CD Ready**: Puede ejecutarse en GitHub Actions, GitLab CI, etc.
