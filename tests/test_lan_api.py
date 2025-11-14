"""
Comprehensive LAN API tests.

Tests all LAN API commands with device status verification at multiple intervals.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from govee.api.lan import power, brightness, color as lan_color
from tests.test_utils import (
    verify_device_state,
    print_test_header,
    print_test_result,
    compare_rgb
)


# Test configuration - update these values
TEST_DEVICE_IP = "192.168.10.26"  # Ground2 Machine
TEST_DEVICE_NAME = "Ground2 Machine"


def test_lan_power_on():
    """Test LAN power ON command with state verification."""
    print_test_header(f"LAN API: Power ON - {TEST_DEVICE_NAME}")

    # Execute command
    result = power.turn_on(TEST_DEVICE_IP)
    print(f"Command sent: power.turn_on()")
    print(f"Result: {result}")

    # Verify state
    expected_state = {"onOff": 1}
    verified, history = verify_device_state(TEST_DEVICE_IP, expected_state)

    print_test_result("Power ON", result, verified, history)
    return verified


def test_lan_power_off():
    """Test LAN power OFF command with state verification."""
    print_test_header(f"LAN API: Power OFF - {TEST_DEVICE_NAME}")

    # Execute command
    result = power.turn_off(TEST_DEVICE_IP)
    print(f"Command sent: power.turn_off()")
    print(f"Result: {result}")

    # Verify state
    expected_state = {"onOff": 0}
    verified, history = verify_device_state(TEST_DEVICE_IP, expected_state)

    print_test_result("Power OFF", result, verified, history)
    return verified


def test_lan_brightness():
    """Test LAN brightness command with state verification."""
    print_test_header(f"LAN API: Brightness Control - {TEST_DEVICE_NAME}")

    test_levels = [25, 50, 75, 100]
    results = []

    for level in test_levels:
        print(f"\n--- Testing brightness level: {level}% ---")

        # Execute command
        result = brightness.set_brightness(TEST_DEVICE_IP, level)
        print(f"Command sent: brightness.set_brightness({level})")
        print(f"Result: {result}")

        # Verify state
        expected_state = {"brightness": level}
        verified, history = verify_device_state(TEST_DEVICE_IP, expected_state, tolerance=5)

        print_test_result(f"Brightness {level}%", result, verified, history)
        results.append(verified)

    return all(results)


def test_lan_color_rgb():
    """Test LAN RGB color command with state verification."""
    print_test_header(f"LAN API: RGB Color Control - {TEST_DEVICE_NAME}")

    test_colors = [
        ("RED", (255, 0, 0)),
        ("GREEN", (0, 255, 0)),
        ("BLUE", (0, 0, 255)),
        ("WHITE", (255, 255, 255)),
    ]
    results = []

    for name, rgb in test_colors:
        print(f"\n--- Testing color: {name} {rgb} ---")

        # Execute command
        result = lan_color.set_color(TEST_DEVICE_IP, rgb)
        print(f"Command sent: color.set_color({rgb})")
        print(f"Result: {result}")

        # Verify state
        r, g, b = rgb
        expected_state = {"color": {"r": r, "g": g, "b": b}}
        verified, history = verify_device_state(TEST_DEVICE_IP, expected_state, tolerance=10)

        print_test_result(f"Color {name}", result, verified, history)
        results.append(verified)

    return all(results)


def test_lan_device_status():
    """Test LAN device status query."""
    print_test_header(f"LAN API: Device Status Query - {TEST_DEVICE_NAME}")

    from govee.api.lan import status

    # Query status
    result = status.get_device_status(TEST_DEVICE_IP)
    print(f"Command sent: status.get_device_status()")

    if result:
        print(f"\nDevice Status:")
        print(f"  Power: {'ON' if result.get('onOff') == 1 else 'OFF'}")
        print(f"  Brightness: {result.get('brightness')}%")
        color = result.get('color', {})
        print(f"  Color: R={color.get('r')}, G={color.get('g')}, B={color.get('b')}")
        print(f"  Color Temperature: {result.get('colorTemInKelvin')}K")
        return True
    else:
        print(f"\n✗ Failed to query device status")
        return False


def run_all_lan_tests():
    """Run all LAN API tests."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE LAN API TEST SUITE")
    print("=" * 80)
    print(f"Test Device: {TEST_DEVICE_NAME} ({TEST_DEVICE_IP})")
    print(f"Status checks at: 0.5s, 1.0s, 1.5s, 2.0s, 3.0s after each command")
    print("=" * 80)

    results = {}

    # Test 1: Power ON
    results['Power ON'] = test_lan_power_on()

    # Test 2: Brightness levels
    results['Brightness'] = test_lan_brightness()

    # Test 3: RGB colors
    results['RGB Colors'] = test_lan_color_rgb()

    # Test 4: Device status query
    results['Device Status'] = test_lan_device_status()

    # Test 5: Power OFF
    results['Power OFF'] = test_lan_power_off()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<50} {status}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    print("=" * 80)
    print(f"Total: {passed_count}/{total_count} tests passed")
    print("=" * 80)

    return all(results.values())


if __name__ == "__main__":
    success = run_all_lan_tests()
    sys.exit(0 if success else 1)
