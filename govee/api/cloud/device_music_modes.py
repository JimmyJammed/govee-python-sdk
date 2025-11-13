"""
Cloud API: Music Mode Capability Parsing

Parses music mode capabilities from device capabilities returned by GET /user/devices.
Music modes are included in the capabilities array with type "devices.capabilities.music_setting"
and instance "musicMode".
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def parse_music_modes(
    device_capabilities: List[Dict[str, Any]],
    device_id: str,
    sku: str,
    device_name: str = None,
) -> List[Dict[str, Any]]:
    """
    Parse music mode options from device capabilities.

    Music modes are returned as part of the device capabilities from GET /user/devices.
    This function extracts the available music modes for a device.

    Args:
        device_capabilities: List of capability dictionaries from device API response
        device_id: Device ID (e.g., "14:15:60:74:F4:07:99:39")
        sku: Device SKU (e.g., "H6008")
        device_name: Optional device name for logging

    Returns:
        List of music mode dictionaries with structure:
        [
            {
                "name": "Energic",
                "value": 5
            },
            {
                "name": "Rhythm",
                "value": 3
            }
        ]

    Example capability structure:
        {
            "type": "devices.capabilities.music_setting",
            "instance": "musicMode",
            "parameters": {
                "dataType": "STRUCT",
                "fields": [
                    {
                        "fieldName": "musicMode",
                        "dataType": "ENUM",
                        "options": [
                            {"name": "Energic", "value": 5},
                            {"name": "Rhythm", "value": 3}
                        ]
                    },
                    {
                        "fieldName": "sensitivity",
                        "dataType": "INTEGER",
                        "range": {"min": 0, "max": 100, "precision": 1}
                    }
                ]
            }
        }
    """
    device_label = device_name or device_id
    logger.debug(f"Parsing music mode capabilities for device {device_label} (SKU: {sku})")

    music_modes = []
    metadata = {}

    # Look for music_setting capability
    for cap in device_capabilities:
        if (
            cap.get("type") == "devices.capabilities.music_setting"
            and cap.get("instance") == "musicMode"
        ):
            parameters = cap.get("parameters", {})
            fields = parameters.get("fields", [])

            # Extract music mode options and other field metadata
            for field in fields:
                field_name = field.get("fieldName")

                if field_name == "musicMode":
                    # Extract the music mode options
                    options = field.get("options", [])
                    for opt in options:
                        mode_name = opt.get("name")
                        mode_value = opt.get("value")
                        if mode_name and mode_value is not None:
                            music_modes.append({"name": mode_name, "value": mode_value})

                # Store metadata for other fields (sensitivity, autoColor, rgb)
                elif field_name in ["sensitivity", "autoColor", "rgb"]:
                    metadata[field_name] = {
                        "dataType": field.get("dataType"),
                        "unit": field.get("unit"),
                        "range": field.get("range"),
                        "options": field.get("options"),
                        "required": field.get("required", False),
                    }

            break  # Only one music_setting capability per device

    if music_modes:
        logger.info(f"Found {len(music_modes)} music modes for {device_label}")
    else:
        logger.debug(f"No music modes found for {device_label}")

    # Attach metadata to each mode for reference
    for mode in music_modes:
        mode["metadata"] = metadata

    return music_modes


def get_music_modes_from_device_data(
    device_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract music modes from full device data dictionary.

    Args:
        device_data: Device data dictionary from API (contains device, deviceName, sku, capabilities)

    Returns:
        List of music mode dictionaries

    Example:
        device_data = {
            "device": "14:15:60:74:F4:07:99:39",
            "deviceName": "Garage Left",
            "sku": "H6008",
            "capabilities": [...]
        }
        modes = get_music_modes_from_device_data(device_data)
    """
    device_id = device_data.get("device", "")
    device_name = device_data.get("deviceName", "")
    sku = device_data.get("sku", "")
    capabilities = device_data.get("capabilities", [])

    return parse_music_modes(
        device_capabilities=capabilities,
        device_id=device_id,
        sku=sku,
        device_name=device_name,
    )
