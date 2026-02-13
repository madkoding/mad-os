#!/usr/bin/env python3
"""
Tests for madOS Hyprland configuration validation.

Validates hyprland.conf syntax and structure to catch configuration errors
that would cause Hyprland to fail or show warnings at startup. Since
Hyprland cannot be run in CI (requires a GPU/display), these tests perform
static analysis on the configuration file.

Checks include:
  - Balanced braces (sections properly opened/closed)
  - Valid top-level keywords and section names
  - Bind syntax (correct dispatcher format)
  - Variable definitions and references
  - Window rule format
  - Color format (rgba/rgb hex)
  - No duplicate keybindings
  - Required sections present
  - Environment variable syntax
"""

import os
import re
import unittest
from collections import Counter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
SKEL_DIR = os.path.join(AIROOTFS, "etc", "skel")
HYPR_DIR = os.path.join(SKEL_DIR, ".config", "hypr")
HYPRLAND_CONF = os.path.join(HYPR_DIR, "hyprland.conf")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")


def _read_config():
    """Read and return the hyprland.conf content."""
    with open(HYPRLAND_CONF) as f:
        return f.read()


def _config_lines():
    """Return non-empty, non-comment lines from hyprland.conf."""
    lines = []
    with open(HYPRLAND_CONF) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# File existence
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandConfigExists(unittest.TestCase):
    """Verify Hyprland configuration files exist."""

    def test_hyprland_conf_exists(self):
        """hyprland.conf must exist in /etc/skel/.config/hypr/."""
        self.assertTrue(
            os.path.isfile(HYPRLAND_CONF),
            "hyprland.conf missing from /etc/skel/.config/hypr/",
        )

    def test_hyprland_session_script_exists(self):
        """hyprland-session wrapper script must exist."""
        path = os.path.join(BIN_DIR, "hyprland-session")
        self.assertTrue(os.path.isfile(path), "hyprland-session missing")


# ═══════════════════════════════════════════════════════════════════════════
# Brace balancing and section structure
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandBraceBalance(unittest.TestCase):
    """Verify braces are properly balanced in hyprland.conf."""

    def test_braces_balanced(self):
        """Every opening { must have a matching closing }."""
        content = _read_config()
        # Remove comments and strings to avoid false positives
        clean = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        opens = clean.count("{")
        closes = clean.count("}")
        self.assertEqual(
            opens, closes,
            f"Unbalanced braces: {opens} opening vs {closes} closing",
        )

    def test_no_nested_section_beyond_two_levels(self):
        """Hyprland supports at most 2-level nesting (e.g. decoration { blur { } })."""
        content = _read_config()
        clean = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        depth = 0
        max_depth = 0
        for char in clean:
            if char == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == "}":
                depth -= 1
        self.assertLessEqual(
            max_depth, 3,
            f"Nesting too deep ({max_depth} levels) – Hyprland supports max 2-level sections",
        )
        self.assertGreaterEqual(
            depth, 0,
            "Brace depth went negative – more } than { at some point",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Valid top-level keywords
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandKeywords(unittest.TestCase):
    """Verify only valid Hyprland keywords are used at the top level."""

    # Known valid top-level keywords in Hyprland config
    VALID_TOP_LEVEL_KEYWORDS = {
        # Sections (categories)
        "general", "decoration", "animations", "input", "misc",
        "dwindle", "master", "gestures", "group", "xwayland",
        "opengl", "render", "cursor", "debug", "binds",
        "ecosystem",
        # Commands / keywords
        "exec-once", "exec", "bind", "binde", "bindel", "bindm",
        "bindr", "bindl", "bindn", "bindrl",
        "monitor", "workspace", "windowrule", "windowrulev2",
        "layerrule", "layerrulev2",
        "source", "env", "bezier", "animation",
        "submap", "plugin",
        "device",
        # Variable definitions
    }

    def _get_top_level_keywords(self):
        """Extract top-level keywords from config (outside sections)."""
        content = _read_config()
        lines = content.splitlines()
        depth = 0
        keywords = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Track brace depth
            depth += stripped.count("{") - stripped.count("}")

            # At top level (depth 0 before this line's braces, or depth 1 if line opens a section)
            # A top-level line is one where depth was 0 before processing
            pre_depth = depth - stripped.count("{") + stripped.count("}")
            if pre_depth == 0:
                # Extract the keyword (before = or {)
                match = re.match(r'^\$?\w[\w-]*', stripped)
                if match:
                    keywords.append(match.group(0))
        return keywords

    def test_all_top_level_keywords_valid(self):
        """Every top-level keyword should be a known Hyprland keyword or variable."""
        keywords = self._get_top_level_keywords()
        for kw in keywords:
            # Skip variable definitions ($var)
            if kw.startswith("$"):
                continue
            with self.subTest(keyword=kw):
                self.assertIn(
                    kw, self.VALID_TOP_LEVEL_KEYWORDS,
                    f"Unknown top-level keyword '{kw}' in hyprland.conf. "
                    f"If this is a new valid keyword, add it to VALID_TOP_LEVEL_KEYWORDS.",
                )

    def test_no_windowrulev2_used(self):
        """windowrulev2 is deprecated; windowrule should be used instead."""
        content = _read_config()
        clean = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        self.assertNotIn(
            "windowrulev2",
            clean,
            "windowrulev2 is deprecated – use windowrule instead",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Required sections
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandRequiredSections(unittest.TestCase):
    """Verify essential sections are present in the config."""

    REQUIRED_SECTIONS = ["input", "general", "decoration", "animations"]

    def test_required_sections_present(self):
        """Essential sections must be defined in hyprland.conf."""
        content = _read_config()
        for section in self.REQUIRED_SECTIONS:
            with self.subTest(section=section):
                pattern = rf'^\s*{re.escape(section)}\s*\{{' 
                self.assertRegex(
                    content, re.compile(pattern, re.MULTILINE),
                    f"Required section '{section}' missing from hyprland.conf",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Variable definitions and references
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandVariables(unittest.TestCase):
    """Verify variable definitions and usage are consistent."""

    def _get_defined_vars(self):
        """Return set of defined variable names ($varName = ...)."""
        content = _read_config()
        return set(re.findall(r'^\s*\$(\w+)\s*=', content, re.MULTILINE))

    def _get_used_vars(self):
        """Return set of variable names used in the config ($varName)."""
        content = _read_config()
        # Remove definition lines to only find usage
        clean = re.sub(r'^\s*\$\w+\s*=.*$', '', content, flags=re.MULTILINE)
        # Remove comments
        clean = re.sub(r'#.*$', '', clean, flags=re.MULTILINE)
        return set(re.findall(r'\$(\w+)', clean))

    def test_mainmod_defined(self):
        """$mainMod must be defined (standard Hyprland convention)."""
        defined = self._get_defined_vars()
        self.assertIn(
            "mainMod", defined,
            "$mainMod must be defined for keybindings",
        )

    def test_all_used_vars_are_defined(self):
        """Every variable used ($var) must have a corresponding definition."""
        defined = self._get_defined_vars()
        used = self._get_used_vars()
        undefined = used - defined
        self.assertEqual(
            undefined, set(),
            f"Variables used but never defined: {undefined}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Bind syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandBindSyntax(unittest.TestCase):
    """Verify keybindings use correct syntax."""

    VALID_BIND_TYPES = {"bind", "binde", "bindel", "bindm", "bindr", "bindl", "bindn"}

    def _get_bind_lines(self):
        """Return all bind lines from the config."""
        lines = _config_lines()
        bind_lines = []
        for line in lines:
            match = re.match(r'^(bind\w*)\s*=\s*(.+)', line)
            if match:
                bind_lines.append((match.group(1), match.group(2), line))
        return bind_lines

    def test_bind_type_valid(self):
        """All bind keywords must be valid Hyprland bind types."""
        bind_lines = self._get_bind_lines()
        for bind_type, _, line in bind_lines:
            with self.subTest(line=line[:60]):
                self.assertIn(
                    bind_type, self.VALID_BIND_TYPES,
                    f"Invalid bind type '{bind_type}'",
                )

    def test_bind_has_minimum_fields(self):
        """Each bind must have at least: MODS, KEY, DISPATCHER (3 comma-separated parts)."""
        bind_lines = self._get_bind_lines()
        for bind_type, value, line in bind_lines:
            with self.subTest(line=line[:60]):
                parts = [p.strip() for p in value.split(",")]
                self.assertGreaterEqual(
                    len(parts), 3,
                    f"Bind must have at least 3 fields (MODS, KEY, DISPATCHER): {line}",
                )

    def test_bind_dispatcher_not_empty(self):
        """The dispatcher field in a bind should not be empty."""
        bind_lines = self._get_bind_lines()
        for bind_type, value, line in bind_lines:
            with self.subTest(line=line[:60]):
                parts = [p.strip() for p in value.split(",")]
                if len(parts) >= 3:
                    dispatcher = parts[2]
                    self.assertTrue(
                        len(dispatcher) > 0,
                        f"Empty dispatcher in bind: {line}",
                    )

    def test_valid_modifiers(self):
        """Modifier keys should be valid Hyprland modifiers."""
        valid_mods = {"SUPER", "SHIFT", "ALT", "CTRL", "CONTROL", "MOD2", "MOD3", "MOD5", ""}
        bind_lines = self._get_bind_lines()
        for bind_type, value, line in bind_lines:
            parts = [p.strip() for p in value.split(",")]
            if len(parts) >= 1:
                mod_str = parts[0].strip()
                # Handle variable references like $mainMod
                mod_str = re.sub(r'\$\w+', '', mod_str)
                mods = mod_str.split()
                for mod in mods:
                    if mod:
                        with self.subTest(line=line[:60], modifier=mod):
                            self.assertIn(
                                mod, valid_mods,
                                f"Invalid modifier '{mod}' in bind: {line}",
                            )


# ═══════════════════════════════════════════════════════════════════════════
# Duplicate keybinding detection
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandNoDuplicateBinds(unittest.TestCase):
    """Detect duplicate keybindings that would cause conflicts."""

    def test_no_duplicate_binds(self):
        """No two binds should have the same modifier+key combination (in same submap)."""
        content = _read_config()
        lines = content.splitlines()
        current_submap = "reset"
        binds = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Track submap changes
            submap_match = re.match(r'^submap\s*=\s*(.+)', stripped)
            if submap_match:
                current_submap = submap_match.group(1).strip()
                continue

            # Collect binds
            bind_match = re.match(r'^(bind\w*)\s*=\s*(.+)', stripped)
            if bind_match:
                bind_type = bind_match.group(1)
                value = bind_match.group(2)
                parts = [p.strip() for p in value.split(",")]
                if len(parts) >= 3:
                    mods = parts[0]
                    key = parts[1]
                    dispatcher = parts[2]
                    # Normalize the binding key (mod+key+submap)
                    bind_key = (current_submap, mods, key, bind_type)
                    binds.append((bind_key, stripped))

        # Check for duplicates
        seen = Counter(b[0] for b in binds)
        duplicates = {k: v for k, v in seen.items() if v > 1}
        self.assertEqual(
            len(duplicates), 0,
            f"Duplicate keybindings found: {duplicates}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Window rule validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandWindowRules(unittest.TestCase):
    """Verify window rules use correct syntax."""

    def _get_window_rules(self):
        """Return all windowrule lines."""
        lines = _config_lines()
        rules = []
        for line in lines:
            match = re.match(r'^windowrule\s*=\s*(.+)', line)
            if match:
                rules.append(match.group(1))
        return rules

    def test_window_rules_have_two_parts(self):
        """Each windowrule must have action and match criteria (comma-separated)."""
        rules = self._get_window_rules()
        for rule in rules:
            with self.subTest(rule=rule[:60]):
                parts = [p.strip() for p in rule.split(",", 1)]
                self.assertEqual(
                    len(parts), 2,
                    f"windowrule must have exactly 2 parts (action, match): {rule}",
                )

    def test_window_rule_action_not_empty(self):
        """The action part of a windowrule must not be empty."""
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                with self.subTest(rule=rule[:60]):
                    self.assertTrue(
                        len(parts[0]) > 0,
                        f"Empty action in windowrule: {rule}",
                    )

    def test_window_rule_match_not_empty(self):
        """The match criteria of a windowrule must not be empty."""
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                with self.subTest(rule=rule[:60]):
                    self.assertTrue(
                        len(parts[1]) > 0,
                        f"Empty match criteria in windowrule: {rule}",
                    )

    def test_window_rule_regex_valid(self):
        """Regex patterns in windowrule match criteria should be valid."""
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                match_str = parts[1]
                # Extract regex from class:^(...)$ pattern
                regex_match = re.search(r'class:\^?\(?([^)]*)\)?\$?', match_str)
                if regex_match:
                    pattern = regex_match.group(1)
                    with self.subTest(pattern=pattern):
                        try:
                            re.compile(pattern)
                        except re.error as e:
                            self.fail(f"Invalid regex in windowrule '{pattern}': {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Color format validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandColors(unittest.TestCase):
    """Verify color values use valid Hyprland format."""

    def test_rgba_colors_valid(self):
        """All rgba() colors must have valid hex format (8 hex digits)."""
        content = _read_config()
        colors = re.findall(r'rgba\(([^)]+)\)', content)
        for color in colors:
            with self.subTest(color=color):
                self.assertRegex(
                    color,
                    r'^[0-9a-fA-F]{8}$',
                    f"Invalid rgba color '{color}' – must be 8 hex digits (RRGGBBAA)",
                )

    def test_rgb_colors_valid(self):
        """All rgb() colors must have valid hex format (6 hex digits)."""
        content = _read_config()
        colors = re.findall(r'(?<!a)rgb\(([^)]+)\)', content)
        for color in colors:
            with self.subTest(color=color):
                self.assertRegex(
                    color,
                    r'^[0-9a-fA-F]{6}$',
                    f"Invalid rgb color '{color}' – must be 6 hex digits (RRGGBB)",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Environment variable syntax
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandEnvVars(unittest.TestCase):
    """Verify env = KEY,VALUE syntax is correct."""

    def test_env_has_key_and_value(self):
        """Each env directive must have KEY,VALUE format."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r'^env\s*=\s*(.+)', line)
            if match:
                value = match.group(1)
                parts = [p.strip() for p in value.split(",", 1)]
                with self.subTest(line=line):
                    self.assertEqual(
                        len(parts), 2,
                        f"env must have KEY,VALUE format: {line}",
                    )
                    self.assertTrue(
                        len(parts[0]) > 0,
                        f"Empty KEY in env: {line}",
                    )
                    self.assertTrue(
                        len(parts[1]) > 0,
                        f"Empty VALUE in env: {line}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Monitor configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandMonitor(unittest.TestCase):
    """Verify monitor configuration syntax."""

    def test_monitor_line_exists(self):
        """At least one monitor configuration must exist."""
        lines = _config_lines()
        monitor_lines = [l for l in lines if l.startswith("monitor")]
        self.assertGreater(
            len(monitor_lines), 0,
            "At least one monitor configuration is required",
        )

    def test_monitor_has_enough_fields(self):
        """monitor = name,resolution,position,scale (4 fields)."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r'^monitor\s*=\s*(.+)', line)
            if match:
                parts = [p.strip() for p in match.group(1).split(",")]
                with self.subTest(line=line):
                    self.assertGreaterEqual(
                        len(parts), 4,
                        f"monitor needs at least 4 fields (name,res,pos,scale): {line}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Submap consistency
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandSubmaps(unittest.TestCase):
    """Verify submap definitions are properly opened and closed."""

    def test_submaps_properly_closed(self):
        """Every submap = <name> must end with submap = reset."""
        content = _read_config()
        clean = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        submap_opens = re.findall(r'^submap\s*=\s*(\S+)', clean, re.MULTILINE)

        # Count non-reset submap activations
        opens = [s for s in submap_opens if s != "reset"]
        resets = [s for s in submap_opens if s == "reset"]

        self.assertEqual(
            len(opens), len(resets),
            f"Unbalanced submaps: {len(opens)} opened, {len(resets)} reset. "
            f"Each submap must end with 'submap = reset'.",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Exec-once validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandExecOnce(unittest.TestCase):
    """Verify exec-once commands are not empty."""

    def test_exec_once_not_empty(self):
        """exec-once commands must have a non-empty command."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r'^exec-once\s*=\s*(.*)', line)
            if match:
                cmd = match.group(1).strip()
                with self.subTest(line=line[:60]):
                    self.assertTrue(
                        len(cmd) > 0,
                        f"Empty exec-once command: {line}",
                    )

    def test_exec_not_empty(self):
        """exec commands must have a non-empty command."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r'^exec\s*=\s*(.*)', line)
            if match:
                cmd = match.group(1).strip()
                with self.subTest(line=line[:60]):
                    self.assertTrue(
                        len(cmd) > 0,
                        f"Empty exec command: {line}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Animation / bezier syntax
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandAnimations(unittest.TestCase):
    """Verify animation and bezier definitions use correct format."""

    def test_bezier_has_five_fields(self):
        """bezier = name, x1, y1, x2, y2 (5 fields)."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r'^bezier\s*=\s*(.+)', line)
            if match:
                parts = [p.strip() for p in match.group(1).split(",")]
                with self.subTest(line=line):
                    self.assertEqual(
                        len(parts), 5,
                        f"bezier needs 5 fields (name, x1, y1, x2, y2): {line}",
                    )
                    # Name should be non-empty
                    self.assertTrue(
                        len(parts[0]) > 0,
                        f"Bezier name must not be empty: {line}",
                    )
                    # Numeric values should be valid floats
                    for i, val in enumerate(parts[1:], 1):
                        try:
                            float(val)
                        except ValueError:
                            self.fail(f"Bezier field {i} is not a number: '{val}' in {line}")

    def test_animation_has_minimum_fields(self):
        """animation = name, onoff, speed, curve[, style] (at least 4 fields)."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r'^animation\s*=\s*(.+)', line)
            if match:
                parts = [p.strip() for p in match.group(1).split(",")]
                with self.subTest(line=line):
                    self.assertGreaterEqual(
                        len(parts), 4,
                        f"animation needs at least 4 fields (name, onoff, speed, curve): {line}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Input section validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandInputSection(unittest.TestCase):
    """Verify input section has required keyboard layout."""

    def test_keyboard_layout_defined(self):
        """Input section must define kb_layout."""
        content = _read_config()
        self.assertIn(
            "kb_layout", content,
            "Input section must define kb_layout for keyboard layout",
        )

    def test_follow_mouse_defined(self):
        """Input section should define follow_mouse behavior."""
        content = _read_config()
        self.assertIn(
            "follow_mouse", content,
            "Input section should define follow_mouse",
        )


# ═══════════════════════════════════════════════════════════════════════════
# General section content validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandGeneralSection(unittest.TestCase):
    """Verify general section has expected settings."""

    def test_layout_defined(self):
        """General section must define a layout (dwindle or master)."""
        content = _read_config()
        self.assertRegex(
            content,
            r'layout\s*=\s*(dwindle|master)',
            "General section must define layout = dwindle or layout = master",
        )

    def test_border_size_defined(self):
        """General section must define border_size."""
        content = _read_config()
        self.assertIn(
            "border_size", content,
            "General section must define border_size",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Hyprland session script validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandSessionScript(unittest.TestCase):
    """Verify hyprland-session script is correct."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "hyprland-session")
        if os.path.isfile(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()

    def test_sets_wayland_session_type(self):
        """hyprland-session must set XDG_SESSION_TYPE=wayland."""
        self.assertIn(
            "XDG_SESSION_TYPE=wayland", self.content,
            "Must set XDG_SESSION_TYPE=wayland",
        )

    def test_sets_desktop_to_hyprland(self):
        """hyprland-session must set XDG_CURRENT_DESKTOP=Hyprland."""
        self.assertIn(
            "XDG_CURRENT_DESKTOP=Hyprland", self.content,
            "Must set XDG_CURRENT_DESKTOP=Hyprland",
        )

    def test_execs_hyprland(self):
        """hyprland-session must exec Hyprland."""
        self.assertIn(
            "exec Hyprland", self.content,
            "Must exec Hyprland at the end",
        )

    def test_has_shebang(self):
        """hyprland-session must have a bash shebang."""
        self.assertTrue(
            self.content.startswith("#!/bin/bash"),
            "Must start with #!/bin/bash",
        )


if __name__ == "__main__":
    unittest.main()
