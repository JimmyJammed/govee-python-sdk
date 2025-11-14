# Govee Python SDK - Test Suite

Comprehensive test suite for validating LAN and Cloud API functionality.

## Overview

This test suite provides:
- **LAN API Tests**: Tests all LAN commands with device status verification at multiple intervals (0.5s, 1.0s, 1.5s, 2.0s, 3.0s)
- **Cloud API Tests**: Tests all Cloud API endpoints
- **Visual Feedback**: Clear step-by-step output showing expected vs actual results
- **Interactive Device Selection**: Choose which device to test at runtime

## Quick Start

### Run All Tests

```bash
python tests/run_tests.py YOUR_API_KEY
```

### Run Specific Test Suites

```bash
# LAN API tests only
python tests/run_tests.py YOUR_API_KEY --lan

# Cloud API tests only
python tests/run_tests.py YOUR_API_KEY --cloud
```

### Use Cached Devices File

```bash
python tests/run_tests.py YOUR_API_KEY --devices-file debug/govee_devices.json
```

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── README.md                # This file
├── run_tests.py             # Main test runner
├── test_config.py           # Device selection and configuration utilities
├── test_utils.py            # Test utilities (status verification, formatting)
├── test_lan_api.py          # LAN API test suite
└── test_cloud_api.py        # Cloud API test suite
```

## LAN API Tests

Tests the following LAN commands with device status verification:

1. **Power Control**
   - Power ON
   - Power OFF

2. **Brightness Control**
   - 25%, 50%, 75%, 100%

3. **RGB Color Control**
   - RED (255, 0, 0)
   - GREEN (0, 255, 0)
   - BLUE (0, 0, 255)
   - WHITE (255, 255, 255)

4. **Device Status Query**
   - Query current device state

### Status Verification

After each LAN command, the test suite queries the device status at multiple intervals:
- 0.5 seconds
- 1.0 seconds
- 1.5 seconds
- 2.0 seconds
- 3.0 seconds

This helps identify slow responses and ensures commands have been applied successfully.

### Example Output

```
────────────────────────────────────────────────────────────────────────────────
STEP 1/11: Power ON via LAN
Expected: Device should turn ON
────────────────────────────────────────────────────────────────────────────────
  Command result: {'msg': {'cmd': 'turn', 'data': {}}}
✓ SUCCESS
    [0.5s] Power: ON
    [1.0s] Power: ON

────────────────────────────────────────────────────────────────────────────────
STEP 2/11: Set Brightness to 25%
Expected: Brightness should be 25%
────────────────────────────────────────────────────────────────────────────────
  Command result: {'msg': {'cmd': 'brightness', 'data': {}}}
✓ SUCCESS
    [0.5s] Brightness: 25%
    [1.0s] Brightness: 25%
```

## Cloud API Tests

Tests the following Cloud API endpoints:

1. **Device Control**
   - Power ON/OFF
   - Brightness (25%, 50%, 75%, 100%)
   - RGB Colors (RED, GREEN, BLUE)

2. **Device State Query**
   - Get current device state with all capabilities

3. **Scenes** (if applicable)
   - Query available light scenes
   - Apply dynamic scenes

### Example Output

```
────────────────────────────────────────────────────────────────────────────────
STEP 1/11: Power ON via Cloud API
Expected: Device should turn ON, API returns code 200
────────────────────────────────────────────────────────────────────────────────
✓ SUCCESS - API returned code 200

────────────────────────────────────────────────────────────────────────────────
STEP 2/11: Set Brightness to 25%
Expected: API returns code 200
────────────────────────────────────────────────────────────────────────────────
✓ SUCCESS - API returned code 200
```

## Interactive Device Selection

When you run the tests, you'll be prompted to select a device:

```
================================================================================
AVAILABLE DEVICES
================================================================================

Lights:
  [1] Ground2 Machine (H7052) [LAN]
  [2] Bulb Cerebro (H6008) [LAN]
  [3] Jimmy Garage Left (H6008)
  [4] Jimmy Garage Right (H6008)
  ... and 55 more

Other Devices:
  [60] Plug Haze (H5080)
  [61] Plug Hawkins Lab (H5080)
================================================================================

Select device [1-63] or 'q' to quit:
```

Devices with `[LAN]` support both LAN and Cloud API tests.

## Requirements

- Python 3.7+
- Valid Govee API key
- At least one Govee device on your network (for LAN tests)

## Test Results

The test suite provides a summary at the end:

```
================================================================================
FINAL TEST SUMMARY
================================================================================
LAN API.............................................. ✓ PASS
Cloud API............................................ ✓ PASS
================================================================================
```

## Troubleshooting

### LAN Tests Fail

- Ensure device has an IP address and is on the same network
- Check that device supports LAN control
- Verify firewall settings allow UDP traffic on ports 4002-4003

### Status Verification Slow

- If status checks consistently succeed at 2-3 second intervals but not earlier, the device may have slower response times
- This is normal behavior for some devices

### Cloud API Tests Fail

- Verify API key is correct
- Check API rate limits (10,000 requests/day)
- Ensure device is online and connected to Govee cloud

## Running Individual Test Modules

You can also run test modules directly:

```bash
# LAN API tests
python tests/test_lan_api.py

# Cloud API tests
python tests/test_cloud_api.py
```

Note: These require updating the test configuration variables at the top of each file.

## Advanced Usage

### Custom Status Check Intervals

Edit `test_utils.py` and modify the `STATUS_CHECK_INTERVALS` variable:

```python
STATUS_CHECK_INTERVALS = [0.5, 1.0, 1.5, 2.0, 3.0]  # Default
```

### Custom Tolerance

Status verification uses tolerance values for numeric comparisons. Default is ±5 for brightness, ±10 for RGB values.

Edit calls to `verify_device_state()` to adjust:

```python
verified, history = verify_device_state(
    device_ip,
    {"brightness": 50},
    tolerance=10  # ±10 instead of default ±5
)
```

## Contributing

When adding new tests:
1. Follow the existing test structure
2. Use `print_test_step()` for clear step descriptions
3. Use `print_step_result()` for consistent success/failure output
4. Include status verification for LAN tests
5. Check API response codes for Cloud tests

## API Stability Tests

### `govee_api_stability_tests.py`

A specialized test suite for diagnosing Govee Cloud API consistency issues.

#### What It Tests

Makes multiple identical requests to Govee Cloud API endpoints and compares responses to detect instability:

1. **Devices API** - `/user/devices` endpoint consistency
2. **DIY Scenes API** - `/device/diy-scenes` endpoint consistency per device
3. **Built-in Scenes API** - `/device/scenes` endpoint consistency per device

#### Usage

```bash
# From the govee-python-sdk directory
export GOVEE_API_KEY="your-api-key-here"
python3 tests/govee_api_stability_tests.py

# Or enter API key when prompted
python3 tests/govee_api_stability_tests.py
```

#### Output

Results saved to: `logs/govee_api_stability_test_results.log`

The log includes:
- Timestamp for each request
- Comparison of responses
- Detailed list of differences
- Reproduction steps for Govee support team

#### Example Result

```
============================================================
  TEST 2: DIY Scenes API Stability
============================================================

Testing device: String Bulbs Peter (H6008)
  Fetch 1: 40 DIY scenes
  Fetch 2: 38 DIY scenes
  Fetch 3: 40 DIY scenes

  ✗ INSTABILITY DETECTED between Fetch 1 and Fetch 2:
    Only in Fetch 1: 2 scenes
      - SC Neon Books (ID: 17926227)
      - SC Bulb Clock1 (ID: 17927453)

⚠️  API INSTABILITY DETECTED
```

#### When to Use

Run this test when:
- Generated files change on consecutive `govee-sync` fetches
- You suspect the API is returning inconsistent data
- Preparing a bug report for Govee support

The detailed log can be sent directly to Govee support team as evidence of API instability.

## License

Same as govee-python-sdk main package.
