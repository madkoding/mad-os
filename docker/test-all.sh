#!/bin/bash
set -e

echo "🚀 Building Arch Linux Docker image for mados-bluetooth tests..."
docker build -t mados-bluetooth-tests:latest -f docker/Dockerfile docker/

echo "📦 Testing backend only..."
docker run --rm -it mados-bluetooth-tests:latest python3 -m unittest tests.test_bluetooth_backend -v

echo "📦 Testing frontend only..."
docker run --rm -it mados-bluetooth-tests:latest python3 -m unittest tests.test_bluetooth_frontend -v

echo "📦 Testing integration only..."
docker run --rm -it mados-bluetooth-tests:latest python3 -m unittest tests.test_bluetooth_integration -v

echo "✅ All Docker tests completed!"
