# Persistence Testing Documentation

## Overview

This directory contains comprehensive tests for the madOS persistence system. The tests cover:

- **Bash script syntax validation** - All scripts must pass `bash -n` syntax check
- **Function coverage tests** - 100% coverage of individual functions
- **find_iso_device tests** - All detection methods with mocked environments
- **Partition safety tests** - MBR/GPT validation, gap detection, boundary backup
- **Integration tests** - Full Docker-based testing of persistence flow

## Test Structure

```
tests/
├── test_persistence_scripts.py      # Syntax and structure validation
├── test_persistence_validation.py   # Validation fixes and safety checks  
├── test_persistence_coverage.py     # Function coverage tests
├── test_find_iso_device.py         # ISO device detection scenarios
├── test_persistence_safety.py      # Partition safety mechanisms
├── test-liveusb-persistence.sh     # Full integration tests in Docker
├── entrypoint.sh                   # Docker test runner
└── README_TESTS.md                 # This file
```

## Running Tests

### Locally (with Docker)

```bash
# Build test Docker image
docker build -f Dockerfile.test -t mados-test .

# Run tests in container
docker run --rm -v $(pwd):/build mados-test

# Or run interactively for debugging
docker run --rm -it -v $(pwd):/build mados-test /bin/bash
```

### Directly (on Arch Linux)

```bash
# Install dependencies
sudo pacman -S python python-pytest python-pytest-cov \
    bash parted e2fsprogs dosfstools util-linux systemd

# Run all tests
cd tests
pytest -v --tb=short

# Run specific test file
pytest test_find_iso_device.py -v

# Run with coverage
pytest --cov=../airootfs/usr/local/bin --cov-report=term-missing

# Run functional tests
bash test-liveusb-persistence.sh
```

### CI/CD

Tests run in GitHub Actions via `.github/workflows/test-persistence.yml`:

1. **Unit tests** - Python validation tests
2. **Integration tests** - Docker-based full system tests
3. **Coverage** - Generate and upload coverage report
4. **Documentation** - Verify docs are updated

## Test Coverage Targets

### Script Coverage

- `setup-persistence.sh`: 100% function coverage
- `mados-persistence`: 100% function coverage
- `mados-persist-init.sh` (embedded): 100% coverage

### Coverage Categories

1. **Syntax validation** - All bash scripts pass `bash -n`
2. **Function tests** - Each function tested with valid/invalid inputs
3. **Edge cases** - Error handling, missing files, invalid inputs
4. **Integration** - Full workflow from ISO detection to persistence enabled

### Key Functions Tested

#### setup-persistence.sh

- `is_usb_device()` - USB detection via multiple methods
- `is_optical_device()` - CD/DVD detection
- `strip_partition()` - Device name normalization
- `find_iso_device()` - ISO detection (5 methods)
- `find_iso_partition()` - ISO partition lookup
- `find_persist_partition()` - Persistence partition lookup
- `get_free_space()` - Free space calculation
- `create_persist_partition()` - Partition creation with safety checks
- `install_persist_files()` - Install init script and service
- `setup_persistence()` - Main function (full workflow)

#### mados-persistence

- `check_live_env()` - Live environment validation
- `find_iso_device()` - ISO detection (simplified)
- `find_persist_partition()` - Partition lookup
- `show_status()` - Display persistence status
- `enable_persistence()` - Enable persistence
- `disable_persistence()` - Disable persistence
- `remove_persistence()` - Remove persistence partition

## Test Scenarios

### find_iso_device Tests

1. **img_dev=UUID=xxxxx** - UUID format detection
2. **img_dev=PARTUUID=xxxxx** - PARTUUID format detection
3. **img_dev=/dev/xxx** - Direct path detection
4. **archisolabel=xxxxx** - Label-based detection
5. **Loopback resolution** - /dev/loop → backing file
6. **Boot files detection** - vmlinuz-linux detection
7. **iso9660 fallback** - Filesystem type detection
8. **Label search** - Legacy label matching
9. **No detection** - Graceful failure when no ISO found

### create_persist_partition Safety Tests

1. **ISO device verification** - Only works on ISO device
2. **MBR partition limit** - Rejects 5th partition on MBR
3. **GPT support** - Allows >4 partitions on GPT
4. **Partition table type** - Validates msdos/gpt/unknown
5. **Partition number gaps** - Detects isohybrid scenarios
6. **Device node creation** - Creates nodes in containers
7. **Boundary backup** - Saves partition boundaries before mkpart
8. **Label verification** - Verifies ext4 label after mkfs
9. **Error cleanup** - Removes partition on mkfs failure

### Integration Tests

1. **Fresh USB** - Create partition, install files, mount overlays
2. **Existing persistence** - Detect existing partition
3. **Data persistence** - Write files, reboot, verify survival
4. **Reboot simulation** - Unmount + re-run init script
5. **Second boot** - Verify detection without recreation
6. **Optical media** - Detect and skip optical drives

## Coverage Goal: 100%

### Current Coverage

Run coverage report:
```bash
pytest --cov=../airootfs/usr/local/bin --cov-report=term-missing
```

### Coverage Breakdown

- **setup-persistence.sh**: Target 100%
  - All 15+ functions tested
  - All 5 detection methods covered
  - All safety checks validated
  - Error handling verified

- **mados-persistence**: Target 100%
  - All 7 functions tested
  - All 4 commands covered (status/enable/disable/remove)
  - All safety checks validated

- **mados-persist-init.sh**: Target 100%
  - All 5 functions tested
  - Overlayfs setup verified
  - Bind mount verified
  - Service restart tested

## Debugging Tests

### Common Issues

1. **Device nodes not created** - Check udevadm settle, mknod fallback
2. **Partition not detected** - Check label, lsblk cache, blkid scan
3. **Mount fails** - Check filesystem type, label, free space
4. **ISO not found** - Check all 5 detection methods

### Verbose Output

```bash
# Run with verbose output
pytest -vv --tb=long

# Run single test
pytest -k "test_img_dev_uuid" -vv

# Stop on first failure
pytest -x

# Run with coverage and open report
pytest --cov=../airootfs/usr/local/bin --cov-report=html
xdg-open coverage_html/index.html
```

### Docker Debugging

```bash
# Build with debug
docker build -f Dockerfile.test -t mados-test-debug .

# Run interactively
docker run --rm -it -v $(pwd):/build mados-test-debug /bin/bash

# Inside container
cd /build
bash tests/entrypoint.sh
```

## Adding New Tests

### For New Function

1. Create test in appropriate file
2. Test valid inputs
3. Test invalid inputs
4. Test edge cases
5. Test error handling

Example:
```python
def test_new_function_valid_input():
    result = subprocess.run([...])
    assert result.returncode == 0
    assert "expected" in result.stdout

def test_new_function_invalid_input():
    result = subprocess.run([...])
    assert result.returncode != 0
```

### For New Feature

1. Update test-liveusb-persistence.sh
2. Add scenario to integration tests
3. Update documentation
4. Verify coverage stays at 100%

## Performance Requirements

Tests should:

- Complete in <10 minutes total
- Run in parallel where possible
- Not require Internet access (except pip install)
- Not require sudo on host (Docker handles it)
- Be deterministic (same results every run)

## Requirements

### Test Container

- Arch Linux base
- Bash 5.0+
- Python 3.8+
- parted 3.4+
- e2fsprogs 1.45+
- util-linux 2.36+
- systemd 247+

### Host (for development)

- Docker 20.10+
- Python 3.8+
- pytest 6.2+

## Maintenance

### Updating Tests

1. Edit test file
2. Run locally: `pytest -v`
3. Run in Docker: `docker run mados-test`
4. Update coverage report
5. Update documentation

### Adding Dependencies

1. Update Dockerfile.test
2. Rebuild image
3. Test

## License

Same as madOS project - see LICENSE file.
