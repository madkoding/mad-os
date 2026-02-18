"""CLI entry point for mados-wifi."""

import sys
from .manager import WiFiManager


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: mados-wifi-cli <command> [args]")
        print("")
        print("Commands:")
        print("  scan           Scan for WiFi networks")
        print("  connect <ssid> [password]  Connect to a network")
        print("  disconnect     Disconnect from current network")
        print("  forget <ssid>  Remove a saved network")
        print("  status         Show current connection status")
        print("  networks       Show saved networks")
        print("  info           Show connection details")
        sys.exit(0)
    
    command = sys.argv[1]
    manager = WiFiManager()
    
    if command == "scan":
        print("Scanning for networks...")
        networks = manager.scan()
        if networks:
            print(f"Found {len(networks)} network(s):")
            for net in networks:
                print(f"  - {net.ssid} ({net.signal}%) [{net.security}]")
        else:
            print("No networks found")
    
    elif command == "connect":
        if len(sys.argv) < 3:
            print("Usage: mados-wifi-cli connect <ssid> [password]")
            sys.exit(1)
        ssid = sys.argv[2]
        password = sys.argv[3] if len(sys.argv) > 3 else None
        result = manager.connect(ssid, password)
        print(result)
    
    elif command == "disconnect":
        result = manager.disconnect()
        print("Disconnected" if result else "Failed to disconnect")
    
    elif command == "forget":
        if len(sys.argv) < 3:
            print("Usage: mados-wifi-cli forget <ssid>")
            sys.exit(1)
        ssid = sys.argv[2]
        result = manager.forget(ssid)
        print("Network removed" if result else "Failed to remove network")
    
    elif command == "status":
        ssid = manager.get_connected_ssid()
        if ssid:
            print(f"Connected to: {ssid}")
        else:
            print("Not connected")
    
    elif command == "networks":
        networks = manager.get_saved_networks()
        if networks:
            print("Saved networks:")
            for net in networks:
                print(f"  - {net}")
        else:
            print("No saved networks")
    
    elif command == "info":
        info = manager.get_info()
        if info:
            print(f"SSID: {info.ssid}")
            print(f"Signal: {info.signal}%")
            print(f"IP: {info.ip4_address}")
        else:
            print("Not connected")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
