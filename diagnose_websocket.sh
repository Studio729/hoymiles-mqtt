#!/bin/bash

echo "=========================================="
echo "  WebSocket Connection Diagnostic"
echo "=========================================="
echo ""

echo "Step 1: Check if bridge has WebSocket connections"
echo "------------------------------------------------"
docker logs hoymiles-smiles 2>&1 | tail -50 | grep -E "WebSocket push.*connections|WebSocket.*Connect"
echo ""

echo "Step 2: Check if bridge received registration"
echo "----------------------------------------------"
docker logs hoymiles-smiles 2>&1 | grep -i "registered websocket"
echo ""

echo "Step 3: Check bridge API endpoint calls"
echo "---------------------------------------"
docker logs hoymiles-smiles 2>&1 | tail -20 | grep -E "API Request|websocket/register"
echo ""

echo "Step 4: Check Home Assistant can reach bridge"
echo "---------------------------------------------"
curl -s http://192.168.1.191:8080/health | jq .healthy
echo ""

echo "=========================================="
echo "  What This Means:"
echo "=========================================="
echo ""
echo "If you see:"
echo "  'Successfully pushed data via WebSocket to 0 connections'"
echo "  → Home Assistant hasn't registered yet"
echo ""
echo "If you see:"
echo "  'Successfully pushed data via WebSocket to 1 connections'"
echo "  → WebSocket is working! ✓"
echo ""
echo "If you see:"
echo "  'Registered WebSocket: Home Assistant'"
echo "  → Registration was successful! ✓"
echo ""

