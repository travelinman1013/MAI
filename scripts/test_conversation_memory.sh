#!/bin/bash
#
# Manual integration test for conversation memory
# Tests multi-turn conversation memory with the chat agent
#

set -e

API_URL="http://localhost:8000/api/v1/agents"
SESSION_ID="manual-test-$(date +%s)"

echo "======================================"
echo "Conversation Memory Integration Test"
echo "======================================"
echo ""
echo "Session ID: $SESSION_ID"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Set context - name
echo -e "${YELLOW}Test 1: Setting context (name)${NC}"
echo "User: My name is Maxwell"
RESPONSE=$(curl -s -X POST "$API_URL/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"My name is Maxwell\", \"session_id\": \"$SESSION_ID\"}")
echo "Assistant: $RESPONSE"
echo ""
sleep 2

# Test 2: Set context - preference
echo -e "${YELLOW}Test 2: Setting context (preference)${NC}"
echo "User: My favorite number is 42"
RESPONSE=$(curl -s -X POST "$API_URL/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"My favorite number is 42\", \"session_id\": \"$SESSION_ID\"}")
echo "Assistant: $RESPONSE"
echo ""
sleep 2

# Test 3: Recall name
echo -e "${YELLOW}Test 3: Recalling name${NC}"
echo "User: What is my name?"
RESPONSE=$(curl -s -X POST "$API_URL/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What is my name?\", \"session_id\": \"$SESSION_ID\"}")
echo "Assistant: $RESPONSE"
echo ""

# Check if response contains "Maxwell"
if echo "$RESPONSE" | grep -qi "maxwell"; then
  echo -e "${GREEN}✓ Name recall PASSED${NC}"
else
  echo -e "${RED}✗ Name recall FAILED - 'Maxwell' not found in response${NC}"
fi
echo ""
sleep 2

# Test 4: Recall preference
echo -e "${YELLOW}Test 4: Recalling favorite number${NC}"
echo "User: What is my favorite number?"
RESPONSE=$(curl -s -X POST "$API_URL/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What is my favorite number?\", \"session_id\": \"$SESSION_ID\"}")
echo "Assistant: $RESPONSE"
echo ""

# Check if response contains "42"
if echo "$RESPONSE" | grep -q "42"; then
  echo -e "${GREEN}✓ Favorite number recall PASSED${NC}"
else
  echo -e "${RED}✗ Favorite number recall FAILED - '42' not found in response${NC}"
fi
echo ""
sleep 2

# Test 5: Check stored history
echo -e "${YELLOW}Test 5: Checking stored history${NC}"
HISTORY=$(curl -s "$API_URL/history/$SESSION_ID")
echo "History response:"
echo "$HISTORY" | python3 -m json.tool 2>/dev/null || echo "$HISTORY"
echo ""

# Count messages in history
MESSAGE_COUNT=$(echo "$HISTORY" | grep -o '"role"' | wc -l | tr -d ' ')
if [ "$MESSAGE_COUNT" -ge 8 ]; then
  echo -e "${GREEN}✓ History storage PASSED (found $MESSAGE_COUNT messages)${NC}"
else
  echo -e "${RED}✗ History storage FAILED (expected at least 8 messages, found $MESSAGE_COUNT)${NC}"
fi
echo ""

# Test 6: New session should not remember
echo -e "${YELLOW}Test 6: Testing session isolation (new session)${NC}"
NEW_SESSION="new-session-$(date +%s)"
echo "User (new session): What is my name?"
RESPONSE=$(curl -s -X POST "$API_URL/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What is my name?\", \"session_id\": \"$NEW_SESSION\"}")
echo "Assistant: $RESPONSE"
echo ""

# Check that response does NOT contain "Maxwell" (new session shouldn't remember)
if echo "$RESPONSE" | grep -qi "maxwell"; then
  echo -e "${RED}✗ Session isolation FAILED - new session remembered old context${NC}"
else
  echo -e "${GREEN}✓ Session isolation PASSED - new session has clean slate${NC}"
fi
echo ""

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"
echo "Original Session: $SESSION_ID"
echo "New Session: $NEW_SESSION"
echo ""
echo "Run these commands to inspect further:"
echo "  # View history for original session:"
echo "  curl -s \"$API_URL/history/$SESSION_ID\" | python3 -m json.tool"
echo ""
echo "  # View history for new session:"
echo "  curl -s \"$API_URL/history/$NEW_SESSION\" | python3 -m json.tool"
echo ""
echo "======================================"
