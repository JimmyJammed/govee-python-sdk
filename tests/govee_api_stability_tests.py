#!/usr/bin/env python3
"""
Govee API Stability Tests

Tests the consistency of Govee Cloud API responses by making multiple
identical requests and comparing the results.

This test suite is designed to help diagnose API instability issues and
provide reproduction steps for the Govee support team.

Usage:
    python3 tests/govee_api_stability_tests.py

Results are saved to: logs/govee_api_stability_test_results.log
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to import govee module
sys.path.insert(0, str(Path(__file__).parent.parent))

from govee.client import GoveeClient
from govee.api.cloud import devices as cloud_devices
from govee.api.cloud import device_diy_scenes


class APIStabilityTester:
    """Test Govee API stability by comparing multiple identical requests."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = GoveeClient(api_key=api_key)
        self.log_lines = []
        self.test_start_time = datetime.now()

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        self.log_lines.append(log_line)

    def log_section(self, title: str):
        """Log a section header."""
        separator = "=" * 80
        self.log("")
        self.log(separator)
        self.log(f"  {title}")
        self.log(separator)
        self.log("")

    def save_log(self):
        """Save log to file."""
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / "govee_api_stability_test_results.log"

        with open(log_file, "w") as f:
            f.write("\n".join(self.log_lines))

        self.log(f"Log saved to: {log_file}")
        return log_file

    def compare_lists(self, list1: List[Any], list2: List[Any], item_type: str) -> Dict[str, Any]:
        """Compare two lists and return differences."""
        # Convert to sets for comparison (using JSON serialization for hashability)
        set1 = {json.dumps(item, sort_keys=True) for item in list1}
        set2 = {json.dumps(item, sort_keys=True) for item in list2}

        only_in_1 = set1 - set2
        only_in_2 = set2 - set1

        return {
            "total_1": len(list1),
            "total_2": len(list2),
            "only_in_fetch_1": len(only_in_1),
            "only_in_fetch_2": len(only_in_2),
            "items_only_in_1": [json.loads(item) for item in sorted(only_in_1)],
            "items_only_in_2": [json.loads(item) for item in sorted(only_in_2)],
            "is_identical": len(only_in_1) == 0 and len(only_in_2) == 0
        }

    async def test_devices_api_stability(self, num_tests: int = 3) -> bool:
        """Test if the devices API returns consistent results."""
        self.log_section("TEST 1: Device List API Stability")

        self.log(f"Making {num_tests} identical requests to the devices API...")
        self.log("Endpoint: GET /router/api/v1/user/devices")
        self.log("")

        results = []

        for i in range(num_tests):
            self.log(f"Fetch {i+1}/{num_tests}...")

            try:
                response = cloud_devices.get_devices(
                    api_key=self.api_key,
                    base_url=self.client.base_url,
                    timeout=self.client.timeout
                )

                # Extract devices data
                if "data" in response:
                    devices_data = response.get("data", [])
                else:
                    devices_data = response.get("payload", {}).get("devices", [])

                # Sort by device ID for consistent comparison
                devices_data = sorted(devices_data, key=lambda d: d.get("device", ""))

                results.append(devices_data)
                self.log(f"  ✓ Received {len(devices_data)} devices")

                # Small delay between requests
                if i < num_tests - 1:
                    await asyncio.sleep(1)

            except Exception as e:
                self.log(f"  ✗ Error: {e}", "ERROR")
                return False

        self.log("")
        self.log("Comparing results...")

        all_identical = True
        for i in range(1, num_tests):
            self.log(f"\nComparing Fetch 1 vs Fetch {i+1}:")
            comparison = self.compare_lists(results[0], results[i], "device")

            if comparison["is_identical"]:
                self.log("  ✓ Results are IDENTICAL")
            else:
                self.log("  ✗ Results are DIFFERENT", "WARNING")
                all_identical = False

                self.log(f"    Fetch 1 has {comparison['total_1']} devices")
                self.log(f"    Fetch {i+1} has {comparison['total_2']} devices")
                self.log(f"    {comparison['only_in_fetch_1']} devices only in Fetch 1")
                self.log(f"    {comparison['only_in_fetch_2']} devices only in Fetch {i+1}")

        return all_identical

    async def test_diy_scenes_api_stability(self, num_tests: int = 3) -> bool:
        """Test if the DIY scenes API returns consistent results for each device."""
        self.log_section("TEST 2: DIY Scenes API Stability")

        # First get devices
        self.log("Getting device list...")
        response = cloud_devices.get_devices(
            api_key=self.api_key,
            base_url=self.client.base_url,
            timeout=self.client.timeout
        )

        if "data" in response:
            devices_data = response.get("data", [])
        else:
            devices_data = response.get("payload", {}).get("devices", [])

        # Test a subset of devices (first 5 that support DIY scenes)
        self.log(f"Testing DIY scenes API for up to 5 devices...")
        self.log("Endpoint: POST /router/api/v1/device/diy-scenes")
        self.log("")

        tested_devices = 0
        unstable_devices = []

        for device_data in devices_data[:10]:  # Check first 10 devices
            if tested_devices >= 5:
                break

            device_id = device_data.get("device")
            device_name = device_data.get("deviceName")
            sku = device_data.get("sku")

            self.log(f"\nTesting device: {device_name} ({sku})")
            self.log(f"Device ID: {device_id}")

            results = []

            for i in range(num_tests):
                try:
                    diy_scenes = device_diy_scenes.get_diy_scenes(
                        api_key=self.api_key,
                        device_id=device_id,
                        sku=sku,
                        base_url=self.client.base_url,
                        timeout=self.client.timeout,
                        device_name=device_name
                    )

                    # Sort by scene ID for consistent comparison
                    diy_scenes = sorted(diy_scenes, key=lambda s: s.get("id", 0))

                    results.append(diy_scenes)
                    self.log(f"  Fetch {i+1}: {len(diy_scenes)} DIY scenes")

                    # Small delay between requests
                    if i < num_tests - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    # Device might not support DIY scenes
                    if "400" in str(e):
                        self.log(f"  Device does not support DIY scenes (400 error)")
                        break
                    else:
                        self.log(f"  Error: {e}", "ERROR")
                        break

            if len(results) == num_tests:
                tested_devices += 1

                # Compare results
                device_stable = True
                for i in range(1, num_tests):
                    comparison = self.compare_lists(results[0], results[i], "DIY scene")

                    if not comparison["is_identical"]:
                        device_stable = False
                        self.log(f"\n  ✗ INSTABILITY DETECTED between Fetch 1 and Fetch {i+1}:", "WARNING")
                        self.log(f"    Fetch 1: {comparison['total_1']} scenes")
                        self.log(f"    Fetch {i+1}: {comparison['total_2']} scenes")
                        self.log(f"    Only in Fetch 1: {comparison['only_in_fetch_1']} scenes")
                        self.log(f"    Only in Fetch {i+1}: {comparison['only_in_fetch_2']} scenes")

                        # Log the actual differences
                        if comparison['items_only_in_1']:
                            self.log(f"\n    Scenes only in Fetch 1:")
                            for scene in comparison['items_only_in_1'][:5]:  # Show first 5
                                self.log(f"      - {scene.get('name')} (ID: {scene.get('id')})")

                        if comparison['items_only_in_2']:
                            self.log(f"\n    Scenes only in Fetch {i+1}:")
                            for scene in comparison['items_only_in_2'][:5]:  # Show first 5
                                self.log(f"      - {scene.get('name')} (ID: {scene.get('id')})")

                if not device_stable:
                    unstable_devices.append({
                        "device_name": device_name,
                        "device_id": device_id,
                        "sku": sku
                    })
                else:
                    self.log(f"  ✓ All fetches returned identical results")

        self.log("")
        if unstable_devices:
            self.log(f"\n⚠️  FOUND API INSTABILITY in {len(unstable_devices)} device(s):", "WARNING")
            for dev in unstable_devices:
                self.log(f"  - {dev['device_name']} ({dev['sku']})")
            return False
        else:
            self.log(f"✓ All {tested_devices} tested devices returned consistent results")
            return True

    async def test_builtin_scenes_api_stability(self, num_tests: int = 3) -> bool:
        """Test if the built-in scenes API returns consistent results."""
        self.log_section("TEST 3: Built-in Scenes API Stability")

        # Get devices
        self.log("Getting device list...")
        response = cloud_devices.get_devices(
            api_key=self.api_key,
            base_url=self.client.base_url,
            timeout=self.client.timeout
        )

        if "data" in response:
            devices_data = response.get("data", [])
        else:
            devices_data = response.get("payload", {}).get("devices", [])

        # Test first device that supports scenes
        self.log(f"Testing built-in scenes API for first device...")
        self.log("Endpoint: POST /router/api/v1/device/scenes")
        self.log("")

        from govee.api.cloud import device_scenes

        for device_data in devices_data[:10]:
            device_id = device_data.get("device")
            device_name = device_data.get("deviceName")
            sku = device_data.get("sku")

            self.log(f"Testing device: {device_name} ({sku})")

            results = []

            for i in range(num_tests):
                try:
                    scenes = device_scenes.get_scenes(
                        api_key=self.api_key,
                        device_id=device_id,
                        sku=sku,
                        base_url=self.client.base_url,
                        timeout=self.client.timeout,
                        device_name=device_name
                    )

                    # Sort by scene ID for consistent comparison
                    scenes = sorted(scenes, key=lambda s: s.get("value", {}).get("id", 0))

                    results.append(scenes)
                    self.log(f"  Fetch {i+1}: {len(scenes)} built-in scenes")

                    if i < num_tests - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    if "400" in str(e):
                        self.log(f"  Device does not support built-in scenes (400 error)")
                        break
                    else:
                        self.log(f"  Error: {e}", "ERROR")
                        break

            if len(results) == num_tests:
                # Compare results
                all_identical = True
                for i in range(1, num_tests):
                    comparison = self.compare_lists(results[0], results[i], "built-in scene")

                    if not comparison["is_identical"]:
                        all_identical = False
                        self.log(f"\n  ✗ INSTABILITY DETECTED between Fetch 1 and Fetch {i+1}:", "WARNING")
                        self.log(f"    Fetch 1: {comparison['total_1']} scenes")
                        self.log(f"    Fetch {i+1}: {comparison['total_2']} scenes")

                if all_identical:
                    self.log(f"  ✓ All fetches returned identical results")

                return all_identical

        return True

    async def run_all_tests(self):
        """Run all stability tests."""
        self.log_section("Govee Cloud API Stability Test Suite")
        self.log(f"Test started at: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"API Base URL: {self.client.base_url}")
        self.log("")
        self.log("PURPOSE:")
        self.log("  This test suite makes multiple identical API requests to test")
        self.log("  whether the Govee Cloud API returns consistent results.")
        self.log("")
        self.log("REPRODUCTION STEPS:")
        self.log("  1. Run this test script with a valid Govee API key")
        self.log("  2. The script will make 3 identical requests to each API endpoint")
        self.log("  3. Results are compared to detect any differences")
        self.log("  4. Any inconsistencies are logged with details")

        results = {}

        # Test 1: Devices API
        try:
            results["devices_stable"] = await self.test_devices_api_stability(num_tests=3)
        except Exception as e:
            self.log(f"Error in devices test: {e}", "ERROR")
            results["devices_stable"] = False

        # Test 2: DIY Scenes API
        try:
            results["diy_scenes_stable"] = await self.test_diy_scenes_api_stability(num_tests=3)
        except Exception as e:
            self.log(f"Error in DIY scenes test: {e}", "ERROR")
            results["diy_scenes_stable"] = False

        # Test 3: Built-in Scenes API
        try:
            results["builtin_scenes_stable"] = await self.test_builtin_scenes_api_stability(num_tests=3)
        except Exception as e:
            self.log(f"Error in built-in scenes test: {e}", "ERROR")
            results["builtin_scenes_stable"] = False

        # Summary
        self.log_section("TEST SUMMARY")

        self.log("Results:")
        self.log(f"  Devices API:       {'✓ STABLE' if results.get('devices_stable') else '✗ UNSTABLE'}")
        self.log(f"  DIY Scenes API:    {'✓ STABLE' if results.get('diy_scenes_stable') else '✗ UNSTABLE'}")
        self.log(f"  Built-in Scenes:   {'✓ STABLE' if results.get('builtin_scenes_stable') else '✗ STABLE'}")

        self.log("")
        if all(results.values()):
            self.log("✓ All APIs are returning consistent results", "INFO")
        else:
            self.log("⚠️  API INSTABILITY DETECTED", "WARNING")
            self.log("")
            self.log("RECOMMENDATION FOR GOVEE SUPPORT TEAM:")
            self.log("  The Govee Cloud API is returning different results for identical requests.")
            self.log("  This causes issues for applications that rely on consistent data.")
            self.log("  Please investigate the following potential causes:")
            self.log("    1. API response caching issues")
            self.log("    2. Database replication lag between API servers")
            self.log("    3. Load balancer distributing requests to servers with different data")
            self.log("    4. Incomplete pagination or data truncation")

        self.log("")
        test_duration = (datetime.now() - self.test_start_time).total_seconds()
        self.log(f"Test completed in {test_duration:.1f} seconds")

        # Save log
        log_file = self.save_log()

        return results, log_file


async def main():
    """Main entry point."""
    # Get API key from environment or prompt user
    api_key = os.environ.get("GOVEE_API_KEY")

    if not api_key:
        print("Please provide your Govee API key:")
        print("  Option 1: Set GOVEE_API_KEY environment variable")
        print("  Option 2: Enter it now:")
        api_key = input("API Key: ").strip()

        if not api_key:
            print("Error: No API key provided")
            sys.exit(1)

    # Run tests
    tester = APIStabilityTester(api_key)
    results, log_file = await tester.run_all_tests()

    print(f"\n{'='*80}")
    print(f"Log file saved to: {log_file}")
    print(f"{'='*80}")

    # Exit with error code if any test failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
