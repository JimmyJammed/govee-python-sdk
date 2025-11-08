#!/usr/bin/env python3
"""
Interactive CLI wizard for Govee device management.

Usage:
    govee-sync          # Interactive wizard mode
    python -m govee.cli # Alternative invocation
"""
import sys
import os
import json
import time
import random
from pathlib import Path
from typing import Optional, List, Dict, Any

from govee.client import GoveeClient
from govee.models import Device, Scene, DIYScene, Colors
from govee import __version__

# Config file location
CONFIG_FILE = Path.home() / ".govee" / "config.json"


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_menu(options: List[str]) -> int:
    """Print menu options and get user selection."""
    print()
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    print(f"  [0] Back/Exit")
    print()

    while True:
        try:
            choice = input("Select an option: ").strip()
            choice_num = int(choice)
            if 0 <= choice_num <= len(options):
                return choice_num
            print(f"Invalid choice. Please enter 0-{len(options)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config: Dict[str, Any]):
    """Save configuration to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_api_key(config: Dict[str, Any]) -> str:
    """Get API key from config or prompt user."""
    if 'api_key' in config:
        return config['api_key']

    print_header("API Key Setup")
    print("\nNo API key found. Please enter your Govee API key.")
    print("You can find this in the Govee Home app under:")
    print("  Settings -> About Us -> Apply for API Key")
    print()

    api_key = input("Enter API key: ").strip()
    if not api_key:
        print("Error: API key cannot be empty")
        sys.exit(1)

    config['api_key'] = api_key
    save_config(config)
    print("\n✓ API key saved!")
    time.sleep(1)
    return api_key


def update_api_key(config: Dict[str, Any]):
    """Prompt user to update API key."""
    print_header("Update API Key")
    print(f"\nCurrent API key: {config.get('api_key', 'Not set')}")
    print()

    new_key = input("Enter new API key (or press Enter to cancel): ").strip()
    if new_key:
        config['api_key'] = new_key
        save_config(config)
        print("\n✓ API key updated!")
    else:
        print("\nCancelled.")
    time.sleep(1)


def fetch_devices(client: GoveeClient):
    """Fetch devices and export as Python modules."""
    print_header("Fetching Govee Devices")

    # Load existing devices first to preserve user-set properties like IP addresses
    current_dir = Path.cwd()
    devices_file = current_dir / "govee_devices.py"
    if devices_file.exists():
        print("\n0. Loading existing devices to preserve IP addresses...")
        try:
            client.load_devices(current_dir)
            print(f"   ✓ Loaded {len(client._devices)} existing devices")
        except Exception as e:
            print(f"   ⚠ Could not load existing devices: {e}")

    print("\n1. Discovering devices from Govee Cloud API...")
    devices = client.discover_devices()
    print(f"   ✓ Found {len(devices)} devices")

    print("\n2. Fetching built-in scenes...")
    builtin_scenes = client.discover_builtin_scenes()
    print(f"   ✓ Found {len(builtin_scenes)} built-in scenes")

    print("\n3. Fetching DIY scenes...")
    diy_scenes = client.discover_diy_scenes()
    print(f"   ✓ Found {len(diy_scenes)} DIY scenes")

    print("\n4. Exporting as Python modules...")
    current_dir = Path.cwd()
    client.export_as_modules(current_dir)
    print(f"   ✓ Exported to:")
    print(f"      - {current_dir / 'govee_devices.py'}")
    if (current_dir / 'govee_scenes.py').exists():
        print(f"      - {current_dir / 'govee_scenes.py'}")
    if (current_dir / 'govee_diy_scenes.py').exists():
        print(f"      - {current_dir / 'govee_diy_scenes.py'}")

    print("\n✓ Fetch complete!")
    input("\nPress Enter to continue...")


def select_device(client: GoveeClient) -> Optional[Device]:
    """Prompt user to select a device."""
    if not client._devices:
        print("\nNo devices available. Fetching devices first...")
        client.discover_devices()
        if not client._devices:
            print("\nError: No devices found!")
            input("Press Enter to continue...")
            return None

    print_header("Select Device")

    # Group devices by type
    lights = [d for d in client._devices if 'light' in (d.metadata.get('type') or '').lower()]
    other = [d for d in client._devices if 'light' not in (d.metadata.get('type') or '').lower()]

    options = []
    device_map = {}

    if lights:
        print("\nLights:")
        for device in sorted(lights, key=lambda d: d.name.lower()):
            idx = len(options) + 1
            lan_tag = " [LAN]" if device.supports_lan else ""
            print(f"  [{idx}] {device.name} ({device.sku}){lan_tag}")
            options.append(device.name)
            device_map[idx] = device

    if other:
        print("\nOther Devices:")
        for device in sorted(other, key=lambda d: d.name.lower()):
            idx = len(options) + 1
            lan_tag = " [LAN]" if device.supports_lan else ""
            print(f"  [{idx}] {device.name} ({device.sku}){lan_tag}")
            options.append(device.name)
            device_map[idx] = device

    print(f"  [0] Back")
    print()

    while True:
        try:
            choice = input("Select device: ").strip()
            choice_num = int(choice)
            if choice_num == 0:
                return None
            if choice_num in device_map:
                return device_map[choice_num]
            print(f"Invalid choice. Please enter 0-{len(options)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            return None


def run_tests(client: GoveeClient):
    """Run LAN and Cloud API tests on selected device."""
    device = select_device(client)
    if not device:
        return

    print_header(f"Running Tests: {device.name}")
    print(f"\nDevice: {device.name}")
    print(f"SKU: {device.sku}")
    print(f"LAN capable: {device.supports_lan}")
    print(f"IP: {device.ip or 'N/A'}")
    print()

    # Get random scenes for testing
    try:
        scenes = client.get_scenes(device)
        diy_scenes = client.get_diy_scenes(device)
        test_scene = random.choice(scenes) if scenes else None
        test_diy_scene = random.choice(diy_scenes) if diy_scenes else None
    except Exception as e:
        print(f"⚠ Could not fetch scenes: {e}")
        test_scene = None
        test_diy_scene = None

    tests = [
        ("Power OFF", lambda: client.power(device, False)),
        ("Power ON", lambda: client.power(device, True)),
        ("Set Color (Red)", lambda: client.set_color(device, Colors.RED)),
        ("Set Color (Blue)", lambda: client.set_color(device, Colors.BLUE)),
        ("Set Brightness (50%)", lambda: client.set_brightness(device, 50)),
        ("Set Brightness (100%)", lambda: client.set_brightness(device, 100)),
    ]

    if test_scene:
        tests.append((f"Apply Scene ({test_scene.name})", lambda: client.apply_scene(device, test_scene)))

    if test_diy_scene:
        tests.append((f"Apply DIY Scene ({test_diy_scene.name})", lambda: client.apply_scene(device, test_diy_scene)))

    print("Running tests...\n")
    passed = 0
    failed = 0

    for i, (test_name, test_func) in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {test_name}...", end=" ", flush=True)
        try:
            result = test_func()
            if result:
                print("✓ PASS")
                passed += 1
            else:
                print("✗ FAIL")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1

        time.sleep(2)  # Delay between commands

    print()
    print("=" * 60)
    print(f"Tests complete: {passed} passed, {failed} failed")
    print("=" * 60)
    input("\nPress Enter to continue...")


def device_commands_menu(client: GoveeClient):
    """Device commands submenu."""
    device = select_device(client)
    if not device:
        return

    while True:
        print_header(f"Device Commands: {device.name}")

        options = [
            "Turn On",
            "Turn Off",
            "Set Color",
            "Set Brightness",
            "Set Warmth",
            "Set Scene",
            "Set DIY Scene"
        ]

        choice = print_menu(options)

        if choice == 0:
            break
        elif choice == 1:  # Turn On
            try:
                result = client.power(device, True)
                print(f"\n✓ Device turned {'ON' if result else 'ON (command sent)'}")
            except Exception as e:
                print(f"\n✗ Error: {e}")
            input("Press Enter to continue...")

        elif choice == 2:  # Turn Off
            try:
                result = client.power(device, False)
                print(f"\n✓ Device turned {'OFF' if result else 'OFF (command sent)'}")
            except Exception as e:
                print(f"\n✗ Error: {e}")
            input("Press Enter to continue...")

        elif choice == 3:  # Set Color
            set_color_submenu(client, device)

        elif choice == 4:  # Set Brightness
            set_brightness(client, device)

        elif choice == 5:  # Set Warmth
            set_warmth(client, device)

        elif choice == 6:  # Set Scene
            set_scene(client, device, diy=False)

        elif choice == 7:  # Set DIY Scene
            set_scene(client, device, diy=True)


def set_color_submenu(client: GoveeClient, device: Device):
    """Color selection submenu."""
    print_header("Select Color")

    color_options = [
        ("Red", Colors.RED),
        ("Green", Colors.GREEN),
        ("Blue", Colors.BLUE),
        ("Yellow", Colors.YELLOW),
        ("Purple", Colors.PURPLE),
        ("Cyan", Colors.CYAN),
        ("White", Colors.WHITE),
        ("Orange", Colors.ORANGE),
        ("Pink", Colors.PINK),
        ("Neon Pink", Colors.NEON_PINK),
        ("Custom RGB", None)
    ]

    options = [name for name, _ in color_options]
    choice = print_menu(options)

    if choice == 0:
        return
    elif choice == len(color_options):  # Custom RGB
        print("\nEnter RGB values (0-255):")
        try:
            r = int(input("  Red (0-255): ").strip())
            g = int(input("  Green (0-255): ").strip())
            b = int(input("  Blue (0-255): ").strip())

            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                print("\n✗ Invalid RGB values!")
                input("Press Enter to continue...")
                return

            result = client.set_color(device, (r, g, b))
            print(f"\n✓ Color set to RGB({r}, {g}, {b})")
        except ValueError:
            print("\n✗ Invalid input!")
        except Exception as e:
            print(f"\n✗ Error: {e}")
    else:
        color_name, color_rgb = color_options[choice - 1]
        try:
            result = client.set_color(device, color_rgb)
            print(f"\n✓ Color set to {color_name}")
        except Exception as e:
            print(f"\n✗ Error: {e}")

    input("Press Enter to continue...")


def set_brightness(client: GoveeClient, device: Device):
    """Set device brightness."""
    print_header("Set Brightness")
    print("\nEnter brightness level (1-100%):")

    try:
        brightness = int(input("Brightness: ").strip())
        if not (1 <= brightness <= 100):
            print("\n✗ Brightness must be between 1 and 100!")
            input("Press Enter to continue...")
            return

        result = client.set_brightness(device, brightness)
        print(f"\n✓ Brightness set to {brightness}%")
    except ValueError:
        print("\n✗ Invalid input!")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    input("Press Enter to continue...")


def set_warmth(client: GoveeClient, device: Device):
    """Set device color temperature (warmth)."""
    print_header("Set Color Temperature")
    print("\nEnter color temperature in Kelvin (2000-9000):")
    print("  2000K = Warm white (candle-like)")
    print("  4000K = Neutral white")
    print("  6500K = Cool white (daylight)")
    print("  9000K = Very cool white")

    try:
        kelvin = int(input("\nKelvin: ").strip())
        if not (2000 <= kelvin <= 9000):
            print("\n✗ Color temperature must be between 2000K and 9000K!")
            input("Press Enter to continue...")
            return

        result = client.set_color_temperature(device, kelvin)
        print(f"\n✓ Color temperature set to {kelvin}K")
    except ValueError:
        print("\n✗ Invalid input!")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    input("Press Enter to continue...")


def set_scene(client: GoveeClient, device: Device, diy: bool = False):
    """Set device scene."""
    scene_type = "DIY Scene" if diy else "Scene"
    print_header(f"Select {scene_type}")

    try:
        if diy:
            scenes = client.get_diy_scenes(device)
        else:
            scenes = client.get_scenes(device)

        if not scenes:
            print(f"\nNo {scene_type.lower()}s available for this device.")
            input("Press Enter to continue...")
            return

        print(f"\nAvailable {scene_type}s:")
        for i, scene in enumerate(scenes, 1):
            print(f"  [{i}] {scene.name}")
        print(f"  [0] Back")
        print()

        while True:
            try:
                choice = input(f"Select {scene_type.lower()}: ").strip()
                choice_num = int(choice)
                if choice_num == 0:
                    return
                if 1 <= choice_num <= len(scenes):
                    selected_scene = scenes[choice_num - 1]
                    result = client.apply_scene(device, selected_scene)
                    print(f"\n✓ Applied {scene_type.lower()}: {selected_scene.name}")
                    input("Press Enter to continue...")
                    return
                print(f"Invalid choice. Please enter 0-{len(scenes)}")
            except ValueError:
                print("Invalid input. Please enter a number.")

    except Exception as e:
        print(f"\n✗ Error fetching {scene_type.lower()}s: {e}")
        input("Press Enter to continue...")


def main_menu():
    """Main menu loop."""
    config = load_config()
    api_key = get_api_key(config)
    client = GoveeClient(api_key=api_key)

    while True:
        clear_screen()
        print_header(f"Govee Control Wizard v{__version__}")

        options = [
            "Update API Key",
            "Fetch Govee Devices",
            "Device Commands",
            "Run Tests"
        ]

        choice = print_menu(options)

        if choice == 0:
            print("\nGoodbye!")
            sys.exit(0)
        elif choice == 1:
            update_api_key(config)
        elif choice == 2:
            fetch_devices(client)
        elif choice == 3:
            device_commands_menu(client)
        elif choice == 4:
            run_tests(client)


def main():
    """Main entry point."""
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
