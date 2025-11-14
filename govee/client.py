"""
Main GoveeClient class for controlling Govee devices.

This client automatically tries LAN control first (if available),
then falls back to Cloud API if LAN fails or is not supported.
"""
import logging
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from govee.models import Device, Scene, DIYScene, MusicMode, Collection, RGBColor, Colors
from govee.exceptions import (
    GoveeError,
    GoveeDeviceNotFoundError,
    GoveeSceneNotFoundError,
    GoveeInvalidParameterError,
)
from govee.api.cloud import devices as cloud_devices
from govee.api.cloud import device_control as cloud_control
from govee.api.cloud import device_diy_scenes as cloud_diy_scenes
from govee.api.cloud import device_scenes as cloud_builtin_scenes
from govee.api.cloud import device_music_modes as cloud_music_modes
from govee.api.lan import power as lan_power
from govee.api.lan import brightness as lan_brightness
from govee.api.lan import color as lan_color

logger = logging.getLogger(__name__)


class GoveeClient:
    """
    Main client for controlling Govee smart devices.

    Supports both LAN (UDP) and Cloud API control with automatic fallback.

    Example:
        client = GoveeClient(api_key="your-api-key", prefer_lan=True)
        devices = client.discover_devices()

        garage_light = client.get_device("Garage Left")
        client.power(garage_light, on=True)
        client.set_brightness(garage_light, 75)
        client.set_color(garage_light, Colors.RED)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openapi.api.govee.com/router/api/v1",
        prefer_lan: bool = True,
        lan_port: int = 4003,
        timeout: float = 10.0,
        max_workers: int = 10,
        log_level: str = "INFO",
    ):
        """
        Initialize Govee client.

        Args:
            api_key: Govee API key (required for Cloud API)
            base_url: Base URL for Govee Cloud API
            prefer_lan: Try LAN control first before falling back to Cloud
            lan_port: UDP port for LAN control (default: 4003)
            timeout: Request timeout in seconds
            max_workers: Max concurrent workers for batch operations
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.prefer_lan = prefer_lan
        self.lan_port = lan_port
        self.timeout = timeout
        self.max_workers = max_workers

        # Device storage
        self._devices: List[Device] = []
        self._scenes: List[Scene] = []
        self._music_modes: List[MusicMode] = []
        self._collections: Dict[str, Collection] = {}

        # Configure logging
        log_level_num = getattr(logging, log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level_num,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logger.setLevel(log_level_num)

    # ========== Device Discovery & Management ==========

    def discover_devices(self, filter_names: Optional[List[str]] = None) -> List[Device]:
        """
        Discover devices from Govee Cloud API.

        Args:
            filter_names: Optional list of device names to filter by.
                         If empty or None, fetches ALL devices.

        Returns:
            List of discovered devices
        """
        logger.info("Discovering devices from Govee Cloud API...")

        # Fetch from Cloud API
        response = cloud_devices.get_devices(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        # Handle both old and new API response formats
        if "data" in response:
            # New API format: data is a list of devices directly
            devices_data = response.get("data", [])
        else:
            # Old API format: data is in payload.devices
            devices_data = response.get("payload", {}).get("devices", [])

        # Create a mapping of existing devices by ID to preserve user-set properties
        existing_devices = {device.id: device for device in self._devices}

        devices = []
        for dev_data in devices_data:
            device_name = dev_data.get("deviceName", "")

            # Apply name filter if specified
            if filter_names and device_name not in filter_names:
                continue

            # Extract capabilities
            capabilities = []
            for cap in dev_data.get("capabilities", []):
                cap_type = cap.get("type", "")
                if cap_type.startswith("devices.capabilities."):
                    cap_name = cap_type.replace("devices.capabilities.", "")
                    capabilities.append(cap_name)

            device_id = dev_data.get("device")

            # Check if device already exists to preserve user-set properties
            existing_device = existing_devices.get(device_id)

            device = Device(
                id=device_id,
                name=device_name,
                sku=dev_data.get("sku"),
                # Preserve IP if device already exists, otherwise use default (None)
                ip=existing_device.ip if existing_device else None,
                capabilities=capabilities,
                metadata={
                    "type": dev_data.get("type"),
                    "retrievable": dev_data.get("retrievable")
                }
            )
            devices.append(device)

        self._devices = devices
        logger.info(f"Discovered {len(devices)} devices")
        return devices

    def load_devices(self, file_path: Union[str, Path]) -> None:
        """
        Load devices from Python module or JSON file.

        Tries to load from Python modules first (govee_devices.py, govee_scenes.py,
        govee_diy_scenes.py, govee_music_modes.py), then falls back to JSON if Python
        modules don't exist.

        Args:
            file_path: Path to Python module (.py), JSON file (.json), or directory containing modules
        """
        file_path = Path(file_path)

        # Determine paths for Python modules
        if file_path.suffix == '.py':
            # If it's a .py file, assume it's govee_devices.py
            devices_module_path = file_path
            module_dir = file_path.parent
        elif file_path.is_dir():
            # If it's a directory, look for modules inside
            module_dir = file_path
            devices_module_path = module_dir / "govee_devices.py"
        else:
            # If it's a JSON file or other, check the parent directory for modules
            module_dir = file_path.parent
            devices_module_path = module_dir / "govee_devices.py"

        scenes_module_path = module_dir / "govee_scenes.py"
        diy_scenes_module_path = module_dir / "govee_diy_scenes.py"
        music_modes_module_path = module_dir / "govee_music_modes.py"

        # Try loading from Python modules first
        if devices_module_path.exists():
            try:
                logger.info(f"Loading devices from Python module: {devices_module_path}")
                import importlib.util

                # Load devices module
                spec = importlib.util.spec_from_file_location("govee_devices", str(devices_module_path))
                if spec and spec.loader:
                    devices_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(devices_module)

                    # Load Device objects from module
                    self._devices = []
                    for device_name in getattr(devices_module, "__all__", []):
                        device_obj = getattr(devices_module, device_name)
                        if isinstance(device_obj, Device):
                            self._devices.append(device_obj)

                # Load built-in scenes module (if exists)
                self._scenes = []
                if scenes_module_path.exists():
                    logger.info(f"Loading scenes from Python module: {scenes_module_path}")
                    spec = importlib.util.spec_from_file_location("govee_scenes", str(scenes_module_path))
                    if spec and spec.loader:
                        scenes_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(scenes_module)

                        for scene_name in getattr(scenes_module, "__all__", []):
                            scene_obj = getattr(scenes_module, scene_name)
                            if isinstance(scene_obj, Scene):
                                self._scenes.append(scene_obj)

                # Load DIY scenes module (if exists)
                # Note: DIY scenes are stored separately from built-in scenes in Python modules,
                # but GoveeClient internally treats them all as Scene objects (with id stored in metadata)
                if diy_scenes_module_path.exists():
                    logger.info(f"Loading DIY scenes from Python module: {diy_scenes_module_path}")
                    spec = importlib.util.spec_from_file_location("govee_diy_scenes", str(diy_scenes_module_path))
                    if spec and spec.loader:
                        diy_scenes_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(diy_scenes_module)

                        for diy_scene_name in getattr(diy_scenes_module, "__all__", []):
                            diy_scene_obj = getattr(diy_scenes_module, diy_scene_name)
                            # DIYScene objects are kept as-is for now
                            # TODO: Consider unifying Scene/DIYScene representation in GoveeClient
                            if isinstance(diy_scene_obj, DIYScene):
                                self._scenes.append(diy_scene_obj)

                # Load music modes module (if exists)
                self._music_modes = []
                if music_modes_module_path.exists():
                    logger.info(f"Loading music modes from Python module: {music_modes_module_path}")
                    spec = importlib.util.spec_from_file_location("govee_music_modes", str(music_modes_module_path))
                    if spec and spec.loader:
                        music_modes_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(music_modes_module)

                        for mode_name in getattr(music_modes_module, "__all__", []):
                            mode_obj = getattr(music_modes_module, mode_name)
                            if isinstance(mode_obj, MusicMode):
                                self._music_modes.append(mode_obj)

                # Collections are not stored in Python modules yet, so initialize empty
                self._collections = {}

                logger.info(f"Loaded {len(self._devices)} devices, {len(self._scenes)} scenes, {len(self._music_modes)} music modes from Python modules")
                return

            except Exception as e:
                logger.warning(f"Failed to load from Python modules: {e}")
                logger.info("Falling back to JSON file...")

        # Fallback to JSON loading
        json_path = file_path if file_path.suffix == '.json' else module_dir / "govee_devices.json"

        if not json_path.exists():
            raise FileNotFoundError(f"Neither Python modules nor JSON file found at {module_dir}")

        logger.info(f"Loading devices from JSON: {json_path}")

        with open(json_path, "r") as f:
            data = json.load(f)

        # Load devices
        self._devices = [Device.from_dict(d) for d in data.get("devices", [])]

        # Load scenes
        self._scenes = [Scene.from_dict(s) for s in data.get("scenes", [])]

        # Load collections
        collections_data = data.get("collections", {})
        self._collections = {}
        for coll_name, device_names in collections_data.items():
            collection_devices = []
            for dev_name in device_names:
                device = self.get_device(name=dev_name, raise_error=False)
                if device:
                    collection_devices.append(device)
            self._collections[coll_name] = Collection(name=coll_name, devices=collection_devices)

        logger.info(f"Loaded {len(self._devices)} devices, {len(self._scenes)} scenes, {len(self._collections)} collections from JSON")

    def save_devices(self, file_path: Union[str, Path]) -> None:
        """
        Save devices to JSON file.

        Args:
            file_path: Path to save JSON file
        """
        file_path = Path(file_path)
        logger.info(f"Saving devices to {file_path}")

        # Prepare collections data (device names only)
        collections_data = {}
        for coll_name, collection in self._collections.items():
            collections_data[coll_name] = [d.name for d in collection.devices]

        data = {
            "devices": [d.to_dict() for d in self._devices],
            "scenes": [s.to_dict() for s in self._scenes],
            "collections": collections_data,
            "metadata": {
                "version": "1.0.0"
            }
        }

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self._devices)} devices to {file_path}")

    def export_as_modules(self, directory: Union[str, Path] = ".") -> None:
        """
        Export devices, scenes, DIY scenes, and music modes as Python modules.

        Creates up to four Python files in the specified directory:
        - govee_devices.py: Device objects
        - govee_scenes.py: Built-in scene objects
        - govee_diy_scenes.py: DIY scene objects
        - govee_music_modes.py: Music mode objects

        These can be imported and used in your code with type hints and IDE autocomplete.

        Args:
            directory: Directory to save modules to (default: current directory)

        Example:
            ```python
            client = GoveeClient(api_key="...")
            devices = client.discover_devices()

            # Export to Python modules
            client.export_as_modules("./")

            # Now you can import and use:
            from govee_devices import ground2_machine
            from govee_scenes import sunset
            from govee_music_modes import energic_h6008
            client.apply_scene(ground2_machine, sunset)
            ```
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting devices, scenes, and music modes as Python modules to {directory}")

        # Export devices
        self._export_devices_module(directory / "govee_devices.py")

        # Export built-in scenes (filter out DIY scenes)
        built_in_scenes = [s for s in self._scenes if not isinstance(s, DIYScene)]
        if built_in_scenes:
            self._export_scenes_module(directory / "govee_scenes.py", built_in_scenes)

        # Export DIY scenes
        diy_scenes = [s for s in self._scenes if isinstance(s, DIYScene)]
        if diy_scenes:
            self._export_diy_scenes_module(directory / "govee_diy_scenes.py", diy_scenes)

        # Export music modes
        music_modes = [m for m in self._music_modes if isinstance(m, MusicMode)]
        if music_modes:
            self._export_music_modes_module(directory / "govee_music_modes.py", music_modes)

        logger.info(f"Exported {len(self._devices)} devices, {len(built_in_scenes)} scenes, {len(diy_scenes)} DIY scenes, {len(music_modes)} music modes")

    def _export_devices_module(self, file_path: Path) -> None:
        """Generate govee_devices.py module."""
        lines = [
            '"""',
            'Govee devices exported from your account.',
            'Generated by govee-python-sdk.',
            '',
            'Import devices directly:',
            '    from govee_devices import ground2_machine',
            '"""',
            'from govee.models import Device',
            '',
            ''
        ]

        # Generate variable names and __all__ list
        var_names = []
        for device in self._devices:
            # Create Python-safe variable name
            var_name = self._to_snake_case(device.name)
            var_names.append(var_name)

            # Create Device object
            lines.append(f'{var_name} = Device(')
            lines.append(f'    id="{device.id}",')
            lines.append(f'    name="{device.name}",')
            lines.append(f'    sku="{device.sku}",')
            ip_value = "None" if not device.ip else f'"{device.ip}"'
            lines.append(f'    ip={ip_value},')
            lines.append(f'    capabilities={repr(device.capabilities)},')
            lines.append(f'    metadata={repr(device.metadata)}')
            lines.append(')')
            lines.append('')

        # Add __all__
        lines.append('__all__ = [')
        for var_name in var_names:
            lines.append(f'    "{var_name}",')
        lines.append(']')

        file_path.write_text('\n'.join(lines))
        logger.info(f"Wrote {len(self._devices)} devices to {file_path}")

    def _export_scenes_module(self, file_path: Path, scenes: List[Scene]) -> None:
        """Generate govee_scenes.py module."""
        lines = [
            '"""',
            'Govee built-in scenes exported from your account.',
            'Generated by govee-python-sdk.',
            '',
            'Import scenes directly:',
            '    from govee_scenes import sunset',
            '"""',
            'from govee.models import Scene',
            '',
            ''
        ]

        # Generate variable names and __all__ list
        var_names = []
        for scene in scenes:
            # Include SKU suffix to avoid duplicates across different device types
            base_name = self._to_snake_case(scene.name)
            var_name = f"{base_name}_{scene.sku.lower()}" if scene.sku else base_name
            var_names.append(var_name)

            # Normalize scene.value dictionary to ensure consistent key ordering
            # Always output as {'id': X, 'paramId': Y} for consistency
            if isinstance(scene.value, dict):
                normalized_value = {
                    'id': scene.value.get('id'),
                    'paramId': scene.value.get('paramId')
                }
                value_str = repr(normalized_value)
            else:
                value_str = repr(scene.value)

            lines.append(f'{var_name} = Scene(')
            lines.append(f'    name="{scene.name}",')
            lines.append(f'    value={value_str},')
            sku_value = "None" if not scene.sku else f'"{scene.sku}"'
            lines.append(f'    sku={sku_value},')
            lines.append(f'    metadata={repr(scene.metadata)}')
            lines.append(')')
            lines.append('')

        # Add __all__
        lines.append('__all__ = [')
        for var_name in var_names:
            lines.append(f'    "{var_name}",')
        lines.append(']')

        file_path.write_text('\n'.join(lines))
        logger.info(f"Wrote {len(scenes)} scenes to {file_path}")

    def _export_diy_scenes_module(self, file_path: Path, diy_scenes: List[DIYScene]) -> None:
        """Generate govee_diy_scenes.py module."""
        lines = [
            '"""',
            'Govee DIY scenes (custom user-created) exported from your account.',
            'Generated by govee-python-sdk.',
            '',
            'Import DIY scenes directly:',
            '    from govee_diy_scenes import my_custom_scene',
            '"""',
            'from govee.models import DIYScene',
            '',
            ''
        ]

        # Generate variable names and __all__ list
        var_names = []
        for scene in diy_scenes:
            # Include SKU suffix to avoid duplicates across different device types
            base_name = self._to_snake_case(scene.name)
            var_name = f"{base_name}_{scene.sku.lower()}" if scene.sku else base_name
            var_names.append(var_name)

            lines.append(f'{var_name} = DIYScene(')
            lines.append(f'    id={scene.id},')
            lines.append(f'    name="{scene.name}",')
            sku_value = "None" if not scene.sku else f'"{scene.sku}"'
            lines.append(f'    sku={sku_value},')
            lines.append(f'    metadata={repr(scene.metadata)}')
            lines.append(')')
            lines.append('')

        # Add __all__
        lines.append('__all__ = [')
        for var_name in var_names:
            lines.append(f'    "{var_name}",')
        lines.append(']')

        file_path.write_text('\n'.join(lines))
        logger.info(f"Wrote {len(diy_scenes)} DIY scenes to {file_path}")

    def _export_music_modes_module(self, file_path: Path, music_modes: List[MusicMode]) -> None:
        """Generate govee_music_modes.py module."""
        lines = [
            '"""',
            'Govee music modes exported from your devices.',
            'Generated by govee-python-sdk.',
            '',
            'Import music modes directly:',
            '    from govee_music_modes import energic_h6008',
            '"""',
            'from govee.models import MusicMode',
            '',
            ''
        ]

        # Generate variable names and __all__ list
        var_names = []
        for mode in music_modes:
            # Include SKU suffix to differentiate modes with same name but different values
            base_name = self._to_snake_case(mode.name)
            var_name = f"{base_name}_{mode.sku.lower()}" if mode.sku else base_name
            var_names.append(var_name)

            lines.append(f'{var_name} = MusicMode(')
            lines.append(f'    name="{mode.name}",')
            lines.append(f'    value={mode.value},')
            sku_value = "None" if not mode.sku else f'"{mode.sku}"'
            lines.append(f'    sku={sku_value},')
            lines.append(f'    metadata={repr(mode.metadata)}')
            lines.append(')')
            lines.append('')

        # Add __all__
        lines.append('__all__ = [')
        for var_name in var_names:
            lines.append(f'    "{var_name}",')
        lines.append(']')

        file_path.write_text('\n'.join(lines))
        logger.info(f"Wrote {len(music_modes)} music modes to {file_path}")

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert device/scene name to snake_case variable name."""
        import re
        # Replace special characters with underscores
        name = re.sub(r'[^\w\s-]', '', name)
        # Replace whitespace and hyphens with underscores
        name = re.sub(r'[-\s]+', '_', name)
        # Convert to lowercase
        name = name.lower()
        # Remove leading/trailing underscores
        name = name.strip('_')
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = f'device_{name}'
        return name or 'unnamed_device'

    def get_device(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        raise_error: bool = True
    ) -> Optional[Device]:
        """
        Get device by name or ID.

        Args:
            name: Device name (case-insensitive)
            id: Device ID
            raise_error: Raise error if not found (default: True)

        Returns:
            Device object or None if not found

        Raises:
            GoveeDeviceNotFoundError: If device not found and raise_error=True
        """
        if not name and not id:
            raise GoveeInvalidParameterError("Must provide either name or id")

        for device in self._devices:
            if name and device.name.lower() == name.lower():
                return device
            if id and device.id == id:
                return device

        if raise_error:
            identifier = name or id
            raise GoveeDeviceNotFoundError(identifier)

        return None

    def get_all_devices(self, lights_only: bool = False) -> List[Device]:
        """
        Get all devices.

        Args:
            lights_only: Only return light devices (exclude plugs, etc.)

        Returns:
            List of devices
        """
        if lights_only:
            return [d for d in self._devices if d.is_light]
        return self._devices.copy()

    def get_collection(self, name: str) -> Collection:
        """
        Get a device collection by name.

        Args:
            name: Collection name

        Returns:
            Collection object

        Raises:
            GoveeError: If collection not found
        """
        if name not in self._collections:
            raise GoveeError(f"Collection not found: {name}")
        return self._collections[name]

    def create_collection(self, name: str, devices: List[Device]) -> Collection:
        """
        Create a new device collection.

        Args:
            name: Collection name
            devices: List of devices

        Returns:
            Created collection
        """
        collection = Collection(name=name, devices=devices)
        self._collections[name] = collection
        return collection

    # ========== Scene Management ==========

    def discover_diy_scenes(
        self,
        devices: Optional[List[Device]] = None,
        prefix_filter: Optional[str] = None
    ) -> List[DIYScene]:
        """
        Discover DIY scenes for devices.

        Args:
            devices: List of devices to fetch scenes for (default: all devices)
            prefix_filter: Only include scenes with this prefix (e.g., "SC_")

        Returns:
            List of discovered DIY scenes
        """
        if devices is None:
            devices = self._devices

        logger.info(f"Discovering DIY scenes for {len(devices)} devices...")

        diy_scenes = []
        seen = set()  # Avoid duplicates

        for device in devices:
            try:
                device_scenes = cloud_diy_scenes.get_diy_scenes(
                    api_key=self.api_key,
                    device_id=device.id,
                    sku=device.sku,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    device_name=device.name
                )

                for scene_data in device_scenes:
                    scene_name = scene_data.get("name", "")

                    # Apply prefix filter
                    if prefix_filter and not scene_name.startswith(prefix_filter):
                        continue

                    scene_id = scene_data.get("id")
                    # Use scene ID + SKU as deduplication key (scene IDs should be unique per SKU)
                    scene_key = (scene_id, device.sku)

                    if scene_key in seen:
                        continue

                    seen.add(scene_key)
                    scene = DIYScene(
                        id=scene_id,
                        name=scene_name,
                        sku=device.sku
                    )
                    diy_scenes.append(scene)

            except Exception as e:
                logger.warning(f"Failed to fetch DIY scenes for {device.name}: {e}")
                continue

        # Add to _scenes list (keeping existing scenes)
        self._scenes.extend(diy_scenes)
        logger.info(f"Discovered {len(diy_scenes)} DIY scenes")
        return diy_scenes

    def discover_builtin_scenes(
        self,
        devices: Optional[List[Device]] = None
    ) -> List[Scene]:
        """
        Discover built-in scenes for devices.

        Built-in scenes are Govee's default scenes (like "Sunrise", "Sunset", "Aurora")
        that users can apply but cannot modify.

        Args:
            devices: List of devices to fetch scenes for (default: all devices)

        Returns:
            List of discovered built-in scenes
        """
        if devices is None:
            devices = self._devices

        logger.info(f"Discovering built-in scenes for {len(devices)} devices...")

        builtin_scenes = []
        seen = set()  # Avoid duplicates

        for device in devices:
            try:
                device_scenes = cloud_builtin_scenes.get_scenes(
                    api_key=self.api_key,
                    device_id=device.id,
                    sku=device.sku,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    device_name=device.name
                )

                for scene_data in device_scenes:
                    scene_name = scene_data.get("name", "")
                    scene_value = scene_data.get("value", {})
                    # Use scene ID + SKU as deduplication key (scene IDs should be unique per SKU)
                    scene_id = scene_value.get("id")
                    scene_key = (scene_id, device.sku)

                    if scene_key in seen:
                        continue

                    seen.add(scene_key)
                    scene = Scene(
                        name=scene_name,
                        value=scene_value,
                        sku=device.sku
                    )
                    builtin_scenes.append(scene)

            except Exception as e:
                logger.warning(f"Failed to fetch built-in scenes for {device.name}: {e}")
                continue

        # Add to _scenes list (keeping existing scenes)
        self._scenes.extend(builtin_scenes)
        logger.info(f"Discovered {len(builtin_scenes)} built-in scenes")
        return builtin_scenes

    def get_scene(
        self,
        name: str,
        device: Device,
        raise_error: bool = True
    ) -> Optional[Scene]:
        """
        Get scene by name for a specific device SKU.

        Args:
            name: Scene name
            device: Device to get scene for (uses device SKU)
            raise_error: Raise error if not found

        Returns:
            Scene object or None

        Raises:
            GoveeSceneNotFoundError: If scene not found and raise_error=True
        """
        # Try exact match first
        for scene in self._scenes:
            if scene.name == name and scene.sku == device.sku:
                return scene

        # Try case-insensitive match
        name_lower = name.lower()
        for scene in self._scenes:
            if scene.name.lower() == name_lower and scene.sku == device.sku:
                return scene

        if raise_error:
            raise GoveeSceneNotFoundError(name, device.sku)

        return None

    def get_scenes(self, device: Device) -> List[Scene]:
        """
        Get all built-in (non-DIY) scenes for a specific device.

        Args:
            device: Device to get scenes for

        Returns:
            List of Scene objects (excluding DIY scenes)
        """
        # Filter scenes for this device's SKU and exclude DIY scenes
        return [
            scene for scene in self._scenes
            if scene.sku == device.sku and not isinstance(scene, DIYScene)
        ]

    def get_diy_scenes(self, device: Device) -> List[DIYScene]:
        """
        Get all DIY scenes for a specific device.

        Args:
            device: Device to get DIY scenes for

        Returns:
            List of DIYScene objects
        """
        # Filter DIY scenes for this device's SKU
        return [
            scene for scene in self._scenes
            if scene.sku == device.sku and isinstance(scene, DIYScene)
        ]

    def discover_music_modes(
        self,
        devices: Optional[List[Device]] = None
    ) -> List[MusicMode]:
        """
        Discover music modes from device capabilities.

        Music modes are included in device capabilities from the GET /user/devices endpoint.
        This method parses those capabilities to extract available music visualization modes.

        Args:
            devices: List of devices to extract music modes from (default: all devices)

        Returns:
            List of discovered music modes
        """
        if devices is None:
            devices = self._devices

        logger.info(f"Discovering music modes for {len(devices)} devices...")

        # Need to re-fetch devices to get full capability details
        response = cloud_devices.get_devices(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        # Handle both old and new API response formats
        if "data" in response:
            devices_data = response.get("data", [])
        else:
            devices_data = response.get("payload", {}).get("devices", [])

        # Create a map of device ID to device data for quick lookup
        device_data_map = {dev["device"]: dev for dev in devices_data}

        music_modes = []
        seen = set()  # Avoid duplicates: (mode_value, SKU)

        for device in devices:
            # Skip devices that don't support music mode
            if not device.supports_music_mode:
                continue

            try:
                # Get the full device data with capabilities
                device_data = device_data_map.get(device.id)
                if not device_data:
                    logger.warning(f"Device {device.name} not found in API response")
                    continue

                # Parse music modes from capabilities
                device_music_modes = cloud_music_modes.get_music_modes_from_device_data(device_data)

                for mode_data in device_music_modes:
                    mode_name = mode_data.get("name", "")
                    mode_value = mode_data.get("value")
                    mode_metadata = mode_data.get("metadata", {})

                    # Use mode value + SKU as deduplication key
                    # (different devices may have same mode names with different values)
                    mode_key = (mode_value, device.sku)

                    if mode_key in seen:
                        continue

                    seen.add(mode_key)
                    music_mode = MusicMode(
                        name=mode_name,
                        value=mode_value,
                        sku=device.sku,
                        metadata=mode_metadata
                    )
                    music_modes.append(music_mode)

            except Exception as e:
                logger.warning(f"Failed to parse music modes for {device.name}: {e}")
                continue

        # Add to _music_modes list
        self._music_modes.extend(music_modes)
        logger.info(f"Discovered {len(music_modes)} music modes")
        return music_modes

    def get_music_modes(self, device: Device) -> List[MusicMode]:
        """
        Get all music modes for a specific device.

        Args:
            device: Device to get music modes for

        Returns:
            List of MusicMode objects for this device SKU
        """
        return [
            mode for mode in self._music_modes
            if mode.sku == device.sku
        ]

    # ========== Device Control (with LAN-first fallback) ==========

    def power(self, device: Device, on: bool) -> bool:
        """
        Turn device on or off.

        Tries LAN first (if supported), falls back to Cloud API.

        Args:
            device: Device to control
            on: True to turn on, False to turn off

        Returns:
            True if successful
        """
        # Try LAN first if preferred and supported
        if self.prefer_lan and device.supports_lan:
            try:
                logger.debug(f"Trying LAN control for {device.name}")
                lan_power.send_power(
                    device_ip=device.ip,
                    on=on,
                    send_port=self.lan_port,
                    timeout=self.timeout
                )
                logger.info(f"LAN control successful: {device.name} -> {'ON' if on else 'OFF'}")
                return True
            except Exception as e:
                logger.warning(f"LAN control failed for {device.name}, falling back to Cloud: {e}")

        # Fallback to Cloud API
        try:
            logger.debug(f"Using Cloud API for {device.name}")
            cloud_control.power(
                api_key=self.api_key,
                device_id=device.id,
                sku=device.sku,
                on=on,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"Cloud control successful: {device.name} -> {'ON' if on else 'OFF'}")
            return True
        except Exception as e:
            logger.error(f"Cloud control failed for {device.name}: {e}")
            raise

    def set_brightness(self, device: Device, percent: int) -> bool:
        """
        Set device brightness (1-100%).

        Tries LAN first (if supported), falls back to Cloud API.

        Args:
            device: Device to control
            percent: Brightness percentage (1-100)

        Returns:
            True if successful
        """
        percent = max(1, min(100, int(percent)))

        # Try LAN first if preferred and supported
        if self.prefer_lan and device.supports_lan:
            try:
                logger.debug(f"Trying LAN control for {device.name}")
                lan_brightness.send_brightness(
                    device_ip=device.ip,
                    percent=percent,
                    send_port=self.lan_port,
                    timeout=self.timeout
                )
                logger.info(f"LAN control successful: {device.name} brightness -> {percent}%")
                return True
            except Exception as e:
                logger.warning(f"LAN control failed for {device.name}, falling back to Cloud: {e}")

        # Fallback to Cloud API
        try:
            logger.debug(f"Using Cloud API for {device.name}")
            cloud_control.brightness(
                api_key=self.api_key,
                device_id=device.id,
                sku=device.sku,
                percent=percent,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"Cloud control successful: {device.name} brightness -> {percent}%")
            return True
        except Exception as e:
            logger.error(f"Cloud control failed for {device.name}: {e}")
            raise

    def set_color(
        self,
        device: Device,
        rgb: RGBColor,
        color_temp_kelvin: int = 0
    ) -> bool:
        """
        Set device color.

        Tries LAN first (if supported), falls back to Cloud API.

        Args:
            device: Device to control
            rgb: RGB tuple (r, g, b) where each value is 0-255
            color_temp_kelvin: Color temperature in Kelvin (2000-9000), or 0 for RGB mode

        Returns:
            True if successful
        """
        # Try LAN first if preferred and supported
        if self.prefer_lan and device.supports_lan:
            try:
                logger.debug(f"Trying LAN control for {device.name}")
                lan_color.send_color(
                    device_ip=device.ip,
                    rgb=rgb,
                    color_temp_kelvin=color_temp_kelvin,
                    send_port=self.lan_port,
                    timeout=self.timeout
                )
                logger.info(f"LAN control successful: {device.name} color -> {rgb}")
                return True
            except Exception as e:
                logger.warning(f"LAN control failed for {device.name}, falling back to Cloud: {e}")

        # Fallback to Cloud API (Cloud only supports RGB, not color temp)
        try:
            logger.debug(f"Using Cloud API for {device.name}")
            cloud_control.color_rgb(
                api_key=self.api_key,
                device_id=device.id,
                sku=device.sku,
                rgb=rgb,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"Cloud control successful: {device.name} color -> {rgb}")
            return True
        except Exception as e:
            logger.error(f"Cloud control failed for {device.name}: {e}")
            raise

    def set_color_temperature(self, device: Device, kelvin: int) -> bool:
        """
        Set device color temperature in Kelvin.

        Note: Color temperature uses the Cloud API. For devices that support LAN,
        you can use set_color() with color_temp_kelvin parameter instead.

        Args:
            device: Device to control
            kelvin: Color temperature in Kelvin (2000-9000)

        Returns:
            True if successful
        """
        try:
            logger.debug(f"Setting color temperature for {device.name} to {kelvin}K")
            cloud_control.color_temperature_kelvin(
                api_key=self.api_key,
                device_id=device.id,
                sku=device.sku,
                kelvin=kelvin,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"Cloud control successful: {device.name} color temperature -> {kelvin}K")
            return True
        except Exception as e:
            logger.error(f"Failed to set color temperature for {device.name}: {e}")
            raise

    async def apply_scene(self, device: Union[Device, list], scene: Union[Scene, DIYScene]) -> bool:
        """
        Apply a scene (built-in or DIY) to device(s).

        Note: Scenes are only available via Cloud API.

        Args:
            device: Device or list of devices to control
            scene: Scene or DIYScene to apply

        Returns:
            True if successful (or True if all devices succeeded when given a list)
        """
        import asyncio

        # Handle list of devices with parallel async execution
        if isinstance(device, list):
            async def apply_worker(dev: Device) -> Tuple[str, bool]:
                """Worker function to apply scene to a single device."""
                try:
                    await self.apply_scene(dev, scene)
                    return (dev.name, True)
                except Exception as e:
                    logger.error(f"Failed to apply scene to {dev.name}: {e}")
                    return (dev.name, False)

            # Execute all devices concurrently
            results_list = await asyncio.gather(*[apply_worker(dev) for dev in device])
            results = dict(results_list)

            all_success = all(results.values())
            logger.info(f"Applied scene '{scene.name}' to {len(results)} devices ({sum(results.values())}/{len(results)} succeeded)")
            return all_success

        # Handle single device - run in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def _apply_scene_sync():
            try:
                # Check if this is a DIY scene or built-in scene
                if isinstance(scene, DIYScene):
                    # DIY scenes use diyScene capability with scene.id
                    cloud_control.scene(
                        api_key=self.api_key,
                        device_id=device.id,
                        sku=device.sku,
                        scene_id=scene.id,
                        base_url=self.base_url,
                        timeout=self.timeout
                    )
                else:
                    # Built-in scenes use lightScene capability with scene.value['id']
                    scene_id = scene.value.get('id')
                    if scene_id is None:
                        raise ValueError(f"Scene '{scene.name}' has no valid id in value field")

                    cloud_control.light_scene(
                        api_key=self.api_key,
                        device_id=device.id,
                        sku=device.sku,
                        scene_id=scene_id,
                        base_url=self.base_url,
                        timeout=self.timeout
                    )

                logger.info(f"Applied scene '{scene.name}' to {device.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to apply scene to {device.name}: {e}")
                raise

        return await loop.run_in_executor(None, _apply_scene_sync)

    async def set_music_mode(
        self,
        device: Union[Device, list],
        mode_value: int,
        sensitivity: int = 100
    ) -> bool:
        """
        Set music visualization mode.

        Note: Music modes are only available via Cloud API.

        Args:
            device: Device or list of devices to control
            mode_value: Music mode ID (device-specific)
            sensitivity: Sensitivity (0-100)

        Returns:
            True if successful (or True if all devices succeeded when given a list)
        """
        import asyncio

        # Handle list of devices with parallel async execution
        if isinstance(device, list):
            async def music_mode_worker(dev: Device) -> Tuple[str, bool]:
                """Worker function to set music mode on a single device."""
                try:
                    await self.set_music_mode(dev, mode_value, sensitivity)
                    return (dev.name, True)
                except Exception as e:
                    logger.error(f"Failed to set music mode on {dev.name}: {e}")
                    return (dev.name, False)

            # Execute all devices concurrently
            results_list = await asyncio.gather(*[music_mode_worker(dev) for dev in device])
            results = dict(results_list)

            all_success = all(results.values())
            logger.info(f"Set music mode {mode_value} on {len(results)} devices ({sum(results.values())}/{len(results)} succeeded)")
            return all_success

        # Handle single device - run in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def _set_music_mode_sync():
            try:
                cloud_control.music_mode(
                    api_key=self.api_key,
                    device_id=device.id,
                    sku=device.sku,
                    mode_value=mode_value,
                    sensitivity=sensitivity,
                    base_url=self.base_url,
                    timeout=self.timeout
                )
                logger.info(f"Set music mode {mode_value} on {device.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to set music mode on {device.name}: {e}")
                raise

        return await loop.run_in_executor(None, _set_music_mode_sync)

    # ========== Batch Operations (Concurrent) ==========

    def power_all(self, devices: Union[List[Device], Collection], on: bool) -> Dict[str, bool]:
        """
        Turn multiple devices on/off concurrently.

        Args:
            devices: List of devices or Collection
            on: True to turn on, False to turn off

        Returns:
            Dictionary mapping device names to success status
        """
        if isinstance(devices, Collection):
            devices = devices.devices

        results = {}

        def worker(device: Device) -> Tuple[str, bool]:
            try:
                self.power(device, on)
                return (device.name, True)
            except Exception as e:
                logger.error(f"Failed to power {'on' if on else 'off'} {device.name}: {e}")
                return (device.name, False)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(worker, device) for device in devices]
            for future in as_completed(futures):
                name, success = future.result()
                results[name] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Batch power {'on' if on else 'off'}: {success_count}/{len(devices)} successful")

        return results

    def set_brightness_all(
        self,
        devices: Union[List[Device], Collection],
        percent: int
    ) -> Dict[str, bool]:
        """
        Set brightness for multiple devices concurrently.

        Args:
            devices: List of devices or Collection
            percent: Brightness percentage (1-100)

        Returns:
            Dictionary mapping device names to success status
        """
        if isinstance(devices, Collection):
            devices = devices.devices

        results = {}

        def worker(device: Device) -> Tuple[str, bool]:
            try:
                self.set_brightness(device, percent)
                return (device.name, True)
            except Exception as e:
                logger.error(f"Failed to set brightness on {device.name}: {e}")
                return (device.name, False)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(worker, device) for device in devices]
            for future in as_completed(futures):
                name, success = future.result()
                results[name] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Batch brightness: {success_count}/{len(devices)} successful")

        return results

    def set_color_all(
        self,
        devices: Union[List[Device], Collection],
        rgb: RGBColor
    ) -> Dict[str, bool]:
        """
        Set color for multiple devices concurrently.

        Args:
            devices: List of devices or Collection
            rgb: RGB color tuple

        Returns:
            Dictionary mapping device names to success status
        """
        if isinstance(devices, Collection):
            devices = devices.devices

        results = {}

        def worker(device: Device) -> Tuple[str, bool]:
            try:
                self.set_color(device, rgb)
                return (device.name, True)
            except Exception as e:
                logger.error(f"Failed to set color on {device.name}: {e}")
                return (device.name, False)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(worker, device) for device in devices]
            for future in as_completed(futures):
                name, success = future.result()
                results[name] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Batch color: {success_count}/{len(devices)} successful")

        return results

    def apply_scene_all(
        self,
        devices: Union[List[Device], Collection],
        scene: Scene
    ) -> Dict[str, bool]:
        """
        Apply scene to multiple devices concurrently.

        Args:
            devices: List of devices or Collection
            scene: Scene to apply

        Returns:
            Dictionary mapping device names to success status
        """
        if isinstance(devices, Collection):
            devices = devices.devices

        results = {}

        def worker(device: Device) -> Tuple[str, bool]:
            try:
                # Get scene for this device's SKU
                device_scene = self.get_scene(scene.name, device, raise_error=False)
                if device_scene:
                    self.apply_scene(device, device_scene)
                    return (device.name, True)
                else:
                    logger.warning(f"Scene '{scene.name}' not found for {device.name} (SKU: {device.sku})")
                    return (device.name, False)
            except Exception as e:
                logger.error(f"Failed to apply scene to {device.name}: {e}")
                return (device.name, False)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(worker, device) for device in devices]
            for future in as_completed(futures):
                name, success = future.result()
                results[name] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Batch scene application: {success_count}/{len(devices)} successful")

        return results

    # ========== State Management ==========

    def save_state(
        self,
        devices: Union[Device, List[Device], Collection],
        force_refresh: bool = True
    ) -> Dict[str, "DeviceState"]:
        """
        Save current state of devices (power, brightness, color, etc.).

        This is useful before running light shows where you want to restore
        the original state afterwards.

        Args:
            devices: Device(s) to save state for
            force_refresh: If True, fetch fresh state from API

        Returns:
            Dictionary mapping device IDs to their saved DeviceState objects

        Example:
            # Save state before light show
            client.save_state([device1, device2])

            # ... run light show ...

            # Restore state after light show
            client.restore_state([device1, device2])
        """
        from govee.state import StateManager

        if not hasattr(self, "_state_manager"):
            self._state_manager = StateManager(self)

        return self._state_manager.save_state(devices, force_refresh)

    def restore_state(
        self,
        devices: Optional[Union[Device, List[Device], Collection]] = None,
        skip_on_error: bool = True
    ) -> Dict[str, bool]:
        """
        Restore previously saved state for devices.

        Args:
            devices: Device(s) to restore. If None, restores all previously saved devices.
            skip_on_error: If True, continue on errors. If False, raise on first error.

        Returns:
            Dictionary mapping device IDs to success status (True=restored, False=failed)

        Example:
            # Restore specific devices
            client.restore_state([device1, device2])

            # Restore all previously saved devices
            client.restore_state()
        """
        from govee.state import StateManager

        if not hasattr(self, "_state_manager"):
            logger.warning("No state manager found. Call save_state() first.")
            return {}

        return self._state_manager.restore_state(devices, skip_on_error)

    def clear_saved_state(
        self,
        devices: Optional[Union[Device, List[Device], Collection]] = None
    ) -> None:
        """
        Clear saved state for devices.

        Args:
            devices: Device(s) to clear state for. If None, clears all saved states.
        """
        if not hasattr(self, "_state_manager"):
            return

        self._state_manager.clear_saved_state(devices)

    def get_saved_state(self, device: Device) -> Optional["DeviceState"]:
        """
        Get saved state for a device without restoring it.

        Args:
            device: Device to get saved state for

        Returns:
            DeviceState if found, None otherwise
        """
        if not hasattr(self, "_state_manager"):
            return None

        return self._state_manager.get_saved_state(device)
