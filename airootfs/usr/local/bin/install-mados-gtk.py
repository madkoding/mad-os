#!/usr/bin/env python3
"""
madOS Installer - GTK Edition
An AI-orchestrated Arch Linux system installer
Beautiful GUI installer with Nord theme and i18n support
"""

# ========== DEMO MODE ==========
# Set to True to run installer in demo mode (no actual disk changes)
# Set to False for real installation
DEMO_MODE = False
# ================================

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
import subprocess
import os
import sys
import re
import threading
import time

# Internationalization
TRANSLATIONS = {
    'English': {
        'title': 'madOS',
        'subtitle': 'AI-Orchestrated Arch Linux | Powered by Claude Code',
        'features': [
            ('• Claude Code AI', '• Optimized 1.9GB RAM'),
            ('• Sway compositor', '• Developer-ready'),
            ('• ZRAM + EarlyOOM', '• Kernel tuning')
        ],
        'language': 'Language:',
        'start_install': 'Start Installation',
        'exit': 'Exit',
        'select_disk': 'Select Disk',
        'warning': 'WARNING: ALL DATA WILL BE ERASED',
        'layout': 'Layout:',
        'back': '← Back',
        'next': 'Next →',
        'partitioning': 'Partitioning Scheme',
        'disk_info': 'Disk:',
        'sep_home_radio': 'Separate /home partition',
        'sep_home_title': 'Separate /home partition:',
        'sep_home_pro1': 'Reinstall OS without losing data',
        'sep_home_pro2': 'Better for backups',
        'sep_home_con': 'Less flexible with space',
        'all_root_radio': 'All in / (recommended for <128GB)',
        'all_root_title': 'All in / (no separate /home):',
        'all_root_pro1': 'Maximum space flexibility',
        'all_root_pro2': 'Better for small disks',
        'all_root_con': 'Reinstall requires backup',
        'efi_label': 'EFI',
        'root_label': 'Root',
        'home_label': 'Home',
        'rest_label': 'rest',
        'all_rest_label': 'all rest',
        'home_dir_label': '/home as directory',
        'create_user': 'Create User Account',
        'username': 'Username:',
        'password': 'Password:',
        'confirm_pwd': 'Confirm Password:',
        'hostname': 'Hostname:',
        'regional': 'Regional Settings',
        'timezone': 'Timezone:',
        'locale_label': 'System Language:',
        'summary': 'Installation Summary',
        'sys_config': 'System Configuration:',
        'disk': 'Disk:',
        'partitions': 'Partitions:',
        'software': 'Included Software:',
        'software_list': '- Sway Wayland compositor\n- Claude Code AI assistant\n- Chromium, VS Code, Git\n- Development tools (Node.js, npm)\n- Optimized for 1.9GB RAM',
        'start_install_btn': 'Start Installation',
        'installing': 'Installing madOS',
        'preparing': 'Preparing installation...',
        'success_title': 'Installation Complete!',
        'success_msg': 'madOS has been successfully installed!\n\nNext steps:\n1. Remove the installation media\n2. Reboot your computer\n3. Log in with your credentials\n4. Type "claude" to start AI assistant',
        'reboot_now': 'Reboot Now',
        'exit_live': 'Exit to Live System'
    },
    'Español': {
        'title': 'madOS',
        'subtitle': 'Arch Linux Orquestado por IA | Powered by Claude Code',
        'features': [
            ('• Claude Code IA', '• Optimizado 1.9GB RAM'),
            ('• Compositor Sway', '• Entorno desarrollo'),
            ('• ZRAM + EarlyOOM', '• Ajuste kernel')
        ],
        'language': 'Idioma:',
        'start_install': 'Iniciar Instalación',
        'exit': 'Salir',
        'select_disk': 'Seleccionar Disco',
        'warning': 'ADVERTENCIA: TODOS LOS DATOS SERÁN BORRADOS',
        'layout': 'Distribución:',
        'back': '← Atrás',
        'next': 'Siguiente →',
        'partitioning': 'Esquema de Particionado',
        'disk_info': 'Disco:',
        'sep_home_radio': 'Partición /home separada',
        'sep_home_title': 'Partición /home separada:',
        'sep_home_pro1': 'Reinstalar SO sin perder datos',
        'sep_home_pro2': 'Mejor para respaldos',
        'sep_home_con': 'Menos flexible con espacio',
        'all_root_radio': 'Todo en / (recomendado para <128GB)',
        'all_root_title': 'Todo en / (sin /home separado):',
        'all_root_pro1': 'Máxima flexibilidad de espacio',
        'all_root_pro2': 'Mejor para discos pequeños',
        'all_root_con': 'Reinstalar requiere respaldo',
        'efi_label': 'EFI',
        'root_label': 'Raíz',
        'home_label': 'Home',
        'rest_label': 'resto',
        'all_rest_label': 'todo el resto',
        'home_dir_label': '/home como directorio',
        'create_user': 'Crear Cuenta de Usuario',
        'username': 'Usuario:',
        'password': 'Contraseña:',
        'confirm_pwd': 'Confirmar Contraseña:',
        'hostname': 'Nombre del equipo:',
        'regional': 'Configuración Regional',
        'timezone': 'Zona horaria:',
        'locale_label': 'Idioma del sistema:',
        'summary': 'Resumen de Instalación',
        'sys_config': 'Configuración del Sistema:',
        'disk': 'Disco:',
        'partitions': 'Particiones:',
        'software': 'Software Incluido:',
        'software_list': '- Compositor Wayland Sway\n- Asistente IA Claude Code\n- Chromium, VS Code, Git\n- Herramientas desarrollo (Node.js, npm)\n- Optimizado para 1.9GB RAM',
        'start_install_btn': 'Iniciar Instalación',
        'installing': 'Instalando madOS',
        'preparing': 'Preparando instalación...',
        'success_title': '¡Instalación Completa!',
        'success_msg': '¡madOS se ha instalado exitosamente!\n\nPróximos pasos:\n1. Remover el medio de instalación\n2. Reiniciar tu computadora\n3. Iniciar sesión con tus credenciales\n4. Escribe "claude" para iniciar el asistente IA',
        'reboot_now': 'Reiniciar Ahora',
        'exit_live': 'Salir al Sistema Live'
    },
    'Français': {
        'title': 'madOS',
        'subtitle': 'Arch Linux Orchestré par IA | Powered by Claude Code',
        'features': [
            ('• Claude Code IA', '• Optimisé 1.9GB RAM'),
            ('• Compositeur Sway', '• Prêt développement'),
            ('• ZRAM + EarlyOOM', '• Tuning kernel')
        ],
        'language': 'Langue:',
        'start_install': 'Démarrer Installation',
        'exit': 'Quitter',
        'select_disk': 'Sélectionner Disque',
        'warning': 'ATTENTION: TOUTES LES DONNÉES SERONT EFFACÉES',
        'layout': 'Disposition:',
        'back': '← Retour',
        'next': 'Suivant →',
        'partitioning': 'Schéma de Partitionnement',
        'disk_info': 'Disque:',
        'sep_home_radio': 'Partition /home séparée',
        'sep_home_title': 'Partition /home séparée:',
        'sep_home_pro1': 'Réinstaller OS sans perdre données',
        'sep_home_pro2': 'Meilleur pour sauvegardes',
        'sep_home_con': 'Moins flexible avec espace',
        'all_root_radio': 'Tout dans / (recommandé pour <128GB)',
        'all_root_title': 'Tout dans / (pas de /home séparé):',
        'all_root_pro1': 'Flexibilité d\'espace maximale',
        'all_root_pro2': 'Meilleur pour petits disques',
        'all_root_con': 'Réinstallation nécessite sauvegarde',
        'efi_label': 'EFI',
        'root_label': 'Racine',
        'home_label': 'Home',
        'rest_label': 'reste',
        'all_rest_label': 'tout le reste',
        'home_dir_label': '/home comme répertoire',
        'create_user': 'Créer Compte Utilisateur',
        'username': 'Utilisateur:',
        'password': 'Mot de passe:',
        'confirm_pwd': 'Confirmer mot de passe:',
        'hostname': 'Nom hôte:',
        'regional': 'Paramètres Régionaux',
        'timezone': 'Fuseau horaire:',
        'locale_label': 'Langue système:',
        'summary': 'Résumé Installation',
        'sys_config': 'Configuration Système:',
        'disk': 'Disque:',
        'partitions': 'Partitions:',
        'software': 'Logiciels Inclus:',
        'software_list': '- Compositeur Wayland Sway\n- Assistant IA Claude Code\n- Chromium, VS Code, Git\n- Outils développement (Node.js, npm)\n- Optimisé pour 1.9GB RAM',
        'start_install_btn': 'Démarrer Installation',
        'installing': 'Installation de madOS',
        'preparing': 'Préparation installation...',
        'success_title': 'Installation Terminée!',
        'success_msg': 'madOS a été installé avec succès!\n\nÉtapes suivantes:\n1. Retirer le média d\'installation\n2. Redémarrer votre ordinateur\n3. Connectez-vous avec vos identifiants\n4. Tapez "claude" pour démarrer l\'assistant IA',
        'reboot_now': 'Redémarrer Maintenant',
        'exit_live': 'Quitter vers Système Live'
    },
    'Deutsch': {
        'title': 'madOS',
        'subtitle': 'KI-Orchestriertes Arch Linux | Powered by Claude Code',
        'features': [
            ('• Claude Code KI', '• Optimiert 1.9GB RAM'),
            ('• Sway Compositor', '• Entwicklerbereit'),
            ('• ZRAM + EarlyOOM', '• Kernel-Tuning')
        ],
        'language': 'Sprache:',
        'start_install': 'Installation Starten',
        'exit': 'Beenden',
        'select_disk': 'Festplatte Wählen',
        'warning': 'WARNUNG: ALLE DATEN WERDEN GELÖSCHT',
        'layout': 'Layout:',
        'back': '← Zurück',
        'next': 'Weiter →',
        'partitioning': 'Partitionierungsschema',
        'disk_info': 'Festplatte:',
        'sep_home_radio': 'Separate /home Partition',
        'sep_home_title': 'Separate /home Partition:',
        'sep_home_pro1': 'OS neu installieren ohne Datenverlust',
        'sep_home_pro2': 'Besser für Backups',
        'sep_home_con': 'Weniger flexibel mit Platz',
        'all_root_radio': 'Alles in / (empfohlen für <128GB)',
        'all_root_title': 'Alles in / (keine separate /home):',
        'all_root_pro1': 'Maximale Speicherflexibilität',
        'all_root_pro2': 'Besser für kleine Festplatten',
        'all_root_con': 'Neuinstallation erfordert Backup',
        'efi_label': 'EFI',
        'root_label': 'Root',
        'home_label': 'Home',
        'rest_label': 'Rest',
        'all_rest_label': 'alles übrig',
        'home_dir_label': '/home als Verzeichnis',
        'create_user': 'Benutzerkonto Erstellen',
        'username': 'Benutzername:',
        'password': 'Passwort:',
        'confirm_pwd': 'Passwort bestätigen:',
        'hostname': 'Hostname:',
        'regional': 'Regionale Einstellungen',
        'timezone': 'Zeitzone:',
        'locale_label': 'Systemsprache:',
        'summary': 'Installationsübersicht',
        'sys_config': 'Systemkonfiguration:',
        'disk': 'Festplatte:',
        'partitions': 'Partitionen:',
        'software': 'Enthaltene Software:',
        'software_list': '- Sway Wayland Compositor\n- Claude Code KI-Assistent\n- Chromium, VS Code, Git\n- Entwicklungstools (Node.js, npm)\n- Optimiert für 1.9GB RAM',
        'start_install_btn': 'Installation Starten',
        'installing': 'madOS wird installiert',
        'preparing': 'Installation vorbereiten...',
        'success_title': 'Installation Abgeschlossen!',
        'success_msg': 'madOS wurde erfolgreich installiert!\n\nNächste Schritte:\n1. Installationsmedium entfernen\n2. Computer neu starten\n3. Mit Anmeldedaten einloggen\n4. "claude" eingeben um KI-Assistent zu starten',
        'reboot_now': 'Jetzt Neu Starten',
        'exit_live': 'Zu Live-System Beenden'
    },
    '中文': {
        'title': 'madOS',
        'subtitle': 'AI编排的Arch Linux | Powered by Claude Code',
        'features': [
            ('• Claude Code AI', '• 优化1.9GB内存'),
            ('• Sway合成器', '• 开发就绪'),
            ('• ZRAM + EarlyOOM', '• 内核调优')
        ],
        'language': '语言:',
        'start_install': '开始安装',
        'exit': '退出',
        'select_disk': '选择磁盘',
        'warning': '警告：所有数据将被删除',
        'layout': '布局:',
        'back': '← 返回',
        'next': '下一步 →',
        'partitioning': '分区方案',
        'disk_info': '磁盘:',
        'sep_home_radio': '独立 /home 分区',
        'sep_home_title': '独立 /home 分区:',
        'sep_home_pro1': '重装系统不丢失数据',
        'sep_home_pro2': '更适合备份',
        'sep_home_con': '空间灵活性较低',
        'all_root_radio': '全部在 / (<128GB推荐)',
        'all_root_title': '全部在 / (无独立/home):',
        'all_root_pro1': '最大空间灵活性',
        'all_root_pro2': '更适合小磁盘',
        'all_root_con': '重装需要备份',
        'efi_label': 'EFI',
        'root_label': '根目录',
        'home_label': '主目录',
        'rest_label': '其余',
        'all_rest_label': '全部剩余',
        'home_dir_label': '/home作为目录',
        'create_user': '创建用户账户',
        'username': '用户名:',
        'password': '密码:',
        'confirm_pwd': '确认密码:',
        'hostname': '主机名:',
        'regional': '区域设置',
        'timezone': '时区:',
        'locale_label': '系统语言:',
        'summary': '安装摘要',
        'sys_config': '系统配置:',
        'disk': '磁盘:',
        'partitions': '分区:',
        'software': '包含的软件:',
        'software_list': '- Sway Wayland合成器\n- Claude Code AI助手\n- Chromium, VS Code, Git\n- 开发工具 (Node.js, npm)\n- 为1.9GB RAM优化',
        'start_install_btn': '开始安装',
        'installing': '正在安装madOS',
        'preparing': '准备安装...',
        'success_title': '安装完成！',
        'success_msg': 'madOS已成功安装！\n\n下一步:\n1. 移除安装介质\n2. 重启计算机\n3. 使用您的凭据登录\n4. 输入"claude"启动AI助手',
        'reboot_now': '立即重启',
        'exit_live': '退出到Live系统'
    },
    '日本語': {
        'title': 'madOS',
        'subtitle': 'AIオーケストレーションArch Linux | Powered by Claude Code',
        'features': [
            ('• Claude Code AI', '• 1.9GB RAM最適化'),
            ('• Swayコンポジター', '• 開発準備完了'),
            ('• ZRAM + EarlyOOM', '• カーネル調整')
        ],
        'language': '言語:',
        'start_install': 'インストール開始',
        'exit': '終了',
        'select_disk': 'ディスク選択',
        'warning': '警告：すべてのデータが削除されます',
        'layout': 'レイアウト:',
        'back': '← 戻る',
        'next': '次へ →',
        'partitioning': 'パーティション方式',
        'disk_info': 'ディスク:',
        'sep_home_radio': '独立した /home パーティション',
        'sep_home_title': '独立した /home パーティション:',
        'sep_home_pro1': 'OSの再インストールでデータを保持',
        'sep_home_pro2': 'バックアップに適している',
        'sep_home_con': '容量の柔軟性が低い',
        'all_root_radio': 'すべて / に (<128GB推奨)',
        'all_root_title': 'すべて / に (独立した /home なし):',
        'all_root_pro1': '最大の容量柔軟性',
        'all_root_pro2': '小容量ディスクに適している',
        'all_root_con': '再インストール時はバックアップ必要',
        'efi_label': 'EFI',
        'root_label': 'ルート',
        'home_label': 'ホーム',
        'rest_label': '残り',
        'all_rest_label': 'すべての残り',
        'home_dir_label': '/homeをディレクトリとして',
        'create_user': 'ユーザーアカウント作成',
        'username': 'ユーザー名:',
        'password': 'パスワード:',
        'confirm_pwd': 'パスワード確認:',
        'hostname': 'ホスト名:',
        'regional': '地域設定',
        'timezone': 'タイムゾーン:',
        'locale_label': 'システム言語:',
        'summary': 'インストール概要',
        'sys_config': 'システム構成:',
        'disk': 'ディスク:',
        'partitions': 'パーティション:',
        'software': '含まれるソフトウェア:',
        'software_list': '- Sway Waylandコンポジター\n- Claude Code AIアシスタント\n- Chromium, VS Code, Git\n- 開発ツール (Node.js, npm)\n- 1.9GB RAM向け最適化',
        'start_install_btn': 'インストール開始',
        'installing': 'madOSインストール中',
        'preparing': 'インストール準備中...',
        'success_title': 'インストール完了！',
        'success_msg': 'madOSが正常にインストールされました！\n\n次のステップ:\n1. インストールメディアを取り外す\n2. コンピュータを再起動\n3. 認証情報でログイン\n4. "claude"と入力してAIアシスタントを起動',
        'reboot_now': '今すぐ再起動',
        'exit_live': 'Liveシステムに終了'
    }
}

# Language to locale mapping
LOCALE_MAP = {
    'English': 'en_US.UTF-8',
    'Español': 'es_ES.UTF-8',
    'Français': 'fr_FR.UTF-8',
    'Deutsch': 'de_DE.UTF-8',
    '中文': 'zh_CN.UTF-8',
    '日本語': 'ja_JP.UTF-8'
}

# All available timezones
TIMEZONES = [
    'UTC',
    'Africa/Cairo', 'Africa/Johannesburg', 'Africa/Lagos', 'Africa/Nairobi',
    'America/Anchorage', 'America/Argentina/Buenos_Aires', 'America/Bogota',
    'America/Caracas', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Mexico_City', 'America/New_York', 'America/Santiago', 'America/Sao_Paulo',
    'America/Toronto', 'America/Vancouver',
    'Asia/Bangkok', 'Asia/Dubai', 'Asia/Hong_Kong', 'Asia/Jakarta', 'Asia/Kolkata',
    'Asia/Manila', 'Asia/Seoul', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Tokyo',
    'Australia/Melbourne', 'Australia/Perth', 'Australia/Sydney',
    'Europe/Amsterdam', 'Europe/Athens', 'Europe/Berlin', 'Europe/Brussels',
    'Europe/Budapest', 'Europe/Dublin', 'Europe/Istanbul', 'Europe/Lisbon',
    'Europe/London', 'Europe/Madrid', 'Europe/Moscow', 'Europe/Paris',
    'Europe/Rome', 'Europe/Stockholm', 'Europe/Vienna', 'Europe/Warsaw',
    'Pacific/Auckland', 'Pacific/Fiji', 'Pacific/Honolulu'
]

# Nord colors
NORD_POLAR_NIGHT = {'nord0': '#2E3440', 'nord1': '#3B4252', 'nord2': '#434C5E', 'nord3': '#4C566A'}
NORD_SNOW_STORM = {'nord4': '#D8DEE9', 'nord5': '#E5E9F0', 'nord6': '#ECEFF4'}
NORD_FROST = {'nord7': '#8FBCBB', 'nord8': '#88C0D0', 'nord9': '#81A1C1', 'nord10': '#5E81AC'}
NORD_AURORA = {'nord11': '#BF616A', 'nord12': '#D08770', 'nord13': '#EBCB8B', 'nord14': '#A3BE8C', 'nord15': '#B48EAD'}


class MadOSInstaller(Gtk.Window):
    def __init__(self):
        super().__init__(title="madOS Installer" + (" (DEMO MODE)" if DEMO_MODE else ""))

        # Check root (skip in demo mode)
        if not DEMO_MODE and os.geteuid() != 0:
            self.show_error("Root Required", "This installer must be run as root.\n\nPlease use: sudo install-mados-gtk.py")
            sys.exit(1)

        self.set_default_size(1024, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)

        # Apply theme
        self.apply_theme()

        # Current language
        self.current_lang = 'English'

        # Installation data
        self.install_data = {
            'disk': None,
            'disk_size_gb': 0,
            'separate_home': True,
            'username': '',
            'password': '',
            'hostname': 'mados-' + self.random_suffix(),
            'timezone': 'UTC',
            'locale': 'en_US.UTF-8'
        }

        # Create notebook
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(False)
        
        # Add demo banner if in demo mode
        if DEMO_MODE:
            overlay = Gtk.Overlay()
            overlay.add(self.notebook)
            
            demo_banner = Gtk.Label()
            demo_banner.set_markup('<span size="small" weight="bold">  DEMO MODE — No Installation Will Occur  </span>')
            demo_banner.get_style_context().add_class('demo-banner')
            demo_banner.set_halign(Gtk.Align.CENTER)
            demo_banner.set_valign(Gtk.Align.START)
            demo_banner.set_margin_top(5)
            overlay.add_overlay(demo_banner)
            
            self.add(overlay)
        else:
            self.add(self.notebook)

        # Create pages
        self.create_welcome_page()
        self.create_disk_selection_page()
        self.create_partitioning_page()
        self.create_user_page()
        self.create_locale_page()
        self.create_summary_page()
        self.create_installation_page()
        self.create_completion_page()

        self.show_all()

    def t(self, key):
        """Translate key to current language"""
        return TRANSLATIONS[self.current_lang].get(key, key)

    def on_language_changed(self, combo):
        """Handle language change - rebuild all pages"""
        self.current_lang = combo.get_active_text()
        self.install_data['locale'] = LOCALE_MAP[self.current_lang]

        # Save current page
        current_page = self.notebook.get_current_page()

        # Remove all pages
        while self.notebook.get_n_pages() > 0:
            self.notebook.remove_page(0)

        # Recreate all pages with new language
        self.create_welcome_page()
        self.create_disk_selection_page()
        self.create_partitioning_page()
        self.create_user_page()
        self.create_locale_page()
        self.create_summary_page()
        self.create_installation_page()
        self.create_completion_page()

        # Restore current page
        self.notebook.set_current_page(min(current_page, self.notebook.get_n_pages() - 1))

        # Show all new widgets
        self.show_all()

    def apply_theme(self):
        """Apply Nord theme - Dark mode"""
        css_provider = Gtk.CssProvider()
        css = f"""
        * {{
            outline-width: 0;
        }}
        
        window {{ 
            background-color: {NORD_POLAR_NIGHT['nord0']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        .demo-banner {{
            background-color: {NORD_AURORA['nord12']};
            color: {NORD_POLAR_NIGHT['nord0']};
            font-weight: bold;
            padding: 5px;
        }}
        
        .title {{ 
            font-size: 24px; 
            font-weight: bold; 
            color: {NORD_SNOW_STORM['nord6']}; 
        }}
        
        .subtitle {{ 
            font-size: 13px; 
            color: {NORD_FROST['nord8']}; 
        }}
        
        label {{ 
            color: {NORD_SNOW_STORM['nord6']};
            background-color: transparent;
        }}
        
        radio, checkbutton {{
            color: {NORD_SNOW_STORM['nord6']};
            background-color: transparent;
        }}
        
        radio:checked {{
            color: {NORD_FROST['nord8']};
        }}
        
        entry {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 5px;
            padding: 6px;
            caret-color: {NORD_FROST['nord8']};
        }}
        
        entry:focus {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            border: 1px solid {NORD_FROST['nord9']};
        }}
        
        entry selection {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        combobox button {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            color: {NORD_SNOW_STORM['nord6']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 5px;
            padding: 6px;
        }}
        
        combobox button:hover {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            background-image: none;
        }}
        
        combobox button cellview {{
            color: {NORD_SNOW_STORM['nord6']};
            background-color: transparent;
        }}
        
        combobox window.popup {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
        }}
        
        combobox window.popup > frame > border {{
            border-color: {NORD_POLAR_NIGHT['nord3']};
        }}
        
        combobox menu, combobox .menu {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        combobox menu menuitem, combobox .menu menuitem {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
            padding: 6px 10px;
        }}
        
        combobox menu menuitem:hover, combobox .menu menuitem:hover {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        cellview {{
            background-color: transparent;
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        menu, .menu, .popup {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        menuitem {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        menuitem:hover {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord10']}, #4A6A94);
            color: #FFFFFF;
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
            text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.3);
        }}
        
        button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord9']}, {NORD_FROST['nord10']});
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
        }}
        
        button:active {{
            background-image: linear-gradient(to bottom, #4A6A94, {NORD_FROST['nord10']});
        }}
        
        .warning-button {{
            background-image: linear-gradient(to bottom, {NORD_AURORA['nord11']}, #9A3B44);
            color: #FFFFFF;
        }}
        
        .warning-button:hover {{
            background-image: linear-gradient(to bottom, #D08080, {NORD_AURORA['nord11']});
        }}
        
        .success-button {{
            background-image: linear-gradient(to bottom, {NORD_AURORA['nord14']}, #7A9168);
            color: #FFFFFF;
        }}
        
        .success-button:hover {{
            background-image: linear-gradient(to bottom, #B5D49E, {NORD_AURORA['nord14']});
        }}
        
        progressbar {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 5px;
        }}
        
        progressbar trough {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 5px;
            min-height: 20px;
        }}
        
        progressbar progress {{
            background-image: linear-gradient(to right, {NORD_FROST['nord8']}, {NORD_FROST['nord10']});
            border-radius: 5px;
            min-height: 20px;
        }}
        
        .warning-box {{
            background-color: {NORD_AURORA['nord11']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        
        .warning-box label {{
            color: {NORD_SNOW_STORM['nord6']};
            font-weight: bold;
        }}
        
        .info-box {{
            background-color: {NORD_FROST['nord10']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        
        .info-box label {{
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        .success-box {{
            background-color: {NORD_AURORA['nord14']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        
        .success-box label {{
            color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        .summary-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_FROST['nord8']};
            border-radius: 5px;
            padding: 15px;
            margin: 10px;
        }}
        
        textview {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord5']};
            padding: 10px;
        }}
        
        textview text {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord5']};
        }}
        
        scrolledwindow {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        list, listbox {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        listbox row {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        listbox row:hover {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
        }}
        
        listbox row:selected {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog, dialog {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog .titlebar, dialog .titlebar {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog box, dialog box {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog label, dialog label {{
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog .dialog-action-area button, dialog .dialog-action-area button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord10']}, #4A6A94);
            color: #FFFFFF;
            border: none;
            border-radius: 5px;
            padding: 8px 20px;
        }}
        
        messagedialog .dialog-action-area button:hover, dialog .dialog-action-area button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord9']}, {NORD_FROST['nord10']});
        }}
        
        .welcome-container {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        .welcome-title {{
            font-size: 28px;
            font-weight: bold;
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        .welcome-subtitle {{
            font-size: 13px;
            color: {NORD_FROST['nord8']};
            font-style: italic;
        }}
        
        .welcome-divider {{
            background-color: {NORD_FROST['nord8']};
            min-height: 2px;
        }}
        
        .feature-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 8px;
            padding: 8px 12px;
        }}
        
        .feature-icon {{
            color: {NORD_FROST['nord8']};
            font-size: 16px;
        }}
        
        .feature-text {{
            color: {NORD_SNOW_STORM['nord4']};
            font-size: 13px;
        }}
        
        .start-button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord8']}, {NORD_FROST['nord10']});
            color: {NORD_POLAR_NIGHT['nord0']};
            border: none;
            border-radius: 8px;
            padding: 10px 32px;
            font-size: 14px;
            font-weight: bold;
        }}
        
        .start-button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord7']}, {NORD_FROST['nord9']});
            box-shadow: 0 4px 12px rgba(136, 192, 208, 0.3);
        }}
        
        .exit-button {{
            background-color: transparent;
            background-image: none;
            color: {NORD_POLAR_NIGHT['nord3']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 8px;
            padding: 10px 24px;
            font-size: 13px;
            font-weight: normal;
        }}
        
        .exit-button:hover {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            color: {NORD_SNOW_STORM['nord4']};
            border-color: {NORD_SNOW_STORM['nord4']};
        }}
        
        .lang-label {{
            color: {NORD_POLAR_NIGHT['nord3']};
            font-size: 12px;
        }}
        
        .version-label {{
            color: {NORD_POLAR_NIGHT['nord3']};
            font-size: 11px;
        }}
        
        /* ── Page Layout ── */
        .page-container {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        .page-header {{
            margin-top: 6px;
            margin-bottom: 2px;
        }}
        
        .page-divider {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            min-height: 1px;
        }}
        
        /* ── Navigation ── */
        .nav-back-button {{
            background-color: transparent;
            background-image: none;
            color: {NORD_SNOW_STORM['nord4']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: normal;
        }}
        
        .nav-back-button:hover {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            color: {NORD_SNOW_STORM['nord6']};
            border-color: {NORD_SNOW_STORM['nord4']};
        }}
        
        /* ── Content Cards ── */
        .content-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 12px 16px;
        }}
        
        /* ── Warning Banner ── */
        .warning-banner {{
            background-color: rgba(191, 97, 106, 0.15);
            border-radius: 8px;
            padding: 6px 12px;
        }}
        
        /* ── Partition Options ── */
        .partition-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 10px 14px;
            border: 2px solid {NORD_POLAR_NIGHT['nord2']};
        }}
        
        /* ── Partition Bar ── */
        .partition-bar-efi {{
            background-color: {NORD_AURORA['nord13']};
            border-radius: 4px 0 0 4px;
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        .partition-bar-root {{
            background-color: {NORD_FROST['nord9']};
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        .partition-bar-home {{
            background-color: {NORD_AURORA['nord14']};
            border-radius: 0 4px 4px 0;
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        .partition-bar-root-only {{
            background-color: {NORD_FROST['nord9']};
            border-radius: 0 4px 4px 0;
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        /* ── Form Styling ── */
        .form-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 16px 20px;
        }}
        
        /* ── Summary Cards ── */
        .summary-card-system {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_FROST['nord8']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .summary-card-account {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_AURORA['nord15']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .summary-card-partitions {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_AURORA['nord13']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .summary-card-software {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_AURORA['nord14']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        /* ── Completion Page ── */
        .completion-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 14px 18px;
            border-left: 4px solid {NORD_AURORA['nord14']};
        }}
        
        /* ── Disk Cards ── */
        .disk-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            border-radius: 10px;
            padding: 0;
            border: 2px solid {NORD_POLAR_NIGHT['nord2']};
            text-shadow: none;
        }}
        
        .disk-card:hover {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            background-image: none;
            border-color: {NORD_FROST['nord9']};
        }}
        
        .disk-card-selected {{
            background-color: rgba(136, 192, 208, 0.08);
            background-image: none;
            border-radius: 10px;
            padding: 0;
            border: 2px solid {NORD_FROST['nord8']};
            text-shadow: none;
        }}
        
        .disk-card-selected:hover {{
            background-color: rgba(136, 192, 208, 0.12);
            background-image: none;
            border-color: {NORD_FROST['nord8']};
        }}
        
        .disk-type-badge {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .disk-type-nvme {{
            background-color: rgba(136, 192, 208, 0.2);
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .disk-type-ssd {{
            background-color: rgba(163, 190, 140, 0.2);
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .disk-type-hdd {{
            background-color: rgba(216, 222, 233, 0.1);
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .demo-banner {{
            background-color: rgba(208, 135, 112, 0.9);
            color: {NORD_POLAR_NIGHT['nord0']};
            border-radius: 0 0 8px 8px;
            padding: 4px 16px;
            font-weight: bold;
        }}
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def random_suffix(self):
        """Generate random hostname suffix"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))

    def _load_logo(self, size=160):
        """Load logo from multiple possible paths"""
        logo_paths = [
            '/usr/share/pixmaps/mados-logo.png',
            'airootfs/usr/share/pixmaps/mados-logo.png',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../share/pixmaps/mados-logo.png')
        ]
        for logo_path in logo_paths:
            try:
                if os.path.exists(logo_path):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, size, size, True)
                    return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception as e:
                print(f"Could not load logo from {logo_path}: {e}")
        return None

    def _create_page_header(self, title, step_num, total_steps=6):
        """Create consistent page header with step indicator"""
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header.get_style_context().add_class('page-header')

        # Step indicator dots
        steps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        steps_box.set_halign(Gtk.Align.CENTER)
        steps_box.set_margin_bottom(8)
        steps_box.set_margin_top(2)

        for i in range(1, total_steps + 1):
            dot = Gtk.Label()
            if i == step_num:
                dot.set_markup(f'<span foreground="{NORD_FROST["nord8"]}" size="9000" weight="bold"> ● </span>')
            elif i < step_num:
                dot.set_markup(f'<span foreground="{NORD_AURORA["nord14"]}" size="9000"> ● </span>')
            else:
                dot.set_markup(f'<span foreground="{NORD_POLAR_NIGHT["nord3"]}" size="9000"> ● </span>')
            steps_box.pack_start(dot, False, False, 0)

            if i < total_steps:
                line = Gtk.Label()
                if i < step_num:
                    line.set_markup(f'<span foreground="{NORD_AURORA["nord14"]}"> ── </span>')
                else:
                    line.set_markup(f'<span foreground="{NORD_POLAR_NIGHT["nord3"]}"> ── </span>')
                steps_box.pack_start(line, False, False, 0)

        header.pack_start(steps_box, False, False, 0)

        # Title
        title_label = Gtk.Label()
        title_label.set_markup(f'<span size="14000" weight="bold" foreground="{NORD_SNOW_STORM["nord6"]}">{title}</span>')
        title_label.set_halign(Gtk.Align.CENTER)
        header.pack_start(title_label, False, False, 0)

        # Divider
        divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        divider.get_style_context().add_class('page-divider')
        divider.set_margin_start(40)
        divider.set_margin_end(40)
        divider.set_margin_top(6)
        header.pack_start(divider, False, False, 0)

        return header

    def _create_nav_buttons(self, back_callback, next_callback, next_label=None, next_class='success-button'):
        """Create consistent navigation buttons"""
        btn_box = Gtk.Box(spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(10)

        back_btn = Gtk.Button(label=self.t('back'))
        back_btn.get_style_context().add_class('nav-back-button')
        back_btn.connect('clicked', back_callback)
        btn_box.pack_start(back_btn, False, False, 0)

        next_btn = Gtk.Button(label=next_label or self.t('next'))
        next_btn.get_style_context().add_class(next_class)
        next_btn.connect('clicked', next_callback)
        btn_box.pack_start(next_btn, False, False, 0)

        return btn_box

    def create_welcome_page(self):
        """Welcome page with centered design"""
        # Main vertical container - everything centered
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('welcome-container')

        # Center content vertically
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)

        # ── Logo ──
        logo_image = self._load_logo(180)
        if logo_image:
            logo_image.set_halign(Gtk.Align.CENTER)
            logo_image.set_margin_bottom(4)
            content.pack_start(logo_image, False, False, 0)
        else:
            fallback = Gtk.Label()
            fallback.set_markup(f'<span size="40000" weight="bold" foreground="{NORD_FROST["nord8"]}">madOS</span>')
            fallback.set_margin_bottom(4)
            content.pack_start(fallback, False, False, 0)

        # ── Subtitle ──
        subtitle = Gtk.Label()
        subtitle.set_markup(f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{self.t("subtitle")}</span>')
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_margin_top(2)
        subtitle.set_margin_bottom(10)
        content.pack_start(subtitle, False, False, 0)

        # ── Divider ──
        divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        divider.get_style_context().add_class('welcome-divider')
        divider.set_margin_start(80)
        divider.set_margin_end(80)
        divider.set_margin_bottom(10)
        content.pack_start(divider, False, False, 0)

        # ── Features grid in cards ──
        features_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        features_box.set_halign(Gtk.Align.CENTER)

        for f1, f2 in self.t('features'):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.get_style_context().add_class('feature-card')

            lbl1 = Gtk.Label()
            lbl1.set_markup(f'<span foreground="{NORD_FROST["nord8"]}" weight="bold">{f1}</span>')
            lbl1.set_halign(Gtk.Align.START)
            card.pack_start(lbl1, False, False, 0)

            lbl2 = Gtk.Label()
            lbl2.set_markup(f'<span size="small" foreground="{NORD_SNOW_STORM["nord4"]}">{f2}</span>')
            lbl2.set_halign(Gtk.Align.START)
            card.pack_start(lbl2, False, False, 0)

            features_box.pack_start(card, False, False, 0)

        content.pack_start(features_box, False, False, 0)

        # ── Language selector ──
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lang_box.set_halign(Gtk.Align.CENTER)
        lang_box.set_margin_top(12)

        lang_label = Gtk.Label()
        lang_label.set_markup(f'<span size="small" foreground="{NORD_POLAR_NIGHT["nord3"]}">{self.t("language")}</span>')
        lang_box.pack_start(lang_label, False, False, 0)

        self.lang_combo = Gtk.ComboBoxText()
        langs = list(TRANSLATIONS.keys())
        for lang in langs:
            self.lang_combo.append_text(lang)
        try:
            self.lang_combo.set_active(langs.index(self.current_lang))
        except:
            self.lang_combo.set_active(0)
        self.lang_combo.connect('changed', self.on_language_changed)
        lang_box.pack_start(self.lang_combo, False, False, 0)

        content.pack_start(lang_box, False, False, 0)

        # ── Buttons ──
        btn_box = Gtk.Box(spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(14)

        start_btn = Gtk.Button(label=self.t('start_install'))
        start_btn.get_style_context().add_class('start-button')
        start_btn.connect('clicked', lambda x: self.notebook.next_page())
        btn_box.pack_start(start_btn, False, False, 0)

        exit_btn = Gtk.Button(label=self.t('exit'))
        exit_btn.get_style_context().add_class('exit-button')
        exit_btn.connect('clicked', lambda x: Gtk.main_quit())
        btn_box.pack_start(exit_btn, False, False, 0)

        content.pack_start(btn_box, False, False, 0)

        # ── Version footer ──
        version = Gtk.Label()
        version.set_markup(f'<span size="small" foreground="{NORD_POLAR_NIGHT["nord3"]}">v1.0 • Arch Linux • x86_64</span>')
        version.set_halign(Gtk.Align.CENTER)
        version.set_margin_top(10)
        content.pack_start(version, False, False, 0)

        page.pack_start(content, True, True, 0)

        self.notebook.append_page(page, Gtk.Label(label="Welcome"))

    def create_disk_selection_page(self):
        """Disk selection page with button cards"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_bottom(14)

        # Page header with step indicator
        header = self._create_page_header(self.t('select_disk'), 1)
        content.pack_start(header, False, False, 0)

        # Warning banner
        warn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        warn_box.get_style_context().add_class('warning-banner')
        warn_box.set_margin_top(8)
        warn_box.set_margin_bottom(8)

        warn_text = Gtk.Label()
        warn_text.set_markup(
            f'<span weight="bold" foreground="{NORD_AURORA["nord11"]}">'
            f'  {self.t("warning")}</span>'
        )
        warn_text.set_halign(Gtk.Align.CENTER)
        warn_box.pack_start(warn_text, True, True, 0)

        content.pack_start(warn_box, False, False, 0)

        # Disk buttons container
        self.disk_buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.disk_buttons_box.set_margin_top(4)
        self.disk_buttons = []
        self.selected_disk_info = None

        self.populate_disks()

        content.pack_start(self.disk_buttons_box, False, False, 0)

        # Navigation buttons
        nav = self._create_nav_buttons(
            lambda x: self.notebook.prev_page(),
            self.on_disk_next
        )
        content.pack_start(nav, False, False, 0)

        scroll.add(content)
        page.pack_start(scroll, True, True, 0)

        self.notebook.append_page(page, Gtk.Label(label="Disk"))

    def populate_disks(self):
        """Populate disk list with clickable button cards"""
        # Clear existing
        for child in self.disk_buttons_box.get_children():
            self.disk_buttons_box.remove(child)
        self.disk_buttons = []
        self.selected_disk_info = None

        def on_disk_click(button, name, size):
            """Handle disk card click - update selection state"""
            for btn in self.disk_buttons:
                ctx = btn.get_style_context()
                ctx.remove_class('disk-card-selected')
                ctx.add_class('disk-card')
            ctx = button.get_style_context()
            ctx.remove_class('disk-card')
            ctx.add_class('disk-card-selected')
            self.selected_disk_info = {'name': name, 'size': size}

        def get_disk_type(name, model=''):
            """Determine disk type from name/model"""
            name_lower = name.lower()
            model_lower = model.lower()
            if 'nvme' in name_lower:
                return 'NVMe'
            elif 'ssd' in model_lower or 'flash' in model_lower:
                return 'SSD'
            else:
                return 'HDD'

        try:
            if DEMO_MODE:
                disk_list = [
                    ('sda', '256G', 'Samsung SSD 860 EVO'),
                    ('nvme0n1', '512G', 'WD Black SN750'),
                    ('sdb', '1T', 'Seagate BarraCuda HDD')
                ]
            else:
                disk_list = []
                result = subprocess.run(['lsblk', '-d', '-n', '-o', 'NAME,SIZE,TYPE,MODEL'],
                                      capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    if 'disk' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0]
                            size = parts[1]
                            model = ' '.join(parts[3:]) if len(parts) > 3 else 'Unknown disk'
                            disk_list.append((name, size, model))

            for name, size, model in disk_list:
                disk_type = get_disk_type(name, model)

                btn = Gtk.Button()
                btn.get_style_context().add_class('disk-card')
                btn.connect('clicked', on_disk_click, name, size)

                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                hbox.set_margin_start(12)
                hbox.set_margin_end(12)
                hbox.set_margin_top(8)
                hbox.set_margin_bottom(8)

                # Type badge
                badge = Gtk.Label()
                badge_class = f'disk-type-{disk_type.lower()}'
                if disk_type == 'NVMe':
                    badge.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">NVMe</span>')
                elif disk_type == 'SSD':
                    badge.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_AURORA["nord14"]}">SSD</span>')
                else:
                    badge.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_SNOW_STORM["nord4"]}">HDD</span>')
                badge.get_style_context().add_class(badge_class)
                badge.set_size_request(60, -1)
                hbox.pack_start(badge, False, False, 0)

                # Device info
                info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                dev_label = Gtk.Label()
                dev_label.set_markup(
                    f'<span weight="bold" size="11000" foreground="{NORD_SNOW_STORM["nord6"]}">'
                    f'/dev/{name}</span>'
                )
                dev_label.set_halign(Gtk.Align.START)
                info_box.pack_start(dev_label, False, False, 0)

                model_label = Gtk.Label()
                model_label.set_markup(
                    f'<span size="9500" foreground="{NORD_SNOW_STORM["nord4"]}">{model}</span>'
                )
                model_label.set_halign(Gtk.Align.START)
                info_box.pack_start(model_label, False, False, 0)
                hbox.pack_start(info_box, True, True, 0)

                # Size (prominent)
                size_label = Gtk.Label()
                size_label.set_markup(
                    f'<span weight="bold" size="14000" foreground="{NORD_FROST["nord8"]}">{size}</span>'
                )
                hbox.pack_start(size_label, False, False, 0)

                btn.add(hbox)
                self.disk_buttons.append(btn)
                self.disk_buttons_box.pack_start(btn, False, False, 0)

        except Exception as e:
            print(f"Error listing disks: {e}")

    def on_disk_next(self, button):
        """Handle disk selection next"""
        if self.selected_disk_info is None:
            self.show_error("No Disk Selected", "Please select a disk to continue.")
            return

        name = self.selected_disk_info['name']
        size_str = self.selected_disk_info['size']
        self.install_data['disk'] = f"/dev/{name}"

        # Parse disk size
        try:
            if 'G' in size_str:
                self.install_data['disk_size_gb'] = int(float(size_str.replace('G', '')))
            elif 'T' in size_str:
                self.install_data['disk_size_gb'] = int(float(size_str.replace('T', '')) * 1024)
            else:
                self.install_data['disk_size_gb'] = 120
        except:
            self.install_data['disk_size_gb'] = 120

        # Show confirmation dialog
        if DEMO_MODE:
            # Demo mode - just show info
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="DEMO MODE"
            )
            dialog.format_secondary_text(
                f"Selected disk: {self.install_data['disk']}\n\n"
                "In real mode, all data would be erased.\n"
                "Demo mode: No actual changes will be made."
            )
            self._style_dialog(dialog)
            dialog.run()
            dialog.destroy()
            self.notebook.next_page()
        else:
            # Real mode - show warning
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="CONFIRM DISK ERASURE"
            )
            dialog.format_secondary_text(
                f"ALL DATA on {self.install_data['disk']} will be PERMANENTLY ERASED!\n\n"
                "Are you absolutely sure you want to continue?"
            )

            self._style_dialog(dialog)
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                self.notebook.next_page()

    def create_partitioning_page(self):
        """Partitioning scheme selection"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_bottom(14)

        # Page header
        header = self._create_page_header(self.t('partitioning'), 2)
        content.pack_start(header, False, False, 0)

        # Selected disk info
        disk_info = Gtk.Label()
        disk_info.set_markup(
            f'<span size="10000" foreground="{NORD_SNOW_STORM["nord4"]}">'
            f'{self.t("disk_info")} <b>{self.install_data["disk"] or "N/A"}</b> '
            f'({self.install_data["disk_size_gb"]} GB)</span>'
        )
        disk_info.set_halign(Gtk.Align.CENTER)
        disk_info.set_margin_top(6)
        disk_info.set_margin_bottom(8)
        content.pack_start(disk_info, False, False, 0)

        # Option 1: Separate /home
        card1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card1.get_style_context().add_class('partition-card')
        card1.set_margin_bottom(8)

        self.radio_separate = Gtk.RadioButton.new_with_label_from_widget(None, '')
        radio_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        radio_box1.pack_start(self.radio_separate, False, False, 0)
        title1 = Gtk.Label()
        title1.set_markup(f'<span weight="bold" size="11000">{GLib.markup_escape_text(self.t("sep_home_radio"))}</span>')
        radio_box1.pack_start(title1, False, False, 0)
        card1.pack_start(radio_box1, False, False, 0)
        self.radio_separate.set_active(True)

        pros1 = Gtk.Label()
        pros1.set_markup(
            f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {self.t("sep_home_pro1")}</span>\n'
            f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {self.t("sep_home_pro2")}</span>\n'
            f'<span size="9000" foreground="{NORD_AURORA["nord11"]}">  ✗ {self.t("sep_home_con")}</span>'
        )
        pros1.set_halign(Gtk.Align.START)
        pros1.set_margin_start(28)
        card1.pack_start(pros1, False, False, 0)

        # Partition bar visualization
        root_size = '50GB' if self.install_data["disk_size_gb"] < 128 else '60GB'
        bar1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bar1.set_margin_start(28)
        bar1.set_margin_end(8)
        bar1.set_margin_top(4)

        efi_bar = Gtk.Label()
        efi_bar.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> EFI 1G </span>')
        efi_bar.get_style_context().add_class('partition-bar-efi')
        bar1.pack_start(efi_bar, False, False, 0)

        root_bar = Gtk.Label()
        root_bar.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> Root {root_size} </span>')
        root_bar.get_style_context().add_class('partition-bar-root')
        bar1.pack_start(root_bar, True, True, 0)

        home_bar = Gtk.Label()
        home_bar.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> Home {self.t("rest_label")} </span>')
        home_bar.get_style_context().add_class('partition-bar-home')
        bar1.pack_start(home_bar, True, True, 0)

        card1.pack_start(bar1, False, False, 0)
        content.pack_start(card1, False, False, 0)

        # Option 2: All in root
        card2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card2.get_style_context().add_class('partition-card')
        card2.set_margin_bottom(8)

        self.radio_all_root = Gtk.RadioButton.new_with_label_from_widget(self.radio_separate, '')
        radio_box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        radio_box2.pack_start(self.radio_all_root, False, False, 0)
        title2 = Gtk.Label()
        title2.set_markup(f'<span weight="bold" size="11000">{GLib.markup_escape_text(self.t("all_root_radio"))}</span>')
        radio_box2.pack_start(title2, False, False, 0)
        card2.pack_start(radio_box2, False, False, 0)

        pros2 = Gtk.Label()
        pros2.set_markup(
            f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {self.t("all_root_pro1")}</span>\n'
            f'<span size="9000" foreground="{NORD_AURORA["nord14"]}">  ✓ {self.t("all_root_pro2")}</span>\n'
            f'<span size="9000" foreground="{NORD_AURORA["nord11"]}">  ✗ {self.t("all_root_con")}</span>'
        )
        pros2.set_halign(Gtk.Align.START)
        pros2.set_margin_start(28)
        card2.pack_start(pros2, False, False, 0)

        bar2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bar2.set_margin_start(28)
        bar2.set_margin_end(8)
        bar2.set_margin_top(6)

        efi_bar2 = Gtk.Label()
        efi_bar2.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> EFI 1G </span>')
        efi_bar2.get_style_context().add_class('partition-bar-efi')
        bar2.pack_start(efi_bar2, False, False, 0)

        root_bar2 = Gtk.Label()
        root_bar2.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> Root {self.t("all_rest_label")} – {self.t("home_dir_label")} </span>')
        root_bar2.get_style_context().add_class('partition-bar-root-only')
        bar2.pack_start(root_bar2, True, True, 0)

        card2.pack_start(bar2, False, False, 0)
        content.pack_start(card2, False, False, 0)

        # Navigation
        nav = self._create_nav_buttons(
            lambda x: self.notebook.prev_page(),
            self.on_partitioning_next
        )
        content.pack_start(nav, False, False, 0)

        scroll.add(content)
        page.pack_start(scroll, True, True, 0)

        self.notebook.append_page(page, Gtk.Label(label="Partitioning"))

    def on_partitioning_next(self, button):
        """Save partitioning choice"""
        self.install_data['separate_home'] = self.radio_separate.get_active()
        self.notebook.next_page()

    def create_user_page(self):
        """User account page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_bottom(14)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)

        # Page header
        header = self._create_page_header(self.t('create_user'), 3)
        content.pack_start(header, False, False, 0)

        # Form card
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form.get_style_context().add_class('form-card')
        form.set_margin_top(10)
        form.set_size_request(380, -1)

        # Username field
        user_label = Gtk.Label()
        user_label.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("username").rstrip(":")}</span>')
        user_label.set_halign(Gtk.Align.START)
        form.pack_start(user_label, False, False, 0)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("lowercase, no spaces")
        form.pack_start(self.username_entry, False, False, 0)

        # Password field
        pwd_label = Gtk.Label()
        pwd_label.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("password").rstrip(":")}</span>')
        pwd_label.set_halign(Gtk.Align.START)
        pwd_label.set_margin_top(4)
        form.pack_start(pwd_label, False, False, 0)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_placeholder_text("enter password")
        form.pack_start(self.password_entry, False, False, 0)

        # Confirm password
        pwd2_label = Gtk.Label()
        pwd2_label.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("confirm_pwd").rstrip(":")}</span>')
        pwd2_label.set_halign(Gtk.Align.START)
        pwd2_label.set_margin_top(4)
        form.pack_start(pwd2_label, False, False, 0)

        self.password2_entry = Gtk.Entry()
        self.password2_entry.set_visibility(False)
        self.password2_entry.set_placeholder_text("confirm password")
        form.pack_start(self.password2_entry, False, False, 0)

        # Hostname
        host_label = Gtk.Label()
        host_label.set_markup(f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("hostname").rstrip(":")}</span>')
        host_label.set_halign(Gtk.Align.START)
        host_label.set_margin_top(4)
        form.pack_start(host_label, False, False, 0)

        self.hostname_entry = Gtk.Entry()
        self.hostname_entry.set_text(self.install_data['hostname'])
        form.pack_start(self.hostname_entry, False, False, 0)

        content.pack_start(form, False, False, 0)

        # Navigation
        nav = self._create_nav_buttons(
            lambda x: self.notebook.prev_page(),
            self.on_user_next
        )
        nav.set_size_request(380, -1)
        content.pack_start(nav, False, False, 0)

        page.pack_start(content, True, False, 0)

        self.notebook.append_page(page, Gtk.Label(label="User"))

    def on_user_next(self, button):
        """Validate and save user data"""
        username = self.username_entry.get_text()
        password = self.password_entry.get_text()
        password2 = self.password2_entry.get_text()
        hostname = self.hostname_entry.get_text()

        # Validate username
        if not re.match(r'^[a-z_][a-z0-9_-]*$', username):
            self.show_error("Invalid Username",
                          "Username must start with a letter and contain only lowercase letters, numbers, - and _")
            return

        # Validate password
        if not password:
            self.show_error("Empty Password", "Password cannot be empty.")
            return

        if password != password2:
            self.show_error("Password Mismatch", "Passwords do not match!")
            return

        # Validate hostname
        if not hostname:
            self.show_error("Empty Hostname", "Hostname cannot be empty.")
            return

        self.install_data['username'] = username
        self.install_data['password'] = password
        self.install_data['hostname'] = hostname

        self.notebook.next_page()

    def create_locale_page(self):
        """Locale page with timezone only (language already selected)"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_bottom(14)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)

        # Page header
        header = self._create_page_header(self.t('regional'), 4)
        content.pack_start(header, False, False, 0)

        # Language info card
        lang_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lang_card.get_style_context().add_class('content-card')
        lang_card.set_margin_top(10)
        lang_card.set_size_request(380, -1)

        lang_icon_label = Gtk.Label()
        lang_icon_label.set_markup(
            f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("locale_label").rstrip(":")}</span>'
        )
        lang_icon_label.set_halign(Gtk.Align.START)
        lang_card.pack_start(lang_icon_label, False, False, 0)

        lang_value = Gtk.Label()
        lang_value.set_markup(
            f'<span size="11000" weight="bold">{self.current_lang}</span>  '
            f'<span size="9000" foreground="{NORD_SNOW_STORM["nord4"]}">({self.install_data["locale"]})</span>'
        )
        lang_value.set_halign(Gtk.Align.START)
        lang_value.set_margin_start(24)
        lang_card.pack_start(lang_value, False, False, 0)

        hint = Gtk.Label()
        hint.set_markup(f'<span size="8000" foreground="{NORD_POLAR_NIGHT["nord3"]}">← Configured on welcome page</span>')
        hint.set_halign(Gtk.Align.START)
        hint.set_margin_start(24)
        lang_card.pack_start(hint, False, False, 0)

        content.pack_start(lang_card, False, False, 0)

        # Timezone card
        tz_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tz_card.get_style_context().add_class('content-card')
        tz_card.set_margin_top(8)
        tz_card.set_size_request(380, -1)

        tz_label = Gtk.Label()
        tz_label.set_markup(
            f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("timezone").rstrip(":")}</span>'
        )
        tz_label.set_halign(Gtk.Align.START)
        tz_card.pack_start(tz_label, False, False, 0)

        self.timezone_combo = Gtk.ComboBoxText()
        for tz in TIMEZONES:
            self.timezone_combo.append_text(tz)
        self.timezone_combo.set_active(0)
        self.timezone_combo.set_margin_start(24)
        self.timezone_combo.set_margin_end(8)
        tz_card.pack_start(self.timezone_combo, False, False, 0)

        content.pack_start(tz_card, False, False, 0)

        # Navigation
        nav = self._create_nav_buttons(
            lambda x: self.notebook.prev_page(),
            self.on_locale_next
        )
        nav.set_size_request(380, -1)
        content.pack_start(nav, False, False, 0)

        page.pack_start(content, True, False, 0)

        self.notebook.append_page(page, Gtk.Label(label="Locale"))

    def on_locale_next(self, button):
        """Save locale data"""
        self.install_data['timezone'] = self.timezone_combo.get_active_text()
        self.update_summary()
        self.notebook.next_page()

    def create_summary_page(self):
        """Summary page with card-based layout"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_bottom(14)

        # Page header
        header = self._create_page_header(self.t('summary'), 5)
        content.pack_start(header, False, False, 0)

        # Summary container (filled dynamically by update_summary)
        self.summary_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.summary_container.set_margin_top(10)
        content.pack_start(self.summary_container, True, False, 0)

        # Navigation
        nav = self._create_nav_buttons(
            lambda x: self.notebook.prev_page(),
            self.on_start_installation,
            next_label=self.t('start_install_btn'),
            next_class='start-button'
        )
        content.pack_start(nav, False, False, 0)

        scroll.add(content)
        page.pack_start(scroll, True, True, 0)

        self.notebook.append_page(page, Gtk.Label(label="Summary"))

    def update_summary(self):
        """Update summary with card-based layout"""
        # Clear existing content
        for child in self.summary_container.get_children():
            self.summary_container.remove(child)

        disk = self.install_data['disk'] or 'N/A'

        # Top row: System + Account side by side
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # System card
        sys_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sys_card.get_style_context().add_class('summary-card-system')

        sys_title = Gtk.Label()
        sys_title.set_markup(f'<span weight="bold" foreground="{NORD_FROST["nord8"]}">{self.t("sys_config").rstrip(":")}</span>')
        sys_title.set_halign(Gtk.Align.START)
        sys_card.pack_start(sys_title, False, False, 0)

        sys_info = Gtk.Label()
        sys_info.set_markup(
            f'<span size="9000">'
            f'  {self.t("disk")}  <b>{disk}</b>\n'
            f'  {self.t("timezone")}  <b>{self.install_data["timezone"]}</b>\n'
            f'  Locale:  <b>{self.install_data["locale"]}</b>'
            f'</span>'
        )
        sys_info.set_halign(Gtk.Align.START)
        sys_card.pack_start(sys_info, False, False, 0)

        top_row.pack_start(sys_card, True, True, 0)

        # Account card
        acct_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        acct_card.get_style_context().add_class('summary-card-account')

        acct_title = Gtk.Label()
        acct_title.set_markup(f'<span weight="bold" foreground="{NORD_AURORA["nord15"]}">Account</span>')
        acct_title.set_halign(Gtk.Align.START)
        acct_card.pack_start(acct_title, False, False, 0)

        acct_info = Gtk.Label()
        acct_info.set_markup(
            f'<span size="9000">'
            f'  {self.t("username")}  <b>{self.install_data["username"]}</b>\n'
            f'  {self.t("hostname")}  <b>{self.install_data["hostname"]}</b>\n'
            f'  Password:  <b>{"●" * min(len(self.install_data["password"]), 8)}</b>'
            f'</span>'
        )
        acct_info.set_halign(Gtk.Align.START)
        acct_card.pack_start(acct_info, False, False, 0)

        top_row.pack_start(acct_card, True, True, 0)

        self.summary_container.pack_start(top_row, False, False, 0)

        # Partitions card
        part_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        part_card.get_style_context().add_class('summary-card-partitions')

        part_title = Gtk.Label()
        part_title.set_markup(f'<span weight="bold" foreground="{NORD_AURORA["nord13"]}">{self.t("partitions")}</span>')
        part_title.set_halign(Gtk.Align.START)
        part_card.pack_start(part_title, False, False, 0)

        if self.install_data['separate_home']:
            root_size = '50GB' if self.install_data['disk_size_gb'] < 128 else '60GB'
            part_text = (
                f'  {disk}1   <b>1GB</b>      {self.t("efi_label")}  (FAT32)\n'
                f'  {disk}2   <b>{root_size}</b>   {self.t("root_label")}  (/)  ext4\n'
                f'  {disk}3   <b>{self.t("rest_label")}</b>     {self.t("home_label")}  (/home)  ext4'
            )
        else:
            part_text = (
                f'  {disk}1   <b>1GB</b>        {self.t("efi_label")}  (FAT32)\n'
                f'  {disk}2   <b>{self.t("all_rest_label")}</b>   {self.t("root_label")}  (/)  ext4 – {self.t("home_dir_label")}'
            )

        part_info = Gtk.Label()
        part_info.set_markup(f'<span size="9000" font_family="monospace">{part_text}</span>')
        part_info.set_halign(Gtk.Align.START)
        part_card.pack_start(part_info, False, False, 0)

        self.summary_container.pack_start(part_card, False, False, 0)

        # Software card
        sw_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sw_card.get_style_context().add_class('summary-card-software')

        sw_title = Gtk.Label()
        sw_title.set_markup(f'<span weight="bold" foreground="{NORD_AURORA["nord14"]}">{self.t("software")}</span>')
        sw_title.set_halign(Gtk.Align.START)
        sw_card.pack_start(sw_title, False, False, 0)

        sw_info = Gtk.Label()
        sw_info.set_markup(f'<span size="9000">{self.t("software_list")}</span>')
        sw_info.set_halign(Gtk.Align.START)
        sw_card.pack_start(sw_info, False, False, 0)

        self.summary_container.pack_start(sw_card, False, False, 0)

        self.summary_container.show_all()

    def create_installation_page(self):
        """Installation page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')
        page.set_valign(Gtk.Align.CENTER)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.set_margin_top(10)
        content.set_margin_bottom(14)

        # Icon
        icon = Gtk.Label()
        icon.set_markup(f'<span size="22000" weight="bold" foreground="{NORD_FROST["nord8"]}">&#x2699;</span>')
        icon.set_halign(Gtk.Align.CENTER)
        content.pack_start(icon, False, False, 0)

        # Title
        title = Gtk.Label()
        title.set_markup(f'<span size="15000" weight="bold">{self.t("installing")}</span>')
        title.set_halign(Gtk.Align.CENTER)
        content.pack_start(title, False, False, 0)

        # Status
        self.status_label = Gtk.Label()
        self.status_label.set_markup(f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{self.t("preparing")}</span>')
        self.status_label.set_halign(Gtk.Align.CENTER)
        content.pack_start(self.status_label, False, False, 0)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_margin_top(4)
        self.progress_bar.set_margin_start(16)
        self.progress_bar.set_margin_end(16)
        content.pack_start(self.progress_bar, False, False, 0)

        # Log viewer in card
        log_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        log_card.get_style_context().add_class('content-card')
        log_card.set_margin_top(8)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(120)
        scrolled.set_max_content_height(180)

        self.log_buffer = Gtk.TextBuffer()
        log_view = Gtk.TextView(buffer=self.log_buffer)
        log_view.set_editable(False)
        log_view.set_monospace(True)
        log_view.set_left_margin(12)
        log_view.set_right_margin(12)
        log_view.set_top_margin(8)
        log_view.set_bottom_margin(8)
        scrolled.add(log_view)

        log_card.pack_start(scrolled, True, True, 0)
        content.pack_start(log_card, True, True, 0)

        page.pack_start(content, True, True, 0)

        self.notebook.append_page(page, Gtk.Label(label="Installing"))

    def create_completion_page(self):
        """Completion page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class('page-container')

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)
        content.set_margin_top(10)
        content.set_margin_bottom(14)

        # Big success icon
        icon = Gtk.Label()
        icon.set_markup(f'<span size="40000" weight="bold" foreground="{NORD_AURORA["nord14"]}">&#x2713;</span>')
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_margin_bottom(8)
        content.pack_start(icon, False, False, 0)

        # Title
        title = Gtk.Label()
        title.set_markup(f'<span size="16000" weight="bold">{self.t("success_title")}</span>')
        title.set_halign(Gtk.Align.CENTER)
        title.set_margin_bottom(10)
        content.pack_start(title, False, False, 0)

        # Info card
        info_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_card.get_style_context().add_class('completion-card')
        info_card.set_size_request(420, -1)

        if DEMO_MODE:
            info = Gtk.Label()
            info.set_markup(
                '<span size="9000">This was a <b>DEMONSTRATION</b> of the madOS installer.\n\n'
                'In real mode (DEMO_MODE = False):\n'
                '  • System would be installed to disk\n'
                '  • All configurations would be applied\n'
                '  • System would be ready to boot\n\n'
                '<b>Edit the file and set DEMO_MODE = False\n'
                'for real installation.</b></span>'
            )
        else:
            info = Gtk.Label()
            info.set_markup(f'<span size="9000">{self.t("success_msg")}</span>')
        info.set_justify(Gtk.Justification.LEFT)
        info.set_line_wrap(True)
        info_card.pack_start(info, False, False, 0)

        content.pack_start(info_card, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(14)

        if not DEMO_MODE:
            reboot_btn = Gtk.Button(label=self.t('reboot_now'))
            reboot_btn.get_style_context().add_class('success-button')
            reboot_btn.connect('clicked', lambda x: subprocess.run(['reboot']))
            btn_box.pack_start(reboot_btn, False, False, 0)

        exit_btn = Gtk.Button(label=self.t('exit_live'))
        exit_btn.get_style_context().add_class('nav-back-button')
        exit_btn.connect('clicked', lambda x: Gtk.main_quit())
        btn_box.pack_start(exit_btn, False, False, 0)

        content.pack_start(btn_box, False, False, 0)

        page.pack_start(content, True, False, 0)

        self.notebook.append_page(page, Gtk.Label(label="Complete"))

    def on_start_installation(self, button):
        """Start the installation process"""
        self.notebook.next_page()

        # Run installation in thread
        thread = threading.Thread(target=self.run_installation)
        thread.daemon = True
        thread.start()

    def log(self, message):
        """Add message to log"""
        GLib.idle_add(self._log_idle, message)

    def _log_idle(self, message):
        """Idle callback for logging"""
        self.log_buffer.insert_at_cursor(message + "\n")
        return False

    def set_progress(self, fraction, text):
        """Update progress bar"""
        GLib.idle_add(self._progress_idle, fraction, text)

    def _progress_idle(self, fraction, text):
        """Idle callback for progress"""
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(f"{int(fraction * 100)}%")
        self.status_label.set_markup(f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{text}</span>')
        return False

    def run_installation(self):
        """Perform the actual installation"""
        try:
            data = self.install_data
            disk = data['disk']
            separate_home = data['separate_home']
            disk_size_gb = data['disk_size_gb']

            # Step 1: Partition
            self.set_progress(0.05, "Partitioning disk...")
            self.log(f"Partitioning {disk}...")
            if DEMO_MODE:
                self.log("[DEMO] Simulating wipefs...")
                time.sleep(0.5)
                self.log("[DEMO] Simulating parted mklabel gpt...")
                time.sleep(0.5)
                self.log("[DEMO] Simulating parted mkpart EFI...")
                time.sleep(0.5)
                self.log("[DEMO] Simulating parted set esp on...")
                time.sleep(0.5)
            else:
                subprocess.run(['wipefs', '-a', disk], check=True)
                subprocess.run(['parted', '-s', disk, 'mklabel', 'gpt'], check=True)
                subprocess.run(['parted', '-s', disk, 'mkpart', 'EFI', 'fat32', '1MiB', '1GiB'], check=True)
                subprocess.run(['parted', '-s', disk, 'set', '1', 'esp', 'on'], check=True)

            if separate_home:
                # Separate /home partition
                if disk_size_gb < 128:
                    if DEMO_MODE:
                        self.log("[DEMO] Simulating parted mkpart root 1GiB-51GiB...")
                        time.sleep(0.5)
                        self.log("[DEMO] Simulating parted mkpart home 51GiB-100%...")
                        time.sleep(0.5)
                    else:
                        subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '51GiB'], check=True)
                        subprocess.run(['parted', '-s', disk, 'mkpart', 'home', 'ext4', '51GiB', '100%'], check=True)
                else:
                    if DEMO_MODE:
                        self.log("[DEMO] Simulating parted mkpart root 1GiB-61GiB...")
                        time.sleep(0.5)
                        self.log("[DEMO] Simulating parted mkpart home 61GiB-100%...")
                        time.sleep(0.5)
                    else:
                        subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '61GiB'], check=True)
                        subprocess.run(['parted', '-s', disk, 'mkpart', 'home', 'ext4', '61GiB', '100%'], check=True)
            else:
                # All in root
                if DEMO_MODE:
                    self.log("[DEMO] Simulating parted mkpart root 1GiB-100%...")
                    time.sleep(0.5)
                else:
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '100%'], check=True)

            if not DEMO_MODE:
                time.sleep(2)
            else:
                time.sleep(0.5)

            boot_part = f"{disk}1"
            root_part = f"{disk}2"
            home_part = f"{disk}3" if separate_home else None

            # Step 2: Format
            self.set_progress(0.15, "Formatting partitions...")
            self.log("Formatting partitions...")
            if DEMO_MODE:
                self.log(f"[DEMO] Simulating mkfs.fat {boot_part}...")
                time.sleep(0.5)
                self.log(f"[DEMO] Simulating mkfs.ext4 {root_part}...")
                time.sleep(0.5)
                if separate_home:
                    self.log(f"[DEMO] Simulating mkfs.ext4 {home_part}...")
                    time.sleep(0.5)
            else:
                subprocess.run(['mkfs.fat', '-F32', boot_part], check=True)
                subprocess.run(['mkfs.ext4', '-F', root_part], check=True)
                if separate_home:
                    subprocess.run(['mkfs.ext4', '-F', home_part], check=True)

            # Step 3: Mount
            self.set_progress(0.20, "Mounting filesystems...")
            self.log("Mounting filesystems...")
            if DEMO_MODE:
                self.log(f"[DEMO] Simulating mount {root_part} /mnt...")
                time.sleep(0.5)
                self.log("[DEMO] Simulating mkdir /mnt/boot...")
                time.sleep(0.3)
                self.log(f"[DEMO] Simulating mount {boot_part} /mnt/boot...")
                time.sleep(0.5)
                if separate_home:
                    self.log("[DEMO] Simulating mkdir /mnt/home...")
                    time.sleep(0.3)
                    self.log(f"[DEMO] Simulating mount {home_part} /mnt/home...")
                    time.sleep(0.5)
            else:
                subprocess.run(['mount', root_part, '/mnt'], check=True)
                subprocess.run(['mkdir', '-p', '/mnt/boot'], check=True)
                subprocess.run(['mount', boot_part, '/mnt/boot'], check=True)
                if separate_home:
                    subprocess.run(['mkdir', '-p', '/mnt/home'], check=True)
                    subprocess.run(['mount', home_part, '/mnt/home'], check=True)

            # Step 4: Install base system
            self.set_progress(0.25, "Installing base system (this may take a while)...")
            self.log("Installing base system...")

            packages = [
                'base', 'base-devel', 'linux', 'linux-firmware', 'intel-ucode',
                'sway', 'swaybg', 'swayidle', 'swaylock', 'waybar', 'wofi', 'mako', 'xorg-xwayland',
                'foot', 'chromium', 'code', 'vim', 'nano', 'git', 'htop', 'openssh', 'wget', 'jq',
                'grim', 'slurp', 'wl-clipboard', 'xdg-desktop-portal-wlr',
                'earlyoom', 'zram-generator', 'iwd', 'pipewire', 'pipewire-pulse', 'wireplumber',
                'intel-media-driver', 'vulkan-intel', 'mesa-utils',
                'ttf-jetbrains-mono-nerd', 'papirus-icon-theme', 'noto-fonts-emoji', 'noto-fonts-cjk',
                'pcmanfm', 'lxappearance',
                'grub', 'efibootmgr', 'networkmanager', 'sudo',
                'nodejs', 'npm', 'python', 'python-gobject', 'gtk3', 'rsync', 'dialog'
            ]

            if DEMO_MODE:
                self.log("[DEMO] Simulating pacstrap with packages:")
                for i, pkg in enumerate(packages):
                    if i % 5 == 0:
                        self.log(f"[DEMO] Installing {pkg}...")
                        time.sleep(0.3)
                time.sleep(1)
            else:
                subprocess.run(['pacstrap', '/mnt'] + packages, check=True)

            # Step 5: Generate fstab
            self.set_progress(0.50, "Generating filesystem table...")
            self.log("Generating fstab...")
            if DEMO_MODE:
                self.log("[DEMO] Simulating genfstab -U /mnt...")
                time.sleep(0.5)
                self.log("[DEMO] Would write fstab to /mnt/etc/fstab")
                time.sleep(0.5)
            else:
                result = subprocess.run(['genfstab', '-U', '/mnt'], capture_output=True, text=True, check=True)
                with open('/mnt/etc/fstab', 'a') as f:
                    f.write(result.stdout)

            # Step 6: Configure system
            self.set_progress(0.55, "Configuring system...")
            self.log("Configuring system...")

            # Create configuration script
            config_script = f'''#!/bin/bash
set -e

# Timezone
ln -sf /usr/share/zoneinfo/{data['timezone']} /etc/localtime
hwclock --systohc

# Locale
echo "{data['locale']} UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG={data['locale']}" > /etc/locale.conf

# Hostname
echo "{data['hostname']}" > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   {data['hostname']}.localdomain {data['hostname']}
EOF

# User
useradd -m -G wheel,audio,video,storage -s /bin/bash {data['username']}
echo "{data['username']}:{data['password']}" | chpasswd

# Sudo
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
echo "{data['username']} ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/claude-nopasswd
chmod 440 /etc/sudoers.d/claude-nopasswd

# GRUB - Auto-detect UEFI or BIOS
if [ -d /sys/firmware/efi/efivars ]; then
    # UEFI mode
    grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=madOS --recheck
else
    # BIOS mode
    grub-install --target=i386-pc --recheck {disk}
fi

# Configure GRUB
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg

# Services
systemctl enable earlyoom
systemctl enable iwd
systemctl enable systemd-timesyncd

# Kernel optimizations
cat > /etc/sysctl.d/99-extreme-low-ram.conf <<EOF
vm.vfs_cache_pressure = 200
vm.swappiness = 5
vm.dirty_ratio = 5
vm.dirty_background_ratio = 3
vm.min_free_kbytes = 16384
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
net.core.rmem_max = 262144
net.core.wmem_max = 262144
EOF

# ZRAM
cat > /etc/systemd/zram-generator.conf <<EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF

# Autologin
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\\\u' --noclear --autologin {data['username']} %I \\$TERM
EOF

# Copy configs
su - {data['username']} -c "mkdir -p ~/.config/{{sway,waybar,foot,wofi,alacritty}}"
su - {data['username']} -c "mkdir -p ~/Pictures/{{Wallpapers,Screenshots}}"
cp -r /etc/skel/.config/* /home/{data['username']}/.config/ 2>/dev/null || true
cp -r /etc/skel/Pictures/* /home/{data['username']}/Pictures/ 2>/dev/null || true
chown -R {data['username']}:{data['username']} /home/{data['username']}

# Bash profile
cat > /home/{data['username']}/.bash_profile <<EOF
[[ -f ~/.bashrc ]] && . ~/.bashrc
if [ -z "\\$DISPLAY" ] && [ "\\$(tty)" = "/dev/tty1" ]; then
  exec sway
fi
EOF
chown {data['username']}:{data['username']} /home/{data['username']}/.bash_profile

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# MOTD
cat > /etc/motd <<EOF

╔═══════════════════════════════════════════════════╗
║                                                   ║
║     ███╗   ███╗ █████╗ ██████╗  ██████╗ ███████╗ ║
║     ████╗ ████║██╔══██╗██╔══██╗██╔═══██╗██╔════╝ ║
║     ██╔████╔██║███████║██║  ██║██║   ██║███████╗ ║
║     ██║╚██╔╝██║██╔══██║██║  ██║██║   ██║╚════██║ ║
║     ██║ ╚═╝ ██║██║  ██║██████╔╝╚██████╔╝███████║ ║
║     ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝ ║
║                                                   ║
║         AI-Orchestrated Arch Linux System        ║
║              Powered by Claude Code              ║
║                                                   ║
╚═══════════════════════════════════════════════════╝

Welcome to madOS! Type 'claude' to start the AI assistant.

EOF
'''

            if DEMO_MODE:
                self.log("[DEMO] Would write configuration script to /mnt/root/configure.sh")
                time.sleep(0.5)
                self.log("[DEMO] Configuration would include:")
                self.log("[DEMO]   - Timezone setup")
                self.log("[DEMO]   - Locale generation")
                self.log("[DEMO]   - Hostname configuration")
                self.log("[DEMO]   - User creation")
                self.log("[DEMO]   - Sudo setup")
                time.sleep(1)
            else:
                with open('/mnt/root/configure.sh', 'w') as f:
                    f.write(config_script)

                subprocess.run(['chmod', '+x', '/mnt/root/configure.sh'], check=True)

            self.set_progress(0.70, "Applying configurations...")
            self.log("Running configuration...")
            if DEMO_MODE:
                self.log("[DEMO] Simulating arch-chroot configuration...")
                self.log("[DEMO]   - Installing GRUB bootloader")
                time.sleep(0.5)
                self.log("[DEMO]   - Enabling services (earlyoom, iwd)...")
                time.sleep(0.5)
                self.log("[DEMO]   - Configuring ZRAM...")
                time.sleep(0.5)
                self.log("[DEMO]   - Setting up autologin...")
                time.sleep(0.5)
                self.log("[DEMO]   - Installing Claude Code...")
                time.sleep(1)
            else:
                subprocess.run(['arch-chroot', '/mnt', '/root/configure.sh'], check=True)

            self.set_progress(0.90, "Cleaning up...")
            self.log("Cleaning up...")
            if DEMO_MODE:
                self.log("[DEMO] Would remove configuration script")
                time.sleep(0.5)
            else:
                subprocess.run(['rm', '/mnt/root/configure.sh'], check=True)

            self.set_progress(1.0, "Installation complete!")
            if DEMO_MODE:
                self.log("\n[OK] Demo installation completed successfully!")
                self.log("\n[DEMO] No actual changes were made to your system.")
                self.log("[DEMO] Set DEMO_MODE = False for real installation.")
            else:
                self.log("\n[OK] Installation completed successfully!")

            # Move to completion page
            GLib.idle_add(self.notebook.next_page)

        except Exception as e:
            self.log(f"\n[ERROR] {str(e)}")
            GLib.idle_add(self.show_error, "Installation Failed", str(e))

    def _style_dialog(self, dialog):
        """Apply dark theme to a dialog"""
        dialog.get_content_area().foreach(
            lambda w: w.get_style_context().add_class('dialog-content') if hasattr(w, 'get_style_context') else None
        )

    def show_error(self, title, message):
        """Show error dialog with dark theme"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        self._style_dialog(dialog)
        dialog.run()
        dialog.destroy()


def main():
    """Main entry point"""
    app = MadOSInstaller()
    app.connect('destroy', Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    main()
