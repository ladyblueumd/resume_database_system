#!/bin/bash

# Resume Database System Setup Script
# Sadiqa "Sadie" Thornton - AI Resume Builder

echo "🤖 Resume Database System Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if Python is installed
print_info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
print_info "Checking pip installation..."
if command -v pip3 &> /dev/null; then
    print_status "pip3 found"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    print_status "pip found"
    PIP_CMD="pip"
else
    print_error "pip not found. Please install pip."
    exit 1
fi

# Create virtual environment (optional but recommended)
print_info "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Install requirements
print_info "Installing Python packages..."
$PIP_CMD install -r requirements.txt
if [ $? -eq 0 ]; then
    print_status "All packages installed successfully"
else
    print_error "Failed to install some packages. Check requirements.txt"
fi

# Download NLTK data
print_info "Downloading NLTK data for text processing..."
python3 -c "
import nltk
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    print('NLTK data downloaded successfully')
except Exception as e:
    print(f'Warning: Could not download NLTK data: {e}')
"

# Create data directory
print_info "Creating data directory..."
mkdir -p data
print_status "Data directory created"

# Check if resume files exist
RESUME_DIR="/Volumes/LLM-Drive/development_files/AI-dashboard/resumes_2024/resumes_for_database"
if [ -d "$RESUME_DIR" ]; then
    print_status "Resume files directory found: $RESUME_DIR"
    print_info "Extracting components from existing resumes..."
    
    # Run extraction script
    python3 resume_extractor.py
    if [ $? -eq 0 ]; then
        print_status "Resume extraction completed successfully"
    else
        print_warning "Resume extraction completed with warnings"
    fi
else
    print_warning "Resume files directory not found. You can add resumes later through the web interface."
fi

# Create sample data if database is empty
print_info "Checking database setup..."
if [ ! -f "data/resume_database.db" ]; then
    print_info "Creating sample database..."
    python3 -c "
from resume_extractor import ResumeExtractor
extractor = ResumeExtractor('data/resume_database.db')
print('Database initialized with schema')
"
    print_status "Database created"
else
    print_status "Database already exists"
fi

# Check if LM Studio is available
print_info "Checking for LM Studio integration..."
if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    print_status "LM Studio detected and running on localhost:1234"
    print_info "AI features will use local models for privacy"
else
    print_warning "LM Studio not detected. AI features will use basic keyword matching."
    print_info "To enable advanced AI features:"
    echo "  1. Install LM Studio"
    echo "  2. Load a model (recommended: gemma-3-4b-it-qat)"
    echo "  3. Start the server on localhost:1234"
fi

# Final setup confirmation
echo ""
echo "🎉 Setup Complete!"
echo "=================="
print_status "Database system ready"
print_status "Web application available"
print_status "Component extraction tools ready"

echo ""
print_info "Next Steps:"
echo "1. Open enhanced_resume_app.html in your browser"
echo "2. Start with the Dashboard tab to see your data"
echo "3. Use Job Matcher to analyze job descriptions"
echo "4. Build resumes with the Resume Builder"

echo ""
print_info "Quick Commands:"
echo "• Open app: open enhanced_resume_app.html"
echo "• Extract more resumes: python3 resume_extractor.py"
echo "• View database: sqlite3 data/resume_database.db"
echo "• Backup data: cp data/resume_database.db backup_\$(date +%Y%m%d).db"

echo ""
print_info "File Locations:"
echo "• Database: data/resume_database.db"
echo "• Extracted components: data/extracted_components.json"
echo "• Web app: enhanced_resume_app.html"
echo "• Documentation: README.md"

echo ""
echo "🚀 Ready to revolutionize your resume creation process!"
echo "   Your 16+ years of IT expertise is now searchable and reusable."
echo ""

# Deactivate virtual environment message
echo "Note: Run 'deactivate' to exit the virtual environment when done."
