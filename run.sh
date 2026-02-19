#!/bin/bash
# Run Anki Card Creator with Supabase

echo "=================================="
echo "ANKI CARD CREATOR"
echo "=================================="
echo ""
echo "Mode: Supabase (Production)"
echo "URL: http://localhost:5000"
echo ""
echo "Admin login:"
echo "  Email: admin@anki-cards.com"
echo "  Password: admin123"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================="
echo ""

source .venv/bin/activate
export USE_LOCAL_DB=false
python app.py
