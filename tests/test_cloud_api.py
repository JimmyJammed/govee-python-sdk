"""
Comprehensive Cloud API tests.

Tests all Cloud API endpoints.
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from govee.api.cloud import (
    devices,
    device_control,
    device_state,
    device_scenes,
    device_diy_scenes
)
from tests.test_utils import print_test_header


# Test configuration - update these values
TEST_API_KEY = "88037fd0-65da-4c97-915c-642b314f0afe"
TEST_DEVICE_ID = "0E:BE:D6:50:83:C6:15:1F"
TEST_DEVICE_SKU = "H7052"
TEST_DEVICE_NAME = "Ground2 Machine"


def test_cloud_get_devices():
    """Test Cloud API: Get all devices."""
    print_test_header(f"Cloud API: Get Devices")

    try:
        result = devices.get_devices(TEST_API_KEY)
        device_list = result if isinstance(result, list) else result.get('devices', [])
        print(f"✓ Successfully retrieved {len(device_list)} devices")
        for dev in device_list[:3]:  # Show first 3
            print(f"  - {dev.get('deviceName')} ({dev.get('sku')})")
        if len(device_list) > 3:
            print(f"  ... and {len(device_list) - 3} more")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_cloud_power_control():
    """Test Cloud API: Power control."""
    print_test_header(f"Cloud API: Power Control - {TEST_DEVICE_NAME}")

    results = []

    # Test Power ON
    print("\n--- Power ON ---")
    try:
        result = device_control.power(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, True)
        code = result.get('code')
        print(f"✓ Power ON: code={code}")
        results.append(code == 200)
        time.sleep(2)
    except Exception as e:
        print(f"✗ Power ON failed: {e}")
        results.append(False)

    # Test Power OFF
    print("\n--- Power OFF ---")
    try:
        result = device_control.power(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, False)
        code = result.get('code')
        print(f"✓ Power OFF: code={code}")
        results.append(code == 200)
        time.sleep(2)
    except Exception as e:
        print(f"✗ Power OFF failed: {e}")
        results.append(False)

    # Power back ON for next tests
    device_control.power(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, True)
    time.sleep(2)

    return all(results)


def test_cloud_brightness_control():
    """Test Cloud API: Brightness control."""
    print_test_header(f"Cloud API: Brightness Control - {TEST_DEVICE_NAME}")

    test_levels = [25, 50, 75, 100]
    results = []

    for level in test_levels:
        print(f"\n--- Brightness {level}% ---")
        try:
            result = device_control.brightness(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, level)
            code = result.get('code')
            print(f"✓ Brightness {level}%: code={code}")
            results.append(code == 200)
            time.sleep(2)
        except Exception as e:
            print(f"✗ Brightness {level}% failed: {e}")
            results.append(False)

    return all(results)


def test_cloud_color_control():
    """Test Cloud API: RGB color control."""
    print_test_header(f"Cloud API: Color Control - {TEST_DEVICE_NAME}")

    test_colors = [
        ("RED", (255, 0, 0)),
        ("GREEN", (0, 255, 0)),
        ("BLUE", (0, 0, 255)),
        ("WHITE", (255, 255, 255)),
    ]
    results = []

    for name, rgb in test_colors:
        print(f"\n--- Color {name} {rgb} ---")
        try:
            result = device_control.color_rgb(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, rgb)
            code = result.get('code')
            print(f"✓ Color {name}: code={code}")
            results.append(code == 200)
            time.sleep(2)
        except Exception as e:
            print(f"✗ Color {name} failed: {e}")
            results.append(False)

    return all(results)


def test_cloud_color_temperature():
    """Test Cloud API: Color temperature control."""
    print_test_header(f"Cloud API: Color Temperature - {TEST_DEVICE_NAME}")

    test_temps = [2000, 4000, 6500, 9000]
    results = []

    for temp in test_temps:
        print(f"\n--- Temperature {temp}K ---")
        try:
            result = device_control.color_temperature_kelvin(
                TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, temp
            )
            code = result.get('code')
            print(f"✓ Temperature {temp}K: code={code}")
            results.append(code == 200)
            time.sleep(2)
        except Exception as e:
            print(f"✗ Temperature {temp}K failed: {e}")
            results.append(False)

    return all(results)


def test_cloud_light_scenes():
    """Test Cloud API: Built-in Light Scenes (Govee Defaults)."""
    print_test_header(f"Cloud API: Built-in Light Scenes - {TEST_DEVICE_NAME}")

    # First get available built-in scenes
    print("\n--- Fetching available built-in scenes ---")
    try:
        scenes_data = device_scenes.get_scenes(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU)
        scene_options = {}

        # scenes_data is a list of scene dictionaries: [{"name": "...", "value": {...}}]
        for scene in scenes_data:
            scene_name = scene.get('name')
            scene_value = scene.get('value')  # {"paramId": X, "id": Y}
            if scene_name and scene_value:
                scene_options[scene_name] = scene_value

        print(f"✓ Found {len(scene_options)} available built-in scenes")
        if scene_options:
            print(f"  Available scenes: {', '.join(list(scene_options.keys())[:5])}")
            if len(scene_options) > 5:
                print(f"  ... and {len(scene_options) - 5} more")
    except Exception as e:
        print(f"✗ Failed to fetch built-in scenes: {e}")
        return False

    # Test applying a few scenes (if available)
    test_scenes = ["Sunrise", "Sunset", "Rainbow"]
    results = []

    if not scene_options:
        print(f"⚠️ No built-in scenes available for device {TEST_DEVICE_NAME}")
        return True  # Not a failure - device may not support built-in scenes

    for scene_name in test_scenes:
        if scene_name in scene_options:
            scene_value = scene_options[scene_name]
            scene_id = scene_value.get('id')
            print(f"\n--- Applying built-in scene: {scene_name} (id={scene_id}) ---")
            try:
                result = device_control.light_scene(
                    TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, scene_id
                )
                code = result.get('code')
                print(f"✓ Scene {scene_name}: code={code}")
                results.append(code == 200)
                time.sleep(3)
            except Exception as e:
                print(f"✗ Scene {scene_name} failed: {e}")
                results.append(False)
        else:
            print(f"⚠️ Scene '{scene_name}' not available on this device")

    # If no test scenes were available, just return success
    if not results:
        print(f"\n⚠️ None of the test scenes ({', '.join(test_scenes)}) are available")
        return True

    return all(results)


def test_cloud_device_state():
    """Test Cloud API: Device state query."""
    print_test_header(f"Cloud API: Device State Query - {TEST_DEVICE_NAME}")

    try:
        state = device_state.get_device_state(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU)

        print(f"✓ Successfully queried device state")
        print(f"\nDevice: {state.get('device')}")
        print(f"SKU: {state.get('sku')}")
        print(f"\nCapabilities:")

        for cap in state.get('capabilities', []):
            instance = cap.get('instance', 'N/A')
            value = cap.get('state', {}).get('value')
            if value is not None:
                print(f"  - {instance}: {value}")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_cloud_diy_scenes():
    """Test Cloud API: DIY Scenes (Custom User-Created Scenes)."""
    print_test_header(f"Cloud API: DIY Scenes - {TEST_DEVICE_NAME}")

    # First get available DIY scenes
    print("\n--- Fetching available DIY scenes ---")
    try:
        diy_scenes_data = device_diy_scenes.get_diy_scenes(TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU)

        print(f"✓ Found {len(diy_scenes_data)} DIY scenes")

        if not diy_scenes_data:
            print(f"⚠️ No DIY scenes available for device {TEST_DEVICE_NAME}")
            return True  # Not a failure - device may not have DIY scenes

        # Show available DIY scenes
        for scene in diy_scenes_data[:5]:  # Show first 5
            print(f"  - {scene.get('name')} (id={scene.get('id')})")

        if len(diy_scenes_data) > 5:
            print(f"  ... and {len(diy_scenes_data) - 5} more")

    except Exception as e:
        print(f"✗ Failed to fetch DIY scenes: {e}")
        return False

    # Test applying a few DIY scenes
    results = []
    test_count = min(3, len(diy_scenes_data))  # Test up to 3 scenes

    for i, scene in enumerate(diy_scenes_data[:test_count]):
        scene_name = scene.get('name')
        scene_id = scene.get('id')
        print(f"\n--- Applying DIY scene: {scene_name} (id={scene_id}) ---")
        try:
            result = device_control.scene(
                TEST_API_KEY, TEST_DEVICE_ID, TEST_DEVICE_SKU, scene_id
            )
            code = result.get('code')
            print(f"✓ DIY Scene {scene_name}: code={code}")
            results.append(code == 200)
            time.sleep(3)
        except Exception as e:
            print(f"✗ DIY Scene {scene_name} failed: {e}")
            results.append(False)

    return all(results) if results else True


def run_all_cloud_tests():
    """Run all Cloud API tests."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE CLOUD API TEST SUITE")
    print("=" * 80)
    print(f"Test Device: {TEST_DEVICE_NAME}")
    print(f"Device ID: {TEST_DEVICE_ID}")
    print(f"SKU: {TEST_DEVICE_SKU}")
    print("=" * 80)

    results = {}

    # Test 1: Get devices
    results['Get Devices'] = test_cloud_get_devices()

    # Test 2: Power control
    results['Power Control'] = test_cloud_power_control()

    # Test 3: Brightness control
    results['Brightness Control'] = test_cloud_brightness_control()

    # Test 4: Color control
    results['Color Control'] = test_cloud_color_control()

    # Test 5: Color temperature
    results['Color Temperature'] = test_cloud_color_temperature()

    # Test 6: Built-in light scenes (Govee defaults)
    results['Built-in Scenes (Govee Defaults)'] = test_cloud_light_scenes()

    # Test 7: Device state query
    results['Device State'] = test_cloud_device_state()

    # Test 8: DIY scenes (Custom user-created)
    results['DIY Scenes (Custom)'] = test_cloud_diy_scenes()

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
    success = run_all_cloud_tests()
    sys.exit(0 if success else 1)
