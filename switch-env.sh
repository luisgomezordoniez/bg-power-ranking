#!/bin/bash
# switch-env.sh — swap between dev and prod config
# Usage:
#   ./switch-env.sh dev   → use DEV Apps Script URL (for local testing)
#   ./switch-env.sh prod  → use PROD Apps Script URL (before committing)

ENV=$1

if [ -z "$ENV" ]; then
  echo "Usage: ./switch-env.sh [dev|prod]"
  echo ""
  # Show current state
  CURRENT=$(grep 'API_URL' config.js | head -1)
  echo "Current config.js: $CURRENT"
  exit 0
fi

if [ "$ENV" = "dev" ]; then
  if [ ! -f config.dev.js ]; then
    echo "Error: config.dev.js not found."
    echo "Create it with your DEV Apps Script URL:"
    echo '  echo '\''const API_URL = "YOUR_DEV_URL";'\'' > config.dev.js'
    exit 1
  fi
  cp config.dev.js config.js
  echo "✓ Switched to DEV"
  echo "  Open files locally: open index.html"
  echo "  Remember: run './switch-env.sh prod' before committing!"

elif [ "$ENV" = "prod" ]; then
  if [ ! -f config.prod.js ]; then
    echo "Error: config.prod.js not found."
    echo "Create it with your PROD Apps Script URL:"
    echo '  echo '\''const API_URL = "YOUR_PROD_URL";'\'' > config.prod.js'
    exit 1
  fi
  cp config.prod.js config.js
  echo "✓ Switched to PROD"
  echo "  Safe to commit and push."

else
  echo "Unknown environment: $ENV"
  echo "Usage: ./switch-env.sh [dev|prod]"
  exit 1
fi
