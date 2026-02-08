# madOS - AI-Orchestrated Arch Linux
# GitHub Pages Website

Este directorio contiene el sitio web promocional de madOS.

## Vista Previa Local

Para ver el sitio localmente:

```bash
cd docs
python -m http.server 8000
```

Luego abre http://localhost:8000 en tu navegador.

## Configuración GitHub Pages

1. Ve a tu repositorio en GitHub
2. Settings → Pages
3. Source: Deploy from a branch
4. Branch: main
5. Folder: /docs
6. Save

El sitio estará disponible en: https://madkoding.github.io/mad-os/

## Estructura

- `index.html` - Página principal
- `styles.css` - Estilos CSS
- `script.js` - JavaScript
- `.nojekyll` - Previene procesamiento Jekyll
- `README.md` - Documentación

## Personalización

### Cambiar el nombre del repositorio
Si cambias el nombre del repo, actualiza en `_config.yml`:
```yaml
baseurl: "/nuevo-nombre"
```

### Dominio personalizado
Para usar un dominio personalizado:
1. Crea un archivo `CNAME` con tu dominio
2. Configura los DNS de tu dominio
3. Actualiza la configuración en GitHub Settings → Pages

## Licencia

GPL-3.0
