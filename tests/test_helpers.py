"""
Shared test utilities for madOS tests.

Provides common test helpers, mocks, and fixtures to reduce code duplication.
"""

import types


def create_gtk_mocks():
    """
    Create mock gi/GTK modules for headless testing.
    
    Returns a tuple of (gi_mock, repo_mock) that can be installed into sys.modules
    to allow importing installer modules that depend on GTK without requiring
    an actual GTK installation.
    
    Usage:
        gi_mock, repo_mock = create_gtk_mocks()
        sys.modules["gi"] = gi_mock
        sys.modules["gi.repository"] = repo_mock
    """
    gi_mock = types.ModuleType("gi")
    gi_mock.require_version = lambda *a, **kw: None

    repo_mock = types.ModuleType("gi.repository")

    class _StubMeta(type):
        def __getattr__(cls, name):
            return _StubWidget

    class _StubWidget(metaclass=_StubMeta):
        def __init__(self, *a, **kw):
            pass

        def __init_subclass__(cls, **kw):
            pass

        def __getattr__(self, name):
            return _stub_func

    def _stub_func(*a, **kw):
        return _StubWidget()

    class _StubModule:
        def __getattr__(self, name):
            return _StubWidget

    for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango"):
        setattr(repo_mock, name, _StubModule())

    return gi_mock, repo_mock
