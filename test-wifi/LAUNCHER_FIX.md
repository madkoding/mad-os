# Fix para mados-wifi launcher

## Problema Identificado

El launcher `/usr/local/bin/mados-wifi` tiene este código:

```bash
# Ensure iwd service is running
if ! systemctl is-active --quiet iwd.service 2>/dev/null; then
    systemctl start iwd.service 2>/dev/null
    sleep 1
fi
```

**Problema**: `systemctl` no funciona en entornos sin systemd (como Docker, contenedores, o cuando systemd no está disponible).

## Solución Propuesta

Usar `service` o verificar directamente si iwd está disponible:

```bash
#!/bin/bash
# madOS WiFi Configuration - Launcher script

# Ensure iwd is available (try systemctl, fallback to direct check)
if ! systemctl is-active --quiet iwd 2>/dev/null; then
    # systemctl not available or failed, try alternative methods
    if command -v service &>/dev/null; then
        service iwd start 2>/dev/null || true
    elif command -v iwctl &>/dev/null; then
        # Direct check - iwctl is available
        true
    else
        # Try to start iwd daemon directly
        iwd --foreground &>/dev/null &
    fi
    sleep 1
fi

# Unblock WiFi rfkill (common on MT7921 and other combo adapters)
rfkill unblock wifi 2>/dev/null || true

# Ensure WiFi modules are loaded (MediaTek MT7921/MT7922)
modprobe mt7921e 2>/dev/null || true
modprobe mt7921s 2>/dev/null || true
modprobe mt7921u 2>/dev/null || true

export PYTHONPATH="/usr/local/lib${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m mados_wifi "$@"
```

## Cambios

1. ✅ Añadir `|| true` a todos los comandos para que no fallen
2. ✅ Fallback para cuando systemctl no está disponible
3. ✅ Mejor manejo de errores

## Tests

```bash
# Test el launcher
bash -n /usr/local/bin/mados-wifi  # Syntax check

# Verificar que no falle sin systemctl
sudo /usr/local/bin/mados-wifi --help
```
