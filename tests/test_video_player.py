#!/usr/bin/env python3
"""
Tests for madOS Video Player playlist module.

Validates playlist management including add/remove, navigation,
shuffle, repeat modes, and media file detection helpers.

These tests use a temporary directory with test files and do not require
GTK or a display server.
"""

import sys
import os
import tempfile
import shutil
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so video player modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks(extra_modules=("Gst", "GstVideo"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "lib")
sys.path.insert(0, LIB_DIR)

from mados_video_player.playlist import (
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    ALL_MEDIA_EXTENSIONS,
    is_media_file,
    is_video_file,
    scan_directory,
    Playlist,
    RepeatMode,
)
from mados_video_player.database import PlaylistDB


# ═══════════════════════════════════════════════════════════════════════════
# Extension sets
# ═══════════════════════════════════════════════════════════════════════════
class TestExtensionSets(unittest.TestCase):
    """Validate the sets of supported extensions."""

    def test_video_extensions_non_empty(self):
        self.assertGreater(len(VIDEO_EXTENSIONS), 0)

    def test_audio_extensions_non_empty(self):
        self.assertGreater(len(AUDIO_EXTENSIONS), 0)

    def test_all_media_is_union(self):
        self.assertEqual(ALL_MEDIA_EXTENSIONS, VIDEO_EXTENSIONS | AUDIO_EXTENSIONS)

    def test_common_video_formats_supported(self):
        for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
            self.assertIn(ext, VIDEO_EXTENSIONS, f"{ext} should be in VIDEO_EXTENSIONS")

    def test_common_audio_formats_supported(self):
        for ext in [".mp3", ".flac", ".ogg", ".wav"]:
            self.assertIn(ext, AUDIO_EXTENSIONS, f"{ext} should be in AUDIO_EXTENSIONS")

    def test_extensions_lowercase(self):
        for ext in ALL_MEDIA_EXTENSIONS:
            self.assertTrue(ext.startswith("."), f"Extension {ext} must start with '.'")
            self.assertEqual(ext, ext.lower(), f"Extension {ext} must be lowercase")

    def test_no_overlap(self):
        overlap = VIDEO_EXTENSIONS & AUDIO_EXTENSIONS
        self.assertEqual(len(overlap), 0, f"Overlapping extensions: {overlap}")


# ═══════════════════════════════════════════════════════════════════════════
# File Detection
# ═══════════════════════════════════════════════════════════════════════════
class TestFileDetection(unittest.TestCase):
    """Validate file type detection helpers."""

    def test_is_media_file_video(self):
        self.assertTrue(is_media_file("/path/to/video.mp4"))
        self.assertTrue(is_media_file("/path/to/video.MKV"))

    def test_is_media_file_audio(self):
        self.assertTrue(is_media_file("/path/to/song.mp3"))
        self.assertTrue(is_media_file("/path/to/song.FLAC"))

    def test_is_media_file_non_media(self):
        self.assertFalse(is_media_file("/path/to/document.pdf"))
        self.assertFalse(is_media_file("/path/to/image.png"))
        self.assertFalse(is_media_file("/path/to/file.txt"))

    def test_is_video_file(self):
        self.assertTrue(is_video_file("/path/to/video.mp4"))
        self.assertFalse(is_video_file("/path/to/song.mp3"))

    def test_is_media_file_case_insensitive(self):
        self.assertTrue(is_media_file("/path/VIDEO.AVI"))
        self.assertTrue(is_media_file("/path/MuSiC.FlaC"))


# ═══════════════════════════════════════════════════════════════════════════
# Scan Directory
# ═══════════════════════════════════════════════════════════════════════════
class TestScanDirectory(unittest.TestCase):
    """Validate directory scanning for media files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mados_vp_test_")
        # Create test files
        for name in ["video.mp4", "movie.mkv", "song.mp3", "readme.txt", "photo.jpg"]:
            open(os.path.join(self.tmpdir, name), "w").close()
        # Create subdirectory with files
        subdir = os.path.join(self.tmpdir, "subdir")
        os.makedirs(subdir)
        for name in ["clip.avi", "track.flac"]:
            open(os.path.join(subdir, name), "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_scan_flat(self):
        results = scan_directory(self.tmpdir, recursive=False)
        names = [os.path.basename(f) for f in results]
        self.assertIn("video.mp4", names)
        self.assertIn("movie.mkv", names)
        self.assertIn("song.mp3", names)
        self.assertNotIn("readme.txt", names)
        self.assertNotIn("photo.jpg", names)
        self.assertNotIn("clip.avi", names)

    def test_scan_recursive(self):
        results = scan_directory(self.tmpdir, recursive=True)
        names = [os.path.basename(f) for f in results]
        self.assertIn("video.mp4", names)
        self.assertIn("clip.avi", names)
        self.assertIn("track.flac", names)

    def test_scan_results_sorted(self):
        results = scan_directory(self.tmpdir)
        self.assertEqual(results, sorted(results))

    def test_scan_nonexistent_directory(self):
        results = scan_directory("/nonexistent/path")
        self.assertEqual(results, [])

    def test_scan_returns_absolute_paths(self):
        results = scan_directory(self.tmpdir)
        for path in results:
            self.assertTrue(os.path.isabs(path))


# ═══════════════════════════════════════════════════════════════════════════
# Playlist - Basic Operations
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylistBasic(unittest.TestCase):
    """Test basic playlist operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mados_vp_test_")
        self.files = []
        for name in ["video1.mp4", "video2.mkv", "video3.avi", "song.mp3"]:
            path = os.path.join(self.tmpdir, name)
            open(path, "w").close()
            self.files.append(path)
        self.playlist = Playlist()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_empty_playlist(self):
        self.assertTrue(self.playlist.is_empty)
        self.assertEqual(self.playlist.count, 0)
        self.assertIsNone(self.playlist.current)
        self.assertEqual(self.playlist.current_index, -1)

    def test_add_file(self):
        result = self.playlist.add_file(self.files[0])
        self.assertTrue(result)
        self.assertEqual(self.playlist.count, 1)
        self.assertFalse(self.playlist.is_empty)
        self.assertEqual(self.playlist.current_index, 0)

    def test_add_non_media_file(self):
        txt_file = os.path.join(self.tmpdir, "readme.txt")
        open(txt_file, "w").close()
        result = self.playlist.add_file(txt_file)
        self.assertFalse(result)
        self.assertEqual(self.playlist.count, 0)

    def test_add_nonexistent_file(self):
        result = self.playlist.add_file("/nonexistent/file.mp4")
        self.assertFalse(result)

    def test_add_multiple_files(self):
        for f in self.files:
            self.playlist.add_file(f)
        self.assertEqual(self.playlist.count, 4)
        self.assertEqual(self.playlist.current_index, 0)

    def test_add_directory(self):
        count = self.playlist.add_directory(self.tmpdir)
        self.assertGreater(count, 0)
        self.assertEqual(self.playlist.count, count)

    def test_clear(self):
        for f in self.files:
            self.playlist.add_file(f)
        self.playlist.clear()
        self.assertTrue(self.playlist.is_empty)
        self.assertEqual(self.playlist.current_index, -1)

    def test_remove_item(self):
        for f in self.files:
            self.playlist.add_file(f)
        initial_count = self.playlist.count
        result = self.playlist.remove(1)
        self.assertTrue(result)
        self.assertEqual(self.playlist.count, initial_count - 1)

    def test_remove_invalid_index(self):
        self.assertFalse(self.playlist.remove(-1))
        self.assertFalse(self.playlist.remove(0))

    def test_remove_before_current(self):
        for f in self.files:
            self.playlist.add_file(f)
        self.playlist.select(2)
        self.playlist.remove(0)
        self.assertEqual(self.playlist.current_index, 1)

    def test_select(self):
        for f in self.files:
            self.playlist.add_file(f)
        result = self.playlist.select(2)
        self.assertIsNotNone(result)
        self.assertEqual(self.playlist.current_index, 2)

    def test_select_invalid(self):
        result = self.playlist.select(99)
        self.assertIsNone(result)

    def test_get_display_name(self):
        self.playlist.add_file(self.files[0])
        name = self.playlist.get_display_name()
        self.assertEqual(name, "video1.mp4")

    def test_get_display_name_empty(self):
        name = self.playlist.get_display_name()
        self.assertEqual(name, "")


# ═══════════════════════════════════════════════════════════════════════════
# Playlist - Navigation
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylistNavigation(unittest.TestCase):
    """Test playlist navigation (next/previous)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mados_vp_test_")
        self.playlist = Playlist()
        for name in ["a.mp4", "b.mp4", "c.mp4", "d.mp4"]:
            path = os.path.join(self.tmpdir, name)
            open(path, "w").close()
            self.playlist.add_file(path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_next(self):
        result = self.playlist.next()
        self.assertIsNotNone(result)
        self.assertEqual(self.playlist.current_index, 1)

    def test_next_at_end_no_repeat(self):
        self.playlist.select(3)
        result = self.playlist.next()
        self.assertIsNone(result)
        self.assertEqual(self.playlist.current_index, 3)

    def test_next_at_end_repeat_all(self):
        self.playlist.repeat_mode = RepeatMode.ALL
        self.playlist.select(3)
        result = self.playlist.next()
        self.assertIsNotNone(result)
        self.assertEqual(self.playlist.current_index, 0)

    def test_next_repeat_one(self):
        self.playlist.repeat_mode = RepeatMode.ONE
        current = self.playlist.current
        result = self.playlist.next()
        self.assertEqual(result, current)

    def test_previous(self):
        self.playlist.select(2)
        result = self.playlist.previous()
        self.assertIsNotNone(result)
        self.assertEqual(self.playlist.current_index, 1)

    def test_previous_at_start_no_repeat(self):
        result = self.playlist.previous()
        self.assertIsNone(result)
        self.assertEqual(self.playlist.current_index, 0)

    def test_previous_at_start_repeat_all(self):
        self.playlist.repeat_mode = RepeatMode.ALL
        result = self.playlist.previous()
        self.assertIsNotNone(result)
        self.assertEqual(self.playlist.current_index, 3)

    def test_next_empty_playlist(self):
        empty = Playlist()
        self.assertIsNone(empty.next())

    def test_previous_empty_playlist(self):
        empty = Playlist()
        self.assertIsNone(empty.previous())


# ═══════════════════════════════════════════════════════════════════════════
# Playlist - Repeat and Shuffle
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylistRepeatShuffle(unittest.TestCase):
    """Test repeat mode cycling and shuffle toggle."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mados_vp_test_")
        self.playlist = Playlist()
        for name in ["a.mp4", "b.mp4", "c.mp4"]:
            path = os.path.join(self.tmpdir, name)
            open(path, "w").close()
            self.playlist.add_file(path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_cycle_repeat(self):
        self.assertEqual(self.playlist.repeat_mode, RepeatMode.NONE)
        self.assertEqual(self.playlist.cycle_repeat(), RepeatMode.ALL)
        self.assertEqual(self.playlist.cycle_repeat(), RepeatMode.ONE)
        self.assertEqual(self.playlist.cycle_repeat(), RepeatMode.NONE)

    def test_toggle_shuffle(self):
        self.assertFalse(self.playlist.shuffle)
        result = self.playlist.toggle_shuffle()
        self.assertTrue(result)
        self.assertTrue(self.playlist.shuffle)
        result = self.playlist.toggle_shuffle()
        self.assertFalse(result)

    def test_shuffle_navigation_visits_all(self):
        self.playlist.repeat_mode = RepeatMode.ALL
        self.playlist.toggle_shuffle()
        visited = set()
        for _ in range(20):  # More than enough iterations
            current = self.playlist.current
            if current:
                visited.add(current)
            self.playlist.next()
        # Shuffle with repeat ALL should eventually visit all items
        self.assertEqual(len(visited), 3)


# ═══════════════════════════════════════════════════════════════════════════
# Repeat Mode constants
# ═══════════════════════════════════════════════════════════════════════════
class TestRepeatMode(unittest.TestCase):
    """Verify repeat mode constant values."""

    def test_repeat_none(self):
        self.assertEqual(RepeatMode.NONE, "none")

    def test_repeat_all(self):
        self.assertEqual(RepeatMode.ALL, "all")

    def test_repeat_one(self):
        self.assertEqual(RepeatMode.ONE, "one")


# ═══════════════════════════════════════════════════════════════════════════
# Translations
# ═══════════════════════════════════════════════════════════════════════════
# Database - SQLite Playlist Persistence
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylistDB(unittest.TestCase):
    """Test SQLite playlist database operations."""

    # Fake file paths used as test data for DB storage — these are never
    # accessed on disk, only stored/retrieved as strings.  NOSONAR
    _F = "/test/media"  # NOSONAR - not a real publicly writable directory
    _A = f"{_F}/a.mp4"
    _B = f"{_F}/b.mp4"
    _C = f"{_F}/c.mp4"
    _X = f"{_F}/x.mp4"
    _Y = f"{_F}/y.mp4"
    _B_MKV = f"{_F}/b.mkv"
    _C_AVI = f"{_F}/c.avi"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mados_vp_db_test_")
        self.db_path = os.path.join(self.tmpdir, "test_playlists.db")
        self.db = PlaylistDB(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir)

    def test_db_file_created(self):
        self.assertTrue(os.path.isfile(self.db_path))

    def test_list_playlists_empty(self):
        result = self.db.list_playlists()
        self.assertEqual(result, [])

    def test_save_and_load_playlist(self):
        files = [self._A, self._B_MKV, self._C_AVI]
        self.db.save_playlist("My Videos", files)
        loaded = self.db.load_playlist("My Videos")
        self.assertEqual(loaded, files)

    def test_save_overwrites_existing(self):
        self.db.save_playlist("Test", [self._A])
        self.db.save_playlist("Test", [self._X, self._Y])
        loaded = self.db.load_playlist("Test")
        self.assertEqual(loaded, [self._X, self._Y])

    def test_load_nonexistent(self):
        result = self.db.load_playlist("Nonexistent")
        self.assertIsNone(result)

    def test_list_playlists_sorted(self):
        self.db.save_playlist("Zebra", [self._A])
        self.db.save_playlist("Alpha", [self._B])
        self.db.save_playlist("Middle", [self._C])
        names = [name for _, name in self.db.list_playlists()]
        self.assertEqual(names, ["Alpha", "Middle", "Zebra"])

    def test_delete_playlist(self):
        self.db.save_playlist("ToDelete", [self._A])
        result = self.db.delete_playlist("ToDelete")
        self.assertTrue(result)
        self.assertIsNone(self.db.load_playlist("ToDelete"))

    def test_delete_nonexistent(self):
        result = self.db.delete_playlist("Ghost")
        self.assertFalse(result)

    def test_delete_cascades_items(self):
        self.db.save_playlist("Cascade", [self._A, self._B])
        self.db.delete_playlist("Cascade")
        # Items should be gone (no orphans)
        cur = self.db._conn.execute("SELECT COUNT(*) FROM playlist_items")
        self.assertEqual(cur.fetchone()[0], 0)

    def test_rename_playlist(self):
        self.db.save_playlist("OldName", [self._A])
        result = self.db.rename_playlist("OldName", "NewName")
        self.assertTrue(result)
        self.assertIsNone(self.db.load_playlist("OldName"))
        self.assertEqual(self.db.load_playlist("NewName"), [self._A])

    def test_rename_nonexistent(self):
        result = self.db.rename_playlist("Ghost", "Whatever")
        self.assertFalse(result)

    def test_rename_to_existing_name(self):
        self.db.save_playlist("First", [self._A])
        self.db.save_playlist("Second", [self._B])
        result = self.db.rename_playlist("First", "Second")
        self.assertFalse(result)

    def test_session_key_value(self):
        self.db.set_session("volume", "0.75")
        self.assertEqual(self.db.get_session("volume"), "0.75")

    def test_session_default(self):
        result = self.db.get_session("missing_key", "fallback")
        self.assertEqual(result, "fallback")

    def test_session_overwrite(self):
        self.db.set_session("key", "value1")
        self.db.set_session("key", "value2")
        self.assertEqual(self.db.get_session("key"), "value2")

    def test_save_session_playlist(self):
        files = [self._A, self._B]
        self.db.save_session_playlist(files, current_index=1,
                                       repeat_mode="all", shuffle=True)
        session = self.db.load_session_playlist()
        self.assertIsNotNone(session)
        self.assertEqual(session["filepaths"], files)
        self.assertEqual(session["current_index"], 1)
        self.assertEqual(session["repeat_mode"], "all")
        self.assertTrue(session["shuffle"])

    def test_load_session_playlist_empty(self):
        result = self.db.load_session_playlist()
        self.assertIsNone(result)

    def test_save_empty_playlist(self):
        self.db.save_playlist("Empty", [])
        loaded = self.db.load_playlist("Empty")
        self.assertEqual(loaded, [])

    def test_playlist_preserves_order(self):
        files = [f"{self._F}/{chr(ord('z') - i)}.mp4" for i in range(10)]
        self.db.save_playlist("Ordered", files)
        loaded = self.db.load_playlist("Ordered")
        self.assertEqual(loaded, files)

    def test_multiple_playlists_independent(self):
        self.db.save_playlist("PL1", [self._A])
        self.db.save_playlist("PL2", [self._X, self._Y])
        self.assertEqual(self.db.load_playlist("PL1"), [self._A])
        self.assertEqual(self.db.load_playlist("PL2"), [self._X, self._Y])

    def test_close_and_reopen(self):
        self.db.save_playlist("Persist", [self._A])
        self.db.close()
        db2 = PlaylistDB(db_path=self.db_path)
        loaded = db2.load_playlist("Persist")
        db2.close()
        self.assertEqual(loaded, [self._A])


# ═══════════════════════════════════════════════════════════════════════════
# Translations
# ═══════════════════════════════════════════════════════════════════════════
class TestTranslations(unittest.TestCase):
    """Test the translations module."""

    def test_import_translations(self):
        from mados_video_player.translations import TRANSLATIONS, get_text, get_languages
        self.assertIsInstance(TRANSLATIONS, dict)
        self.assertGreater(len(TRANSLATIONS), 0)

    def test_all_languages_have_title(self):
        from mados_video_player.translations import TRANSLATIONS
        for lang, strings in TRANSLATIONS.items():
            self.assertIn("title", strings, f"Language '{lang}' missing 'title' key")

    def test_get_text_default(self):
        from mados_video_player.translations import get_text
        result = get_text("title")
        self.assertEqual(result, "madOS Video Player")

    def test_get_text_spanish(self):
        from mados_video_player.translations import get_text
        result = get_text("title", "Español")
        self.assertIn("madOS", result)

    def test_get_text_missing_key(self):
        from mados_video_player.translations import get_text
        result = get_text("nonexistent_key_xyz")
        self.assertEqual(result, "nonexistent_key_xyz")

    def test_get_languages(self):
        from mados_video_player.translations import get_languages
        langs = get_languages()
        self.assertIn("English", langs)
        self.assertIn("Español", langs)
        self.assertGreaterEqual(len(langs), 6)

    def test_all_languages_have_same_keys(self):
        from mados_video_player.translations import TRANSLATIONS
        english_keys = set(TRANSLATIONS["English"].keys())
        for lang, strings in TRANSLATIONS.items():
            lang_keys = set(strings.keys())
            missing = english_keys - lang_keys
            self.assertEqual(
                len(missing), 0,
                f"Language '{lang}' missing keys: {missing}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# Module metadata
# ═══════════════════════════════════════════════════════════════════════════
class TestModuleMetadata(unittest.TestCase):
    """Test package metadata."""

    def test_version(self):
        from mados_video_player import __version__
        self.assertIsInstance(__version__, str)
        self.assertTrue(len(__version__) > 0)

    def test_app_id(self):
        from mados_video_player import __app_id__
        self.assertEqual(__app_id__, "mados-video-player")

    def test_app_name(self):
        from mados_video_player import __app_name__
        self.assertEqual(__app_name__, "madOS Video Player")


if __name__ == "__main__":
    unittest.main()
