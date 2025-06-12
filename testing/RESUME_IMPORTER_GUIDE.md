# Resume Importer Guide

## Overview
The Resume Importer is a powerful feature that automatically extracts and categorizes components from your resume, making it easy to build a comprehensive database of your professional experience.

## Features

### 🔍 Intelligent Parsing
The system automatically identifies and extracts:
- **Professional Summary** - Career overview and key strengths
- **Technical Skills** - Programming languages, tools, platforms
- **Professional Skills** - Soft skills and core competencies  
- **Work Experience** - Job roles, companies, and achievements
- **Education** - Degrees, institutions, and academic details
- **Certifications** - Professional credentials and licenses
- **Projects** - Notable projects and accomplishments

### 📥 Multiple Import Methods

#### Method 1: Text Paste
1. Copy your resume text to clipboard
2. Go to Dashboard tab
3. Paste text in the "Resume Text" area
4. Click "Parse Resume Text"
5. Review extracted components
6. Select components to import
7. Click "Import Selected"

#### Method 2: File Upload (FIXED!)
**✅ Now supports .doc, .docx, .pdf, .txt files**

**Recent Fix (May 31, 2025)**: Fixed .doc file processing that was extracting 0 components
- Added proper text extraction for Microsoft Word .doc files
- Uses macOS `textutil` command for reliable .doc processing
- Also supports .docx via python-docx library
- PDF support via PyPDF2
- Enhanced error handling and validation

**Upload Process:**
1. Go to Dashboard tab
2. Click the file upload area or "Choose File"
3. Select your resume file (.doc, .docx, .pdf, .txt)
4. File is automatically processed after selection
5. Review extracted components
6. Select components to import
7. Click "Import Selected"

## Supported File Formats

| Format | Library/Method | Status |
|--------|---------------|--------|
| .txt   | Native Python | ✅ Working |
| .docx  | python-docx   | ✅ Working |
| .doc   | macOS textutil | ✅ Working |
| .pdf   | PyPDF2        | ✅ Working |
| .html  | Native parsing | ✅ Working |

## Troubleshooting

### If file upload shows "0 components extracted":
1. **Check file format** - Ensure file is .doc, .docx, .pdf, or .txt
2. **Check file content** - File must contain readable text (not just images)
3. **Try text paste method** - Copy text manually and use paste method
4. **Check file size** - Very large files may timeout
5. **Convert format** - Try saving as .txt or .docx if having issues

### If components aren't detected:
1. **Check section headers** - Use standard headers like "EXPERIENCE", "SKILLS", "EDUCATION"
2. **Format consistently** - Use clear formatting with line breaks between sections
3. **Review extracted text** - Check if text was extracted correctly from file

## Example Resume Structure

```
PROFESSIONAL SUMMARY
Experienced IT Professional with 10+ years...

TECHNICAL SKILLS
Windows Server, Active Directory, Python, SQL

WORK EXPERIENCE
Senior Desktop Support Specialist
Tech Corp - Jan 2020 to Present
• Managed 500+ workstations
• Implemented automated solutions

EDUCATION
Bachelor of Science in Information Technology
State University - 2018

CERTIFICATIONS
CompTIA A+, Network+, Security+
```

## Component Selection Tips

- **Select relevant components** - Choose items that match your target roles
- **Review before importing** - Read through extracted text for accuracy
- **Edit after import** - Components can be edited in the Component Library
- **Use descriptive titles** - Components get auto-titled based on content

## Integration

Imported components automatically appear in:
- **Component Library** - For browsing and editing
- **Job Matcher** - For finding relevant components for positions
- **Resume Builder** - For creating targeted resumes

---

*Last updated: May 31, 2025 - Fixed .doc file processing* 