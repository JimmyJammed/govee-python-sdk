# govee-python v1.0.2

**Release date:** February 23, 2025

## Installation

```bash
pip install govee-python==1.0.2
# or upgrade
pip install --upgrade govee-python
```

**PyPI:** https://pypi.org/project/govee-python/1.0.2/

---

## What's New

### Added

- **Comprehensive Color Palettes** – 90+ predefined RGB color constants
  - Basic, neon, pastel, warm whites, seasonal (Halloween, Christmas, patriotic), deep/dark, and nature palettes
  - `Colors.list_colors()` and improved `Colors.get()` documentation

- **Optional LAN Verification** – New `verify` parameter on `GoveeClient.power()`
  - Use `client.power(device, False, verify=False)` for faster fire-and-forget power commands when confirmation isn’t needed

### Changed

- **Aggressive LAN Timeouts** – LAN timeouts reduced from 2–10 seconds to **0.5 seconds**
  - Much faster Cloud API fallback when LAN is unavailable
  - Verification: 500ms delay + 500ms status query (1 second max)

- **Faster State Restoration** – State restore now uses `verify=False` for power commands
  - Post-show restore in ~1 second instead of 10+ seconds

### Fixed

- **LAN Status Socket Conflicts** – Resolved "[Errno 48] Address already in use" during parallel status queries
  - LAN status queries now use ephemeral ports so multiple queries can run without port conflicts

---

## Links

- [Changelog](https://github.com/JimmyJammed/govee-python-sdk/blob/main/CHANGELOG.md)
- [Repository](https://github.com/JimmyJammed/govee-python-sdk)
