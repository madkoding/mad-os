#!/usr/bin/env python3
"""
Tests for madOS Installer configuration and translations.

Validates that configuration constants, locale mappings, timezone lists,
package definitions, color palettes, and translation dictionaries are
complete, consistent, and correctly structured.

These tests run in CI without requiring GTK or a display server.
"""

import sys
import os
import re
import types
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
gi_mock = types.ModuleType("gi")
gi_mock.require_version = lambda *a, **kw: None

repo_mock = types.ModuleType("gi.repository")


class _StubMeta(type):
    def __getattr__(cls, name):
        return _StubWidget


class _StubWidget(metaclass=_StubMeta):
    def __init__(self, *a, **kw):
        pass

    def __init_subclass__(cls, **kw):
        pass

    def __getattr__(self, name):
        return _stub_func


def _stub_func(*a, **kw):
    return _StubWidget()


class _StubModule:
    def __getattr__(self, name):
        return _StubWidget


for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango"):
    setattr(repo_mock, name, _StubModule())

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "lib")
sys.path.insert(0, LIB_DIR)

from mados_installer.config import (
    DEMO_MODE,
    LOCALE_MAP,
    TIMEZONES,
    NORD_POLAR_NIGHT,
    NORD_SNOW_STORM,
    NORD_FROST,
    NORD_AURORA,
    PACKAGES_PHASE1,
    PACKAGES_PHASE2,
    PACKAGES,
    GPU_COMPUTE_PACKAGES,
    RSYNC_EXCLUDES,
    LOCALE_KB_MAP,
)
from mados_installer.translations import TRANSLATIONS
from mados_installer.utils import random_suffix


# ═══════════════════════════════════════════════════════════════════════════
# Configuration constants
# ═══════════════════════════════════════════════════════════════════════════
class TestDemoMode(unittest.TestCase):
    """Verify DEMO_MODE is a boolean and defaults to False for production."""

    def test_demo_mode_is_bool(self):
        self.assertIsInstance(DEMO_MODE, bool)

    def test_demo_mode_default(self):
        self.assertFalse(DEMO_MODE, "DEMO_MODE should be False for production builds")


class TestLocaleMap(unittest.TestCase):
    """Verify LOCALE_MAP is well-formed."""

    def test_not_empty(self):
        self.assertGreater(len(LOCALE_MAP), 0)

    def test_english_present(self):
        self.assertIn("English", LOCALE_MAP)

    def test_spanish_present(self):
        self.assertIn("Español", LOCALE_MAP)

    def test_values_are_utf8_locales(self):
        for lang, locale in LOCALE_MAP.items():
            with self.subTest(lang=lang):
                self.assertTrue(
                    locale.endswith(".UTF-8"),
                    f"Locale '{locale}' for '{lang}' should end with .UTF-8",
                )

    def test_all_locales_have_country(self):
        """Every locale should be in xx_YY.UTF-8 format."""
        pattern = re.compile(r"^[a-z]{2}_[A-Z]{2}\.UTF-8$")
        for lang, locale in LOCALE_MAP.items():
            with self.subTest(lang=lang):
                self.assertRegex(locale, pattern)


class TestTimezones(unittest.TestCase):
    """Verify timezone list is complete and valid."""

    def test_not_empty(self):
        self.assertGreater(len(TIMEZONES), 0)

    def test_utc_present(self):
        self.assertIn("UTC", TIMEZONES)

    def test_major_timezones(self):
        expected = [
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
        ]
        for tz in expected:
            with self.subTest(timezone=tz):
                self.assertIn(tz, TIMEZONES)

    def test_no_duplicates(self):
        self.assertEqual(len(TIMEZONES), len(set(TIMEZONES)))

    def test_sorted_by_region(self):
        """Verify UTC is first, then timezones are generally sorted."""
        self.assertEqual(TIMEZONES[0], "UTC")

    def test_format_region_slash_city(self):
        """All non-UTC timezones should have Region/City format."""
        for tz in TIMEZONES:
            if tz == "UTC":
                continue
            with self.subTest(timezone=tz):
                self.assertIn(
                    "/", tz, f"Timezone '{tz}' should have Region/City format"
                )


class TestNordColors(unittest.TestCase):
    """Verify Nord color palette values are valid hex colors."""

    HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def _check_palette(self, palette, name):
        for key, color in palette.items():
            with self.subTest(palette=name, key=key):
                self.assertRegex(
                    color,
                    self.HEX_PATTERN,
                    f"Color '{key}' value '{color}' is not a valid hex color",
                )

    def test_polar_night(self):
        self.assertEqual(len(NORD_POLAR_NIGHT), 4)
        self._check_palette(NORD_POLAR_NIGHT, "POLAR_NIGHT")

    def test_snow_storm(self):
        self.assertEqual(len(NORD_SNOW_STORM), 3)
        self._check_palette(NORD_SNOW_STORM, "SNOW_STORM")

    def test_frost(self):
        self.assertEqual(len(NORD_FROST), 4)
        self._check_palette(NORD_FROST, "FROST")

    def test_aurora(self):
        self.assertEqual(len(NORD_AURORA), 5)
        self._check_palette(NORD_AURORA, "AURORA")

    def test_nord_keys_numbered(self):
        """Nord keys should be nord0-nord15."""
        all_keys = set()
        for palette in (NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_FROST, NORD_AURORA):
            all_keys.update(palette.keys())
        for i in range(16):
            self.assertIn(f"nord{i}", all_keys)


# ═══════════════════════════════════════════════════════════════════════════
# Package lists
# ═══════════════════════════════════════════════════════════════════════════
class TestPackageLists(unittest.TestCase):
    """Verify package lists are non-empty and contain essential packages."""

    def test_phase1_not_empty(self):
        self.assertGreater(len(PACKAGES_PHASE1), 0)

    def test_phase2_not_empty(self):
        self.assertGreater(len(PACKAGES_PHASE2), 0)

    def test_combined_equals_sum(self):
        self.assertEqual(len(PACKAGES), len(PACKAGES_PHASE1) + len(PACKAGES_PHASE2))
        self.assertEqual(PACKAGES, PACKAGES_PHASE1 + PACKAGES_PHASE2)

    def test_no_duplicate_packages(self):
        """No package should appear in both Phase 1 and Phase 2."""
        overlap = set(PACKAGES_PHASE1) & set(PACKAGES_PHASE2)
        self.assertEqual(overlap, set(), f"Packages in both phases: {overlap}")

    def test_essential_phase1_packages(self):
        essential = [
            "base",
            "linux",
            "grub",
            "networkmanager",
            "sudo",
            "python",
            "gtk3",
            "nodejs",
            "npm",
        ]
        for pkg in essential:
            with self.subTest(package=pkg):
                self.assertIn(pkg, PACKAGES_PHASE1)

    def test_essential_phase2_packages(self):
        essential = ["chromium", "code", "git", "pipewire", "bluez"]
        for pkg in essential:
            with self.subTest(package=pkg):
                self.assertIn(pkg, PACKAGES_PHASE2)

    def test_package_names_valid(self):
        """Package names should only contain valid characters."""
        pattern = re.compile(r"^[a-z0-9][a-z0-9._+-]*$")
        for pkg in PACKAGES:
            with self.subTest(package=pkg):
                self.assertRegex(
                    pkg, pattern, f"Package name '{pkg}' contains invalid characters"
                )

    def test_gtk_dependencies_in_phase1(self):
        """GTK dependencies needed for installer must be in Phase 1."""
        gtk_deps = ["python", "python-gobject", "gtk3"]
        for pkg in gtk_deps:
            with self.subTest(package=pkg):
                self.assertIn(pkg, PACKAGES_PHASE1)


class TestLocaleKeyboardMap(unittest.TestCase):
    """Verify locale to keyboard layout mapping is consistent."""

    def test_all_locales_mapped(self):
        """Every locale in LOCALE_MAP should have a keyboard mapping."""
        for lang, locale in LOCALE_MAP.items():
            with self.subTest(lang=lang, locale=locale):
                self.assertIn(
                    locale,
                    LOCALE_KB_MAP,
                    f"Locale '{locale}' for '{lang}' has no keyboard mapping",
                )

    def test_keyboard_layouts_valid(self):
        """Keyboard layouts should be short alphanumeric strings."""
        for locale, layout in LOCALE_KB_MAP.items():
            with self.subTest(locale=locale):
                self.assertTrue(
                    layout.isalpha() and len(layout) <= 4,
                    f"Layout '{layout}' for '{locale}' seems invalid",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Translations
# ═══════════════════════════════════════════════════════════════════════════
class TestTranslations(unittest.TestCase):
    """Verify translation dictionaries are complete and consistent."""

    def test_all_locale_map_languages_have_translations(self):
        for lang in LOCALE_MAP.keys():
            with self.subTest(lang=lang):
                self.assertIn(
                    lang,
                    TRANSLATIONS,
                    f"Language '{lang}' in LOCALE_MAP has no translations",
                )

    def test_english_is_reference(self):
        self.assertIn("English", TRANSLATIONS)

    def test_all_languages_have_same_keys(self):
        """Every language should have the same set of translation keys."""
        reference_keys = set(TRANSLATIONS["English"].keys())
        for lang, trans in TRANSLATIONS.items():
            with self.subTest(lang=lang):
                trans_keys = set(trans.keys())
                missing = reference_keys - trans_keys
                self.assertEqual(
                    missing, set(), f"Language '{lang}' is missing keys: {missing}"
                )

    def test_no_empty_translations(self):
        """No translation value should be an empty string."""
        for lang, trans in TRANSLATIONS.items():
            for key, value in trans.items():
                if isinstance(value, str):
                    with self.subTest(lang=lang, key=key):
                        self.assertGreater(
                            len(value), 0, f"Empty translation for '{key}' in '{lang}'"
                        )

    def test_features_structure(self):
        """Features should be a list of tuples with 2 strings each."""
        for lang, trans in TRANSLATIONS.items():
            with self.subTest(lang=lang):
                features = trans.get("features", [])
                self.assertIsInstance(features, list)
                for i, feat in enumerate(features):
                    self.assertIsInstance(
                        feat, tuple, f"Feature {i} in '{lang}' is not a tuple"
                    )
                    self.assertEqual(
                        len(feat), 2, f"Feature {i} in '{lang}' should have 2 elements"
                    )

    def test_title_consistent(self):
        """Title should be 'madOS' in all languages."""
        for lang, trans in TRANSLATIONS.items():
            with self.subTest(lang=lang):
                self.assertEqual(trans.get("title"), "madOS")


# ═══════════════════════════════════════════════════════════════════════════
# Utility functions
# ═══════════════════════════════════════════════════════════════════════════
class TestRandomSuffix(unittest.TestCase):
    """Verify random_suffix() generates valid hostname suffixes."""

    def test_default_length(self):
        suffix = random_suffix()
        self.assertEqual(len(suffix), 4)

    def test_custom_length(self):
        for length in (1, 8, 16):
            with self.subTest(length=length):
                self.assertEqual(len(random_suffix(length)), length)

    def test_alphanumeric_only(self):
        """Suffix should only contain lowercase letters and digits."""
        for _ in range(20):
            suffix = random_suffix()
            self.assertTrue(suffix.isalnum())
            self.assertEqual(suffix, suffix.lower())

    def test_randomness(self):
        """Two generated suffixes should (almost certainly) differ."""
        suffixes = {random_suffix(8) for _ in range(10)}
        self.assertGreater(len(suffixes), 1)


class TestCreatePageHeader(unittest.TestCase):
    """Verify create_page_header accepts (app, title, step_num) arguments."""

    def test_signature_accepts_app_title_step(self):
        """create_page_header must accept (app, title, step_num) to match callers."""
        import inspect
        from mados_installer.pages.base import create_page_header

        sig = inspect.signature(create_page_header)
        params = list(sig.parameters.keys())
        self.assertEqual(params[0], "app", "First parameter must be 'app'")
        self.assertEqual(params[1], "title", "Second parameter must be 'title'")
        self.assertEqual(params[2], "step_num", "Third parameter must be 'step_num'")

    def test_callable_with_app_title_step(self):
        """create_page_header(app, title, step_num) must not raise TypeError."""
        from mados_installer.pages.base import create_page_header

        # Should not raise when called with (app_object, str, int)
        class FakeApp:
            pass

        try:
            create_page_header(FakeApp(), "Test Title", 3)
        except TypeError as e:
            self.fail(f"create_page_header raised TypeError: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Rsync installation configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestRsyncConfig(unittest.TestCase):
    """Verify rsync-based installation configuration constants."""

    PKG_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._+-]*$")

    # -- GPU_COMPUTE_PACKAGES ------------------------------------------

    def test_gpu_compute_packages_is_dict(self):
        """GPU_COMPUTE_PACKAGES must be a dict."""
        self.assertIsInstance(GPU_COMPUTE_PACKAGES, dict)

    def test_gpu_compute_packages_has_required_keys(self):
        """GPU_COMPUTE_PACKAGES must have 'nvidia', 'amd', and 'common' keys."""
        for key in ("nvidia", "amd", "common"):
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    GPU_COMPUTE_PACKAGES,
                    f"GPU_COMPUTE_PACKAGES missing required key '{key}'",
                )

    def test_gpu_compute_packages_values_non_empty(self):
        """Each GPU_COMPUTE_PACKAGES value must be a non-empty list."""
        for key, pkgs in GPU_COMPUTE_PACKAGES.items():
            with self.subTest(key=key):
                self.assertIsInstance(
                    pkgs, list, f"GPU_COMPUTE_PACKAGES['{key}'] must be a list"
                )
                self.assertGreater(
                    len(pkgs), 0, f"GPU_COMPUTE_PACKAGES['{key}'] must not be empty"
                )

    def test_gpu_compute_packages_valid_names(self):
        """All GPU compute package names must be valid Arch package names."""
        for key, pkgs in GPU_COMPUTE_PACKAGES.items():
            for pkg in pkgs:
                with self.subTest(key=key, package=pkg):
                    self.assertRegex(
                        pkg,
                        self.PKG_NAME_PATTERN,
                        f"GPU_COMPUTE_PACKAGES['{key}'] entry '{pkg}' is invalid",
                    )

    def test_nvidia_has_cuda(self):
        """NVIDIA GPU compute packages must include CUDA."""
        self.assertIn("cuda", GPU_COMPUTE_PACKAGES["nvidia"])

    def test_amd_has_rocm(self):
        """AMD GPU compute packages must include ROCm."""
        rocm_pkgs = GPU_COMPUTE_PACKAGES["amd"]
        has_rocm = any("rocm" in p for p in rocm_pkgs)
        self.assertTrue(has_rocm, "AMD packages must include ROCm runtime")

    def test_common_has_opencl_headers(self):
        """Common GPU compute packages must include opencl-headers."""
        self.assertIn("opencl-headers", GPU_COMPUTE_PACKAGES["common"])

    # -- RSYNC_EXCLUDES ------------------------------------------------

    def test_rsync_excludes_not_empty(self):
        """RSYNC_EXCLUDES must be a non-empty list."""
        self.assertIsInstance(RSYNC_EXCLUDES, list)
        self.assertGreater(
            len(RSYNC_EXCLUDES), 0, "RSYNC_EXCLUDES must not be empty"
        )

    def test_rsync_excludes_start_with_slash(self):
        """All RSYNC_EXCLUDES entries must start with '/'."""
        for exc in RSYNC_EXCLUDES:
            with self.subTest(exclude=exc):
                self.assertTrue(
                    exc.startswith("/"),
                    f"RSYNC_EXCLUDES entry '{exc}' must start with '/'",
                )

    def test_rsync_excludes_critical_entries(self):
        """Critical virtual filesystems and mount points must be excluded."""
        critical = ["/dev/*", "/proc/*", "/sys/*", "/mnt/*"]
        for entry in critical:
            with self.subTest(exclude=entry):
                self.assertIn(
                    entry,
                    RSYNC_EXCLUDES,
                    f"Critical exclude '{entry}' missing from RSYNC_EXCLUDES",
                )

    def test_rsync_excludes_run_and_tmp(self):
        """Transient directories /run/* and /tmp/* must be excluded."""
        # These are rsync exclude patterns (not directory access) — safe by design
        for entry in ("/run/*", "/tmp/*"):  # NOSONAR - rsync exclude patterns  # noqa: S5443
            with self.subTest(exclude=entry):
                self.assertIn(entry, RSYNC_EXCLUDES)

    def test_rsync_excludes_machine_id(self):
        """machine-id must be excluded so it can be regenerated on first boot."""
        self.assertIn("/etc/machine-id", RSYNC_EXCLUDES)

    def test_rsync_excludes_fstab(self):
        """fstab must be excluded so genfstab can generate a fresh one."""
        self.assertIn("/etc/fstab", RSYNC_EXCLUDES)

    def test_rsync_excludes_pacman_cache(self):
        """Pacman package cache must be excluded to save disk space."""
        self.assertIn("/var/cache/pacman/pkg/*", RSYNC_EXCLUDES)


if __name__ == "__main__":
    unittest.main()
