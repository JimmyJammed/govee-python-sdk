#!/usr/bin/env python3
"""
Create GitHub release

Usage:
    export GITHUB_TOKEN=your_token_here
    python3 create_release.py [version]

Examples:
    python3 create_release.py 1.0.1
    python3 create_release.py 1.0.0
"""

import json
import os
import sys
import urllib.request
import urllib.error

REPO = "JimmyJammed/govee-python-sdk"

# Get version from command line or default
VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0.1"
TAG = f"v{VERSION}"

RELEASE_BODIES = {
    "1.0.0": """# Version 1.0.0 - Initial Release

A modern, easy-to-use Python library for controlling Govee smart lights via LAN (UDP) and Cloud (HTTPS) APIs.

## Features

- **Interactive CLI Wizard** - Easy setup and device control with `govee-sync`
- **Dual Protocol Support** - LAN (UDP) for fast local control, Cloud API for full features
- **Automatic Fallback** - Tries LAN first, falls back to Cloud seamlessly
- **State Management** - Save and restore device states (perfect for light shows)
- **Type-Safe Models** - Full type hints with dataclasses for IDE autocomplete
- **Python Module Export** - Import devices and scenes directly as Python objects
- **Built-in & DIY Scenes** - Apply Govee's default scenes or your custom creations
- **Concurrent Operations** - Control multiple devices simultaneously
- **Batch Operations** - Group devices for coordinated control

## Installation

```bash
pip install govee-python
```

## Quick Start

```bash
govee-sync
```

The wizard will guide you through setting up your API key, discovering devices, and exporting Python modules.

## Documentation

See [README.md](README.md) for full documentation and examples.""",
    "1.0.1": """# Version 1.0.1 - Patch Release

This patch release follows a complete git history rewrite and codebase cleanup, ensuring a clean foundation for future development.

## What's Changed

- **Git History Rewrite** - Clean slate with a single initial commit
- **Codebase Cleanup** - Removed legacy code and improved structure
- **Documentation Updates** - Updated repository URLs and metadata
- **PyPI Synchronization** - Aligned with PyPI package version

## Installation

```bash
pip install govee-python==1.0.1
```

## Features

- **Interactive CLI Wizard** - Easy setup and device control with `govee-sync`
- **Dual Protocol Support** - LAN (UDP) for fast local control, Cloud API for full features
- **Automatic Fallback** - Tries LAN first, falls back to Cloud seamlessly
- **State Management** - Save and restore device states (perfect for light shows)
- **Type-Safe Models** - Full type hints with dataclasses for IDE autocomplete
- **Python Module Export** - Import devices and scenes directly as Python objects
- **Built-in & DIY Scenes** - Apply Govee's default scenes or your custom creations
- **Concurrent Operations** - Control multiple devices simultaneously
- **Batch Operations** - Group devices for coordinated control

## Quick Start

```bash
govee-sync
```

The wizard will guide you through setting up your API key, discovering devices, and exporting Python modules.

## Documentation

See [README.md](README.md) for full documentation and examples."""
}

def get_release_body(version):
    """Get release body for a specific version"""
    return RELEASE_BODIES.get(version, RELEASE_BODIES.get("1.0.1", ""))

def main():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("\nTo create a release, you need a GitHub Personal Access Token:")
        print("1. Create a token at: https://github.com/settings/tokens")
        print("2. Give it 'repo' scope")
        print("3. Run: export GITHUB_TOKEN=your_token_here")
        print(f"4. Run this script again: python3 create_release.py {VERSION}")
        print("\nOr create the release manually at:")
        print(f"   https://github.com/{REPO}/releases/new")
        print(f"   - Select tag: {TAG}")
        print(f"   - Title: {TAG}")
        sys.exit(1)
    
    release_body = get_release_body(VERSION)
    if not release_body:
        print(f"❌ No release body defined for version {VERSION}")
        print(f"   Available versions: {', '.join(RELEASE_BODIES.keys())}")
        sys.exit(1)
    
    print(f"📦 Creating release {TAG} for {REPO}")
    print(f"   Version: {VERSION}")
    
    release_data = {
        "tag_name": TAG,
        "name": TAG,
        "body": release_body,
        "draft": False,
        "prerelease": False
    }
    
    url = f"https://api.github.com/repos/{REPO}/releases"
    data = json.dumps(release_data).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'token {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ Release created successfully!")
            print(f"   URL: {result.get('html_url', 'N/A')}")
            return 0
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('message', error_body)
        except:
            error_msg = error_body
        print(f"❌ Failed to create release: {e.code}")
        print(f"   Error: {error_msg}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

