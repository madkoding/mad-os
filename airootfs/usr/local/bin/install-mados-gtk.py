#!/usr/bin/env python3
"""
madOS Installer - Launcher script
Thin wrapper that imports and runs the modular installer package
from /usr/local/lib/mados-installer/
"""

import sys
sys.path.insert(0, '/usr/local/lib')

from mados_installer import main
main()
