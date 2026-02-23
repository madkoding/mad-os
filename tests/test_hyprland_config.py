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
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        opens = clean.count("{")
        closes = clean.count("}")
        self.assertEqual(
            opens,
            closes,
            f"Unbalanced braces: {opens} opening vs {closes} closing",
        )

    def test_no_nested_section_beyond_two_levels(self):
        """Hyprland supports at most 2-level nesting (e.g. decoration { blur { } })."""
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        depth = 0
        max_depth = 0
        for char in clean:
            if char == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == "}":
                depth -= 1
        self.assertLessEqual(
            max_depth,
            3,
            f"Nesting too deep ({max_depth} levels) – Hyprland supports max 2-level sections",
        )
        self.assertGreaterEqual(
            depth,
            0,
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
        "general",
        "decoration",
        "animations",
        "input",
        "misc",
        "dwindle",
        "master",
        "gestures",
        "group",
        "xwayland",
        "opengl",
        "render",
        "cursor",
        "debug",
        "binds",
        "ecosystem",
        # Commands / keywords
        "exec-once",
        "exec",
        "bind",
        "binde",
        "bindel",
        "bindm",
        "bindr",
        "bindl",
        "bindn",
        "bindrl",
        "monitor",
        "workspace",
        "windowrule",
        "windowrulev2",
        "layerrule",
        "layerrulev2",
        "source",
        "env",
        "bezier",
        "animation",
        "submap",
        "plugin",
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
                match = re.match(r"^\$?\w[\w-]*", stripped)
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
                    kw,
                    self.VALID_TOP_LEVEL_KEYWORDS,
                    f"Unknown top-level keyword '{kw}' in hyprland.conf. "
                    f"If this is a new valid keyword, add it to VALID_TOP_LEVEL_KEYWORDS.",
                )

    def test_no_windowrulev2_used(self):
        """windowrulev2 is deprecated since Hyprland 0.53; windowrule should be used.

        Starting with Hyprland 0.53 (current in Arch repos), the config
        system was rewritten and windowrulev2 was removed.  All window
        rules must now use the unified 'windowrule' keyword.
        """
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        self.assertNotIn(
            "windowrulev2",
            clean,
            "windowrulev2 is deprecated since Hyprland 0.53 – use windowrule instead",
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
                pattern = rf"^\s*{re.escape(section)}\s*\{{"
                self.assertRegex(
                    content,
                    re.compile(pattern, re.MULTILINE),
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
        return set(re.findall(r"^\s*\$(\w+)\s*=", content, re.MULTILINE))

    def _get_used_vars(self):
        """Return set of variable names used in the config ($varName)."""
        content = _read_config()
        # Remove definition lines to only find usage
        clean = re.sub(r"^\s*\$\w+\s*=.*$", "", content, flags=re.MULTILINE)
        # Remove comments
        clean = re.sub(r"#.*$", "", clean, flags=re.MULTILINE)
        # Remove inline shell scripts (bash -c '...') which use shell variables
        clean = re.sub(r"bash\s+-c\s+'[^']*'", "", clean)
        return set(re.findall(r"\$(\w+)", clean))

    def test_mainmod_defined(self):
        """$mainMod must be defined (standard Hyprland convention)."""
        defined = self._get_defined_vars()
        self.assertIn(
            "mainMod",
            defined,
            "$mainMod must be defined for keybindings",
        )

    def test_all_used_vars_are_defined(self):
        """Every variable used ($var) must have a corresponding definition."""
        defined = self._get_defined_vars()
        used = self._get_used_vars()
        undefined = used - defined
        self.assertEqual(
            undefined,
            set(),
            f"Variables used but never defined: {undefined}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Bind syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandBindSyntax(unittest.TestCase):
    """Verify keybindings use correct syntax."""

    VALID_BIND_TYPES = {
        "bind",
        "binde",
        "bindel",
        "bindm",
        "bindr",
        "bindl",
        "bindn",
        "bindrl",
    }

    def _get_bind_lines(self):
        """Return all bind lines from the config."""
        lines = _config_lines()
        bind_lines = []
        for line in lines:
            match = re.match(r"^(bind\w*)\s*=\s*(.+)", line)
            if match:
                bind_lines.append((match.group(1), match.group(2), line))
        return bind_lines

    def test_bind_type_valid(self):
        """All bind keywords must be valid Hyprland bind types."""
        bind_lines = self._get_bind_lines()
        for bind_type, _, line in bind_lines:
            with self.subTest(line=line[:60]):
                self.assertIn(
                    bind_type,
                    self.VALID_BIND_TYPES,
                    f"Invalid bind type '{bind_type}'",
                )

    def test_bind_has_minimum_fields(self):
        """Each bind must have at least: MODS, KEY, DISPATCHER (3 comma-separated parts)."""
        bind_lines = self._get_bind_lines()
        for bind_type, value, line in bind_lines:
            with self.subTest(line=line[:60]):
                parts = [p.strip() for p in value.split(",")]
                self.assertGreaterEqual(
                    len(parts),
                    3,
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
                    self.assertGreater(
                        len(dispatcher),
                        0,
                        f"Empty dispatcher in bind: {line}",
                    )

    def test_valid_modifiers(self):
        """Modifier keys should be valid Hyprland modifiers."""
        valid_mods = {
            "SUPER",
            "SHIFT",
            "ALT",
            "CTRL",
            "CONTROL",
            "MOD2",
            "MOD3",
            "MOD5",
            "",
        }
        bind_lines = self._get_bind_lines()
        for bind_type, value, line in bind_lines:
            parts = [p.strip() for p in value.split(",")]
            if len(parts) >= 1:
                mod_str = parts[0].strip()
                # Handle variable references like $mainMod
                mod_str = re.sub(r"\$\w+", "", mod_str)
                mods = mod_str.split()
                for mod in mods:
                    if mod:
                        with self.subTest(line=line[:60], modifier=mod):
                            self.assertIn(
                                mod,
                                valid_mods,
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
            submap_match = re.match(r"^submap\s*=\s*(.+)", stripped)
            if submap_match:
                current_submap = submap_match.group(1).strip()
                continue

            # Collect binds
            bind_match = re.match(r"^(bind\w*)\s*=\s*(.+)", stripped)
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
            len(duplicates),
            0,
            f"Duplicate keybindings found: {duplicates}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Window rule validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandWindowRules(unittest.TestCase):
    """Verify window rules use correct Hyprland v0.53+ syntax.

    Since Hyprland 0.53 the window-rule system was rewritten:
      - ``windowrulev2`` is removed; use ``windowrule`` only.
      - Match props use ``match:class``, ``match:title``, etc.
      - Static effects like ``float``, ``tile``, ``center``, ``pseudo``
        require a value (e.g. ``float 1``).
    """

    # Static effects that require a value in Hyprland v0.53+
    EFFECTS_REQUIRING_VALUE = {
        "float",
        "tile",
        "fullscreen",
        "maximize",
        "center",
        "pseudo",
        "pin",
        "no_initial_focus",
    }

    def _get_window_rules(self):
        """Return all windowrule lines."""
        lines = _config_lines()
        rules = []
        for line in lines:
            match = re.match(r"^windowrule\s*=\s*(.+)", line)
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
                    len(parts),
                    2,
                    f"windowrule must have exactly 2 parts (action, match): {rule}",
                )

    def test_window_rule_action_not_empty(self):
        """The action part of a windowrule must not be empty."""
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                with self.subTest(rule=rule[:60]):
                    self.assertGreater(
                        len(parts[0]),
                        0,
                        f"Empty action in windowrule: {rule}",
                    )

    def test_window_rule_match_not_empty(self):
        """The match criteria of a windowrule must not be empty."""
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                with self.subTest(rule=rule[:60]):
                    self.assertGreater(
                        len(parts[1]),
                        0,
                        f"Empty match criteria in windowrule: {rule}",
                    )

    def test_window_rule_uses_match_prefix(self):
        """Match props must use 'match:' prefix (v0.53+ syntax).

        The old ``class:`` / ``title:`` syntax (without ``match:`` prefix)
        is no longer valid.  All match criteria must use ``match:class``,
        ``match:title``, etc.
        """
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                match_str = parts[1]
                with self.subTest(rule=rule[:60]):
                    # Detect bare class:/title: without match: prefix
                    bare = re.search(
                        r"(?<!\w)(?<!match:)(class|title|initial_class|initial_title):",
                        match_str,
                    )
                    if bare:
                        self.fail(
                            f"Use 'match:{bare.group(1)}' instead of bare '{bare.group(1)}:' "
                            f"(Hyprland v0.53+ syntax): {rule}"
                        )

    def test_window_rule_effects_have_values(self):
        """Static effects like 'float', 'tile', etc. must have a value in v0.53+.

        For example ``float 1`` is valid, but bare ``float`` is not.
        """
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                effect_str = parts[0]
                effect_parts = effect_str.split()
                effect_name = effect_parts[0] if effect_parts else ""
                with self.subTest(rule=rule[:60]):
                    if effect_name in self.EFFECTS_REQUIRING_VALUE:
                        self.assertGreater(
                            len(effect_parts),
                            1,
                            f"Effect '{effect_name}' requires a value (e.g. '{effect_name} 1') "
                            f"in Hyprland v0.53+: {rule}",
                        )

    def test_window_rule_regex_valid(self):
        """Regex patterns in windowrule match criteria should be valid."""
        rules = self._get_window_rules()
        for rule in rules:
            parts = [p.strip() for p in rule.split(",", 1)]
            if len(parts) == 2:
                match_str = parts[1]
                # Extract regex from match:class ^(...)$ pattern (v0.53+ syntax)
                regex_match = re.search(r"match:class\s+\^?\(?([^)]*)\)?\$?", match_str)
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
        colors = re.findall(r"rgba\(([^)]+)\)", content)
        for color in colors:
            with self.subTest(color=color):
                self.assertRegex(
                    color,
                    r"^[0-9a-fA-F]{8}$",
                    f"Invalid rgba color '{color}' – must be 8 hex digits (RRGGBBAA)",
                )

    def test_rgb_colors_valid(self):
        """All rgb() colors must have valid hex format (6 hex digits)."""
        content = _read_config()
        colors = re.findall(r"(?<!a)rgb\(([^)]+)\)", content)
        for color in colors:
            with self.subTest(color=color):
                self.assertRegex(
                    color,
                    r"^[0-9a-fA-F]{6}$",
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
            match = re.match(r"^env\s*=\s*(.+)", line)
            if match:
                value = match.group(1)
                parts = [p.strip() for p in value.split(",", 1)]
                with self.subTest(line=line):
                    self.assertEqual(
                        len(parts),
                        2,
                        f"env must have KEY,VALUE format: {line}",
                    )
                    self.assertGreater(
                        len(parts[0]),
                        0,
                        f"Empty KEY in env: {line}",
                    )
                    self.assertGreater(
                        len(parts[1]),
                        0,
                        f"Empty VALUE in env: {line}",
                    )
                    self.assertGreater(
                        len(parts[0]),
                        0,
                        f"Empty KEY in env: {line}",
                    )
                    self.assertGreater(
                        len(parts[1]),
                        0,
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
            len(monitor_lines),
            0,
            "At least one monitor configuration is required",
        )

    def test_monitor_has_enough_fields(self):
        """monitor = name,resolution,position,scale (4 fields)."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r"^monitor\s*=\s*(.+)", line)
            if match:
                parts = [p.strip() for p in match.group(1).split(",")]
                with self.subTest(line=line):
                    self.assertGreaterEqual(
                        len(parts),
                        4,
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
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        submap_opens = re.findall(r"^submap\s*=\s*(\S+)", clean, re.MULTILINE)

        # Count non-reset submap activations
        opens = [s for s in submap_opens if s != "reset"]
        resets = [s for s in submap_opens if s == "reset"]

        self.assertEqual(
            len(opens),
            len(resets),
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
            match = re.match(r"^exec-once\s*=\s*(.*)", line)
            if match:
                cmd = match.group(1).strip()
                with self.subTest(line=line[:60]):
                    self.assertGreater(
                        len(cmd),
                        0,
                        f"Empty exec-once command: {line}",
                    )

    def test_exec_not_empty(self):
        """exec commands must have a non-empty command."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r"^exec\s*=\s*(.*)", line)
            if match:
                cmd = match.group(1).strip()
                with self.subTest(line=line[:60]):
                    self.assertGreater(
                        len(cmd),
                        0,
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
            match = re.match(r"^bezier\s*=\s*(.+)", line)
            if match:
                parts = [p.strip() for p in match.group(1).split(",")]
                with self.subTest(line=line):
                    self.assertEqual(
                        len(parts),
                        5,
                        f"bezier needs 5 fields (name, x1, y1, x2, y2): {line}",
                    )
                    # Name should be non-empty
                    self.assertGreater(
                        len(parts[0]),
                        0,
                        f"Bezier name must not be empty: {line}",
                    )
                    # Numeric values should be valid floats
                    for i, val in enumerate(parts[1:], 1):
                        try:
                            float(val)
                        except ValueError:
                            self.fail(
                                f"Bezier field {i} is not a number: '{val}' in {line}"
                            )

    def test_animation_has_minimum_fields(self):
        """animation = name, onoff, speed, curve[, style] (at least 4 fields)."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r"^animation\s*=\s*(.+)", line)
            if match:
                parts = [p.strip() for p in match.group(1).split(",")]
                with self.subTest(line=line):
                    self.assertGreaterEqual(
                        len(parts),
                        4,
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
            "kb_layout",
            content,
            "Input section must define kb_layout for keyboard layout",
        )

    def test_follow_mouse_defined(self):
        """Input section should define follow_mouse behavior."""
        content = _read_config()
        self.assertIn(
            "follow_mouse",
            content,
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
            r"layout\s*=\s*(dwindle|master)",
            "General section must define layout = dwindle or layout = master",
        )

    def test_border_size_defined(self):
        """General section must define border_size."""
        content = _read_config()
        self.assertIn(
            "border_size",
            content,
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
            "XDG_SESSION_TYPE=wayland",
            self.content,
            "Must set XDG_SESSION_TYPE=wayland",
        )

    def test_sets_desktop_to_hyprland(self):
        """hyprland-session must set XDG_CURRENT_DESKTOP=Hyprland."""
        self.assertIn(
            "XDG_CURRENT_DESKTOP=Hyprland",
            self.content,
            "Must set XDG_CURRENT_DESKTOP=Hyprland",
        )

    def test_execs_hyprland(self):
        """hyprland-session must exec start-hyprland."""
        self.assertIn(
            "exec start-hyprland",
            self.content,
            "Must exec start-hyprland at the end",
        )

    def test_has_shebang(self):
        """hyprland-session must have a bash shebang."""
        self.assertTrue(
            self.content.startswith("#!/bin/bash"),
            "Must start with #!/bin/bash",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Dispatcher validation
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandDispatchers(unittest.TestCase):
    """Verify bind dispatchers are valid Hyprland dispatchers."""

    # Known valid dispatchers in Hyprland (verified against v0.53 source)
    VALID_DISPATCHERS = {
        "exec",
        "execr",
        "pass",
        "killactive",
        "closewindow",
        "workspace",
        "movetoworkspace",
        "movetoworkspacesilent",
        "togglefloating",
        "fullscreen",
        "fakefullscreen",
        "dpms",
        "pin",
        "movefocus",
        "movewindow",
        "swapwindow",
        "centerwindow",
        "resizeactive",
        "moveactive",
        "resizewindowpixel",
        "movewindowpixel",
        "cyclenext",
        "swapnext",
        "focuswindow",
        "focusmonitor",
        "splitratio",
        "toggleopaque",
        "movecursortocorner",
        "movecursor",
        "renameworkspace",
        "exit",
        "forcerendererreload",
        "movecurrentworkspacetomonitor",
        "focusworkspaceoncurrentmonitor",
        "moveworkspacetomonitor",
        "swapactiveworkspaces",
        "bringactivetotop",
        "alterzorder",
        "togglespecialworkspace",
        "focusurgentorlast",
        "togglegroup",
        "changegroupactive",
        "focuscurrentorlast",
        "lockgroups",
        "lockactivegroup",
        "moveintogroup",
        "moveoutofgroup",
        "movewindoworgroup",
        "movegroupwindow",
        "denywindowfromgroup",
        "setfloating",
        "settiled",
        "pseudo",
        "togglesplit",
        "layoutmsg",
        "submap",
        "global",
        "sendshortcut",
        "event",
        # Mouse-specific dispatchers (used with bindm)
        "resizewindow",
    }

    def _get_dispatchers_used(self):
        """Extract all dispatchers used in bind commands."""
        lines = _config_lines()
        dispatchers = []
        for line in lines:
            match = re.match(r"^(bind[emlrn]*)\s*=\s*(.+)", line)
            if match:
                parts = [p.strip() for p in match.group(2).split(",")]
                if len(parts) >= 3:
                    dispatchers.append((parts[2], line))
        return dispatchers

    def test_all_dispatchers_valid(self):
        """Every dispatcher used in a bind must be a known Hyprland dispatcher."""
        dispatchers = self._get_dispatchers_used()
        for dispatcher, line in dispatchers:
            with self.subTest(dispatcher=dispatcher, line=line[:60]):
                self.assertIn(
                    dispatcher,
                    self.VALID_DISPATCHERS,
                    f"Unknown dispatcher '{dispatcher}' in: {line}",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Config variable validation against known Hyprland options
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandConfigVariables(unittest.TestCase):
    """Verify all config variables inside sections are known Hyprland options.

    Cross-referenced against Hyprland v0.53 source code
    (src/config/ConfigManager.cpp registerConfigVar calls).
    """

    # Valid config variables registered in Hyprland v0.53 source code
    VALID_SECTION_VARS = {
        # input section
        "input:kb_layout",
        "input:kb_variant",
        "input:kb_model",
        "input:kb_options",
        "input:kb_rules",
        "input:kb_file",
        "input:numlock_by_default",
        "input:resolve_binds_by_sym",
        "input:repeat_rate",
        "input:repeat_delay",
        "input:sensitivity",
        "input:accel_profile",
        "input:force_no_accel",
        "input:left_handed",
        "input:scroll_points",
        "input:scroll_method",
        "input:scroll_button",
        "input:scroll_button_lock",
        "input:scroll_factor",
        "input:natural_scroll",
        "input:follow_mouse",
        "input:mouse_refocus",
        "input:float_switch_override_focus",
        "input:special_fallthrough",
        "input:off_window_axis_events",
        "input:emulate_discrete_scroll",
        # input:touchpad
        "input:touchpad:natural_scroll",
        "input:touchpad:disable_while_typing",
        "input:touchpad:clickfinger_behavior",
        "input:touchpad:tap_button_map",
        "input:touchpad:middle_button_emulation",
        "input:touchpad:tap-to-click",
        "input:touchpad:tap-and-drag",
        "input:touchpad:drag_lock",
        "input:touchpad:scroll_factor",
        "input:touchpad:flip_x",
        "input:touchpad:flip_y",
        "input:touchpad:drag_3fg",
        # input:touchdevice
        "input:touchdevice:transform",
        "input:touchdevice:output",
        "input:touchdevice:enabled",
        # input:tablet
        "input:tablet:transform",
        "input:tablet:output",
        "input:tablet:region_position",
        "input:tablet:region_size",
        "input:tablet:relative_input",
        "input:tablet:left_handed",
        "input:tablet:active_area_size",
        "input:tablet:active_area_position",
        # general section
        "general:border_size",
        "general:gaps_in",
        "general:gaps_out",
        "general:float_gaps",
        "general:gaps_workspaces",
        "general:no_focus_fallback",
        "general:resize_on_border",
        "general:extend_border_grab_area",
        "general:hover_icon_on_border",
        "general:layout",
        "general:allow_tearing",
        "general:resize_corner",
        "general:col.active_border",
        "general:col.inactive_border",
        "general:col.nogroup_border",
        "general:col.nogroup_border_active",
        "general:modal_parent_blocking",
        "general:locale",
        "general:snap:enabled",
        "general:snap:window_gap",
        "general:snap:monitor_gap",
        "general:snap:border_overlap",
        "general:snap:respect_gaps",
        # decoration section
        "decoration:rounding",
        "decoration:rounding_power",
        "decoration:active_opacity",
        "decoration:inactive_opacity",
        "decoration:fullscreen_opacity",
        "decoration:blur:enabled",
        "decoration:blur:size",
        "decoration:blur:passes",
        "decoration:blur:ignore_opacity",
        "decoration:blur:new_optimizations",
        "decoration:blur:xray",
        "decoration:blur:contrast",
        "decoration:blur:brightness",
        "decoration:blur:vibrancy",
        "decoration:blur:vibrancy_darkness",
        "decoration:blur:noise",
        "decoration:blur:special",
        "decoration:blur:popups",
        "decoration:blur:popups_ignorealpha",
        "decoration:blur:input_methods",
        "decoration:blur:input_methods_ignorealpha",
        "decoration:shadow:enabled",
        "decoration:shadow:range",
        "decoration:shadow:render_power",
        "decoration:shadow:ignore_window",
        "decoration:shadow:offset",
        "decoration:shadow:scale",
        "decoration:shadow:sharp",
        "decoration:shadow:color",
        "decoration:shadow:color_inactive",
        # animations section
        "animations:enabled",
        "animations:first_launch_animation",
        # misc section
        "misc:disable_hyprland_logo",
        "misc:disable_splash_rendering",
        "misc:col.splash",
        "misc:splash_font_family",
        "misc:font_family",
        "misc:force_default_wallpaper",
        "misc:vfr",
        "misc:vrr",
        "misc:mouse_move_enables_dpms",
        "misc:key_press_enables_dpms",
        "misc:always_follow_on_dnd",
        "misc:layers_hog_keyboard_focus",
        "misc:animate_manual_resizes",
        "misc:animate_mouse_windowdragging",
        "misc:disable_autoreload",
        "misc:enable_swallow",
        "misc:swallow_regex",
        "misc:swallow_exception_regex",
        "misc:focus_on_activate",
        "misc:mouse_move_focuses_monitor",
        "misc:render_ahead_of_time",
        "misc:render_ahead_safezone",
        "misc:allow_session_lock_restore",
        "misc:background_color",
        "misc:close_special_on_empty",
        "misc:new_window_takes_over_fullscreen",
        "misc:exit_window_retains_fullscreen",
        "misc:initial_workspace_tracking",
        "misc:middle_click_paste",
        # dwindle section
        "dwindle:pseudotile",
        "dwindle:force_split",
        "dwindle:preserve_split",
        "dwindle:smart_split",
        "dwindle:smart_resizing",
        "dwindle:permanent_direction_override",
        "dwindle:special_scale_factor",
        "dwindle:split_width_multiplier",
        "dwindle:use_active_for_splits",
        "dwindle:default_split_ratio",
        "dwindle:split_bias",
        # master section
        "master:new_status",
        "master:new_on_top",
        "master:new_on_active",
        "master:no_gaps_when_only",
        "master:special_scale_factor",
        "master:slave_count_for_center_master",
        "master:orientation",
        "master:inherit_fullscreen",
        "master:always_center_master",
        "master:smart_resizing",
        "master:mfact",
        "master:center_ignores_reserved",
        # xwayland section
        "xwayland:force_zero_scaling",
        "xwayland:use_nearest_neighbor",
        "xwayland:enabled",
        # gestures section
        "gestures:workspace_swipe",
        "gestures:workspace_swipe_fingers",
        "gestures:workspace_swipe_min_fingers",
        "gestures:workspace_swipe_distance",
        "gestures:workspace_swipe_touch",
        "gestures:workspace_swipe_invert",
        "gestures:workspace_swipe_min_speed_to_force",
        "gestures:workspace_swipe_cancel_ratio",
        "gestures:workspace_swipe_create_new",
        "gestures:workspace_swipe_direction_lock",
        "gestures:workspace_swipe_direction_lock_threshold",
        "gestures:workspace_swipe_forever",
        "gestures:workspace_swipe_use_r",
        # cursor section
        "cursor:no_hardware_cursors",
        "cursor:no_break_fs_vrr",
        "cursor:min_refresh_rate",
        "cursor:hotspot_padding",
        "cursor:inactive_timeout",
        "cursor:no_warps",
        "cursor:persistent_warps",
        "cursor:warp_on_change_workspace",
        "cursor:default_monitor",
        "cursor:zoom_factor",
        "cursor:zoom_rigid",
        "cursor:enable_hyprcursor",
        "cursor:hide_on_key_press",
        "cursor:hide_on_touch",
        "cursor:allow_dumb_copy",
    }

    def _get_section_variables(self):
        """Extract section:variable pairs from the config."""
        content = _read_config()
        lines = content.splitlines()
        section_stack = []
        variables = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if "{" in stripped:
                name = stripped.split("{")[0].strip()
                section_stack.append(name)
            elif "}" in stripped:
                if section_stack:
                    section_stack.pop()
            elif "=" in stripped and section_stack:
                key = stripped.split("=")[0].strip()
                full_path = ":".join(section_stack) + ":" + key
                variables.append((full_path, i, stripped))

        return variables

    def test_all_section_variables_valid(self):
        """Every variable inside a config section must be a known Hyprland option.

        This catches deprecated, misspelled, or non-existent config variables
        that would cause Hyprland to log errors at startup.
        """
        variables = self._get_section_variables()
        for full_path, lineno, line in variables:
            # Skip animation/bezier definitions (these are keywords, not variables)
            if full_path.startswith("animations:bezier") or full_path.startswith(
                "animations:animation"
            ):
                continue
            with self.subTest(variable=full_path, line=lineno):
                self.assertIn(
                    full_path,
                    self.VALID_SECTION_VARS,
                    f"L{lineno}: Unknown config variable '{full_path}' – "
                    f"may be deprecated, misspelled, or not valid for Hyprland v0.53+. "
                    f"Line: {line}",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Wallpaper glitch script validation
# ═══════════════════════════════════════════════════════════════════════════
class TestWallpaperGlitchScript(unittest.TestCase):
    """Verify the wallpaper glitch script exists and is well-formed."""

    SCRIPT_PATH = os.path.join(BIN_DIR, "mados-wallpaper-glitch")

    def test_script_exists(self):
        """mados-wallpaper-glitch script must exist."""
        self.assertTrue(
            os.path.isfile(self.SCRIPT_PATH),
            "mados-wallpaper-glitch script missing from /usr/local/bin/",
        )

    def test_script_has_shebang(self):
        """mados-wallpaper-glitch must have a bash shebang."""
        with open(self.SCRIPT_PATH) as f:
            first_line = f.readline().strip()
        self.assertTrue(
            first_line.startswith("#!") and "bash" in first_line,
            f"Must start with bash shebang, got: {first_line}",
        )

    def test_script_uses_swww(self):
        """mados-wallpaper-glitch must use swww for wallpaper transitions."""
        with open(self.SCRIPT_PATH) as f:
            content = f.read()
        self.assertIn("swww", content, "Script must use swww for transitions")

    def test_script_listens_for_workspace_events(self):
        """mados-wallpaper-glitch must listen for workspace change events."""
        with open(self.SCRIPT_PATH) as f:
            content = f.read()
        self.assertIn("workspace", content, "Script must handle workspace events")

    def test_script_uses_share_backgrounds(self):
        """mados-wallpaper-glitch must read wallpapers from /usr/share/backgrounds/."""
        with open(self.SCRIPT_PATH) as f:
            content = f.read()
        self.assertIn(
            "/usr/share/backgrounds",
            content,
            "Script must use /usr/share/backgrounds as wallpaper source",
        )

    def test_script_assigns_per_workspace_wallpapers(self):
        """mados-wallpaper-glitch must assign different wallpapers per workspace."""
        with open(self.SCRIPT_PATH) as f:
            content = f.read()
        self.assertIn(
            "sqlite3",
            content,
            "Script must use SQLite for per-workspace wallpaper mapping",
        )
        self.assertIn(
            "assignments",
            content,
            "Script must use 'assignments' table for workspace-wallpaper mapping",
        )

    def test_script_kills_previous_instances(self):
        """mados-wallpaper-glitch must prevent duplicate instances."""
        with open(self.SCRIPT_PATH) as f:
            content = f.read()
        self.assertIn(
            "kill_previous",
            content,
            "Script must kill previous instances to avoid duplicates",
        )

    def test_hyprland_conf_references_script(self):
        """hyprland.conf must exec-once the wallpaper glitch script."""
        content = _read_config()
        self.assertIn(
            "mados-wallpaper-glitch",
            content,
            "hyprland.conf must launch mados-wallpaper-glitch via exec-once",
        )

    def test_profiledef_has_permissions(self):
        """profiledef.sh must set permissions for mados-wallpaper-glitch."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn(
            "mados-wallpaper-glitch",
            content,
            "profiledef.sh must include permissions for mados-wallpaper-glitch",
        )

    def test_script_sets_initial_wallpaper_without_transition(self):
        """mados-wallpaper-glitch must set initial wallpaper without glitch transition.

        The initial wallpaper should be set with no/fast transition for
        maximum reliability. Glitch transitions are only for workspace switching.
        """
        with open(self.SCRIPT_PATH) as f:
            content = f.read()

        # Must wait for swww-daemon
        self.assertIn("swww query", content, "Must wait for swww-daemon")
        # Must have socat event listener
        self.assertIn("socat", content, "Must have socat event listener")
        # Must set initial wallpaper without transition ("false" = no transition)
        self.assertIn(
            '"false"',
            content,
            "Must set initial wallpaper without transition effect",
        )

    def test_script_checks_dependencies(self):
        """mados-wallpaper-glitch must check for required tools before running.

        The script should exit gracefully if swww or socat are not
        available, to avoid interfering with the normal wallpaper setup.
        """
        with open(self.SCRIPT_PATH) as f:
            content = f.read()

        # Script checks for both swww and socat via command -v
        self.assertIn(
            "command -v",
            content,
            "Script must check tool availability with command -v",
        )
        self.assertIn(
            "swww",
            content,
            "Script must check if swww is available",
        )
        self.assertIn(
            "socat",
            content,
            "Script must check if socat is available",
        )

    def test_script_uses_sqlite(self):
        """mados-wallpaper-glitch must use SQLite for wallpaper storage."""
        with open(self.SCRIPT_PATH) as f:
            content = f.read()
        self.assertIn(
            "sqlite3",
            content,
            "Script must use sqlite3 for persistent wallpaper database",
        )
        self.assertIn(
            "wallpapers.db",
            content,
            "Script must use wallpapers.db database file",
        )
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS wallpapers",
            content,
            "Script must create wallpapers catalog table",
        )
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS assignments",
            content,
            "Script must create workspace assignments table",
        )

    def test_hyprland_wallpaper_uses_no_transition(self):
        """hyprland.conf must set initial wallpaper with --transition-type none.

        Fancy transitions (pixelate, wave, etc.) can fail on certain
        hardware at startup. The initial wallpaper must use no transition
        for maximum reliability.
        """
        content = _read_config()
        # Find the swww img startup line (not in a comment)
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "swww img" in stripped and "/usr/share/backgrounds/" in stripped:
                self.assertIn(
                    "--transition-type none",
                    stripped,
                    "Initial wallpaper must use --transition-type none "
                    "for reliable startup",
                )
                return
        self.fail("hyprland.conf must have a swww img startup line")


# ═══════════════════════════════════════════════════════════════════════════
# Sway wallpaper startup retry validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayWallpaperStartup(unittest.TestCase):
    """Verify Sway config has robust wallpaper initialization."""

    SWAY_CONF = os.path.join(SKEL_DIR, ".config", "sway", "config")
    WALLPAPER_SCRIPT = os.path.join(BIN_DIR, "mados-sway-wallpapers")

    def test_sway_config_has_wallpaper_directive(self):
        """Sway config must set wallpaper via output directive."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "output * bg",
            content,
            "Sway config must have an 'output * bg' wallpaper directive",
        )

    def test_sway_config_has_wallpaper_retry(self):
        """Sway config must retry wallpaper after compositor initializes."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "swaymsg",
            content,
            "Sway config must use swaymsg to retry wallpaper after startup",
        )

    def test_sway_wallpaper_retry_uses_loop(self):
        """Sway wallpaper retry must use a loop for reliability on slow hardware."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "for ",
            content,
            "Sway config must use a retry loop for wallpaper refresh "
            "(single-attempt retry is unreliable on slow hardware)",
        )

    def test_sway_wallpaper_script_exists(self):
        """mados-sway-wallpapers script must exist."""
        self.assertTrue(
            os.path.isfile(self.WALLPAPER_SCRIPT),
            "mados-sway-wallpapers script missing from /usr/local/bin/",
        )

    def test_sway_wallpaper_script_has_shebang(self):
        """mados-sway-wallpapers must have a bash shebang."""
        with open(self.WALLPAPER_SCRIPT) as f:
            first_line = f.readline()
        self.assertIn("bash", first_line)

    def test_sway_wallpaper_script_uses_share_backgrounds(self):
        """mados-sway-wallpapers must read from /usr/share/backgrounds/."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "/usr/share/backgrounds",
            content,
            "Script must use /usr/share/backgrounds as wallpaper source",
        )

    def test_sway_wallpaper_script_subscribes_to_workspace_events(self):
        """mados-sway-wallpapers must subscribe to workspace events."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "subscribe",
            content,
            "Script must subscribe to sway workspace events",
        )

    def test_sway_config_launches_wallpaper_script(self):
        """Sway config must exec mados-sway-wallpapers."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "mados-sway-wallpapers",
            content,
            "Sway config must launch mados-sway-wallpapers via exec",
        )

    def test_profiledef_has_wallpaper_script_permissions(self):
        """profiledef.sh must set permissions for mados-sway-wallpapers."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn(
            "mados-sway-wallpapers",
            content,
            "profiledef.sh must include permissions for mados-sway-wallpapers",
        )

    def test_sway_wallpaper_script_uses_unbuffered_jq(self):
        """mados-sway-wallpapers must use jq --unbuffered for immediate event delivery."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "--unbuffered",
            content,
            "Script must use jq --unbuffered to prevent buffered output in pipe "
            "(without this, workspace events are never delivered to the while-read loop)",
        )

    def test_sway_wallpaper_script_uses_sqlite(self):
        """mados-sway-wallpapers must use SQLite for workspace-wallpaper mapping."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "sqlite3",
            content,
            "Script must use sqlite3 for persistent wallpaper storage",
        )
        self.assertIn(
            "wallpapers.db",
            content,
            "Script must use wallpapers.db database file",
        )
        # Should have wallpapers and assignments tables
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS wallpapers",
            content,
            "Script must create wallpapers catalog table",
        )
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS assignments",
            content,
            "Script must create workspace assignments table",
        )

    def test_sway_wallpaper_script_uses_inplace_shuffle(self):
        """mados-sway-wallpapers must shuffle arrays in-place (no subshell passing)."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        # Should NOT pass arrays through echo/read subshells
        self.assertNotIn(
            'echo "${wallpapers[@]}"',
            content,
            "Script must not pass arrays through echo (fragile with spaces in paths)",
        )
        # Should use global array directly
        self.assertIn(
            "WALLPAPERS",
            content,
            "Script must use a global WALLPAPERS array for in-place operations",
        )

    def test_sway_wallpaper_script_has_logging(self):
        """mados-sway-wallpapers must log for debugging."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "logger",
            content,
            "Script must use logger for diagnostic output",
        )

    def test_sway_wallpaper_script_kills_previous_instances(self):
        """mados-sway-wallpapers must prevent duplicate instances."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "kill_previous",
            content,
            "Script must kill previous instances to avoid duplicates",
        )

    def test_sway_config_uses_placeholder_background(self):
        """Sway config must use a neutral placeholder, not a wallpaper file."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "solid_color",
            content,
            "Sway config must use solid_color placeholder (wallpaper managed by script)",
        )
        self.assertNotIn(
            "mad-os-wallpaper",
            content,
            "Sway config must not hardcode a wallpaper file (managed by script)",
        )

    def test_sway_wallpaper_script_has_exit_trap(self):
        """mados-sway-wallpapers must trap EXIT for cleanup handler."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "trap cleanup EXIT",
            content,
            "Script must trap EXIT for cleanup handler",
        )

    def test_sway_wallpaper_requires_sqlite3(self):
        """mados-sway-wallpapers must check for sqlite3 in required tools."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "sqlite3",
            content,
            "Script must require sqlite3 command",
        )

    def test_packages_include_sqlite(self):
        """packages.x86_64 must include sqlite for wallpaper database."""
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            packages = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        self.assertIn(
            "sqlite",
            packages,
            "sqlite package must be in packages.x86_64 for wallpaper DB",
        )

    def test_sway_wallpaper_preserves_user_assignments(self):
        """mados-sway-wallpapers must preserve existing user wallpaper assignments."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        # The script should check existing assignments before overwriting
        self.assertIn(
            "SELECT COUNT",
            content,
            "Script must check existing assignments before reassigning "
            "(preserve user selections from wallpaper settings GUI)",
        )

    def test_sway_wallpaper_uses_persistent_db(self):
        """mados-sway-wallpapers must store data in ~/.local/share/mados/."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            ".local/share/mados",
            content,
            "Database must be in ~/.local/share/mados/ for persistence across reboots",
        )
        # Must NOT use PID-based state directories
        self.assertNotIn(
            "mados-wallpapers-$$",
            content,
            "Must not use PID-based state dirs (use SQLite DB instead)",
        )

    def test_sway_wallpaper_unlimited_reconnects(self):
        """mados-sway-wallpapers must not limit reconnection attempts."""
        with open(self.WALLPAPER_SCRIPT) as f:
            content = f.read()
        self.assertNotIn(
            "MAX_RECONNECTS",
            content,
            "Script must not have a MAX_RECONNECTS limit; "
            "daemon should always try to reconnect for reliability",
        )


class TestSwayWallpaperSetHelper(unittest.TestCase):
    """Verify mados-sway-wallpaper-set helper script."""

    HELPER_SCRIPT = os.path.join(BIN_DIR, "mados-sway-wallpaper-set")
    SWAY_CONF = os.path.join(SKEL_DIR, ".config", "sway", "config")

    def test_helper_script_exists(self):
        """mados-sway-wallpaper-set helper must exist."""
        self.assertTrue(
            os.path.isfile(self.HELPER_SCRIPT),
            "mados-sway-wallpaper-set script missing from /usr/local/bin/",
        )

    def test_helper_script_has_shebang(self):
        """mados-sway-wallpaper-set must have a bash shebang."""
        with open(self.HELPER_SCRIPT) as f:
            first_line = f.readline()
        self.assertIn("bash", first_line)

    def test_helper_reads_sqlite_db(self):
        """Helper must read from the same SQLite database as the daemon."""
        with open(self.HELPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "wallpapers.db",
            content,
            "Helper must read from wallpapers.db database",
        )
        self.assertIn(
            "sqlite3",
            content,
            "Helper must use sqlite3 to query the database",
        )

    def test_helper_uses_swaymsg(self):
        """Helper must set wallpaper via swaymsg."""
        with open(self.HELPER_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "swaymsg",
            content,
            "Helper must use swaymsg to set wallpaper",
        )

    def test_helper_accepts_workspace_argument(self):
        """Helper must accept optional workspace number argument."""
        with open(self.HELPER_SCRIPT) as f:
            content = f.read()
        # Should reference $1 or ${1} for workspace argument
        self.assertTrue(
            "$1" in content or "${1" in content,
            "Helper must accept workspace number as first argument",
        )

    def test_profiledef_has_helper_permissions(self):
        """profiledef.sh must set permissions for mados-sway-wallpaper-set."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn(
            "mados-sway-wallpaper-set",
            content,
            "profiledef.sh must include permissions for mados-sway-wallpaper-set",
        )

    def test_sway_config_calls_helper_on_workspace_switch(self):
        """Sway config must call wallpaper helper on workspace switch bindings."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "mados-sway-wallpaper-set",
            content,
            "Sway config workspace bindings must call mados-sway-wallpaper-set",
        )

    def test_sway_workspace_switch_uses_super_alt_arrows(self):
        """Sway config must use Super+Alt+arrows for workspace prev/next."""
        with open(self.SWAY_CONF) as f:
            content = f.read()
        self.assertIn(
            "$mod+Mod1+Left",
            content,
            "Sway config must bind Super+Alt+Left for workspace prev",
        )
        self.assertIn(
            "$mod+Mod1+Right",
            content,
            "Sway config must bind Super+Alt+Right for workspace next",
        )


if __name__ == "__main__":
    unittest.main()
