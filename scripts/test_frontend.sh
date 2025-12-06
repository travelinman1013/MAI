#!/bin/bash
# Frontend integration test script

set -e  # Exit on error

echo "============================================"
echo "MAI Frontend Integration Test Suite"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

echo "Step 1: Running unit tests with pytest..."
echo "==========================================="
if poetry run pytest tests/gui/test_frontend_integration.py -v; then
    echo -e "${GREEN}Unit tests: PASSED${NC}"
else
    echo -e "${RED}Unit tests: FAILED${NC}"
    exit 1
fi
echo ""

echo "Step 2: Checking Python imports..."
echo "==========================================="
if poetry run python -c "from src.gui.app import create_chat_interface; from src.gui.api_client import MAIClient; from src.gui.theme import create_mai_theme; from src.core.documents.processor import DocumentProcessor; print('All imports successful')"; then
    echo -e "${GREEN}Import check: PASSED${NC}"
else
    echo -e "${RED}Import check: FAILED${NC}"
    exit 1
fi
echo ""

echo "Step 3: Verifying API endpoints (if server is running)..."
echo "==========================================="
# Check if API is available
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}API health endpoint: ACCESSIBLE${NC}"

    # Check specific endpoints
    if curl -s http://localhost:8000/api/v1/agents/ > /dev/null 2>&1; then
        echo -e "${GREEN}Agents endpoint: ACCESSIBLE${NC}"
    else
        echo -e "${YELLOW}Agents endpoint: NOT ACCESSIBLE${NC}"
    fi

    if curl -s http://localhost:8000/api/v1/models/ > /dev/null 2>&1; then
        echo -e "${GREEN}Models endpoint: ACCESSIBLE${NC}"
    else
        echo -e "${YELLOW}Models endpoint: NOT ACCESSIBLE${NC}"
    fi
else
    echo -e "${YELLOW}API server not running (this is OK for unit tests)${NC}"
fi
echo ""

echo "Step 4: Checking GUI accessibility..."
echo "==========================================="
# Check if GUI is running
if curl -s http://localhost:7860 > /dev/null 2>&1; then
    echo -e "${GREEN}GUI is accessible at http://localhost:7860${NC}"
else
    echo -e "${YELLOW}GUI is not running (start with 'docker compose up')${NC}"
fi
echo ""

echo "Step 5: Verifying configuration..."
echo "==========================================="
if poetry run python -c "from src.gui.config import gui_settings; assert hasattr(gui_settings, 'max_document_size_mb'); assert hasattr(gui_settings, 'enable_model_switching'); print('Configuration OK')"; then
    echo -e "${GREEN}Configuration check: PASSED${NC}"
else
    echo -e "${RED}Configuration check: FAILED${NC}"
    exit 1
fi
echo ""

echo "============================================"
echo -e "${GREEN}All tests completed successfully!${NC}"
echo "============================================"
echo ""
echo "Summary:"
echo "  - Unit tests: PASSED"
echo "  - Import check: PASSED"
echo "  - Configuration: PASSED"
echo ""
echo "To run the full application:"
echo "  docker compose up -d"
echo "  Open http://localhost:7860"
echo ""
