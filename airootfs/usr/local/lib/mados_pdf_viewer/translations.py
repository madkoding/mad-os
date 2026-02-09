"""
madOS PDF Viewer - Internationalization / Translations

Provides translations for 6 languages:
  English, Español, Français, Deutsch, 中文, 日本語

Usage:
    from .translations import TRANSLATIONS, get_text
    text = get_text('open', lang='English')
"""

TRANSLATIONS = {
    'English': {
        # Window / general
        'title': 'madOS PDF Viewer',
        'language': 'Language',

        # File operations
        'open': 'Open',
        'save': 'Save',
        'save_as': 'Save As',
        'print_doc': 'Print',
        'export_images': 'Export as Images',
        'open_file': 'Open File',
        'save_file': 'Save File',
        'file_info': 'File Info',

        # Navigation
        'page': 'Page',
        'of_pages': 'of',
        'go_to_page': 'Go to Page',
        'total_pages': 'Total Pages',
        'prev_page': 'Previous Page',
        'next_page': 'Next Page',
        'first_page': 'First Page',
        'last_page': 'Last Page',

        # Zoom
        'zoom_in': 'Zoom In',
        'zoom_out': 'Zoom Out',
        'fit_width': 'Fit Width',
        'fit_page': 'Fit Page',
        'actual_size': 'Actual Size',

        # Text annotations
        'text_annotation': 'Text Annotation',
        'add_text': 'Add Text',
        'font_size': 'Font Size',
        'text_color': 'Text Color',

        # Signatures
        'signature': 'Signature',
        'draw_signature': 'Draw Signature',
        'place_signature': 'Place Signature',
        'save_signature': 'Save Signature',
        'load_signature': 'Load Signature',
        'clear_signature': 'Clear Signature',
        'signature_saved': 'Signature saved successfully.',
        'signature_loaded': 'Signature loaded successfully.',

        # Form fields
        'form_fields': 'Form Fields',
        'fill_form': 'Fill Form',
        'highlight_fields': 'Highlight Fields',

        # Annotations
        'annotations': 'Annotations',
        'clear_annotations': 'Clear Annotations',

        # Status / messages
        'error': 'Error',
        'success': 'Success',
        'no_file': 'No file opened.',
        'unsaved_changes': 'You have unsaved changes. Do you want to save before closing?',

        # Printing
        'print_dialog': 'Print Document',
        'printing': 'Printing...',
        'print_complete': 'Print complete.',
    },

    'Español': {
        'title': 'Visor PDF de madOS',
        'language': 'Idioma',

        'open': 'Abrir',
        'save': 'Guardar',
        'save_as': 'Guardar como',
        'print_doc': 'Imprimir',
        'export_images': 'Exportar como imágenes',
        'open_file': 'Abrir archivo',
        'save_file': 'Guardar archivo',
        'file_info': 'Información del archivo',

        'page': 'Página',
        'of_pages': 'de',
        'go_to_page': 'Ir a la página',
        'total_pages': 'Total de páginas',
        'prev_page': 'Página anterior',
        'next_page': 'Página siguiente',
        'first_page': 'Primera página',
        'last_page': 'Última página',

        'zoom_in': 'Acercar',
        'zoom_out': 'Alejar',
        'fit_width': 'Ajustar al ancho',
        'fit_page': 'Ajustar a la página',
        'actual_size': 'Tamaño real',

        'text_annotation': 'Anotación de texto',
        'add_text': 'Agregar texto',
        'font_size': 'Tamaño de fuente',
        'text_color': 'Color del texto',

        'signature': 'Firma',
        'draw_signature': 'Dibujar firma',
        'place_signature': 'Colocar firma',
        'save_signature': 'Guardar firma',
        'load_signature': 'Cargar firma',
        'clear_signature': 'Borrar firma',
        'signature_saved': 'Firma guardada correctamente.',
        'signature_loaded': 'Firma cargada correctamente.',

        'form_fields': 'Campos de formulario',
        'fill_form': 'Rellenar formulario',
        'highlight_fields': 'Resaltar campos',

        'annotations': 'Anotaciones',
        'clear_annotations': 'Borrar anotaciones',

        'error': 'Error',
        'success': 'Éxito',
        'no_file': 'No hay archivo abierto.',
        'unsaved_changes': 'Tiene cambios sin guardar. ¿Desea guardar antes de cerrar?',

        'print_dialog': 'Imprimir documento',
        'printing': 'Imprimiendo...',
        'print_complete': 'Impresión completada.',
    },

    'Français': {
        'title': 'Visionneuse PDF madOS',
        'language': 'Langue',

        'open': 'Ouvrir',
        'save': 'Enregistrer',
        'save_as': 'Enregistrer sous',
        'print_doc': 'Imprimer',
        'export_images': 'Exporter en images',
        'open_file': 'Ouvrir un fichier',
        'save_file': 'Enregistrer le fichier',
        'file_info': 'Informations sur le fichier',

        'page': 'Page',
        'of_pages': 'sur',
        'go_to_page': 'Aller à la page',
        'total_pages': 'Nombre de pages',
        'prev_page': 'Page précédente',
        'next_page': 'Page suivante',
        'first_page': 'Première page',
        'last_page': 'Dernière page',

        'zoom_in': 'Zoom avant',
        'zoom_out': 'Zoom arrière',
        'fit_width': 'Ajuster à la largeur',
        'fit_page': 'Ajuster à la page',
        'actual_size': 'Taille réelle',

        'text_annotation': 'Annotation de texte',
        'add_text': 'Ajouter du texte',
        'font_size': 'Taille de la police',
        'text_color': 'Couleur du texte',

        'signature': 'Signature',
        'draw_signature': 'Dessiner la signature',
        'place_signature': 'Placer la signature',
        'save_signature': 'Enregistrer la signature',
        'load_signature': 'Charger la signature',
        'clear_signature': 'Effacer la signature',
        'signature_saved': 'Signature enregistrée avec succès.',
        'signature_loaded': 'Signature chargée avec succès.',

        'form_fields': 'Champs de formulaire',
        'fill_form': 'Remplir le formulaire',
        'highlight_fields': 'Surligner les champs',

        'annotations': 'Annotations',
        'clear_annotations': 'Effacer les annotations',

        'error': 'Erreur',
        'success': 'Succès',
        'no_file': 'Aucun fichier ouvert.',
        'unsaved_changes': 'Vous avez des modifications non enregistrées. Voulez-vous enregistrer avant de fermer ?',

        'print_dialog': 'Imprimer le document',
        'printing': 'Impression en cours...',
        'print_complete': 'Impression terminée.',
    },

    'Deutsch': {
        'title': 'madOS PDF-Betrachter',
        'language': 'Sprache',

        'open': 'Öffnen',
        'save': 'Speichern',
        'save_as': 'Speichern unter',
        'print_doc': 'Drucken',
        'export_images': 'Als Bilder exportieren',
        'open_file': 'Datei öffnen',
        'save_file': 'Datei speichern',
        'file_info': 'Dateiinformationen',

        'page': 'Seite',
        'of_pages': 'von',
        'go_to_page': 'Gehe zu Seite',
        'total_pages': 'Gesamtseiten',
        'prev_page': 'Vorherige Seite',
        'next_page': 'Nächste Seite',
        'first_page': 'Erste Seite',
        'last_page': 'Letzte Seite',

        'zoom_in': 'Vergrößern',
        'zoom_out': 'Verkleinern',
        'fit_width': 'Breite anpassen',
        'fit_page': 'Seite anpassen',
        'actual_size': 'Originalgröße',

        'text_annotation': 'Textanmerkung',
        'add_text': 'Text hinzufügen',
        'font_size': 'Schriftgröße',
        'text_color': 'Textfarbe',

        'signature': 'Unterschrift',
        'draw_signature': 'Unterschrift zeichnen',
        'place_signature': 'Unterschrift platzieren',
        'save_signature': 'Unterschrift speichern',
        'load_signature': 'Unterschrift laden',
        'clear_signature': 'Unterschrift löschen',
        'signature_saved': 'Unterschrift erfolgreich gespeichert.',
        'signature_loaded': 'Unterschrift erfolgreich geladen.',

        'form_fields': 'Formularfelder',
        'fill_form': 'Formular ausfüllen',
        'highlight_fields': 'Felder hervorheben',

        'annotations': 'Anmerkungen',
        'clear_annotations': 'Anmerkungen löschen',

        'error': 'Fehler',
        'success': 'Erfolg',
        'no_file': 'Keine Datei geöffnet.',
        'unsaved_changes': 'Sie haben nicht gespeicherte Änderungen. Möchten Sie vor dem Schließen speichern?',

        'print_dialog': 'Dokument drucken',
        'printing': 'Drucken...',
        'print_complete': 'Drucken abgeschlossen.',
    },

    '中文': {
        'title': 'madOS PDF 查看器',
        'language': '语言',

        'open': '打开',
        'save': '保存',
        'save_as': '另存为',
        'print_doc': '打印',
        'export_images': '导出为图片',
        'open_file': '打开文件',
        'save_file': '保存文件',
        'file_info': '文件信息',

        'page': '页',
        'of_pages': '/',
        'go_to_page': '跳转到页',
        'total_pages': '总页数',
        'prev_page': '上一页',
        'next_page': '下一页',
        'first_page': '第一页',
        'last_page': '最后一页',

        'zoom_in': '放大',
        'zoom_out': '缩小',
        'fit_width': '适合宽度',
        'fit_page': '适合页面',
        'actual_size': '实际大小',

        'text_annotation': '文本注释',
        'add_text': '添加文本',
        'font_size': '字体大小',
        'text_color': '文本颜色',

        'signature': '签名',
        'draw_signature': '绘制签名',
        'place_signature': '放置签名',
        'save_signature': '保存签名',
        'load_signature': '加载签名',
        'clear_signature': '清除签名',
        'signature_saved': '签名保存成功。',
        'signature_loaded': '签名加载成功。',

        'form_fields': '表单字段',
        'fill_form': '填写表单',
        'highlight_fields': '高亮字段',

        'annotations': '注释',
        'clear_annotations': '清除注释',

        'error': '错误',
        'success': '成功',
        'no_file': '没有打开的文件。',
        'unsaved_changes': '您有未保存的更改。是否在关闭前保存？',

        'print_dialog': '打印文档',
        'printing': '正在打印...',
        'print_complete': '打印完成。',
    },

    '日本語': {
        'title': 'madOS PDFビューア',
        'language': '言語',

        'open': '開く',
        'save': '保存',
        'save_as': '名前を付けて保存',
        'print_doc': '印刷',
        'export_images': '画像として書き出す',
        'open_file': 'ファイルを開く',
        'save_file': 'ファイルを保存',
        'file_info': 'ファイル情報',

        'page': 'ページ',
        'of_pages': '/',
        'go_to_page': 'ページに移動',
        'total_pages': '総ページ数',
        'prev_page': '前のページ',
        'next_page': '次のページ',
        'first_page': '最初のページ',
        'last_page': '最後のページ',

        'zoom_in': '拡大',
        'zoom_out': '縮小',
        'fit_width': '幅に合わせる',
        'fit_page': 'ページに合わせる',
        'actual_size': '実際のサイズ',

        'text_annotation': 'テキスト注釈',
        'add_text': 'テキストを追加',
        'font_size': 'フォントサイズ',
        'text_color': 'テキストの色',

        'signature': '署名',
        'draw_signature': '署名を描く',
        'place_signature': '署名を配置',
        'save_signature': '署名を保存',
        'load_signature': '署名を読み込む',
        'clear_signature': '署名を消去',
        'signature_saved': '署名が正常に保存されました。',
        'signature_loaded': '署名が正常に読み込まれました。',

        'form_fields': 'フォームフィールド',
        'fill_form': 'フォームに記入',
        'highlight_fields': 'フィールドを強調表示',

        'annotations': '注釈',
        'clear_annotations': '注釈を消去',

        'error': 'エラー',
        'success': '成功',
        'no_file': 'ファイルが開かれていません。',
        'unsaved_changes': '保存されていない変更があります。閉じる前に保存しますか？',

        'print_dialog': 'ドキュメントを印刷',
        'printing': '印刷中...',
        'print_complete': '印刷が完了しました。',
    },
}

# Default language
DEFAULT_LANGUAGE = 'English'


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


def get_text(key, lang=None):
    """
    Retrieve a translated string for the given key and language.

    Args:
        key: The translation key to look up.
        lang: The language name (e.g. 'English', 'Deutsch').
              Falls back to DEFAULT_LANGUAGE if not found.

    Returns:
        The translated string, or the key itself if not found.
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    return lang_dict.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))


def available_languages():
    """Return a list of available language names."""
    return list(TRANSLATIONS.keys())
