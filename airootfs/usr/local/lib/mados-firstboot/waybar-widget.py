#!/usr/bin/env python3
"""
madOS First-Boot Progress Widget for Waybar
Displays real-time progress of first-boot setup
"""

import json
import os
import sys
from pathlib import Path

PROGRESS_FILE = Path("/tmp/mados-firstboot-progress")
STATUS_DIR = Path("/var/lib/mados-firstboot")


def get_progress():
    """Get current progress percentage"""
    try:
        if PROGRESS_FILE.exists():
            return int(PROGRESS_FILE.read_text().strip())
    except (ValueError, IOError):
        pass
    return None


def get_phase_status():
    """Get status of individual phases"""
    phases = [
        "package-update",
        "package-install",
        "user-config",
        "desktop-config",
        "services-enable",
        "cleanup",
    ]
    
    status = {}
    for phase in phases:
        phase_file = STATUS_DIR / f"{phase}.status"
        try:
            status[phase] = phase_file.read_text().strip()
        except (IOError, FileNotFoundError):
            status[phase] = "pending"
    
    return status


def format_tooltip(phase_status):
    """Format tooltip text with phase details"""
    lines = ["First-Boot Setup Progress:"]
    labels = {
        "package-update": "📦 Package Update",
        "package-install": "📥 Package Install",
        "user-config": "👤 User Config",
        "desktop-config": "🖥️ Desktop Config",
        "services-enable": "⚙️ Services",
        "cleanup": "🧹 Cleanup",
    }
    
    for phase in phase_status:
        status = phase_status[phase]
        if status == "complete":
            icon = "✓"
        elif status == "running":
            icon = "⟳"
        else:
            icon = "○"
        label = labels.get(phase, phase)
        lines.append(f"{icon} {label}")
    
    return "\n".join(lines)


def main():
    progress = get_progress()
    
    if progress is None:
        # No progress file, setup not started or complete
        print(json.dumps({"text": "", "tooltip": "First-boot setup complete"}))
        return
    
    if progress >= 100:
        print(json.dumps({"text": "", "tooltip": "First-boot setup complete"}))
        return
    
    phase_status = get_phase_status()
    tooltip = format_tooltip(phase_status)
    
    # Find current running phase
    current_phase = ""
    for phase, status in phase_status.items():
        if status == "running":
            current_phase = phase
            break
    
    # Format display text
    if current_phase:
        display_text = f"⚙️ {progress}%"
    else:
        display_text = f"📊 {progress}%"
    
    # Format colors based on progress
    if progress < 30:
        color = "#f5a962"  # Nord orange
    elif progress < 70:
        color = "#88c0d0"  # Nord blue
    else:
        color = "#a3be8c"  # Nord green
    
    output = {
        "text": display_text,
        "tooltip": f"{tooltip}\n\nOverall: {progress}%",
        "class": "firstboot-progress",
        "percentage": progress,
    }
    
    if color:
        output["color"] = color
    
    print(json.dumps(output))


if __name__ == "__main__":
    main()
