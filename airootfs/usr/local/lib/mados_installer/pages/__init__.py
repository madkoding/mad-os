"""
madOS Installer - Pages package
"""

from .welcome import create_welcome_page
from .wifi import create_wifi_page
from .disk import create_disk_page
from .partitioning import create_partitioning_page
from .user import create_user_page
from .locale import create_locale_page
from .summary import create_summary_page
from .installation import create_installation_page
from .completion import create_completion_page

__all__ = [
    'create_welcome_page',
    'create_wifi_page',
    'create_disk_page',
    'create_partitioning_page',
    'create_user_page',
    'create_locale_page',
    'create_summary_page',
    'create_installation_page',
    'create_completion_page',
]
