# State Management Implementation Summary

## Overview

Implemented comprehensive state save/restore functionality for the Govee Python SDK. This feature allows users to capture device states (power, brightness, color, etc.) before making changes, then restore them afterwards—perfect for light shows and automation.

## Files Created

### 1. `/govee/state.py` (351 lines)
**Purpose**: Core state management implementation

**Key Classes**:
- `DeviceState` - Dataclass representing saved device state
  - Captures: power, brightness, color, color temperature
  - Raw capabilities stored for future extensibility

- `StateManager` - Main state management class
  - `save_state()` - Save current state of devices via Cloud API
  - `restore_state()` - Restore previously saved states
  - `clear_saved_state()` - Clear saved states from memory
  - `get_saved_state()` - Get saved state without restoring
  - `has_saved_state()` - Check if state exists

**Features**:
- Supports single devices, lists, or Collections
- Error resilience (continues on failure, skip_on_error flag)
- Idempotent operations (safe to call multiple times)
- Graceful degradation (handles devices that don't support certain features)
- Proper state restoration order (power first, then settings)

### 2. `/govee/client.py` (Methods added)
**Purpose**: Integrate state management into GoveeClient

**New Methods** (lines 1373-1467):
- `save_state(devices, force_refresh=True)` - Save device states
- `restore_state(devices=None, skip_on_error=True)` - Restore saved states
- `clear_saved_state(devices=None)` - Clear saved states
- `get_saved_state(device)` - Get saved state without restoring

**Implementation Details**:
- Lazy initialization of StateManager (created on first use)
- Stored as `_state_manager` attribute on client
- Methods delegate to StateManager for actual work
- Clean, simple API surface for end users

### 3. `/govee/__init__.py` (Updated)
**Purpose**: Export state management classes

**Changes**:
- Added `StateManager` and `DeviceState` imports
- Added to `__all__` for public API

### 4. `/docs/STATE_MANAGEMENT.md` (467 lines)
**Purpose**: Comprehensive documentation

**Contents**:
- Quick start guide
- API reference with all methods
- Usage patterns (5 common patterns)
- Integration example with Light Show Manager
- DeviceState object reference
- Advanced StateManager usage
- Best practices
- Complete working examples
- Limitations and troubleshooting

### 5. `/examples/state_management_example.py` (156 lines)
**Purpose**: Executable examples demonstrating state management

**Examples Included**:
1. Basic State Save/Restore - Single device
2. Multiple Devices - Save/restore multiple at once
3. Light Show Pattern - Recommended usage pattern

**Features**:
- Fully commented and explained
- Ready to run (just add API key)
- Shows real-world usage patterns

### 6. `/README.md` (Updated)
**Purpose**: Add state management to main README

**Changes**:
- Added "State Management" to features list
- New "State Management (Save & Restore)" section in Usage Examples
- Link to detailed documentation

## StrangerCourt Integration

### `/starcourt/main.py` (Updated)

**Pre-Show Hook** (lines 631-637):
```python
# Save current state of all lights before show
try:
    print("[PRE-SHOW] Saving current state of all lights...")
    govee_client.save_state(GDEV.ALL_LIGHTS)
    print("[PRE-SHOW] Light state saved successfully")
except Exception as e:
    print(f"[WARN] Failed to save light state: {e}")
```

**Post-Show Hook** (lines 725-732):
```python
# Restore saved state of all lights
try:
    print("[POST-SHOW] Restoring previous state of all lights...")
    results = govee_client.restore_state()
    success_count = sum(1 for v in results.values() if v)
    print(f"[POST-SHOW] Light state restored: {success_count}/{len(results)} devices successful")
except Exception as e:
    print(f"[WARN] Failed to restore light state: {e}")
```

**What Gets Saved/Restored**:
- `GDEV.ALL_LIGHTS` - All garage, balcony, neon, and triad lights
- Total of ~30 devices saved before each show
- State restored after show cleanup (after hardware shutdown)

## Technical Implementation Details

### State Capture Flow

1. **User calls `save_state()`**
   - Client delegates to StateManager
   - For each device:
     - Call Cloud API `get_device_state()` endpoint
     - Parse capabilities array into DeviceState object
     - Store in `_saved_states` dict (keyed by device ID)

2. **Cloud API Response Structure**:
```json
{
  "sku": "H6008",
  "device": "14:15:60:74:F4:07:99:39",
  "capabilities": [
    {"instance": "powerSwitch", "state": {"value": 1}},
    {"instance": "brightness", "state": {"value": 75}},
    {"instance": "colorRgb", "state": {"value": {"r": 255, "g": 0, "b": 0}}}
  ]
}
```

3. **Parsed into DeviceState**:
```python
DeviceState(
    device=Device(...),
    power=True,
    brightness=75,
    color=(255, 0, 0),
    raw_capabilities=[...]
)
```

### State Restoration Flow

1. **User calls `restore_state()`**
   - Client delegates to StateManager
   - For each device with saved state:
     - **Step 1**: If power=False, turn off and skip rest
     - **Step 2**: If power=True, turn on first
     - **Step 3**: Restore brightness (if saved and supported)
     - **Step 4**: Restore color OR color temperature (if saved)

2. **Order matters**:
   - Power must be set first (can't set brightness on OFF device)
   - Brightness before color (better user experience)
   - Color temp OR color (not both, color takes precedence)

3. **Error Handling**:
   - Each step wrapped in try/except
   - `skip_on_error=True` (default) continues on failure
   - Returns dict mapping device ID → success boolean

### What's NOT Restored

**Scenes and Music Modes** - Intentionally not restored because:
1. They may have been applied temporarily during the show
2. User may not want them back
3. Setting specific color/brightness is more predictable
4. API limitations make exact scene restoration difficult

## Usage Pattern

### Recommended Pattern (Light Shows)

```python
# 1. BEFORE SHOW: Save state
client.save_state(all_lights)

# 2. DURING SHOW: Make changes
show.run()  # Changes lights however you want

# 3. AFTER SHOW: Restore state
client.restore_state()  # Restores everything saved
```

### Integration with Light Show Manager

```python
async def pre_show_hook(show: Show, context: dict):
    # Save state before show starts
    govee_client.save_state(devices)

async def post_show_hook(show: Show, context: dict):
    # Restore state after show ends
    govee_client.restore_state()
```

## Error Handling

**Save State**:
- If a device fails to save, stores empty DeviceState
- Logs error but continues with other devices
- Never raises (swallows exceptions by design)

**Restore State**:
- If a device fails to restore, logs error and continues
- Returns dict with success status per device
- `skip_on_error=True` (default) continues on failure
- `skip_on_error=False` raises on first failure

**Network Failures**:
- Cloud API timeout: Logs error, device skipped
- Connection error: Logs error, device skipped
- Rate limiting: May affect multiple devices

## Performance Considerations

**Save State**:
- One API call per device (sequential)
- ~30 devices × ~1 second = ~30 seconds
- Runs once at show start (acceptable delay)

**Restore State**:
- Multiple API calls per device (power, brightness, color)
- Sequential execution (must wait for power before brightness)
- ~30 devices × ~3 seconds = ~90 seconds worst case
- Can be optimized in future with parallel requests

**Memory**:
- ~1KB per DeviceState object
- 30 devices = ~30KB total
- Negligible memory footprint

## Future Enhancements

Potential improvements for future versions:

1. **Parallel Restoration**
   - Restore multiple devices concurrently
   - Reduce total restoration time

2. **Persistent State**
   - Save state to disk (JSON file)
   - Survive process restarts
   - Useful for power failures

3. **State Diffs**
   - Only restore changed values
   - Reduce API calls

4. **LAN State Support**
   - Some devices support state queries via LAN
   - Faster than Cloud API

5. **Scene/Music Mode Restoration**
   - Optional flag to restore scenes
   - May require additional API endpoints

6. **State History**
   - Keep multiple saved states (stack)
   - Allow rolling back to earlier states

## Testing

**Manual Testing Checklist**:
- ✓ Save state of single device
- ✓ Save state of multiple devices
- ✓ Save state of Collection
- ✓ Restore state of single device
- ✓ Restore state of multiple devices
- ✓ Restore all saved devices (no args)
- ✓ Clear saved state
- ✓ Get saved state without restoring
- ✓ Error handling (device offline)
- ✓ Integration with StrangerCourt main.py

**Example Test Script**:
See `/examples/state_management_example.py` for runnable examples.

## API Compatibility

**Requires**:
- Cloud API access (API key required)
- Device state endpoint: `POST /router/api/v1/device/state`
- Device control endpoints (for restoration)

**LAN Support**:
- LAN does not support state queries (Cloud API only)
- Restoration uses LAN-first fallback (if available)

## Documentation

**User-Facing Docs**:
- `README.md` - Quick example in Usage section
- `docs/STATE_MANAGEMENT.md` - Comprehensive guide
- `examples/state_management_example.py` - Runnable examples

**Developer Docs**:
- `govee/state.py` - Inline docstrings for all classes/methods
- `govee/client.py` - Method docstrings with examples
- This document - Implementation summary

## Summary

Implemented a complete state management system for the Govee Python SDK:

✅ **Core Implementation**: StateManager class with save/restore functionality
✅ **Client Integration**: Simple API methods on GoveeClient
✅ **StrangerCourt Integration**: Pre/post show hooks save/restore automatically
✅ **Documentation**: Comprehensive docs with examples
✅ **Examples**: Runnable example scripts
✅ **Error Handling**: Graceful degradation and error resilience
✅ **Performance**: Optimized for light show use case

**Use Case**: Perfect for light shows where you want to temporarily change lights and restore them afterwards. The StrangerCourt project now automatically saves all light states before each show and restores them after the show completes.

**API**:
```python
# Save state
client.save_state(devices)

# Restore state
client.restore_state()

# Clear state
client.clear_saved_state()

# Get state without restoring
state = client.get_saved_state(device)
```

**Integration**: Fully integrated into StrangerCourt's main.py pre/post show hooks. All 30+ lights automatically saved before each show and restored afterwards.
