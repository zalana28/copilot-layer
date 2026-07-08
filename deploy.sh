#!/usr/bin/env bash
# Deploy Copilot Layer MCP backend to Railway.
# Manual prerequisite: `railway login` (opens browser, needs your account).
set -e
cd "$(dirname "$0")"

echo "== Copilot Layer deploy =="
# 1. Install Railway CLI if missing
if ! command -v railway >/dev/null 2>&1; then
  echo "[1/4] Installing Railway CLI..."
  npm i -g @railway/cli
else
  echo "[1/4] Railway CLI already present."
fi

# 2. Link / init project (interactive only if no project yet)
echo "[2/4] Linking project..."
if [ ! -f "railway.json" ] && [ ! -d ".railway" ]; then
  railway init --name "copilot-layer" || true
else
  railway link || true
fi

# 3. Deploy
echo "[3/4] Deploying..."
railway up --detach

# 4. Get public domain
echo "[4/4] Fetching public domain..."
sleep 5
DOMAIN=$(railway domain 2>/dev/null | tail -1 || true)
echo "----------------------------------------"
if [ -n "$DOMAIN" ]; then
  echo "DEPLOYED URL: $DOMAIN"
  echo "MCP endpoint: $DOMAIN/mcp"
  echo "Healthcheck:  $DOMAIN/health"
else
  echo "Domain not auto-assigned. Get it from https://railway.app -> your project -> Settings -> Domains"
fi
echo "----------------------------------------"
echo "Copy the URL above and send it to din (Hermes) to update the A2MCP endpoint on OKX #4625."
