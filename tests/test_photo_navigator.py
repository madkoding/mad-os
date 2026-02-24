#!/usr/bin/env python3
"""
Tests for madOS Photo Viewer file navigator.

Validates file type detection helpers and the FileNavigator class that
manages listing and navigating through image and video files within a
directory.

These tests use a temporary directory with test files and do not require
GTK or a display server.
"""

import sys
import os
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so photo viewer modules can be imported headlessly.
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

from mados_photo_viewer.navigator import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    ALL_EXTENSIONS,
    is_image_file,
    is_video_file,
    is_media_file,
    FileNavigator,
)


# ═══════════════════════════════════════════════════════════════════════════
# Extension sets
# ═══════════════════════════════════════════════════════════════════════════
class TestExtensionSets(unittest.TestCase):
    """Verify extension set constants are correct."""

    def test_image_extensions_not_empty(self):
        self.assertGreater(len(IMAGE_EXTENSIONS), 0)

    def test_video_extensions_not_empty(self):
        self.assertGreater(len(VIDEO_EXTENSIONS), 0)

    def test_all_is_union(self):
        self.assertEqual(ALL_EXTENSIONS, IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)

    def test_no_overlap(self):
        overlap = IMAGE_EXTENSIONS & VIDEO_EXTENSIONS
        self.assertEqual(overlap, set())

    def test_common_image_formats(self):
        for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
            with self.subTest(ext=ext):
                self.assertIn(ext, IMAGE_EXTENSIONS)

    def test_common_video_formats(self):
        for ext in (".mp4", ".mkv", ".avi", ".webm", ".mov"):
            with self.subTest(ext=ext):
                self.assertIn(ext, VIDEO_EXTENSIONS)

    def test_all_lowercase(self):
        for ext in ALL_EXTENSIONS:
            with self.subTest(ext=ext):
                self.assertEqual(ext, ext.lower())
                self.assertTrue(ext.startswith("."))


# ═══════════════════════════════════════════════════════════════════════════
# File type detection helpers
# ═══════════════════════════════════════════════════════════════════════════
class TestIsImageFile(unittest.TestCase):
    """Verify is_image_file() detects image extensions."""

    def test_jpg(self):
        self.assertTrue(is_image_file("photo.jpg"))

    def test_png(self):
        self.assertTrue(is_image_file("image.png"))

    def test_case_insensitive(self):
        self.assertTrue(is_image_file("Photo.JPG"))
        self.assertTrue(is_image_file("IMAGE.PNG"))

    def test_video_is_not_image(self):
        self.assertFalse(is_image_file("movie.mp4"))

    def test_text_file(self):
        self.assertFalse(is_image_file("document.txt"))

    def test_no_extension(self):
        self.assertFalse(is_image_file("noext"))

    def test_full_path(self):
        self.assertTrue(is_image_file("/home/user/pics/photo.jpeg"))


class TestIsVideoFile(unittest.TestCase):
    """Verify is_video_file() detects video extensions."""

    def test_mp4(self):
        self.assertTrue(is_video_file("movie.mp4"))

    def test_mkv(self):
        self.assertTrue(is_video_file("video.mkv"))

    def test_case_insensitive(self):
        self.assertTrue(is_video_file("Movie.MP4"))

    def test_image_is_not_video(self):
        self.assertFalse(is_video_file("photo.jpg"))

    def test_no_extension(self):
        self.assertFalse(is_video_file("noext"))


class TestIsMediaFile(unittest.TestCase):
    """Verify is_media_file() detects both image and video files."""

    def test_image(self):
        self.assertTrue(is_media_file("photo.jpg"))

    def test_video(self):
        self.assertTrue(is_media_file("movie.mp4"))

    def test_non_media(self):
        self.assertFalse(is_media_file("readme.md"))


# ═══════════════════════════════════════════════════════════════════════════
# FileNavigator
# ═══════════════════════════════════════════════════════════════════════════
class TestFileNavigatorInit(unittest.TestCase):
    """Verify FileNavigator initial state."""

    def test_empty_state(self):
        nav = FileNavigator()
        self.assertIsNone(nav.current_file)
        self.assertEqual(nav.current_filename, "")
        self.assertEqual(nav.current_index, 0)
        self.assertEqual(nav.total_count, 0)
        self.assertFalse(nav.has_files)
        self.assertFalse(nav.is_current_image)
        self.assertFalse(nav.is_current_video)

    def test_go_next_empty(self):
        nav = FileNavigator()
        self.assertIsNone(nav.go_next())

    def test_go_prev_empty(self):
        nav = FileNavigator()
        self.assertIsNone(nav.go_prev())


class TestFileNavigatorLoadDirectory(unittest.TestCase):
    """Verify FileNavigator.load_directory() scanning and positioning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create test files
        self.files = [
            "alpha.jpg",
            "beta.png",
            "gamma.mp4",
            "delta.txt",
            "epsilon.svg",
            "readme.md",
        ]
        for f in self.files:
            with open(os.path.join(self.tmpdir, f), "w") as fp:
                fp.write("test")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_loads_media_files_only(self):
        nav = FileNavigator()
        target = os.path.join(self.tmpdir, "alpha.jpg")
        nav.load_directory(target)
        # Should have: alpha.jpg, beta.png, epsilon.svg, gamma.mp4
        self.assertEqual(nav.total_count, 4)

    def test_non_media_excluded(self):
        nav = FileNavigator()
        target = os.path.join(self.tmpdir, "alpha.jpg")
        nav.load_directory(target)
        filenames = []
        for _ in range(nav.total_count):
            filenames.append(nav.current_filename)
            nav.go_next()
        self.assertNotIn("delta.txt", filenames)
        self.assertNotIn("readme.md", filenames)

    def test_positions_at_target(self):
        nav = FileNavigator()
        target = os.path.join(self.tmpdir, "beta.png")
        result = nav.load_directory(target)
        self.assertTrue(result)
        self.assertEqual(nav.current_filename, "beta.png")

    def test_files_sorted_case_insensitive(self):
        nav = FileNavigator()
        target = os.path.join(self.tmpdir, "alpha.jpg")
        nav.load_directory(target)
        # Sorted: alpha.jpg, beta.png, epsilon.svg, gamma.mp4
        self.assertEqual(nav.current_filename, "alpha.jpg")

    def test_target_not_media(self):
        nav = FileNavigator()
        target = os.path.join(self.tmpdir, "delta.txt")
        result = nav.load_directory(target)
        self.assertFalse(result)
        # Should still have media files loaded, positioned at first
        self.assertEqual(nav.total_count, 4)

    def test_nonexistent_directory(self):
        nav = FileNavigator()
        result = nav.load_directory("/nonexistent/path/file.jpg")
        self.assertFalse(result)
        self.assertFalse(nav.has_files)


class TestFileNavigatorNavigation(unittest.TestCase):
    """Verify next/prev navigation with wraparound."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for f in ["a.jpg", "b.png", "c.mp4"]:
            with open(os.path.join(self.tmpdir, f), "w") as fp:
                fp.write("test")
        self.nav = FileNavigator()
        self.nav.load_directory(os.path.join(self.tmpdir, "a.jpg"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_go_next(self):
        self.assertEqual(self.nav.current_filename, "a.jpg")
        self.nav.go_next()
        self.assertEqual(self.nav.current_filename, "b.png")
        self.nav.go_next()
        self.assertEqual(self.nav.current_filename, "c.mp4")

    def test_next_wraps_around(self):
        self.nav.go_next()
        self.nav.go_next()
        self.nav.go_next()  # Should wrap to first
        self.assertEqual(self.nav.current_filename, "a.jpg")

    def test_go_prev(self):
        self.nav.go_prev()  # Wraps to last
        self.assertEqual(self.nav.current_filename, "c.mp4")

    def test_prev_wraps_around(self):
        self.nav.go_prev()
        self.assertEqual(self.nav.current_filename, "c.mp4")
        self.nav.go_prev()
        self.assertEqual(self.nav.current_filename, "b.png")
        self.nav.go_prev()
        self.assertEqual(self.nav.current_filename, "a.jpg")

    def test_current_index_one_based(self):
        self.assertEqual(self.nav.current_index, 1)
        self.nav.go_next()
        self.assertEqual(self.nav.current_index, 2)

    def test_is_current_image(self):
        self.assertTrue(self.nav.is_current_image)
        self.assertFalse(self.nav.is_current_video)

    def test_is_current_video(self):
        self.nav.go_next()
        self.nav.go_next()  # c.mp4
        self.assertTrue(self.nav.is_current_video)
        self.assertFalse(self.nav.is_current_image)


class TestFileNavigatorGoToFile(unittest.TestCase):
    """Verify go_to_file() navigation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for f in ["a.jpg", "b.png", "c.mp4"]:
            with open(os.path.join(self.tmpdir, f), "w") as fp:
                fp.write("test")
        self.nav = FileNavigator()
        self.nav.load_directory(os.path.join(self.tmpdir, "a.jpg"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_go_to_same_dir(self):
        target = os.path.join(self.tmpdir, "c.mp4")
        result = self.nav.go_to_file(target)
        self.assertTrue(result)
        self.assertEqual(self.nav.current_filename, "c.mp4")

    def test_go_to_nonexistent(self):
        target = os.path.join(self.tmpdir, "nope.jpg")
        result = self.nav.go_to_file(target)
        self.assertFalse(result)

    def test_go_to_different_dir(self):
        otherdir = tempfile.mkdtemp()
        with open(os.path.join(otherdir, "other.jpg"), "w") as f:
            f.write("test")
        target = os.path.join(otherdir, "other.jpg")
        result = self.nav.go_to_file(target)
        self.assertTrue(result)
        self.assertEqual(self.nav.current_filename, "other.jpg")
        import shutil

        shutil.rmtree(otherdir, ignore_errors=True)


class TestFileNavigatorRefresh(unittest.TestCase):
    """Verify refresh() rescans directory while maintaining position."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for f in ["a.jpg", "b.png"]:
            with open(os.path.join(self.tmpdir, f), "w") as fp:
                fp.write("test")
        self.nav = FileNavigator()
        self.nav.load_directory(os.path.join(self.tmpdir, "b.png"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_refresh_maintains_position(self):
        self.assertEqual(self.nav.current_filename, "b.png")
        self.nav.refresh()
        self.assertEqual(self.nav.current_filename, "b.png")

    def test_refresh_picks_up_new_files(self):
        self.assertEqual(self.nav.total_count, 2)
        with open(os.path.join(self.tmpdir, "c.gif"), "w") as f:
            f.write("test")
        self.nav.refresh()
        self.assertEqual(self.nav.total_count, 3)
        self.assertEqual(self.nav.current_filename, "b.png")

    def test_refresh_handles_deleted_file(self):
        os.unlink(os.path.join(self.tmpdir, "b.png"))
        self.nav.refresh()
        self.assertEqual(self.nav.total_count, 1)
        self.assertEqual(self.nav.current_filename, "a.jpg")

    def test_refresh_empty_directory(self):
        os.unlink(os.path.join(self.tmpdir, "a.jpg"))
        os.unlink(os.path.join(self.tmpdir, "b.png"))
        self.nav.refresh()
        self.assertEqual(self.nav.total_count, 0)
        self.assertFalse(self.nav.has_files)

    def test_refresh_no_directory(self):
        nav = FileNavigator()
        nav.refresh()  # Should not raise


class TestFileNavigatorSingleFile(unittest.TestCase):
    """Verify navigation with only one file in the directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        with open(os.path.join(self.tmpdir, "only.jpg"), "w") as f:
            f.write("test")
        self.nav = FileNavigator()
        self.nav.load_directory(os.path.join(self.tmpdir, "only.jpg"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_single_file_next_stays(self):
        self.nav.go_next()
        self.assertEqual(self.nav.current_filename, "only.jpg")

    def test_single_file_prev_stays(self):
        self.nav.go_prev()
        self.assertEqual(self.nav.current_filename, "only.jpg")

    def test_total_count(self):
        self.assertEqual(self.nav.total_count, 1)
        self.assertEqual(self.nav.current_index, 1)


if __name__ == "__main__":
    unittest.main()
