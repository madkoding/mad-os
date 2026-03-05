# Contributing to madOS

Thank you for your interest in contributing to madOS! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/mad-os.git`
3. Create a **feature branch**: `git checkout -b feature/your-feature-name`

## Development Workflow

### Branches
- `main` - Stable releases only
- `develop` - Beta/development builds
- Feature branches: `feature/`, `fix/`, `hotfix/`

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `hotfix` - Critical production fix
- `docs` - Documentation only
- `refactor` - Code refactoring
- `test` - Adding/updating tests
- `ci` - CI/CD changes

**Examples:**
```
feat(audio): add equalizer presets for headphones
fix(installer): correct disk partitioning on UEFI
hotfix(boot): fix kernel panic on AMD GPUs
docs: update build instructions
```

### Pull Request Process

1. Update documentation if needed
2. Ensure all tests pass
3. Update the CHANGELOG if applicable
4. Submit a PR targeting `develop` (for features) or `main` (for hotfixes)
5. Fill out the PR template completely

## Building the ISO

```bash
# Install dependencies
sudo pacman -Syu --needed archiso

# Build
sudo mkarchiso -v -w /tmp/work -o out .
```

## Code Standards

- Shell scripts: Use ShellCheck
- Python: Follow PEP 8, use type hints
- Configuration: YAML for configs, JSON for data files

## License

By contributing, you agree that your contributions will be licensed under the project's license.
