#!/bin/bash
# =============================================================================
# Validation test for persistence creation during live session
# This test simulates the full workflow WITHOUT requiring host root privileges
# by running everything inside a Docker container.
# =============================================================================

set -euo pipefail

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  PERSISTENCE CREATION VALIDATION - LIVE SESSION TEST           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    echo "Please install Docker and try again"
    exit 1
fi

# Check if test script exists
if [ ! -f "${REPO_DIR}/tests/test-liveusb-persistence.sh" ]; then
    echo "❌ Test script not found: ${REPO_DIR}/tests/test-liveusb-persistence.sh"
    exit 1
fi

echo "✅ Docker is available"
echo "✅ Test script exists"
echo ""

# Build test image
echo "📦 Building Docker test image..."
docker build -f "${REPO_DIR}/Dockerfile.test" -t mados-test:latest "${REPO_DIR}" 2>&1 | tail -5

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo ""
echo "🚀 Running persistence validation in Docker container..."
echo "   (Container will run as root with all necessary privileges)"
echo ""

# Run the functional test inside Docker
# The container will have root privileges and can:
# - Create loopback devices
# - Mount filesystems
# - Create partitions
# - Test the full persistence workflow

docker run --rm \
    --privileged \
    -v "${REPO_DIR}:/build" \
    mados-test:latest bash -c "
        set -euo pipefail
        cd /build
        
        echo ''
        echo '=== Running Full Persistence Validation ==='
        echo ''
        
        # Run the functional test
        bash tests/test-liveusb-persistence.sh
        
        echo ''
        echo '=== VALIDATION COMPLETE ==='
    "

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  ✅ PERSISTENCE CREATION VALIDATION PASSED                    ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "The persistence system was validated in a Docker container"
    echo "simulating a live USB environment with:"
    echo "  • Loopback device as 'USB'"
    echo "  • ISO partition with ARCHISO label"
    echo "  • EFI partition"
    echo "  • Free space for persistence"
    echo ""
    echo "Test verified:"
    echo "  ✓ ISO device detection"
    echo "  ✓ Persistence partition creation"
    echo "  ✓ Init script installation"
    echo "  ✓ Systemd service setup"
    echo "  ✓ Overlayfs mounts (/etc, /usr, /var, /opt)"
    echo "  ✓ Bind mount (/home)"
    echo "  ✓ Data persistence across 'reboot'"
    echo ""
    exit 0
else
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  ❌ PERSISTENCE CREATION VALIDATION FAILED                    ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    exit 1
fi
