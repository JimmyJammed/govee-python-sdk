"""
Example demonstrating state save/restore functionality.

This is useful for light shows where you want to restore the original
state of lights after the show completes.
"""
import time
from govee import GoveeClient, Colors

# Initialize client
API_KEY = "your-api-key-here"
client = GoveeClient(api_key=API_KEY, prefer_lan=True)

# Discover devices
print("Discovering devices...")
devices = client.discover_devices()
print(f"Found {len(devices)} device(s)\n")

if not devices:
    print("No devices found. Exiting.")
    exit(1)

# Get first device for demo
device = devices[0]
print(f"Using device: {device.name}")
print(f"Device supports: brightness={device.supports_brightness}, color={device.supports_color}\n")

# ========== EXAMPLE 1: Basic State Save/Restore ==========
print("=" * 60)
print("EXAMPLE 1: Basic State Save/Restore")
print("=" * 60)

# Save current state
print("\n1. Saving current state...")
client.save_state(device)
print("   State saved!")

# Check saved state
saved_state = client.get_saved_state(device)
if saved_state:
    print(f"   Saved state: {saved_state}")

# Change device state
print("\n2. Changing device to RED at 100% brightness...")
client.power(device, True)
time.sleep(0.5)

if device.supports_brightness:
    client.set_brightness(device, 100)
    time.sleep(0.5)

if device.supports_color:
    client.set_color(device, Colors.RED)
    time.sleep(0.5)

print("   Device changed! Wait 3 seconds...")
time.sleep(3)

# Restore original state
print("\n3. Restoring original state...")
results = client.restore_state(device)
if results.get(device.id):
    print("   State restored successfully!")
else:
    print("   Failed to restore state")

print("\n" + "=" * 60)
print("Demo complete! Your device should be back to its original state.")
print("=" * 60)


# ========== EXAMPLE 2: Multiple Devices ==========
if len(devices) > 1:
    print("\n\n")
    print("=" * 60)
    print("EXAMPLE 2: Multiple Devices")
    print("=" * 60)

    # Save state of first 3 devices
    demo_devices = devices[:3]
    print(f"\n1. Saving state of {len(demo_devices)} devices...")
    client.save_state(demo_devices)
    print("   States saved!")

    # Change all devices to blue
    print("\n2. Changing all devices to BLUE...")
    for dev in demo_devices:
        client.power(dev, True)
        if dev.supports_color:
            client.set_color(dev, Colors.BLUE)

    print("   Devices changed! Wait 3 seconds...")
    time.sleep(3)

    # Restore all states
    print("\n3. Restoring all states...")
    results = client.restore_state()
    success_count = sum(1 for v in results.values() if v)
    print(f"   Restored {success_count}/{len(results)} devices successfully")

    print("\n" + "=" * 60)
    print("Multi-device demo complete!")
    print("=" * 60)


# ========== EXAMPLE 3: Light Show Pattern ==========
print("\n\n")
print("=" * 60)
print("EXAMPLE 3: Light Show Pattern (recommended usage)")
print("=" * 60)

print("\n1. BEFORE LIGHT SHOW: Save state")
client.save_state(device)

print("\n2. DURING LIGHT SHOW: Do whatever you want")
print("   Simulating light show with color changes...")

# Simulate a light show
colors = [Colors.RED, Colors.GREEN, Colors.BLUE, Colors.YELLOW, Colors.PURPLE]
client.power(device, True)

for i, color in enumerate(colors):
    if device.supports_color:
        print(f"   Step {i+1}: {color}")
        client.set_color(device, color)
        time.sleep(0.8)

print("\n3. AFTER LIGHT SHOW: Restore state")
client.restore_state(device)
print("   Original state restored!")

print("\n" + "=" * 60)
print("Light show pattern complete!")
print("=" * 60)

# Clean up
print("\n\nCleaning up saved states...")
client.clear_saved_state()
print("Done!")
