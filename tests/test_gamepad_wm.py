#!/usr/bin/env python3
"""
Tests for madOS gamepad/Steam Deck/Xbox Series integration (mados-gamepad-wm).

Validates:
  - Script existence and permissions in profiledef.sh
  - Python syntax validity
  - python-evdev listed in packages
  - Compositor auto-start integration (Sway and Hyprland)
  - GamepadState dispatch logic (mocked evdev)
  - Backend action methods exist for both Sway and Hyprland
  - Device detection helpers
  - Compositor detection logic
  - Gamepad profile detection (deck / xbox / generic)
  - Xbox-specific bindings (LT/RT + D-pad, Share button)
  - Profile-aware dispatch (back paddles vs trigger combos)
"""

import ast
import os
import re
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SKEL_DIR = os.path.join(AIROOTFS, "etc", "skel")
SWAY_CONFIG = os.path.join(SKEL_DIR, ".config", "sway", "config")
HYPR_CONFIG = os.path.join(SKEL_DIR, ".config", "hypr", "hyprland.conf")
PACKAGES_FILE = os.path.join(REPO_DIR, "packages.x86_64")
PROFILEDEF = os.path.join(REPO_DIR, "profiledef.sh")
GAMEPAD_SCRIPT = os.path.join(BIN_DIR, "mados-gamepad-wm")


def _create_evdev_mock():
    """Create a minimal evdev mock module so we can import mados-gamepad-wm."""
    evdev_mock = types.ModuleType("evdev")

    class FakeEcodes:
        """Fake ecodes with standard gamepad codes."""
        BTN_SOUTH = 304
        BTN_EAST = 305
        BTN_NORTH = 307
        BTN_WEST = 308
        BTN_TL = 310
        BTN_TR = 311
        BTN_SELECT = 314
        BTN_START = 315
        BTN_MODE = 316
        BTN_THUMBL = 317
        BTN_THUMBR = 318
        BTN_TRIGGER_HAPPY1 = 704
        BTN_TRIGGER_HAPPY2 = 705
        BTN_TRIGGER_HAPPY3 = 706
        BTN_TRIGGER_HAPPY4 = 707
        KEY_RECORD = 167
        ABS_HAT0X = 16
        ABS_HAT0Y = 17
        ABS_Z = 2
        ABS_RZ = 5
        EV_KEY = 1
        EV_ABS = 3

    evdev_mock.ecodes = FakeEcodes()

    class FakeInputDevice:
        def __init__(self, path=""):
            self.path = path
            self.name = f"Fake Gamepad ({path})"
            self.fd = 42

        def capabilities(self, verbose=False):
            return {
                FakeEcodes.EV_KEY: [
                    FakeEcodes.BTN_SOUTH, FakeEcodes.BTN_EAST,
                    FakeEcodes.BTN_NORTH, FakeEcodes.BTN_WEST,
                    FakeEcodes.BTN_TL, FakeEcodes.BTN_TR,
                    FakeEcodes.BTN_START, FakeEcodes.BTN_SELECT,
                    FakeEcodes.BTN_MODE,
                ],
                FakeEcodes.EV_ABS: [
                    FakeEcodes.ABS_HAT0X, FakeEcodes.ABS_HAT0Y,
                ],
            }

        def close(self):
            pass

        def read(self):
            return []

    evdev_mock.InputDevice = FakeInputDevice
    return evdev_mock


def _import_gamepad_module():
    """Import mados-gamepad-wm as a module, with evdev mocked."""
    evdev_mock = _create_evdev_mock()
    sys.modules["evdev"] = evdev_mock
    sys.modules["evdev.ecodes"] = evdev_mock.ecodes

    import importlib.util
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader("mados_gamepad_wm", GAMEPAD_SCRIPT)
    spec = importlib.util.spec_from_file_location(
        "mados_gamepad_wm", GAMEPAD_SCRIPT, loader=loader
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════════
# File & Package Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestGamepadFileExists(unittest.TestCase):
    """Verify gamepad script and related configs exist."""

    def test_gamepad_script_exists(self):
        """mados-gamepad-wm must exist in /usr/local/bin/."""
        self.assertTrue(os.path.isfile(GAMEPAD_SCRIPT),
                        "mados-gamepad-wm script missing")

    def test_gamepad_script_has_shebang(self):
        """Script must start with Python3 shebang."""
        with open(GAMEPAD_SCRIPT) as f:
            first_line = f.readline()
        self.assertIn("python3", first_line,
                       "mados-gamepad-wm must have python3 shebang")

    def test_python_syntax_valid(self):
        """Script must have valid Python syntax."""
        with open(GAMEPAD_SCRIPT) as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.fail(f"Syntax error in mados-gamepad-wm: {e}")


class TestGamepadPackages(unittest.TestCase):
    """Verify python-evdev is in the package list."""

    def test_python_evdev_in_packages(self):
        """python-evdev must be listed in packages.x86_64."""
        with open(PACKAGES_FILE) as f:
            packages = f.read()
        self.assertIn("python-evdev", packages,
                       "python-evdev must be in packages.x86_64 for gamepad support")


class TestGamepadProfileDef(unittest.TestCase):
    """Verify mados-gamepad-wm is registered in profiledef.sh."""

    def test_gamepad_in_profiledef(self):
        """mados-gamepad-wm must be in profiledef.sh file_permissions."""
        with open(PROFILEDEF) as f:
            content = f.read()
        self.assertIn("mados-gamepad-wm", content,
                       "mados-gamepad-wm must be in profiledef.sh file_permissions")

    def test_gamepad_permissions_755(self):
        """mados-gamepad-wm must have 0:0:755 permissions."""
        with open(PROFILEDEF) as f:
            content = f.read()
        pattern = r'mados-gamepad-wm.*0:0:755'
        self.assertRegex(content, pattern,
                         "mados-gamepad-wm must have 0:0:755 permissions")


# ═══════════════════════════════════════════════════════════════════════════
# Compositor Integration Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayIntegration(unittest.TestCase):
    """Verify mados-gamepad-wm is started by Sway config."""

    def test_gamepad_in_sway_config(self):
        """Sway config must exec mados-gamepad-wm."""
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn("mados-gamepad-wm", content,
                       "Sway config must start mados-gamepad-wm")

    def test_sway_config_specifies_compositor(self):
        """Sway config must pass --compositor sway."""
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn("--compositor sway", content,
                       "Sway config must pass --compositor sway to mados-gamepad-wm")


class TestHyprlandIntegration(unittest.TestCase):
    """Verify mados-gamepad-wm is started by Hyprland config."""

    def test_gamepad_in_hyprland_config(self):
        """Hyprland config must exec-once mados-gamepad-wm."""
        with open(HYPR_CONFIG) as f:
            content = f.read()
        self.assertIn("mados-gamepad-wm", content,
                       "Hyprland config must start mados-gamepad-wm")

    def test_hyprland_config_specifies_compositor(self):
        """Hyprland config must pass --compositor hyprland."""
        with open(HYPR_CONFIG) as f:
            content = f.read()
        self.assertIn("--compositor hyprland", content,
                       "Hyprland config must pass --compositor hyprland")


# ═══════════════════════════════════════════════════════════════════════════
# Module Import & Backend Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestGamepadModuleImport(unittest.TestCase):
    """Verify the gamepad module can be imported with mocked evdev."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def test_module_has_version(self):
        """Module must define VERSION."""
        self.assertTrue(hasattr(self.mod, "VERSION"))

    def test_module_has_sway_backend(self):
        """Module must define SwayBackend."""
        self.assertTrue(hasattr(self.mod, "SwayBackend"))

    def test_module_has_hyprland_backend(self):
        """Module must define HyprlandBackend."""
        self.assertTrue(hasattr(self.mod, "HyprlandBackend"))

    def test_module_has_gamepad_state(self):
        """Module must define GamepadState."""
        self.assertTrue(hasattr(self.mod, "GamepadState"))

    def test_module_has_inhibit_checker(self):
        """Module must define InhibitChecker."""
        self.assertTrue(hasattr(self.mod, "InhibitChecker"))


class TestSwayBackendActions(unittest.TestCase):
    """Verify SwayBackend has all required action methods."""

    REQUIRED_ACTIONS = [
        "focus_left", "focus_right", "focus_up", "focus_down",
        "move_left", "move_right", "move_up", "move_down",
        "resize_shrink_w", "resize_grow_w", "resize_shrink_h", "resize_grow_h",
        "workspace_prev", "workspace_next",
        "move_to_workspace_prev", "move_to_workspace_next",
        "close_window", "fullscreen", "toggle_floating",
        "focus_mode_toggle", "scratchpad_show", "scratchpad_move",
        "layout_toggle",
        "terminal", "launcher", "file_manager",
        "reload", "exit_wm",
        "screenshot_region", "screenshot_full",
        "volume_up", "volume_down", "volume_mute",
        "brightness_up", "brightness_down",
    ]

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()
        cls.backend = cls.mod.SwayBackend()

    def test_all_actions_present(self):
        """SwayBackend must implement all required action methods."""
        for action in self.REQUIRED_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(
                    callable(getattr(self.backend, action, None)),
                    f"SwayBackend missing method: {action}"
                )


class TestHyprlandBackendActions(unittest.TestCase):
    """Verify HyprlandBackend has all required action methods."""

    REQUIRED_ACTIONS = TestSwayBackendActions.REQUIRED_ACTIONS

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()
        cls.backend = cls.mod.HyprlandBackend()

    def test_all_actions_present(self):
        """HyprlandBackend must implement all required action methods."""
        for action in self.REQUIRED_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(
                    callable(getattr(self.backend, action, None)),
                    f"HyprlandBackend missing method: {action}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# GamepadState Dispatch Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestGamepadStateDispatch(unittest.TestCase):
    """Test that button combos dispatch correct backend actions."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def _make_state(self, profile=None):
        """Create a GamepadState with a mock backend."""
        backend = MagicMock()
        if profile is None:
            profile = self.mod.PROFILE_DECK
        return self.mod.GamepadState(backend, profile=profile), backend

    def _press(self, state, code):
        """Simulate a button press."""
        state.on_button(code, True)

    def _release(self, state, code):
        """Simulate a button release."""
        state.on_button(code, False)

    # ── Steam + button combos ──

    def test_steam_a_opens_terminal(self):
        """Steam + A must call terminal()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)   # Steam held
        self._press(state, self.mod.BTN_SOUTH)  # A pressed
        backend.terminal.assert_called_once()

    def test_steam_b_closes_window(self):
        """Steam + B must call close_window()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_EAST)
        backend.close_window.assert_called_once()

    def test_steam_x_opens_launcher(self):
        """Steam + X must call launcher()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_NORTH)
        backend.launcher.assert_called_once()

    def test_steam_y_opens_file_manager(self):
        """Steam + Y must call file_manager()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_WEST)
        backend.file_manager.assert_called_once()

    def test_steam_l1_prev_workspace(self):
        """Steam + L1 must call workspace_prev()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_TL)
        backend.workspace_prev.assert_called_once()

    def test_steam_r1_next_workspace(self):
        """Steam + R1 must call workspace_next()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_TR)
        backend.workspace_next.assert_called_once()

    def test_steam_start_fullscreen(self):
        """Steam + Start must call fullscreen()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_START)
        backend.fullscreen.assert_called_once()

    def test_steam_select_toggle_floating(self):
        """Steam + Select must call toggle_floating()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_SELECT)
        backend.toggle_floating.assert_called_once()

    def test_steam_l3_scratchpad(self):
        """Steam + L3 must call scratchpad_show()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_THUMBL)
        backend.scratchpad_show.assert_called_once()

    def test_steam_r3_reload(self):
        """Steam + R3 must call reload()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_THUMBR)
        backend.reload.assert_called_once()

    # ── D-pad combos ──

    def test_steam_dpad_focus(self):
        """Steam + D-pad must call focus_ methods."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)

        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.focus_left.assert_called()

        state.on_dpad(self.mod.ABS_HAT0X, 1)
        backend.focus_right.assert_called()

        state.on_dpad(self.mod.ABS_HAT0Y, -1)
        backend.focus_up.assert_called()

        state.on_dpad(self.mod.ABS_HAT0Y, 1)
        backend.focus_down.assert_called()

    def test_steam_l1_dpad_moves_window(self):
        """Steam + L1 + D-pad must call move_ methods."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_TL)

        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.move_left.assert_called()

        state.on_dpad(self.mod.ABS_HAT0X, 1)
        backend.move_right.assert_called()

    def test_steam_r1_dpad_moves_to_workspace(self):
        """Steam + R1 + D-pad must move to workspace prev/next."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_TR)

        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.move_to_workspace_prev.assert_called()

        state.on_dpad(self.mod.ABS_HAT0X, 1)
        backend.move_to_workspace_next.assert_called()

    def test_l1_dpad_resizes_window(self):
        """L1 + D-pad (no Steam) must call resize_ methods."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_TL)  # L1 without Steam

        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.resize_shrink_w.assert_called()

        state.on_dpad(self.mod.ABS_HAT0X, 1)
        backend.resize_grow_w.assert_called()

    def test_r1_dpad_switches_workspace(self):
        """R1 + D-pad (no Steam) must switch workspaces."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_TR)  # R1 without Steam

        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.workspace_prev.assert_called()

        state.on_dpad(self.mod.ABS_HAT0X, 1)
        backend.workspace_next.assert_called()

    # ── Back paddles ──

    def test_l4_volume_down(self):
        """L4 must call volume_down()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_TH1)
        backend.volume_down.assert_called_once()

    def test_r4_volume_up(self):
        """R4 must call volume_up()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_TH2)
        backend.volume_up.assert_called_once()

    def test_l5_brightness_down(self):
        """L5 must call brightness_down()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_TH3)
        backend.brightness_down.assert_called_once()

    def test_r5_brightness_up(self):
        """R5 must call brightness_up()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_TH4)
        backend.brightness_up.assert_called_once()

    # ── Exit combo ──

    def test_steam_start_select_exits(self):
        """Steam + Start + Select must call exit_wm()."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_START)
        # Reset combo tracking for the 3-button exit combo
        state._combo_fired.clear()
        self._press(state, self.mod.BTN_SELECT)
        backend.exit_wm.assert_called_once()

    # ── Combo deduplication ──

    def test_combo_not_fired_twice_while_held(self):
        """A combo must not fire again while the same buttons are held."""
        state, backend = self._make_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_SOUTH)
        self._press(state, self.mod.BTN_SOUTH)  # re-press (shouldn't happen, but test)
        self.assertEqual(backend.terminal.call_count, 1,
                         "Combo should only fire once while held")


# ═══════════════════════════════════════════════════════════════════════════
# Compositor Detection Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestCompositorDetection(unittest.TestCase):
    """Test auto-detection of compositor."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    @patch.dict(os.environ, {"SWAYSOCK": "/run/user/1000/sway-ipc.1000.sock"}, clear=False)
    def test_detects_sway_via_env(self):
        """Must detect sway when SWAYSOCK is set."""
        result = self.mod.detect_compositor()
        self.assertEqual(result, "sway")

    @patch.dict(os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "abc123"}, clear=False)
    def test_detects_hyprland_via_env(self):
        """Must detect hyprland when HYPRLAND_INSTANCE_SIGNATURE is set."""
        # Remove SWAYSOCK if present to avoid false detection
        env = os.environ.copy()
        env.pop("SWAYSOCK", None)
        with patch.dict(os.environ, env, clear=True):
            os.environ["HYPRLAND_INSTANCE_SIGNATURE"] = "abc123"
            result = self.mod.detect_compositor()
            self.assertEqual(result, "hyprland")


# ═══════════════════════════════════════════════════════════════════════════
# Button Mapping Completeness
# ═══════════════════════════════════════════════════════════════════════════
class TestButtonMappingCompleteness(unittest.TestCase):
    """Verify that the key Sway/Hyprland bindings are covered by gamepad combos."""

    EXPECTED_WM_ACTIONS = {
        "terminal",        # Mod+Return
        "close_window",    # Mod+Shift+q
        "launcher",        # Mod+d
        "file_manager",    # Mod+e
        "fullscreen",      # Mod+f
        "toggle_floating", # Mod+Shift+Space
        "focus_left",      # Mod+Left
        "focus_right",     # Mod+Right
        "focus_up",        # Mod+Up
        "focus_down",      # Mod+Down
        "move_left",       # Mod+Shift+Left
        "move_right",      # Mod+Shift+Right
        "move_up",         # Mod+Shift+Up
        "move_down",       # Mod+Shift+Down
        "workspace_prev",  # Mod+Alt+Left
        "workspace_next",  # Mod+Alt+Right
        "reload",          # Mod+Shift+c
        "exit_wm",         # Mod+Shift+e
        "volume_up",       # XF86AudioRaiseVolume
        "volume_down",     # XF86AudioLowerVolume
        "brightness_up",   # XF86MonBrightnessUp
        "brightness_down", # XF86MonBrightnessDown
        "scratchpad_show", # Mod+minus
        "resize_shrink_w", # resize mode
        "resize_grow_w",
        "layout_toggle",
    }

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def test_sway_backend_covers_all_actions(self):
        """SwayBackend must cover all expected WM actions."""
        backend = self.mod.SwayBackend()
        for action in self.EXPECTED_WM_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(
                    callable(getattr(backend, action, None)),
                    f"SwayBackend missing WM action: {action}"
                )

    def test_hyprland_backend_covers_all_actions(self):
        """HyprlandBackend must cover all expected WM actions."""
        backend = self.mod.HyprlandBackend()
        for action in self.EXPECTED_WM_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(
                    callable(getattr(backend, action, None)),
                    f"HyprlandBackend missing WM action: {action}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Trigger Handling Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestTriggerHandling(unittest.TestCase):
    """Test analog trigger threshold detection."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def test_l2_below_threshold(self):
        """L2 value below threshold should not be considered pressed."""
        state = self.mod.GamepadState(MagicMock())
        state.on_trigger(self.mod.ABS_Z, 50)
        self.assertFalse(state.l2_pressed)

    def test_l2_above_threshold(self):
        """L2 value above threshold should be considered pressed."""
        state = self.mod.GamepadState(MagicMock())
        state.on_trigger(self.mod.ABS_Z, 200)
        self.assertTrue(state.l2_pressed)

    def test_r2_below_threshold(self):
        """R2 value below threshold should not be considered pressed."""
        state = self.mod.GamepadState(MagicMock())
        state.on_trigger(self.mod.ABS_RZ, 50)
        self.assertFalse(state.r2_pressed)

    def test_r2_above_threshold(self):
        """R2 value above threshold should be considered pressed."""
        state = self.mod.GamepadState(MagicMock())
        state.on_trigger(self.mod.ABS_RZ, 200)
        self.assertTrue(state.r2_pressed)


# ═══════════════════════════════════════════════════════════════════════════
# InhibitChecker Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestInhibitChecker(unittest.TestCase):
    """Test game detection and inhibition logic."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def test_default_not_inhibited(self):
        """InhibitChecker should not be inhibited by default (no game)."""
        checker = self.mod.InhibitChecker("sway")
        # Mock _check_inhibit to return False (no game)
        checker._check_inhibit = lambda: False
        checker._last_check = 0
        self.assertFalse(checker.is_inhibited())

    def test_inhibited_when_game_detected(self):
        """InhibitChecker should be inhibited when _check_inhibit returns True."""
        checker = self.mod.InhibitChecker("sway")
        checker._check_inhibit = lambda: True
        checker._last_check = 0
        self.assertTrue(checker.is_inhibited())

    def test_manual_toggle_cycle(self):
        """Manual toggle should cycle: auto -> off -> on -> auto."""
        checker = self.mod.InhibitChecker("sway")

        # Initially auto
        self.assertIsNone(checker.manual_override)

        # First toggle -> manual OFF (inhibited)
        result = checker.toggle_manual()
        self.assertIn("DISABLED", result)
        self.assertTrue(checker.inhibited)

        # Second toggle -> manual ON (not inhibited)
        result = checker.toggle_manual()
        self.assertIn("ENABLED", result)
        self.assertFalse(checker.inhibited)

        # Third toggle -> auto
        result = checker.toggle_manual()
        self.assertIn("AUTO", result)
        self.assertIsNone(checker.manual_override)

    def test_manual_override_force_on(self):
        """When manual override is ON, is_inhibited must return False."""
        checker = self.mod.InhibitChecker("sway")
        checker.manual_override = True
        self.assertFalse(checker.is_inhibited())

    def test_manual_override_force_off(self):
        """When manual override is OFF, is_inhibited must return True."""
        checker = self.mod.InhibitChecker("sway")
        checker.manual_override = False
        self.assertTrue(checker.is_inhibited())

    def test_matches_steam(self):
        """_matches_game must match Steam app_id."""
        self.assertTrue(self.mod.InhibitChecker._matches_game("steam"))
        self.assertTrue(self.mod.InhibitChecker._matches_game("Steam"))

    def test_matches_gamescope(self):
        """_matches_game must match gamescope."""
        self.assertTrue(self.mod.InhibitChecker._matches_game("gamescope"))

    def test_matches_steam_app_prefix(self):
        """_matches_game must match steam_app_12345."""
        self.assertTrue(self.mod.InhibitChecker._matches_game("steam_app_12345"))

    def test_matches_proton(self):
        """_matches_game must match Proton processes."""
        self.assertTrue(self.mod.InhibitChecker._matches_game("proton"))

    def test_matches_emulators(self):
        """_matches_game must match known emulator names."""
        for emu in ["retroarch", "dolphin-emu", "pcsx2", "rpcs3", "yuzu"]:
            with self.subTest(emu=emu):
                self.assertTrue(self.mod.InhibitChecker._matches_game(emu))

    def test_does_not_match_desktop_apps(self):
        """_matches_game must NOT match desktop app names."""
        for app in ["foot", "chromium", "code", "pcmanfm", "wofi"]:
            with self.subTest(app=app):
                self.assertFalse(self.mod.InhibitChecker._matches_game(app))

    def test_known_desktop_app_detection(self):
        """_is_known_desktop_app must recognize madOS desktop apps."""
        self.assertTrue(self.mod.InhibitChecker._is_known_desktop_app("foot", ""))
        self.assertTrue(self.mod.InhibitChecker._is_known_desktop_app("chromium", ""))
        self.assertTrue(self.mod.InhibitChecker._is_known_desktop_app("mados-launcher", ""))
        self.assertFalse(self.mod.InhibitChecker._is_known_desktop_app("unknown_game", ""))

    def test_empty_app_id_not_game(self):
        """_matches_game must return False for empty string."""
        self.assertFalse(self.mod.InhibitChecker._matches_game(""))
        self.assertFalse(self.mod.InhibitChecker._matches_game(None))


# ═══════════════════════════════════════════════════════════════════════════
# Inhibition + GamepadState Integration Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestGamepadStateInhibition(unittest.TestCase):
    """Test that GamepadState respects inhibit checker during dispatch."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def _make_inhibited_state(self, is_inhibited=True, profile=None):
        """Create a GamepadState with a mock inhibit checker."""
        backend = MagicMock()
        checker = MagicMock()
        checker.is_inhibited.return_value = is_inhibited
        if profile is None:
            profile = self.mod.PROFILE_DECK
        state = self.mod.GamepadState(backend, inhibit_checker=checker, profile=profile)
        return state, backend, checker

    def _press(self, state, code):
        state.on_button(code, True)

    def test_wm_binds_blocked_when_inhibited(self):
        """Steam+A should NOT call terminal() when inhibited."""
        state, backend, _ = self._make_inhibited_state(True)
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_SOUTH)
        backend.terminal.assert_not_called()

    def test_wm_binds_work_when_not_inhibited(self):
        """Steam+A should call terminal() when NOT inhibited."""
        state, backend, _ = self._make_inhibited_state(False)
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_SOUTH)
        backend.terminal.assert_called_once()

    def test_back_paddles_work_when_inhibited(self):
        """L4/R4 (volume) should ALWAYS work, even when inhibited."""
        state, backend, _ = self._make_inhibited_state(True)
        self._press(state, self.mod.BTN_TH1)  # L4 -> volume down
        backend.volume_down.assert_called_once()

        self._press(state, self.mod.BTN_TH2)  # R4 -> volume up
        backend.volume_up.assert_called_once()

    def test_brightness_paddles_work_when_inhibited(self):
        """L5/R5 (brightness) should ALWAYS work, even when inhibited."""
        state, backend, _ = self._make_inhibited_state(True)
        self._press(state, self.mod.BTN_TH3)  # L5 -> brightness down
        backend.brightness_down.assert_called_once()

        self._press(state, self.mod.BTN_TH4)  # R5 -> brightness up
        backend.brightness_up.assert_called_once()

    def test_toggle_combo_works_when_inhibited(self):
        """Steam+L3+R3 toggle should ALWAYS work, even when inhibited."""
        state, backend, checker = self._make_inhibited_state(True)
        checker.toggle_manual.return_value = "MANUALLY ENABLED"

        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_THUMBL)
        self._press(state, self.mod.BTN_THUMBR)
        checker.toggle_manual.assert_called_once()

    def test_dpad_blocked_when_inhibited(self):
        """D-pad actions should be blocked when inhibited."""
        state, backend, _ = self._make_inhibited_state(True)
        self._press(state, self.mod.BTN_MODE)
        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.focus_left.assert_not_called()

    def test_dpad_works_when_not_inhibited(self):
        """D-pad actions should work when not inhibited."""
        state, backend, _ = self._make_inhibited_state(False)
        self._press(state, self.mod.BTN_MODE)
        state.on_dpad(self.mod.ABS_HAT0X, -1)
        backend.focus_left.assert_called()

    def test_select_screenshot_blocked_when_inhibited(self):
        """Select (screenshot) should be blocked when inhibited."""
        state, backend, _ = self._make_inhibited_state(True)
        self._press(state, self.mod.BTN_SELECT)
        backend.screenshot_region.assert_not_called()

    def test_close_window_blocked_when_inhibited(self):
        """Steam+B (close window) should be blocked when inhibited."""
        state, backend, _ = self._make_inhibited_state(True)
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_EAST)
        backend.close_window.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Gamepad Profile Detection Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestGamepadProfileDetection(unittest.TestCase):
    """Test detect_gamepad_profile() with various device configurations."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def _make_device(self, name, has_paddles=False, has_share=False):
        """Create a fake device with given name and capabilities."""
        dev = MagicMock()
        dev.name = name
        keys = [
            self.mod.BTN_SOUTH, self.mod.BTN_EAST,
            self.mod.BTN_NORTH, self.mod.BTN_WEST,
            self.mod.BTN_TL, self.mod.BTN_TR,
            self.mod.BTN_START, self.mod.BTN_SELECT,
            self.mod.BTN_MODE,
        ]
        if has_paddles:
            keys.extend([self.mod.BTN_TH1, self.mod.BTN_TH2,
                         self.mod.BTN_TH3, self.mod.BTN_TH4])
        if has_share:
            keys.append(self.mod.KEY_RECORD)
        ecodes_mod = self.mod.evdev.ecodes
        dev.capabilities.return_value = {
            ecodes_mod.EV_KEY: keys,
            ecodes_mod.EV_ABS: [ecodes_mod.ABS_HAT0X, ecodes_mod.ABS_HAT0Y],
        }
        return dev

    def test_deck_detected_by_name_and_paddles(self):
        """Steam Deck should be detected by name + back paddles."""
        dev = self._make_device("Valve Software Steam Controller", has_paddles=True)
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_DECK)

    def test_deck_detected_by_paddles_alone(self):
        """Device with back paddles but unknown name → still deck profile."""
        dev = self._make_device("Unknown Gamepad With Paddles", has_paddles=True)
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_DECK)

    def test_xbox_detected_by_name(self):
        """Xbox controller detected by name pattern."""
        dev = self._make_device("Xbox Series X Controller")
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_XBOX)

    def test_xbox_one_detected(self):
        """Xbox One controller detected by name pattern."""
        dev = self._make_device("Microsoft X-Box One pad")
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_XBOX)

    def test_xbox_360_detected(self):
        """Xbox 360 controller detected by name pattern."""
        dev = self._make_device("Xbox 360 Wireless Receiver")
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_XBOX)

    def test_xbox_wireless_detected(self):
        """Xbox Wireless controller detected by name pattern."""
        dev = self._make_device("Xbox Wireless Controller")
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_XBOX)

    def test_generic_for_unknown(self):
        """Unknown gamepad should return generic profile."""
        dev = self._make_device("8BitDo Pro 2")
        result = self.mod.detect_gamepad_profile([dev])
        self.assertEqual(result, self.mod.PROFILE_GENERIC)

    def test_empty_device_list(self):
        """Empty device list should return generic profile."""
        result = self.mod.detect_gamepad_profile([])
        self.assertEqual(result, self.mod.PROFILE_GENERIC)


# ═══════════════════════════════════════════════════════════════════════════
# Xbox-Specific Dispatch Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestXboxDispatch(unittest.TestCase):
    """Test Xbox-specific button combos and trigger-based media controls."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def _make_xbox_state(self, inhibit_checker=None):
        """Create a GamepadState with xbox profile and mock backend."""
        backend = MagicMock()
        state = self.mod.GamepadState(backend, inhibit_checker=inhibit_checker,
                                       profile=self.mod.PROFILE_XBOX)
        return state, backend

    def _press(self, state, code):
        state.on_button(code, True)

    def _release(self, state, code):
        state.on_button(code, False)

    # ── Share button ──

    def test_share_button_screenshot(self):
        """Share button (KEY_RECORD) should trigger screenshot_region."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.KEY_RECORD)
        backend.screenshot_region.assert_called_once()

    def test_share_button_not_during_xbox_held(self):
        """Share button should NOT fire when Xbox button is held."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.KEY_RECORD)
        backend.screenshot_region.assert_not_called()

    def test_share_button_works_when_inhibited(self):
        """Share button should work even when inhibited (media key)."""
        checker = MagicMock()
        checker.is_inhibited.return_value = True
        state, backend = self._make_xbox_state(inhibit_checker=checker)
        self._press(state, self.mod.KEY_RECORD)
        backend.screenshot_region.assert_called_once()

    # ── LT + D-pad → Volume ──

    def test_lt_dpad_up_volume_up(self):
        """LT + D-pad Up should call volume_up on Xbox profile."""
        state, backend = self._make_xbox_state()
        state.on_trigger(self.mod.ABS_Z, 200)  # LT pressed
        state.on_dpad(self.mod.ABS_HAT0Y, -1)  # D-pad Up
        backend.volume_up.assert_called()

    def test_lt_dpad_down_volume_down(self):
        """LT + D-pad Down should call volume_down on Xbox profile."""
        state, backend = self._make_xbox_state()
        state.on_trigger(self.mod.ABS_Z, 200)  # LT pressed
        state.on_dpad(self.mod.ABS_HAT0Y, 1)   # D-pad Down
        backend.volume_down.assert_called()

    def test_lt_dpad_horizontal_no_volume(self):
        """LT + D-pad Left/Right should NOT trigger volume on Xbox."""
        state, backend = self._make_xbox_state()
        state.on_trigger(self.mod.ABS_Z, 200)  # LT pressed
        state.on_dpad(self.mod.ABS_HAT0X, -1)  # D-pad Left
        backend.volume_up.assert_not_called()
        backend.volume_down.assert_not_called()

    # ── RT + D-pad → Brightness ──

    def test_rt_dpad_up_brightness_up(self):
        """RT + D-pad Up should call brightness_up on Xbox profile."""
        state, backend = self._make_xbox_state()
        state.on_trigger(self.mod.ABS_RZ, 200) # RT pressed
        state.on_dpad(self.mod.ABS_HAT0Y, -1)  # D-pad Up
        backend.brightness_up.assert_called()

    def test_rt_dpad_down_brightness_down(self):
        """RT + D-pad Down should call brightness_down on Xbox profile."""
        state, backend = self._make_xbox_state()
        state.on_trigger(self.mod.ABS_RZ, 200) # RT pressed
        state.on_dpad(self.mod.ABS_HAT0Y, 1)   # D-pad Down
        backend.brightness_down.assert_called()

    def test_rt_dpad_horizontal_no_brightness(self):
        """RT + D-pad Left/Right should NOT trigger brightness on Xbox."""
        state, backend = self._make_xbox_state()
        state.on_trigger(self.mod.ABS_RZ, 200) # RT pressed
        state.on_dpad(self.mod.ABS_HAT0X, 1)   # D-pad Right
        backend.brightness_up.assert_not_called()
        backend.brightness_down.assert_not_called()

    # ── LT/RT media combos work even when inhibited ──

    def test_lt_volume_works_when_inhibited(self):
        """LT + D-pad volume should work even when inhibited (Xbox)."""
        checker = MagicMock()
        checker.is_inhibited.return_value = True
        state, backend = self._make_xbox_state(inhibit_checker=checker)
        state.on_trigger(self.mod.ABS_Z, 200)  # LT pressed
        state.on_dpad(self.mod.ABS_HAT0Y, -1)  # D-pad Up
        backend.volume_up.assert_called()

    def test_rt_brightness_works_when_inhibited(self):
        """RT + D-pad brightness should work even when inhibited (Xbox)."""
        checker = MagicMock()
        checker.is_inhibited.return_value = True
        state, backend = self._make_xbox_state(inhibit_checker=checker)
        state.on_trigger(self.mod.ABS_RZ, 200) # RT pressed
        state.on_dpad(self.mod.ABS_HAT0Y, -1)  # D-pad Up
        backend.brightness_up.assert_called()

    # ── Xbox button combos (same as Steam Deck) ──

    def test_xbox_a_terminal(self):
        """Xbox + A should call terminal() on Xbox profile."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_SOUTH)
        backend.terminal.assert_called_once()

    def test_xbox_b_close(self):
        """Xbox + B should call close_window() on Xbox profile."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_EAST)
        backend.close_window.assert_called_once()

    def test_xbox_x_launcher(self):
        """Xbox + X should call launcher() on Xbox profile."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_NORTH)
        backend.launcher.assert_called_once()

    def test_xbox_start_select_exits(self):
        """Xbox + Start + Select should call exit_wm() on Xbox profile."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_START)
        state._combo_fired.clear()
        self._press(state, self.mod.BTN_SELECT)
        backend.exit_wm.assert_called_once()

    def test_xbox_l3_r3_toggle(self):
        """Xbox + LS + RS should toggle manual override on Xbox profile."""
        checker = MagicMock()
        checker.is_inhibited.return_value = False
        checker.toggle_manual.return_value = "MANUALLY DISABLED"
        state, backend = self._make_xbox_state(inhibit_checker=checker)
        self._press(state, self.mod.BTN_MODE)
        self._press(state, self.mod.BTN_THUMBL)
        self._press(state, self.mod.BTN_THUMBR)
        checker.toggle_manual.assert_called_once()

    # ── Xbox back paddles should NOT fire (Xbox lacks them) ──

    def test_xbox_no_back_paddle_volume(self):
        """BTN_TH1/TH2 should NOT trigger volume on Xbox profile."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_TH1)
        backend.volume_down.assert_not_called()
        self._press(state, self.mod.BTN_TH2)
        backend.volume_up.assert_not_called()

    def test_xbox_no_back_paddle_brightness(self):
        """BTN_TH3/TH4 should NOT trigger brightness on Xbox profile."""
        state, backend = self._make_xbox_state()
        self._press(state, self.mod.BTN_TH3)
        backend.brightness_down.assert_not_called()
        self._press(state, self.mod.BTN_TH4)
        backend.brightness_up.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Deck-Specific Dispatch Tests (back paddles)
# ═══════════════════════════════════════════════════════════════════════════
class TestDeckDispatch(unittest.TestCase):
    """Test that Deck-specific back paddle actions work with deck profile."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def _make_deck_state(self):
        backend = MagicMock()
        state = self.mod.GamepadState(backend, profile=self.mod.PROFILE_DECK)
        return state, backend

    def _press(self, state, code):
        state.on_button(code, True)

    def test_l4_volume_down_deck(self):
        """L4 must call volume_down() on deck profile."""
        state, backend = self._make_deck_state()
        self._press(state, self.mod.BTN_TH1)
        backend.volume_down.assert_called_once()

    def test_r4_volume_up_deck(self):
        """R4 must call volume_up() on deck profile."""
        state, backend = self._make_deck_state()
        self._press(state, self.mod.BTN_TH2)
        backend.volume_up.assert_called_once()

    def test_l5_brightness_down_deck(self):
        """L5 must call brightness_down() on deck profile."""
        state, backend = self._make_deck_state()
        self._press(state, self.mod.BTN_TH3)
        backend.brightness_down.assert_called_once()

    def test_r5_brightness_up_deck(self):
        """R5 must call brightness_up() on deck profile."""
        state, backend = self._make_deck_state()
        self._press(state, self.mod.BTN_TH4)
        backend.brightness_up.assert_called_once()

    def test_lt_dpad_does_not_volume_on_deck(self):
        """LT + D-pad should NOT trigger volume on deck (use paddles instead)."""
        state, backend = self._make_deck_state()
        state.on_trigger(self.mod.ABS_Z, 200)
        state.on_dpad(self.mod.ABS_HAT0Y, -1)
        backend.volume_up.assert_not_called()
        backend.volume_down.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Generic Profile Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestGenericProfileDispatch(unittest.TestCase):
    """Test generic profile behaves like Xbox (LT/RT media, no back paddles)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def _make_generic_state(self):
        backend = MagicMock()
        state = self.mod.GamepadState(backend, profile=self.mod.PROFILE_GENERIC)
        return state, backend

    def test_lt_dpad_volume_generic(self):
        """LT + D-pad should control volume on generic profile."""
        state, backend = self._make_generic_state()
        state.on_trigger(self.mod.ABS_Z, 200)
        state.on_dpad(self.mod.ABS_HAT0Y, -1)
        backend.volume_up.assert_called()

    def test_rt_dpad_brightness_generic(self):
        """RT + D-pad should control brightness on generic profile."""
        state, backend = self._make_generic_state()
        state.on_trigger(self.mod.ABS_RZ, 200)
        state.on_dpad(self.mod.ABS_HAT0Y, -1)
        backend.brightness_up.assert_called()

    def test_share_button_screenshot_generic(self):
        """Share button should trigger screenshot on generic profile."""
        state, backend = self._make_generic_state()
        state.on_button(self.mod.KEY_RECORD, True)
        backend.screenshot_region.assert_called_once()

    def test_no_back_paddles_generic(self):
        """BTN_TH1-4 should NOT trigger on generic profile."""
        state, backend = self._make_generic_state()
        state.on_button(self.mod.BTN_TH1, True)
        backend.volume_down.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Profile Constants Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestProfileConstants(unittest.TestCase):
    """Verify profile constants and KEY_RECORD are defined."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_gamepad_module()

    def test_profile_deck_defined(self):
        """PROFILE_DECK constant must be defined."""
        self.assertEqual(self.mod.PROFILE_DECK, "deck")

    def test_profile_xbox_defined(self):
        """PROFILE_XBOX constant must be defined."""
        self.assertEqual(self.mod.PROFILE_XBOX, "xbox")

    def test_profile_generic_defined(self):
        """PROFILE_GENERIC constant must be defined."""
        self.assertEqual(self.mod.PROFILE_GENERIC, "generic")

    def test_key_record_defined(self):
        """KEY_RECORD constant must be defined (Xbox Share button)."""
        self.assertEqual(self.mod.KEY_RECORD, 167)

    def test_version_is_2(self):
        """VERSION must be 2.x for multi-controller support."""
        self.assertTrue(self.mod.VERSION.startswith("2."),
                        f"VERSION should be 2.x, got {self.mod.VERSION}")


if __name__ == "__main__":
    unittest.main()
