#!/bin/bash
set -e

echo "=== mados-wifi System Tests ==="
echo ""

# Check if mados-wifi exists
if [ ! -f "airootfs/usr/local/bin/mados-wifi" ]; then
    echo "ERROR: mados-wifi not found"
    exit 1
fi

# Check if mados_wifi library exists
if [ ! -d "airootfs/usr/local/lib/mados_wifi" ]; then
    echo "ERROR: mados_wifi library not found"
    exit 1
fi

echo "✓ Found mados-wifi and library"

# Check required dependencies
echo ""
echo "=== Checking dependencies ==="

for pkg in python python-gobject gtk3 iwd wireless_tools; do
    if pacman -Qi "$pkg" &> /dev/null; then
        echo "✓ $pkg installed"
    else
        echo "✗ $pkg NOT installed (will be checked in container)"
    fi
done

echo ""
echo "=== Testing Python import ==="

# Test Python import
python3 -c "import sys; sys.path.insert(0, 'airootfs/usr/local/lib'); import mados_wifi; print('✓ Python import successful')"
python3 -c "import sys; sys.path.insert(0, 'airootfs/usr/local/lib'); from mados_wifi import check_wifi_available, get_wifi_device, scan_networks; print('✓ Backend imports successful')"

echo ""
echo "=== Testing backend functions ==="

# Create a test script
cat > /tmp/test_wifi_backend.py << 'EOF'
import sys
sys.path.insert(0, '/home/madkoding/proyectos/mad-os/airootfs/usr/local/lib')

from mados_wifi import (
    check_wifi_available,
    get_wifi_device,
    scan_networks,
    get_active_ssid,
    get_saved_connections,
    connect_to_network,
    disconnect_network,
    forget_network,
)

def test_functions():
    print("\n--- Function Tests ---\n")
    
    # Test 1: check_wifi_available
    print("1. check_wifi_available():")
    result = check_wifi_available()
    print(f"   Result: {result}")
    
    # Test 2: get_wifi_device
    print("\n2. get_wifi_device():")
    device = get_wifi_device()
    print(f"   Device: {device}")
    
    # Test 3: scan_networks
    print("\n3. scan_networks():")
    networks = scan_networks()
    print(f"   Networks found: {len(networks)}")
    
    # Test 4: get_active_ssid
    print("\n4. get_active_ssid():")
    ssid = get_active_ssid()
    print(f"   Active SSID: {ssid}")
    
    # Test 5: get_saved_connections
    print("\n5. get_saved_connections():")
    saved = get_saved_connections()
    print(f"   Saved connections: {len(saved)}")
    
    print("\n--- All tests passed ---\n")
    return True

if __name__ == "__main__":
    try:
        test_functions()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

python3 /tmp/test_wifi_backend.py

echo ""
echo "=== Testing iwctl availability ==="

if command -v iwctl &> /dev/null; then
    echo "✓ iwctl is available"
    iwctl --version 2>&1 || true
else
    echo "✗ iwctl not installed (will be tested in container)"
fi

echo ""
echo "=== Testing rfkill availability ==="

if command -v rfkill &> /dev/null; then
    echo "✓ rfkill is available"
    rfkill list 2>&1 || true
else
    echo "✗ rfkill not installed (will be tested in container)"
fi

echo ""
echo "=== Testing iwd service ==="

if systemctl list-unit-files | grep -q iwd; then
    echo "✓ iwd service found"
    systemctl is-active iwd 2>&1 || true
else
    echo "✗ iwd service not found"
fi

# Clean up
rm -f /tmp/test_wifi_backend.py

echo ""
echo "=== All system tests completed ==="
