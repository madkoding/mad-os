# Testing Guide: Persistent Storage Feature

## Overview

This guide describes how to test the persistent storage feature in madOS.

## Prerequisites

1. Build the madOS ISO with the persistence changes
2. USB drive with at least 8GB capacity (16GB+ recommended)
3. Physical or virtual machine for testing

## Building the ISO

```bash
# Clone repository
git clone https://github.com/madkoding/mad-os
cd mad-os

# Checkout the persistence branch (if not merged to main yet)
git checkout copilot/add-persistent-memory-space

# Or if merged to main:
# git checkout main

# Build ISO (requires Arch Linux)
sudo mkarchiso -v -w work/ -o out/ .

# ISO will be in out/madOS-*.iso
```

## Test Plan

### Test 1: Auto-Configuration with Free Space

**Objective**: Verify persistence auto-configures when USB has free space

**Steps**:
1. Write ISO to USB with extra space:
   ```bash
   # For 16GB USB, use direct dd
   sudo dd if=out/madOS-*.iso of=/dev/sdX bs=4M status=progress oflag=sync
   # This leaves ~12GB free space
   ```

2. Boot from USB

3. After boot, check persistence status:
   ```bash
   mados-persistence status
   ```

**Expected Result**:
- Message: "Persistence is configured"
- Shows device, size, usage, mount point
- Partition labeled `MADOS_PERSIST` exists
- Service log shows successful creation:
  ```bash
  cat /var/log/mados-persistence.log
  ```

### Test 2: Manual Persistence Enable

**Objective**: Verify manual persistence setup works

**Steps**:
1. Write ISO to USB without extra space (or remove persistence partition)
2. Boot from USB
3. Check initial status:
   ```bash
   mados-persistence status
   # Should show "Persistence not configured"
   ```

4. Use parted to create free space (or use larger USB)
5. Enable persistence:
   ```bash
   sudo mados-persistence enable
   ```

**Expected Result**:
- Confirmation prompts appear
- Partition created successfully
- Status shows enabled
- Log file shows creation process

### Test 3: Data Persistence Across Reboots

**Objective**: Verify data actually persists

**Steps**:
1. Boot from USB with persistence enabled
2. Create test file:
   ```bash
   echo "Test persistence" > ~/test-file.txt
   cat ~/test-file.txt
   ```

3. Install a package:
   ```bash
   sudo pacman -S htop
   which htop  # Should show /usr/bin/htop
   ```

4. Modify system config:
   ```bash
   echo "alias test='echo persistence works'" >> ~/.bashrc
   source ~/.bashrc
   test  # Should print "persistence works"
   ```

5. Reboot the system:
   ```bash
   sudo reboot
   ```

6. After reboot, verify:
   ```bash
   # Check file
   cat ~/test-file.txt  # Should show "Test persistence"
   
   # Check package
   which htop  # Should still be installed
   
   # Check config
   test  # Should still print "persistence works"
   ```

**Expected Result**:
- All changes persist after reboot
- Files remain
- Installed packages remain
- Configurations remain

### Test 4: Persistence Disable/Enable

**Objective**: Verify disable/remove functionality

**Steps**:
1. Boot with persistence enabled
2. Check status:
   ```bash
   mados-persistence status
   ```

3. Disable persistence:
   ```bash
   sudo mados-persistence disable
   ```

4. Verify it's unmounted:
   ```bash
   mados-persistence status  # Should show not mounted
   ```

5. Reboot and verify it re-enables:
   ```bash
   sudo reboot
   # After boot:
   mados-persistence status  # Should be mounted again
   ```

**Expected Result**:
- Disable unmounts but doesn't delete
- Re-enables on next boot
- Data preserved

### Test 5: Persistence Removal

**Objective**: Verify permanent removal works

**Steps**:
1. Boot with persistence enabled
2. Note current persistence device:
   ```bash
   mados-persistence status
   ```

3. Remove persistence:
   ```bash
   sudo mados-persistence remove
   # Type "yes" to confirm
   ```

4. Verify removal:
   ```bash
   mados-persistence status  # Should show not configured
   lsblk  # MADOS_PERSIST partition should be gone
   ```

**Expected Result**:
- Partition completely removed
- Space reclaimed
- Status shows not configured

### Test 6: Boot Menu Verification

**Objective**: Verify boot menu shows persistence info

**Steps**:
1. Reboot and enter boot menu
2. Check GRUB/Syslinux menu entries

**Expected Result**:
- Menu shows "madOS Live (with Persistence)"
- Help text mentions auto-configuration
- Both UEFI and BIOS menus updated

### Test 7: Welcome Message

**Objective**: Verify welcome message appears

**Steps**:
1. Boot from USB
2. Observe TTY1 after login

**Expected Result**:
- Welcome message appears with madOS logo
- Shows persistence info
- Shows quick commands
- If persistence enabled, shows "✓ Persistent storage is enabled"

### Test 8: Small USB Drive (No Free Space)

**Objective**: Verify graceful handling when no space available

**Steps**:
1. Write ISO to small USB (4GB) that fills completely
2. Boot from USB
3. Check status:
   ```bash
   mados-persistence status
   cat /var/log/mados-persistence.log
   ```

**Expected Result**:
- Status shows not configured
- Log shows insufficient space message
- System boots normally without errors
- User can manually enable later if space freed

### Test 9: Partition Space Usage

**Objective**: Verify dynamic sizing works correctly

**Steps**:
1. Test with different USB sizes:
   - 8GB USB
   - 16GB USB
   - 32GB USB

2. For each, check partition size:
   ```bash
   mados-persistence status
   lsblk -o NAME,SIZE,LABEL
   ```

**Expected Result**:
- 8GB → ~4-5GB persistence
- 16GB → ~12-13GB persistence
- 32GB → ~28-29GB persistence
- Uses all available free space

### Test 10: Service Status

**Objective**: Verify systemd service works correctly

**Steps**:
1. Boot from USB
2. Check service status:
   ```bash
   systemctl status mados-persistence.service
   ```

3. Check service logs:
   ```bash
   journalctl -u mados-persistence.service
   ```

**Expected Result**:
- Service shows as "active (exited)" or similar
- No errors in logs
- Shows successful execution

## Edge Cases to Test

### Edge Case 1: Corrupted Persistence Partition

**Steps**:
1. Create persistence partition
2. Force corruption (or simulate):
   ```bash
   sudo umount /dev/sdX3
   # Corrupt filesystem (careful!)
   sudo dd if=/dev/urandom of=/dev/sdX3 bs=1M count=10
   ```
3. Reboot and observe

**Expected**: System should handle gracefully, log error

### Edge Case 2: Multiple madOS USBs

**Steps**:
1. Create two madOS USBs with persistence
2. Boot from each alternately
3. Verify each maintains separate persistence

**Expected**: Each USB has independent persistence

### Edge Case 3: BIOS vs UEFI Boot

**Steps**:
1. Boot same USB in BIOS mode
2. Enable persistence
3. Boot same USB in UEFI mode
4. Verify persistence still works

**Expected**: Persistence works regardless of boot mode

## Verification Checklist

After testing, verify:

- [ ] Auto-configuration works with free space
- [ ] Manual enable works correctly
- [ ] Data persists across reboots
- [ ] Packages persist across reboots
- [ ] Config files persist across reboots
- [ ] Disable/enable cycle works
- [ ] Remove permanently deletes partition
- [ ] Boot menu shows persistence info
- [ ] Welcome message appears
- [ ] Handles no free space gracefully
- [ ] Dynamic sizing uses full available space
- [ ] Systemd service runs successfully
- [ ] Works on both BIOS and UEFI
- [ ] Logs provide useful debugging info
- [ ] Multiple USBs maintain separate persistence

## Documentation Verification

Check that documentation is:

- [ ] Accessible in live environment: `/usr/share/doc/madOS/PERSISTENCE.md`
- [ ] Available in repository: `docs/PERSISTENCE.md`
- [ ] Referenced in README.md
- [ ] Updated in CLAUDE.md

## Performance Testing

Test performance with persistence:

1. **Boot Time**:
   - Measure boot time without persistence
   - Measure boot time with persistence
   - Should be similar (maybe 1-2s difference)

2. **File Operations**:
   - Test creating/reading/writing files
   - Should be reasonable for USB speeds

3. **Package Operations**:
   - Test installing large packages
   - Test upgrading system
   - Should work normally

## Troubleshooting Tests

Verify troubleshooting steps in documentation:

1. Test fsck on persistence partition
2. Test manual mounting
3. Verify log file locations
4. Test recovery from common issues

## Reporting Issues

If any test fails, report with:

1. Test number/name that failed
2. USB size and type
3. Boot mode (UEFI/BIOS)
4. Error messages from:
   - `/var/log/mados-persistence.log`
   - `journalctl -u mados-persistence.service`
   - `mados-persistence status`
5. Output of `lsblk` and `parted /dev/sdX print`

## Success Criteria

All tests should pass with:
- No errors in logs
- Expected behavior matches actual behavior
- User experience is smooth and intuitive
- Documentation is clear and helpful
