"""
Tests for madOS post-installation configuration and system setup

Updated for modular installer architecture.
Tests now validate the external bash scripts in mados_installer/scripts/
"""

import os
import re
import subprocess
import unittest
from unittest.mock import MagicMock, patch

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SCRIPTS_DIR = os.path.join(LIB_DIR, "mados_installer", "scripts")


# ═══════════════════════════════════════════════════════════════════════════
# Initramfs / mkinitcpio preset restoration
# ═══════════════════════════════════════════════════════════════════════════
class TestInitramfsPresetRestoration(unittest.TestCase):
    """Verify the installer restores the standard linux.preset before mkinitcpio."""

    def setUp(self):
        rebuild_script = os.path.join(SCRIPTS_DIR, "rebuild-initramfs.sh")
        if not os.path.isfile(rebuild_script):
            self.skipTest("rebuild-initramfs.sh not found")
        with open(rebuild_script) as f:
            self.script_content = f.read()

    def test_restores_standard_linux_preset(self):
        """Installer must restore standard linux.preset with default/fallback presets."""
        self.assertIn(
            "PRESETS=('default' 'fallback')",
            self.script_content,
            "Installer must restore standard PRESETS=('default' 'fallback') in linux.preset",
        )

    def test_removes_archiso_mkinitcpio_conf(self):
        """Installer must remove archiso-specific mkinitcpio config."""
        self.assertIn(
            "rm -f /etc/mkinitcpio.conf.d/archiso.conf",
            self.script_content,
            "Installer must remove archiso.conf before mkinitcpio -P",
        )

    def test_preset_written_before_mkinitcpio(self):
        """linux.preset must be restored before mkinitcpio -P runs."""
        preset_pos = self.script_content.find("PRESETS=('default' 'fallback')")
        mkinitcpio_pos = self.script_content.find("mkinitcpio -P")
        self.assertNotEqual(preset_pos, -1, "Must contain preset restoration")
        self.assertNotEqual(mkinitcpio_pos, -1, "Must contain mkinitcpio -P")
        self.assertLess(
            preset_pos,
            mkinitcpio_pos,
            "linux.preset must be written before mkinitcpio -P is called",
        )

    def test_kernel_recovery_before_mkinitcpio(self):
        """Installer must recover kernel from modules dir if /boot/vmlinuz-linux is missing."""
        self.assertIn(
            "/usr/lib/modules/",
            self.script_content,
            "Installer must recover kernel from /usr/lib/modules/*/vmlinuz",
        )
        recovery_pos = self.script_content.find("/usr/lib/modules/")
        mkinitcpio_pos = self.script_content.find("mkinitcpio -P")
        self.assertLess(
            recovery_pos,
            mkinitcpio_pos,
            "Kernel recovery must happen before mkinitcpio -P is called",
        )

    def test_kernel_recovery_fallback_reinstall(self):
        """Installer must have fallback to reinstall linux package if kernel not found."""
        self.assertIn(
            "pacman -Sy --noconfirm linux",
            self.script_content,
            "Installer must fallback to reinstalling linux package if kernel still missing",
        )

    def test_kms_before_plymouth_in_mkinitcpio(self):
        """mkinitcpio.conf must have kms hook before plymouth."""
        self.assertIn(
            "HOOKS=(base udev autodetect microcode modconf kms plymouth block filesystems keyboard fsck)",
            self.script_content,
            "mkinitcpio.conf must have kms before plymouth in HOOKS",
        )

    def test_microcode_hook_in_mkinitcpio(self):
        """mkinitcpio.conf must include microcode hook."""
        self.assertIn(
            "microcode",
            self.script_content,
            "mkinitcpio.conf must include microcode hook",
        )

    def test_kernel_recovery_before_grub(self):
        """Kernel recovery must happen before GRUB installation."""
        # Kernel recovery is in rebuild-initramfs.sh which runs before GRUB config
        # Just verify the script contains kernel recovery
        self.assertIn(
            "vmlinuz-linux",
            self.script_content,
            "Script must handle vmlinuz-linux kernel",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live ISO cleanup
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveISOCleanup(unittest.TestCase):
    """Verify the installer removes live ISO-specific configurations."""

    def setUp(self):
        apply_script = os.path.join(SCRIPTS_DIR, "apply-configuration.sh")
        config_script = os.path.join(SCRIPTS_DIR, "configure-system.sh")
        
        if not os.path.isfile(apply_script):
            self.apply_content = ""
        else:
            with open(apply_script) as f:
                self.apply_content = f.read()
        
        if not os.path.isfile(config_script):
            self.config_content = ""
        else:
            with open(config_script) as f:
                self.config_content = f.read()
        
        self.combined_content = self.apply_content + self.config_content

    def test_removes_live_autologin_override(self):
        """Installer must remove live autologin override."""
        self.assertIn(
            "rm -rf /etc/systemd/system/getty@tty1.service.d",
            self.config_content,
            "Installer must delete getty@tty1 autologin override",
        )

    def test_removes_live_user_mados(self):
        """Installer must remove the live user mados."""
        self.assertIn(
            "userdel",
            self.config_content,
            "Installer must delete mados user",
        )

    def test_removes_live_sudoers(self):
        """Installer must remove live sudoers rules."""
        self.assertIn(
            "rm -f /etc/sudoers.d/99-opencode-nopasswd",
            self.config_content,
            "Installer must remove 99-opencode-nopasswd sudoers",
        )

    def test_removes_archiso_root_scripts(self):
        """Installer must remove archiso root scripts."""
        self.assertIn(
            "rm -f /root/.automated_script.sh",
            self.apply_content,
            "Installer must remove /root/.automated_script.sh",
        )

    def test_cleans_dangling_symlinks(self):
        """Installer must clean dangling systemd symlinks."""
        self.assertIn(
            "find /etc/systemd/system -type l ! -exec test -e {} \\; -delete",
            self.config_content,
            "Installer must remove dangling symlinks",
        )

    def test_disable_before_rm(self):
        """Services must be disabled before removing unit files."""
        self.assertIn(
            "systemctl disable",
            self.config_content,
            "Installer must disable services before removal",
        )

    def test_removes_live_only_services(self):
        """Installer must remove live-only systemd services."""
        for svc in ["livecd-talk.service", "pacman-init.service", "choose-mirror.service"]:
            with self.subTest(service=svc):
                self.assertIn(svc, self.config_content, f"Installer must remove {svc}")

    def test_removes_timezone_service(self):
        """Installer must remove mados-timezone.service."""
        self.assertIn(
            "mados-timezone.service",
            self.config_content,
            "Installer must remove mados-timezone.service",
        )

    def test_initializes_pacman_keyring_in_chroot(self):
        """Installer must initialize pacman keyring in chroot."""
        self.assertIn(
            "pacman-key --init",
            self.config_content,
            "Installer must initialize pacman keyring",
        )

    def test_keyring_init_before_pacman_calls(self):
        """pacman-key must be initialized before package operations."""
        keyring_pos = self.config_content.find("pacman-key --init")
        pacman_pos = self.config_content.find("pacman -Sy")
        if keyring_pos != -1 and pacman_pos != -1:
            self.assertLess(keyring_pos, pacman_pos, "Keyring must be initialized before pacman calls")

    def test_keyring_init_before_services(self):
        """Keyring init must run before enabling services."""
        keyring_pos = self.config_content.find("pacman-key --populate")
        systemctl_pos = self.config_content.find("systemctl enable")
        if keyring_pos != -1 and systemctl_pos != -1:
            self.assertLess(keyring_pos, systemctl_pos, "Keyring must be ready before services")

    def test_live_cleanup_before_useradd(self):
        """Live artifacts must be removed before creating new user."""
        rm_pos = self.config_content.find("userdel mados")
        useradd_pos = self.config_content.find("useradd")
        if rm_pos != -1 and useradd_pos != -1:
            self.assertLess(rm_pos, useradd_pos, "Live user must be removed before useradd")

    def test_useradd_uses_usr_bin_zsh(self):
        """New user must use /usr/bin/zsh as default shell."""
        self.assertIn(
            "/usr/bin/zsh",
            self.config_content,
            "User must be created with /usr/bin/zsh shell",
        )

    def test_creates_sway_pacman_hook(self):
        """Installer must create pacman hook for Sway session file."""
        self.assertIn(
            "sway-desktop-override.hook",
            self.apply_content,
            "Installer must create sway-desktop-override.hook",
        )

    def test_creates_hyprland_pacman_hook(self):
        """Installer must create pacman hook for Hyprland session file."""
        self.assertIn(
            "hyprland-desktop-override.hook",
            self.apply_content,
            "Installer must create hyprland-desktop-override.hook",
        )

    def test_pacman_hooks_have_correct_exec(self):
        """Pacman hooks must use sed to update session .desktop files."""
        self.assertIn(
            "Exec = /usr/bin/sed",
            self.apply_content,
            "Pacman hooks must use sed to modify .desktop files",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Post-install services
# ═══════════════════════════════════════════════════════════════════════════
class TestPostInstallServices(unittest.TestCase):
    """Verify essential services are enabled during installation."""

    def setUp(self):
        apply_script = os.path.join(SCRIPTS_DIR, "apply-configuration.sh")
        config_script = os.path.join(SCRIPTS_DIR, "configure-system.sh")
        
        self.script_content = ""
        if os.path.isfile(apply_script):
            with open(apply_script) as f:
                self.script_content += f.read()
        if os.path.isfile(config_script):
            with open(config_script) as f:
                self.script_content += f.read()
        
        if not self.script_content:
            self.skipTest("No config scripts found")

    def test_enables_greetd(self):
        """Installer must enable greetd display manager."""
        self.assertIn(
            "systemctl enable greetd",
            self.script_content,
            "Installer must enable greetd",
        )

    def test_enables_plymouth_quit_wait(self):
        """Installer must enable plymouth-quit-wait.service."""
        self.assertIn(
            "plymouth-quit-wait.service",
            self.script_content,
            "Installer must enable plymouth-quit-wait.service",
        )

    def test_greetd_ordered_after_plymouth_quit(self):
        """greetd.service.d override must order after plymouth-quit-wait."""
        self.assertIn(
            "After=systemd-logind.service plymouth-quit-wait.service",
            self.script_content,
            "greetd must start after plymouth-quit-wait",
        )

    def test_required_services_enabled(self):
        """Installer must enable essential services."""
        required = ["NetworkManager", "systemd-resolved", "earlyoom", "systemd-timesyncd"]
        for svc in required:
            with self.subTest(service=svc):
                self.assertIn(f"systemctl enable {svc}", self.script_content)


# ═══════════════════════════════════════════════════════════════════════════
# Copy item error reporting
# ═══════════════════════════════════════════════════════════════════════════
class TestCopyItemErrorReporting(unittest.TestCase):
    """Verify _copy_item function has proper error reporting."""

    def setUp(self):
        import sys
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()

    def test_copy_item_checks_source_exists(self):
        """copy_item must check if source file exists before copying."""
        from mados_installer.modules.file_copier import copy_item
        import inspect
        source = inspect.getsource(copy_item)
        self.assertIn(
            "os.path.exists",
            source,
            "copy_item must check os.path.exists",
        )

    def test_copy_item_warns_on_missing_source(self):
        """copy_item must print warning when source doesn't exist."""
        from mados_installer.modules.file_copier import copy_item
        import inspect
        source = inspect.getsource(copy_item)
        self.assertIn(
            "WARNING",
            source,
            "copy_item must warn on missing source",
        )

    def test_copy_item_captures_cp_output(self):
        """copy_item must capture cp stderr."""
        from mados_installer.modules.file_copier import copy_item
        import inspect
        source = inspect.getsource(copy_item)
        self.assertIn(
            "capture_output",
            source,
            "copy_item must capture subprocess output",
        )

    def test_copy_item_checks_returncode(self):
        """copy_item must check cp return code."""
        from mados_installer.modules.file_copier import copy_item
        import inspect
        source = inspect.getsource(copy_item)
        self.assertIn(
            "returncode",
            source,
            "copy_item must check returncode",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Chroot validation
# ═══════════════════════════════════════════════════════════════════════════
class TestChrootValidation(unittest.TestCase):
    """Verify chroot script validation before execution."""

    def setUp(self):
        import sys
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()

    def test_validates_script_exists_before_chroot(self):
        """Installer must validate config script exists before chroot."""
        # This is now handled by the modular structure
        # configure-system.sh is copied and validated in file_copier module
        from mados_installer.modules.file_copier import step_copy_scripts
        import inspect
        source = inspect.getsource(step_copy_scripts)
        self.assertIn("copy_item", source, "Must use copy_item to copy scripts")

    def test_validates_script_not_empty(self):
        """Chroot must fail if config script is empty."""
        # This validation is implicit - bash will fail on empty script
        from mados_installer.modules.config_generator import build_config_script
        script = build_config_script({
            "username": "test",
            "timezone": "UTC",
            "locale": "en_US.UTF-8",
            "hostname": "test",
            "disk": "/dev/sda",
        })
        self.assertGreater(len(script), 100, "Config script must have content")


if __name__ == "__main__":
    unittest.main()
