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

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from govee.client import GoveeClient
from govee.models import Device, Scene, Collection, Colors, RGBColor
from govee.exceptions import (
    GoveeError,
    GoveeAPIError,
    GoveeConnectionError,
    GoveeTimeoutError,
    GoveeDeviceNotFoundError,
    GoveeSceneNotFoundError,
    GoveeInvalidParameterError,
    GoveeLANNotSupportedError,
)
from govee.discovery import DeviceSync

__all__ = [
    "GoveeClient",
    "Device",
    "Scene",
    "Collection",
    "Colors",
    "RGBColor",
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
