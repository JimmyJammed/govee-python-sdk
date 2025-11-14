"""
Custom exceptions for govee-python package.
"""


class GoveeError(Exception):
    """Base exception for all Govee-related errors."""

    pass


class GoveeAPIError(GoveeError):
    """Raised when Govee API returns an error response."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class GoveeConnectionError(GoveeError):
    """Raised when unable to connect to Govee API or device."""

    pass


class GoveeTimeoutError(GoveeError):
    """Raised when a request times out."""

    pass


class GoveeDeviceNotFoundError(GoveeError):
    """Raised when a device cannot be found."""

    def __init__(self, device_identifier: str):
        self.device_identifier = device_identifier
        super().__init__(f"Device not found: {device_identifier}")


class GoveeSceneNotFoundError(GoveeError):
    """Raised when a scene cannot be found."""

    def __init__(self, scene_name: str, device_sku: str = None):
        self.scene_name = scene_name
        self.device_sku = device_sku
        msg = f"Scene not found: {scene_name}"
        if device_sku:
            msg += f" for device SKU {device_sku}"
        super().__init__(msg)


class GoveeInvalidParameterError(GoveeError):
    """Raised when invalid parameters are provided."""

    pass


class GoveeLANNotSupportedError(GoveeError):
    """Raised when LAN control is attempted on a device that doesn't support it."""

    def __init__(self, device_name: str):
        self.device_name = device_name
        super().__init__(f"Device does not support LAN control: {device_name}")
