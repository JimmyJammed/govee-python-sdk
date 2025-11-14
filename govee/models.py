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
        metadata: Additional mode metadata (sensitivity range, color options, etc.)
    """

    name: str
    value: int
    sku: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert music mode to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicMode":
        """Create music mode from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert music mode to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MusicMode":
        """Create music mode from JSON string."""
        return cls.from_dict(json.loads(json_str))

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
    """
    Comprehensive RGB color presets for smart lighting control.

    Available color palettes:
    - Basic colors: WHITE, BLACK, RED, GREEN, BLUE, etc.
    - Neon colors: NEON_PINK, NEON_PURPLE, NEON_BLUE, etc.
    - Pastel colors: PASTEL_PINK, PASTEL_BLUE, PASTEL_YELLOW, etc.
    - Warm whites: WARM_WHITE, SOFT_WHITE, DAYLIGHT
    - Halloween: HALLOWEEN_ORANGE, HALLOWEEN_PURPLE, HALLOWEEN_GREEN
    - Christmas: CHRISTMAS_RED, CHRISTMAS_GREEN, CHRISTMAS_GOLD

    Usage:
        client.set_color(device, Colors.NEON_PINK)
        client.set_color(device, Colors.get("warm white"))
    """

    # ═══════════════════════════════════════════════════════════════════
    # BASIC COLORS
    # ═══════════════════════════════════════════════════════════════════
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    PINK = (255, 192, 203)
    BROWN = (139, 69, 19)
    GRAY = (128, 128, 128)
    SILVER = (192, 192, 192)
    GOLD = (255, 215, 0)

    # ═══════════════════════════════════════════════════════════════════
    # NEON COLORS - Vivid, high-saturation colors
    # ═══════════════════════════════════════════════════════════════════
    NEON_PINK = (255, 20, 147)      # Hot pink
    NEON_PURPLE = (191, 64, 255)    # Vivid purple
    NEON_BLUE = (0, 191, 255)       # Deep sky blue
    NEON_ORANGE = (255, 120, 0)     # Bright orange
    NEON_YELLOW = (255, 255, 40)    # Vivid yellow
    NEON_GREEN = (57, 255, 20)      # Bright green
    NEON_RED = (255, 0, 60)         # Vivid red
    NEON_CYAN = (0, 255, 255)       # Electric cyan

    # ═══════════════════════════════════════════════════════════════════
    # PASTEL COLORS - Soft, muted colors
    # ═══════════════════════════════════════════════════════════════════
    PASTEL_PINK = (255, 209, 220)
    PASTEL_BLUE = (174, 198, 207)
    PASTEL_YELLOW = (253, 253, 150)
    PASTEL_GREEN = (119, 221, 119)
    PASTEL_PURPLE = (179, 158, 181)
    PASTEL_ORANGE = (255, 179, 71)
    PASTEL_MINT = (152, 255, 152)
    PASTEL_PEACH = (255, 218, 185)

    # ═══════════════════════════════════════════════════════════════════
    # WARM WHITES - Various shades of white for ambiance
    # ═══════════════════════════════════════════════════════════════════
    WARM_WHITE = (255, 197, 143)    # 2700K - Cozy, warm glow
    SOFT_WHITE = (255, 214, 170)    # 3000K - Comfortable white
    NEUTRAL_WHITE = (255, 241, 224) # 4000K - Balanced white
    COOL_WHITE = (255, 250, 244)    # 5000K - Bright, energetic
    DAYLIGHT = (255, 255, 251)      # 6500K - Natural daylight

    # ═══════════════════════════════════════════════════════════════════
    # HALLOWEEN COLORS
    # ═══════════════════════════════════════════════════════════════════
    HALLOWEEN_ORANGE = (255, 117, 24)
    HALLOWEEN_PURPLE = (102, 0, 153)
    HALLOWEEN_GREEN = (26, 255, 26)
    HALLOWEEN_BLACK = (20, 20, 20)

    # ═══════════════════════════════════════════════════════════════════
    # CHRISTMAS COLORS
    # ═══════════════════════════════════════════════════════════════════
    CHRISTMAS_RED = (200, 16, 46)
    CHRISTMAS_GREEN = (0, 108, 45)
    CHRISTMAS_GOLD = (212, 175, 55)
    CHRISTMAS_SILVER = (192, 192, 192)
    CHRISTMAS_WHITE = (255, 255, 255)

    # ═══════════════════════════════════════════════════════════════════
    # PATRIOTIC COLORS (USA)
    # ═══════════════════════════════════════════════════════════════════
    PATRIOT_RED = (191, 10, 48)
    PATRIOT_WHITE = (255, 255, 255)
    PATRIOT_BLUE = (0, 40, 104)

    # ═══════════════════════════════════════════════════════════════════
    # DEEP/DARK COLORS - Moody, atmospheric colors
    # ═══════════════════════════════════════════════════════════════════
    DEEP_RED = (139, 0, 0)
    DEEP_BLUE = (0, 0, 139)
    DEEP_GREEN = (0, 100, 0)
    DEEP_PURPLE = (75, 0, 130)      # Indigo
    DEEP_ORANGE = (255, 69, 0)
    MIDNIGHT_BLUE = (25, 25, 112)

    # ═══════════════════════════════════════════════════════════════════
    # VIBRANT COLORS - High-energy, saturated colors
    # ═══════════════════════════════════════════════════════════════════
    VIBRANT_RED = (255, 0, 0)
    VIBRANT_ORANGE = (255, 127, 0)
    VIBRANT_YELLOW = (255, 255, 0)
    VIBRANT_GREEN = (0, 255, 0)
    VIBRANT_CYAN = (0, 255, 255)
    VIBRANT_BLUE = (0, 0, 255)
    VIBRANT_MAGENTA = (255, 0, 255)

    # ═══════════════════════════════════════════════════════════════════
    # NATURE COLORS - Earth tones and natural hues
    # ═══════════════════════════════════════════════════════════════════
    SKY_BLUE = (135, 206, 235)
    OCEAN_BLUE = (0, 119, 190)
    FOREST_GREEN = (34, 139, 34)
    GRASS_GREEN = (124, 252, 0)
    SUNSET_ORANGE = (255, 99, 71)
    SUNRISE_YELLOW = (255, 223, 0)
    LAVENDER = (230, 230, 250)
    CORAL = (255, 127, 80)
    TURQUOISE = (64, 224, 208)
    MINT = (189, 252, 201)
    PEACH = (255, 218, 185)

    # ═══════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def get(cls, name: str) -> Optional[RGBColor]:
        """
        Get color by name (case-insensitive, supports spaces/hyphens).

        Args:
            name: Color name (e.g., "neon pink", "warm-white", "CHRISTMAS_RED")

        Returns:
            RGB tuple or None if color not found

        Examples:
            Colors.get("neon pink")    # (255, 20, 147)
            Colors.get("warm-white")   # (255, 197, 143)
            Colors.get("RED")          # (255, 0, 0)
        """
        name_upper = name.upper().replace(" ", "_").replace("-", "_")
        return getattr(cls, name_upper, None)

    @classmethod
    def list_colors(cls) -> list[str]:
        """
        Get a list of all available color names.

        Returns:
            List of color names (lowercase with spaces)

        Example:
            >>> Colors.list_colors()
            ['white', 'black', 'red', 'neon pink', 'pastel blue', ...]
        """
        colors = []
        for attr in dir(cls):
            if not attr.startswith('_') and attr.isupper():
                # Convert NEON_PINK to "neon pink"
                color_name = attr.lower().replace('_', ' ')
                colors.append(color_name)
        return sorted(colors)
