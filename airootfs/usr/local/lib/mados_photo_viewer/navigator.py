"""
madOS Photo Viewer - File Navigator
=====================================

Manages listing and navigating through image and video files within a
directory. Supports previous/next navigation and reports the current
index and total count for the status bar.

Supported image formats: jpg, jpeg, png, gif, bmp, webp, svg, tiff, tif
Supported video formats: mp4, mkv, avi, webm, mov, ogv
"""

import os

# Supported file extensions (lowercase)
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
    ".tiff",
    ".tif",
}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".ogv"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def is_image_file(filepath):
    """Check if a filepath has a supported image extension.

    Args:
        filepath: Path string to check.

    Returns:
        True if the file extension matches a supported image format.
    """
    _, ext = os.path.splitext(filepath)
    return ext.lower() in IMAGE_EXTENSIONS


def is_video_file(filepath):
    """Check if a filepath has a supported video extension.

    Args:
        filepath: Path string to check.

    Returns:
        True if the file extension matches a supported video format.
    """
    _, ext = os.path.splitext(filepath)
    return ext.lower() in VIDEO_EXTENSIONS


def is_media_file(filepath):
    """Check if a filepath is a supported image or video file.

    Args:
        filepath: Path string to check.

    Returns:
        True if the file is a supported media type.
    """
    _, ext = os.path.splitext(filepath)
    return ext.lower() in ALL_EXTENSIONS


class FileNavigator:
    """Navigates through media files in a directory.

    Maintains a sorted list of supported media files in the current
    directory and tracks the current position for prev/next navigation.
    """

    def __init__(self):
        """Initialize with empty file list."""
        self._files = []
        self._index = -1
        self._directory = None

    @property
    def current_file(self):
        """Return the full path of the currently selected file, or None."""
        if 0 <= self._index < len(self._files):
            return os.path.join(self._directory, self._files[self._index])
        return None

    @property
    def current_filename(self):
        """Return just the filename of the current file, or empty string."""
        if 0 <= self._index < len(self._files):
            return self._files[self._index]
        return ""

    @property
    def current_index(self):
        """Return the 1-based index of the current file (0 if none)."""
        if 0 <= self._index < len(self._files):
            return self._index + 1
        return 0

    @property
    def total_count(self):
        """Return the total number of media files in the directory."""
        return len(self._files)

    @property
    def has_files(self):
        """Return True if there are any media files loaded."""
        return len(self._files) > 0

    @property
    def is_current_image(self):
        """Return True if the current file is an image."""
        f = self.current_file
        return f is not None and is_image_file(f)

    @property
    def is_current_video(self):
        """Return True if the current file is a video."""
        f = self.current_file
        return f is not None and is_video_file(f)

    def load_directory(self, filepath):
        """Scan the directory containing filepath and set it as current.

        Builds a case-insensitive sorted list of supported media files
        in the same directory as the given filepath, and positions the
        index at the given file.

        Args:
            filepath: Full path to a file. Its parent directory will be scanned.

        Returns:
            True if the file was found in the directory listing.
        """
        filepath = os.path.abspath(filepath)
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        self._directory = directory
        self._files = []
        self._index = -1

        try:
            entries = os.listdir(directory)
        except OSError:
            return False

        # Filter to supported media files and sort case-insensitively
        media_files = [
            f
            for f in entries
            if os.path.isfile(os.path.join(directory, f)) and is_media_file(f)
        ]
        media_files.sort(key=lambda f: f.lower())

        self._files = media_files

        # Find the current file in the list
        try:
            self._index = self._files.index(filename)
            return True
        except ValueError:
            # File not in list (maybe unsupported); position at start
            if self._files:
                self._index = 0
            return False

    def go_next(self):
        """Move to the next file in the directory.

        Wraps around to the first file at the end.

        Returns:
            The full path of the new current file, or None.
        """
        if not self._files:
            return None
        self._index = (self._index + 1) % len(self._files)
        return self.current_file

    def go_prev(self):
        """Move to the previous file in the directory.

        Wraps around to the last file at the beginning.

        Returns:
            The full path of the new current file, or None.
        """
        if not self._files:
            return None
        self._index = (self._index - 1) % len(self._files)
        return self.current_file

    def go_to_file(self, filepath):
        """Navigate to a specific file, reloading directory if needed.

        If the file is in a different directory, reload the file list.
        Otherwise, just update the index.

        Args:
            filepath: Full path to the target file.

        Returns:
            True if navigation succeeded.
        """
        filepath = os.path.abspath(filepath)
        directory = os.path.dirname(filepath)

        if directory != self._directory:
            return self.load_directory(filepath)

        filename = os.path.basename(filepath)
        try:
            self._index = self._files.index(filename)
            return True
        except ValueError:
            return False

    def refresh(self):
        """Re-scan the current directory and try to maintain position.

        Useful after files are added or removed externally.
        """
        if self._directory is None:
            return

        current = self.current_filename
        try:
            entries = os.listdir(self._directory)
        except OSError:
            return

        media_files = [
            f
            for f in entries
            if os.path.isfile(os.path.join(self._directory, f)) and is_media_file(f)
        ]
        media_files.sort(key=lambda f: f.lower())
        self._files = media_files

        if current and current in self._files:
            self._index = self._files.index(current)
        elif self._files:
            self._index = max(0, min(self._index, len(self._files) - 1))
        else:
            self._index = -1

    def get_image_filter(self):
        """Create a Gtk.FileFilter for supported image formats.

        Returns:
            A Gtk.FileFilter for images.
        """
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        filt = Gtk.FileFilter()
        filt.set_name("Images")
        for ext in IMAGE_EXTENSIONS:
            filt.add_pattern(f"*{ext}")
            filt.add_pattern(f"*{ext.upper()}")
        return filt

    def get_all_media_filter(self):
        """Create a Gtk.FileFilter for all supported media formats.

        Returns:
            A Gtk.FileFilter for images and videos.
        """
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        filt = Gtk.FileFilter()
        filt.set_name("All Media (Images & Videos)")
        for ext in ALL_EXTENSIONS:
            filt.add_pattern(f"*{ext}")
            filt.add_pattern(f"*{ext.upper()}")
        return filt
