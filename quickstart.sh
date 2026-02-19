#!/bin/bash
# Quickstart script for Anki Card Creator
# Usage: ./quickstart.sh

echo "=================================="
echo "ANKI CARD CREATOR - QUICKSTART"
echo "=================================="
echo ""

# Activate virtual environment
source .venv/bin/activate

# Check if local database exists and has data
if [ -f "local.db" ]; then
    echo "✓ Local database found"
    SQLITE_SIZE=$(ls -lh local.db | awk '{print $5}')
    echo "  Size: $SQLITE_SIZE"
else
    echo "⚠ Local database not found. Importing..."
    python import_optimized.py
fi

# Run verification tests
echo ""
echo "=== Running Verification Tests ==="
python final_test.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Tests failed. Please check errors above."
    exit 1
fi

# Start the app
echo ""
echo "=================================="
echo "STARTING APPLICATION"
echo "=================================="
echo ""
echo "The app will be available at:"
echo "  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py
