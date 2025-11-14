#!/bin/bash
# Script to create GitHub release for v1.0.0

set -e

REPO="JimmyJammed/govee-python-sdk"
TAG="v1.0.0"

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable not set"
    echo ""
    echo "To create a release, you need a GitHub Personal Access Token."
    echo "1. Create a token at: https://github.com/settings/tokens"
    echo "2. Give it 'repo' scope"
    echo "3. Run: export GITHUB_TOKEN=your_token_here"
    echo "4. Run this script again"
    echo ""
    echo "Or create the release manually at:"
    echo "   https://github.com/$REPO/releases/new"
    exit 1
fi

# Release body
RELEASE_BODY='# Version 1.0.0 - Initial Release

A modern, easy-to-use Python library for controlling Govee smart lights via LAN (UDP) and Cloud (HTTPS) APIs.

## Features

- **Interactive CLI Wizard** - Easy setup and device control with `govee-sync`
- **Dual Protocol Support** - LAN (UDP) for fast local control, Cloud API for full features
- **Automatic Fallback** - Tries LAN first, falls back to Cloud seamlessly
- **State Management** - Save and restore device states (perfect for light shows)
- **Type-Safe Models** - Full type hints with dataclasses for IDE autocomplete
- **Python Module Export** - Import devices and scenes directly as Python objects
- **Built-in & DIY Scenes** - Apply Govee'\''s default scenes or your custom creations
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

See [README.md](README.md) for full documentation and examples.'

# Create JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
  "tag_name": "$TAG",
  "name": "$TAG",
  "body": $(echo "$RELEASE_BODY" | jq -Rs .),
  "draft": false,
  "prerelease": false
}
EOF
)

# Create release via GitHub API
echo "Creating release $TAG for $REPO..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "https://api.github.com/repos/$REPO/releases" \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.github.v3+json" \
  -d "$JSON_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "201" ]; then
    RELEASE_URL=$(echo "$BODY" | grep -o '"html_url":"[^"]*' | cut -d'"' -f4)
    echo "✅ Release created successfully!"
    echo "   URL: $RELEASE_URL"
else
    echo "❌ Failed to create release"
    echo "   HTTP Code: $HTTP_CODE"
    echo "   Response: $BODY"
    exit 1
fi

