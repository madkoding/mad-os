"""
madOS Audio Equalizer
=====================

A professional 8-band audio equalizer application for madOS,
built with PyGTK3 and PipeWire/PulseAudio backend integration.

Features:
    - 8-band parametric equalizer (60Hz to 12kHz)
    - PipeWire filter-chain backend with PulseAudio fallback
    - 10 built-in presets plus custom user presets
    - Nord color theme with visual gain indicators
    - Internationalization support for 6 languages
    - Master volume control with mute toggle
    - Real-time audio output device detection

Package modules:
    - app: Main GTK3 application window and UI
    - backend: PipeWire/PulseAudio audio processing backend
    - presets: Preset management (built-in and custom)
    - translations: Multi-language translation strings
    - theme: Nord color theme CSS for GTK3
"""

__version__ = "1.0.0"
__app_id__ = "mados-equalizer"
__app_name__ = "madOS Equalizer"
