#!/usr/bin/env python3
"""
Batch operations example.

Demonstrates:
- Importing devices from Python modules
- Creating device collections
- Controlling multiple devices concurrently
- Batch power, brightness, and color operations
"""
import time
from govee import GoveeClient, Colors

# Import devices directly from generated module
# (Run setup script first to generate govee_devices.py)
from govee_devices import garage_left, garage_right

# Initialize client
client = GoveeClient(
    api_key="your-api-key-here",
    prefer_lan=True,
    max_workers=10,  # Control up to 10 devices simultaneously
    log_level="INFO"
)

# Create a collection of garage lights using imported devices
garage_lights = client.create_collection("garage", [
    garage_left,
    garage_right
])

print(f"Controlling {len(garage_lights)} devices: {[d.name for d in garage_lights]}")

# Turn all on concurrently
print("\nTurning all on...")
results = client.power_all(garage_lights, on=True)
print(f"Success: {sum(results.values())}/{len(results)}")
time.sleep(1)

# Set brightness on all
print("\nSetting brightness to 75%...")
results = client.set_brightness_all(garage_lights, 75)
print(f"Success: {sum(results.values())}/{len(results)}")
time.sleep(1)

# Cycle through colors
colors = [Colors.RED, Colors.GREEN, Colors.BLUE, Colors.PURPLE]
for color in colors:
    print(f"\nSetting color to {color}...")
    results = client.set_color_all(garage_lights, color)
    print(f"Success: {sum(results.values())}/{len(results)}")
    time.sleep(2)

# Turn all off
print("\nTurning all off...")
results = client.power_all(garage_lights, on=False)
print(f"Success: {sum(results.values())}/{len(results)}")

print("\nDone!")
