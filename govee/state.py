"""
State management for Govee devices.

Provides functionality to save and restore device states (power, brightness, color, etc.)
for use in scenarios like light shows where you want to restore the original state afterwards.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from govee.models import Device, Collection, RGBColor

logger = logging.getLogger(__name__)


@dataclass
class DeviceState:
    """
    Represents the saved state of a Govee device.

    Attributes:
        device: The device this state belongs to
        power: Power state (True=on, False=off, None=unknown)
        brightness: Brightness percentage (1-100, None=unknown)
        color: RGB color tuple (None=unknown)
        color_temperature: Color temperature in Kelvin (None=unknown)
        scene: Scene information (None=unknown)
        music_mode: Music mode information (None=unknown)
        raw_capabilities: Raw capabilities data from API
    """
    device: Device
    power: Optional[bool] = None
    brightness: Optional[int] = None
    color: Optional[RGBColor] = None
    color_temperature: Optional[int] = None
    scene: Optional[Dict[str, Any]] = None
    music_mode: Optional[Dict[str, Any]] = None
    raw_capabilities: List[Dict[str, Any]] = field(default_factory=list)

    def __repr__(self) -> str:
        parts = [f"device='{self.device.name}'"]
        if self.power is not None:
            parts.append(f"power={'ON' if self.power else 'OFF'}")
        if self.brightness is not None:
            parts.append(f"brightness={self.brightness}%")
        if self.color is not None:
            parts.append(f"color={self.color}")
        return f"DeviceState({', '.join(parts)})"


class StateManager:
    """
    Manages saving and restoring device states.

    This allows you to capture the current state of devices before a light show,
    then restore them afterwards.

    Example:
        state_manager = StateManager(client)

        # Save state before light show
        state_manager.save_state([device1, device2])

        # Run light show (devices get changed)
        client.power(device1, True)
        client.set_color(device1, Colors.RED)

        # Restore original state after light show
        state_manager.restore_state([device1, device2])
    """

    def __init__(self, client):
        """
        Initialize state manager.

        Args:
            client: GoveeClient instance for reading/writing device state
        """
        self.client = client
        self._saved_states: Dict[str, DeviceState] = {}

    def save_state(
        self,
        devices: Union[Device, List[Device], Collection],
        force_refresh: bool = True
    ) -> Dict[str, DeviceState]:
        """
        Save the current state of one or more devices.

        Args:
            devices: Single device, list of devices, or Collection to save state for
            force_refresh: If True, fetch fresh state from API. If False, state may be stale.

        Returns:
            Dictionary mapping device IDs to their saved states

        Example:
            # Save single device
            state_manager.save_state(garage_light)

            # Save multiple devices
            state_manager.save_state([device1, device2, device3])

            # Save a collection
            state_manager.save_state(all_lights)
        """
        # Normalize input to list
        if isinstance(devices, Device):
            device_list = [devices]
        elif isinstance(devices, Collection):
            device_list = devices.devices
        else:
            device_list = devices

        logger.info(f"Saving state for {len(device_list)} device(s) (parallel)")

        saved_states = {}

        def save_worker(device: Device) -> Tuple[str, DeviceState]:
            """Worker function to save state for a single device."""
            try:
                state = self._get_device_state(device, force_refresh)
                logger.debug(f"Saved state for {device.name}: {state}")
                return (device.id, state)
            except Exception as e:
                logger.error(f"Failed to save state for {device.name}: {e}")
                # Return empty state so we don't try to restore it later
                empty_state = DeviceState(device=device)
                return (device.id, empty_state)

        # Use ThreadPoolExecutor for concurrent API calls
        max_workers = min(len(device_list), 20)  # Max 20 concurrent requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(save_worker, device) for device in device_list]
            for future in as_completed(futures):
                device_id, state = future.result()
                self._saved_states[device_id] = state
                saved_states[device_id] = state

        logger.info(f"Successfully saved state for {len(saved_states)} device(s)")
        return saved_states

    def restore_state(
        self,
        devices: Optional[Union[Device, List[Device], Collection]] = None,
        skip_on_error: bool = True
    ) -> Dict[str, bool]:
        """
        Restore previously saved state for one or more devices.

        Args:
            devices: Devices to restore. If None, restores all previously saved devices.
            skip_on_error: If True, continue restoring other devices on error. If False, raise.

        Returns:
            Dictionary mapping device IDs to success status (True=restored, False=failed)

        Example:
            # Restore specific devices
            state_manager.restore_state([device1, device2])

            # Restore all previously saved devices
            state_manager.restore_state()
        """
        # Determine which devices to restore
        if devices is None:
            # Restore all saved devices
            device_list = [state.device for state in self._saved_states.values()]
            logger.info(f"Restoring state for all {len(device_list)} saved device(s)")
        else:
            # Normalize input to list
            if isinstance(devices, Device):
                device_list = [devices]
            elif isinstance(devices, Collection):
                device_list = devices.devices
            else:
                device_list = devices
            logger.info(f"Restoring state for {len(device_list)} device(s) (parallel)")

        results = {}

        def restore_worker(device: Device) -> Tuple[str, bool]:
            """Worker function to restore state for a single device."""
            # Check if we have saved state for this device
            if device.id not in self._saved_states:
                logger.warning(f"No saved state for {device.name}, skipping")
                return (device.id, False)

            state = self._saved_states[device.id]

            try:
                success = self._restore_device_state(device, state)

                if success:
                    logger.info(f"Restored state for {device.name}")
                else:
                    logger.warning(f"Partially restored state for {device.name}")

                return (device.id, success)

            except Exception as e:
                logger.error(f"Failed to restore state for {device.name}: {e}")
                if not skip_on_error:
                    raise
                return (device.id, False)

        # Use ThreadPoolExecutor for concurrent restoration
        # Each device's restoration is still sequential (power→color→brightness)
        # but multiple devices are restored in parallel
        max_workers = min(len(device_list), 20)  # Max 20 concurrent restorations
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(restore_worker, device) for device in device_list]
            for future in as_completed(futures):
                device_id, success = future.result()
                results[device_id] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Restored state for {success_count}/{len(results)} device(s)")
        return results

    def clear_saved_state(
        self,
        devices: Optional[Union[Device, List[Device], Collection]] = None
    ) -> None:
        """
        Clear saved state for devices.

        Args:
            devices: Devices to clear state for. If None, clears all saved states.
        """
        if devices is None:
            count = len(self._saved_states)
            self._saved_states.clear()
            logger.info(f"Cleared all {count} saved device state(s)")
        else:
            # Normalize input to list
            if isinstance(devices, Device):
                device_list = [devices]
            elif isinstance(devices, Collection):
                device_list = devices.devices
            else:
                device_list = devices

            for device in device_list:
                if device.id in self._saved_states:
                    del self._saved_states[device.id]
                    logger.debug(f"Cleared saved state for {device.name}")

            logger.info(f"Cleared saved state for {len(device_list)} device(s)")

    def get_saved_state(self, device: Device) -> Optional[DeviceState]:
        """
        Get the saved state for a device (without restoring it).

        Args:
            device: Device to get saved state for

        Returns:
            DeviceState if found, None otherwise
        """
        return self._saved_states.get(device.id)

    def has_saved_state(self, device: Device) -> bool:
        """
        Check if we have saved state for a device.

        Args:
            device: Device to check

        Returns:
            True if we have saved state, False otherwise
        """
        return device.id in self._saved_states

    # ========== Internal Methods ==========

    def _get_device_state(self, device: Device, force_refresh: bool) -> DeviceState:
        """
        Get current state of a device from the API.

        Tries LAN first (if device has IP), falls back to Cloud API.

        Args:
            device: Device to query
            force_refresh: Whether to force a fresh API call

        Returns:
            DeviceState object with current device state
        """
        # Try LAN first if device supports it
        if self.client.prefer_lan and device.supports_lan:
            try:
                from govee.api.lan import status as lan_status
                logger.debug(f"Trying LAN status query for {device.name}")

                lan_state = lan_status.get_device_status(
                    device_ip=device.ip,
                    send_port=self.client.lan_port,
                    timeout=min(self.client.timeout, 2.0)  # Shorter timeout for LAN
                )

                if lan_state is not None:
                    logger.info(f"LAN status query successful for {device.name}")
                    return self._parse_lan_state(device, lan_state)
                else:
                    logger.warning(f"LAN status query returned no data for {device.name}, falling back to Cloud")

            except Exception as e:
                logger.warning(f"LAN status query failed for {device.name}, falling back to Cloud: {e}")

        # Fallback to Cloud API
        from govee.api.cloud import device_state

        logger.debug(f"Using Cloud API for {device.name} state")
        state_data = device_state.get_device_state(
            api_key=self.client.api_key,
            device_id=device.id,
            sku=device.sku,
            base_url=self.client.base_url,
            timeout=self.client.timeout
        )

        capabilities = state_data.get("capabilities", [])

        # Parse capabilities into structured state
        device_state_obj = DeviceState(device=device, raw_capabilities=capabilities)

        logger.info(f"Parsing state for {device.name} from {len(capabilities)} capabilities")

        # Debug: Print all capability instances to see what's available
        instances = [cap.get("instance", "UNKNOWN") for cap in capabilities]
        logger.info(f"Available capability instances for {device.name}: {instances}")

        for cap in capabilities:
            cap_type = cap.get("type", "")
            instance = cap.get("instance", "")
            state_value = cap.get("state", {})

            # Power state
            if instance == "powerSwitch":
                value = state_value.get("value")
                if value is not None:
                    device_state_obj.power = bool(value)

            # Brightness
            elif instance == "brightness":
                value = state_value.get("value")
                if value is not None:
                    device_state_obj.brightness = int(value)

            # Color (RGB)
            elif instance == "colorRgb":
                value = state_value.get("value")
                if value is not None:
                    # Handle both dict format {"r": X, "g": Y, "b": Z} and integer format
                    if isinstance(value, dict):
                        r = value.get("r", 0)
                        g = value.get("g", 0)
                        b = value.get("b", 0)
                        device_state_obj.color = (r, g, b)
                        logger.info(f"Captured color for {device.name}: RGB({r}, {g}, {b}) [dict format]")
                    elif isinstance(value, int):
                        # Packed RGB integer: 0xRRGGBB
                        r = (value >> 16) & 0xFF
                        g = (value >> 8) & 0xFF
                        b = value & 0xFF
                        device_state_obj.color = (r, g, b)
                        logger.info(f"Captured color for {device.name}: RGB({r}, {g}, {b}) [integer format: {value}]")

            # Color Temperature
            elif instance == "colorTemperatureK":
                value = state_value.get("value")
                if value is not None:
                    device_state_obj.color_temperature = int(value)

            # Scene
            elif instance in ["lightScene", "dynamicScene"]:
                device_state_obj.scene = state_value

            # Music Mode
            elif instance == "musicMode":
                device_state_obj.music_mode = state_value

        return device_state_obj

    def _parse_lan_state(self, device: Device, lan_state: Dict[str, Any]) -> DeviceState:
        """
        Parse LAN API state response into DeviceState.

        LAN API returns:
        {
            "onOff": 1,  # 1=on, 0=off
            "brightness": 100,  # 1-100
            "color": {"r": 255, "g": 0, "b": 0},
            "colorTemInKelvin": 7200  # 2000-9000
        }

        Args:
            device: Device this state belongs to
            lan_state: State dict from LAN API

        Returns:
            DeviceState object
        """
        device_state_obj = DeviceState(device=device)

        # Power state
        if "onOff" in lan_state:
            device_state_obj.power = bool(lan_state["onOff"])
            logger.debug(f"LAN power state for {device.name}: {device_state_obj.power}")

        # Brightness
        if "brightness" in lan_state:
            device_state_obj.brightness = int(lan_state["brightness"])
            logger.debug(f"LAN brightness for {device.name}: {device_state_obj.brightness}%")

        # Color (RGB) - LAN returns dict format
        if "color" in lan_state and isinstance(lan_state["color"], dict):
            r = lan_state["color"].get("r", 0)
            g = lan_state["color"].get("g", 0)
            b = lan_state["color"].get("b", 0)
            device_state_obj.color = (r, g, b)
            logger.info(f"Captured color for {device.name}: RGB({r}, {g}, {b}) [LAN API]")

        # Color Temperature
        if "colorTemInKelvin" in lan_state:
            device_state_obj.color_temperature = int(lan_state["colorTemInKelvin"])
            logger.debug(f"LAN color temp for {device.name}: {device_state_obj.color_temperature}K")

        return device_state_obj

    def _restore_device_state(self, device: Device, state: DeviceState) -> bool:
        """
        Restore a device to a saved state.

        Args:
            device: Device to restore
            state: Saved state to restore to

        Returns:
            True if fully successful, False if any operation failed
        """
        import time
        success = True

        logger.info(f"Restoring {device.name}: power={state.power}, brightness={state.brightness}, color={state.color}")

        # Restore in order: power on/off, then other properties

        # 1. If device should be off, turn it off and skip other settings
        if state.power is False:
            try:
                self.client.power(device, False, verify=False)  # Fast, no verification
                logger.debug(f"Restored power=OFF for {device.name}")
            except Exception as e:
                logger.error(f"Failed to restore power for {device.name}: {e}")
                success = False
            # When restoring to OFF state, skip other settings
            return success

        # 2. If device should be on, turn it on first
        if state.power is True:
            try:
                self.client.power(device, True, verify=False)  # Fast, no verification
                logger.debug(f"Restored power=ON for {device.name}")
                # Small delay to let device power on and be ready for commands
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to restore power for {device.name}: {e}")
                success = False

        # 3. Restore color FIRST (this will implicitly disable music mode if it was active)
        # Must be done before brightness to ensure color takes effect
        if state.color is not None and device.supports_color:
            try:
                self.client.set_color(device, state.color)
                logger.debug(f"Restored color={state.color} for {device.name}")
                # Small delay after color change
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Failed to restore color for {device.name}: {e}")
                success = False

        # 4. Restore color temperature (if we have it and no color was set)
        elif state.color_temperature is not None and state.color_temperature > 0:
            try:
                self.client.set_color_temperature(device, state.color_temperature)
                logger.debug(f"Restored color_temperature={state.color_temperature}K for {device.name}")
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Failed to restore color temperature for {device.name}: {e}")
                success = False

        # 5. Restore brightness AFTER color (so brightness applies to the restored color)
        if state.brightness is not None and device.supports_brightness:
            try:
                self.client.set_brightness(device, state.brightness)
                logger.debug(f"Restored brightness={state.brightness}% for {device.name}")
            except Exception as e:
                logger.error(f"Failed to restore brightness for {device.name}: {e}")
                success = False

        # Note: We don't restore scenes or music modes because:
        # 1. They may have been applied temporarily and user may not want them back
        # 2. Setting color/brightness is more predictable for light show restoration
        # 3. API limitations may prevent setting exact scene state
        # 4. Setting color explicitly will disable any active music mode

        return success
