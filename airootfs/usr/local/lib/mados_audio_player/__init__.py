"""
madOS Audio Player
==================

A Winamp-inspired audio player for madOS, built with PyGTK3
and mpv backend. Supports all common audio formats through
mpv/ffmpeg.

Features:
    - Winamp-inspired compact UI with Nord theme
    - Full playback controls (play, pause, stop, prev, next)
    - Seek bar with time display
    - Volume control with mute toggle
    - Playlist management (add files, folders, remove, clear)
    - Shuffle and repeat modes
    - Drag and drop support
    - File browser integration
    - Internationalization support for 6 languages
    - mpv backend (supports MP3, FLAC, OGG, WAV, AAC, OPUS, etc.)

Package modules:
    - app: Main GTK3 application window and UI
    - backend: mpv audio playback backend via JSON IPC
    - playlist: Playlist management
    - translations: Multi-language translation strings
    - theme: Nord color theme CSS for GTK3 (Winamp-inspired)
"""

__version__ = "1.0.0"
__app_id__ = "mados-audio-player"
__app_name__ = "madOS Audio Player"
