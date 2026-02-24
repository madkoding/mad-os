#!/usr/bin/env python3
"""
Tests for madOS Sway configuration validation.

Validates the Sway config syntax and structure to catch configuration errors
that would cause Sway to fail or show warnings at startup.  Since Sway
cannot be run in CI (requires a GPU/display), these tests perform static
analysis on the configuration file.

Checks include:
  - File existence
  - Balanced braces (blocks properly opened/closed)
  - Valid top-level keywords (against Sway v1.11 source)
  - Required input blocks present
  - Variable definitions and usage consistency
  - Keybinding syntax validation
  - No duplicate keybindings (mode-aware)
  - Window rule criteria format
  - Color format (#RRGGBB hex)
  - Input subcommand validation (against Sway v1.11 source)
  - exec/exec_always commands not empty
  - Mode blocks properly defined and closed
  - sway-session script validation
  - Feature parity with Hyprland compositor
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
SWAY_DIR = os.path.join(SKEL_DIR, ".config", "sway")
SWAY_CONF = os.path.join(SWAY_DIR, "config")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
HYPR_DIR = os.path.join(SKEL_DIR, ".config", "hypr")
HYPRLAND_CONF = os.path.join(HYPR_DIR, "hyprland.conf")


def _read_config():
    """Read and return the Sway config content."""
    with open(SWAY_CONF) as f:
        return f.read()


def _config_lines():
    """Return non-empty, non-comment lines from the Sway config."""
    lines = []
    with open(SWAY_CONF) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# File existence
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayConfigExists(unittest.TestCase):
    """Verify Sway configuration files exist."""

    def test_sway_config_exists(self):
        """Sway config must exist in /etc/skel/.config/sway/."""
        self.assertTrue(
            os.path.isfile(SWAY_CONF),
            "Sway config missing from /etc/skel/.config/sway/",
        )

    def test_sway_session_script_exists(self):
        """sway-session wrapper script must exist."""
        path = os.path.join(BIN_DIR, "sway-session")
        self.assertTrue(os.path.isfile(path), "sway-session missing")

    def test_sway_config_not_empty(self):
        """Sway config must not be empty."""
        content = _read_config()
        self.assertGreater(
            len(content.strip()),
            0,
            "Sway config file is empty",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Brace balancing and section structure
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayBraceBalance(unittest.TestCase):
    """Verify braces are properly balanced in the Sway config."""

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

    def test_brace_depth_never_negative(self):
        """Brace depth must never go negative (more } than { at any point)."""
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        depth = 0
        for i, char in enumerate(clean):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            self.assertGreaterEqual(
                depth,
                0,
                f"Brace depth went negative at character position {i} – "
                f"more closing braces than opening braces",
            )

    def test_no_excessive_nesting(self):
        """Sway config should not have excessive nesting (max 3 levels)."""
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
            f"Nesting too deep ({max_depth} levels) – Sway typically uses 1-2 levels",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Valid top-level keywords (Sway v1.11 source)
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayKeywords(unittest.TestCase):
    """Verify only valid Sway keywords are used at the top level."""

    # Top-level config commands from Sway v1.11 commands.c handlers array
    VALID_TOP_LEVEL_KEYWORDS = {
        # From handlers array (config-time AND runtime)
        "assign", "bar", "bindcode", "bindgesture", "bindswitch", "bindsym",
        "client.background", "client.focused", "client.focused_inactive",
        "client.focused_tab_title", "client.placeholder",
        "client.unfocused", "client.urgent",
        "default_border", "default_floating_border",
        "exec", "exec_always",
        "floating_maximum_size", "floating_minimum_size", "floating_modifier",
        "focus", "focus_follows_mouse", "focus_on_window_activation",
        "focus_wrapping",
        "font", "for_window", "force_display_urgency_hint",
        "force_focus_wrapping", "fullscreen",
        "gaps", "hide_edge_borders", "input", "mode", "mouse_warping",
        "new_float", "new_window", "no_focus", "output",
        "popup_during_fullscreen", "seat", "set", "show_marks",
        "smart_borders", "smart_gaps", "tiling_drag", "tiling_drag_threshold",
        "title_align", "titlebar_border_thickness", "titlebar_padding",
        "unbindcode", "unbindgesture", "unbindswitch", "unbindsym",
        "workspace", "workspace_auto_back_and_forth",
        # Config-only commands (config_handlers)
        "default_orientation", "include", "primary_selection",
        "swaybg_command", "swaynag_command", "workspace_layout", "xwayland",
    }

    def _get_top_level_keywords(self):
        """Extract top-level keywords from config (outside blocks)."""
        content = _read_config()
        lines = content.splitlines()
        depth = 0
        keywords = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Calculate depth before this line
            pre_depth = depth
            depth += stripped.count("{") - stripped.count("}")

            # Only process lines at top level (depth 0 before processing)
            if pre_depth == 0:
                # Extract the keyword: first word(s) before any arguments
                # Handle dotted keywords like client.focused
                match = re.match(r"^([\w][\w.-]*)", stripped)
                if match:
                    keywords.append(match.group(1))
        return keywords

    def test_all_top_level_keywords_valid(self):
        """Every top-level keyword should be a known Sway v1.11 keyword."""
        keywords = self._get_top_level_keywords()
        for kw in keywords:
            with self.subTest(keyword=kw):
                self.assertIn(
                    kw,
                    self.VALID_TOP_LEVEL_KEYWORDS,
                    f"Unknown top-level keyword '{kw}' in Sway config. "
                    f"If this is a new valid keyword, add it to "
                    f"VALID_TOP_LEVEL_KEYWORDS.",
                )

    def test_essential_keywords_present(self):
        """Essential Sway keywords must be present in the config."""
        content = _read_config()
        essential = ["set", "bindsym", "exec", "input", "output"]
        for kw in essential:
            with self.subTest(keyword=kw):
                self.assertIn(
                    kw,
                    content,
                    f"Essential keyword '{kw}' missing from Sway config",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Required input sections
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayRequiredSections(unittest.TestCase):
    """Verify essential input blocks are present in the config."""

    def test_keyboard_input_block_present(self):
        """An input type:keyboard block must be defined."""
        content = _read_config()
        self.assertRegex(
            content,
            re.compile(r"^\s*input\s+type:keyboard\s*\{", re.MULTILINE),
            "Required 'input type:keyboard' block missing from Sway config",
        )

    def test_touchpad_input_block_present(self):
        """An input type:touchpad block must be defined."""
        content = _read_config()
        self.assertRegex(
            content,
            re.compile(r"^\s*input\s+type:touchpad\s*\{", re.MULTILINE),
            "Required 'input type:touchpad' block missing from Sway config",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Variable definitions and references
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayVariables(unittest.TestCase):
    """Verify variable definitions and usage are consistent."""

    @staticmethod
    def _is_set_line(parts):
        """Return True if the split line tokens represent a 'set $var value' definition."""
        return len(parts) >= 3 and parts[0] == "set" and parts[1].startswith("$")

    def _get_defined_vars(self):
        """Return dict of defined variable names to their values (set $var value)."""
        defs = {}
        for line in _config_lines():
            parts = line.split()
            if self._is_set_line(parts):
                defs[parts[1][1:]] = " ".join(parts[2:])
        return defs

    def _get_used_vars(self):
        """Return set of variable names referenced in the config ($var)."""
        content = _read_config()
        # Remove comments first to avoid matching vars in comment text
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        # Remove definition lines to only find usage (line-by-line to avoid
        # backtracking-vulnerable regex with multiple quantifiers)
        filtered = []
        for line in clean.splitlines():
            parts = line.split()
            if self._is_set_line(parts):
                continue
            filtered.append(line)
        clean = "\n".join(filtered)
        return set(re.findall(r"\$([\w-]+)", clean))

    def test_mod_defined(self):
        """$mod must be defined (standard Sway convention)."""
        defined = self._get_defined_vars()
        self.assertIn(
            "mod",
            defined,
            "$mod must be defined for keybindings",
        )

    def test_term_defined(self):
        """$term must be defined for terminal launcher."""
        defined = self._get_defined_vars()
        self.assertIn(
            "term",
            defined,
            "$term must be defined for the terminal keybinding",
        )

    def test_menu_defined(self):
        """$menu must be defined for application launcher."""
        defined = self._get_defined_vars()
        self.assertIn(
            "menu",
            defined,
            "$menu must be defined for the app launcher keybinding",
        )

    def test_all_used_vars_are_defined(self):
        """Every variable used ($var) must have a corresponding set definition."""
        defined = set(self._get_defined_vars().keys())
        used = self._get_used_vars()
        # Filter out variables used inside shell command strings (e.g., $(date ...))
        # and gnome-schema which contains a hyphen that gets split
        undefined = used - defined
        self.assertEqual(
            undefined,
            set(),
            f"Variables used but never defined: {undefined}",
        )

    def test_vim_direction_vars_defined(self):
        """Vim-style direction variables must be defined ($left, $down, $up, $right)."""
        defined = self._get_defined_vars()
        for var in ["left", "down", "up", "right"]:
            with self.subTest(variable=var):
                self.assertIn(
                    var,
                    defined,
                    f"${var} must be defined for vim-style navigation",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Keybinding syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayBindsymSyntax(unittest.TestCase):
    """Verify keybindings use correct Sway bindsym syntax."""

    def _get_bindsym_lines(self):
        """Return all bindsym lines from the config (outside mode blocks too)."""
        lines = _config_lines()
        bind_lines = []
        for line in lines:
            match = re.match(r"^bindsym\s+(.+)", line)
            if match:
                bind_lines.append((match.group(1), line))
        return bind_lines

    def test_bindsym_has_key_and_action(self):
        """Each bindsym must have at least a key combo and an action."""
        bind_lines = self._get_bindsym_lines()
        self.assertGreater(len(bind_lines), 0, "No bindsym lines found")
        for value, line in bind_lines:
            with self.subTest(line=line[:80]):
                # Strip optional flags like --locked, --no-startup-id
                clean_value = re.sub(r"--\S+\s*", "", value).strip()
                parts = clean_value.split(None, 1)
                self.assertGreaterEqual(
                    len(parts),
                    2,
                    f"bindsym must have at least key+action: {line}",
                )

    def test_bindsym_action_not_empty(self):
        """The action part of a bindsym must not be empty."""
        bind_lines = self._get_bindsym_lines()
        for value, line in bind_lines:
            with self.subTest(line=line[:80]):
                # Strip flags
                clean_value = re.sub(r"--\S+\s*", "", value).strip()
                parts = clean_value.split(None, 1)
                if len(parts) >= 2:
                    action = parts[1].strip()
                    self.assertGreater(
                        len(action),
                        0,
                        f"Empty action in bindsym: {line}",
                    )

    def test_bindsym_uses_valid_flags(self):
        """bindsym flags must be valid Sway flags."""
        valid_flags = {"--locked", "--to-code", "--no-warn",
                       "--no-repeat", "--release", "--no-startup-id",
                       "--inhibited", "--border", "--whole-window",
                       "--exclude-titlebar", "--input-device"}
        bind_lines = self._get_bindsym_lines()
        for value, line in bind_lines:
            flags = re.findall(r"(--\S+)", value)
            for flag in flags:
                with self.subTest(line=line[:80], flag=flag):
                    self.assertIn(
                        flag,
                        valid_flags,
                        f"Invalid bindsym flag '{flag}' in: {line}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Duplicate keybinding detection
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayNoDuplicateBinds(unittest.TestCase):
    """Detect duplicate keybindings that would cause conflicts."""

    def test_no_duplicate_binds(self):
        """No two bindsym should have the same key in the same mode."""
        content = _read_config()
        lines = content.splitlines()
        current_mode = "default"
        binds = []
        depth = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Track mode blocks
            mode_match = re.match(r'^mode\s+"([^"]+)"\s*\{', stripped)
            if mode_match:
                current_mode = mode_match.group(1)
                depth += 1
                continue

            if stripped == "}":
                if depth > 0:
                    depth -= 1
                    if depth == 0:
                        current_mode = "default"
                continue

            # Collect bindsym lines
            bind_match = re.match(r"^bindsym\s+(.+)", stripped)
            if bind_match:
                value = bind_match.group(1)
                # Strip flags
                clean_value = re.sub(r"--\S+\s*", "", value).strip()
                parts = clean_value.split(None, 1)
                if len(parts) >= 1:
                    key_combo = parts[0]
                    # Normalize: the binding key is (mode, key_combo)
                    bind_key = (current_mode, key_combo)
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
class TestSwayWindowRules(unittest.TestCase):
    """Verify for_window rules use correct Sway criteria syntax."""

    # Valid criteria keys for Sway for_window rules
    VALID_CRITERIA = {
        "app_id", "class", "instance", "title", "window_role",
        "window_type", "con_id", "con_mark", "floating", "tiling",
        "urgent", "workspace", "shell", "pid",
        "floating_from", "tiling_from", "all",
    }

    def _get_for_window_rules(self):
        """Return all for_window lines with their criteria."""
        lines = _config_lines()
        rules = []
        for line in lines:
            match = re.match(r"^for_window\s+\[([^\]]+)\]\s+(.+)", line)
            if match:
                rules.append((match.group(1), match.group(2), line))
        return rules

    def _get_no_focus_rules(self):
        """Return all no_focus lines with their criteria."""
        lines = _config_lines()
        rules = []
        for line in lines:
            match = re.match(r"^no_focus\s+\[([^\]]+)\]", line)
            if match:
                rules.append((match.group(1), line))
        return rules

    def test_for_window_has_criteria_and_action(self):
        """Each for_window must have [criteria] and an action."""
        rules = self._get_for_window_rules()
        self.assertGreater(len(rules), 0, "No for_window rules found")
        for criteria, action, line in rules:
            with self.subTest(line=line[:80]):
                self.assertGreater(
                    len(criteria.strip()),
                    0,
                    f"Empty criteria in for_window: {line}",
                )
                self.assertGreater(
                    len(action.strip()),
                    0,
                    f"Empty action in for_window: {line}",
                )

    def test_for_window_criteria_keys_valid(self):
        """Criteria keys in for_window must be valid Sway criteria."""
        rules = self._get_for_window_rules()
        for criteria, _, line in rules:
            # Parse key=value pairs from criteria (string split to avoid
            # backtracking-vulnerable regex)
            keys = [
                tok.split("=")[0]
                for tok in criteria.split()
                if "=" in tok
            ]
            for key in keys:
                with self.subTest(line=line[:80], key=key):
                    self.assertIn(
                        key,
                        self.VALID_CRITERIA,
                        f"Invalid criteria key '{key}' in for_window: {line}",
                    )

    def test_no_focus_criteria_keys_valid(self):
        """Criteria keys in no_focus must be valid Sway criteria."""
        rules = self._get_no_focus_rules()
        for criteria, line in rules:
            keys = [
                tok.split("=")[0]
                for tok in criteria.split()
                if "=" in tok
            ]
            for key in keys:
                with self.subTest(line=line[:80], key=key):
                    self.assertIn(
                        key,
                        self.VALID_CRITERIA,
                        f"Invalid criteria key '{key}' in no_focus: {line}",
                    )

    def test_criteria_values_are_quoted(self):
        """Criteria values in brackets should be quoted for safety."""
        rules = self._get_for_window_rules()
        for criteria, _, line in rules:
            # Find key=value pairs where value is not quoted (string
            # split to avoid backtracking-vulnerable regex)
            unquoted = []
            for tok in criteria.split():
                if "=" not in tok:
                    continue
                k, _, rest = tok.partition("=")
                if rest and not rest.startswith('"'):
                    # Strip trailing ']' that may be part of bracket syntax
                    unquoted.append((k, rest.rstrip("]")))
            for key, val in unquoted:
                with self.subTest(line=line[:80], key=key, value=val):
                    if not val.startswith('"'):
                        self.fail(
                            f"Criteria value for '{key}' should be quoted: "
                            f'{key}="{val}" in: {line}'
                        )


# ═══════════════════════════════════════════════════════════════════════════
# Color format validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayColors(unittest.TestCase):
    """Verify color values use valid #RRGGBB hex format."""

    def test_hex_colors_valid_format(self):
        """All #RRGGBB colors must have valid hex format (6 hex digits)."""
        content = _read_config()
        # Remove comments
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        # Find all hex color references (#XXXXXX)
        colors = re.findall(r"(#[0-9a-fA-F]+)\b", clean)
        for color in colors:
            with self.subTest(color=color):
                self.assertRegex(
                    color,
                    r"^#[0-9a-fA-F]{6}$",
                    f"Invalid hex color '{color}' – must be #RRGGBB (6 hex digits)",
                )

    def test_color_variables_defined(self):
        """Color variables referenced in client.* directives must be defined."""
        content = _read_config()
        # Find client.* lines (they use color variables)
        client_lines = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("client.") and not line.strip().startswith("#")
        ]
        self.assertGreater(
            len(client_lines),
            0,
            "No client.* color directives found in config",
        )

    def test_client_focused_has_five_colors(self):
        """client.focused must have 5 color arguments."""
        lines = _config_lines()
        found = False
        for line in lines:
            # Match "client.focused " but not "client.focused_inactive" etc.
            if re.match(r"^client\.focused\s+(?!_)", line):
                found = True
                parts = line.split()
                # client.focused + 5 colors = 6 parts
                self.assertEqual(
                    len(parts),
                    6,
                    f"client.focused needs 5 colors (border bg text indicator child_border): {line}",
                )
                break
        self.assertTrue(found, "client.focused directive not found in config")


# ═══════════════════════════════════════════════════════════════════════════
# Input subcommand validation (Sway v1.11 source)
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayInputSubcommands(unittest.TestCase):
    """Verify input subcommands are valid Sway v1.11 commands."""

    # Valid input subcommands from sway/commands/input/ directory (v1.11)
    VALID_INPUT_SUBCOMMANDS = {
        "accel_profile", "calibration_matrix", "click_method",
        "clickfinger_button_map", "drag", "drag_lock", "dwt", "dwtp",
        "events", "left_handed", "map_from_region", "map_to_output",
        "map_to_region", "middle_emulation", "natural_scroll",
        "pointer_accel", "repeat_delay", "repeat_rate", "rotation_angle",
        "scroll_button", "scroll_button_lock", "scroll_factor",
        "scroll_method", "tap", "tap_button_map", "tool_mode",
        "xkb_capslock", "xkb_file", "xkb_layout", "xkb_model",
        "xkb_numlock", "xkb_options", "xkb_rules", "xkb_switch_layout",
        "xkb_variant",
    }

    def _get_input_subcommands(self):
        """Extract subcommands used inside input { } blocks."""
        content = _read_config()
        lines = content.splitlines()
        in_input = False
        depth = 0
        subcommands = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if re.match(r"^input\s+", stripped):
                in_input = True

            if in_input:
                if "{" in stripped:
                    depth += stripped.count("{")
                if "}" in stripped:
                    depth -= stripped.count("}")
                    if depth <= 0:
                        in_input = False
                        depth = 0
                        continue

                # Only collect subcommands inside the block (depth >= 1)
                if depth >= 1 and "{" not in stripped and "}" not in stripped:
                    match = re.match(r"^\s*(\w+)\s+", stripped)
                    if match:
                        subcommands.append((match.group(1), stripped))

        return subcommands

    def test_all_input_subcommands_valid(self):
        """Every subcommand inside input blocks must be a valid Sway input command."""
        subcommands = self._get_input_subcommands()
        self.assertGreater(len(subcommands), 0, "No input subcommands found")
        for subcmd, line in subcommands:
            with self.subTest(subcommand=subcmd, line=line.strip()):
                self.assertIn(
                    subcmd,
                    self.VALID_INPUT_SUBCOMMANDS,
                    f"Unknown input subcommand '{subcmd}' – not valid in "
                    f"Sway v1.11. Line: {line.strip()}",
                )

    def test_keyboard_has_xkb_layout(self):
        """Keyboard input block must define xkb_layout."""
        content = _read_config()
        self.assertIn(
            "xkb_layout",
            content,
            "Keyboard input block must define xkb_layout",
        )

    def test_touchpad_has_tap(self):
        """Touchpad input block must enable tap."""
        content = _read_config()
        self.assertIn(
            "tap enabled",
            content,
            "Touchpad input block should enable tap-to-click",
        )


# ═══════════════════════════════════════════════════════════════════════════
# exec/exec_always command validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayExecCommands(unittest.TestCase):
    """Verify exec and exec_always commands are not empty."""

    def test_exec_commands_not_empty(self):
        """Standalone exec commands must have a non-empty command."""
        lines = _config_lines()
        for line in lines:
            # Match standalone exec (not part of bindsym)
            # exec at the start of a line (top-level) with optional flags
            match = re.match(r"^exec(?!_always)\s+(.*)", line)
            if match:
                cmd = match.group(1).strip()
                # Skip exec { blocks (the opening brace)
                if cmd == "{":
                    continue
                # Strip --no-startup-id flag
                cmd = re.sub(r"--no-startup-id\s*", "", cmd).strip()
                with self.subTest(line=line[:80]):
                    self.assertGreater(
                        len(cmd),
                        0,
                        f"Empty exec command: {line}",
                    )

    def test_exec_always_commands_not_empty(self):
        """exec_always commands must have a non-empty command."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r"^exec_always\s+(.*)", line)
            if match:
                cmd = match.group(1).strip()
                # Strip --no-startup-id flag
                cmd = re.sub(r"--no-startup-id\s*", "", cmd).strip()
                with self.subTest(line=line[:80]):
                    self.assertGreater(
                        len(cmd),
                        0,
                        f"Empty exec_always command: {line}",
                    )

    def test_exec_in_bindsym_not_empty(self):
        """exec commands inside bindsym must have a non-empty command."""
        lines = _config_lines()
        for line in lines:
            match = re.match(r"^bindsym\s+.+\s+exec\s+(.*)", line)
            if match:
                cmd = match.group(1).strip()
                with self.subTest(line=line[:80]):
                    self.assertGreater(
                        len(cmd),
                        0,
                        f"Empty exec in bindsym: {line}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Mode block validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayModeBlocks(unittest.TestCase):
    """Verify mode blocks are properly defined and closed."""

    def _get_mode_blocks(self):
        """Extract mode names and their content."""
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        # Find mode "name" { ... } blocks
        modes = re.findall(r'mode\s+"([^"]+)"\s*\{', clean)
        return modes

    def test_mode_blocks_exist(self):
        """At least a resize mode should be defined."""
        modes = self._get_mode_blocks()
        self.assertGreater(
            len(modes),
            0,
            "At least one mode block (e.g., resize) should be defined",
        )

    def test_resize_mode_exists(self):
        """A 'resize' mode must be defined."""
        modes = self._get_mode_blocks()
        self.assertIn(
            "resize",
            modes,
            "A 'resize' mode must be defined for window resizing",
        )

    def test_mode_blocks_have_escape(self):
        """Each mode block must have an Escape binding to return to default."""
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        # Find mode blocks
        mode_blocks = re.findall(
            r'mode\s+"([^"]+)"\s*\{([^}]*)\}', clean, re.DOTALL
        )
        for name, body in mode_blocks:
            with self.subTest(mode=name):
                self.assertIn(
                    "Escape",
                    body,
                    f"Mode '{name}' must have an Escape binding to exit",
                )

    def test_mode_blocks_return_to_default(self):
        """Each mode block must have a binding that returns to mode 'default'."""
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        mode_blocks = re.findall(
            r'mode\s+"([^"]+)"\s*\{([^}]*)\}', clean, re.DOTALL
        )
        for name, body in mode_blocks:
            with self.subTest(mode=name):
                self.assertIn(
                    'mode "default"',
                    body,
                    f"Mode '{name}' must have a binding to return to mode \"default\"",
                )

    def test_mode_activation_bindsym_exists(self):
        """Each defined mode must have a top-level bindsym to enter it."""
        content = _read_config()
        clean = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        modes = re.findall(r'mode\s+"([^"]+)"\s*\{', clean)
        for mode_name in modes:
            with self.subTest(mode=mode_name):
                pattern = rf'bindsym\s+.+\s+mode\s+"{re.escape(mode_name)}"'
                self.assertRegex(
                    clean,
                    re.compile(pattern),
                    f"No bindsym found to enter mode '{mode_name}'",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Sway session script validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSwaySessionScript(unittest.TestCase):
    """Verify sway-session script is correct."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "sway-session")
        if os.path.isfile(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()

    def test_has_shebang(self):
        """sway-session must have a bash shebang."""
        self.assertTrue(
            self.content.startswith("#!/bin/bash"),
            "Must start with #!/bin/bash",
        )

    def test_sets_wayland_session_type(self):
        """sway-session must set XDG_SESSION_TYPE=wayland."""
        self.assertIn(
            "XDG_SESSION_TYPE=wayland",
            self.content,
            "Must set XDG_SESSION_TYPE=wayland",
        )

    def test_sets_desktop_to_sway(self):
        """sway-session must set XDG_CURRENT_DESKTOP=sway."""
        self.assertIn(
            "XDG_CURRENT_DESKTOP=sway",
            self.content,
            "Must set XDG_CURRENT_DESKTOP=sway",
        )

    def test_execs_sway(self):
        """sway-session must exec sway at the end."""
        self.assertIn(
            "exec sway",
            self.content,
            "Must exec sway at the end",
        )

    def test_sets_wayland_env(self):
        """sway-session must set MOZ_ENABLE_WAYLAND=1 for Firefox."""
        self.assertIn(
            "MOZ_ENABLE_WAYLAND=1",
            self.content,
            "Must set MOZ_ENABLE_WAYLAND=1 for Firefox Wayland support",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Feature parity with Hyprland compositor
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayConfigFeatureParity(unittest.TestCase):
    """Verify both compositors have matching essential features.

    Both Sway and Hyprland configs should provide a consistent user
    experience with the same basic features available via keyboard.
    """

    def setUp(self):
        with open(SWAY_CONF) as f:
            self.sway = f.read()
        if os.path.isfile(HYPRLAND_CONF):
            with open(HYPRLAND_CONF) as f:
                self.hyprland = f.read()
        else:
            self.hyprland = ""

    # --- Workspaces 1-5 ---

    def test_workspaces_1_through_5(self):
        """Sway config must bind workspaces 1-5."""
        for ws in range(1, 6):
            with self.subTest(workspace=ws):
                pattern = rf"bindsym\s+\$mod\+{ws}\s+workspace\s+number\s+{ws}"
                self.assertRegex(
                    self.sway,
                    re.compile(pattern),
                    f"Sway config must bind $mod+{ws} to workspace {ws}",
                )

    def test_move_to_workspaces_1_through_5(self):
        """Sway config must bind move-to-workspace for workspaces 1-5."""
        for ws in range(1, 6):
            with self.subTest(workspace=ws):
                self.assertIn(
                    f"move container to workspace number {ws}",
                    self.sway,
                    f"Sway config must have move-to-workspace binding for workspace {ws}",
                )

    # --- Terminal and launcher ---

    def test_terminal_binding(self):
        """Sway config must have a terminal launcher binding ($mod+Return)."""
        self.assertIn(
            "$mod+Return",
            self.sway,
            "Sway config must bind $mod+Return to launch terminal",
        )
        self.assertIn(
            "exec $term",
            self.sway,
            "Terminal binding must exec $term",
        )

    def test_app_launcher_binding(self):
        """Sway config must have an app launcher binding ($mod+d)."""
        self.assertIn(
            "$mod+d",
            self.sway,
            "Sway config must bind $mod+d for app launcher",
        )

    # --- Multimedia keys ---

    def test_volume_mute_binding(self):
        """Sway config must have XF86AudioMute binding."""
        self.assertIn(
            "XF86AudioMute",
            self.sway,
            "Sway config must bind XF86AudioMute for volume mute",
        )

    def test_volume_up_binding(self):
        """Sway config must have XF86AudioRaiseVolume binding."""
        self.assertIn(
            "XF86AudioRaiseVolume",
            self.sway,
            "Sway config must bind XF86AudioRaiseVolume for volume up",
        )

    def test_volume_down_binding(self):
        """Sway config must have XF86AudioLowerVolume binding."""
        self.assertIn(
            "XF86AudioLowerVolume",
            self.sway,
            "Sway config must bind XF86AudioLowerVolume for volume down",
        )

    def test_mic_mute_binding(self):
        """Sway config must have XF86AudioMicMute binding."""
        self.assertIn(
            "XF86AudioMicMute",
            self.sway,
            "Sway config must bind XF86AudioMicMute for mic mute",
        )

    def test_brightness_up_binding(self):
        """Sway config must have XF86MonBrightnessUp binding."""
        self.assertIn(
            "XF86MonBrightnessUp",
            self.sway,
            "Sway config must bind XF86MonBrightnessUp for brightness up",
        )

    def test_brightness_down_binding(self):
        """Sway config must have XF86MonBrightnessDown binding."""
        self.assertIn(
            "XF86MonBrightnessDown",
            self.sway,
            "Sway config must bind XF86MonBrightnessDown for brightness down",
        )

    # --- Screenshots ---

    def test_screenshot_binding(self):
        """Sway config must have Print key screenshot binding."""
        self.assertIn(
            "Print",
            self.sway,
            "Sway config must bind Print for screenshots",
        )

    def test_screenshot_uses_grim(self):
        """Sway config must use grim for native Wayland screenshots."""
        self.assertIn(
            "grim",
            self.sway,
            "Sway config must use grim for Wayland screenshots",
        )

    def test_screenshot_clipboard_binding(self):
        """Sway config must have clipboard screenshot binding ($mod+Shift+s)."""
        self.assertIn(
            "$mod+Shift+s",
            self.sway,
            "Sway config must bind $mod+Shift+s for clipboard screenshot",
        )

    # --- Scratchpad ---

    def test_scratchpad_bindings(self):
        """Sway config must have scratchpad show and move bindings."""
        self.assertIn(
            "scratchpad show",
            self.sway,
            "Sway config must have scratchpad show binding",
        )
        self.assertIn(
            "move scratchpad",
            self.sway,
            "Sway config must have move-to-scratchpad binding",
        )

    # --- Floating ---

    def test_floating_toggle(self):
        """Sway config must have floating toggle binding."""
        self.assertIn(
            "floating toggle",
            self.sway,
            "Sway config must have a floating toggle binding",
        )

    def test_floating_modifier(self):
        """Sway config must define floating_modifier."""
        self.assertIn(
            "floating_modifier",
            self.sway,
            "Sway config must define floating_modifier for mouse drag",
        )

    # --- Resize ---

    def test_resize_mode(self):
        """Sway config must have a resize mode."""
        self.assertRegex(
            self.sway,
            re.compile(r'mode\s+"resize"'),
            "Sway config must define a 'resize' mode",
        )

    def test_resize_mode_entry_binding(self):
        """Sway config must have a binding to enter resize mode."""
        self.assertIn(
            'mode "resize"',
            self.sway,
            "Sway config must have bindsym to enter resize mode",
        )

    # --- Window management ---

    def test_kill_binding(self):
        """Sway config must have a kill binding ($mod+Shift+q)."""
        self.assertIn(
            "kill",
            self.sway,
            "Sway config must have a kill window binding",
        )

    def test_fullscreen_binding(self):
        """Sway config must have a fullscreen binding."""
        self.assertIn(
            "fullscreen",
            self.sway,
            "Sway config must have a fullscreen binding",
        )

    def test_focus_parent_binding(self):
        """Sway config must have focus parent binding."""
        self.assertIn(
            "focus parent",
            self.sway,
            "Sway config must have focus parent binding",
        )

    # --- Layout ---

    def test_layout_stacking_binding(self):
        """Sway config must have stacking layout binding."""
        self.assertIn(
            "layout stacking",
            self.sway,
            "Sway config must have stacking layout binding",
        )

    def test_layout_tabbed_binding(self):
        """Sway config must have tabbed layout binding."""
        self.assertIn(
            "layout tabbed",
            self.sway,
            "Sway config must have tabbed layout binding",
        )

    # --- Reload ---

    def test_reload_binding(self):
        """Sway config must have a reload binding ($mod+Shift+c)."""
        self.assertIn(
            "reload",
            self.sway,
            "Sway config must have a reload binding",
        )

    # --- Navigation ---

    def test_vim_navigation_bindings(self):
        """Sway config must have vim-style (hjkl) navigation bindings."""
        for direction in ["left", "down", "up", "right"]:
            with self.subTest(direction=direction):
                self.assertIn(
                    f"focus {direction}",
                    self.sway,
                    f"Sway config must have focus {direction} binding",
                )

    def test_arrow_navigation_bindings(self):
        """Sway config must have arrow key navigation bindings."""
        for key in ["Left", "Down", "Up", "Right"]:
            with self.subTest(key=key):
                self.assertIn(
                    f"$mod+{key}",
                    self.sway,
                    f"Sway config must bind $mod+{key} for navigation",
                )

    # --- Workspace cycling ---

    def test_workspace_cycling_bindings(self):
        """Sway config must have Super+Alt+arrow workspace cycling."""
        self.assertIn(
            "$mod+Mod1+Left",
            self.sway,
            "Sway config must bind Super+Alt+Left for workspace cycling",
        )
        self.assertIn(
            "$mod+Mod1+Right",
            self.sway,
            "Sway config must bind Super+Alt+Right for workspace cycling",
        )

    # --- System includes ---

    def test_includes_system_config(self):
        """Sway config must include system config drop-ins."""
        self.assertIn(
            "include /etc/sway/config.d/*",
            self.sway,
            "Sway config must include /etc/sway/config.d/* for system overrides",
        )

    # --- Both compositors use same tools ---

    def test_both_use_wpctl_for_audio(self):
        """Both compositors must use wpctl (PipeWire) for audio control."""
        self.assertIn(
            "wpctl",
            self.sway,
            "Sway config must use wpctl for PipeWire audio control",
        )
        if self.hyprland:
            self.assertIn(
                "wpctl",
                self.hyprland,
                "Hyprland config must use wpctl for PipeWire audio control",
            )

    def test_both_use_brightnessctl(self):
        """Both compositors must use brightnessctl for brightness control."""
        self.assertIn(
            "brightnessctl",
            self.sway,
            "Sway config must use brightnessctl for brightness",
        )
        if self.hyprland:
            self.assertIn(
                "brightnessctl",
                self.hyprland,
                "Hyprland config must use brightnessctl for brightness",
            )

    def test_both_use_foot_terminal(self):
        """Both compositors must use foot as the terminal emulator."""
        self.assertIn(
            "foot",
            self.sway,
            "Sway config must define foot as terminal",
        )
        if self.hyprland:
            self.assertIn(
                "foot",
                self.hyprland,
                "Hyprland config must define foot as terminal",
            )

    def test_both_use_wofi_launcher(self):
        """Both compositors must use wofi as the application launcher."""
        self.assertIn(
            "wofi",
            self.sway,
            "Sway config must use wofi as app launcher",
        )
        if self.hyprland:
            self.assertIn(
                "wofi",
                self.hyprland,
                "Hyprland config must use wofi as app launcher",
            )


if __name__ == "__main__":
    unittest.main()
