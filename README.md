# govee-python-sdk

A modern, easy-to-use Python library for controlling Govee smart lights via LAN (UDP) and Cloud (HTTPS) APIs.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Interactive CLI Wizard** - Easy setup and device control with `govee-sync`
- **Dual Protocol Support** - LAN (UDP) for fast local control, Cloud API for full features
- **Automatic Fallback** - Tries LAN first, falls back to Cloud seamlessly
- **Type-Safe Models** - Full type hints with dataclasses for IDE autocomplete
- **Python Module Export** - Import devices and scenes directly as Python objects
- **Built-in & DIY Scenes** - Apply Govee's default scenes or your custom creations
- **Concurrent Operations** - Control multiple devices simultaneously
- **Batch Operations** - Group devices for coordinated control

## Quick Start

### Installation

```bash
pip install govee-python
```

### Interactive Wizard

The easiest way to get started:

```bash
govee-sync
```

The wizard will guide you through:
1. Setting up your API key
2. Discovering your Govee devices
3. Fetching available scenes (built-in and DIY)
4. Exporting everything as Python modules
5. Controlling your devices interactively

### Using in Your Code

After running the wizard, you'll have Python modules with your devices:

```python
from govee import GoveeClient, Colors
from govee_devices import garage_left, garage_right
from govee_scenes import sunset_glow_h6008

# Initialize client
client = GoveeClient(
    api_key="your-api-key-here",
    prefer_lan=True  # Try LAN first for faster response
)

# Control a single device
client.power(garage_left, on=True)
client.set_brightness(garage_left, 75)
client.set_color(garage_left, Colors.NEON_PINK)

# Apply a scene
client.apply_scene(garage_left, sunset_glow_h6008)

# Control multiple devices
garage_lights = client.create_collection("garage", [garage_left, garage_right])
client.power_all(garage_lights, on=True)
client.set_color_all(garage_lights, Colors.BLUE)
```

## Getting Your API Key

1. Open the **Govee Home** app
2. Go to **Settings** → **About Us** → **Apply for API Key**
3. Follow the instructions to receive your key via email

## Installation Options

### From PyPI (Recommended)

```bash
pip install govee-python
```

### From Source

```bash
git clone https://github.com/yourusername/govee-python-sdk.git
cd govee-python-sdk
pip install -e .
```

## Usage Examples

### Basic Device Control

```python
from govee import GoveeClient, Colors

client = GoveeClient(api_key="your-api-key-here")

# Discover devices
devices = client.discover_devices()
device = client.get_device("Living Room Light")

# Power control
client.power(device, on=True)
client.power(device, on=False)

# Brightness (1-100%)
client.set_brightness(device, 50)

# Colors
client.set_color(device, Colors.RED)
client.set_color(device, (255, 128, 0))  # Custom RGB

# Color temperature (2000-9000K)
client.set_color_temperature(device, 4000)
```

### Working with Scenes

```python
# Get built-in scenes
scenes = client.get_scenes(device)
sunset = [s for s in scenes if s.name == "Sunset Glow"][0]
client.apply_scene(device, sunset)

# Get DIY scenes
diy_scenes = client.get_diy_scenes(device)
my_scene = [s for s in diy_scenes if s.name == "My Custom Scene"][0]
client.apply_scene(device, my_scene)
```

### Batch Operations

```python
# Create a collection
living_room = client.create_collection("living_room", [
    client.get_device("TV Backlight"),
    client.get_device("Floor Lamp"),
    client.get_device("Ceiling Light")
])

# Control all devices at once
client.power_all(living_room, on=True)
client.set_brightness_all(living_room, 80)
client.set_color_all(living_room, Colors.WARM_WHITE)

# Results dictionary shows success/failure per device
results = client.power_all(living_room, on=True)
print(f"Success: {sum(results.values())}/{len(results)}")
```

### Export Devices as Python Modules

```python
client = GoveeClient(api_key="your-api-key-here")

# Discover everything
devices = client.discover_devices()
builtin_scenes = client.discover_builtin_scenes()
diy_scenes = client.discover_diy_scenes()

# Export to Python modules
client.export_as_modules("./")

# This creates:
# - govee_devices.py (all your devices as importable objects)
# - govee_scenes.py (built-in scenes by device SKU)
# - govee_diy_scenes.py (your custom DIY scenes)
```

Now you can import them:

```python
from govee_devices import bedroom_light, garage_left
from govee_scenes import sunset_glow_h6008, aurora_h7021
from govee_diy_scenes import my_halloween_scene_h6008
```

## CLI Wizard Commands

The interactive wizard (`govee-sync`) provides:

- **Update API Key** - Change your Govee API key
- **Fetch Govee Devices** - Discover devices and scenes from the cloud
- **Device Commands** - Interactive menu to control any device
  - Turn on/off
  - Set colors
  - Adjust brightness
  - Change color temperature
  - Apply scenes (built-in or DIY)
- **Run Tests** - Test all device features automatically

## Configuration

### Client Options

```python
client = GoveeClient(
    api_key="your-key",
    prefer_lan=True,         # Try LAN first (faster)
    lan_port=4003,           # UDP port for LAN control
    timeout=10.0,            # Request timeout in seconds
    max_workers=10,          # Concurrent workers for batch operations
    log_level="INFO"         # Logging level (DEBUG, INFO, WARNING, ERROR)
)
```

### LAN Control Setup

For faster LAN control:

1. Enable **LAN Control** in the Govee Home app for each device
2. Ensure devices are on the same network as your Python script
3. The library will automatically detect and use LAN when available

The wizard will help you configure LAN control interactively.

## Device Models

### Device

```python
device = Device(
    id="14:15:60:74:F4:07:99:39",  # Govee MAC address
    name="Garage Left",             # Human-readable name
    sku="H6008",                    # Device model
    ip="192.168.1.100",             # IP address (optional, for LAN)
    capabilities=[...],             # Supported features
    metadata={...}                  # Additional device info
)

# Check capabilities
device.supports_lan           # Has LAN control enabled
device.supports_cloud         # Can use Cloud API
device.supports_scenes        # Supports scene application
device.is_light               # Is a light (vs plug/sensor)
```

### Scene (Built-in)

```python
scene = Scene(
    name="Sunset Glow",
    value={"id": 1173, "paramId": 1235},  # Scene IDs
    sku="H6008",                           # Compatible device model
    metadata={}
)
```

### DIYScene (User-created)

```python
diy_scene = DIYScene(
    id=12345,                    # Scene ID
    name="Halloween Spooky",     # Your custom name
    sku="H6008",                 # Compatible device model
    metadata={}
)
```

## Predefined Colors

```python
from govee import Colors

# Basic colors
Colors.WHITE, Colors.RED, Colors.GREEN, Colors.BLUE
Colors.YELLOW, Colors.CYAN, Colors.MAGENTA

# Extended colors
Colors.ORANGE, Colors.PURPLE, Colors.PINK
Colors.WARM_WHITE, Colors.COOL_WHITE

# Neon colors
Colors.NEON_PINK, Colors.NEON_PURPLE, Colors.NEON_BLUE
Colors.NEON_ORANGE, Colors.NEON_YELLOW, Colors.NEON_GREEN

# Or use custom RGB
client.set_color(device, (255, 128, 64))
```

## Error Handling

```python
from govee.exceptions import (
    GoveeAPIError,
    GoveeConnectionError,
    GoveeTimeoutError,
    GoveeDeviceNotFoundError,
    GoveeSceneNotFoundError
)

try:
    client.power(device, on=True)
except GoveeConnectionError:
    print("Failed to connect to device")
except GoveeTimeoutError:
    print("Request timed out")
except GoveeAPIError as e:
    print(f"API error {e.status_code}: {e}")
```

## Package Structure

```
govee/
├── __init__.py           # Main exports (GoveeClient, Colors, models)
├── client.py             # GoveeClient - main API
├── models.py             # Device, Scene, DIYScene, Collection models
├── exceptions.py         # Custom exceptions
├── cli.py                # Interactive CLI wizard (govee-sync)
├── api/
│   ├── cloud/            # Cloud API endpoints
│   │   ├── devices.py              # Device discovery
│   │   ├── device_control.py       # Device commands
│   │   ├── device_scenes.py        # Built-in scenes
│   │   └── device_diy_scenes.py    # DIY scenes
│   └── lan/              # LAN API endpoints
│       ├── power.py                # UDP power control
│       ├── brightness.py           # UDP brightness control
│       └── color.py                # UDP color control
└── discovery/
    └── sync.py           # Device discovery with smart sync

examples/
├── basic_control.py      # Simple device control
└── batch_operations.py   # Multi-device control
```

## Examples

See the `examples/` directory for complete examples:

- [basic_control.py](examples/basic_control.py) - Simple on/off, colors, brightness
- [batch_operations.py](examples/batch_operations.py) - Controlling multiple devices

## API Reference

### GoveeClient Methods

**Discovery:**
- `discover_devices()` - Fetch devices from Govee Cloud
- `discover_builtin_scenes()` - Fetch Govee's built-in scenes
- `discover_diy_scenes()` - Fetch your custom DIY scenes
- `get_device(name)` - Get device by name
- `get_scene(name, device)` - Get scene by name for device
- `export_as_modules(directory)` - Export devices/scenes as Python modules

**Device Control:**
- `power(device, on)` - Turn device on/off
- `set_brightness(device, percent)` - Set brightness (1-100%)
- `set_color(device, rgb)` - Set RGB color
- `set_color_temperature(device, kelvin)` - Set color temperature (2000-9000K)
- `apply_scene(device, scene)` - Apply built-in or DIY scene

**Batch Operations:**
- `create_collection(name, devices)` - Group devices
- `power_all(devices, on)` - Power on/off multiple devices
- `set_brightness_all(devices, percent)` - Set brightness for all
- `set_color_all(devices, rgb)` - Set color for all
- `apply_scene_all(devices, scene)` - Apply scene to all

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Govee for their smart home devices and developer-friendly APIs
- The Python community for excellent libraries

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/govee-python-sdk/issues)
- **Documentation**: This README
- **Examples**: See the [examples/](examples/) directory

## Changelog

### 0.1.0 (2025-11-07)

Initial release:
- Interactive CLI wizard (`govee-sync`)
- LAN and Cloud API support
- Device discovery and Python module export
- Built-in and DIY scene support
- Batch operations for multiple devices
- Type-safe models with full IDE support
- Automatic LAN/Cloud fallback
- Comprehensive error handling
