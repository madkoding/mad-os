#!/bin/bash
# Script para ejecutar pruebas en Docker con Arch Linux

set -e

echo "🔍 Compilando imagen Docker para pruebas de mados-bluetooth..."
docker build -t mados-bluetooth-tests -f Dockerfile.tests .

echo "🚀 Ejecutando pruebas en Docker..."
docker run --rm -it mados-bluetooth-tests
