"""
LAN API: Device Discovery via UDP broadcast

Discovers Govee devices on the local network by listening for
UDP broadcast messages on port 4001.
"""
import socket
import json
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 4001
SCAN_MESSAGE = {"msg": {"cmd": "scan", "data": {"account_topic": "reserve"}}}


def discover_devices(timeout: float = 3.0, retries: int = 2) -> List[Dict[str, str]]:
    """
    Discover Govee devices on the local network via UDP broadcast.

    Args:
        timeout: How long to wait for responses (seconds)
        retries: Number of scan attempts

    Returns:
        List of discovered devices with format:
        [
            {
                "ip": "192.168.1.100",
                "device_id": "AA:BB:CC:DD:EE:FF:00:11",
                "sku": "H6008",
                "bleVersionHard": "3.01.01",
                "bleVersionSoft": "1.03.01",
                "wifiVersionHard": "1.00.10",
                "wifiVersionSoft": "1.02.03"
            },
            ...
        ]

    Example:
        devices = discover_devices()
        for device in devices:
            print(f"{device['device_id']} at {device['ip']}")
    """
    discovered = {}  # Use dict to deduplicate by device_id

    for attempt in range(retries):
        logger.debug(f"Discovery attempt {attempt + 1}/{retries}")

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        try:
            # Send broadcast message
            message = json.dumps(SCAN_MESSAGE).encode('utf-8')
            sock.sendto(message, ('<broadcast>', DISCOVERY_PORT))
            logger.debug(f"Sent broadcast scan message on port {DISCOVERY_PORT}")

            # Listen for responses
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    ip_address = addr[0]

                    # Parse response
                    try:
                        response = json.loads(data.decode('utf-8'))
                        msg = response.get('msg', {})

                        # Check if this is a device response
                        if msg.get('cmd') == 'scan' and 'data' in msg:
                            device_data = msg['data']
                            device_id = device_data.get('device')

                            if device_id:
                                discovered[device_id] = {
                                    'ip': ip_address,
                                    'device_id': device_id,
                                    'sku': device_data.get('sku'),
                                    'bleVersionHard': device_data.get('bleVersionHard'),
                                    'bleVersionSoft': device_data.get('bleVersionSoft'),
                                    'wifiVersionHard': device_data.get('wifiVersionHard'),
                                    'wifiVersionSoft': device_data.get('wifiVersionSoft'),
                                }
                                logger.info(f"Discovered device {device_id} ({device_data.get('sku')}) at {ip_address}")

                    except json.JSONDecodeError:
                        logger.debug(f"Received non-JSON response from {ip_address}")
                        continue

                except socket.timeout:
                    break  # Timeout reached, move to next retry

        except Exception as e:
            logger.error(f"Discovery error on attempt {attempt + 1}: {e}")

        finally:
            sock.close()

        # Short delay between retries
        if attempt < retries - 1:
            time.sleep(0.5)

    devices = list(discovered.values())
    logger.info(f"Discovery complete: found {len(devices)} device(s)")
    return devices


def find_device_ip(device_id: str, timeout: float = 3.0, retries: int = 2) -> Optional[str]:
    """
    Find the IP address of a specific device by device ID.

    Args:
        device_id: Device ID (MAC address format like AA:BB:CC:DD:EE:FF:00:11)
        timeout: How long to wait for responses (seconds)
        retries: Number of scan attempts

    Returns:
        IP address as string, or None if not found

    Example:
        ip = find_device_ip("AA:BB:CC:DD:EE:FF:00:11")
        if ip:
            print(f"Device found at {ip}")
    """
    devices = discover_devices(timeout=timeout, retries=retries)

    for device in devices:
        if device['device_id'] == device_id:
            return device['ip']

    return None


def get_device_ip_map(timeout: float = 3.0, retries: int = 2) -> Dict[str, str]:
    """
    Get a mapping of device IDs to IP addresses.

    Args:
        timeout: How long to wait for responses (seconds)
        retries: Number of scan attempts

    Returns:
        Dictionary mapping device_id -> ip_address

    Example:
        ip_map = get_device_ip_map()
        # {"AA:BB:CC:..": "192.168.1.100", ...}
    """
    devices = discover_devices(timeout=timeout, retries=retries)
    return {device['device_id']: device['ip'] for device in devices}
