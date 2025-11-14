#!/usr/bin/env python3
"""
Simple utility to scan for Govee devices on the local network.

Usage:
    python -m govee.lan_scan
"""
from govee.api.lan import discovery


def main():
    """Scan for Govee devices on LAN."""
    print("=" * 70)
    print("Govee LAN Device Scanner")
    print("=" * 70)
    print()
    print("Scanning local network for Govee devices...")
    print("This may take a few seconds...")
    print()

    # Discover devices
    devices = discovery.discover_devices(timeout=5.0, retries=3)

    if not devices:
        print("No devices discovered on local network.")
        print()
        print("Troubleshooting:")
        print("  - Ensure devices are powered on and connected to WiFi")
        print("  - Check that your computer is on the same network")
        print("  - Some devices may not support LAN discovery")
        print("  - Try querying devices directly by IP if known")
        return

    print(f"Found {len(devices)} device(s):")
    print()
    print(f"{'Device ID':<35} {'IP Address':<20} {'SKU':<10}")
    print("-" * 70)

    for dev in devices:
        print(f"{dev['device_id']:<35} {dev['ip']:<20} {dev['sku']:<10}")

    print()
    print("=" * 70)
    print()
    print("To use these IPs in your sync config:")
    print("  1. Run: govee-sync --api-key YOUR_KEY --output govee_devices.json")
    print("  2. Manually add IP addresses to the generated JSON file")
    print("  3. Re-run govee-sync with --preserve-manual to keep your IPs")
    print()


if __name__ == "__main__":
    main()
