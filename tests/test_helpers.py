"""
Shared test utilities for madOS tests.

Provides common test helpers, mocks, and fixtures to reduce code duplication.
"""

import sys
import types

# Default GTK-related module names that most test files need mocked.
DEFAULT_GI_MODULES = ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango")


def create_gtk_mocks(extra_modules=()):
    """
    Create mock gi/GTK modules for headless testing.

    Returns a tuple of (gi_mock, repo_mock) that can be installed into
    sys.modules to allow importing modules that depend on GTK without
    requiring an actual GTK installation.

    *extra_modules* is an optional iterable of additional gi.repository
    sub-module names to stub (e.g. ``("Gst", "GstVideo")``).

    Usage::

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
        """No-op GTK widget stub for headless CI."""

        def __init__(self, *a, **kw):
            pass  # Intentionally empty: absorb any GTK constructor arguments

        def __init_subclass__(cls, **kw):
            pass  # Intentionally empty: allow subclassing without GTK side-effects

        def __getattr__(self, name):
            return _stub_func

    def _stub_func(*a, **kw):
        return _StubWidget()

    class _StubModule:
        def __getattr__(self, name):
            return _StubWidget

    for name in (*DEFAULT_GI_MODULES, *extra_modules):
        setattr(repo_mock, name, _StubModule())

    return gi_mock, repo_mock


def install_gtk_mocks(extra_modules=(), *, use_setdefault=False):
    """Create **and** install GTK mocks into ``sys.modules``.

    This is the one-liner replacement for the boilerplate that previously
    appeared at the top of every test file.

    Parameters
    ----------
    extra_modules:
        Additional gi.repository sub-module names to stub.
    use_setdefault:
        If *True*, use ``sys.modules.setdefault`` instead of direct
        assignment so that previously-installed real modules are kept.
    """
    gi_mock, repo_mock = create_gtk_mocks(extra_modules)
    if use_setdefault:
        sys.modules.setdefault("gi", gi_mock)
        sys.modules.setdefault("gi.repository", repo_mock)
    else:
        sys.modules["gi"] = gi_mock
        sys.modules["gi.repository"] = repo_mock
    return gi_mock, repo_mock
