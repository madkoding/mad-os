#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get the project root (parent of test-wifi)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Clean previous build
rm -rf build
mkdir -p build

# Copy required files
cp "$PROJECT_ROOT/airootfs/usr/local/bin/mados-wifi" build/
cp -r "$PROJECT_ROOT/airootfs/usr/local/lib/mados_wifi" build/
cp test_backend.py build/

echo "=== mados-wifi Docker Tests ==="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    exit 1
fi

echo "=== Building Docker image for mados-wifi testing ==="
echo "This will create an Arch Linux container with mados-wifi and its dependencies"
echo ""

docker build -t mados-wifi-test -f Dockerfile build/

echo ""
echo "=== Running mados-wifi tests ==="
echo ""

docker run --rm \
    --privileged \
    --cap-add=NET_ADMIN \
    --cap-add=SYS_ADMIN \
    -v /sys:/sys:ro \
    mados-wifi-test

echo ""
echo "=== Tests completed ==="

# Clean up
rm -rf build
