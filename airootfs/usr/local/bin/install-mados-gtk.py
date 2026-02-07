#!/usr/bin/env python3
"""
madOS Installer - GTK Edition
An AI-orchestrated Arch Linux system installer
Beautiful GUI installer with Nord theme and i18n support
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
import subprocess
import os
import sys
import re
import threading

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
        super().__init__(title="madOS Installer")

        # Check root
        if os.geteuid() != 0:
            self.show_error("Root Required", "This installer must be run as root.\n\nPlease use: sudo install-mados-gtk.py")
            sys.exit(1)

        self.set_default_size(950, 480)
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
        """Apply Nord theme"""
        css_provider = Gtk.CssProvider()
        css = f"""
        window {{ background-color: {NORD_POLAR_NIGHT['nord0']}; }}
        .title {{ font-size: 24px; font-weight: bold; color: {NORD_SNOW_STORM['nord6']}; }}
        .subtitle {{ font-size: 13px; color: {NORD_FROST['nord8']}; }}
        label {{ color: {NORD_SNOW_STORM['nord6']}; }}
        radio {{ color: {NORD_SNOW_STORM['nord6']}; }}
        entry {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            color: {NORD_SNOW_STORM['nord6']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 5px;
            padding: 8px;
        }}
        button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord10']}, #4A6A94);
            color: #FFFFFF;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            font-weight: bold;
            text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.3);
        }}
        button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord9']}, {NORD_FROST['nord10']});
        }}
        .warning-button {{
            background-image: linear-gradient(to bottom, {NORD_AURORA['nord11']}, #9A3B44);
            color: #FFFFFF;
        }}
        .success-button {{
            background-image: linear-gradient(to bottom, {NORD_AURORA['nord14']}, #7A9168);
            color: #FFFFFF;
        }}
        progressbar {{ background-color: {NORD_POLAR_NIGHT['nord2']}; }}
        progressbar progress {{
            background-image: linear-gradient(to right, {NORD_FROST['nord8']}, {NORD_FROST['nord10']});
            border-radius: 5px;
        }}
        .warning-box {{
            background-color: {NORD_AURORA['nord11']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        .warning-box label {{
            color: {NORD_POLAR_NIGHT['nord0']};
            font-weight: bold;
        }}
        .info-box {{
            background-color: {NORD_FROST['nord10']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        .info-box label {{
            color: {NORD_POLAR_NIGHT['nord0']};
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

    def create_welcome_page(self):
        """Welcome page with language selector"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hbox.set_halign(Gtk.Align.CENTER)
        hbox.set_valign(Gtk.Align.CENTER)
        hbox.set_margin_top(15)
        hbox.set_margin_bottom(15)
        hbox.set_margin_start(30)
        hbox.set_margin_end(30)

        # Logo
        logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        logo_box.set_valign(Gtk.Align.CENTER)

        logo_paths = ['/usr/share/pixmaps/mados-logo.svg']
        for logo_path in logo_paths:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 100, 100, True)
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                logo_box.pack_start(image, False, False, 0)
                break
            except:
                continue

        hbox.pack_start(logo_box, False, False, 0)

        # Content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        title = Gtk.Label()
        title.set_markup(f'<span size="large" weight="bold">{self.t("title")}</span>')
        title.get_style_context().add_class('title')
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label=self.t('subtitle'))
        subtitle.get_style_context().add_class('subtitle')
        subtitle.set_halign(Gtk.Align.START)
        box.pack_start(subtitle, False, False, 0)

        # Features in 2 columns
        features_grid = Gtk.Grid()
        features_grid.set_column_spacing(15)
        features_grid.set_row_spacing(3)
        features_grid.set_margin_top(8)

        for row, (f1, f2) in enumerate(self.t('features')):
            label1 = Gtk.Label(label=f1)
            label1.set_halign(Gtk.Align.START)
            features_grid.attach(label1, 0, row, 1, 1)

            label2 = Gtk.Label(label=f2)
            label2.set_halign(Gtk.Align.START)
            features_grid.attach(label2, 1, row, 1, 1)

        box.pack_start(features_grid, False, False, 0)

        # Language selector
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lang_box.set_margin_top(8)

        lang_label = Gtk.Label(label=self.t('language'))
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

        box.pack_start(lang_box, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.START)
        btn_box.set_margin_top(8)

        start_btn = Gtk.Button(label=self.t('start_install'))
        start_btn.get_style_context().add_class('success-button')
        start_btn.connect('clicked', lambda x: self.notebook.next_page())
        btn_box.pack_start(start_btn, False, False, 0)

        exit_btn = Gtk.Button(label=self.t('exit'))
        exit_btn.connect('clicked', lambda x: Gtk.main_quit())
        btn_box.pack_start(exit_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)
        hbox.pack_start(box, True, True, 0)

        self.notebook.append_page(hbox, Gtk.Label(label="Welcome"))

    def create_disk_selection_page(self):
        """Disk selection page"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Title + Warning horizontal
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)

        title = Gtk.Label()
        title.set_markup(f'<span size="large" weight="bold">{self.t("select_disk")}</span>')
        header_box.pack_start(title, False, False, 0)

        warning = Gtk.Label()
        warning.set_markup(f'<span size="small" weight="bold" foreground="#BF616A">{self.t("warning")}</span>')
        header_box.pack_start(warning, False, False, 0)

        box.pack_start(header_box, False, False, 5)

        # Disks
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(55)

        self.disk_listbox = Gtk.ListBox()
        self.disk_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolled.add(self.disk_listbox)

        # Populate disks
        self.populate_disks()

        box.pack_start(scrolled, True, True, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label=self.t('back'))
        back_btn.connect('clicked', lambda x: self.notebook.prev_page())
        btn_box.pack_start(back_btn, False, False, 0)

        next_btn = Gtk.Button(label=self.t('next'))
        next_btn.get_style_context().add_class('success-button')
        next_btn.connect('clicked', self.on_disk_next)
        btn_box.pack_start(next_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Disk"))

    def populate_disks(self):
        """Populate disk list"""
        try:
            result = subprocess.run(['lsblk', '-d', '-n', '-o', 'NAME,SIZE,TYPE'],
                                  capture_output=True, text=True)
            disks = [line for line in result.stdout.splitlines() if 'disk' in line]

            for disk_line in disks:
                parts = disk_line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    size = parts[1]

                    row = Gtk.ListBoxRow()
                    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                    hbox.set_margin_start(10)
                    hbox.set_margin_end(10)
                    hbox.set_margin_top(5)
                    hbox.set_margin_bottom(5)

                    label = Gtk.Label()
                    label.set_markup(f'<b>/dev/{name}</b>  ({size})')
                    label.set_halign(Gtk.Align.START)
                    hbox.pack_start(label, True, True, 0)

                    row.add(hbox)
                    row.disk_name = name
                    row.disk_size = size
                    self.disk_listbox.add(row)
        except Exception as e:
            print(f"Error listing disks: {e}")

    def on_disk_next(self, button):
        """Handle disk selection next"""
        row = self.disk_listbox.get_selected_row()
        if row is None:
            self.show_error("No Disk Selected", "Please select a disk to continue.")
            return

        self.install_data['disk'] = f"/dev/{row.disk_name}"

        # Parse disk size
        size_str = row.disk_size
        try:
            if 'G' in size_str:
                self.install_data['disk_size_gb'] = int(float(size_str.replace('G', '')))
            elif 'T' in size_str:
                self.install_data['disk_size_gb'] = int(float(size_str.replace('T', '')) * 1024)
            else:
                self.install_data['disk_size_gb'] = 120  # default
        except:
            self.install_data['disk_size_gb'] = 120

        # Show confirmation dialog
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

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.notebook.next_page()

    def create_partitioning_page(self):
        """Partitioning scheme selection"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(30)
        box.set_margin_end(30)
        box.set_margin_top(20)
        box.set_margin_bottom(15)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        # Title
        title = Gtk.Label()
        title.set_markup(f'<span size="large" weight="bold">{self.t("partitioning")}</span>')
        box.pack_start(title, False, False, 10)

        # Disk info
        disk_info = Gtk.Label()
        disk_info.set_markup(f'<span size="small">{self.t("disk_info")} <b>{self.install_data["disk"] or "N/A"}</b> ({self.install_data["disk_size_gb"]} GB)</span>')
        box.pack_start(disk_info, False, False, 5)

        # Radio buttons
        self.radio_separate = Gtk.RadioButton.new_with_label_from_widget(None, self.t("sep_home_radio"))
        self.radio_separate.set_active(True)

        # Info box for separate home
        sep_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        sep_box.get_style_context().add_class('info-box')
        sep_box.set_margin_start(30)

        sep_label = Gtk.Label()
        sep_label.set_markup(f'<b>{self.t("sep_home_title")}</b>')
        sep_label.set_halign(Gtk.Align.START)
        sep_box.pack_start(sep_label, False, False, 0)

        sep_pros = Gtk.Label()
        sep_pros.set_markup(f'  ✓ {self.t("sep_home_pro1")}\n  ✓ {self.t("sep_home_pro2")}\n  ✗ {self.t("sep_home_con")}')
        sep_pros.set_halign(Gtk.Align.START)
        sep_box.pack_start(sep_pros, False, False, 0)

        if self.install_data["disk_size_gb"] < 128:
            sep_scheme = Gtk.Label()
            sep_scheme.set_markup(f'  <span size="small">{self.t("efi_label")} 1GB | {self.t("root_label")} 50GB | {self.t("home_label")} {self.t("rest_label")}</span>')
            sep_scheme.set_halign(Gtk.Align.START)
            sep_box.pack_start(sep_scheme, False, False, 0)
        else:
            sep_scheme = Gtk.Label()
            sep_scheme.set_markup(f'  <span size="small">{self.t("efi_label")} 1GB | {self.t("root_label")} 60GB | {self.t("home_label")} {self.t("rest_label")}</span>')
            sep_scheme.set_halign(Gtk.Align.START)
            sep_box.pack_start(sep_scheme, False, False, 0)

        box.pack_start(self.radio_separate, False, False, 5)
        box.pack_start(sep_box, False, False, 5)

        # All in root
        self.radio_all_root = Gtk.RadioButton.new_with_label_from_widget(self.radio_separate, self.t("all_root_radio"))

        # Info box for all in root
        all_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        all_box.get_style_context().add_class('success-box')
        all_box.set_margin_start(30)

        all_label = Gtk.Label()
        all_label.set_markup(f'<b>{self.t("all_root_title")}</b>')
        all_label.set_halign(Gtk.Align.START)
        all_box.pack_start(all_label, False, False, 0)

        all_pros = Gtk.Label()
        all_pros.set_markup(f'  ✓ {self.t("all_root_pro1")}\n  ✓ {self.t("all_root_pro2")}\n  ✗ {self.t("all_root_con")}')
        all_pros.set_halign(Gtk.Align.START)
        all_box.pack_start(all_pros, False, False, 0)

        all_scheme = Gtk.Label()
        all_scheme.set_markup(f'  <span size="small">{self.t("efi_label")} 1GB | {self.t("root_label")} {self.t("all_rest_label")} | {self.t("home_dir_label")}</span>')
        all_scheme.set_halign(Gtk.Align.START)
        all_box.pack_start(all_scheme, False, False, 0)

        box.pack_start(self.radio_all_root, False, False, 5)
        box.pack_start(all_box, False, False, 5)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(15)

        back_btn = Gtk.Button(label=self.t('back'))
        back_btn.connect('clicked', lambda x: self.notebook.prev_page())
        btn_box.pack_start(back_btn, False, False, 0)

        next_btn = Gtk.Button(label=self.t('next'))
        next_btn.get_style_context().add_class('success-button')
        next_btn.connect('clicked', self.on_partitioning_next)
        btn_box.pack_start(next_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Partitioning"))

    def on_partitioning_next(self, button):
        """Save partitioning choice"""
        self.install_data['separate_home'] = self.radio_separate.get_active()
        self.notebook.next_page()

    def create_user_page(self):
        """User account page"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        title = Gtk.Label()
        title.set_markup(f'<span size="large" weight="bold">{self.t("create_user")}</span>')
        box.pack_start(title, False, False, 5)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_margin_top(15)

        grid.attach(Gtk.Label(label=self.t('username')), 0, 0, 1, 1)
        self.username_entry = Gtk.Entry()
        self.username_entry.set_width_chars(30)
        self.username_entry.set_placeholder_text("lowercase, no spaces")
        grid.attach(self.username_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label=self.t('password')), 0, 1, 1, 1)
        self.password_entry = Gtk.Entry()
        self.password_entry.set_width_chars(30)
        self.password_entry.set_visibility(False)
        self.password_entry.set_placeholder_text("enter password")
        grid.attach(self.password_entry, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label=self.t('confirm_pwd')), 0, 2, 1, 1)
        self.password2_entry = Gtk.Entry()
        self.password2_entry.set_width_chars(30)
        self.password2_entry.set_visibility(False)
        self.password2_entry.set_placeholder_text("confirm password")
        grid.attach(self.password2_entry, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label=self.t('hostname')), 0, 3, 1, 1)
        self.hostname_entry = Gtk.Entry()
        self.hostname_entry.set_width_chars(30)
        self.hostname_entry.set_text(self.install_data['hostname'])
        grid.attach(self.hostname_entry, 1, 3, 1, 1)

        box.pack_start(grid, True, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label=self.t('back'))
        back_btn.connect('clicked', lambda x: self.notebook.prev_page())
        btn_box.pack_start(back_btn, False, False, 0)

        next_btn = Gtk.Button(label=self.t('next'))
        next_btn.get_style_context().add_class('success-button')
        next_btn.connect('clicked', self.on_user_next)
        btn_box.pack_start(next_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="User"))

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
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        title = Gtk.Label()
        title.set_markup(f'<span size="large" weight="bold">{self.t("regional")}</span>')
        box.pack_start(title, False, False, 5)

        # Show current language selection
        lang_info = Gtk.Label()
        lang_info.set_markup(f'<span size="small"><b>System Language:</b> {self.current_lang} ({self.install_data["locale"]})</span>')
        lang_info.set_halign(Gtk.Align.START)
        lang_info.set_margin_start(20)
        box.pack_start(lang_info, False, False, 5)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_margin_top(15)

        # Only timezone selector
        grid.attach(Gtk.Label(label=self.t('timezone')), 0, 0, 1, 1)

        self.timezone_combo = Gtk.ComboBoxText()
        for tz in TIMEZONES:
            self.timezone_combo.append_text(tz)
        self.timezone_combo.set_active(0)

        grid.attach(self.timezone_combo, 1, 0, 1, 1)

        box.pack_start(grid, True, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label=self.t('back'))
        back_btn.connect('clicked', lambda x: self.notebook.prev_page())
        btn_box.pack_start(back_btn, False, False, 0)

        next_btn = Gtk.Button(label=self.t('next'))
        next_btn.get_style_context().add_class('success-button')
        next_btn.connect('clicked', self.on_locale_next)
        btn_box.pack_start(next_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Locale"))

    def on_locale_next(self, button):
        """Save locale data"""
        self.install_data['timezone'] = self.timezone_combo.get_active_text()
        self.update_summary()
        self.notebook.next_page()

    def create_summary_page(self):
        """Summary page"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        title = Gtk.Label()
        title.set_markup(f'<span size="large" weight="bold">{self.t("summary")}</span>')
        box.pack_start(title, False, False, 5)

        # Summary text
        self.summary_label = Gtk.Label()
        self.summary_label.set_halign(Gtk.Align.START)
        self.summary_label.set_margin_start(20)
        self.summary_label.set_margin_top(10)
        box.pack_start(self.summary_label, True, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label=self.t('back'))
        back_btn.connect('clicked', lambda x: self.notebook.prev_page())
        btn_box.pack_start(back_btn, False, False, 0)

        install_btn = Gtk.Button(label=self.t('start_install_btn'))
        install_btn.get_style_context().add_class('success-button')
        install_btn.connect('clicked', self.on_start_installation)
        btn_box.pack_start(install_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Summary"))

    def update_summary(self):
        """Update summary text"""
        disk = self.install_data['disk'] or 'N/A'

        # Build partition info
        if self.install_data['separate_home']:
            root_size = '50GB' if self.install_data['disk_size_gb'] < 128 else '60GB'
            part_info = f'{disk}1   1GB      {self.t("efi_label")}\n  {disk}2   {root_size}   {self.t("root_label")} (/)\n  {disk}3   {self.t("rest_label")}     {self.t("home_label")} (/home)'
        else:
            part_info = f'{disk}1   1GB      {self.t("efi_label")}\n  {disk}2   {self.t("all_rest_label")}   {self.t("root_label")} (/) - {self.t("home_dir_label")}'

        text = f"""<span size="large">
<b>{self.t("sys_config")}</b>

  {self.t("disk")}       {disk}
  Username:   {self.install_data['username']}
  {self.t("hostname")}   {self.install_data['hostname']}
  {self.t("timezone")}   {self.install_data['timezone']}
  Locale:     {self.install_data['locale']}

<b>{self.t("partitions")}</b>
  {part_info}

<b>{self.t("software")}</b>
  {self.t("software_list")}
</span>"""
        self.summary_label.set_markup(text)

    def create_installation_page(self):
        """Installation page"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_start(30)
        box.set_margin_end(30)
        box.set_margin_top(30)
        box.set_margin_bottom(20)
        box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label()
        title.set_markup(f'<span size="x-large" weight="bold">{self.t("installing")}</span>')
        box.pack_start(title, False, False, 0)

        self.status_label = Gtk.Label()
        self.status_label.set_markup(f'<span size="large">{self.t("preparing")}</span>')
        box.pack_start(self.status_label, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        box.pack_start(self.progress_bar, False, False, 0)

        # Log
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(150)
        self.log_buffer = Gtk.TextBuffer()
        log_view = Gtk.TextView(buffer=self.log_buffer)
        log_view.set_editable(False)
        log_view.set_monospace(True)
        log_view.set_left_margin(15)
        log_view.set_right_margin(15)
        log_view.set_top_margin(10)
        log_view.set_bottom_margin(10)
        scrolled.add(log_view)
        box.pack_start(scrolled, True, True, 0)

        self.notebook.append_page(box, Gtk.Label(label="Installing"))

    def create_completion_page(self):
        """Completion page"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_top(30)
        box.set_margin_bottom(30)

        # Success box
        success_box = Gtk.Box()
        success_box.get_style_context().add_class('success-box')
        success = Gtk.Label()
        success.set_markup(f'<span size="xx-large" weight="bold">{self.t("success_title")}</span>')
        success_box.pack_start(success, True, True, 15)
        box.pack_start(success_box, False, False, 10)

        # Info
        info = Gtk.Label(label=self.t('success_msg'))
        info.set_justify(Gtk.Justification.CENTER)
        info.set_line_wrap(True)
        box.pack_start(info, False, False, 10)

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.CENTER)

        reboot_btn = Gtk.Button(label=self.t('reboot_now'))
        reboot_btn.get_style_context().add_class('success-button')
        reboot_btn.connect('clicked', lambda x: subprocess.run(['reboot']))
        btn_box.pack_start(reboot_btn, False, False, 0)

        exit_btn = Gtk.Button(label=self.t('exit_live'))
        exit_btn.connect('clicked', lambda x: Gtk.main_quit())
        btn_box.pack_start(exit_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Complete"))

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
        self.status_label.set_markup(f'<span size="large">{text}</span>')
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
            subprocess.run(['wipefs', '-a', disk], check=True)
            subprocess.run(['parted', '-s', disk, 'mklabel', 'gpt'], check=True)
            subprocess.run(['parted', '-s', disk, 'mkpart', 'EFI', 'fat32', '1MiB', '1GiB'], check=True)
            subprocess.run(['parted', '-s', disk, 'set', '1', 'esp', 'on'], check=True)

            if separate_home:
                # Separate /home partition
                if disk_size_gb < 128:
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '51GiB'], check=True)
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'home', 'ext4', '51GiB', '100%'], check=True)
                else:
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '61GiB'], check=True)
                    subprocess.run(['parted', '-s', disk, 'mkpart', 'home', 'ext4', '61GiB', '100%'], check=True)
            else:
                # All in root
                subprocess.run(['parted', '-s', disk, 'mkpart', 'root', 'ext4', '1GiB', '100%'], check=True)

            import time
            time.sleep(2)

            boot_part = f"{disk}1"
            root_part = f"{disk}2"
            home_part = f"{disk}3" if separate_home else None

            # Step 2: Format
            self.set_progress(0.15, "Formatting partitions...")
            self.log("Formatting partitions...")
            subprocess.run(['mkfs.fat', '-F32', boot_part], check=True)
            subprocess.run(['mkfs.ext4', '-F', root_part], check=True)
            if separate_home:
                subprocess.run(['mkfs.ext4', '-F', home_part], check=True)

            # Step 3: Mount
            self.set_progress(0.20, "Mounting filesystems...")
            self.log("Mounting filesystems...")
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

            subprocess.run(['pacstrap', '/mnt'] + packages, check=True)

            # Step 5: Generate fstab
            self.set_progress(0.50, "Generating filesystem table...")
            self.log("Generating fstab...")
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

            with open('/mnt/root/configure.sh', 'w') as f:
                f.write(config_script)

            subprocess.run(['chmod', '+x', '/mnt/root/configure.sh'], check=True)

            self.set_progress(0.70, "Applying configurations...")
            self.log("Running configuration...")
            subprocess.run(['arch-chroot', '/mnt', '/root/configure.sh'], check=True)

            self.set_progress(0.90, "Cleaning up...")
            self.log("Cleaning up...")
            subprocess.run(['rm', '/mnt/root/configure.sh'], check=True)

            self.set_progress(1.0, "Installation complete!")
            self.log("\n✅ Installation completed successfully!")

            # Move to completion page
            GLib.idle_add(self.notebook.next_page)

        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            GLib.idle_add(self.show_error, "Installation Failed", str(e))

    def show_error(self, title, message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main():
    """Main entry point"""
    app = MadOSInstaller()
    app.connect('destroy', Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    main()
