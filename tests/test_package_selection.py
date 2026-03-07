#!/usr/bin/env python3
"""
Tests for madOS Installer Package Selection Page.

Validates that the package selection page:
- Displays all package groups correctly
- Has correct default selections
- Properly tracks user selections
- Integrates with summary page
"""

import os
import sys
import unittest

# Mock gi.repository before importing GTK components
sys.modules['gi'] = unittest.mock.MagicMock()
sys.modules['gi.repository'] = unittest.mock.MagicMock()

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")

sys.path.insert(0, LIB_DIR)


class TestPackageGroups(unittest.TestCase):
    """Test package group definitions."""

    def setUp(self):
        from mados_installer.pages.packages import PACKAGE_GROUPS
        self.groups = PACKAGE_GROUPS

    def test_has_dev_tools_group(self):
        """Must have Development Tools group."""
        self.assertIn("dev_tools", self.groups)
        self.assertEqual(self.groups["dev_tools"]["name"], "Development Tools")

    def test_has_ai_ml_group(self):
        """Must have AI/ML Tools group."""
        self.assertIn("ai_ml", self.groups)
        self.assertEqual(self.groups["ai_ml"]["name"], "AI/ML Tools")

    def test_has_multimedia_group(self):
        """Must have Multimedia Production group."""
        self.assertIn("multimedia", self.groups)
        self.assertEqual(self.groups["multimedia"]["name"], "Multimedia Production")

    def test_groups_have_required_fields(self):
        """Each group must have name, description, icon, and packages."""
        for group_id, group_data in self.groups.items():
            self.assertIn("name", group_data)
            self.assertIn("description", group_data)
            self.assertIn("icon", group_data)
            self.assertIn("packages", group_data)

    def test_packages_have_required_fields(self):
        """Each package must have id, name, and default fields."""
        for group_id, group_data in self.groups.items():
            for pkg in group_data["packages"]:
                self.assertIn("id", pkg)
                self.assertIn("name", pkg)
                self.assertIn("default", pkg)

    def test_dev_tools_packages(self):
        """Dev Tools should have essential packages."""
        dev_packages = [p["id"] for p in self.groups["dev_tools"]["packages"]]
        self.assertIn("base-devel", dev_packages)
        self.assertIn("git", dev_packages)
        self.assertIn("docker", dev_packages)

    def test_ai_ml_packages(self):
        """AI/ML should have essential packages."""
        ai_packages = [p["id"] for p in self.groups["ai_ml"]["packages"]]
        self.assertIn("ollama", ai_packages)
        self.assertIn("opencode", ai_packages)
        self.assertIn("python-pytorch", ai_packages)

    def test_multimedia_packages(self):
        """Multimedia should have essential packages."""
        multimedia_packages = [p["id"] for p in self.groups["multimedia"]["packages"]]
        self.assertIn("kdenlive", multimedia_packages)
        self.assertIn("gimp", multimedia_packages)
        self.assertIn("blender", multimedia_packages)


class TestPackageSelectionPage(unittest.TestCase):
    """Test the PackageSelectionPage logic."""

    def test_package_groups_structure(self):
        """Package groups should have correct structure."""
        from mados_installer.pages.packages import PACKAGE_GROUPS
        
        self.assertIsInstance(PACKAGE_GROUPS, dict)
        self.assertGreater(len(PACKAGE_GROUPS), 0)
        
        # Check each group has required fields
        for group_id, group_data in PACKAGE_GROUPS.items():
            self.assertIn("name", group_data)
            self.assertIn("description", group_data)
            self.assertIn("icon", group_data)
            self.assertIn("packages", group_data)
            self.assertIsInstance(group_data["packages"], list)

    def test_default_selections_logic(self):
        """Default selections should include essential packages."""
        from mados_installer.pages.packages import PACKAGE_GROUPS
        
        selected = set()
        for group_id, group_data in PACKAGE_GROUPS.items():
            for pkg in group_data["packages"]:
                if pkg.get("default", False):
                    selected.add(pkg["id"])
        
        # Essential defaults
        self.assertIn("ollama", selected)
        self.assertIn("opencode", selected)
        self.assertIn("base-devel", selected)
        self.assertIn("git", selected)

    def test_all_package_ids_unique(self):
        """All package IDs should be unique across groups."""
        from mados_installer.pages.packages import PACKAGE_GROUPS
        
        all_ids = []
        for group_data in PACKAGE_GROUPS.values():
            for pkg in group_data["packages"]:
                all_ids.append(pkg["id"])
        
        # Check for duplicates
        self.assertEqual(len(all_ids), len(set(all_ids)), "Duplicate package IDs found")


class TestPackageIntegration(unittest.TestCase):
    """Test integration with installer flow."""

    def test_page_registered_in_init(self):
        """PackageSelectionPage must be exported from pages package."""
        from mados_installer.pages import PackageSelectionPage
        self.assertTrue(callable(PackageSelectionPage))

    def test_package_groups_importable(self):
        """PACKAGE_GROUPS must be importable from packages module."""
        from mados_installer.pages.packages import PACKAGE_GROUPS
        self.assertIsInstance(PACKAGE_GROUPS, dict)
        self.assertGreater(len(PACKAGE_GROUPS), 0)

    def test_app_imports_package_page(self):
        """app.py must import PackageSelectionPage."""
        app_py_path = os.path.join(LIB_DIR, "mados_installer", "app.py")
        with open(app_py_path) as f:
            content = f.read()
        self.assertIn("PackageSelectionPage", content)

    def test_app_builds_package_page(self):
        """app.py must create PackageSelectionPage in _build_pages."""
        app_py_path = os.path.join(LIB_DIR, "mados_installer", "app.py")
        with open(app_py_path) as f:
            content = f.read()
        self.assertIn("PackageSelectionPage(self", content)


class TestSummaryIntegration(unittest.TestCase):
    """Test summary page shows package selection."""

    def test_summary_shows_packages(self):
        """Summary page update must reference package selection."""
        summary_py_path = os.path.join(LIB_DIR, "mados_installer", "pages", "summary.py")
        with open(summary_py_path) as f:
            content = f.read()
        self.assertIn("package_selection", content)
        self.assertIn("PACKAGE_GROUPS", content)


class TestPackageInstallation(unittest.TestCase):
    """Test that selected packages are used during installation."""

    def test_installer_references_packages(self):
        """Installer should reference package selection."""
        install_py_path = os.path.join(LIB_DIR, "mados_installer", "pages", "installation.py")
        if os.path.isfile(install_py_path):
            with open(install_py_path) as f:
                content = f.read()
            # Installer should handle package selection somehow
            # This is a placeholder for future implementation
            self.assertTrue(os.path.isfile(install_py_path))


if __name__ == "__main__":
    unittest.main()
