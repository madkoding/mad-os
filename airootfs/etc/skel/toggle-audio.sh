#!/bin/bash
# Script para habilitar/deshabilitar audio

if systemctl --user is-active pipewire &>/dev/null; then
    echo "Deshabilitando audio..."
    systemctl --user stop pipewire pipewire-pulse wireplumber
    systemctl --user mask pipewire pipewire-pulse wireplumber
    echo "Audio deshabilitado. Usa 'bash $0 on' para reactivar."
else
    echo "Habilitando audio..."
    systemctl --user unmask pipewire pipewire-pulse wireplumber
    systemctl --user start pipewire pipewire-pulse wireplumber
    echo "Audio habilitado."
fi
