# State Management

The Govee Python SDK includes powerful state management functionality that allows you to save and restore device states (power, brightness, color, etc.). This is particularly useful for light shows, automation routines, or any scenario where you want to temporarily change devices and then restore them to their original state.

## Quick Start

```python
from govee import GoveeClient

client = GoveeClient(api_key="your-api-key")
devices = client.discover_devices()
device = client.get_device("Living Room")

# Save current state
client.save_state(device)

# Make changes during your light show
client.power(device, True)
client.set_color(device, (255, 0, 0))  # Red
client.set_brightness(device, 100)

# Restore original state
client.restore_state(device)
```

## Features

- **Comprehensive State Capture**: Saves power, brightness, color, color temperature
- **Single or Multiple Devices**: Save/restore one device or many at once
- **Automatic Fallback**: Gracefully handles devices that don't support certain features
- **Error Resilience**: Continues restoring other devices even if one fails
- **Collections Support**: Works with Device objects, lists, or Collections

## What Gets Saved?

The state manager captures:

- **Power State**: On/Off status
- **Brightness**: Current brightness level (1-100%)
- **Color**: RGB color values
- **Color Temperature**: Kelvin temperature (for devices that support it)

Scenes and music modes are intentionally **not** restored, as they may have been temporary and restoring them could be unpredictable.

## API Reference

### `save_state(devices, force_refresh=True)`

Save the current state of one or more devices.

**Parameters:**
- `devices` (Device | List[Device] | Collection): Device(s) to save state for
- `force_refresh` (bool): If True, fetches fresh state from API (default: True)

**Returns:**
- `Dict[str, DeviceState]`: Mapping of device IDs to their saved states

**Example:**
```python
# Single device
client.save_state(garage_light)

# Multiple devices
client.save_state([device1, device2, device3])

# Collection
client.save_state(all_lights)
```

### `restore_state(devices=None, skip_on_error=True)`

Restore previously saved state for devices.

**Parameters:**
- `devices` (Device | List[Device] | Collection | None): Devices to restore. If None, restores all saved devices.
- `skip_on_error` (bool): If True, continues on errors. If False, raises on first error (default: True)

**Returns:**
- `Dict[str, bool]`: Mapping of device IDs to success status (True=restored, False=failed)

**Example:**
```python
# Restore specific devices
client.restore_state([device1, device2])

# Restore all previously saved devices
client.restore_state()
```

### `clear_saved_state(devices=None)`

Clear saved state for devices.

**Parameters:**
- `devices` (Device | List[Device] | Collection | None): Devices to clear. If None, clears all.

**Example:**
```python
# Clear specific device
client.clear_saved_state(device)

# Clear all saved states
client.clear_saved_state()
```

### `get_saved_state(device)`

Get the saved state for a device without restoring it.

**Parameters:**
- `device` (Device): Device to get saved state for

**Returns:**
- `DeviceState | None`: Saved state if found, None otherwise

**Example:**
```python
state = client.get_saved_state(device)
if state:
    print(f"Saved state: power={state.power}, brightness={state.brightness}")
```

## Usage Patterns

### Pattern 1: Simple Light Show

```python
# Before light show
client.save_state(all_lights)

# During light show (change lights however you want)
client.power_all(all_lights, True)
client.set_color_all(all_lights, Colors.RED)
# ... more changes ...

# After light show
client.restore_state()  # Restores all saved devices
```

### Pattern 2: Per-Device Control

```python
# Save specific devices
client.save_state([living_room, bedroom, kitchen])

# Change them individually
client.set_color(living_room, Colors.BLUE)
client.set_brightness(bedroom, 50)
client.power(kitchen, False)

# Restore specific devices
client.restore_state([living_room, bedroom])  # Kitchen stays off
```

### Pattern 3: Error Handling

```python
# Save state with error handling
try:
    states = client.save_state(devices)
    print(f"Saved state for {len(states)} devices")
except Exception as e:
    print(f"Failed to save state: {e}")

# Restore with error handling
try:
    results = client.restore_state()
    success_count = sum(1 for v in results.values() if v)
    print(f"Restored {success_count}/{len(results)} devices")
except Exception as e:
    print(f"Failed to restore state: {e}")
```

### Pattern 4: Conditional Restoration

```python
# Save state
client.save_state(devices)

# Check if device has saved state before restoring
for device in devices:
    if client.get_saved_state(device):
        print(f"Restoring {device.name}")
        client.restore_state(device)
    else:
        print(f"No saved state for {device.name}")
```

### Pattern 5: Integration with Light Show Manager

```python
from lightshow import LightShowManager, Show
from govee import GoveeClient

client = GoveeClient(api_key="your-api-key")
devices = client.discover_devices()

async def pre_show_hook(show: Show, context: dict):
    """Save state before show starts"""
    print("Saving device states...")
    client.save_state(devices)

async def post_show_hook(show: Show, context: dict):
    """Restore state after show ends"""
    print("Restoring device states...")
    results = client.restore_state()
    print(f"Restored {sum(results.values())}/{len(results)} devices")

# Create show with hooks
show = Show(
    name="My Show",
    audio_file="show.mp3",
    duration=120.0
)

manager = LightShowManager(
    shows=[show],
    hooks=LifecycleHooks(
        pre_show=pre_show_hook,
        post_show=post_show_hook
    )
)

# Run show (state automatically saved/restored)
manager.run_show("My Show")
```

## DeviceState Object

The `DeviceState` object represents the saved state of a device:

```python
@dataclass
class DeviceState:
    device: Device                      # The device this state belongs to
    power: Optional[bool]               # Power state (True=on, False=off)
    brightness: Optional[int]           # Brightness (1-100%)
    color: Optional[Tuple[int, int, int]]  # RGB color tuple
    color_temperature: Optional[int]    # Color temperature in Kelvin
    scene: Optional[Dict]               # Scene information (not restored)
    music_mode: Optional[Dict]          # Music mode info (not restored)
    raw_capabilities: List[Dict]        # Raw API response
```

## StateManager (Advanced)

For advanced use cases, you can use the `StateManager` class directly:

```python
from govee import GoveeClient, StateManager

client = GoveeClient(api_key="your-api-key")
state_manager = StateManager(client)

# Save state
state_manager.save_state(devices)

# Check if device has saved state
if state_manager.has_saved_state(device):
    # Get saved state without restoring
    state = state_manager.get_saved_state(device)
    print(f"Device was at {state.brightness}% brightness")

    # Restore when ready
    state_manager.restore_state(device)
```

## Best Practices

1. **Save State Early**: Save device state before making any changes
2. **Use try/except**: Wrap save/restore calls in error handlers
3. **Restore in Finally**: Use try/finally to ensure state is restored even on errors
4. **Check Success**: Review the results dict from `restore_state()` to verify success
5. **Clear When Done**: Call `clear_saved_state()` when you're finished to free memory

## Complete Example

```python
from govee import GoveeClient, Colors
import time

client = GoveeClient(api_key="your-api-key")
devices = client.discover_devices()

# Get devices for light show
garage_lights = [d for d in devices if "garage" in d.name.lower()]

try:
    # Save current state
    print("Saving current state...")
    saved_states = client.save_state(garage_lights)
    print(f"Saved state for {len(saved_states)} devices")

    # Run light show
    print("Starting light show...")
    client.power_all(garage_lights, True)

    colors = [Colors.RED, Colors.GREEN, Colors.BLUE]
    for color in colors:
        client.set_color_all(garage_lights, color)
        time.sleep(2)

    print("Light show complete!")

finally:
    # Always restore state, even if show failed
    print("Restoring original state...")
    results = client.restore_state(garage_lights)
    success = sum(1 for v in results.values() if v)
    print(f"Restored {success}/{len(results)} devices")

    # Clean up
    client.clear_saved_state()
```

## Limitations

- State is stored in memory (not persisted to disk)
- Scenes and music modes are not restored (by design)
- API rate limits apply when saving/restoring many devices
- State may be stale if devices are controlled outside the SDK

## Troubleshooting

**"No state manager found" warning:**
- Call `save_state()` before calling `restore_state()`

**Some devices fail to restore:**
- Check the results dict from `restore_state()` to see which failed
- Devices may be offline or unreachable
- API rate limits may have been hit

**State doesn't match what I see:**
- Set `force_refresh=True` (default) to fetch fresh state from API
- Some devices may have been controlled outside the SDK

**Restore takes too long:**
- State restoration is sequential to ensure correct order (power first, then settings)
- For many devices, this can take a few seconds
- Consider using smaller groups of devices
