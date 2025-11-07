#!/bin/bash
echo "========================================="
echo "Checking Home Assistant Sensor Data"
echo "========================================="
echo ""

# Get container logs for the last 2 minutes, focusing on push updates and polling
echo "=== Recent Home Assistant Logs (Last 2 min) ==="
docker logs hoymiles-smiles-homeassistant-1 --since 2m 2>&1 | grep -E "WebSocket|Poll|Update|Sensor Init|Initial State" | tail -50

echo ""
echo "=== Bridge Push Activity (Last 2 min) ==="
docker logs hoymiles-smiles-hoymiles-smiles-1 --since 2m 2>&1 | grep -E "Successfully pushed|WebSocket.*Connected" | tail -10

echo ""
echo "=== API Polling Activity (Last 2 min) ==="
docker logs hoymiles-smiles-hoymiles-smiles-1 --since 2m 2>&1 | grep -E "\[API Request\]" | tail -20

