#!/bin/bash
set -e

echo "=== mados-wifi Docker Tests (Unit Tests) ==="
echo ""
echo "This test verifies the mados-wifi backend logic without requiring"
echo "actual WiFi hardware, using mocking and static analysis."
echo ""

# Clean build
rm -rf build
mkdir -p build

# Copy files
cp -r /home/madkoding/proyectos/mad-os/airootfs/usr/local/bin/mados-wifi build/
cp -r /home/madkoding/proyectos/mad-os/airootfs/usr/local/lib/mados_wifi build/
cp /home/madkoding/proyectos/mad-os/test-wifi/test_unit.py build/

# Build Docker image
docker build -t mados-wifi-test -f Dockerfile.unit build/

echo ""
echo "=== Running unit tests in container ==="
echo ""

docker run --rm mados-wifi-test

echo ""
echo "=== Unit tests completed ==="

# Clean up
rm -rf build
