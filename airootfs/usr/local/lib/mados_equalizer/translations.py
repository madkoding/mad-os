"""
madOS Audio Equalizer - Internationalization / Translations
===========================================================

Provides translation strings for 6 languages:
    - English
    - Espanol (Spanish)
    - Francais (French)
    - Deutsch (German)
    - Chinese (Simplified)
    - Japanese

All UI strings are accessed through the TRANSLATIONS dictionary
using language name as key and string identifier as sub-key.
"""

TRANSLATIONS = {
    'English': {
        # Application
        'title': 'madOS Equalizer',
        'equalizer': 'Equalizer',
        'audio_equalizer': 'Audio Equalizer',

        # Enable/Disable
        'enable': 'Enable',
        'disable': 'Disable',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'bypass': 'Bypass',

        # Presets
        'preset': 'Preset',
        'presets': 'Presets',
        'save_preset': 'Save Preset',
        'delete_preset': 'Delete Preset',
        'custom_preset': 'Custom Preset',
        'preset_name': 'Preset Name',

        # Built-in preset names
        'flat': 'Flat',
        'rock': 'Rock',
        'pop': 'Pop',
        'jazz': 'Jazz',
        'classical': 'Classical',
        'bass_boost': 'Bass Boost',
        'treble_boost': 'Treble Boost',
        'vocal': 'Vocal',
        'electronic': 'Electronic',
        'acoustic': 'Acoustic',

        # Frequency bands
        'band_60': '60 Hz',
        'band_170': '170 Hz',
        'band_310': '310 Hz',
        'band_600': '600 Hz',
        'band_1k': '1 kHz',
        'band_3k': '3 kHz',
        'band_6k': '6 kHz',
        'band_12k': '12 kHz',

        # Gain and frequency
        'gain': 'Gain',
        'frequency': 'Frequency',
        'db': 'dB',

        # Volume
        'master_volume': 'Master Volume',
        'volume': 'Volume',
        'mute': 'Mute',
        'unmute': 'Unmute',

        # Output
        'output_device': 'Output Device',
        'no_device': 'No Device Found',
        'active_output': 'Active Output',

        # Actions
        'reset': 'Reset',
        'apply': 'Apply',

        # Language
        'language': 'Language',

        # Dialogs
        'error': 'Error',
        'success': 'Success',
        'save': 'Save',
        'cancel': 'Cancel',
        'close': 'Close',

        # Status messages
        'preset_saved': 'Preset saved successfully',
        'preset_deleted': 'Preset deleted successfully',
        'preset_exists': 'A preset with this name already exists',
        'eq_applied': 'Equalizer settings applied',
        'eq_disabled': 'Equalizer disabled',
    },

    'Español': {
        # Application
        'title': 'Ecualizador madOS',
        'equalizer': 'Ecualizador',
        'audio_equalizer': 'Ecualizador de Audio',

        # Enable/Disable
        'enable': 'Activar',
        'disable': 'Desactivar',
        'enabled': 'Activado',
        'disabled': 'Desactivado',
        'bypass': 'Bypass',

        # Presets
        'preset': 'Preajuste',
        'presets': 'Preajustes',
        'save_preset': 'Guardar Preajuste',
        'delete_preset': 'Eliminar Preajuste',
        'custom_preset': 'Preajuste Personalizado',
        'preset_name': 'Nombre del Preajuste',

        # Built-in preset names
        'flat': 'Plano',
        'rock': 'Rock',
        'pop': 'Pop',
        'jazz': 'Jazz',
        'classical': 'Clasica',
        'bass_boost': 'Refuerzo de Graves',
        'treble_boost': 'Refuerzo de Agudos',
        'vocal': 'Vocal',
        'electronic': 'Electronica',
        'acoustic': 'Acustica',

        # Frequency bands
        'band_60': '60 Hz',
        'band_170': '170 Hz',
        'band_310': '310 Hz',
        'band_600': '600 Hz',
        'band_1k': '1 kHz',
        'band_3k': '3 kHz',
        'band_6k': '6 kHz',
        'band_12k': '12 kHz',

        # Gain and frequency
        'gain': 'Ganancia',
        'frequency': 'Frecuencia',
        'db': 'dB',

        # Volume
        'master_volume': 'Volumen Principal',
        'volume': 'Volumen',
        'mute': 'Silenciar',
        'unmute': 'Activar Sonido',

        # Output
        'output_device': 'Dispositivo de Salida',
        'no_device': 'Dispositivo No Encontrado',
        'active_output': 'Salida Activa',

        # Actions
        'reset': 'Restablecer',
        'apply': 'Aplicar',

        # Language
        'language': 'Idioma',

        # Dialogs
        'error': 'Error',
        'success': 'Correcto',
        'save': 'Guardar',
        'cancel': 'Cancelar',
        'close': 'Cerrar',

        # Status messages
        'preset_saved': 'Preajuste guardado correctamente',
        'preset_deleted': 'Preajuste eliminado correctamente',
        'preset_exists': 'Ya existe un preajuste con este nombre',
        'eq_applied': 'Ajustes del ecualizador aplicados',
        'eq_disabled': 'Ecualizador desactivado',
    },

    'Français': {
        # Application
        'title': 'Egaliseur madOS',
        'equalizer': 'Egaliseur',
        'audio_equalizer': 'Egaliseur Audio',

        # Enable/Disable
        'enable': 'Activer',
        'disable': 'Desactiver',
        'enabled': 'Active',
        'disabled': 'Desactive',
        'bypass': 'Bypass',

        # Presets
        'preset': 'Preselection',
        'presets': 'Preselections',
        'save_preset': 'Enregistrer',
        'delete_preset': 'Supprimer',
        'custom_preset': 'Preselection Personnalisee',
        'preset_name': 'Nom de la Preselection',

        # Built-in preset names
        'flat': 'Plat',
        'rock': 'Rock',
        'pop': 'Pop',
        'jazz': 'Jazz',
        'classical': 'Classique',
        'bass_boost': 'Renforcement des Basses',
        'treble_boost': 'Renforcement des Aigus',
        'vocal': 'Vocal',
        'electronic': 'Electronique',
        'acoustic': 'Acoustique',

        # Frequency bands
        'band_60': '60 Hz',
        'band_170': '170 Hz',
        'band_310': '310 Hz',
        'band_600': '600 Hz',
        'band_1k': '1 kHz',
        'band_3k': '3 kHz',
        'band_6k': '6 kHz',
        'band_12k': '12 kHz',

        # Gain and frequency
        'gain': 'Gain',
        'frequency': 'Frequence',
        'db': 'dB',

        # Volume
        'master_volume': 'Volume Principal',
        'volume': 'Volume',
        'mute': 'Muet',
        'unmute': 'Reactiver le Son',

        # Output
        'output_device': 'Peripherique de Sortie',
        'no_device': 'Aucun Peripherique Trouve',
        'active_output': 'Sortie Active',

        # Actions
        'reset': 'Reinitialiser',
        'apply': 'Appliquer',

        # Language
        'language': 'Langue',

        # Dialogs
        'error': 'Erreur',
        'success': 'Succes',
        'save': 'Enregistrer',
        'cancel': 'Annuler',
        'close': 'Fermer',

        # Status messages
        'preset_saved': 'Preselection enregistree avec succes',
        'preset_deleted': 'Preselection supprimee avec succes',
        'preset_exists': 'Une preselection avec ce nom existe deja',
        'eq_applied': 'Parametres de l\'egaliseur appliques',
        'eq_disabled': 'Egaliseur desactive',
    },

    'Deutsch': {
        # Application
        'title': 'madOS Equalizer',
        'equalizer': 'Equalizer',
        'audio_equalizer': 'Audio-Equalizer',

        # Enable/Disable
        'enable': 'Aktivieren',
        'disable': 'Deaktivieren',
        'enabled': 'Aktiviert',
        'disabled': 'Deaktiviert',
        'bypass': 'Bypass',

        # Presets
        'preset': 'Voreinstellung',
        'presets': 'Voreinstellungen',
        'save_preset': 'Speichern',
        'delete_preset': 'Loeschen',
        'custom_preset': 'Eigene Voreinstellung',
        'preset_name': 'Name der Voreinstellung',

        # Built-in preset names
        'flat': 'Flach',
        'rock': 'Rock',
        'pop': 'Pop',
        'jazz': 'Jazz',
        'classical': 'Klassik',
        'bass_boost': 'Bassverstaerkung',
        'treble_boost': 'Hoehenverstaerkung',
        'vocal': 'Gesang',
        'electronic': 'Elektronisch',
        'acoustic': 'Akustisch',

        # Frequency bands
        'band_60': '60 Hz',
        'band_170': '170 Hz',
        'band_310': '310 Hz',
        'band_600': '600 Hz',
        'band_1k': '1 kHz',
        'band_3k': '3 kHz',
        'band_6k': '6 kHz',
        'band_12k': '12 kHz',

        # Gain and frequency
        'gain': 'Verstaerkung',
        'frequency': 'Frequenz',
        'db': 'dB',

        # Volume
        'master_volume': 'Hauptlautstaerke',
        'volume': 'Lautstaerke',
        'mute': 'Stumm',
        'unmute': 'Ton An',

        # Output
        'output_device': 'Ausgabegeraet',
        'no_device': 'Kein Geraet Gefunden',
        'active_output': 'Aktive Ausgabe',

        # Actions
        'reset': 'Zuruecksetzen',
        'apply': 'Anwenden',

        # Language
        'language': 'Sprache',

        # Dialogs
        'error': 'Fehler',
        'success': 'Erfolg',
        'save': 'Speichern',
        'cancel': 'Abbrechen',
        'close': 'Schliessen',

        # Status messages
        'preset_saved': 'Voreinstellung erfolgreich gespeichert',
        'preset_deleted': 'Voreinstellung erfolgreich geloescht',
        'preset_exists': 'Eine Voreinstellung mit diesem Namen existiert bereits',
        'eq_applied': 'Equalizer-Einstellungen angewendet',
        'eq_disabled': 'Equalizer deaktiviert',
    },

    '中文': {
        # Application
        'title': 'madOS 均衡器',
        'equalizer': '均衡器',
        'audio_equalizer': '音频均衡器',

        # Enable/Disable
        'enable': '启用',
        'disable': '禁用',
        'enabled': '已启用',
        'disabled': '已禁用',
        'bypass': '旁通',

        # Presets
        'preset': '预设',
        'presets': '预设列表',
        'save_preset': '保存预设',
        'delete_preset': '删除预设',
        'custom_preset': '自定义预设',
        'preset_name': '预设名称',

        # Built-in preset names
        'flat': '平坦',
        'rock': '摇滚',
        'pop': '流行',
        'jazz': '爵士',
        'classical': '古典',
        'bass_boost': '低音增强',
        'treble_boost': '高音增强',
        'vocal': '人声',
        'electronic': '电子',
        'acoustic': '原声',

        # Frequency bands
        'band_60': '60 Hz',
        'band_170': '170 Hz',
        'band_310': '310 Hz',
        'band_600': '600 Hz',
        'band_1k': '1 kHz',
        'band_3k': '3 kHz',
        'band_6k': '6 kHz',
        'band_12k': '12 kHz',

        # Gain and frequency
        'gain': '增益',
        'frequency': '频率',
        'db': 'dB',

        # Volume
        'master_volume': '主音量',
        'volume': '音量',
        'mute': '静音',
        'unmute': '取消静音',

        # Output
        'output_device': '输出设备',
        'no_device': '未找到设备',
        'active_output': '活动输出',

        # Actions
        'reset': '重置',
        'apply': '应用',

        # Language
        'language': '语言',

        # Dialogs
        'error': '错误',
        'success': '成功',
        'save': '保存',
        'cancel': '取消',
        'close': '关闭',

        # Status messages
        'preset_saved': '预设保存成功',
        'preset_deleted': '预设删除成功',
        'preset_exists': '已存在同名预设',
        'eq_applied': '均衡器设置已应用',
        'eq_disabled': '均衡器已禁用',
    },

    '日本語': {
        # Application
        'title': 'madOS イコライザー',
        'equalizer': 'イコライザー',
        'audio_equalizer': 'オーディオイコライザー',

        # Enable/Disable
        'enable': '有効',
        'disable': '無効',
        'enabled': '有効',
        'disabled': '無効',
        'bypass': 'バイパス',

        # Presets
        'preset': 'プリセット',
        'presets': 'プリセット一覧',
        'save_preset': 'プリセットを保存',
        'delete_preset': 'プリセットを削除',
        'custom_preset': 'カスタムプリセット',
        'preset_name': 'プリセット名',

        # Built-in preset names
        'flat': 'フラット',
        'rock': 'ロック',
        'pop': 'ポップ',
        'jazz': 'ジャズ',
        'classical': 'クラシック',
        'bass_boost': '低音ブースト',
        'treble_boost': '高音ブースト',
        'vocal': 'ボーカル',
        'electronic': 'エレクトロニック',
        'acoustic': 'アコースティック',

        # Frequency bands
        'band_60': '60 Hz',
        'band_170': '170 Hz',
        'band_310': '310 Hz',
        'band_600': '600 Hz',
        'band_1k': '1 kHz',
        'band_3k': '3 kHz',
        'band_6k': '6 kHz',
        'band_12k': '12 kHz',

        # Gain and frequency
        'gain': 'ゲイン',
        'frequency': '周波数',
        'db': 'dB',

        # Volume
        'master_volume': 'マスターボリューム',
        'volume': '音量',
        'mute': 'ミュート',
        'unmute': 'ミュート解除',

        # Output
        'output_device': '出力デバイス',
        'no_device': 'デバイスが見つかりません',
        'active_output': 'アクティブ出力',

        # Actions
        'reset': 'リセット',
        'apply': '適用',

        # Language
        'language': '言語',

        # Dialogs
        'error': 'エラー',
        'success': '成功',
        'save': '保存',
        'cancel': 'キャンセル',
        'close': '閉じる',

        # Status messages
        'preset_saved': 'プリセットが正常に保存されました',
        'preset_deleted': 'プリセットが正常に削除されました',
        'preset_exists': 'この名前のプリセットは既に存在します',
        'eq_applied': 'イコライザー設定が適用されました',
        'eq_disabled': 'イコライザーが無効になりました',
    },
}

# Default language
DEFAULT_LANGUAGE = 'English'

# List of available languages
AVAILABLE_LANGUAGES = list(TRANSLATIONS.keys())


def detect_system_language():
    """Detect the system language from environment variables.

    Returns:
        The language name matching available translations, or 'English' as default.
    """
    import os
    import locale

    # Try to get locale from environment
    lang_code = None
    for var in ['LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE']:
        lang_code = os.environ.get(var)
        if lang_code:
            break

    if not lang_code:
        try:
            lang_code, _ = locale.getdefaultlocale()
        except:
            pass

    if not lang_code:
        return DEFAULT_LANGUAGE

    # Extract language prefix (e.g., 'es' from 'es_ES.UTF-8')
    lang_prefix = lang_code.split('_')[0].split('.')[0].lower()

    # Map language codes to translation keys
    lang_map = {
        'en': 'English',
        'es': 'Español',
        'fr': 'Français',
        'de': 'Deutsch',
        'zh': '中文',
        'ja': '日本語',
    }

    return lang_map.get(lang_prefix, DEFAULT_LANGUAGE)


def get_text(key, language=None):
    """Get translated text for a given key and language.

    Args:
        key: The translation key to look up.
        language: The language to use. Defaults to English if not specified
                  or if the key is not found in the specified language.

    Returns:
        The translated string, or the key itself if no translation is found.
    """
    if language is None:
        language = DEFAULT_LANGUAGE

    lang_dict = TRANSLATIONS.get(language, TRANSLATIONS[DEFAULT_LANGUAGE])
    return lang_dict.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))


def get_preset_display_name(preset_key, language=None):
    """Get the localized display name for a built-in preset.

    Args:
        preset_key: The internal preset key (e.g., 'rock', 'jazz').
        language: The language to use for translation.

    Returns:
        The localized preset name string.
    """
    return get_text(preset_key, language)
