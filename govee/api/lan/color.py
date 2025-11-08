"""
LAN API: Color control via UDP

Sends color/color temperature commands to Govee devices over local network.
"""
import logging
import socket
import json
import time
from typing import Tuple, Optional

from govee.exceptions import GoveeConnectionError, GoveeLANNotSupportedError
from govee.api.lan import status as lan_status

logger = logging.getLogger(__name__)

DEFAULT_SEND_PORT = 4003  # Port to send commands to
DEFAULT_LISTEN_PORT = 4002  # Port to listen for responses on
DEFAULT_TIMEOUT = 5.0
DEFAULT_VERIFICATION_DELAY = 0.5  # Delay before verifying command (500ms - adjustable for slower networks/devices)


def send_color(
    device_ip: str,
    rgb: Tuple[int, int, int],
    color_temp_kelvin: int = 0,
    send_port: int = DEFAULT_SEND_PORT,
    listen_port: int = DEFAULT_LISTEN_PORT,
    timeout: float = DEFAULT_TIMEOUT,
    verification_delay: float = DEFAULT_VERIFICATION_DELAY
) -> bool:
    """
    Send color command to device via LAN (UDP) and optionally verify.

    Note: Govee devices use a split-port protocol:
    - Commands are sent TO port 4003
    - Responses are received FROM port 4002 (device sends back to client's port)
    - Control commands don't respond, but devStatus queries do

    Args:
        device_ip: Device IP address
        rgb: RGB tuple (r, g, b) where each value is 0-255
        color_temp_kelvin: Color temperature in Kelvin (2000-9000), or 0 for RGB mode
        send_port: UDP port to send command to (default: 4003)
        listen_port: UDP port to bind for receiving response (default: 4002)
        timeout: Socket timeout in seconds
        verification_delay: Seconds to wait before verifying (default: 0.5s).
                           Set to 0 to disable verification. Increase for slower networks.

    Returns:
        True if command sent successfully (and verified if verification_delay > 0)

    Raises:
        GoveeConnectionError: If unable to send command or verification fails
    """
    r, g, b = rgb

    # Clamp RGB values to valid range
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))

    # Clamp color temperature to valid range (or 0 for RGB mode)
    if color_temp_kelvin > 0:
        color_temp_kelvin = max(2000, min(9000, int(color_temp_kelvin)))

    # Govee LAN API requires commands to be wrapped in a "msg" object
    payload = {
        "msg": {
            "cmd": "colorwc",
            "data": {
                "color": {"r": r, "g": g, "b": b},
                "colorTemInKelvin": color_temp_kelvin,
            },
        }
    }

    # Send the command (fire-and-forget)
    _send_udp_command(device_ip, send_port, listen_port, payload, timeout)

    # Verify the command worked by querying device status (if verification enabled)
    if verification_delay > 0:
        # Give device a moment to process the command
        time.sleep(verification_delay)

        logger.debug(f"Verifying color command for {device_ip}")
        status = lan_status.get_device_status(
            device_ip=device_ip,
            send_port=send_port,
            listen_port=listen_port,
            timeout=timeout
        )

        if status is None:
            logger.warning(f"Could not verify color for {device_ip} (no status response)")
            # Don't fail - the command was sent successfully
            return True

        actual_color = status.get("color", {})
        actual_r = actual_color.get("r")
        actual_g = actual_color.get("g")
        actual_b = actual_color.get("b")

        if actual_r != r or actual_g != g or actual_b != b:
            raise GoveeConnectionError(
                f"Color command verification failed: expected RGB({r},{g},{b}), got RGB({actual_r},{actual_g},{actual_b})"
            )

        logger.info(f"Color command verified: {device_ip} is RGB({r},{g},{b})")

    return True


def _send_udp_command(
    device_ip: str, send_port: int, listen_port: int, payload: dict, timeout: float
) -> bool:
    """
    Send UDP command to Govee device (fire-and-forget).

    Note: Govee devices typically do NOT send responses to control commands.
    They execute the command immediately without acknowledgment. Only the
    devStatus query command generates a response.

    Args:
        device_ip: Device IP address
        send_port: UDP port to send command to (typically 4003)
        listen_port: UDP port for responses (unused for control commands, kept for API compatibility)
        payload: JSON payload to send
        timeout: Socket timeout (unused, kept for API compatibility)

    Returns:
        True if command sent successfully

    Raises:
        GoveeConnectionError: If unable to send
        GoveeLANNotSupportedError: If no IP provided
    """
    if not device_ip:
        raise GoveeLANNotSupportedError("No IP address provided for LAN control")

    sock = None
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Convert payload to JSON bytes
        message = json.dumps(payload).encode("utf-8")

        logger.debug(f"Sending LAN command to {device_ip}:{send_port}: {payload}")

        # Send command (fire-and-forget - device will not respond)
        sock.sendto(message, (device_ip, send_port))

        logger.info(f"Successfully sent LAN command to {device_ip}")
        return True

    except socket.error as e:
        logger.error(f"Socket error sending to {device_ip}: {e}")
        raise GoveeConnectionError(f"Failed to send LAN command to {device_ip}: {e}") from e

    except Exception as e:
        logger.error(f"Unexpected error sending to {device_ip}: {e}")
        raise GoveeConnectionError(f"Unexpected error sending LAN command: {e}") from e

    finally:
        if sock:
            sock.close()
