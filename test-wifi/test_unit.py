#!/usr/bin/env python3
"""Unit tests for mados-wifi core functionality.

Tests backend functions by executing the module code directly.
"""

import sys
import subprocess
import re
import os

# Execute backend code directly to avoid import issues
backend_path = '/usr/local/lib/mados_wifi/core/backend.py'

def run_test(test_name, test_func):
    """Run a test function and report results."""
    try:
        result = test_func()
        status = "PASS" if result else "FAIL"
        print(f"  Status: {status}\n")
        return (test_name, result)
    except Exception as e:
        print(f"  ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return (test_name, False)


def test_run_command():
    """Test _run_command function - executes real subprocess."""
    print("Test 1: _run_command()...")
    exec_result = subprocess.run(
        ['python3', '-c', """
import sys
sys.path.insert(0, '/usr/local/lib')
exec(open('/usr/local/lib/mados_wifi/core/backend.py').read())
result = _run_command(['echo', 'hello'])
assert result.returncode == 0, 'Command failed'
assert 'hello' in result.stdout, 'Wrong output'
print('OK')
"""],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert exec_result.returncode == 0, f"Test failed: {exec_result.stderr}"
    assert "OK" in exec_result.stdout
    return True


def test_strip_ansi():
    """Test _strip_ansi function."""
    print("Test 2: _strip_ansi()...")
    exec_result = subprocess.run(
        ['python3', '-c', """
import sys
sys.path.insert(0, '/usr/local/lib')
exec(open('/usr/local/lib/mados_wifi/core/backend.py').read())
ansi_text = "\\x1B[31mRed text\\x1B[0m and \\x1B[1mBold\\x1B[0m"
clean = _strip_ansi(ansi_text)
assert 'Red text' in clean, 'Missing red text'
assert 'Bold' in clean, 'Missing bold'
assert '\\x1B' not in clean, 'ANSI codes not stripped'
print('OK')
"""],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert exec_result.returncode == 0, f"Test failed: {exec_result.stderr}"
    assert "OK" in exec_result.stdout
    return True


def test_parse_iwctl_table():
    """Test _parse_iwctl_table function."""
    print("Test 3: _parse_iwctl_table()...")
    exec_result = subprocess.run(
        ['python3', '-c', """
import sys
sys.path.insert(0, '/usr/local/lib')
exec(open('/usr/local/lib/mados_wifi/core/backend.py').read())
output = '''
Network name  Security  Signal
MyNetwork     WPA2      ****
HiddenNet     WPA2      ***
OpenNet       Open      **
'''
rows = _parse_iwctl_table(output)
assert len(rows) >= 3, f'Expected 3+ networks, got {len(rows)}'
first_ssid = rows[0][0][0]
assert 'MyNetwork' in first_ssid, f'Expected MyNetwork, got {first_ssid}'
print('OK')
"""],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert exec_result.returncode == 0, f"Test failed: {exec_result.stderr}"
    assert "OK" in exec_result.stdout
    return True


def test_cidr_to_netmask():
    """Test _cidr_to_netmask function."""
    print("Test 4: _cidr_to_netmask()...")
    exec_result = subprocess.run(
        ['python3', '-c', """
import sys
sys.path.insert(0, '/usr/local/lib')
exec(open('/usr/local/lib/mados_wifi/core/backend.py').read())
assert _cidr_to_netmask('24') == '255.255.255.0', 'Wrong /24 mask'
assert _cidr_to_netmask('16') == '255.255.0.0', 'Wrong /16 mask'
assert _cidr_to_netmask('32') == '255.255.255.255', 'Wrong /32 mask'
assert _cidr_to_netmask('0') == '0.0.0.0', 'Wrong /0 mask'
assert _cidr_to_netmask('invalid') == 'invalid', 'Should return invalid unchanged'
print('OK')
"""],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert exec_result.returncode == 0, f"Test failed: {exec_result.stderr}"
    assert "OK" in exec_result.stdout
    return True


def test_split_nmcli_line():
    """Test _split_nmcli_line function."""
    print("Test 5: _split_nmcli_line()...")
    exec_result = subprocess.run(
        ['python3', '-c', """
import sys
sys.path.insert(0, '/usr/local/lib')
exec(open('/usr/local/lib/mados_wifi/core/backend.py').read())
line = 'field1:field2:field3'
parts = _split_nmcli_line(line)
assert parts == ['field1', 'field2', 'field3'], f'Wrong parts: {parts}'
line = 'field1:field\\\\:2:field3'
parts = _split_nmcli_line(line)
assert parts == ['field1', 'field:2', 'field3'], f'Wrong escaped: {parts}'
print('OK')
"""],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert exec_result.returncode == 0, f"Test failed: {exec_result.stderr}"
    assert "OK" in exec_result.stdout
    return True


def run_all_tests():
    """Run all unit tests."""
    tests = [
        ("_run_command", test_run_command),
        ("_strip_ansi", test_strip_ansi),
        ("_parse_iwctl_table", test_parse_iwctl_table),
        ("_cidr_to_netmask", test_cidr_to_netmask),
        ("_split_nmcli_line", test_split_nmcli_line),
    ]
    
    results = []
    for name, test_func in tests:
        result = run_test(name, test_func)
        results.append(result)
    
    print("\n" + "="*60)
    print("UNIT TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {name}")
    
    print("="*60)
    print(f"Total: {passed}/{total} tests passed")
    print("="*60)
    
    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
