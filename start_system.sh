#!/bin/bash

# Resume Database System Startup Script
# Launches the complete system with all components

echo "🚀 Starting Resume Database System"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if database exists
if [ ! -f "resume_database.db" ]; then
    echo -e "${YELLOW}[!]${NC} Database not found. Creating new database..."
    
    # Run the extractor to create database
    if [ -f "resume_extractor.py" ]; then
        python3 resume_extractor.py
        echo -e "${GREEN}[✓]${NC} Database created and populated"
    else
        echo -e "${RED}[✗]${NC} resume_extractor.py not found!"
        exit 1
    fi
else
    echo -e "${GREEN}[✓]${NC} Database found: resume_database.db"
fi

# Check if we need to integrate existing app data
echo ""
echo -e "${BLUE}[?]${NC} Do you want to import data from your existing resume template app? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    python3 integrate_existing_app.py
fi

# Install/Update Python dependencies
echo ""
echo -e "${BLUE}[i]${NC} Checking Python dependencies..."
pip3 install -r requirements.txt --quiet

# Start the Flask backend
echo ""
echo -e "${GREEN}[✓]${NC} Starting Flask backend API..."
echo -e "${BLUE}[i]${NC} Backend will run at: http://localhost:5000"
echo ""

# Open the browser after a short delay
(sleep 3 && open http://localhost:5000) &

# Start Flask app
python3 app.py 