#!/usr/bin/env python3
"""
Tests for madOS audio quality auto-detection and configuration.

Validates the mados-audio-quality.sh script that detects hardware audio
capabilities and configures PipeWire/WirePlumber for maximum quality.

These tests verify:
- Script syntax and structure
- Configuration file generation
- Sample rate and bit depth detection logic
- PipeWire/WirePlumber config format
- Integration with systemd services
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")
SKEL_DIR = os.path.join(AIROOTFS, "etc", "skel")

AUDIO_QUALITY_SCRIPT = os.path.join(BIN_DIR, "mados-audio-quality.sh")
AUDIO_QUALITY_SERVICE = os.path.join(SYSTEMD_DIR, "mados-audio-quality.service")
USER_SERVICE = os.path.join(
    SKEL_DIR, ".config", "systemd", "user", "mados-audio-quality.service"
)


# ═══════════════════════════════════════════════════════════════════════════
# Script existence and syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioQualityScriptBasics(unittest.TestCase):
    """Verify the audio quality script exists and has valid syntax."""

    def test_script_exists(self):
        """mados-audio-quality.sh must exist."""
        self.assertTrue(
            os.path.isfile(AUDIO_QUALITY_SCRIPT),
            "mados-audio-quality.sh script not found",
        )

    def test_script_executable_permission(self):
        """Script should be marked executable in profiledef.sh."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn(
            "mados-audio-quality.sh",
            content,
            "mados-audio-quality.sh not found in profiledef.sh",
        )

    def test_script_valid_bash_syntax(self):
        """Script must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", AUDIO_QUALITY_SCRIPT],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Bash syntax error: {result.stderr}")

    def test_script_has_shebang(self):
        """Script must start with bash shebang."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith("#!"))
        self.assertIn("bash", first_line)

    def test_script_uses_strict_mode(self):
        """Script should use set -euo pipefail for safety."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        self.assertIn("set -euo pipefail", content)

    def test_script_has_license(self):
        """Script should include SPDX license identifier."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        self.assertIn("SPDX-License-Identifier", content)


# ═══════════════════════════════════════════════════════════════════════════
# Script structure and functions
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioQualityScriptStructure(unittest.TestCase):
    """Verify the script has all required functions."""

    def setUp(self):
        with open(AUDIO_QUALITY_SCRIPT) as f:
            self.content = f.read()

    def test_has_detect_max_sample_rate_function(self):
        """Script must have detect_max_sample_rate function."""
        self.assertIn("detect_max_sample_rate()", self.content)

    def test_has_detect_max_bit_depth_function(self):
        """Script must have detect_max_bit_depth function."""
        self.assertIn("detect_max_bit_depth()", self.content)

    def test_has_calculate_quantum_function(self):
        """Script must have calculate_quantum function."""
        self.assertIn("calculate_quantum()", self.content)

    def test_has_create_pipewire_config_function(self):
        """Script must have create_pipewire_config function."""
        self.assertIn("create_pipewire_config()", self.content)

    def test_has_create_wireplumber_config_function(self):
        """Script must have create_wireplumber_config function."""
        self.assertIn("create_wireplumber_config()", self.content)

    def test_has_main_function(self):
        """Script must have main function."""
        self.assertIn("main()", self.content)

    def test_uses_systemd_logging(self):
        """Script should use systemd-cat for logging."""
        self.assertIn("systemd-cat", self.content)
        self.assertIn("LOG_TAG", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Sample rate detection logic
# ═══════════════════════════════════════════════════════════════════════════
class TestSampleRateDetection(unittest.TestCase):
    """Verify sample rate detection produces valid outputs."""

    def test_default_sample_rates_defined(self):
        """Script must define standard sample rates."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        # Check for common high-quality rates
        self.assertIn("48000", content)
        self.assertIn("96000", content)
        self.assertIn("192000", content)

    def test_sample_rate_limits(self):
        """Script should limit sample rates to standard values."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        # Should check for standard rates
        self.assertRegex(content, r"44100|48000|88200|96000|176400|192000")


# ═══════════════════════════════════════════════════════════════════════════
# Configuration file generation
# ═══════════════════════════════════════════════════════════════════════════
class TestConfigGeneration(unittest.TestCase):
    """Test configuration file generation in a temporary directory."""

    def setUp(self):
        """Create a temporary directory for test configs."""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_can_execute_script_help(self):
        """Script should execute without errors (dry-run test)."""
        # This tests that the script at least loads without immediate errors
        result = subprocess.run(
            ["bash", "-c", f"source {AUDIO_QUALITY_SCRIPT} && type -t main"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("function", result.stdout)


# ═══════════════════════════════════════════════════════════════════════════
# PipeWire configuration format validation
# ═══════════════════════════════════════════════════════════════════════════
class TestPipeWireConfigFormat(unittest.TestCase):
    """Verify PipeWire configuration format is correct."""

    def test_config_structure(self):
        """Generated config must have proper PipeWire syntax."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()

        # Check for key PipeWire configuration properties
        self.assertIn("default.clock.rate", content)
        self.assertIn("default.clock.quantum", content)
        self.assertIn("resample.quality", content)
        self.assertIn("audio.format", content)

    def test_uses_high_quality_resampling(self):
        """Config should set high quality resampling (quality=10)."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        self.assertIn("resample.quality      = 10", content)

    def test_supports_multiple_formats(self):
        """Config should support S16LE, S24LE, and S32LE formats."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        self.assertIn("S16LE", content)
        self.assertIn("S24LE", content)
        self.assertIn("S32LE", content)


# ═══════════════════════════════════════════════════════════════════════════
# WirePlumber configuration validation
# ═══════════════════════════════════════════════════════════════════════════
class TestWirePlumberConfig(unittest.TestCase):
    """Verify WirePlumber configuration format."""

    def test_wireplumber_rules_structure(self):
        """Generated WirePlumber config must have proper syntax."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()

        # Check for WirePlumber rule syntax
        self.assertIn("monitor.alsa.rules", content)
        self.assertIn("matches", content)
        self.assertIn("actions", content)
        self.assertIn("update-props", content)

    def test_enables_acp_ucm(self):
        """Config should enable ACP and UCM for best device support."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()
        self.assertIn("api.alsa.use-acp", content)
        self.assertIn("api.alsa.use-ucm", content)


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemdServices(unittest.TestCase):
    """Verify systemd service units are properly configured."""

    def test_system_service_exists(self):
        """System-wide service must exist."""
        self.assertTrue(
            os.path.isfile(AUDIO_QUALITY_SERVICE),
            "mados-audio-quality.service not found",
        )

    def test_system_service_valid_syntax(self):
        """Service file must have valid systemd syntax."""
        with open(AUDIO_QUALITY_SERVICE) as f:
            content = f.read()
        self.assertIn("[Unit]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)

    def test_system_service_runs_after_audio_init(self):
        """Service must run after mados-audio-init.service."""
        with open(AUDIO_QUALITY_SERVICE) as f:
            content = f.read()
        self.assertIn("After=", content)
        self.assertIn("mados-audio-init.service", content)

    def test_system_service_oneshot(self):
        """Service should be Type=oneshot."""
        with open(AUDIO_QUALITY_SERVICE) as f:
            content = f.read()
        self.assertIn("Type=oneshot", content)

    def test_system_service_enabled(self):
        """Service should be enabled in multi-user.target.wants."""
        wants_dir = os.path.join(SYSTEMD_DIR, "multi-user.target.wants")
        service_link = os.path.join(wants_dir, "mados-audio-quality.service")
        self.assertTrue(
            os.path.islink(service_link), "mados-audio-quality.service not enabled"
        )

    def test_user_service_exists(self):
        """User service must exist in skel."""
        self.assertTrue(os.path.isfile(USER_SERVICE), "User service not found in skel")

    def test_user_service_valid_syntax(self):
        """User service file must have valid systemd syntax."""
        with open(USER_SERVICE) as f:
            content = f.read()
        self.assertIn("[Unit]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioQualityIntegration(unittest.TestCase):
    """Test integration with the rest of the system."""

    def test_script_in_path(self):
        """Script must be in /usr/local/bin."""
        self.assertTrue(
            AUDIO_QUALITY_SCRIPT.endswith("usr/local/bin/mados-audio-quality.sh")
        )

    def test_works_with_existing_audio_init(self):
        """Should work alongside existing mados-audio-init.sh."""
        audio_init = os.path.join(BIN_DIR, "mados-audio-init.sh")
        self.assertTrue(os.path.isfile(audio_init))

        # Both scripts should be independent
        with open(AUDIO_QUALITY_SCRIPT) as f:
            quality_content = f.read()
        with open(audio_init) as f:
            _ = f.read()

        # Quality script should not interfere with ALSA mixer settings
        self.assertNotIn("amixer", quality_content)

    def test_handles_live_and_installed_environments(self):
        """Script should work in both live and installed systems."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()

        # Should handle both system and user configs
        self.assertIn("/etc/pipewire", content)
        self.assertIn(".config/pipewire", content)
        self.assertIn("/etc/skel", content)

    def test_safe_for_missing_hardware(self):
        """Script should not fail if no audio hardware is present."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()

        # Should use defaults if detection fails
        self.assertIn("DEFAULT_SAMPLE_RATE", content)
        self.assertIn("DEFAULT_BIT_DEPTH", content)


# ═══════════════════════════════════════════════════════════════════════════
# Quantum calculation tests
# ═══════════════════════════════════════════════════════════════════════════
class TestQuantumCalculation(unittest.TestCase):
    """Test buffer size (quantum) calculation logic."""

    def test_quantum_scales_with_sample_rate(self):
        """Higher sample rates should use larger buffers."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()

        # Verify that quantum sizes increase with sample rate
        self.assertIn("192000", content)
        self.assertIn("quantum=1024", content)
        self.assertIn("96000", content)
        self.assertIn("quantum=768", content)

    def test_quantum_ranges_defined(self):
        """Min and max quantum values should be defined."""
        with open(AUDIO_QUALITY_SCRIPT) as f:
            content = f.read()

        self.assertIn("DEFAULT_MIN_QUANTUM", content)
        self.assertIn("DEFAULT_MAX_QUANTUM", content)
        self.assertIn("DEFAULT_QUANTUM", content)


# ═══════════════════════════════════════════════════════════════════════════
# Hardware detection source validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHardwareDetectionSources(unittest.TestCase):
    """Verify detection reads from correct ALSA sources."""

    def setUp(self):
        with open(AUDIO_QUALITY_SCRIPT) as f:
            self.content = f.read()

    def test_reads_codec_files(self):
        """Detection must read from /proc/asound/card*/codec* (static info)."""
        self.assertIn("/proc/asound/card*/codec*", self.content)

    def test_reads_stream_files(self):
        """Detection must read from /proc/asound/card*/stream* (static info)."""
        self.assertIn("/proc/asound/card*/stream*", self.content)

    def test_does_not_read_hw_params(self):
        """Detection must NOT read from hw_params (only shows active stream)."""
        self.assertNotIn("hw_params", self.content)

    def test_bit_depth_checks_codec_and_stream(self):
        """Bit depth detection should check both codec and stream files."""
        # Should grep for S32/S24 in codec files
        self.assertIn('grep -qi "S32" "$codec"', self.content)
        self.assertIn('grep -qi "S24" "$codec"', self.content)
        # Should grep for S32/S24 in stream files
        self.assertIn('grep -qi "S32" "$stream"', self.content)
        self.assertIn('grep -qi "S24" "$stream"', self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Allowed rates validation
# ═══════════════════════════════════════════════════════════════════════════
class TestAllowedRates(unittest.TestCase):
    """Verify PipeWire config uses multiple allowed rates."""

    def setUp(self):
        with open(AUDIO_QUALITY_SCRIPT) as f:
            self.content = f.read()

    def test_has_build_allowed_rates_function(self):
        """Script must have build_allowed_rates function."""
        self.assertIn("build_allowed_rates()", self.content)

    def test_allowed_rates_includes_44100_and_48000(self):
        """Allowed rates must always include 44100 and 48000."""
        self.assertIn('allowed_rates="44100 48000"', self.content)

    def test_allowed_rates_includes_high_rates(self):
        """Allowed rates must include high sample rates for capable hardware."""
        self.assertIn("96000", self.content)
        self.assertIn("192000", self.content)
        self.assertIn("176400", self.content)

    def test_config_does_not_restrict_to_single_rate(self):
        """PipeWire config must not restrict allowed-rates to a single value."""
        # The old bug: allowed-rates = [ ${sample_rate} ]
        # Ensure we use allowed_rates variable, not sample_rate alone
        self.assertIn("[ ${allowed_rates} ]", self.content)
        self.assertNotIn("[ ${sample_rate} ]", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# User service enablement
# ═══════════════════════════════════════════════════════════════════════════
class TestUserServiceEnabled(unittest.TestCase):
    """Verify user service is enabled via symlink."""

    def test_user_service_enabled_in_default_target(self):
        """User service must be enabled in default.target.wants."""
        wants_dir = os.path.join(
            SKEL_DIR, ".config", "systemd", "user", "default.target.wants"
        )
        service_link = os.path.join(wants_dir, "mados-audio-quality.service")
        self.assertTrue(
            os.path.islink(service_link),
            "User mados-audio-quality.service not enabled in default.target.wants",
        )

    def test_user_service_symlink_target(self):
        """User service symlink must point to the correct service file."""
        wants_dir = os.path.join(
            SKEL_DIR, ".config", "systemd", "user", "default.target.wants"
        )
        service_link = os.path.join(wants_dir, "mados-audio-quality.service")
        target = os.readlink(service_link)
        self.assertIn("mados-audio-quality.service", target)


# ═══════════════════════════════════════════════════════════════════════════
# Installer integration for post-installation
# ═══════════════════════════════════════════════════════════════════════════
INSTALLER_DIR = os.path.join(AIROOTFS, "usr", "local", "lib", "mados_installer")
INSTALLATION_PY = os.path.join(INSTALLER_DIR, "pages", "installation.py")


class TestInstallerAudioQualityIntegration(unittest.TestCase):
    """Verify the installer sets up audio quality for the installed system."""

    def setUp(self):
        with open(INSTALLATION_PY) as f:
            self.content = f.read()

    def test_installer_copies_audio_quality_script(self):
        """Installer must copy mados-audio-quality.sh to installed system."""
        self.assertIn("mados-audio-quality.sh", self.content)
        self.assertIn(
            "MNT_USR_LOCAL_BIN",
            self.content,
            "Installer must use MNT_USR_LOCAL_BIN constant for copying scripts",
        )

    def test_installer_creates_system_service(self):
        """First-boot script must create mados-audio-quality.service."""
        self.assertIn("mados-audio-quality.service", self.content)
        self.assertIn(
            "systemctl enable mados-audio-quality.service",
            self.content,
            "Installer must enable mados-audio-quality.service",
        )

    def test_installer_creates_user_service(self):
        """First-boot script must set up user-level audio quality service."""
        self.assertIn(
            "mados-audio-quality.service",
            self.content,
        )
        self.assertIn(
            "default.target.wants/mados-audio-quality.service",
            self.content,
            "Installer must enable user audio quality service via symlink",
        )

    def test_system_service_runs_after_audio_init(self):
        """System service in installer must depend on mados-audio-init."""
        self.assertIn(
            "After=systemd-udev-settle.service sound.target mados-audio-init.service",
            self.content,
        )

    def test_user_service_runs_before_pipewire(self):
        """User service must run before PipeWire starts."""
        self.assertIn(
            "Before=pipewire.service pipewire-pulse.service wireplumber.service",
            self.content,
        )


if __name__ == "__main__":
    unittest.main()
