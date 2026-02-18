#!/bin/bash
# =============================================================================
# madOS Persistence Tests - Easy Runner
# =============================================================================
# Quick script to run all persistence tests
# =============================================================================

set -euo pipefail

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     madOS Persistence Tests - Easy Runner                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

# Check if we're in the repo
if [ ! -f "Dockerfile.test" ]; then
    echo -e "${RED}Error: Must run from madOS repo root${NC}"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found, running tests directly...${NC}"
    
    # Run tests directly
    if [ ! -x "$(command -v pytest)" ]; then
        echo -e "${RED}Error: pytest not found. Install with: pip install pytest pytest-cov${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Running tests directly...${NC}"
    pytest tests/ -v --tb=short
    exit $?
fi

echo -e "${BLUE}Building test Docker image...${NC}"
docker build -f Dockerfile.test -t mados-test .

echo -e "${BLUE}Running tests in Docker container...${NC}"
docker run --rm -v "$(pwd)":/build mados-test

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                  ALL TESTS COMPLETED SUCCESSFULLY              ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
