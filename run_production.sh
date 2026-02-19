#!/bin/bash
# Run with Supabase (set USE_LOCAL_DB=false in .env)
echo "Starting Anki Card Creator (Production Mode)..."
echo "URL: http://localhost:5000"
echo ""
source .venv/bin/activate
export USE_LOCAL_DB=false
python app.py
