#!/bin/bash
# Test script for LLM providers
# Usage: ./scripts/test_providers.sh [provider]

set -e

API_URL="${API_URL:-http://localhost:8000}"
PROVIDER="${1:-auto}"

echo "Testing LLM Provider: $PROVIDER"
echo "API URL: $API_URL"
echo "================================"

# Check API health
echo -n "API Health: "
curl -sf "$API_URL/api/health" > /dev/null && echo "OK" || echo "FAILED"

# Check LLM status
echo -n "LLM Status: "
STATUS=$(curl -sf "$API_URL/api/llm-status")
CONNECTED=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['connected'])")
MODEL=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model_name', 'None'))")
echo "Connected=$CONNECTED, Model=$MODEL"

# List providers
echo -e "\nAvailable Providers:"
curl -sf "$API_URL/api/models/providers" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data['providers']:
    status = '✓' if p['connected'] else '✗'
    print(f\"  {status} {p['name']}: {p.get('model', 'N/A')}\")
"

# List models
echo -e "\nAvailable Models:"
curl -sf "$API_URL/api/models/" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data['models']:
    print(f\"  - {m['id']} ({m['provider']})\")
" 2>/dev/null || echo "  (no models or provider unavailable)"

echo -e "\n================================"
echo "Test complete!"
