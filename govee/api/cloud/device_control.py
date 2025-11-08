"""
Cloud API: POST /router/api/v1/device/control

Controls Govee devices via capability-based commands.
"""
import logging
import uuid
from typing import Dict, Any, Optional
import requests

from govee.exceptions import GoveeAPIError, GoveeConnectionError, GoveeTimeoutError

logger = logging.getLogger(__name__)

ENDPOINT = "/device/control"


def control_device(
    api_key: str,
    device_id: str,
    sku: str,
    capability_type: str,
    capability_instance: str,
    value: Any,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Send a control command to a Govee device via Cloud API.

    Args:
        api_key: Govee API key
        device_id: Device ID (e.g., "14:15:60:74:F4:07:99:39")
        sku: Device SKU (e.g., "H6008")
        capability_type: Capability type (e.g., "devices.capabilities.on_off")
        capability_instance: Capability instance (e.g., "powerSwitch")
        value: Capability value (type varies by capability)
        base_url: Base URL for Govee API
        timeout: Request timeout in seconds

    Returns:
        API response dictionary

    Raises:
        GoveeAPIError: If API returns an error
        GoveeConnectionError: If connection fails
        GoveeTimeoutError: If request times out

    Example usage:
        # Turn on device
        control_device(
            api_key="...",
            device_id="...",
            sku="H6008",
            capability_type="devices.capabilities.on_off",
            capability_instance="powerSwitch",
            value=1
        )
    """
    url = f"{base_url.rstrip('/')}{ENDPOINT}"
    headers = {"Govee-API-Key": api_key, "Content-Type": "application/json"}

    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {
            "device": device_id,
            "sku": sku,
            "capability": {"type": capability_type, "instance": capability_instance, "value": value},
        },
    }

    logger.debug(f"Sending control command to {device_id}: {capability_type}/{capability_instance}={value}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        # Check for API error codes
        code = data.get("code")
        if code != 200:
            message = data.get("message", "Unknown error")
            raise GoveeAPIError(
                f"API returned error code {code}: {message}",
                status_code=code,
                response_data=data,
            )

        logger.info(f"Successfully sent command to {device_id}")
        return data

    except requests.exceptions.Timeout as e:
        logger.error(f"Request timed out: {e}")
        raise GoveeTimeoutError(f"Request to {url} timed out after {timeout}s") from e

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise GoveeConnectionError(f"Failed to connect to {url}") from e

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        try:
            error_data = response.json()
            message = error_data.get("message", str(e))
        except Exception:
            message = str(e)

        raise GoveeAPIError(
            f"HTTP error: {message}", status_code=response.status_code, response_data=error_data
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise GoveeAPIError(f"Unexpected error controlling device: {e}") from e


# Convenience functions for common control operations


def power(
    api_key: str,
    device_id: str,
    sku: str,
    on: bool,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Turn device on or off.

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        on: True to turn on, False to turn off
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.on_off",
        capability_instance="powerSwitch",
        value=1 if on else 0,
        base_url=base_url,
        timeout=timeout,
    )


def brightness(
    api_key: str,
    device_id: str,
    sku: str,
    percent: int,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Set device brightness (1-100%).

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        percent: Brightness percentage (1-100)
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    # Clamp to valid range
    percent = max(1, min(100, int(percent)))

    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.brightness",
        capability_instance="brightness",
        value=percent,
        base_url=base_url,
        timeout=timeout,
    )


def color_rgb(
    api_key: str,
    device_id: str,
    sku: str,
    rgb: tuple,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Set device color (RGB).

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        rgb: RGB tuple (r, g, b) where each value is 0-255
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    r, g, b = rgb
    # Clamp to valid range
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))

    # Encode RGB as single integer: (r << 16) + (g << 8) + b
    rgb_value = (r << 16) + (g << 8) + b

    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.color_setting",
        capability_instance="colorRgb",
        value=rgb_value,
        base_url=base_url,
        timeout=timeout,
    )


def scene(
    api_key: str,
    device_id: str,
    sku: str,
    scene_id: int,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Apply a DIY scene to device.

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        scene_id: Scene ID from Govee API
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.dynamic_scene",
        capability_instance="diyScene",
        value=scene_id,
        base_url=base_url,
        timeout=timeout,
    )


def music_mode(
    api_key: str,
    device_id: str,
    sku: str,
    mode_value: int,
    sensitivity: int = 100,
    auto_color: int = 1,
    rgb: Optional[tuple] = None,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Set music visualization mode.

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        mode_value: Music mode ID (device-specific)
        sensitivity: Sensitivity (0-100), default 100
        auto_color: Auto color (1=on, 0=off), default 1
        rgb: Optional RGB color tuple if auto_color=0
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    # Clamp sensitivity
    sensitivity = max(0, min(100, int(sensitivity)))

    music_value = {"musicMode": mode_value, "sensitivity": sensitivity, "autoColor": auto_color}

    if rgb is not None and auto_color == 0:
        r, g, b = rgb
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        music_value["rgb"] = (r << 16) + (g << 8) + b

    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.music_setting",
        capability_instance="musicMode",
        value=music_value,
        base_url=base_url,
        timeout=timeout,
    )


def color_temperature_kelvin(
    api_key: str,
    device_id: str,
    sku: str,
    kelvin: int,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Set device color temperature in Kelvin.

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        kelvin: Color temperature in Kelvin (2000-9000)
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    # Clamp to valid range
    kelvin = max(2000, min(9000, int(kelvin)))

    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.color_setting",
        capability_instance="colorTemperatureK",
        value=kelvin,
        base_url=base_url,
        timeout=timeout,
    )


def toggle(
    api_key: str,
    device_id: str,
    sku: str,
    instance: str,
    on: bool,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Toggle device feature on/off (oscillation, nightlight, air deflector, etc.).

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        instance: Toggle instance (e.g., "oscillationToggle", "nightlightToggle")
        on: True to turn on, False to turn off
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.toggle",
        capability_instance=instance,
        value=1 if on else 0,
        base_url=base_url,
        timeout=timeout,
    )


def light_scene(
    api_key: str,
    device_id: str,
    sku: str,
    scene_id: int,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Apply a light scene to device.

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        scene_id: Light scene ID from Govee API
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.dynamic_scene",
        capability_instance="lightScene",
        value=scene_id,
        base_url=base_url,
        timeout=timeout,
    )


def snapshot_scene(
    api_key: str,
    device_id: str,
    sku: str,
    snapshot_id: int,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Apply a snapshot scene to device.

    Args:
        api_key: Govee API key
        device_id: Device ID
        sku: Device SKU
        snapshot_id: Snapshot scene ID
        base_url: Base URL for Govee API
        timeout: Request timeout

    Returns:
        API response
    """
    return control_device(
        api_key=api_key,
        device_id=device_id,
        sku=sku,
        capability_type="devices.capabilities.dynamic_scene",
        capability_instance="snapshot",
        value=snapshot_id,
        base_url=base_url,
        timeout=timeout,
    )
