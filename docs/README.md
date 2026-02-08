# madOS GitHub Pages

Sitio web promocional para madOS - AI-Orchestrated Arch Linux

## 🌐 Ver el Sitio

- **Producción**: https://madkoding.github.io/mad-os/
- **Local**: Abre `index.html` en tu navegador

## 📁 Estructura

```
docs/
├── index.html      # Página principal
├── styles.css      # Estilos (tema Nord)
├── script.js       # JavaScript interactivo
└── README.md       # Este archivo
```

## 🚀 Características del Sitio

- ✨ Diseño moderno con tema Nord
- 📱 Completamente responsivo
- 🎨 Animaciones suaves
- ⚡ Optimizado para rendimiento
- 🌙 Modo oscuro nativo
- 🔍 SEO optimizado

## 🛠️ Desarrollo Local

1. Clona el repositorio:
```bash
git clone https://github.com/madkoding/mad-os.git
cd mad-os/docs
```

2. Abre con un servidor local:
```bash
# Opción 1: Python
python -m http.server 8000

# Opción 2: Node.js
npx http-server

# Opción 3: PHP
php -S localhost:8000
```

3. Visita `http://localhost:8000`

## 📝 Personalización

### Colores

Los colores están definidos en `styles.css` usando variables CSS (tema Nord):

```css
:root {
    --accent-primary: #88c0d0;
    --accent-secondary: #81a1c1;
    --bg-primary: #0f1419;
    /* ... más colores */
}
```

### Contenido

Edita `index.html` para modificar:
- Textos y descripciones
- Enlaces a GitHub
- Características destacadas
- Información de instaladores

### Animaciones

Las animaciones se controlan en `script.js`:
- Scroll suave
- Fade-in al hacer scroll
- Efectos hover
- Menu móvil

## 🌐 Configuración GitHub Pages

1. Ve a Settings → Pages en tu repositorio
2. Selecciona la rama `main`
3. Selecciona la carpeta `/docs`
4. Guarda y espera unos minutos

Tu sitio estará disponible en:
`https://madkoding.github.io/mad-os/`

## 📊 Secciones del Sitio

### Hero
Sección principal con CTA y estadísticas clave

### Features
6 características destacadas de madOS

### Installers
Comparación de los 3 instaladores disponibles

### Hardware
Especificaciones recomendadas del sistema

### Download
Instrucciones de descarga y instalación

### Applications
Listado de aplicaciones incluidas

## 🔧 Tecnologías

- HTML5 semántico
- CSS3 con variables y Grid/Flexbox
- JavaScript vanilla (sin dependencias)
- Google Fonts (Inter & JetBrains Mono)

## 📱 Responsive

Breakpoints:
- Desktop: 1024px+
- Tablet: 768px - 1023px
- Mobile: hasta 767px

## ⚡ Optimizaciones

- Lazy loading de imágenes
- CSS optimizado
- JavaScript minificado
- Fonts preconnect
- Smooth scrolling nativo

## 🎨 Diseño

Basado en:
- Nord Theme palette
- Material Design principles
- Apple HIG guidelines

## 🐛 Reportar Problemas

Si encuentras algún problema con el sitio web, por favor:
1. Abre un issue en GitHub
2. Incluye captura de pantalla
3. Menciona navegador y versión

## 📄 Licencia

GPL-3.0 - Ver archivo LICENSE en la raíz del repositorio

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/mejora`)
3. Commit cambios (`git commit -m 'Agrega mejora'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Abre un Pull Request

---

Hecho con ❤️ por la comunidad madOS
