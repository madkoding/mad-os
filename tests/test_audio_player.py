#!/usr/bin/env python3
"""
Tests for madOS Audio Player.

Validates the playlist manager, backend helpers, translations,
theme, and module metadata. These tests run in CI without
requiring mpv, PipeWire, or audio hardware.
"""

import sys
import os
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so GTK modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "lib")
sys.path.insert(0, LIB_DIR)

from mados_audio_player.playlist import (
    Playlist, Track, format_time,
    REPEAT_OFF, REPEAT_ALL, REPEAT_ONE,
)
from mados_audio_player.database import PlaylistDB, DEFAULT_PLAYLIST
from mados_audio_player.backend import MpvBackend
from mados_audio_player.translations import (
    TRANSLATIONS, AVAILABLE_LANGUAGES, DEFAULT_LANGUAGE,
    get_text, detect_system_language,
)
from mados_audio_player import __version__, __app_id__, __app_name__


# ═══════════════════════════════════════════════════════════════════════════
# Module metadata
# ═══════════════════════════════════════════════════════════════════════════
class TestModuleMetadata(unittest.TestCase):
    """Verify package metadata."""

    def test_version_is_string(self):
        self.assertIsInstance(__version__, str)

    def test_app_id(self):
        self.assertEqual(__app_id__, "mados-audio-player")

    def test_app_name(self):
        self.assertEqual(__app_name__, "madOS Audio Player")


# ═══════════════════════════════════════════════════════════════════════════
# Track
# ═══════════════════════════════════════════════════════════════════════════
class TestTrack(unittest.TestCase):
    """Verify Track data model."""

    def test_title_from_filename(self):
        t = Track("/path/to/My Song.mp3")
        self.assertEqual(t.title, "My Song")

    def test_filepath_stored(self):
        t = Track("/music/test.flac")
        self.assertEqual(t.filepath, "/music/test.flac")

    def test_default_artist_empty(self):
        t = Track("/music/test.mp3")
        self.assertEqual(t.artist, "")

    def test_default_album_empty(self):
        t = Track("/music/test.mp3")
        self.assertEqual(t.album, "")

    def test_default_duration_zero(self):
        t = Track("/music/test.mp3")
        self.assertEqual(t.duration, 0.0)

    def test_display_name_no_artist(self):
        t = Track("/music/Cool Track.ogg")
        self.assertEqual(t.display_name(), "Cool Track")

    def test_display_name_with_artist(self):
        t = Track("/music/song.mp3")
        t.artist = "Artist Name"
        t.title = "Song Title"
        self.assertEqual(t.display_name(), "Artist Name - Song Title")

    def test_update_metadata(self):
        t = Track("/music/test.mp3")
        t.update_metadata({
            "title": "Real Title",
            "artist": "Real Artist",
            "album": "Real Album",
        })
        self.assertEqual(t.title, "Real Title")
        self.assertEqual(t.artist, "Real Artist")
        self.assertEqual(t.album, "Real Album")

    def test_update_metadata_partial(self):
        t = Track("/music/test.mp3")
        t.update_metadata({"artist": "Only Artist"})
        self.assertEqual(t.title, "test")  # from filename
        self.assertEqual(t.artist, "Only Artist")

    def test_repr(self):
        t = Track("/music/test.mp3")
        self.assertIn("/music/test.mp3", repr(t))

    def test_default_db_id_none(self):
        t = Track("/music/test.mp3")
        self.assertIsNone(t.db_id)

    def test_db_id_assigned(self):
        t = Track("/music/test.mp3", db_id=42)
        self.assertEqual(t.db_id, 42)


# ═══════════════════════════════════════════════════════════════════════════
# Format time
# ═══════════════════════════════════════════════════════════════════════════
class TestFormatTime(unittest.TestCase):
    """Verify time formatting."""

    def test_zero(self):
        self.assertEqual(format_time(0), "0:00")

    def test_negative(self):
        self.assertEqual(format_time(-5), "0:00")

    def test_seconds_only(self):
        self.assertEqual(format_time(45), "0:45")

    def test_minutes_and_seconds(self):
        self.assertEqual(format_time(185), "3:05")

    def test_hours(self):
        self.assertEqual(format_time(3661), "1:01:01")

    def test_exact_minute(self):
        self.assertEqual(format_time(60), "1:00")

    def test_exact_hour(self):
        self.assertEqual(format_time(3600), "1:00:00")

    def test_nan(self):
        self.assertEqual(format_time(float('nan')), "0:00")


# ═══════════════════════════════════════════════════════════════════════════
# Playlist
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylist(unittest.TestCase):
    """Verify playlist management (SQLite-backed)."""

    def setUp(self):
        self.pl = Playlist(db_path=":memory:")
        self.tmpdir = tempfile.mkdtemp()
        self.files = []
        for name in ["track1.mp3", "track2.flac", "track3.ogg"]:
            p = os.path.join(self.tmpdir, name)
            with open(p, "w") as f:
                f.write("fake audio")
            self.files.append(p)

    def tearDown(self):
        self.pl.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_by_default(self):
        self.assertTrue(self.pl.is_empty)
        self.assertEqual(self.pl.count, 0)

    def test_add_file(self):
        track = self.pl.add_file(self.files[0])
        self.assertIsNotNone(track)
        self.assertEqual(self.pl.count, 1)

    def test_add_nonexistent_file(self):
        result = self.pl.add_file("/nonexistent/fake.mp3")
        self.assertIsNone(result)

    def test_add_files(self):
        count = self.pl.add_files(self.files)
        self.assertEqual(count, 3)
        self.assertEqual(self.pl.count, 3)

    def test_add_directory(self):
        count = self.pl.add_directory(self.tmpdir)
        self.assertEqual(count, 3)

    def test_clear(self):
        self.pl.add_files(self.files)
        self.pl.clear()
        self.assertTrue(self.pl.is_empty)
        self.assertEqual(self.pl.current_index, -1)

    def test_set_current(self):
        self.pl.add_files(self.files)
        track = self.pl.set_current(1)
        self.assertIsNotNone(track)
        self.assertEqual(self.pl.current_index, 1)

    def test_set_current_invalid(self):
        self.pl.add_files(self.files)
        result = self.pl.set_current(99)
        self.assertIsNone(result)

    def test_get_current_no_selection(self):
        self.assertIsNone(self.pl.get_current_track())

    def test_next_track_sequential(self):
        self.pl.add_files(self.files)
        self.pl.set_current(0)
        track = self.pl.next_track()
        self.assertEqual(self.pl.current_index, 1)

    def test_next_track_at_end_no_repeat(self):
        self.pl.add_files(self.files)
        self.pl.set_current(2)
        track = self.pl.next_track()
        self.assertIsNone(track)

    def test_next_track_at_end_repeat_all(self):
        self.pl.add_files(self.files)
        self.pl.set_current(2)
        self.pl.repeat_mode = REPEAT_ALL
        track = self.pl.next_track()
        self.assertIsNotNone(track)
        self.assertEqual(self.pl.current_index, 0)

    def test_next_track_repeat_one(self):
        self.pl.add_files(self.files)
        self.pl.set_current(1)
        self.pl.repeat_mode = REPEAT_ONE
        track = self.pl.next_track()
        self.assertIsNotNone(track)
        self.assertEqual(self.pl.current_index, 1)

    def test_prev_track(self):
        self.pl.add_files(self.files)
        self.pl.set_current(2)
        track = self.pl.prev_track()
        self.assertEqual(self.pl.current_index, 1)

    def test_prev_track_at_start_no_repeat(self):
        self.pl.add_files(self.files)
        self.pl.set_current(0)
        track = self.pl.prev_track()
        self.assertEqual(self.pl.current_index, 0)

    def test_prev_track_at_start_repeat_all(self):
        self.pl.add_files(self.files)
        self.pl.set_current(0)
        self.pl.repeat_mode = REPEAT_ALL
        track = self.pl.prev_track()
        self.assertEqual(self.pl.current_index, 2)

    def test_remove_index(self):
        self.pl.add_files(self.files)
        self.assertEqual(self.pl.count, 3)
        self.pl.remove_index(1)
        self.assertEqual(self.pl.count, 2)

    def test_remove_invalid_index(self):
        self.pl.add_files(self.files)
        result = self.pl.remove_index(99)
        self.assertFalse(result)

    def test_remove_indices(self):
        self.pl.add_files(self.files)
        self.pl.remove_indices([0, 2])
        self.assertEqual(self.pl.count, 1)

    def test_toggle_shuffle(self):
        self.assertFalse(self.pl.shuffle)
        self.pl.toggle_shuffle()
        self.assertTrue(self.pl.shuffle)
        self.pl.toggle_shuffle()
        self.assertFalse(self.pl.shuffle)

    def test_cycle_repeat(self):
        self.assertEqual(self.pl.repeat_mode, REPEAT_OFF)
        mode = self.pl.cycle_repeat()
        self.assertEqual(mode, REPEAT_ALL)
        mode = self.pl.cycle_repeat()
        self.assertEqual(mode, REPEAT_ONE)
        mode = self.pl.cycle_repeat()
        self.assertEqual(mode, REPEAT_OFF)

    def test_total_duration_str_empty(self):
        self.assertEqual(self.pl.total_duration_str(), "0:00")

    def test_next_on_empty_playlist(self):
        self.assertIsNone(self.pl.next_track())

    def test_prev_on_empty_playlist(self):
        self.assertIsNone(self.pl.prev_track())

    def test_playlist_name_default(self):
        self.assertEqual(self.pl.playlist_name, DEFAULT_PLAYLIST)

    def test_track_has_db_id(self):
        track = self.pl.add_file(self.files[0])
        self.assertIsNotNone(track.db_id)

    def test_update_track_metadata_syncs(self):
        self.pl.add_files(self.files)
        track = self.pl.tracks[0]
        self.pl.update_track_metadata(track, {"title": "New Title", "artist": "New Artist"})
        self.assertEqual(track.title, "New Title")
        self.assertEqual(track.artist, "New Artist")

    def test_update_track_duration_syncs(self):
        self.pl.add_files(self.files)
        track = self.pl.tracks[0]
        self.pl.update_track_duration(track, 180.5)
        self.assertEqual(track.duration, 180.5)

    def test_state_persists_in_db(self):
        """Verify that shuffle/repeat state is saved to DB."""
        self.pl.toggle_shuffle()
        self.pl.cycle_repeat()
        # Read state directly from DB
        self.assertEqual(
            self.pl._db.get_bool_setting("shuffle"), True
        )
        self.assertEqual(
            self.pl._db.get_int_setting("repeat_mode"), REPEAT_ALL
        )


# ═══════════════════════════════════════════════════════════════════════════
# PlaylistDB (SQLite layer)
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylistDB(unittest.TestCase):
    """Verify SQLite database layer."""

    def setUp(self):
        self.db = PlaylistDB(":memory:")

    def tearDown(self):
        self.db.close()

    def test_create_playlist(self):
        pid = self.db.create_playlist("Test")
        self.assertIsNotNone(pid)
        self.assertIsInstance(pid, int)

    def test_create_duplicate_returns_existing(self):
        pid1 = self.db.create_playlist("Test")
        pid2 = self.db.create_playlist("Test")
        self.assertEqual(pid1, pid2)

    def test_list_playlists(self):
        self.db.create_playlist("A")
        self.db.create_playlist("B")
        playlists = self.db.list_playlists()
        names = [p[1] for p in playlists]
        self.assertIn("A", names)
        self.assertIn("B", names)

    def test_rename_playlist(self):
        pid = self.db.create_playlist("Old")
        result = self.db.rename_playlist(pid, "New")
        self.assertTrue(result)
        playlists = self.db.list_playlists()
        names = [p[1] for p in playlists]
        self.assertIn("New", names)
        self.assertNotIn("Old", names)

    def test_rename_conflict(self):
        self.db.create_playlist("A")
        pid2 = self.db.create_playlist("B")
        result = self.db.rename_playlist(pid2, "A")
        self.assertFalse(result)

    def test_delete_playlist(self):
        pid = self.db.create_playlist("ToDelete")
        self.db.delete_playlist(pid)
        self.assertFalse(self.db.playlist_exists("ToDelete"))

    def test_playlist_exists(self):
        self.db.create_playlist("Exists")
        self.assertTrue(self.db.playlist_exists("Exists"))
        self.assertFalse(self.db.playlist_exists("NoExist"))

    def test_add_and_get_tracks(self):
        pid = self.db.create_playlist("Test")
        self.db.add_track(pid, "/music/a.mp3", title="Song A")
        self.db.add_track(pid, "/music/b.mp3", title="Song B")
        tracks = self.db.get_tracks(pid)
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0]["title"], "Song A")
        self.assertEqual(tracks[1]["title"], "Song B")

    def test_track_positions_sequential(self):
        pid = self.db.create_playlist("Test")
        self.db.add_track(pid, "/music/a.mp3")
        self.db.add_track(pid, "/music/b.mp3")
        self.db.add_track(pid, "/music/c.mp3")
        tracks = self.db.get_tracks(pid)
        positions = [t["position"] for t in tracks]
        self.assertEqual(positions, [0, 1, 2])

    def test_get_track_count(self):
        pid = self.db.create_playlist("Test")
        self.assertEqual(self.db.get_track_count(pid), 0)
        self.db.add_track(pid, "/music/a.mp3")
        self.db.add_track(pid, "/music/b.mp3")
        self.assertEqual(self.db.get_track_count(pid), 2)

    def test_update_track_metadata(self):
        pid = self.db.create_playlist("Test")
        tid = self.db.add_track(pid, "/music/a.mp3", title="Old")
        self.db.update_track_metadata(tid, title="New", artist="Artist")
        tracks = self.db.get_tracks(pid)
        self.assertEqual(tracks[0]["title"], "New")
        self.assertEqual(tracks[0]["artist"], "Artist")

    def test_remove_track_at(self):
        pid = self.db.create_playlist("Test")
        self.db.add_track(pid, "/music/a.mp3")
        self.db.add_track(pid, "/music/b.mp3")
        self.db.add_track(pid, "/music/c.mp3")
        result = self.db.remove_track_at(pid, 1)
        self.assertTrue(result)
        tracks = self.db.get_tracks(pid)
        self.assertEqual(len(tracks), 2)
        # Positions should be reindexed
        self.assertEqual(tracks[0]["position"], 0)
        self.assertEqual(tracks[1]["position"], 1)

    def test_remove_track_at_invalid(self):
        pid = self.db.create_playlist("Test")
        result = self.db.remove_track_at(pid, 99)
        self.assertFalse(result)

    def test_remove_tracks_at_multiple(self):
        pid = self.db.create_playlist("Test")
        self.db.add_track(pid, "/music/a.mp3")
        self.db.add_track(pid, "/music/b.mp3")
        self.db.add_track(pid, "/music/c.mp3")
        self.db.remove_tracks_at(pid, [0, 2])
        tracks = self.db.get_tracks(pid)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["filepath"], "/music/b.mp3")

    def test_clear_tracks(self):
        pid = self.db.create_playlist("Test")
        self.db.add_track(pid, "/music/a.mp3")
        self.db.add_track(pid, "/music/b.mp3")
        self.db.clear_tracks(pid)
        self.assertEqual(self.db.get_track_count(pid), 0)

    def test_settings_string(self):
        self.db.set_setting("key1", "value1")
        self.assertEqual(self.db.get_setting("key1"), "value1")

    def test_settings_default(self):
        self.assertIsNone(self.db.get_setting("missing"))
        self.assertEqual(self.db.get_setting("missing", "def"), "def")

    def test_settings_int(self):
        self.db.set_setting("count", "42")
        self.assertEqual(self.db.get_int_setting("count"), 42)

    def test_settings_int_default(self):
        self.assertEqual(self.db.get_int_setting("missing", 7), 7)

    def test_settings_bool_true(self):
        self.db.set_setting("flag", "True")
        self.assertTrue(self.db.get_bool_setting("flag"))

    def test_settings_bool_false(self):
        self.db.set_setting("flag", "False")
        self.assertFalse(self.db.get_bool_setting("flag"))

    def test_settings_bool_default(self):
        self.assertFalse(self.db.get_bool_setting("missing"))

    def test_settings_overwrite(self):
        self.db.set_setting("key", "old")
        self.db.set_setting("key", "new")
        self.assertEqual(self.db.get_setting("key"), "new")

    def test_delete_cascade_removes_tracks(self):
        pid = self.db.create_playlist("CascadeTest")
        self.db.add_track(pid, "/music/a.mp3")
        self.db.add_track(pid, "/music/b.mp3")
        self.db.delete_playlist(pid)
        self.assertEqual(self.db.get_track_count(pid), 0)


# ═══════════════════════════════════════════════════════════════════════════
# Playlist persistence / multi-playlist
# ═══════════════════════════════════════════════════════════════════════════
class TestPlaylistPersistence(unittest.TestCase):
    """Verify playlist persistence across instances."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.files = []
        for name in ["song1.mp3", "song2.flac"]:
            p = os.path.join(self.tmpdir, name)
            with open(p, "w") as f:
                f.write("fake")
            self.files.append(p)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tracks_persist_across_instances(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        # Instance 1: add tracks
        pl1 = Playlist(db_path=db_file)
        pl1.add_files(self.files)
        pl1.set_current(1)
        pl1.close()

        # Instance 2: verify tracks loaded
        pl2 = Playlist(db_path=db_file)
        self.assertEqual(pl2.count, 2)
        self.assertEqual(pl2.current_index, 1)
        self.assertEqual(pl2.tracks[0].filepath, self.files[0])
        pl2.close()

    def test_shuffle_repeat_persist(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl1 = Playlist(db_path=db_file)
        pl1.toggle_shuffle()
        pl1.cycle_repeat()  # -> REPEAT_ALL
        pl1.cycle_repeat()  # -> REPEAT_ONE
        pl1.close()

        pl2 = Playlist(db_path=db_file)
        self.assertTrue(pl2.shuffle)
        self.assertEqual(pl2.repeat_mode, REPEAT_ONE)
        pl2.close()

    def test_multiple_playlists(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl = Playlist(db_path=db_file, playlist_name="Rock")
        pl.add_files(self.files)
        self.assertEqual(pl.playlist_name, "Rock")
        self.assertEqual(pl.count, 2)

        pl.switch_playlist("Jazz")
        self.assertEqual(pl.playlist_name, "Jazz")
        self.assertEqual(pl.count, 0)

        pl.switch_playlist("Rock")
        self.assertEqual(pl.count, 2)
        pl.close()

    def test_list_playlists(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl = Playlist(db_path=db_file, playlist_name="A")
        pl.switch_playlist("B")
        pl.switch_playlist("C")
        names = [p[1] for p in pl.list_playlists()]
        self.assertIn("A", names)
        self.assertIn("B", names)
        self.assertIn("C", names)
        pl.close()

    def test_rename_playlist(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl = Playlist(db_path=db_file, playlist_name="Old")
        result = pl.rename_playlist("New")
        self.assertTrue(result)
        self.assertEqual(pl.playlist_name, "New")
        pl.close()

    def test_delete_other_playlist(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl = Playlist(db_path=db_file, playlist_name="Keep")
        pl.switch_playlist("Delete")
        pl.switch_playlist("Keep")
        result = pl.delete_playlist("Delete")
        self.assertTrue(result)
        names = [p[1] for p in pl.list_playlists()]
        self.assertNotIn("Delete", names)
        pl.close()

    def test_cannot_delete_current_playlist(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl = Playlist(db_path=db_file, playlist_name="Current")
        result = pl.delete_playlist("Current")
        self.assertFalse(result)
        pl.close()

    def test_save_playlist_as(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl = Playlist(db_path=db_file)
        pl.add_files(self.files)
        result = pl.save_playlist_as("Copy")
        self.assertTrue(result)
        # Duplicate name should fail
        result2 = pl.save_playlist_as("Copy")
        self.assertFalse(result2)
        pl.close()

    def test_metadata_persists(self):
        db_file = os.path.join(self.tmpdir, "test.db")
        pl1 = Playlist(db_path=db_file)
        pl1.add_file(self.files[0])
        pl1.update_track_metadata(
            pl1.tracks[0],
            {"title": "Persisted", "artist": "Test Artist"}
        )
        pl1.update_track_duration(pl1.tracks[0], 240.0)
        pl1.close()

        pl2 = Playlist(db_path=db_file)
        self.assertEqual(pl2.tracks[0].title, "Persisted")
        self.assertEqual(pl2.tracks[0].artist, "Test Artist")
        self.assertEqual(pl2.tracks[0].duration, 240.0)
        pl2.close()


# ═══════════════════════════════════════════════════════════════════════════
# Backend helpers
# ═══════════════════════════════════════════════════════════════════════════
class TestMpvBackendHelpers(unittest.TestCase):
    """Test backend static/class methods (no mpv process needed)."""

    def test_is_audio_file_mp3(self):
        self.assertTrue(MpvBackend.is_audio_file("test.mp3"))

    def test_is_audio_file_flac(self):
        self.assertTrue(MpvBackend.is_audio_file("test.flac"))

    def test_is_audio_file_ogg(self):
        self.assertTrue(MpvBackend.is_audio_file("test.ogg"))

    def test_is_audio_file_wav(self):
        self.assertTrue(MpvBackend.is_audio_file("test.wav"))

    def test_is_audio_file_opus(self):
        self.assertTrue(MpvBackend.is_audio_file("test.opus"))

    def test_is_audio_file_aac(self):
        self.assertTrue(MpvBackend.is_audio_file("test.aac"))

    def test_is_audio_file_m4a(self):
        self.assertTrue(MpvBackend.is_audio_file("test.m4a"))

    def test_not_audio_file_txt(self):
        self.assertFalse(MpvBackend.is_audio_file("readme.txt"))

    def test_not_audio_file_py(self):
        self.assertFalse(MpvBackend.is_audio_file("script.py"))

    def test_not_audio_file_jpg(self):
        self.assertFalse(MpvBackend.is_audio_file("image.jpg"))

    def test_case_insensitive(self):
        self.assertTrue(MpvBackend.is_audio_file("SONG.MP3"))

    def test_audio_extensions_set(self):
        self.assertIsInstance(MpvBackend.AUDIO_EXTENSIONS, set)
        self.assertIn('.mp3', MpvBackend.AUDIO_EXTENSIONS)
        self.assertIn('.flac', MpvBackend.AUDIO_EXTENSIONS)

    def test_scan_directory(self):
        tmpdir = tempfile.mkdtemp()
        try:
            for name in ["a.mp3", "b.flac", "c.txt", "d.ogg"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("data")
            result = MpvBackend.scan_directory(tmpdir)
            self.assertEqual(len(result), 3)  # mp3, flac, ogg
            for path in result:
                self.assertTrue(MpvBackend.is_audio_file(path))
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_scan_directory_nonexistent(self):
        result = MpvBackend.scan_directory("/nonexistent/dir/xyz")
        self.assertEqual(result, [])

    def test_scan_directory_non_recursive(self):
        tmpdir = tempfile.mkdtemp()
        try:
            subdir = os.path.join(tmpdir, "sub")
            os.makedirs(subdir)
            with open(os.path.join(tmpdir, "a.mp3"), "w") as f:
                f.write("data")
            with open(os.path.join(subdir, "b.mp3"), "w") as f:
                f.write("data")
            result = MpvBackend.scan_directory(tmpdir, recursive=False)
            self.assertEqual(len(result), 1)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════
# Backend state
# ═══════════════════════════════════════════════════════════════════════════
class TestMpvBackendState(unittest.TestCase):
    """Test backend initial state (no mpv process)."""

    def test_initial_state(self):
        b = MpvBackend()
        self.assertFalse(b.is_playing)
        self.assertFalse(b.is_paused)
        self.assertFalse(b.is_muted)
        self.assertEqual(b.volume, 100)
        self.assertEqual(b.position, 0.0)
        self.assertEqual(b.duration, 0.0)
        self.assertIsNone(b.current_file)

    def test_formatted_metadata_no_file(self):
        b = MpvBackend()
        meta = b.get_formatted_metadata()
        self.assertEqual(meta['title'], '')
        self.assertEqual(meta['artist'], '')
        self.assertEqual(meta['album'], '')

    def test_formatted_metadata_with_file(self):
        b = MpvBackend()
        b.current_file = "/music/My Song.mp3"
        b.metadata = {}
        meta = b.get_formatted_metadata()
        self.assertEqual(meta['title'], 'My Song')

    def test_formatted_metadata_with_tags(self):
        b = MpvBackend()
        b.current_file = "/music/file.mp3"
        b.metadata = {
            'title': 'Tagged Title',
            'artist': 'Tagged Artist',
            'album': 'Tagged Album',
        }
        meta = b.get_formatted_metadata()
        self.assertEqual(meta['title'], 'Tagged Title')
        self.assertEqual(meta['artist'], 'Tagged Artist')
        self.assertEqual(meta['album'], 'Tagged Album')


# ═══════════════════════════════════════════════════════════════════════════
# Translations
# ═══════════════════════════════════════════════════════════════════════════
class TestTranslations(unittest.TestCase):
    """Verify translation data and functions."""

    def test_six_languages(self):
        self.assertEqual(len(AVAILABLE_LANGUAGES), 6)

    def test_default_language_english(self):
        self.assertEqual(DEFAULT_LANGUAGE, "English")

    def test_all_languages_have_title(self):
        for lang in AVAILABLE_LANGUAGES:
            with self.subTest(lang=lang):
                self.assertIn("title", TRANSLATIONS[lang])

    def test_all_languages_have_play(self):
        for lang in AVAILABLE_LANGUAGES:
            with self.subTest(lang=lang):
                self.assertIn("play", TRANSLATIONS[lang])

    def test_all_languages_have_playlist(self):
        for lang in AVAILABLE_LANGUAGES:
            with self.subTest(lang=lang):
                self.assertIn("playlist", TRANSLATIONS[lang])

    def test_get_text_english(self):
        self.assertEqual(get_text("play", "English"), "Play")

    def test_get_text_spanish(self):
        self.assertEqual(get_text("play", "Español"), "Reproducir")

    def test_get_text_fallback(self):
        # Nonexistent key falls back to key itself
        result = get_text("nonexistent_key_xyz", "English")
        self.assertEqual(result, "nonexistent_key_xyz")

    def test_get_text_default_language(self):
        result = get_text("play")
        self.assertEqual(result, "Play")

    def test_get_text_unknown_language(self):
        result = get_text("play", "Klingon")
        self.assertEqual(result, "Play")  # falls back to English

    def test_detect_system_language_default(self):
        old = os.environ.get("LANG")
        try:
            os.environ["LANG"] = "en_US.UTF-8"
            self.assertEqual(detect_system_language(), "English")
        finally:
            if old is not None:
                os.environ["LANG"] = old
            elif "LANG" in os.environ:
                del os.environ["LANG"]

    def test_detect_system_language_spanish(self):
        old = os.environ.get("LANG")
        try:
            os.environ["LANG"] = "es_ES.UTF-8"
            self.assertEqual(detect_system_language(), "Español")
        finally:
            if old is not None:
                os.environ["LANG"] = old
            elif "LANG" in os.environ:
                del os.environ["LANG"]

    def test_consistent_keys(self):
        """All languages must have the same set of keys as English."""
        en_keys = set(TRANSLATIONS["English"].keys())
        for lang in AVAILABLE_LANGUAGES:
            with self.subTest(lang=lang):
                lang_keys = set(TRANSLATIONS[lang].keys())
                self.assertEqual(lang_keys, en_keys,
                                 f"{lang} missing: {en_keys - lang_keys}, "
                                 f"extra: {lang_keys - en_keys}")

    def test_no_empty_values(self):
        """No translation value should be empty string."""
        for lang in AVAILABLE_LANGUAGES:
            for key, value in TRANSLATIONS[lang].items():
                with self.subTest(lang=lang, key=key):
                    self.assertTrue(len(value) > 0,
                                    f"{lang}[{key}] is empty")


# ═══════════════════════════════════════════════════════════════════════════
# Theme
# ═══════════════════════════════════════════════════════════════════════════
class TestTheme(unittest.TestCase):
    """Verify theme module loads correctly."""

    def test_import_theme(self):
        from mados_audio_player.theme import THEME_CSS, NORD
        self.assertIsInstance(THEME_CSS, str)
        self.assertGreater(len(THEME_CSS), 100)

    def test_nord_colors(self):
        from mados_audio_player.theme import NORD
        self.assertIn('nord0', NORD)
        self.assertIn('nord8', NORD)
        self.assertIn('nord14', NORD)
        self.assertEqual(len(NORD), 16)

    def test_css_contains_player_classes(self):
        from mados_audio_player.theme import THEME_CSS
        self.assertIn("track-display", THEME_CSS)
        self.assertIn("transport-btn", THEME_CSS)
        self.assertIn("seek-bar", THEME_CSS)
        self.assertIn("playlist-view", THEME_CSS)
        self.assertIn("volume-bar", THEME_CSS)


# ═══════════════════════════════════════════════════════════════════════════
# Repeat mode constants
# ═══════════════════════════════════════════════════════════════════════════
class TestRepeatModes(unittest.TestCase):
    """Verify repeat mode constants."""

    def test_repeat_off(self):
        self.assertEqual(REPEAT_OFF, 0)

    def test_repeat_all(self):
        self.assertEqual(REPEAT_ALL, 1)

    def test_repeat_one(self):
        self.assertEqual(REPEAT_ONE, 2)


# ═══════════════════════════════════════════════════════════════════════════
# Spectrum Analyzer
# ═══════════════════════════════════════════════════════════════════════════
class TestSpectrumAnalyzer(unittest.TestCase):
    """Verify the FFT spectrum analyzer module (no cava required)."""

    def test_import_spectrum(self):
        from mados_audio_player.spectrum import SpectrumAnalyzer
        self.assertTrue(callable(SpectrumAnalyzer))

    def test_default_num_bars(self):
        from mados_audio_player.spectrum import SpectrumAnalyzer, NUM_BARS
        sa = SpectrumAnalyzer()
        self.assertEqual(sa.num_bars, NUM_BARS)
        self.assertEqual(len(sa.bars), NUM_BARS)
        self.assertEqual(len(sa.peaks), NUM_BARS)

    def test_custom_num_bars(self):
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=16)
        self.assertEqual(sa.num_bars, 16)
        self.assertEqual(len(sa.bars), 16)
        self.assertEqual(len(sa.peaks), 16)

    def test_initial_bars_zero(self):
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        for v in sa.bars:
            self.assertEqual(v, 0.0)
        for v in sa.peaks:
            self.assertEqual(v, 0.0)

    def test_is_active_initially_false(self):
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        self.assertFalse(sa.is_active)

    def test_update_with_zero_bars(self):
        """update() should not crash when all bars are zero."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        sa.update()
        for v in sa.bars:
            self.assertEqual(v, 0.0)

    def test_update_with_target_bars(self):
        """update() should move bars toward target values."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=4)
        # Simulate cava data
        sa._target_bars = [0.8, 0.5, 0.3, 0.0]
        sa.update()
        self.assertAlmostEqual(sa.bars[0], 0.8)
        self.assertAlmostEqual(sa.bars[1], 0.5)
        self.assertAlmostEqual(sa.bars[2], 0.3)
        self.assertAlmostEqual(sa.bars[3], 0.0)

    def test_peaks_track_bars(self):
        """Peaks should rise to match bars."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=2)
        sa._target_bars = [1.0, 0.5]
        sa.update()
        self.assertAlmostEqual(sa.peaks[0], 1.0)
        self.assertAlmostEqual(sa.peaks[1], 0.5)

    def test_peaks_decay(self):
        """Peaks should decay when bars drop."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=1)
        # Set peak high
        sa._target_bars = [1.0]
        sa.update()
        self.assertAlmostEqual(sa.peaks[0], 1.0)
        # Drop target to zero
        sa._target_bars = [0.0]
        # After several updates, peak should decrease
        for _ in range(10):
            sa.update()
        self.assertLess(sa.peaks[0], 1.0)

    def test_bars_gravity_decay(self):
        """Bars should fall with gravity when target drops."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=1)
        sa._target_bars = [1.0]
        sa.update()
        self.assertAlmostEqual(sa.bars[0], 1.0)
        # Drop target
        sa._target_bars = [0.0]
        sa.update()
        self.assertLess(sa.bars[0], 1.0)
        self.assertGreater(sa.bars[0], 0.0)

    def test_bars_never_negative(self):
        """Bars should never go below zero."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=1)
        sa._target_bars = [0.0]
        for _ in range(100):
            sa.update()
        self.assertEqual(sa.bars[0], 0.0)

    def test_peaks_never_negative(self):
        """Peaks should never go below zero."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer(num_bars=1)
        sa._target_bars = [0.5]
        sa.update()
        sa._target_bars = [0.0]
        for _ in range(500):
            sa.update()
        self.assertGreaterEqual(sa.peaks[0], 0.0)

    def test_stop_without_start(self):
        """stop() should not crash when not started."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        sa.stop()  # Should not raise

    def test_cleanup_alias(self):
        """cleanup() should be an alias for stop()."""
        from mados_audio_player.spectrum import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        sa.cleanup()  # Should not raise

    def test_constants_exported(self):
        from mados_audio_player.spectrum import NUM_BARS, PEAK_DECAY, BAR_GRAVITY
        self.assertIsInstance(NUM_BARS, int)
        self.assertGreater(NUM_BARS, 0)
        self.assertIsInstance(PEAK_DECAY, float)
        self.assertIsInstance(BAR_GRAVITY, float)


if __name__ == "__main__":
    unittest.main()
