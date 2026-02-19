#!/bin/bash
# Run locally with SQLite
echo "Starting Anki Card Creator (Local Mode)..."
echo "URL: http://localhost:5000"
echo ""
source .venv/bin/activate
export USE_LOCAL_DB=true
python app.py
