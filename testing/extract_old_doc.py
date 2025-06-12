#!/usr/bin/env python3
"""
Extract text from old .doc format files
"""

import os
import sys

def extract_doc_text(file_path):
    """Extract text from .doc file using available methods"""
    
    # Method 1: Try textract
    try:
        import textract
        text = textract.process(file_path, method='antiword')
        return text.decode('utf-8')
    except ImportError:
        print("textract not available, trying other methods...")
    except Exception as e:
        print(f"textract failed: {e}")
    
    # Method 2: Try python-docx2txt
    try:
        import docx2txt
        text = docx2txt.process(file_path)
        if text:
            return text
    except ImportError:
        print("docx2txt not available, trying other methods...")
    except Exception as e:
        print(f"docx2txt failed: {e}")
    
    # Method 3: Try antiword directly if available
    try:
        import subprocess
        result = subprocess.run(['antiword', file_path], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        print(f"antiword failed: {e}")
    
    # Method 4: Try catdoc if available
    try:
        import subprocess
        result = subprocess.run(['catdoc', file_path], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        print(f"catdoc failed: {e}")
    
    return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_old_doc.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    text = extract_doc_text(file_path)
    if text:
        print("Successfully extracted text:")
        print("=" * 50)
        print(text)
    else:
        print("Failed to extract text from the document") 