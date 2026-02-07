#!/bin/bash
# Instalar Claude Code si no está instalado
if ! command -v claude &>/dev/null; then
    echo "Instalando Claude Code..."
    npm install -g @anthropic-ai/claude-code
    echo "Claude Code instalado. Versión:"
    claude --version
else
    echo "Claude Code ya está instalado:"
    claude --version
fi
