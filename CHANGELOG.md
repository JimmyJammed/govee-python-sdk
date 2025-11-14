# Changelog

All notable changes to the govee-python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Comprehensive Color Palettes** - 90+ predefined RGB color constants
  - Basic colors: WHITE, BLACK, RED, GREEN, BLUE, etc.
  - Neon colors: NEON_PINK, NEON_PURPLE, NEON_BLUE (8 vivid colors)
  - Pastel colors: PASTEL_PINK, PASTEL_BLUE, PASTEL_YELLOW (8 soft colors)
  - Warm whites: WARM_WHITE (2700K), SOFT_WHITE (3000K), DAYLIGHT (6500K)
  - Halloween palette: HALLOWEEN_ORANGE, HALLOWEEN_PURPLE, HALLOWEEN_GREEN
  - Christmas palette: CHRISTMAS_RED, CHRISTMAS_GREEN, CHRISTMAS_GOLD
  - Patriotic colors: PATRIOT_RED, PATRIOT_WHITE, PATRIOT_BLUE
  - Deep/dark colors: DEEP_RED, DEEP_BLUE, MIDNIGHT_BLUE (6 moody colors)
  - Nature colors: SKY_BLUE, OCEAN_BLUE, FOREST_GREEN, CORAL (11 natural hues)
  - `Colors.list_colors()` method to list all available colors
  - Enhanced `Colors.get()` with better documentation
- **Optional LAN Verification** - Added `verify` parameter to `GoveeClient.power()`
  - Skip LAN status verification for faster operation when verification isn't needed
  - Useful for pre-show operations where speed is more important than confirmation
  - Example: `client.power(device, False, verify=False)` for instant power-off

### Changed
- **Aggressive LAN Timeouts** - Reduced LAN timeouts from 2-10 seconds to 0.5 seconds
  - LAN status queries: 2.0s → 0.5s (4x faster)
  - LAN power/brightness/color: 5.0s → 0.5s (10x faster)
  - Total verification time: 500ms delay + 500ms status query = 1 second max
  - Fast Cloud API fallback on LAN failure (no more 10-second waits)
  - GoveeClient timeout (10s) now only applies to Cloud API (HTTP requests)
- **Faster State Restoration** - State restoration now uses `verify=False` for power commands
  - Eliminates 10+ second LAN verification timeouts during post-show cleanup
  - State restoration now completes in ~1 second instead of 10+ seconds
  - Fire-and-forget power commands for maximum speed

### Fixed
- **LAN Status Socket Conflicts** - Fixed "[Errno 48] Address already in use" errors
  - Changed LAN status queries to use ephemeral ports (port 0)
  - Allows parallel status queries without socket binding conflicts
  - Devices respond to the querying socket's port, so ephemeral ports work perfectly

## [1.2.0] - 2024-11-13

### Added
- **LAN API State Queries** - Use local network for faster state retrieval
  - `_get_device_state()` now tries LAN first, falls back to Cloud API
  - `_parse_lan_state()` method to handle LAN API response format
  - 4x faster state queries (~0.1s vs ~0.4s per device)
  - Automatic fallback to Cloud API if LAN unavailable
- **Async Device Control Methods** - Native async support for parallel operations
  - `apply_scene()` is now async, accepts Device or list of devices
  - `set_music_mode()` is now async, accepts Device or list of devices
  - Methods use `asyncio.gather()` for true concurrent execution
  - Integrates seamlessly with async show frameworks
  - Simplifies show building with device collections

### Changed
- **Parallel State Operations** - ThreadPoolExecutor for concurrent API calls
  - `save_state()` now processes up to 20 devices in parallel
  - `restore_state()` now processes up to 20 devices in parallel
  - 10x faster for multiple devices (~0.4s for 10 devices vs ~4s sequential)
  - Increased max workers from 10 to 20 for improved throughput on large device sets

### Fixed
- **Packed RGB Integer Support** - Handle Cloud API's integer color format
  - Cloud API returns RGB as packed integer (e.g., `9109759` = `0x8B00FF`)
  - Added bit manipulation to extract R, G, B components
  - Colors now capture and restore correctly
- **Color Temperature Validation** - Skip restoration if value is 0
  - Prevents 400 errors from invalid Kelvin values

### Performance
- 2 devices: ~6s → ~0.6s with LAN (10x faster)
- 10 devices: ~40s → ~0.3s with LAN parallel (133x faster)
- 30 devices: ~120s → ~0.9s with LAN parallel (133x faster)

## [1.1.0] - 2024-11-13

### Added
- **State Management System** - Save and restore device states (power, brightness, color, etc.)
  - `GoveeClient.save_state()` - Save current state of devices
  - `GoveeClient.restore_state()` - Restore previously saved states
  - `GoveeClient.clear_saved_state()` - Clear saved states
  - `GoveeClient.get_saved_state()` - Get saved state without restoring
  - New `StateManager` class for advanced state management
  - New `DeviceState` dataclass representing saved device state
  - Comprehensive documentation in `docs/STATE_MANAGEMENT.md`
  - Example script at `examples/state_management_example.py`

### Changed
- Updated README with state management examples
- Version bump to 1.1.0

### Use Cases
- Perfect for light shows where you want to restore original state afterwards
- Automation routines that temporarily change lights
- Testing and development workflows

## [1.0.0] - 2024-11-07

### Added
- Initial release
- Interactive CLI wizard (`govee-sync`)
- Dual protocol support (LAN + Cloud API)
- Automatic LAN-first fallback
- Type-safe models with full type hints
- Python module export for devices and scenes
- Built-in and DIY scene support
- Concurrent and batch operations
- Device collections
- Comprehensive examples and documentation

[1.2.0]: https://github.com/yourusername/govee-python/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/yourusername/govee-python/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yourusername/govee-python/releases/tag/v1.0.0
