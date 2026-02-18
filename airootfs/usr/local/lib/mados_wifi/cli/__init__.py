"""Command-line interface for mados-wifi.

This module provides a CLI interface for WiFi management without requiring
a graphical environment. It uses the core backend module.
"""

from .manager import WiFiManager
from .command import main

__all__ = ['WiFiManager', 'main']
