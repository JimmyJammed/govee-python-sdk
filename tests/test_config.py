"""
Test configuration and device selection utilities.
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from govee.api.cloud import devices as cloud_devices


def load_device_from_file(api_key: str, devices_file: str = None):
    """
    Load devices from Python module or fetch from API.

    Args:
        api_key: Govee API key
        devices_file: Path to Python devices module or JSON file (optional)

    Returns:
        List of device dictionaries
    """
    # Try loading from Python module first (govee_devices.py)
    if devices_file:
        # If it's a .py file or points to a directory with govee_devices.py
        if devices_file.endswith('.py'):
            module_path = devices_file
        elif os.path.isdir(devices_file):
            module_path = os.path.join(devices_file, 'govee_devices.py')
        else:
            # Assume it's pointing to a directory, try govee_devices.py
            dir_path = os.path.dirname(devices_file) if devices_file else '.'
            module_path = os.path.join(dir_path, 'govee_devices.py')

        # Try to import from Python module
        if os.path.exists(module_path):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("govee_devices", module_path)
                if spec and spec.loader:
                    govee_devices_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(govee_devices_module)

                    # Convert Device objects to dictionaries for compatibility
                    devices_list = []
                    for device_name in govee_devices_module.__all__:
                        device_obj = getattr(govee_devices_module, device_name)
                        devices_list.append({
                            'id': device_obj.id,
                            'name': device_obj.name,
                            'sku': device_obj.sku,
                            'ip': device_obj.ip,
                            'device': device_obj.id,  # For API format compatibility
                            'deviceName': device_obj.name,  # For API format compatibility
                            'capabilities': device_obj.capabilities,
                            'metadata': device_obj.metadata,
                            'type': device_obj.metadata.get('type', '')
                        })
                    print(f"Loaded {len(devices_list)} devices from Python module: {module_path}")
                    return devices_list
            except Exception as e:
                print(f"Warning: Failed to load devices from Python module: {e}")

        # Fallback to JSON if Python module doesn't exist
        if devices_file.endswith('.json') and os.path.exists(devices_file):
            try:
                with open(devices_file, 'r') as f:
                    data = json.load(f)
                    devices_list = data.get('devices', [])
                    print(f"Loaded {len(devices_list)} devices from JSON file: {devices_file}")
                    return devices_list
            except Exception as e:
                print(f"Warning: Failed to load devices from JSON file: {e}")

    # Fallback to API
    try:
        print("Fetching devices from Govee API...")
        response = cloud_devices.get_devices(api_key)

        # Extract devices list from response
        # Handle both old and new API response formats
        if "data" in response:
            # New API format: data is a list of devices directly
            devices_list = response.get("data", [])
        else:
            # Old API format: data is in payload.devices
            devices_list = response.get("payload", {}).get("devices", [])

        return devices_list
    except Exception as e:
        print(f"Error: Failed to fetch devices from API: {e}")
        return []


def select_device_interactive(devices_list):
    """
    Interactive device selection menu.

    Args:
        devices_list: List of device dictionaries

    Returns:
        Selected device dictionary or None
    """
    if not devices_list:
        print("Error: No devices available")
        return None

    print("\n" + "=" * 80)
    print("AVAILABLE DEVICES")
    print("=" * 80)

    # Group devices by type
    lights = []
    other = []

    for dev in devices_list:
        dev_type = dev.get('type') or ''
        dev_type = dev_type.lower() if dev_type else ''
        if 'light' in dev_type:
            lights.append(dev)
        else:
            other.append(dev)

    # Sort devices alphabetically by name
    # Handle both API format ('deviceName') and JSON format ('name')
    lights.sort(key=lambda d: (d.get('deviceName') or d.get('name', '')).lower())
    other.sort(key=lambda d: (d.get('deviceName') or d.get('name', '')).lower())

    # Display lights first
    idx = 1
    device_map = {}

    if lights:
        print("\nLights:")
        for dev in lights:
            # Handle both API format ('deviceName') and JSON format ('name')
            name = dev.get('deviceName') or dev.get('name', 'Unknown')
            sku = dev.get('sku', 'Unknown')
            # Handle both API format ('device') and JSON format ('id')
            device_id = dev.get('device') or dev.get('id', 'Unknown')
            # Check if device has IP (LAN capable)
            ip_info = " [LAN]" if dev.get('ip') else ""
            print(f"  [{idx}] {name} ({sku}){ip_info}")
            device_map[idx] = dev
            idx += 1

    if other:
        print("\nOther Devices:")
        for dev in other:
            # Handle both API format ('deviceName') and JSON format ('name')
            name = dev.get('deviceName') or dev.get('name', 'Unknown')
            sku = dev.get('sku', 'Unknown')
            ip_info = " [LAN]" if dev.get('ip') else ""
            print(f"  [{idx}] {name} ({sku}){ip_info}")
            device_map[idx] = dev
            idx += 1

    print("=" * 80)

    # Get user selection
    while True:
        try:
            selection = input(f"\nSelect device [1-{len(device_map)}] or 'q' to quit: ").strip()

            if selection.lower() == 'q':
                return None

            selection_num = int(selection)
            if 1 <= selection_num <= len(device_map):
                selected_dev = device_map[selection_num]
                print(f"\n✓ Selected: {selected_dev.get('deviceName')}")
                return selected_dev
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(device_map)}")

        except ValueError:
            print("Invalid input. Please enter a number or 'q'")
        except KeyboardInterrupt:
            print("\n\nTest cancelled by user")
            return None


def get_test_device(api_key: str, devices_file: str = None):
    """
    Get device for testing through interactive selection.

    Args:
        api_key: Govee API key
        devices_file: Optional path to devices JSON file

    Returns:
        Dictionary with device info: {
            'api_key': str,
            'device_id': str,
            'sku': str,
            'name': str,
            'ip': str or None,
            'full_data': dict
        }
    """
    devices_list = load_device_from_file(api_key, devices_file)

    if not devices_list:
        print("Error: No devices found")
        return None

    selected = select_device_interactive(devices_list)

    if not selected:
        return None

    return {
        'api_key': api_key,
        # Handle both API format ('device') and JSON format ('id')
        'device_id': selected.get('device') or selected.get('id'),
        'sku': selected.get('sku'),
        # Handle both API format ('deviceName') and JSON format ('name')
        'name': selected.get('deviceName') or selected.get('name'),
        'ip': selected.get('ip'),
        'full_data': selected
    }


def print_test_step(step_num: int, total_steps: int, action: str, expected: str):
    """
    Print a formatted test step with expected outcome.

    Args:
        step_num: Current step number
        total_steps: Total number of steps
        action: Description of action being performed
        expected: Expected result/outcome
    """
    print(f"\n{'─' * 80}")
    print(f"STEP {step_num}/{total_steps}: {action}")
    print(f"Expected: {expected}")
    print(f"{'─' * 80}")


def print_step_result(success: bool, actual_result: str = None):
    """
    Print the result of a test step.

    Args:
        success: Whether step succeeded
        actual_result: Optional description of actual result
    """
    status = "✓ SUCCESS" if success else "✗ FAILED"
    color = "\033[92m" if success else "\033[91m"  # Green or Red
    reset = "\033[0m"

    print(f"{color}{status}{reset}", end="")
    if actual_result:
        print(f" - {actual_result}")
    else:
        print()


if __name__ == "__main__":
    # Test the device selection
    import sys

    if len(sys.argv) < 2:
        print("Usage: python test_config.py <API_KEY> [devices_file]")
        sys.exit(1)

    api_key = sys.argv[1]
    devices_file = sys.argv[2] if len(sys.argv) > 2 else None

    device_info = get_test_device(api_key, devices_file)

    if device_info:
        print("\nDevice Information:")
        print(f"  Name: {device_info['name']}")
        print(f"  Device ID: {device_info['device_id']}")
        print(f"  SKU: {device_info['sku']}")
        print(f"  IP: {device_info['ip'] or 'N/A'}")
    else:
        print("\nNo device selected")
