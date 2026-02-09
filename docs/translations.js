// Multilanguage translations for madOS website
const translations = {
    es: {
        // Navigation
        'nav.features': 'Características',
        'nav.installers': 'Instaladores',
        'nav.hardware': 'Hardware',
        'nav.download': 'Descargar',
        
        // Hero
        'hero.badge': '🤖 Powered by Claude Code',
        'hero.title': 'AI-Orchestrated Arch Linux',
        'hero.subtitle': 'Una distribución Arch Linux optimizada para sistemas con poca RAM, con inteligencia artificial integrada para gestión inteligente del sistema.',
        'hero.download': 'Descargar madOS',
        'hero.github': 'Ver en GitHub',
        'hero.stat.ram': 'Uso de RAM',
        'hero.stat.minram': 'RAM mínima',
        'hero.stat.opensource': 'Open Source',
        
        // Features
        'features.title': 'Características Destacadas',
        'features.subtitle': 'Todo lo que necesitas en un sistema operativo ligero y potente',
        'feature.ai.title': 'Claude Code Integration',
        'feature.ai.desc': 'Asistente de IA integrado para orquestación inteligente del sistema y asistencia avanzada.',
        'feature.ram.title': 'Optimizado para Poca RAM',
        'feature.ram.desc': 'Diseñado específicamente para sistemas con 1.9GB RAM (Intel Atom) con ZRAM y EarlyOOM.',
        'feature.lightweight.title': 'Escritorio Ligero',
        'feature.lightweight.desc': 'Compositor Sway con tema Nord consume solo ~67MB de RAM para máximo rendimiento.',
        'feature.wifi.title': 'Configuración WiFi Integrada',
        'feature.wifi.desc': 'Conecta a tu red WiFi directamente desde el instalador. Escaneo automático de redes con soporte WPA2.',
        'feature.multilang.title': '6 Idiomas',
        'feature.multilang.desc': 'Instalador disponible en inglés, español, francés, alemán, chino y japonés con layout de teclado automático.',
        'feature.dev.title': 'Listo para Desarrollar',
        'feature.dev.desc': 'Node.js, npm, Git y VS Code pre-instalados para comenzar a programar inmediatamente.',
        'feature.tuned.title': 'Ajustado al Máximo',
        'feature.tuned.desc': 'Optimizaciones de kernel, red y memoria para extraer el máximo rendimiento.',
        'feature.installer.title': 'Instalador Hermoso',
        'feature.installer.desc': 'Instalador gráfico GTK con tema Nord, navegación intuitiva, progreso en tiempo real y boot splash animado.',
        'feature.security.title': 'Seguro por Defecto',
        'feature.security.desc': 'Root bloqueado, bootloader UEFI dual (NVRAM + fallback), contraseñas seguras y Claude Code aislado por usuario.',
        
        // Installers
        'installers.title': 'Instalador Gráfico',
        'installers.subtitle': 'Instalación guiada con interfaz visual moderna',
        'installer.gtk.title': 'GTK Installer',
        'installer.gtk.subtitle': 'Interfaz gráfica hermosa',
        'installer.gtk.feat1': '✓ Interfaz gráfica con tema Nord',
        'installer.gtk.feat2': '✓ Configuración WiFi integrada',
        'installer.gtk.feat3': '✓ 6 idiomas (ES, EN, FR, DE, ZH, JA)',
        'installer.gtk.feat4': '✓ Progreso en tiempo real paquete a paquete',
        'installer.gtk.feat5': '✓ Soporte Intel + AMD con bootloader UEFI dual',
        'installer.gtk.feat6': '✓ Boot splash animado con tema Nord',
        
        // Hardware
        'hardware.title': 'Hardware Objetivo',
        'hardware.subtitle': 'madOS está optimizado para dar nueva vida a hardware modesto',
        'hardware.cpu': 'CPU',
        'hardware.cpu.desc': 'Intel Atom / AMD o equivalente (x86_64)',
        'hardware.ram': 'RAM',
        'hardware.ram.desc': '1.9GB mínimo (optimizado para memoria limitada)',
        'hardware.gpu': 'GPU',
        'hardware.gpu.desc': 'Intel integrada (soporte para renderizado por software)',
        'hardware.storage': 'Almacenamiento',
        'hardware.storage.desc': '32GB+ recomendado',
        'hardware.boot': 'Arranque',
        'hardware.boot.desc': 'Soporte UEFI y BIOS',
        'hardware.monitor.title': 'Monitor del Sistema',
        'hardware.monitor.ram': 'RAM en uso',
        'hardware.monitor.cpu': 'CPU (promedio)',
        'hardware.monitor.zram': 'ZRAM Compresión',
        'hardware.monitor.zram.value': '50% ratio (zstd)',
        
        // Download
        'download.title': 'Descarga madOS',
        'download.subtitle': 'Comienza tu experiencia con madOS hoy',
        'download.build.title': 'Compilar Localmente',
        'download.build.desc': 'Construye la ISO en tu sistema Arch Linux',
        'download.iso.title': 'Descargar ISO',
        'download.iso.desc': 'Obtén la última versión oficial',
        'download.iso.button': 'Descargar desde Internet Archive',
        'download.iso.checksums': 'Ver checksums en GitHub',
        'download.steps.title': 'Pasos de Instalación',
        'download.step1.title': 'Crear USB Booteable',
        'download.step2.title': 'Arrancar desde USB',
        'download.step2.desc': 'Espera a que Sway inicie automáticamente',
        'download.step3.title': 'Ejecutar Instalador',
        'download.step4.title': '¡Disfruta madOS!',
        'download.step4.desc': 'Reinicia y comienza a usar tu sistema',
        
        // Applications
        'apps.title': 'Aplicaciones Incluidas',
        'apps.subtitle': 'Todo lo que necesitas, pre-instalado',
        'apps.desktop': 'Entorno de Escritorio',
        'apps.desktop.sway': 'Compositor Wayland compatible con i3',
        'apps.desktop.waybar': 'Barra de estado personalizable',
        'apps.desktop.wofi': 'Lanzador de aplicaciones',
        'apps.desktop.foot': 'Emulador de terminal rápido',
        'apps.desktop.mako': 'Daemon de notificaciones',
        'apps.applications': 'Aplicaciones',
        'apps.applications.chromium': 'Navegador web',
        'apps.applications.vscode': 'Editor de código',
        'apps.applications.pcmanfm': 'Gestor de archivos',
        'apps.applications.lxappearance': 'Configurador de temas',
        'apps.dev': 'Herramientas de Desarrollo',
        'apps.dev.claude': 'Asistente IA',
        'apps.dev.git': 'Control de versiones',
        'apps.dev.htop': 'Monitor del sistema',
        'apps.dev.editors': 'Editores de texto',
        
        // Footer
        'footer.tagline': 'AI-Orchestrated Arch Linux System',
        'footer.powered': 'Powered by Claude Code',
        'footer.project': 'Proyecto',
        'footer.project.github': 'GitHub',
        'footer.project.issues': 'Issues',
        'footer.project.docs': 'Documentación',
        'footer.resources': 'Recursos',
        'footer.resources.download': 'Descargar',
        'footer.resources.installers': 'Instaladores',
        'footer.resources.features': 'Características',
        'footer.community': 'Comunidad',
        'footer.community.discussions': 'Discussions',
        'footer.community.contribute': 'Contribuir',
        'footer.copyright': '2026 madOS. Distribuido bajo licencia GPL-3.0. Hecho con ❤️ para la comunidad open source.',
        
        // Meta
        'meta.title': 'madOS - AI-Orchestrated Arch Linux | Linux ligero con Claude Code',
        'meta.description': 'madOS: distribución Arch Linux optimizada para sistemas con poca RAM (1.9GB), con Claude Code integrado para orquestación inteligente. Sway, Nord theme, ~67MB RAM.',
        'meta.og.description': 'Distribución Arch Linux optimizada para poca RAM (1.9GB) con Claude Code integrado para orquestación inteligente del sistema. Sway + Nord theme, ~67MB RAM.',
        'meta.og.image.alt': 'madOS - Distribución Arch Linux con IA integrada, vista previa de terminal y estadísticas clave',
        'meta.og.locale': 'es_ES'
    },
    en: {
        // Navigation
        'nav.features': 'Features',
        'nav.installers': 'Installers',
        'nav.hardware': 'Hardware',
        'nav.download': 'Download',
        
        // Hero
        'hero.badge': '🤖 Powered by Claude Code',
        'hero.title': 'AI-Orchestrated Arch Linux',
        'hero.subtitle': 'An Arch Linux distribution optimized for low-RAM systems, with integrated artificial intelligence for smart system management.',
        'hero.download': 'Download madOS',
        'hero.github': 'View on GitHub',
        'hero.stat.ram': 'RAM Usage',
        'hero.stat.minram': 'Minimum RAM',
        'hero.stat.opensource': 'Open Source',
        
        // Features
        'features.title': 'Key Features',
        'features.subtitle': 'Everything you need in a lightweight and powerful operating system',
        'feature.ai.title': 'Claude Code Integration',
        'feature.ai.desc': 'Integrated AI assistant for intelligent system orchestration and advanced assistance.',
        'feature.ram.title': 'Optimized for Low RAM',
        'feature.ram.desc': 'Specifically designed for systems with 1.9GB RAM (Intel Atom) with ZRAM and EarlyOOM.',
        'feature.lightweight.title': 'Lightweight Desktop',
        'feature.lightweight.desc': 'Sway compositor with Nord theme uses only ~67MB RAM for maximum performance.',
        'feature.wifi.title': 'Built-in WiFi Setup',
        'feature.wifi.desc': 'Connect to your WiFi network directly from the installer. Automatic network scanning with WPA2 support.',
        'feature.multilang.title': '6 Languages',
        'feature.multilang.desc': 'Installer available in English, Spanish, French, German, Chinese and Japanese with automatic keyboard layout.',
        'feature.dev.title': 'Ready to Develop',
        'feature.dev.desc': 'Node.js, npm, Git, and VS Code pre-installed to start coding immediately.',
        'feature.tuned.title': 'Fully Tuned',
        'feature.tuned.desc': 'Kernel, network, and memory optimizations to extract maximum performance.',
        'feature.installer.title': 'Beautiful Installer',
        'feature.installer.desc': 'GTK graphical installer with Nord theme, intuitive navigation, real-time progress and animated boot splash.',
        'feature.security.title': 'Secure by Default',
        'feature.security.desc': 'Locked root, dual UEFI bootloader (NVRAM + fallback), secure passwords and per-user Claude Code isolation.',
        
        // Installers
        'installers.title': 'Graphical Installer',
        'installers.subtitle': 'Guided installation with modern visual interface',
        'installer.gtk.title': 'GTK Installer',
        'installer.gtk.subtitle': 'Beautiful graphical interface',
        'installer.gtk.feat1': '✓ Graphical interface with Nord theme',
        'installer.gtk.feat2': '✓ Built-in WiFi configuration',
        'installer.gtk.feat3': '✓ 6 languages (ES, EN, FR, DE, ZH, JA)',
        'installer.gtk.feat4': '✓ Real-time per-package progress',
        'installer.gtk.feat5': '✓ Intel + AMD support with dual UEFI bootloader',
        'installer.gtk.feat6': '✓ Animated boot splash with Nord theme',
        
        // Hardware
        'hardware.title': 'Target Hardware',
        'hardware.subtitle': 'madOS is optimized to breathe new life into modest hardware',
        'hardware.cpu': 'CPU',
        'hardware.cpu.desc': 'Intel Atom / AMD or equivalent (x86_64)',
        'hardware.ram': 'RAM',
        'hardware.ram.desc': '1.9GB minimum (optimized for limited memory)',
        'hardware.gpu': 'GPU',
        'hardware.gpu.desc': 'Intel integrated (software rendering support)',
        'hardware.storage': 'Storage',
        'hardware.storage.desc': '32GB+ recommended',
        'hardware.boot': 'Boot',
        'hardware.boot.desc': 'UEFI and BIOS support',
        'hardware.monitor.title': 'System Monitor',
        'hardware.monitor.ram': 'RAM in use',
        'hardware.monitor.cpu': 'CPU (average)',
        'hardware.monitor.zram': 'ZRAM Compression',
        'hardware.monitor.zram.value': '50% ratio (zstd)',
        
        // Download
        'download.title': 'Download madOS',
        'download.subtitle': 'Start your madOS experience today',
        'download.build.title': 'Build Locally',
        'download.build.desc': 'Build the ISO on your Arch Linux system',
        'download.iso.title': 'Download ISO',
        'download.iso.desc': 'Get the latest official release',
        'download.iso.button': 'Download from Internet Archive',
        'download.iso.checksums': 'View checksums on GitHub',
        'download.steps.title': 'Installation Steps',
        'download.step1.title': 'Create Bootable USB',
        'download.step2.title': 'Boot from USB',
        'download.step2.desc': 'Wait for Sway to start automatically',
        'download.step3.title': 'Run Installer',
        'download.step4.title': 'Enjoy madOS!',
        'download.step4.desc': 'Reboot and start using your system',
        
        // Applications
        'apps.title': 'Included Applications',
        'apps.subtitle': 'Everything you need, pre-installed',
        'apps.desktop': 'Desktop Environment',
        'apps.desktop.sway': 'i3-compatible Wayland compositor',
        'apps.desktop.waybar': 'Customizable status bar',
        'apps.desktop.wofi': 'Application launcher',
        'apps.desktop.foot': 'Fast terminal emulator',
        'apps.desktop.mako': 'Notification daemon',
        'apps.applications': 'Applications',
        'apps.applications.chromium': 'Web browser',
        'apps.applications.vscode': 'Code editor',
        'apps.applications.pcmanfm': 'File manager',
        'apps.applications.lxappearance': 'Theme configurator',
        'apps.dev': 'Development Tools',
        'apps.dev.claude': 'AI Assistant',
        'apps.dev.git': 'Version control',
        'apps.dev.htop': 'System monitor',
        'apps.dev.editors': 'Text editors',
        
        // Footer
        'footer.tagline': 'AI-Orchestrated Arch Linux System',
        'footer.powered': 'Powered by Claude Code',
        'footer.project': 'Project',
        'footer.project.github': 'GitHub',
        'footer.project.issues': 'Issues',
        'footer.project.docs': 'Documentation',
        'footer.resources': 'Resources',
        'footer.resources.download': 'Download',
        'footer.resources.installers': 'Installers',
        'footer.resources.features': 'Features',
        'footer.community': 'Community',
        'footer.community.discussions': 'Discussions',
        'footer.community.contribute': 'Contribute',
        'footer.copyright': '2026 madOS. Licensed under GPL-3.0. Made with ❤️ for the open source community.',
        
        // Meta
        'meta.title': 'madOS - AI-Orchestrated Arch Linux | Lightweight Linux with Claude Code',
        'meta.description': 'madOS: Arch Linux distribution optimized for low-RAM systems (1.9GB), with Claude Code integrated for intelligent system orchestration. Sway, Nord theme, ~67MB RAM.',
        'meta.og.description': 'Arch Linux distribution optimized for low-RAM systems (1.9GB) with Claude Code integrated for intelligent system orchestration. Sway + Nord theme, ~67MB RAM.',
        'meta.og.image.alt': 'madOS - AI-Orchestrated Arch Linux distribution with terminal preview and key stats',
        'meta.og.locale': 'en_US'
    }
};

// Language detection and management
const i18n = {
    currentLang: 'es',
    defaultLang: 'es',
    
    // Detect browser language
    detectLanguage() {
        const stored = localStorage.getItem('madOS-lang');
        if (stored && translations[stored]) {
            return stored;
        }
        
        const browserLang = navigator.language || navigator.userLanguage;
        const langCode = browserLang.split('-')[0];
        
        return translations[langCode] ? langCode : this.defaultLang;
    },
    
    // Initialize language
    init() {
        this.currentLang = this.detectLanguage();
        this.applyTranslations();
        this.updateHtmlLang();
        this.updateMetaTags();
    },
    
    // Set language
    setLanguage(lang) {
        if (!translations[lang]) return;
        
        this.currentLang = lang;
        localStorage.setItem('madOS-lang', lang);
        this.applyTranslations();
        this.updateHtmlLang();
        this.updateMetaTags();
        
        // Update language selector
        document.querySelectorAll('.lang-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });
    },
    
    // Get translation
    t(key) {
        return translations[this.currentLang][key] || translations[this.defaultLang][key] || key;
    },
    
    // Apply all translations
    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);
            
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.placeholder = translation;
            } else {
                element.textContent = translation;
            }
        });
        
        // Handle elements with HTML content
        document.querySelectorAll('[data-i18n-html]').forEach(element => {
            const key = element.getAttribute('data-i18n-html');
            element.innerHTML = this.t(key);
        });
    },
    
    // Update HTML lang attribute
    updateHtmlLang() {
        document.documentElement.lang = this.currentLang;
    },
    
    // Update meta tags
    updateMetaTags() {
        const title = this.t('meta.title');
        const description = this.t('meta.description');
        const ogDescription = this.t('meta.og.description');
        const ogImageAlt = this.t('meta.og.image.alt');
        const ogLocale = this.t('meta.og.locale');

        document.title = title;

        // Basic SEO meta
        const metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) metaDesc.content = description;

        // Open Graph
        const ogTitle = document.querySelector('meta[property="og:title"]');
        if (ogTitle) ogTitle.content = title;

        const ogDesc = document.querySelector('meta[property="og:description"]');
        if (ogDesc) ogDesc.content = ogDescription;

        const ogImgAlt = document.querySelector('meta[property="og:image:alt"]');
        if (ogImgAlt) ogImgAlt.content = ogImageAlt;

        const ogLoc = document.querySelector('meta[property="og:locale"]');
        if (ogLoc) ogLoc.content = ogLocale;

        // Twitter
        const twitterTitle = document.querySelector('meta[name="twitter:title"]');
        if (twitterTitle) twitterTitle.content = title;

        const twitterDesc = document.querySelector('meta[name="twitter:description"]');
        if (twitterDesc) twitterDesc.content = ogDescription;

        const twitterImgAlt = document.querySelector('meta[name="twitter:image:alt"]');
        if (twitterImgAlt) twitterImgAlt.content = ogImageAlt;

        // Update HTML lang attribute for SEO
        const langMap = { 'es': 'es', 'en': 'en' };
        document.documentElement.lang = langMap[this.currentLang] || 'es';
    }
};

// Auto-initialize on DOM load
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => i18n.init());
    } else {
        i18n.init();
    }
}
