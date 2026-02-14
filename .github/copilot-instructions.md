# Copilot Instructions for madOS

## Project Overview

madOS is an AI-orchestrated Arch Linux distribution built using `archiso`. It targets low-RAM systems (1.9GB) with Intel Atom processors and integrates OpenCode as an AI assistant. The project produces a custom live/installer ISO with a GTK graphical installer and pre-configured Sway desktop environment.

## Build Commands

```bash
# Build the ISO (requires Arch Linux with archiso installed)
sudo pacman -S archiso
sudo mkarchiso -v -w work/ -o out/ .
```

- Build requires ~10GB free disk space
- Build artifacts go in `work/` (safe to delete after build)
- Final ISO appears in `out/`
- Build time: ~10-20 minutes

## Testing

### Unit Tests (pytest)

```bash
# Install test dependencies
python3 -m pip install pytest

# Run all unit tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_boot_scripts.py -v
```

### Integration Tests (require Docker with Arch Linux container)

```bash
# USB Persistence tests
docker run --privileged --rm -v $(pwd):/build archlinux:latest bash /build/tests/test-liveusb-persistence.sh

# First-boot simulation
docker run --privileged --rm -v $(pwd):/build archlinux:latest bash /build/tests/test-first-boot-simulation.sh

# Installer Python validation
docker run --privileged --rm -v $(pwd):/build archlinux:latest bash /build/tests/test-installer-python-validation.sh
```

### Test Conventions

- Tests use Python `unittest` framework via `pytest`
- Test files are in `tests/` directory, named `test_*.py` (unit) or `test-*.sh` (integration)
- GTK-dependent tests use mock modules from `tests/test_helpers.py` for headless execution
- Paths in tests reference `REPO_DIR` relative to the test file location

## Repository Structure

### Core archiso Files

- `profiledef.sh` — ISO metadata (name, publisher, version) and file permissions
- `packages.x86_64` — Package list for the ISO (one package per line)
- `pacman.conf` — Pacman configuration for the build

### Boot Configuration

- `grub/` — GRUB bootloader config (UEFI)
- `syslinux/` — Syslinux config (BIOS)
- `efiboot/` — EFI boot loader configuration

### Root Filesystem (`airootfs/`)

- `airootfs/etc/` — System configuration (sysctl, systemd, skel configs)
- `airootfs/usr/local/bin/` — Custom scripts and executables
- `airootfs/usr/local/lib/` — Python library modules for tools

### Key Scripts

- `airootfs/usr/local/bin/install-mados` — Installer launcher
- `airootfs/usr/local/bin/install-mados-gtk.py` — GTK graphical installer (Python + GTK3)
- `airootfs/usr/local/lib/mados_installer/` — Installer Python modules
- `airootfs/usr/local/bin/setup-opencode.sh` — OpenCode setup script
- `airootfs/usr/local/bin/setup-persistence.sh` — Persistent storage setup

### Documentation

- `docs/` — Project documentation and GitHub Pages site
- `docs/PERSISTENCE.md` — Persistent storage documentation
- `docs/DEBUGGING.md` — Debugging guide

## Code Style and Conventions

- **Shell scripts**: Use `#!/usr/bin/env bash`, follow shellcheck guidelines
- **Python scripts**: Use `#!/usr/bin/env python3`, standard library preferred
- **GTK installer**: Uses Nord color scheme (polar night background, frost accents)
- **File permissions**: New executable scripts must be added to `profiledef.sh` `file_permissions` array
- **Package additions**: Add one package per line to `packages.x86_64`
- **System name**: "madOS" (all lowercase in filenames, styled in display text)

## CI/CD Pipeline

The CI/CD pipeline (`.github/workflows/ci-cd.yml`) runs in stages:

1. **Stage 1** — Unit tests (pytest, parallel matrix) and integration tests run in parallel
2. **Stage 2** — Installer validation in Arch container (requires Stage 1)
3. **Stage 3** — ISO build with mkarchiso (only on tags or manual trigger)
4. **Stage 4** — Upload to Internet Archive
5. **Stage 5** — GitHub Release and website update (stable releases only)

GitHub Pages deployment is in `.github/workflows/pages.yml`.

## Important Guidelines

- Keep `python`, `python-gobject`, and `gtk3` in `packages.x86_64` (required for the installer)
- RAM optimizations target 1.9GB systems — avoid adding heavy packages without justification
- When adding new scripts to `airootfs/usr/local/bin/`, update `profiledef.sh` with proper permissions
- When modifying the installer, update tests in `tests/test_installer_config.py`
- Desktop configs live in `airootfs/etc/skel/.config/` (Sway, Waybar, Foot, Wofi)
- ZRAM and kernel tuning configs are in `airootfs/etc/sysctl.d/` and `airootfs/etc/systemd/`
