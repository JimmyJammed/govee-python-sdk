"""
LAN API: Device status query via UDP

Queries device status over local network to verify device state.
"""
import logging
import socket
import json
from typing import Optional, Dict, Any

from govee.exceptions import GoveeConnectionError, GoveeTimeoutError, GoveeLANNotSupportedError

logger = logging.getLogger(__name__)

DEFAULT_SEND_PORT = 4003  # Port to send commands to
DEFAULT_LISTEN_PORT = 4002  # Port to listen for responses on
DEFAULT_TIMEOUT = 2.0  # Shorter timeout for status queries


def get_device_status(
    device_ip: str,
    send_port: int = DEFAULT_SEND_PORT,
    listen_port: int = DEFAULT_LISTEN_PORT,
    timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """
    Query device status via LAN (UDP).

    Note: Govee devices use a split-port protocol:
    - Commands are sent TO port 4003
    - Responses are received FROM port 4002 (device sends back to client's port)

    Args:
        device_ip: Device IP address
        send_port: UDP port to send command to (default: 4003)
        listen_port: UDP port to bind for receiving response (default: 4002)
        timeout: Socket timeout in seconds

    Returns:
        Dictionary with device status:
        {
            "onOff": 1,  # 1=on, 0=off
            "brightness": 100,  # 1-100
            "color": {"r": 255, "g": 0, "b": 0},
            "colorTemInKelvin": 7200  # 2000-9000
        }
        Returns None if device doesn't respond

    Raises:
        GoveeConnectionError: If unable to send command
        GoveeLANNotSupportedError: If no IP provided
    """
    if not device_ip:
        raise GoveeLANNotSupportedError("No IP address provided for LAN control")

    payload = {
        "msg": {
            "cmd": "devStatus",
            "data": {}
        }
    }

    sock = None
    try:
        # Create UDP socket and bind to listen port for responses
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', listen_port))
        sock.settimeout(timeout)

        # Convert payload to JSON bytes
        message = json.dumps(payload).encode("utf-8")

        logger.debug(f"Querying device status at {device_ip}:{send_port} (listening on port {listen_port})")

        # Send query to device
        sock.sendto(message, (device_ip, send_port))

        # Wait for response on listen port
        try:
            response_data, addr = sock.recvfrom(1024)
            logger.debug(f"Received status response from {addr}: {response_data}")

            # Parse JSON response
            response = json.loads(response_data.decode("utf-8"))

            # Extract data from response
            if "msg" in response and "data" in response["msg"]:
                status = response["msg"]["data"]
                logger.info(f"Device {device_ip} status: {status}")
                return status
            else:
                logger.warning(f"Unexpected response format from {device_ip}: {response}")
                return None

        except socket.timeout:
            logger.warning(f"No status response from {device_ip} after {timeout}s")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse status response from {device_ip}: {e}")
            return None

    except socket.error as e:
        logger.error(f"Socket error querying {device_ip}: {e}")
        raise GoveeConnectionError(f"Failed to query device status at {device_ip}: {e}") from e

    except Exception as e:
        logger.error(f"Unexpected error querying {device_ip}: {e}")
        raise GoveeConnectionError(f"Unexpected error querying device status: {e}") from e

    finally:
        if sock:
            sock.close()
