"""
Cloud API: POST /router/api/v1/device/scenes

Fetches built-in scenes for a specific device.
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, List
import requests

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from govee.exceptions import GoveeAPIError, GoveeConnectionError, GoveeTimeoutError

logger = logging.getLogger(__name__)

ENDPOINT = "/device/scenes"


def get_scenes(
    api_key: str,
    device_id: str,
    sku: str,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
    device_name: str = None,
) -> List[Dict[str, Any]]:
    """
    Fetch built-in scenes for a specific device.

    Built-in scenes are Govee's default scenes (like "Sunrise", "Sunset", "Aurora")
    that users can apply but cannot modify.

    Args:
        api_key: Govee API key
        device_id: Device ID (e.g., "14:15:60:74:F4:07:99:39")
        sku: Device SKU (e.g., "H6008")
        base_url: Base URL for Govee API
        timeout: Request timeout in seconds

    Returns:
        List of scene dictionaries

    Raises:
        GoveeAPIError: If API returns an error
        GoveeConnectionError: If connection fails
        GoveeTimeoutError: If request times out

    Example response:
        [
            {
                "name": "Sunrise",
                "value": {"paramId": 1, "id": 10}
            },
            {
                "name": "Sunset",
                "value": {"paramId": 1, "id": 11}
            }
        ]
    """
    url = f"{base_url.rstrip('/')}{ENDPOINT}"
    headers = {"Govee-API-Key": api_key, "Content-Type": "application/json"}

    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {"device": device_id, "sku": sku},
    }

    device_label = device_name or device_id
    logger.debug(f"Fetching built-in scenes for device {device_label} (SKU: {sku})")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        # Check for API error codes
        code = data.get("code")
        if code != 200:
            message = data.get("message", "Unknown error")

            # 400 errors typically mean the device doesn't support scenes
            # This is expected for some devices (like plugs), so log as debug
            if code == 400:
                logger.debug(f"Device {device_label} does not support scenes (400 error)")
            else:
                logger.error(f"API error {code} for device {device_label}: {message}")

            raise GoveeAPIError(
                f"API returned error code {code}: {message}",
                status_code=code,
                response_data=data,
            )

        # Extract scenes from capabilities
        # The API returns scenes in: payload.capabilities[].parameters.options[]
        # where capability type is "devices.capabilities.dynamic_scene" and instance is "lightScene"
        scenes = []
        payload = data.get("payload", {})
        capabilities = payload.get("capabilities", [])

        for cap in capabilities:
            if cap.get("type") == "devices.capabilities.dynamic_scene" and cap.get("instance") == "lightScene":
                options = cap.get("parameters", {}).get("options", [])
                # Each option has: {"name": "...", "value": {"paramId": X, "id": Y}}
                for opt in options:
                    scenes.append({
                        "name": opt.get("name"),
                        "value": opt.get("value")
                    })
                break  # Only one lightScene capability per device

        logger.info(f"Successfully fetched {len(scenes)} built-in scenes for {device_label}")
        return scenes

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
        # Check if this is a GoveeAPIError with 400 status (expected for devices without scenes)
        if isinstance(e, GoveeAPIError) and "400" in str(e):
            logger.debug(f"Device {device_label} does not support scenes (caught in handler)")
        else:
            logger.error(f"Unexpected error: {e}")
        raise GoveeAPIError(f"Unexpected error fetching scenes: {e}") from e


async def get_scenes_async(
    api_key: str,
    device_id: str,
    sku: str,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
    device_name: str = None,
    session: aiohttp.ClientSession = None,
) -> List[Dict[str, Any]]:
    """
    Async version: Fetch built-in scenes for a specific device.

    Built-in scenes are Govee's default scenes (like "Sunrise", "Sunset", "Aurora")
    that users can apply but cannot modify.

    Args:
        api_key: Govee API key
        device_id: Device ID (e.g., "14:15:60:74:F4:07:99:39")
        sku: Device SKU (e.g., "H6008")
        base_url: Base URL for Govee API
        timeout: Request timeout in seconds
        device_name: Optional device name for logging
        session: Optional aiohttp session (will create one if not provided)

    Returns:
        List of scene dictionaries

    Raises:
        GoveeAPIError: If API returns an error
        GoveeConnectionError: If connection fails
        GoveeTimeoutError: If request times out
    """
    if not AIOHTTP_AVAILABLE:
        raise ImportError("aiohttp is required for async operations. Install with: pip install aiohttp")

    url = f"{base_url.rstrip('/')}{ENDPOINT}"
    headers = {"Govee-API-Key": api_key, "Content-Type": "application/json"}

    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {"device": device_id, "sku": sku},
    }

    device_label = device_name or device_id
    logger.debug(f"Fetching built-in scenes for device {device_label} (SKU: {sku})")

    # Create session if not provided
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            response.raise_for_status()
            data = await response.json()

            # Check for API error codes
            code = data.get("code")
            if code != 200:
                message = data.get("message", "Unknown error")

                # 400 errors typically mean the device doesn't support scenes
                if code == 400:
                    logger.debug(f"Device {device_label} does not support scenes (400 error)")
                else:
                    logger.error(f"API error {code} for device {device_label}: {message}")

                raise GoveeAPIError(
                    f"API returned error code {code}: {message}",
                    status_code=code,
                    response_data=data,
                )

            # Extract scenes from capabilities
            scenes = []
            payload_data = data.get("payload", {})
            capabilities = payload_data.get("capabilities", [])

            for cap in capabilities:
                if cap.get("type") == "devices.capabilities.dynamic_scene" and cap.get("instance") == "lightScene":
                    options = cap.get("parameters", {}).get("options", [])
                    for opt in options:
                        scenes.append({
                            "name": opt.get("name"),
                            "value": opt.get("value")
                        })
                    break

            logger.info(f"Successfully fetched {len(scenes)} built-in scenes for {device_label}")
            return scenes

    except aiohttp.ClientError as e:
        logger.error(f"Connection error: {e}")
        raise GoveeConnectionError(f"Failed to connect to {url}") from e

    except asyncio.TimeoutError as e:
        logger.error(f"Request timed out after {timeout}s")
        raise GoveeTimeoutError(f"Request to {url} timed out after {timeout}s") from e

    except Exception as e:
        if isinstance(e, GoveeAPIError) and "400" in str(e):
            logger.debug(f"Device {device_label} does not support scenes (caught in handler)")
        else:
            logger.error(f"Unexpected error: {e}")
        raise GoveeAPIError(f"Unexpected error fetching scenes: {e}") from e

    finally:
        if close_session:
            await session.close()
