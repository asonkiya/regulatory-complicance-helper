#!/usr/bin/env bash
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}Accessibility Copilot — First-time setup${NC}"
echo "----------------------------------------"

# 1. Check Docker
if ! command -v docker &>/dev/null; then
  echo -e "${RED}Docker is not installed.${NC}"
  echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/ then re-run this script."
  exit 1
fi

if ! docker info &>/dev/null; then
  echo -e "${RED}Docker daemon is not running.${NC}"
  echo "Open Docker Desktop and wait for it to start, then re-run this script."
  exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# 2. Copy .env if needed
if [ ! -f .env ]; then
  cp .env.example .env
  echo -e "${GREEN}✓ Created .env from .env.example${NC}"
else
  echo -e "${YELLOW}! .env already exists — skipping copy${NC}"
fi

# 3. Prompt for Anthropic API key
if grep -q "your_anthropic_api_key_here" .env; then
  echo ""
  echo -e "${BOLD}You need an Anthropic API key for AI features (alt text, transcript cleaning, document titles).${NC}"
  echo "Get one at https://console.anthropic.com/ → API Keys"
  echo ""
  read -rp "Paste your Anthropic API key: " api_key
  if [ -z "$api_key" ]; then
    echo -e "${YELLOW}! No key entered. You can add it later by editing .env (ANTHROPIC_API_KEY=sk-ant-...).${NC}"
    echo -e "${YELLOW}  AI features won't work until you do.${NC}"
  else
    # Replace the placeholder value
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s|ANTHROPIC_API_KEY=your_anthropic_api_key_here|ANTHROPIC_API_KEY=${api_key}|" .env
    else
      sed -i "s|ANTHROPIC_API_KEY=your_anthropic_api_key_here|ANTHROPIC_API_KEY=${api_key}|" .env
    fi
    echo -e "${GREEN}✓ API key saved to .env${NC}"
  fi
else
  echo -e "${GREEN}✓ Anthropic API key already set${NC}"
fi

# 4. Build and start
echo ""
echo -e "${BOLD}Building and starting all services (this takes a few minutes the first time)...${NC}"
echo ""
docker compose up --build -d

# 5. Wait for backend to be ready
echo ""
echo "Waiting for backend to be ready..."
attempt=0
max_attempts=30
until curl -sf http://localhost:8000/health &>/dev/null || [ $attempt -ge $max_attempts ]; do
  sleep 3
  attempt=$((attempt + 1))
  echo -n "."
done
echo ""

if [ $attempt -ge $max_attempts ]; then
  echo -e "${YELLOW}Backend is taking a while — it may still be running migrations.${NC}"
  echo "Check progress with: docker compose logs backend"
else
  echo -e "${GREEN}✓ Backend is up${NC}"
fi

# 6. Done
echo ""
echo -e "${GREEN}${BOLD}Setup complete!${NC}"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  API docs:  http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f          # stream all logs"
echo "  docker compose logs -f backend  # backend only"
echo "  docker compose down             # stop everything"
echo "  docker compose down -v          # stop + wipe database"
echo ""
