#!/bin/bash

echo "=== Checking Home Assistant Logs ==="
echo ""
echo "If you're using Home Assistant OS/Supervised, run this in HA's terminal:"
echo "  ha core logs | grep -i hoymiles"
echo ""
echo "If you're using Docker Compose, run:"
echo "  docker logs homeassistant 2>&1 | grep -i hoymiles"
echo ""
echo "If HA is standalone, check:"
echo "  /config/home-assistant.log"
echo ""
echo "Look for these specific lines:"
echo "  - [WebSocket Registration] Registering with bridge"
echo "  - [WebSocket Registration] ✓ Successfully registered"
echo "  - OR error messages from the integration"

