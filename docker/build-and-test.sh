#!/bin/bash
set -e

echo "🚀 Building Arch Linux Docker image for mados-bluetooth tests..."
docker build -t mados-bluetooth-tests:latest -f docker/Dockerfile docker/

echo "📦 Running tests in Docker container..."
docker run --rm -it mados-bluetooth-tests:latest

echo "✅ Tests completed!"
