"""
Cloud API: MQTT Device Event Subscription

Subscribe to real-time device events via MQTTS protocol.
Endpoint: mqtts://mqtt.openapi.govee.com:8883
Topic: GA/[API-Key]
"""
import logging
import json
import ssl
import threading
from typing import Callable, Optional, Dict, Any

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

from govee.exceptions import GoveeAPIError, GoveeConnectionError

logger = logging.getLogger(__name__)

MQTT_HOST = "mqtt.openapi.govee.com"
MQTT_PORT = 8883


class GoveeEventClient:
    """
    MQTT client for subscribing to Govee device events in real-time.

    Example usage:
        def on_event(event_data):
            print(f"Device event: {event_data}")

        client = GoveeEventClient(api_key="your-api-key")
        client.connect(on_event)
        # Events will be received via callback
        # Call client.disconnect() when done
    """

    def __init__(self, api_key: str, host: str = MQTT_HOST, port: int = MQTT_PORT):
        """
        Initialize MQTT event client.

        Args:
            api_key: Govee API key (used for authentication and topic subscription)
            host: MQTT broker host (default: mqtt.openapi.govee.com)
            port: MQTT broker port (default: 8883 for MQTTS)

        Raises:
            GoveeAPIError: If paho-mqtt library is not installed
        """
        if not MQTT_AVAILABLE:
            raise GoveeAPIError(
                "paho-mqtt library is required for device events. "
                "Install it with: pip install paho-mqtt"
            )

        self.api_key = api_key
        self.host = host
        self.port = port
        self.topic = f"GA/{api_key}"

        self._client: Optional[mqtt.Client] = None
        self._callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._connected = False
        self._connect_lock = threading.Lock()

        logger.info(f"Initialized GoveeEventClient for topic: {self.topic}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT connection is established."""
        if rc == 0:
            self._connected = True
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")

            # Subscribe to device events topic
            client.subscribe(self.topic)
            logger.info(f"Subscribed to topic: {self.topic}")
        else:
            self._connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized",
            }
            error_msg = error_messages.get(rc, f"Connection refused - code {rc}")
            logger.error(f"MQTT connection failed: {error_msg}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when MQTT connection is lost."""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code: {rc})")
        else:
            logger.info("MQTT client disconnected")

    def _on_message(self, client, userdata, msg):
        """Callback when a message is received."""
        try:
            payload = msg.payload.decode('utf-8')
            logger.debug(f"Received message on {msg.topic}: {payload}")

            # Parse JSON payload
            event_data = json.loads(payload)

            # Call user's callback if provided
            if self._callback:
                self._callback(event_data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing event: {e}")

    def connect(
        self,
        on_event: Callable[[Dict[str, Any]], None],
        blocking: bool = False,
        timeout: float = 10.0
    ) -> None:
        """
        Connect to MQTT broker and start receiving device events.

        Args:
            on_event: Callback function to handle device events.
                      Receives a dictionary with event data:
                      {
                          "msg": {
                              "cmd": "status",
                              "data": {
                                  "state": {"onOff": 1},
                                  "device": "device_id",
                                  "sku": "H6008"
                              }
                          }
                      }
            blocking: If True, blocks until disconnect() is called.
                     If False, runs in background thread.
            timeout: Connection timeout in seconds

        Raises:
            GoveeConnectionError: If connection fails
            GoveeAPIError: If MQTT client cannot be initialized
        """
        with self._connect_lock:
            if self._connected:
                logger.warning("Already connected to MQTT broker")
                return

            self._callback = on_event

            try:
                # Create MQTT client
                self._client = mqtt.Client(
                    client_id=f"govee_python_sdk_{self.api_key[:8]}",
                    protocol=mqtt.MQTTv311
                )

                # Set callbacks
                self._client.on_connect = self._on_connect
                self._client.on_disconnect = self._on_disconnect
                self._client.on_message = self._on_message

                # Configure TLS/SSL
                self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)

                # Set username (API key) for authentication
                self._client.username_pw_set(username=self.api_key)

                # Connect to broker
                logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}...")
                self._client.connect(self.host, self.port, keepalive=60)

                # Start network loop
                if blocking:
                    logger.info("Starting blocking event loop...")
                    self._client.loop_forever()
                else:
                    logger.info("Starting background event loop...")
                    self._client.loop_start()

            except Exception as e:
                logger.error(f"Failed to connect to MQTT broker: {e}")
                raise GoveeConnectionError(f"MQTT connection failed: {e}") from e

    def disconnect(self) -> None:
        """
        Disconnect from MQTT broker and stop receiving events.
        """
        with self._connect_lock:
            if not self._connected or not self._client:
                logger.warning("Not connected to MQTT broker")
                return

            try:
                logger.info("Disconnecting from MQTT broker...")
                self._client.loop_stop()
                self._client.disconnect()
                self._connected = False
                logger.info("Disconnected successfully")

            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                raise GoveeAPIError(f"Failed to disconnect: {e}") from e

    @property
    def is_connected(self) -> bool:
        """Check if client is currently connected to MQTT broker."""
        return self._connected

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        if self._connected:
            self.disconnect()


# Convenience function for simple event subscription
def subscribe_events(
    api_key: str,
    on_event: Callable[[Dict[str, Any]], None],
    blocking: bool = False,
    host: str = MQTT_HOST,
    port: int = MQTT_PORT,
    timeout: float = 10.0
) -> GoveeEventClient:
    """
    Subscribe to device events with a simple function call.

    Args:
        api_key: Govee API key
        on_event: Callback function to handle events
        blocking: If True, blocks until connection is closed
        host: MQTT broker host
        port: MQTT broker port
        timeout: Connection timeout

    Returns:
        GoveeEventClient instance (call .disconnect() when done)

    Example:
        def handle_event(event):
            print(f"Device updated: {event}")

        # Non-blocking (runs in background)
        client = subscribe_events(api_key="xxx", on_event=handle_event)
        # Do other work...
        client.disconnect()

        # Blocking (runs forever until Ctrl+C)
        subscribe_events(api_key="xxx", on_event=handle_event, blocking=True)
    """
    client = GoveeEventClient(api_key=api_key, host=host, port=port)
    client.connect(on_event=on_event, blocking=blocking, timeout=timeout)
    return client
