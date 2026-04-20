"""
Govee Python - Control Govee smart lights via LAN and Cloud APIs.

Example usage:
    from govee import GoveeClient, Colors
    
    client = GoveeClient(api_key="your-key", prefer_lan=True)
    devices = client.discover_devices()
    
    garage_light = client.get_device("Garage Left")
    client.power(garage_light, on=True)
    client.set_color(garage_light, Colors.RED)
"""

__version__ = "1.2.0"
__author__ = "Your Name"
__license__ = "MIT"

from govee.client import GoveeClient
from govee.discovery import DeviceSync
from govee.exceptions import (
    GoveeAPIError,
    GoveeConnectionError,
    GoveeDeviceNotFoundError,
    GoveeError,
    GoveeInvalidParameterError,
    GoveeLANNotSupportedError,
    GoveeSceneNotFoundError,
    GoveeTimeoutError,
)
from govee.models import Collection, Colors, Device, RGBColor, Scene
from govee.state import DeviceState, StateManager

__all__ = [
    "GoveeClient",
    "Device",
    "Scene",
    "Collection",
    "Colors",
    "RGBColor",
    "StateManager",
    "DeviceState",
    "GoveeError",
    "GoveeAPIError",
    "GoveeConnectionError",
    "GoveeTimeoutError",
    "GoveeDeviceNotFoundError",
    "GoveeSceneNotFoundError",
    "GoveeInvalidParameterError",
    "GoveeLANNotSupportedError",
    "DeviceSync",
    "__version__",
]
