"""
Cloud API: POST /router/api/v1/device/state

Query the current status of a device.
"""
import logging
import uuid
from typing import Dict, Any, List
import requests

from govee.exceptions import GoveeAPIError, GoveeConnectionError, GoveeTimeoutError

logger = logging.getLogger(__name__)

ENDPOINT = "/device/state"


def get_device_state(
    api_key: str,
    device_id: str,
    sku: str,
    base_url: str = "https://openapi.api.govee.com/router/api/v1",
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Query the current status of a device via Cloud API.

    Args:
        api_key: Govee API key
        device_id: Device ID (e.g., "14:15:60:74:F4:07:99:39")
        sku: Device SKU (e.g., "H6008")
        base_url: Base URL for Govee API
        timeout: Request timeout in seconds

    Returns:
        Dictionary containing device state with capabilities:
        {
            "sku": "H6008",
            "device": "14:15:60:74:F4:07:99:39",
            "capabilities": [
                {
                    "type": "devices.capabilities.on_off",
                    "instance": "powerSwitch",
                    "state": {"value": 1}
                },
                {
                    "type": "devices.capabilities.range",
                    "instance": "brightness",
                    "state": {"value": 100}
                }
            ]
        }

    Raises:
        GoveeAPIError: If API returns an error
        GoveeConnectionError: If connection fails
        GoveeTimeoutError: If request times out

    Note:
        When device is offline, returned status represents historical data.
        When online (state.value: true), data reflects current device state.
    """
    url = f"{base_url.rstrip('/')}{ENDPOINT}"
    headers = {"Govee-API-Key": api_key, "Content-Type": "application/json"}

    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {"device": device_id, "sku": sku},
    }

    logger.debug(f"Querying device state for {device_id} (SKU: {sku})")

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

        payload_data = data.get("payload", {})
        capabilities = payload_data.get("capabilities", [])
        logger.info(f"Successfully fetched state for {device_id}: {len(capabilities)} capabilities")
        return payload_data

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
        raise GoveeAPIError(f"Unexpected error fetching device state: {e}") from e
