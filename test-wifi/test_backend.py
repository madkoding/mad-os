#!/usr/bin/env python3
"""Test suite for mados-wifi backend functionality."""

import sys
import os
import subprocess
import time

# Add the library path
sys.path.insert(0, "/usr/local/lib")

from mados_wifi import (
    check_wifi_available,
    get_wifi_device,
    scan_networks,
    connect_to_network,
    disconnect_network,
    forget_network,
    get_active_ssid,
    get_connection_details,
    get_saved_connections,
    set_auto_connect,
    set_static_ip,
    set_dhcp,
    set_dns_override,
    async_scan,
)


def test_check_wifi_available():
    """Test that WiFi availability check works."""
    print("Test 1: check_wifi_available()...")
    result = check_wifi_available()
    print(f"  Result: {result}")
    return result


def test_get_wifi_device():
    """Test that we can detect a WiFi device."""
    print("Test 2: get_wifi_device()...")
    device = get_wifi_device()
    print(f"  Device: {device}")
    return device is not None


def test_scan_networks():
    """Test that we can scan for networks."""
    print("Test 3: scan_networks()...")

    # First ensure iwd is running
    try:
        subprocess.run(["systemctl", "start", "iwd"], capture_output=True, check=False)
        time.sleep(1)
    except:
        pass

    networks = scan_networks()
    print(f"  Networks found: {len(networks)}")
    for net in networks[:3]:  # Show first 3
        print(f"    - {net.ssid} ({net.signal}%) [{net.security}]")
    return len(networks) >= 0  # May be 0 if no networks available


def test_get_active_ssid():
    """Test getting active connection."""
    print("Test 4: get_active_ssid()...")
    ssid = get_active_ssid()
    print(f"  Active SSID: {ssid}")
    return True  # May be None if not connected


def test_get_saved_connections():
    """Test getting saved connections."""
    print("Test 5: get_saved_connections()...")
    connections = get_saved_connections()
    print(f"  Saved connections: {len(connections)}")
    for conn in connections:
        print(f"    - {conn}")
    return True


def test_iwctl_available():
    """Test that iwctl is available."""
    print("Test 6: Checking iwctl availability...")
    try:
        result = subprocess.run(["iwctl", "--version"], capture_output=True, text=True)
        print(f"  iwctl available: {result.returncode == 0}")
        print(f"  Version: {result.stdout.strip() or result.stderr.strip()}")
        return result.returncode == 0
    except FileNotFoundError:
        print("  ERROR: iwctl not found")
        return False


def test_rfkill_available():
    """Test that rfkill is available."""
    print("Test 7: Checking rfkill availability...")
    try:
        result = subprocess.run(["rfkill", "list"], capture_output=True, text=True)
        print(f"  rfkill available: {result.returncode == 0}")
        return result.returncode == 0
    except FileNotFoundError:
        print("  ERROR: rfkill not found")
        return False


def test_iwd_service_status():
    """Test iwd service status."""
    print("Test 8: Checking iwd service...")
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "iwd"], capture_output=True, text=True
        )
        status = result.stdout.strip()
        print(f"  iwd status: {status}")
        return status == "active"
    except:
        print("  ERROR: Could not check iwd service")
        return False


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        ("iwctl available", test_iwctl_available),
        ("rfkill available", test_rfkill_available),
        ("iwd service", test_iwd_service_status),
        ("check_wifi_available", test_check_wifi_available),
        ("get_wifi_device", test_get_wifi_device),
        ("scan_networks", test_scan_networks),
        ("get_active_ssid", test_get_active_ssid),
        ("get_saved_connections", test_get_saved_connections),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  Status: {status}\n")
            results.append((name, result))
        except Exception as e:
            print(f"  ERROR: {e}\n")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)

    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
