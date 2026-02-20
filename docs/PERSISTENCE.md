# madOS Persistent Storage

madOS live USB can be configured with persistent storage, allowing you to save changes, install packages, and keep your data across reboots.

**Note**: Persistence is only available when booting from USB devices. When booting from ISO files (e.g., in VMs or from CD/DVD), persistence is automatically disabled to prevent boot issues.

## Overview

Persistent storage creates a partition on your USB drive (labeled `persistence`) that stores all system changes using **overlayfs** and a **bind mount**:

| Directory | Method | What persists |
|-----------|--------|---------------|
| `/etc` | overlayfs | System configuration |
| `/usr` | overlayfs | Installed packages, binaries, libraries |
| `/var` | overlayfs | Package cache, logs, databases |
| `/opt` | overlayfs | Optional packages |
| `/home` | bind mount | User files, dotfiles, application data |

## How It Works

### Architecture

```
USB Drive:
├── Partition 1: ISO Data (read-only, iso9660)
├── Partition 2: EFI System Partition (vfat)
└── Partition 3: persistence (ext4) ← Your persistent storage
    ├── mados-persist-init.sh        ← Init script (runs on every boot)
    ├── mados-persistence.service    ← systemd unit (stored here)
    ├── overlays/
    │   ├── etc/upper/ + work/       ← overlayfs layers for /etc
    │   ├── usr/upper/ + work/       ← overlayfs layers for /usr
    │   ├── var/upper/ + work/       ← overlayfs layers for /var
    │   └── opt/upper/ + work/       ← overlayfs layers for /opt
    └── home/                        ← bind-mounted to /home
```

### Boot Sequence

1. systemd starts `mados-persistence.service` (before display-manager)
2. Service runs `setup-persistence.sh`:
   - Detects USB device and persistence partition
   - On first boot: creates partition, formats ext4, installs init script
   - On subsequent boots: mounts partition, runs init script
3. Init script (`/mnt/persistence/mados-persist-init.sh`):
   - Mounts persistence partition at `/mnt/persistence`
   - Sets up overlayfs for `/etc`, `/usr`, `/var`, `/opt`
   - Runs `ldconfig` after `/usr` overlay
   - Bind-mounts `/home` from persistence partition

### What's Persistent

✓ **Persistent** (saved across reboots):
- Installed packages via pacman (stored in /usr overlay)
- System configuration changes (/etc overlay)
- User files and documents (/home bind mount)
- Application settings and preferences
- Package cache and databases (/var overlay)

✗ **Not Persistent** (reset each boot):
- Running processes
- Temporary files in `/tmp`
- Kernel modules (ISO kernel is used)

## Enabling Persistence

### Automatic (Recommended)

Persistence is automatically set up on first boot if there is free space on your USB drive:

1. Boot from madOS USB
2. Wait for the system to start (overlays are mounted before the display manager)
3. Check persistence status:
   ```bash
   mados-persistence status
   ```

### Manual Setup

If automatic setup didn't work or you want to explicitly enable it:

```bash
sudo mados-persistence enable
```

This will:
- Detect your USB device
- Check available free space
- Create a persistence partition using all free space
- Format it with ext4 filesystem (label: `persistence`)
- Set up overlayfs mounts for /etc, /usr, /var, /opt
- Bind-mount /home
- Install init script and service into the persistence partition

## Requirements

- At least 100MB of free space on your USB drive
- **Booting from a USB device** (not ISO/CD/DVD)
- Running from live USB environment
- Root privileges for setup

**Important**: Persistence is not available when booting from ISO files in VMs or from CD/DVD media.

## Usage

### Check Status

```bash
mados-persistence status
```

Shows:
- Whether persistence is enabled
- Partition size and usage
- Mount point
- Available space
- Overlay mount status for /etc, /usr, /var, /opt
- Bind mount status for /home

### Disable for Current Session

To temporarily disable persistence without removing data:

```bash
sudo mados-persistence disable
```

Persistence will be re-enabled on next boot.

### Remove Persistence

To permanently remove the persistence partition and free up space:

```bash
sudo mados-persistence remove
```

⚠️ **Warning**: This permanently deletes all persistent data!

## How It Works

### Partition Layout

When you write madOS to a USB drive and enable persistence:

```
USB Drive:
├── Partition 1: ISO Data (read-only)
├── Partition 2: EFI System Partition
└── Partition 3: persistence (ext4) <- Your persistent storage
```

### Dynamic Size

The persistence partition automatically uses **all remaining free space** on your USB drive:

- 8GB USB → ~4-5GB for persistence
- 16GB USB → ~12-13GB for persistence
- 32GB USB → ~28-29GB for persistence
- 64GB USB → ~60-61GB for persistence

### What's Persistent

✓ **Persistent** (saved across reboots):
- Installed packages via pacman (in /usr overlay)
- System configuration changes (in /etc overlay)
- Files in home directory (bind mount)
- Package cache and databases (in /var overlay)
- Optional software (in /opt overlay)

✗ **Not Persistent** (reset each boot):
- Running processes
- Temporary files in `/tmp`
- Kernel modules (ISO kernel is used)

## Boot Options

### GRUB Menu

madOS provides boot options for persistence:

- **madOS Live** - Standard boot with persistence (if configured)
- **madOS Live (Safe Graphics)** - Safe mode with persistence

### Boot Parameters

Advanced users can customize persistence behavior:

- `cow_spacesize=512M` - RAM overlay size (default: 256M)
- Label `persistence` is used to identify the persistence partition

## Troubleshooting

### Persistence Not Available (ISO/VM Boot)

**Problem**: Persistence not available when booting in VM or from CD/DVD

**Explanation**: Persistence is only supported on USB devices. When you boot from an ISO file (in VirtualBox, QEMU, etc.) or from a CD/DVD, the system automatically detects this and disables persistence to prevent boot issues.

**Solutions**:
1. Write the ISO to a USB drive using:
   ```bash
   sudo dd if=madOS.iso of=/dev/sdX bs=4M conv=fsync oflag=direct status=progress
   ```
2. For VMs, use USB passthrough to pass a real USB device to the VM
3. For testing in VMs without persistence, boot normally - all changes will be stored in RAM

**Check logs** to confirm:
```bash
cat /var/log/mados-persistence.log
```
You should see: "Device /dev/sdX is not a USB device (likely ISO/CD/VM), skipping persistence setup"

### Persistence Not Auto-Created

**Problem**: Persistence partition wasn't created automatically

**Solutions**:
1. Check for free space:
   ```bash
   lsblk
   parted /dev/sdX print free
   ```

2. Manually enable:
   ```bash
   sudo mados-persistence enable
   ```

3. Check logs:
   ```bash
   cat /var/log/mados-persistence.log
   ```

### Insufficient Space

**Problem**: Not enough free space on USB

**Solutions**:
1. Use a larger USB drive (16GB+ recommended)
2. Reduce ISO partition size when creating USB
3. Use manual partition layout with `dd` and `parted`

### Persistence Partition Not Mounting

**Problem**: Partition exists but not mounting

**Solutions**:
1. Check partition integrity:
   ```bash
   sudo fsck.ext4 /dev/sdX3
   ```

2. Manually mount:
   ```bash
   sudo mount -L persistence /mnt
   ```

3. Check systemd service:
   ```bash
   systemctl status mados-persistence.service
   ```

### Partition Full

**Problem**: No space left on persistence partition

**Solutions**:
1. Check usage:
   ```bash
   mados-persistence status
   df -h
   ```

2. Clean package cache:
   ```bash
   sudo pacman -Sc
   ```

3. Remove orphaned packages:
   ```bash
   sudo pacman -Rns $(pacman -Qtdq)
   ```

4. Clear user cache:
   ```bash
   rm -rf ~/.cache/*
   ```

### Isohybrid Partition Layout Issues (Advanced)

**Problem**: Partition creation fails or ISO data is overwritten on isohybrid USBs

**Background**: Some USB boot methods create an "isohybrid" layout where:
- Partition 1 (ISO data) exists as a device node (`/dev/sda1`) but is NOT in the partition table
- Only partition 2 (EFI) appears in the partition table
- This creates a "gap" that some partitioning tools try to fill

**Symptoms**:
- Log shows "WARNING: Found device partition nodes not in partition table"
- Log shows "WARNING: Partition numbering gaps detected"
- Partition creation uses `sfdisk` instead of `parted`

**How madOS Handles This**:
The partition creation script automatically detects this situation and:
1. Enumerates all device partition nodes (`/dev/sda1`, `/dev/sda2`, etc.)
2. Compares with partition table entries from `parted`
3. Identifies gaps (partitions in devices but not in table)
4. Uses `sfdisk` with explicit partition numbers instead of `parted`
5. Creates the new partition with a safe number (e.g., 3) that won't conflict

**If you see errors**:
Check the log for details:
```bash
cat /var/log/mados-persistence.log | grep -A5 "device partition nodes"
```

Expected safe behavior:
- Script detects gaps and switches to `sfdisk`
- New partition is numbered to avoid conflicts
- Existing partitions (ISO data, EFI) remain untouched

**If using parted manually** (not recommended):
- Never assume partition numbers will match your expectations
- Always check which partitions exist as device nodes before creating new ones
- Prefer `sfdisk` with explicit partition numbers for isohybrid layouts

## Best Practices

### 1. Regular Backups

Even with persistence, back up important data:
```bash
# Backup to external drive
rsync -av ~/Documents /mnt/backup/
```

### 2. Monitor Space

Check available space regularly:
```bash
mados-persistence status
```

### 3. Clean Up Periodically

Remove unused packages:
```bash
sudo pacman -Rns $(pacman -Qtdq)
sudo pacman -Sc
```

### 4. Graceful Shutdown

Always shut down properly to avoid data corruption:
```bash
sudo shutdown -h now
```

## Performance Considerations

### Speed

- **First Boot**: May be slower while creating partition
- **Subsequent Boots**: Slightly slower than non-persistent due to overlay
- **File Operations**: Performance depends on USB drive speed

### USB-Optimized Mount Options

madOS automatically applies performance optimizations to reduce read lags on USB storage:

**Mount Options:**
- **noatime**: Disables access time updates on file reads (eliminates write operations during reads)
- **commit=60**: Increases journal commit interval from 5s to 60s (reduces metadata sync frequency)
- **data=writeback**: Allows data writes without ordering relative to metadata (improves throughput)

**Filesystem Creation Options:**
- **lazy_itable_init=0**: Completes inode table initialization during format (avoids background delays)
- **lazy_journal_init=0**: Completes journal initialization during format (consistent performance)
- **-m 1**: Only 1% reserved blocks instead of 5% (more usable space on USB)

These options prioritize performance over data safety, which is acceptable for a live system where:
- The system is temporary by nature
- Important data should be backed up externally
- A power loss would require reboot anyway

**Result**: Significantly reduced read lag and improved overall I/O performance on USB devices.

### Recommendations

- Use USB 3.0 or faster for best performance
- Use high-quality USB drives with good write speeds
- Avoid filling the persistence partition completely
- For critical data, maintain external backups

## Advanced Usage

### Manual Partition Creation

For advanced users who want custom partition layouts:

```bash
# 1. Write ISO to USB (leaves free space)
sudo dd if=madOS.iso of=/dev/sdX bs=4M conv=fsync oflag=direct status=progress

# 2. Create persistence partition
sudo parted /dev/sdX mkpart primary ext4 4GB 100%

# 3. Format with label
sudo mkfs.ext4 -L persistence /dev/sdX3

# 4. Boot madOS - persistence will be auto-detected and overlays configured
```

### Multiple USB Drives

Each madOS USB can have its own independent persistence:

- Drive A: Development setup
- Drive B: Production environment
- Drive C: Testing configuration

Each maintains separate persistent storage.

### Persistence with Installation

Persistence is only for live USB environments. Once you install madOS to a hard drive, everything is naturally persistent.

## Security Notes

⚠️ **Important Security Considerations**:

1. **Encryption**: The persistence partition is NOT encrypted by default
2. **Lost USB**: Anyone with physical access can read your data
3. **Secure Data**: For sensitive data, consider:
   - Full disk encryption (LUKS)
   - Encrypted containers (VeraCrypt)
   - Cloud storage with encryption

## FAQ

**Q: Does persistence slow down the system?**  
A: Minimal impact. Overlay system is efficient.

**Q: Can I resize the persistence partition?**  
A: Yes, use `parted` or `gparted` to resize the ext4 partition.

**Q: Will persistence work with both UEFI and BIOS?**  
A: Yes, persistence is boot-mode independent.

**Q: Can I access persistence partition from another OS?**  
A: Yes, it's a standard ext4 partition. Mount it and browse.

**Q: What happens if I disable persistence?**  
A: Changes are stored only in RAM and lost on reboot.

**Q: How do I backup my persistence partition?**  
A: Use `dd` to create an image:
```bash
sudo dd if=/dev/sdX3 of=persistence-backup.img bs=4M status=progress
```

## Support

For issues with persistence:

1. Check logs: `/var/log/mados-persistence.log`
2. Check service: `systemctl status mados-persistence.service`
3. Report issues: GitHub Issues
4. Ask OpenCode: `opencode` (madOS AI assistant)

## See Also

- [Installation Guide](../README.md)
- [Troubleshooting](../README.md#troubleshooting)
- [ArchWiki: Persistent Live USB](https://wiki.archlinux.org/title/USB_flash_installation_medium)
