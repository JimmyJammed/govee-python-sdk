"""
Test utilities for verifying device state changes.
"""
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from govee.api.lan import status
from govee.api.lan.power import DEFAULT_VERIFICATION_DELAY

logger = logging.getLogger(__name__)

# Default delay before status check (in seconds) - uses same delay as LAN API (500ms)
DEFAULT_STATUS_CHECK_DELAY = DEFAULT_VERIFICATION_DELAY


def verify_device_state(
    device_ip: str,
    expected_state: Dict[str, Any],
    delay: float = None,
    tolerance: int = 5
) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify device state after a delay.

    Args:
        device_ip: Device IP address
        expected_state: Expected state values (e.g., {"onOff": 1, "brightness": 50})
        delay: Seconds to wait before checking (default: 0.5s - same as LAN API)
        tolerance: Tolerance for numeric comparisons (e.g., brightness ±5)

    Returns:
        Tuple of (success: bool, state: Dict)
        state contains the actual device state retrieved
    """
    if delay is None:
        delay = DEFAULT_STATUS_CHECK_DELAY

    # Wait for device to process command
    time.sleep(delay)

    try:
        state = status.get_device_status(device_ip)

        if not state:
            logger.error("No response from device")
            return False, None

        # Check if state matches expected
        matches = True
        for key, expected_value in expected_state.items():
            actual_value = state.get(key)

            if actual_value is None:
                matches = False
                break

            # Handle nested values (e.g., color)
            if isinstance(expected_value, dict):
                if not isinstance(actual_value, dict):
                    matches = False
                    break
                for sub_key, sub_expected in expected_value.items():
                    sub_actual = actual_value.get(sub_key)
                    if abs(sub_actual - sub_expected) > tolerance:
                        matches = False
                        break
            # Handle numeric values with tolerance
            elif isinstance(expected_value, (int, float)):
                if abs(actual_value - expected_value) > tolerance:
                    matches = False
                    break
            # Handle exact matches
            else:
                if actual_value != expected_value:
                    matches = False
                    break

        if matches:
            logger.info(f"State verified successfully after {delay}s")
        else:
            logger.warning(f"State did not match expected after {delay}s")

        return matches, state

    except Exception as e:
        logger.error(f"Error checking status: {e}")
        return False, None


def print_test_header(test_name: str):
    """Print a formatted test header."""
    print(f"\n{'=' * 80}")
    print(f"TEST: {test_name}")
    print('=' * 80)


def print_test_result(
    command_name: str,
    command_result: Any,
    state_verified: bool,
    status_history: List[Dict[str, Any]]
):
    """
    Print formatted test results.

    Args:
        command_name: Name of command executed
        command_result: Result from command execution
        state_verified: Whether state was successfully verified
        status_history: List of status check results
    """
    print(f"\n[{command_name}]")
    print("-" * 40)
    print(f"Command Result: {command_result}")
    print(f"State Verified: {'✓ YES' if state_verified else '✗ NO'}")

    if status_history:
        print("\nStatus Check History:")
        for check in status_history:
            interval = check['interval']
            state = check.get('state')
            error = check.get('error')

            if error:
                print(f"  [{interval}s] ✗ Error: {error}")
            elif state:
                on_off = state.get('onOff', 'N/A')
                brightness = state.get('brightness', 'N/A')
                color = state.get('color', {})
                r = color.get('r', 'N/A')
                g = color.get('g', 'N/A')
                b = color.get('b', 'N/A')
                print(f"  [{interval}s] onOff={on_off}, brightness={brightness}, color=({r},{g},{b})")
            else:
                print(f"  [{interval}s] ✗ No response")


def compare_rgb(actual: Dict[str, int], expected: Tuple[int, int, int], tolerance: int = 5) -> bool:
    """
    Compare RGB values with tolerance.

    Args:
        actual: Dict with 'r', 'g', 'b' keys
        expected: Tuple of (r, g, b)
        tolerance: Tolerance for each color component

    Returns:
        True if colors match within tolerance
    """
    r, g, b = expected
    return (
        abs(actual.get('r', 0) - r) <= tolerance and
        abs(actual.get('g', 0) - g) <= tolerance and
        abs(actual.get('b', 0) - b) <= tolerance
    )
