"""
madOS Audio Equalizer - Preset Management
==========================================

Manages built-in and custom user equalizer presets.

Built-in presets provide predefined gain values for 8 frequency bands
(60Hz, 170Hz, 310Hz, 600Hz, 1kHz, 3kHz, 6kHz, 12kHz).

Custom presets are stored in ~/.config/mados/equalizer/presets.json
and can be created, loaded, and deleted by the user.
"""

import json
import os
from pathlib import Path


# Frequency bands in Hz (used as reference throughout the application)
FREQUENCY_BANDS = [60, 170, 310, 600, 1000, 3000, 6000, 12000]

# Display labels for each frequency band
BAND_LABELS = ["60", "170", "310", "600", "1k", "3k", "6k", "12k"]

# Translation keys for each frequency band
BAND_KEYS = [
    "band_60",
    "band_170",
    "band_310",
    "band_600",
    "band_1k",
    "band_3k",
    "band_6k",
    "band_12k",
]

# Gain range in dB
GAIN_MIN = -12.0
GAIN_MAX = 12.0
GAIN_DEFAULT = 0.0

# Built-in presets with gain values for each of the 8 bands (in dB)
BUILTIN_PRESETS = {
    "flat": {
        "name": "Flat",
        "key": "flat",
        "gains": [0, 0, 0, 0, 0, 0, 0, 0],
        "builtin": True,
    },
    "rock": {
        "name": "Rock",
        "key": "rock",
        "gains": [4, 3, 1, 0, -1, 1, 3, 4],
        "builtin": True,
    },
    "pop": {
        "name": "Pop",
        "key": "pop",
        "gains": [-1, 2, 4, 4, 2, 0, -1, -2],
        "builtin": True,
    },
    "jazz": {
        "name": "Jazz",
        "key": "jazz",
        "gains": [3, 2, 1, 2, -1, -1, 0, 2],
        "builtin": True,
    },
    "classical": {
        "name": "Classical",
        "key": "classical",
        "gains": [4, 3, 2, 1, -1, 0, 2, 3],
        "builtin": True,
    },
    "bass_boost": {
        "name": "Bass Boost",
        "key": "bass_boost",
        "gains": [6, 5, 4, 2, 0, 0, 0, 0],
        "builtin": True,
    },
    "treble_boost": {
        "name": "Treble Boost",
        "key": "treble_boost",
        "gains": [0, 0, 0, 0, 1, 3, 5, 6],
        "builtin": True,
    },
    "vocal": {
        "name": "Vocal",
        "key": "vocal",
        "gains": [-2, 0, 2, 4, 4, 2, 0, -2],
        "builtin": True,
    },
    "electronic": {
        "name": "Electronic",
        "key": "electronic",
        "gains": [5, 4, 1, 0, -2, 1, 3, 5],
        "builtin": True,
    },
    "acoustic": {
        "name": "Acoustic",
        "key": "acoustic",
        "gains": [3, 2, 1, 0, 1, 1, 2, 3],
        "builtin": True,
    },
}

# Ordered list of built-in preset keys for consistent UI display
BUILTIN_PRESET_ORDER = [
    "flat",
    "rock",
    "pop",
    "jazz",
    "classical",
    "bass_boost",
    "treble_boost",
    "vocal",
    "electronic",
    "acoustic",
]


class PresetManager:
    """Manages equalizer presets including built-in and user-defined presets.

    Attributes:
        config_dir: Path to the configuration directory.
        presets_file: Path to the custom presets JSON file.
        custom_presets: Dictionary of user-defined presets.
    """

    def __init__(self):
        """Initialize the PresetManager and load custom presets from disk."""
        self.config_dir = Path.home() / ".config" / "mados" / "equalizer"
        self.presets_file = self.config_dir / "presets.json"
        self.custom_presets = {}
        self._load_custom_presets()

    def _ensure_config_dir(self):
        """Create the configuration directory if it does not exist."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create config directory: {e}")

    def _load_custom_presets(self):
        """Load custom presets from the JSON file on disk.

        If the file does not exist or is corrupt, starts with an empty set.
        """
        if not self.presets_file.exists():
            self.custom_presets = {}
            return

        try:
            with open(self.presets_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.custom_presets = {}
            for key, preset in data.items():
                # Validate preset structure
                if isinstance(preset, dict) and "gains" in preset:
                    gains = preset["gains"]
                    if isinstance(gains, list) and len(gains) == 8:
                        # Clamp gains to valid range
                        gains = [max(GAIN_MIN, min(GAIN_MAX, float(g))) for g in gains]
                        self.custom_presets[key] = {
                            "name": preset.get("name", key),
                            "key": key,
                            "gains": gains,
                            "builtin": False,
                        }
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load custom presets: {e}")
            self.custom_presets = {}

    def _save_custom_presets(self):
        """Save custom presets to the JSON file on disk.

        Returns:
            True if save was successful, False otherwise.
        """
        self._ensure_config_dir()
        try:
            # Prepare serializable data
            data = {}
            for key, preset in self.custom_presets.items():
                data[key] = {
                    "name": preset["name"],
                    "gains": preset["gains"],
                }

            with open(self.presets_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            print(f"Error: Could not save custom presets: {e}")
            return False

    def get_builtin_presets(self):
        """Return the ordered list of built-in presets.

        Returns:
            List of preset dictionaries in display order.
        """
        return [BUILTIN_PRESETS[key] for key in BUILTIN_PRESET_ORDER]

    def get_custom_presets(self):
        """Return the list of user-defined presets sorted by name.

        Returns:
            List of preset dictionaries sorted alphabetically by name.
        """
        return sorted(self.custom_presets.values(), key=lambda p: p["name"].lower())

    def get_all_presets(self):
        """Return all presets with built-in presets first, then custom.

        Returns:
            List of all preset dictionaries.
        """
        return self.get_builtin_presets() + self.get_custom_presets()

    def get_preset(self, key):
        """Get a preset by its key.

        Args:
            key: The preset key to look up.

        Returns:
            The preset dictionary, or None if not found.
        """
        if key in BUILTIN_PRESETS:
            return BUILTIN_PRESETS[key]
        return self.custom_presets.get(key)

    def save_custom_preset(self, name, gains):
        """Save a new custom preset or update an existing one.

        Args:
            name: The display name for the preset.
            gains: List of 8 gain values in dB.

        Returns:
            Tuple of (success: bool, message: str, key: str).
            The key is the sanitized internal key for the preset.
        """
        if not name or not name.strip():
            return False, "Preset name cannot be empty", ""

        name = name.strip()

        # Generate a key from the name
        key = self._name_to_key(name)

        # Check if this would overwrite a built-in preset
        if key in BUILTIN_PRESETS:
            return False, "preset_exists", key

        # Validate gains
        if not isinstance(gains, (list, tuple)) or len(gains) != 8:
            return False, "Invalid gain values", key

        # Clamp gains to valid range
        clamped_gains = [max(GAIN_MIN, min(GAIN_MAX, float(g))) for g in gains]

        self.custom_presets[key] = {
            "name": name,
            "key": key,
            "gains": clamped_gains,
            "builtin": False,
        }

        if self._save_custom_presets():
            return True, "preset_saved", key
        else:
            return False, "error", key

    def delete_custom_preset(self, key):
        """Delete a custom preset by its key.

        Built-in presets cannot be deleted.

        Args:
            key: The preset key to delete.

        Returns:
            Tuple of (success: bool, message: str).
        """
        if key in BUILTIN_PRESETS:
            return False, "Cannot delete built-in presets"

        if key not in self.custom_presets:
            return False, "Preset not found"

        del self.custom_presets[key]

        if self._save_custom_presets():
            return True, "preset_deleted"
        else:
            return False, "error"

    def is_builtin(self, key):
        """Check if a preset key belongs to a built-in preset.

        Args:
            key: The preset key to check.

        Returns:
            True if the key is a built-in preset, False otherwise.
        """
        return key in BUILTIN_PRESETS

    def preset_exists(self, name):
        """Check if a preset with the given name already exists.

        Args:
            name: The preset name to check.

        Returns:
            True if a preset with this name exists (built-in or custom).
        """
        key = self._name_to_key(name.strip())
        return key in BUILTIN_PRESETS or key in self.custom_presets

    @staticmethod
    def _name_to_key(name):
        """Convert a preset display name to an internal key.

        Converts to lowercase, replaces spaces with underscores,
        and removes non-alphanumeric characters.

        Args:
            name: The display name to convert.

        Returns:
            The sanitized key string.
        """
        key = name.lower().strip()
        key = key.replace(" ", "_")
        key = "".join(c for c in key if c.isalnum() or c == "_")
        return key or "unnamed"

    def get_flat_gains(self):
        """Return flat (all zeros) gain values.

        Returns:
            List of 8 zero values.
        """
        return [GAIN_DEFAULT] * 8
