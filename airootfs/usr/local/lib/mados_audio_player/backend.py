"""
madOS Audio Player - mpv Backend
=================================

Provides audio playback functionality using mpv as the backend.
mpv is controlled via its JSON IPC protocol over a Unix socket,
which allows real-time control and status querying.

Features:
    - Play, pause, stop, seek
    - Volume and mute control
    - Track metadata retrieval
    - Position/duration tracking
    - Support for all audio formats via ffmpeg/mpv
"""

import json
import os
import socket
import subprocess
import tempfile
import threading
import time


class MpvBackend:
    """Audio playback backend using mpv via JSON IPC socket.

    Manages an mpv subprocess and communicates with it through
    a Unix domain socket using mpv's JSON IPC protocol.
    """

    # Audio file extensions supported by mpv/ffmpeg
    AUDIO_EXTENSIONS = {
        '.mp3', '.flac', '.ogg', '.opus', '.wav', '.aac', '.m4a',
        '.wma', '.ape', '.mka', '.webm', '.mp4', '.aiff', '.aif',
        '.alac', '.tta', '.wv', '.dsd', '.dsf', '.dff', '.ac3',
        '.amr', '.au', '.mid', '.midi', '.mod', '.s3m', '.xm',
        '.it', '.spc', '.vgm', '.nsf', '.snd', '.ra', '.rm',
    }

    def __init__(self):
        self._process = None
        self._socket_path = os.path.join(
            tempfile.gettempdir(),
            f"mados-audio-player-{os.getpid()}.sock"
        )
        self._sock = None
        self._lock = threading.Lock()
        self._running = False
        self._response_buf = b""

        # State
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.duration = 0.0
        self.position = 0.0
        self.volume = 100
        self.is_muted = False
        self.metadata = {}

    @staticmethod
    def _detect_audio_output():
        """Detect the best audio output for mpv.

        Checks if PipeWire is running (preferred on madOS), falls back
        to PulseAudio, then ALSA.
        """
        try:
            r = subprocess.run(
                ['pactl', 'info'],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0:
                if 'PipeWire' in r.stdout:
                    return 'pipewire'
                return 'pulse'
        except Exception:
            pass
        return 'alsa'

    def start(self):
        """Start the mpv process with JSON IPC socket."""
        if self._process and self._process.poll() is None:
            return

        # Clean up old socket
        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except OSError:
                pass

        cmd = [
            'mpv',
            '--idle=yes',
            '--no-video',
            '--no-terminal',
            '--really-quiet',
            f'--input-ipc-server={self._socket_path}',
            '--volume=100',
            '--audio-display=no',
            f'--ao={self._detect_audio_output()}',
            # Audio buffer: 1 second to prevent choppy playback on slow CPUs
            '--audio-buffer=1.0',
            # Demuxer readahead: 5 seconds of data buffered ahead
            '--demuxer-max-bytes=512KiB',
            '--demuxer-readahead-secs=5',
            # Enable gapless audio for smooth track transitions
            '--gapless-audio=yes',
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._running = True

            # Wait for socket to become available
            for _ in range(50):
                if os.path.exists(self._socket_path):
                    break
                time.sleep(0.1)

            self._connect()
        except FileNotFoundError:
            self._running = False
            raise RuntimeError("mpv not found. Please install mpv.")

    def _connect(self):
        """Connect to the mpv IPC socket."""
        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.settimeout(2.0)
            self._sock.connect(self._socket_path)
        except (socket.error, OSError):
            self._sock = None

    def _send_command(self, command, *args):
        """Send a command to mpv via IPC and return the response.

        Args:
            command: The mpv IPC command name.
            *args: Command arguments.

        Returns:
            The 'data' field from the mpv response, or None on error.
        """
        if not self._sock:
            self._connect()
            if not self._sock:
                return None

        msg = json.dumps({"command": [command] + list(args)}) + "\n"

        with self._lock:
            try:
                self._sock.sendall(msg.encode('utf-8'))
                response = self._read_response()
                if response is None:
                    return None
                # Check if command succeeded
                if response.get('error') == 'success':
                    # Return data if present, otherwise True to signal success
                    data = response.get('data')
                    return data if data is not None else True
                return response
            except (socket.error, OSError, json.JSONDecodeError):
                self._sock = None
                return None

    def _read_response(self):
        """Read and parse a JSON response from the mpv socket."""
        data = b""
        try:
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Look for complete JSON lines
                lines = data.split(b'\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        # Skip event messages, look for command response
                        if 'error' in parsed and parsed.get('error') == 'success':
                            return parsed
                        if 'error' in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        continue
                # If we got at least one complete line, we're done
                if len(lines) > 1:
                    break
        except socket.timeout:
            # Parse whatever we have
            if data:
                for line in data.split(b'\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        if 'error' in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        continue
        except (socket.error, OSError):
            pass
        return None

    def play_file(self, filepath):
        """Load and play an audio file.

        Args:
            filepath: Absolute path to the audio file.
        """
        if not os.path.isfile(filepath):
            return False

        self.current_file = filepath
        result = self._send_command("loadfile", filepath, "replace")
        if result is not None:
            self.is_playing = True
            self.is_paused = False
            return True
        return False

    def toggle_pause(self):
        """Toggle play/pause state."""
        self._send_command("cycle", "pause")
        self.is_paused = not self.is_paused

    def pause(self):
        """Pause playback."""
        if self.is_playing and not self.is_paused:
            self._send_command("set_property", "pause", True)
            self.is_paused = True

    def resume(self):
        """Resume playback."""
        if self.is_playing and self.is_paused:
            self._send_command("set_property", "pause", False)
            self.is_paused = False

    def stop(self):
        """Stop playback."""
        self._send_command("stop")
        self.is_playing = False
        self.is_paused = False
        self.position = 0.0
        self.duration = 0.0
        self.current_file = None

    def seek(self, position):
        """Seek to a position in seconds.

        Args:
            position: Target position in seconds.
        """
        self._send_command("seek", position, "absolute")

    def set_volume(self, volume):
        """Set volume level.

        Args:
            volume: Volume level (0-100).
        """
        self.volume = max(0, min(100, int(volume)))
        self._send_command("set_property", "volume", self.volume)

    def set_mute(self, muted):
        """Set mute state.

        Args:
            muted: True to mute, False to unmute.
        """
        self.is_muted = muted
        self._send_command("set_property", "mute", "yes" if muted else "no")

    def toggle_mute(self):
        """Toggle mute state."""
        self.set_mute(not self.is_muted)

    def get_property(self, prop):
        """Get a property value from mpv.

        Args:
            prop: The mpv property name.

        Returns:
            The property value, or None if unavailable.
        """
        return self._send_command("get_property", prop)

    def update_state(self):
        """Update internal state from mpv properties.

        Call this periodically to keep position/duration/metadata in sync.
        """
        try:
            pos = self.get_property("time-pos")
            if pos is not None and isinstance(pos, (int, float)):
                self.position = float(pos)

            dur = self.get_property("duration")
            if dur is not None and isinstance(dur, (int, float)):
                self.duration = float(dur)

            paused = self.get_property("pause")
            if isinstance(paused, bool):
                self.is_paused = paused

            idle = self.get_property("idle-active")
            if isinstance(idle, bool) and idle:
                self.is_playing = False

            meta = self.get_property("metadata")
            if isinstance(meta, dict):
                self.metadata = meta
        except Exception:
            pass

    def get_formatted_metadata(self):
        """Get formatted metadata for the current track.

        Returns:
            dict with 'title', 'artist', 'album' keys.
        """
        meta = self.metadata or {}
        title = (meta.get('title') or meta.get('TITLE')
                 or meta.get('Title') or '')
        artist = (meta.get('artist') or meta.get('ARTIST')
                  or meta.get('Artist') or '')
        album = (meta.get('album') or meta.get('ALBUM')
                 or meta.get('Album') or '')

        # Fallback to filename for title
        if not title and self.current_file:
            title = os.path.splitext(os.path.basename(self.current_file))[0]

        return {
            'title': title,
            'artist': artist,
            'album': album,
        }

    def get_audio_info(self):
        """Get audio format information.

        Returns:
            dict with 'format', 'bitrate', 'samplerate' keys.
        """
        info = {}
        try:
            codec = self.get_property("audio-codec-name")
            if codec:
                info['format'] = str(codec).upper()

            bitrate = self.get_property("audio-bitrate")
            if bitrate and isinstance(bitrate, (int, float)):
                info['bitrate'] = f"{int(bitrate / 1000)} kbps"

            samplerate = self.get_property("audio-params/samplerate")
            if samplerate and isinstance(samplerate, (int, float)):
                info['samplerate'] = f"{int(samplerate)} Hz"
        except Exception:
            pass
        return info

    def is_track_finished(self):
        """Check if the current track has finished playing.

        Returns:
            True if playback ended (idle and was playing).
        """
        idle = self.get_property("idle-active")
        return isinstance(idle, bool) and idle and self.current_file is not None

    def cleanup(self):
        """Clean up mpv process and socket."""
        self._running = False

        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

        if self._process and self._process.poll() is None:
            try:
                self._send_command("quit")
            except Exception:
                pass
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._process.kill()
                except OSError:
                    pass

        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except OSError:
                pass

    @classmethod
    def is_audio_file(cls, filepath):
        """Check if a file is a supported audio file.

        Args:
            filepath: Path to check.

        Returns:
            True if the file extension is a known audio format.
        """
        _, ext = os.path.splitext(filepath)
        return ext.lower() in cls.AUDIO_EXTENSIONS

    @classmethod
    def scan_directory(cls, dirpath, recursive=True):
        """Scan a directory for audio files.

        Args:
            dirpath: Directory path to scan.
            recursive: Whether to scan subdirectories.

        Returns:
            Sorted list of absolute paths to audio files found.
        """
        audio_files = []
        if recursive:
            for root, _dirs, files in os.walk(dirpath):
                for f in files:
                    fpath = os.path.join(root, f)
                    if cls.is_audio_file(fpath):
                        audio_files.append(fpath)
        else:
            try:
                for f in os.listdir(dirpath):
                    fpath = os.path.join(dirpath, f)
                    if os.path.isfile(fpath) and cls.is_audio_file(fpath):
                        audio_files.append(fpath)
            except OSError:
                pass
        audio_files.sort()
        return audio_files
