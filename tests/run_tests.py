"""
Comprehensive test runner for govee-python-sdk.

Usage:
    python run_tests.py <API_KEY> [options]

Options:
    --lan          Run LAN API tests only
    --cloud        Run Cloud API tests only
    --fallback     Run LAN fallback tests only
    --all          Run all tests (default)
    --devices-file Path to devices JSON file (optional)
"""
import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_config import get_test_device, print_test_step, print_step_result


def run_lan_tests(device_info):
    """Run LAN API tests."""
    print("\n" + "=" * 80)
    print("LAN API TESTS")
    print("=" * 80)

    if not device_info.get('ip'):
        print(f"Device: {device_info['name']}")
        print("\n✗ SKIPPED - Device does not have IP address")
        print("  LAN tests require a device that supports LAN control.")
        print("  Please select a device with [LAN] indicator next time.")
        print("=" * 80)
        return False

    print(f"Device: {device_info['name']}")
    print(f"IP: {device_info['ip']}")
    print(f"Status verification delay: 0.5s (same as LAN API default)")
    print("=" * 80)

    from govee.api.lan import power, brightness, color as lan_color, status
    from tests.test_utils import verify_device_state
    import time

    device_ip = device_info['ip']
    total_steps = 11  # 1 power on, 4 brightness, 4 colors, 1 status query, 1 power off
    step = 0
    results = []

    # Test 1: Power ON
    step += 1
    print_test_step(step, total_steps, "Power ON via LAN", "Device should turn ON")
    try:
        result = power.send_power(device_ip, True)
        print(f"  Command result: {result}")
        verified, state = verify_device_state(device_ip, {"onOff": 1})
        print_step_result(verified)
        if state:
            print(f"    Verified state: Power={'ON' if state.get('onOff') == 1 else 'OFF'}")
        results.append(verified)
    except Exception as e:
        print_step_result(False, str(e))
        results.append(False)

    # Test 2-5: Brightness levels
    for brightness_level in [25, 50, 75, 100]:
        step += 1
        print_test_step(step, total_steps, f"Set Brightness to {brightness_level}%", f"Brightness should be {brightness_level}%")
        try:
            result = brightness.send_brightness(device_ip, brightness_level)
            print(f"  Command result: {result}")
            verified, state = verify_device_state(device_ip, {"brightness": brightness_level}, tolerance=5)
            print_step_result(verified)
            if state:
                print(f"    Verified state: Brightness={state.get('brightness')}%")
            results.append(verified)
            time.sleep(0.5)
        except Exception as e:
            print_step_result(False, str(e))
            results.append(False)

    # Test 6-9: RGB Colors
    colors = [("RED", (255, 0, 0)), ("GREEN", (0, 255, 0)), ("BLUE", (0, 0, 255)), ("WHITE", (255, 255, 255))]
    for color_name, rgb in colors:
        step += 1
        print_test_step(step, total_steps, f"Set Color to {color_name}", f"Color should be RGB{rgb}")
        try:
            result = lan_color.send_color(device_ip, rgb)
            print(f"  Command result: {result}")
            r, g, b = rgb
            verified, state = verify_device_state(device_ip, {"color": {"r": r, "g": g, "b": b}}, tolerance=10)
            print_step_result(verified)
            if state and state.get('color'):
                c = state['color']
                print(f"    Verified state: Color=R={c.get('r')}, G={c.get('g')}, B={c.get('b')}")
            results.append(verified)
            time.sleep(0.5)
        except Exception as e:
            print_step_result(False, str(e))
            results.append(False)

    # Test 10: Device Status Query
    step += 1
    print_test_step(step, total_steps, "Query Device Status", "Should return current device state")
    try:
        result = status.get_device_status(device_ip)
        if result:
            print(f"  Power: {'ON' if result.get('onOff') == 1 else 'OFF'}")
            print(f"  Brightness: {result.get('brightness')}%")
            c = result.get('color', {})
            print(f"  Color: R={c.get('r')}, G={c.get('g')}, B={c.get('b')}")
            print_step_result(True)
            results.append(True)
        else:
            print_step_result(False, "No response")
            results.append(False)
    except Exception as e:
        print_step_result(False, str(e))
        results.append(False)

    # Test 11: Power OFF
    step += 1
    print_test_step(step, total_steps, "Power OFF via LAN", "Device should turn OFF")
    try:
        result = power.send_power(device_ip, False)
        print(f"  Command result: {result}")
        verified, state = verify_device_state(device_ip, {"onOff": 0})
        print_step_result(verified)
        if state:
            print(f"    Verified state: Power={'ON' if state.get('onOff') == 1 else 'OFF'}")
        results.append(verified)
    except Exception as e:
        print_step_result(False, str(e))
        results.append(False)

    # Print LAN test summary
    print("\n" + "=" * 80)
    print("LAN API TEST SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    print("=" * 80)

    return all(results)


def run_cloud_tests(device_info):
    """Run Cloud API tests."""
    print("\n" + "=" * 80)
    print("CLOUD API TESTS")
    print("=" * 80)
    print(f"Device: {device_info['name']}")
    print(f"Device ID: {device_info['device_id']}")
    print(f"SKU: {device_info['sku']}")
    print("=" * 80)

    from govee.api.cloud import device_control, device_state, device_scenes
    import time

    api_key = device_info['api_key']
    device_id = device_info['device_id']
    sku = device_info['sku']

    total_steps = 11
    step = 0
    results = []

    # Test 1: Power ON
    step += 1
    print_test_step(step, total_steps, "Power ON via Cloud API", "Device should turn ON, API returns code 200")
    try:
        result = device_control.power(api_key, device_id, sku, True)
        code = result.get('code')
        success = (code == 200)
        print_step_result(success, f"API returned code {code}")
        results.append(success)
        time.sleep(2)
    except Exception as e:
        print_step_result(False, str(e))
        results.append(False)

    # Test 2-5: Brightness levels
    for brightness_level in [25, 50, 75, 100]:
        step += 1
        print_test_step(step, total_steps, f"Set Brightness to {brightness_level}%", f"API returns code 200")
        try:
            result = device_control.brightness(api_key, device_id, sku, brightness_level)
            code = result.get('code')
            success = (code == 200)
            print_step_result(success, f"API returned code {code}")
            results.append(success)
            time.sleep(2)
        except Exception as e:
            print_step_result(False, str(e))
            results.append(False)

    # Test 6-8: RGB Colors
    colors = [("RED", (255, 0, 0)), ("GREEN", (0, 255, 0)), ("BLUE", (0, 0, 255))]
    for color_name, rgb in colors:
        step += 1
        print_test_step(step, total_steps, f"Set Color to {color_name}", f"API returns code 200")
        try:
            result = device_control.color_rgb(api_key, device_id, sku, rgb)
            code = result.get('code')
            success = (code == 200)
            print_step_result(success, f"API returned code {code}")
            results.append(success)
            time.sleep(2)
        except Exception as e:
            print_step_result(False, str(e))
            results.append(False)

    # Test 9: Device State Query
    step += 1
    print_test_step(step, total_steps, "Query Device State", "Should return current device state")
    try:
        state = device_state.get_device_state(api_key, device_id, sku)
        print(f"  Device: {state.get('device')}")
        print(f"  SKU: {state.get('sku')}")
        caps = state.get('capabilities', [])
        print(f"  Capabilities: {len(caps)} found")
        print_step_result(True, f"{len(caps)} capabilities retrieved")
        results.append(True)
    except Exception as e:
        print_step_result(False, str(e))
        results.append(False)

    # Test 10: Power OFF
    step += 1
    print_test_step(step, total_steps, "Power OFF via Cloud API", "Device should turn OFF, API returns code 200")
    try:
        result = device_control.power(api_key, device_id, sku, False)
        code = result.get('code')
        success = (code == 200)
        print_step_result(success, f"API returned code {code}")
        results.append(success)
    except Exception as e:
        print_step_result(False, str(e))
        results.append(False)

    # Print Cloud test summary
    print("\n" + "=" * 80)
    print("CLOUD API TEST SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    print("=" * 80)

    return all(results)


def main():
    parser = argparse.ArgumentParser(description='Run govee-python-sdk tests')
    parser.add_argument('api_key', help='Govee API key')
    parser.add_argument('--lan', action='store_true', help='Run LAN API tests only')
    parser.add_argument('--cloud', action='store_true', help='Run Cloud API tests only')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    parser.add_argument('--devices-file', help='Path to devices file (Python module or JSON). Defaults to current directory.')

    args = parser.parse_args()

    # Default to all tests if no specific test selected
    if not (args.lan or args.cloud):
        args.all = True

    # Default devices_file to current directory if not specified
    # This will load from govee_devices.py if it exists there
    devices_file = args.devices_file if args.devices_file else '.'

    # Get test device
    device_info = get_test_device(args.api_key, devices_file)

    if not device_info:
        print("\nNo device selected. Exiting...")
        sys.exit(1)

    results = {}

    # Run requested tests
    if args.lan or args.all:
        results['LAN API'] = run_lan_tests(device_info)

    if args.cloud or args.all:
        results['Cloud API'] = run_cloud_tests(device_info)

    # Print final summary
    print("\n" + "=" * 80)
    print("FINAL TEST SUMMARY")
    print("=" * 80)
    for test_suite, passed in results.items():
        if passed:
            status = "✓ PASS"
        elif passed is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIPPED"
        print(f"{test_suite:.<50} {status}")
    print("=" * 80)

    # Consider test suite passing if all tests passed (or were skipped)
    # Only fail if any test explicitly failed (False vs None/skipped)
    all_passed = all(result is not False for result in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
