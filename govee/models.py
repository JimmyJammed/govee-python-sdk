"""
Core data models for govee-python package.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
import json


@dataclass
class Device:
    """
    Represents a Govee device.

    Attributes:
        id: Unique device identifier from Govee (e.g., "14:15:60:74:F4:07:99:39")
        name: Human-readable device name (e.g., "Garage Left")
        sku: Device model/SKU (e.g., "H6008")
        ip: Optional IP address for LAN control
        capabilities: List of capability names (e.g., ["on_off", "brightness", "color_setting"])
        metadata: Additional device metadata
    """

    id: str
    name: str
    sku: str
    ip: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize device data after initialization."""
        # Ensure capabilities is a list
        if not isinstance(self.capabilities, list):
            self.capabilities = list(self.capabilities) if self.capabilities else []

    @property
    def supports_lan(self) -> bool:
        """Check if device supports LAN control (has IP address)."""
        return bool(self.ip)

    @property
    def supports_cloud(self) -> bool:
        """Check if device supports Cloud API control (always True if ID and SKU present)."""
        return bool(self.id and self.sku)

    @property
    def supports_scenes(self) -> bool:
        """Check if device supports DIY scenes."""
        return "dynamic_scene" in self.capabilities

    @property
    def supports_music_mode(self) -> bool:
        """Check if device supports music visualization modes."""
        return "music_setting" in self.capabilities

    @property
    def supports_brightness(self) -> bool:
        """Check if device supports brightness control."""
        return "brightness" in self.capabilities

    @property
    def supports_color(self) -> bool:
        """Check if device supports color control."""
        return "color_setting" in self.capabilities or "colorRgb" in self.capabilities

    @property
    def is_light(self) -> bool:
        """
        Check if device is a light (not a plug or other device type).
        Based on device type metadata or SKU patterns.
        """
        # Check metadata
        device_type = self.metadata.get("type", "").lower()
        if device_type and device_type != "devices.types.light":
            return False

        # Check SKU patterns (H5080 = smart plug)
        if self.sku in ["H5080", "H5081"]:
            return False

        # Default to True (most Govee devices are lights)
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """Create device from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert device to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Device":
        """Create device from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        lan_status = "LAN" if self.supports_lan else "Cloud"
        return f"Device(name='{self.name}', sku='{self.sku}', {lan_status})"


@dataclass
class Scene:
    """
    Represents a Govee built-in scene (read-only, predefined by Govee).

    These are Govee's default scenes like "Sunrise", "Sunset", "Aurora", etc.
    Users can apply these scenes but cannot modify them.

    Attributes:
        name: Scene name (e.g., "Sunrise", "Sunset", "Aurora")
        value: Scene control value containing paramId and scene id
        sku: Device SKU this scene is available for (e.g., "H6008")
        metadata: Additional scene metadata
    """

    name: str
    value: Dict[str, int]  # {"paramId": X, "id": Y}
    sku: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        """Create scene from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert scene to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Scene":
        """Create scene from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return f"Scene(name='{self.name}', sku='{self.sku}')"


@dataclass
class DIYScene:
    """
    Represents a Govee DIY scene (user-created/customizable scene).

    DIY Scenes are custom scenes that users can create and modify in the Govee app,
    as opposed to Govee's built-in default scenes which cannot be altered.

    Attributes:
        id: Scene ID from Govee API
        name: Scene name (e.g., "SC_Bulb_Starcourt")
        sku: Device SKU this scene is designed for (e.g., "H6008")
        metadata: Additional scene metadata
    """

    id: int
    name: str
    sku: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DIY scene to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DIYScene":
        """Create DIY scene from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert DIY scene to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DIYScene":
        """Create DIY scene from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return f"DIYScene(name='{self.name}', id={self.id}, sku='{self.sku}')"


@dataclass
class MusicMode:
    """
    Represents a music visualization mode.

    Attributes:
        name: Mode name (e.g., "Energic", "Rhythm")
        value: Mode ID/value for API
        sku: Device SKU this mode is available for
    """

    name: str
    value: int
    sku: str

    def __repr__(self) -> str:
        return f"MusicMode(name='{self.name}', sku='{self.sku}')"


@dataclass
class Collection:
    """
    Represents a group of devices.

    Attributes:
        name: Collection name (e.g., "garage_lights")
        devices: List of devices in this collection
    """

    name: str
    devices: List[Device] = field(default_factory=list)

    def __len__(self) -> int:
        """Return number of devices in collection."""
        return len(self.devices)

    def __iter__(self):
        """Iterate over devices in collection."""
        return iter(self.devices)

    def __getitem__(self, index: int) -> Device:
        """Get device by index."""
        return self.devices[index]

    def filter(self, **kwargs) -> "Collection":
        """
        Filter devices by attribute values.

        Example:
            garage_lights.filter(sku="H6008")
            garage_lights.filter(supports_lan=True)
        """
        filtered = []
        for device in self.devices:
            match = True
            for key, value in kwargs.items():
                device_value = getattr(device, key, None)
                if device_value != value:
                    match = False
                    break
            if match:
                filtered.append(device)

        return Collection(name=f"{self.name}_filtered", devices=filtered)

    def get_by_name(self, name: str) -> Optional[Device]:
        """Get device by name (case-insensitive)."""
        name_lower = name.lower()
        for device in self.devices:
            if device.name.lower() == name_lower:
                return device
        return None

    def get_by_id(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        for device in self.devices:
            if device.id == device_id:
                return device
        return None

    def add(self, device: Device) -> None:
        """Add a device to the collection."""
        if device not in self.devices:
            self.devices.append(device)

    def remove(self, device: Device) -> None:
        """Remove a device from the collection."""
        if device in self.devices:
            self.devices.remove(device)

    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary."""
        return {"name": self.name, "devices": [d.to_dict() for d in self.devices]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collection":
        """Create collection from dictionary."""
        return cls(
            name=data["name"], devices=[Device.from_dict(d) for d in data.get("devices", [])]
        )

    def __repr__(self) -> str:
        return f"Collection(name='{self.name}', devices={len(self.devices)})"


# Color type alias for RGB tuples
RGBColor = Tuple[int, int, int]


# Predefined color constants
class Colors:
    """Common RGB color presets."""

    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    PINK = (255, 192, 203)

    # Neon colors
    NEON_PINK = (255, 20, 147)
    NEON_PURPLE = (191, 64, 255)
    NEON_BLUE = (0, 191, 255)
    NEON_ORANGE = (255, 120, 0)
    NEON_YELLOW = (255, 255, 40)
    NEON_GREEN = (57, 255, 20)

    @classmethod
    def get(cls, name: str) -> Optional[RGBColor]:
        """Get color by name (case-insensitive)."""
        name_upper = name.upper().replace(" ", "_").replace("-", "_")
        return getattr(cls, name_upper, None)
