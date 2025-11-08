#!/usr/bin/env python3
"""
Basic Govee device control example.

Demonstrates:
- Initializing the client
- Discovering devices
- Basic on/off control
- Setting brightness and color
"""
import time
from govee import GoveeClient, Colors

# Initialize client with your API key
client = GoveeClient(
    api_key="your-api-key-here",
    prefer_lan=True,  # Try LAN first for faster response
    log_level="INFO"
)

# Option 1: Discover devices from Cloud API (first-time setup)
print("Discovering devices...")
devices = client.discover_devices()
print(f"Found {len(devices)} devices")

# Export as Python modules for future use
client.export_as_modules("./")

# Option 2: Import device directly (after running export once)
# from govee_devices import garage_left
# device = garage_left

# Get a specific device
device = client.get_device("Garage Left")
print(f"Controlling device: {device.name}")
print(f"  SKU: {device.sku}")
print(f"  Supports LAN: {device.supports_lan}")
print(f"  IP: {device.ip or 'Not set'}")

# Turn on
print("\nTurning on...")
client.power(device, on=True)
time.sleep(1)

# Set brightness to 50%
print("Setting brightness to 50%...")
client.set_brightness(device, 50)
time.sleep(1)

# Change colors
colors = [
    ("Red", Colors.RED),
    ("Green", Colors.GREEN),
    ("Blue", Colors.BLUE),
    ("Purple", Colors.PURPLE),
    ("Neon Pink", Colors.NEON_PINK)
]

for color_name, color_rgb in colors:
    print(f"Setting color to {color_name}...")
    client.set_color(device, color_rgb)
    time.sleep(2)

# Set brightness to 100%
print("Setting brightness to 100%...")
client.set_brightness(device, 100)
time.sleep(1)

# Turn off
print("Turning off...")
client.power(device, on=False)

print("\nDone!")
