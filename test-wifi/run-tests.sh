#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building Docker image for mados-wifi testing ==="
docker build -t mados-wifi-test .

echo ""
echo "=== Starting Docker container with WiFi testing ==="
echo "This will run interactive tests to verify mados-wifi functionality."
echo ""

# Run the container with privilege and network access
docker run -it \
    --privileged \
    --network host \
    --cap-add=NET_ADMIN \
    --cap-add=SYS_ADMIN \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --rm \
    mados-wifi-test
