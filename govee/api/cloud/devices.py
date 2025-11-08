"""
Cloud API: GET /router/api/v1/user/devices

Fetches all devices associated with the Govee account.
"""
import logging
from typing import Dict, Any
import requests

from govee.exceptions import GoveeAPIError, GoveeConnectionError, GoveeTimeoutError

logger = logging.getLogger(__name__)

ENDPOINT = "/user/devices"


def get_devices(
    api_key: str, base_url: str = "https://openapi.api.govee.com/router/api/v1", timeout: float = 10.0
) -> Dict[str, Any]:
    """
    Fetch all devices from Govee Cloud API.

    Args:
        api_key: Govee API key
        base_url: Base URL for Govee API (default: official endpoint)
        timeout: Request timeout in seconds

    Returns:
        Dictionary containing API response with devices list

    Raises:
        GoveeAPIError: If API returns an error
        GoveeConnectionError: If connection fails
        GoveeTimeoutError: If request times out

    Example response:
        {
            "code": 200,
            "message": "Success",
            "payload": {
                "capabilities": [...],
                "devices": [
                    {
                        "device": "14:15:60:74:F4:07:99:39",
                        "deviceName": "Garage Left",
                        "sku": "H6008",
                        "type": "devices.types.light",
                        "capabilities": [...]
                    }
                ]
            }
        }
    """
    url = f"{base_url.rstrip('/')}{ENDPOINT}"
    headers = {"Govee-API-Key": api_key, "Content-Type": "application/json"}

    logger.debug(f"Fetching devices from {url}")

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
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

        # Handle both old and new API response formats
        if "data" in data:
            # New API format: data is a list of devices directly
            devices_list = data.get("data", [])
        else:
            # Old API format: data is in payload.devices
            devices_list = data.get("payload", {}).get("devices", [])

        logger.info(f"Successfully fetched {len(devices_list)} devices")
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
        raise GoveeAPIError(f"Unexpected error fetching devices: {e}") from e
