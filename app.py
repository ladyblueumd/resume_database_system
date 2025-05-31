#!/usr/bin/env python3
"""
Flask Backend API for Resume Database System
Provides REST endpoints for frontend to interact with SQLite database
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import requests
from urllib.parse import urlparse
import tempfile
from werkzeug.utils import secure_filename
import docx
import PyPDF2
import subprocess

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=['*'])  # Allow CORS for local development

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'resume_database.db')

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'html'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize AI model for semantic matching
try:
    semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Semantic model loaded successfully")
except Exception as e:
    logger.warning(f"Could not load semantic model: {e}. Falling back to keyword matching.")
    semantic_model = None


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn


def dict_from_row(row):
    """Convert a sqlite3.Row to a dictionary"""
    return dict(zip(row.keys(), row))


# Resume parsing functions
def parse_resume_text(text: str) -> Dict[str, List[str]]:
    """
    Enhanced resume text parser that extracts complete sections based on headers
    """
    components = {
        'professional_summary': [],
        'technical_skills': [],
        'professional_skills': [],
        'work_experience': [],
        'education': [],
        'certifications': [],
        'projects': [],
        'contact_info': [],
        'other_sections': []
    }
    
    # Clean and normalize text
    text = re.sub(r'\r\n', '\n', text)  # Normalize line endings
    text = re.sub(r'\n{3,}', '\n\n', text)  # Reduce excessive line breaks
    lines = [line.rstrip() for line in text.split('\n')]
    
    # Detect sections by finding lines that look like headers
    sections = []
    current_section = None
    current_content = []
    
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        # Skip empty lines
        if not stripped_line:
            if current_content and current_content[-1].strip():  # Don't add multiple empty lines
                current_content.append(line)
            continue
        
        # Check if this line looks like a header
        is_header = detect_section_header(stripped_line, i, lines)
        
        if is_header:
            # Save previous section if it exists
            if current_section is not None and current_content:
                sections.append({
                    'header': current_section,
                    'content': '\n'.join(current_content).strip(),
                    'line_start': len(sections)
                })
            
            # Start new section
            current_section = stripped_line
            current_content = []
        else:
            # Add to current section
            current_content.append(line)
    
    # Don't forget the last section
    if current_section is not None and current_content:
        sections.append({
            'header': current_section,
            'content': '\n'.join(current_content).strip(),
            'line_start': len(sections)
        })
    
    # Categorize sections based on their headers and content
    for section in sections:
        header = section['header'].lower()
        content = section['content']
        category = categorize_section(header, content)
        
        if category and content.strip():
            # Create a complete component with header and content
            full_component = f"{section['header']}\n{content}"
            components[category].append(full_component)
    
    # Remove empty sections
    components = {k: v for k, v in components.items() if v}
    
    return components


def detect_section_header(line: str, line_index: int, all_lines: list) -> bool:
    """
    Detect if a line looks like a section header
    """
    # Skip very short lines
    if len(line.strip()) < 2:
        return False
    
    # Common header patterns
    header_indicators = [
        # All caps headers
        lambda l: l.isupper() and len(l.split()) <= 5 and not any(char.isdigit() for char in l),
        
        # Headers that end with colons
        lambda l: l.endswith(':') and len(l.split()) <= 4,
        
        # Company name patterns (contains Corp, Inc, LLC, etc.)
        lambda l: any(indicator in l.upper() for indicator in ['CORP', 'INC', 'LLC', 'COMPANY', 'TECHNOLOGIES', 'SYSTEMS', 'GROUP', 'ASSOCIATES']),
        
        # Job title patterns (standalone titles that are likely headers)
        lambda l: any(title in l.lower() for title in ['president', 'manager', 'specialist', 'technician', 'engineer', 'analyst', 'director', 'coordinator', 'representative']) and len(l.split()) <= 4,
        
        # Educational institution patterns
        lambda l: any(edu in l.lower() for edu in ['university', 'college', 'school', 'institute', 'academy']) and len(l.split()) <= 6,
        
        # Common section headers
        lambda l: any(section in l.lower().replace(' ', '') for section in [
            'experience', 'employment', 'workhistory', 'careerhis',
            'education', 'academic', 'qualifications', 'degrees',
            'skills', 'competencies', 'expertise', 'abilities',
            'certifications', 'certificates', 'licenses', 'credentials',
            'projects', 'portfolio', 'achievements', 'accomplishments',
            'summary', 'profile', 'objective', 'overview',
            'contact', 'contactinfo', 'personalinfo'
        ]),
        
        # Date range patterns (might be job duration headers)
        lambda l: bool(re.search(r'\b(19|20)\d{2}\s*[-–—]\s*(19|20)\d{2}\b', l)) or 
                 bool(re.search(r'\b(19|20)\d{2}\s*[-–—]\s*present\b', l, re.I)),
        
        # Location patterns (City, State format)
        lambda l: bool(re.search(r'^[A-Z][a-z]+,\s*[A-Z]{2}(\s+\d{5})?$', l.strip())),
    ]
    
    # Check if line matches any header pattern
    for indicator in header_indicators:
        try:
            if indicator(line):
                return True
        except:
            continue
    
    # Additional context-based checks
    if line_index < len(all_lines) - 1:
        next_line = all_lines[line_index + 1].strip()
        
        # If next line starts with bullet points or dashes, current line might be header
        if next_line and (next_line.startswith('•') or next_line.startswith('-') or next_line.startswith('*')):
            return True
        
        # If current line is shorter and next line is much longer, might be a header
        if len(line) < 50 and len(next_line) > 80:
            return True
    
    return False


def categorize_section(header: str, content: str) -> str:
    """
    Categorize a section based on its header and content
    """
    header_lower = header.lower()
    content_lower = content.lower()
    combined = f"{header_lower} {content_lower}"
    
    # Professional summary indicators
    if any(keyword in header_lower for keyword in ['summary', 'profile', 'objective', 'overview', 'about']):
        return 'professional_summary'
    
    # Technical skills indicators
    if any(keyword in header_lower for keyword in ['technical', 'computer', 'software', 'programming', 'technology', 'platform', 'tool']):
        return 'technical_skills'
    
    # Professional skills indicators  
    if any(keyword in header_lower for keyword in ['skill', 'competenc', 'abilit', 'strength', 'expertise']) and 'technical' not in header_lower:
        return 'professional_skills'
    
    # Work experience indicators
    if any(keyword in header_lower for keyword in ['experience', 'employment', 'work', 'career', 'history']):
        return 'work_experience'
    
    # Company names and job titles are usually work experience
    if any(indicator in header_lower for indicator in ['corp', 'inc', 'llc', 'company', 'technologies', 'systems']):
        return 'work_experience'
    
    if any(title in header_lower for title in ['president', 'manager', 'specialist', 'technician', 'engineer', 'analyst', 'director', 'coordinator', 'representative']):
        return 'work_experience'
    
    # Education indicators
    if any(keyword in header_lower for keyword in ['education', 'academic', 'degree', 'university', 'college', 'school']):
        return 'education'
    
    # Certification indicators
    if any(keyword in header_lower for keyword in ['certification', 'certificate', 'license', 'credential', 'accreditation']):
        return 'certifications'
    
    # Project indicators
    if any(keyword in header_lower for keyword in ['project', 'portfolio', 'achievement', 'accomplishment']):
        return 'projects'
    
    # Contact info indicators
    if any(keyword in header_lower for keyword in ['contact', 'phone', 'email', 'address', 'linkedin']):
        return 'contact_info'
    
    # Content-based categorization for unclear headers
    if any(keyword in content_lower for keyword in ['managed', 'developed', 'implemented', 'led', 'coordinated', 'supervised', 'responsible for']):
        return 'work_experience'
    
    if any(keyword in content_lower for keyword in ['bachelor', 'master', 'phd', 'degree', 'graduated', 'gpa']):
        return 'education'
    
    if any(keyword in content_lower for keyword in ['certified', 'licensed', 'comptia', 'microsoft certified', 'cisco']):
        return 'certifications'
    
    # If we can't categorize it, put it in other_sections
    return 'other_sections'


def extract_text_from_file(filepath: str, filename: str) -> str:
    """Extract text from various file formats"""
    try:
        file_ext = filename.lower().split('.')[-1]
        
        if file_ext in ['txt', 'text']:
            # Plain text file
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        elif file_ext == 'docx':
            # Word 2007+ format
            doc = docx.Document(filepath)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text)
            
        elif file_ext == 'doc':
            # Older Word format - try using system commands
            try:
                # Try using antiword if available (common on macOS/Linux)
                result = subprocess.run(['antiword', filepath], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            try:
                # Try using textutil (macOS specific)
                result = subprocess.run(['textutil', '-convert', 'txt', '-stdout', filepath], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # If all else fails, try to read as plain text (may not work well)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Remove control characters and clean up
                    import string
                    printable = set(string.printable)
                    content = ''.join(filter(lambda x: x in printable, content))
                    return content if len(content.strip()) > 50 else None
            except:
                pass
                
        elif file_ext == 'pdf':
            # PDF format
            text = []
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
            
        elif file_ext == 'html':
            # HTML format - strip tags
            from html import unescape
            import re
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', html_content)
                # Decode HTML entities
                text = unescape(text)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                return text
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting text from {filename}: {e}")
        return None


# API Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': os.path.exists(DATABASE_PATH),
        'semantic_model': semantic_model is not None
    })


@app.route('/api/components', methods=['GET'])
def get_components():
    """Get all resume components with optional filtering"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get query parameters
        section_type = request.args.get('section_type')
        search_query = request.args.get('q')
        limit = request.args.get('limit', 100, type=int)
        
        # Build query
        query = """
            SELECT rc.*, st.name as section_type_name
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            WHERE 1=1
        """
        params = []
        
        if section_type:
            query += " AND st.name = ?"
            params.append(section_type)
        
        if search_query:
            query += " AND (rc.title LIKE ? OR rc.content LIKE ? OR rc.keywords LIKE ?)"
            search_pattern = f'%{search_query}%'
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY rc.usage_count DESC, rc.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        components = [dict_from_row(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(components)
        
    except Exception as e:
        logger.error(f"Error fetching components: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/components', methods=['POST'])
def create_component():
    """Create a new resume component"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get section type ID
        cursor.execute("SELECT id FROM section_types WHERE name = ?", (data['section_type'],))
        section_type_row = cursor.fetchone()
        if not section_type_row:
            return jsonify({'error': 'Invalid section type'}), 400
        
        section_type_id = section_type_row['id']
        
        # Insert component
        cursor.execute("""
            INSERT INTO resume_components 
            (section_type_id, title, content, keywords, industry_tags, skill_level, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            section_type_id,
            data['title'],
            data['content'],
            data.get('keywords', ''),
            data.get('industry_tags', ''),
            data.get('skill_level', 'intermediate'),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        component_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': component_id, 'message': 'Component created successfully'}), 201
        
    except Exception as e:
        logger.error(f"Error creating component: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/components/<int:component_id>', methods=['GET'])
def get_component(component_id):
    """Get a specific resume component"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rc.*, st.name as section_type_name
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            WHERE rc.id = ?
        """, (component_id,))
        
        component = cursor.fetchone()
        conn.close()
        
        if not component:
            return jsonify({'error': 'Component not found'}), 404
        
        return jsonify(dict_from_row(component))
        
    except Exception as e:
        logger.error(f"Error fetching component: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/components/<int:component_id>', methods=['PUT'])
def update_component(component_id):
    """Update a resume component"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get section_type_id if section_type is provided
        section_type_id = None
        if 'section_type' in data:
            cursor.execute("SELECT id FROM section_types WHERE name = ?", (data['section_type'],))
            result = cursor.fetchone()
            if result:
                section_type_id = result[0]
            else:
                # If section type doesn't exist, create it
                cursor.execute("INSERT INTO section_types (name) VALUES (?)", (data['section_type'],))
                section_type_id = cursor.lastrowid
        
        # Update component - build query dynamically based on provided fields
        update_fields = []
        update_values = []
        
        if 'title' in data:
            update_fields.append("title = ?")
            update_values.append(data['title'])
            
        if 'content' in data:
            update_fields.append("content = ?")
            update_values.append(data['content'])
            
        if 'keywords' in data:
            update_fields.append("keywords = ?")
            update_values.append(data.get('keywords', ''))
            
        if 'industry_tags' in data:
            update_fields.append("industry_tags = ?")
            update_values.append(data.get('industry_tags', ''))
            
        if section_type_id:
            update_fields.append("section_type_id = ?")
            update_values.append(section_type_id)
        
        # Always update the timestamp
        update_fields.append("updated_at = ?")
        update_values.append(datetime.now().isoformat())
        
        # Add component_id for WHERE clause
        update_values.append(component_id)
        
        if update_fields:
            query = f"UPDATE resume_components SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'error': 'Component not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Component updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating component: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/components/<int:component_id>/usage', methods=['POST'])
def track_component_usage(component_id):
    """Track when a component is used in a resume"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Increment usage count
        cursor.execute("""
            UPDATE resume_components 
            SET usage_count = usage_count + 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), component_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Usage tracked'})
        
    except Exception as e:
        logger.error(f"Error tracking usage: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/job-matcher', methods=['POST'])
def match_job_description():
    """Analyze job description and find matching components"""
    try:
        data = request.json
        job_description = data.get('job_description', '')
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        # Get all components
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rc.*, st.name as section_type_name
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
        """)
        
        components = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        
        # Perform matching
        if semantic_model:
            # Use semantic similarity
            matches = semantic_match_components(job_description, components)
        else:
            # Fallback to keyword matching
            matches = keyword_match_components(job_description, components)
        
        # Extract keywords from job description
        keywords = extract_keywords(job_description)
        
        return jsonify({
            'keywords': keywords,
            'matches': matches[:20],  # Return top 20 matches
            'total_matches': len(matches)
        })
        
    except Exception as e:
        logger.error(f"Error in job matching: {e}")
        return jsonify({'error': str(e)}), 500


def semantic_match_components(job_description: str, components: List[Dict]) -> List[Dict]:
    """Use semantic similarity to match components to job description"""
    # Encode job description
    job_embedding = semantic_model.encode(job_description)
    
    # Encode all components
    component_texts = [f"{c['title']} {c['content']}" for c in components]
    component_embeddings = semantic_model.encode(component_texts)
    
    # Calculate similarities
    similarities = cosine_similarity([job_embedding], component_embeddings)[0]
    
    # Create matches with scores
    matches = []
    for i, (component, score) in enumerate(zip(components, similarities)):
        if score > 0.3:  # Threshold for relevance
            matches.append({
                'component': component,
                'score': float(score),
                'match_percentage': int(score * 100)
            })
    
    # Sort by score
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches


def keyword_match_components(job_description: str, components: List[Dict]) -> List[Dict]:
    """Use keyword matching to find relevant components"""
    keywords = extract_keywords(job_description)
    
    matches = []
    for component in components:
        score = 0
        component_text = f"{component['title']} {component['content']} {component.get('keywords', '')}".lower()
        
        for keyword in keywords:
            if keyword.lower() in component_text:
                score += 1
        
        if score > 0:
            matches.append({
                'component': component,
                'score': score,
                'match_percentage': min(100, int((score / len(keywords)) * 100))
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches


def extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords from text"""
    # Technical keywords relevant to IT/Desktop Support
    tech_keywords = [
        'windows', 'linux', 'macos', 'active directory', 'servicenow',
        'office365', 'microsoft 365', 'azure', 'aws', 'vmware', 'citrix',
        'desktop support', 'help desk', 'technical support', 'troubleshooting',
        'hardware', 'software', 'network', 'networking', 'vpn', 'security',
        'server', 'cloud', 'deployment', 'migration', 'imaging', 'sccm',
        'intune', 'jamf', 'bitlocker', 'powershell', 'scripting', 'automation',
        'itil', 'incident management', 'asset management', 'documentation',
        'customer service', 'communication', 'problem solving'
    ]
    
    found_keywords = []
    text_lower = text.lower()
    
    for keyword in tech_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    # Also extract any words that appear to be technologies (capitalized, contain numbers)
    potential_tech = re.findall(r'\b[A-Z][A-Za-z0-9]+\b', text)
    for tech in potential_tech[:10]:  # Limit to prevent spam
        if len(tech) > 2 and tech.lower() not in found_keywords:
            found_keywords.append(tech)
    
    return found_keywords


@app.route('/api/employment', methods=['GET'])
def get_employment_history():
    """Get all employment history records"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM employment_history
            ORDER BY start_date DESC
        """)
        
        employment = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(employment)
        
    except Exception as e:
        logger.error(f"Error fetching employment: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/employment', methods=['POST'])
def create_employment():
    """Create a new employment record"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO employment_history 
            (company_name, position_title, start_date, end_date, location, 
             employment_type, industry, responsibilities, achievements, 
             technologies_used, skills_gained, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['company_name'],
            data['position_title'],
            data.get('start_date'),
            data.get('end_date'),
            data.get('location', ''),
            data.get('employment_type', 'full-time'),
            data.get('industry', ''),
            json.dumps(data.get('responsibilities', [])),
            json.dumps(data.get('achievements', [])),
            json.dumps(data.get('technologies_used', [])),
            json.dumps(data.get('skills_gained', [])),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        employment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': employment_id, 'message': 'Employment record created'}), 201
        
    except Exception as e:
        logger.error(f"Error creating employment: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/job-descriptions', methods=['GET'])
def get_job_descriptions():
    """Get saved job descriptions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM job_descriptions
            ORDER BY created_at DESC
        """)
        
        jobs = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(jobs)
        
    except Exception as e:
        logger.error(f"Error fetching job descriptions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/job-descriptions', methods=['POST'])
def save_job_description():
    """Save a job description for future reference"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract keywords
        keywords = extract_keywords(data['job_description'])
        
        cursor.execute("""
            INSERT INTO job_descriptions 
            (company_name, position_title, job_description, keywords, 
             location, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['company_name'],
            data['position_title'],
            data['job_description'],
            json.dumps(keywords),
            data.get('location', ''),
            'saved',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': job_id, 'keywords': keywords}), 201
        
    except Exception as e:
        logger.error(f"Error saving job description: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/resumes', methods=['POST'])
def generate_resume():
    """Generate a resume from selected components"""
    try:
        data = request.json
        component_ids = data.get('component_ids', [])
        job_id = data.get('job_id')
        title = data.get('title', 'Generated Resume')
        
        if not component_ids:
            return jsonify({'error': 'No components selected'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Track component usage
        for comp_id in component_ids:
            cursor.execute("""
                UPDATE resume_components 
                SET usage_count = usage_count + 1 
                WHERE id = ?
            """, (comp_id,))
        
        # Save generated resume
        cursor.execute("""
            INSERT INTO generated_resumes 
            (job_description_id, resume_title, components_used, 
             status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            title,
            json.dumps(component_ids),
            'draft',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        resume_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': resume_id, 'message': 'Resume generated'}), 201
        
    except Exception as e:
        logger.error(f"Error generating resume: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get database statistics for dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total components
        cursor.execute("SELECT COUNT(*) FROM resume_components")
        stats['total_components'] = cursor.fetchone()[0]
        
        # Components by section
        cursor.execute("""
            SELECT st.name, COUNT(*) as count
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            GROUP BY st.name
        """)
        stats['components_by_section'] = {row['name']: row['count'] for row in cursor.fetchall()}
        
        # Total employment records
        cursor.execute("SELECT COUNT(*) FROM employment_history")
        stats['total_employment'] = cursor.fetchone()[0]
        
        # Total job descriptions
        cursor.execute("SELECT COUNT(*) FROM job_descriptions")
        stats['total_jobs'] = cursor.fetchone()[0]
        
        # Total generated resumes
        cursor.execute("SELECT COUNT(*) FROM generated_resumes")
        stats['total_resumes'] = cursor.fetchone()[0]
        
        conn.close()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        return jsonify({'error': str(e)}), 500


# Serve the HTML file
@app.route('/')
def serve_html():
    """Serve the main HTML interface"""
    try:
        with open('enhanced_resume_app_api.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>Resume Database System</h1>
        <p>HTML interface file not found. Using basic fallback.</p>
        <p>API is running at: <a href="/api/health">/api/health</a></p>
        """


# Work Orders API Routes

@app.route('/api/work-orders', methods=['GET'])
def get_work_orders():
    """Get all work orders with optional filtering"""
    try:
        conn = get_db_connection()
        
        # Parse query parameters
        category = request.args.get('category')
        company = request.args.get('company')
        work_type = request.args.get('work_type')
        client_type = request.args.get('client_type')
        state = request.args.get('state')
        project_id = request.args.get('project_id')
        unassigned = request.args.get('unassigned', 'false').lower() == 'true'
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        if unassigned:
            query = """
                SELECT wo.* FROM work_orders wo
                LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
                WHERE wopa.work_order_id IS NULL
            """
            params = []
        else:
            query = "SELECT * FROM work_orders WHERE 1=1"
            params = []
        
        if category:
            query += " AND work_category = ?"
            params.append(category)
        if company:
            query += " AND company_name LIKE ?"
            params.append(f"%{company}%")
        if work_type:
            query += " AND work_type LIKE ?"
            params.append(f"%{work_type}%")
        if client_type:
            query += " AND client_type = ?"
            params.append(client_type)
        if state:
            query += " AND state = ?"
            params.append(state)
        if project_id:
            query = """
                SELECT wo.* FROM work_orders wo
                JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
                WHERE wopa.project_id = ?
            """
            params = [project_id]
        
        query += " ORDER BY service_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        work_orders = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields
        for wo in work_orders:
            if wo['technologies_used']:
                wo['technologies_used'] = json.loads(wo['technologies_used'])
            if wo['skills_demonstrated']:
                wo['skills_demonstrated'] = json.loads(wo['skills_demonstrated'])
        
        conn.close()
        return jsonify(work_orders)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/stats', methods=['GET'])
def get_work_order_stats():
    """Get work order statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("SELECT COUNT(*) FROM work_orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT company_name) FROM work_orders")
        unique_companies = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(pay_amount) FROM work_orders WHERE pay_amount IS NOT NULL")
        total_earnings = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(pay_amount) FROM work_orders WHERE pay_amount IS NOT NULL")
        avg_pay = cursor.fetchone()[0] or 0
        
        # Unassigned work orders
        cursor.execute("""
            SELECT COUNT(*) FROM work_orders wo
            LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
            WHERE wopa.work_order_id IS NULL
        """)
        unassigned_orders = cursor.fetchone()[0]
        
        # By category
        cursor.execute("""
            SELECT work_category, COUNT(*) as count, 
                   COALESCE(SUM(pay_amount), 0) as total_pay
            FROM work_orders 
            GROUP BY work_category 
            ORDER BY count DESC
        """)
        by_category = [dict(row) for row in cursor.fetchall()]
        
        # By year
        cursor.execute("""
            SELECT strftime('%Y', service_date) as year, 
                   COUNT(*) as count,
                   COALESCE(SUM(pay_amount), 0) as total_pay
            FROM work_orders 
            WHERE service_date IS NOT NULL
            GROUP BY strftime('%Y', service_date)
            ORDER BY year DESC
        """)
        by_year = [dict(row) for row in cursor.fetchall()]
        
        # Top companies
        cursor.execute("""
            SELECT company_name, COUNT(*) as count,
                   COALESCE(SUM(pay_amount), 0) as total_pay
            FROM work_orders 
            GROUP BY company_name 
            ORDER BY count DESC
            LIMIT 10
        """)
        top_companies = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_orders': total_orders,
            'unique_companies': unique_companies,
            'total_earnings': round(total_earnings, 2),
            'average_pay': round(avg_pay, 2),
            'unassigned_orders': unassigned_orders,
            'by_category': by_category,
            'by_year': by_year,
            'top_companies': top_companies
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/categories', methods=['GET'])
def get_work_order_categories():
    """Get unique work order categories"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT work_category FROM work_orders ORDER BY work_category")
        categories = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT work_type FROM work_orders WHERE work_type IS NOT NULL ORDER BY work_type")
        work_types = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT client_type FROM work_orders WHERE client_type IS NOT NULL ORDER BY client_type")
        client_types = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT state FROM work_orders WHERE state IS NOT NULL ORDER BY state")
        states = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'categories': categories,
            'work_types': work_types,
            'client_types': client_types,
            'states': states
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/<int:work_order_id>', methods=['GET'])
def get_work_order(work_order_id):
    """Get a specific work order"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,))
        work_order = cursor.fetchone()
        
        if not work_order:
            return jsonify({'error': 'Work order not found'}), 404
        
        wo_dict = dict(work_order)
        
        # Parse JSON fields
        if wo_dict['technologies_used']:
            wo_dict['technologies_used'] = json.loads(wo_dict['technologies_used'])
        if wo_dict['skills_demonstrated']:
            wo_dict['skills_demonstrated'] = json.loads(wo_dict['skills_demonstrated'])
        
        conn.close()
        return jsonify(wo_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/<int:work_order_id>', methods=['PUT'])
def update_work_order(work_order_id):
    """Update a work order"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if work order exists
        cursor.execute("SELECT id FROM work_orders WHERE id = ?", (work_order_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Work order not found'}), 404
        
        # Update fields
        update_fields = []
        params = []
        
        for field in ['work_description', 'challenges_faced', 'solutions_implemented', 
                     'client_feedback', 'lessons_learned', 'complexity_level',
                     'include_in_resume', 'highlight_project']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if update_fields:
            params.append(datetime.now().isoformat())
            params.append(work_order_id)
            
            query = f"UPDATE work_orders SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return jsonify({'message': 'Work order updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/resume-components', methods=['GET'])
def generate_resume_components_from_work_orders():
    """Generate resume components from work orders"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get highlighted work orders
        cursor.execute("""
            SELECT * FROM work_orders 
            WHERE include_in_resume = TRUE 
            ORDER BY highlight_project DESC, pay_amount DESC, service_date DESC
            LIMIT 20
        """)
        
        work_orders = [dict(row) for row in cursor.fetchall()]
        
        components = []
        
        for wo in work_orders:
            # Parse JSON fields
            technologies = json.loads(wo['technologies_used']) if wo['technologies_used'] else []
            skills = json.loads(wo['skills_demonstrated']) if wo['skills_demonstrated'] else []
            
            # Create work experience component
            title = f"{wo['work_type']} - {wo['company_name']}"
            if wo['service_date']:
                service_date = datetime.strptime(wo['service_date'], '%Y-%m-%d').strftime('%B %Y')
                title += f" ({service_date})"
            
            content = wo['title']
            if wo['work_description']:
                content += f"\n{wo['work_description']}"
            if wo['location']:
                content += f"\nLocation: {wo['location']}"
            
            # Add technologies and skills as keywords
            keywords = technologies + skills + [wo['work_category'], wo['client_type']]
            keywords = [k for k in keywords if k]  # Remove empty strings
            
            component = {
                'title': title,
                'content': content,
                'section_type': 'work_experience',
                'keywords': keywords,
                'industry_tags': [wo['client_type']] if wo['client_type'] else [],
                'source': 'fieldnation_work_order',
                'source_id': wo['id']
            }
            
            components.append(component)
        
        conn.close()
        return jsonify(components)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/import', methods=['POST'])
def import_work_orders():
    """Trigger work order import from CSV files"""
    try:
        # This would call your import script
        import subprocess
        result = subprocess.run(['python', 'import_field_nation_data.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                'message': 'Import completed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'error': 'Import failed',
                'details': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PROJECT MANAGEMENT API ROUTES

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all work order projects"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        include_resume_only = request.args.get('resume_only', 'false').lower() == 'true'
        
        if include_resume_only:
            cursor.execute("SELECT * FROM project_portfolio")
        else:
            cursor.execute("""
                SELECT p.*, 
                       COUNT(wopa.work_order_id) as work_order_count,
                       COALESCE(SUM(wo.pay_amount), 0) as calculated_earnings
                FROM work_order_projects p
                LEFT JOIN work_order_project_assignments wopa ON p.id = wopa.project_id
                LEFT JOIN work_orders wo ON wopa.work_order_id = wo.id
                GROUP BY p.id
                ORDER BY p.priority_level, p.end_date DESC
            """)
        
        projects = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields
        for project in projects:
            for field in ['key_achievements', 'technologies_used', 'skills_demonstrated', 'locations_served', 'target_job_types']:
                if project.get(field):
                    project[field] = json.loads(project[field])
        
        conn.close()
        return jsonify(projects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new work order project"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert project
        cursor.execute("""
            INSERT INTO work_order_projects (
                project_name, project_description, project_type, client_name, client_type,
                start_date, end_date, duration_weeks, scope_description, team_size, my_role,
                key_achievements, technologies_used, skills_demonstrated, include_in_resume,
                priority_level, target_job_types, project_summary, challenges_overcome,
                business_impact, lessons_learned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['project_name'], data.get('project_description', ''),
            data.get('project_type', 'support'), data.get('client_name', ''),
            data.get('client_type', 'enterprise'), data.get('start_date'),
            data.get('end_date'), data.get('duration_weeks'),
            data.get('scope_description', ''), data.get('team_size', 1),
            data.get('my_role', 'Technical Specialist'),
            json.dumps(data.get('key_achievements', [])),
            json.dumps(data.get('technologies_used', [])),
            json.dumps(data.get('skills_demonstrated', [])),
            data.get('include_in_resume', True), data.get('priority_level', 3),
            json.dumps(data.get('target_job_types', [])),
            data.get('project_summary', ''), data.get('challenges_overcome', ''),
            data.get('business_impact', ''), data.get('lessons_learned', '')
        ))
        
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': project_id, 'message': 'Project created successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a work order project"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update project
        update_fields = []
        params = []
        
        for field in ['project_name', 'project_description', 'project_type', 'client_name', 
                     'client_type', 'start_date', 'end_date', 'duration_weeks', 
                     'scope_description', 'team_size', 'my_role', 'include_in_resume',
                     'priority_level', 'project_summary', 'challenges_overcome',
                     'business_impact', 'lessons_learned']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        # Handle JSON fields
        for field in ['key_achievements', 'technologies_used', 'skills_demonstrated', 
                     'locations_served', 'target_job_types']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(json.dumps(data[field]))
        
        if update_fields:
            params.append(datetime.now().isoformat())
            params.append(project_id)
            
            query = f"UPDATE work_order_projects SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return jsonify({'message': 'Project updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/work-orders', methods=['POST'])
def assign_work_orders_to_project(project_id):
    """Assign work orders to a project"""
    try:
        data = request.json
        work_order_ids = data.get('work_order_ids', [])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if project exists
        cursor.execute("SELECT id FROM work_order_projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Project not found'}), 404
        
        # Assign work orders
        assigned = 0
        for wo_id in work_order_ids:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO work_order_project_assignments 
                    (work_order_id, project_id, role_in_project)
                    VALUES (?, ?, ?)
                """, (wo_id, project_id, data.get('role_in_project', 'Primary')))
                assigned += 1
            except Exception as e:
                print(f"Error assigning work order {wo_id}: {e}")
        
        # Update project metrics
        cursor.execute("""
            UPDATE work_order_projects 
            SET total_work_orders = (
                SELECT COUNT(*) FROM work_order_project_assignments 
                WHERE project_id = ?
            ),
            total_earnings = COALESCE((
                SELECT SUM(wo.pay_amount) 
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ?
            ), 0),
            avg_rating = COALESCE((
                SELECT AVG(wo.wo_rating) 
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ? AND wo.wo_rating IS NOT NULL
            ), 0)
            WHERE id = ?
        """, (project_id, project_id, project_id, project_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Assigned {assigned} work orders to project',
            'assigned_count': assigned
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/work-orders/<int:work_order_id>', methods=['DELETE'])
def remove_work_order_from_project(project_id, work_order_id):
    """Remove a work order from a project"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM work_order_project_assignments 
            WHERE project_id = ? AND work_order_id = ?
        """, (project_id, work_order_id))
        
        # Update project metrics
        cursor.execute("""
            UPDATE work_order_projects 
            SET total_work_orders = (
                SELECT COUNT(*) FROM work_order_project_assignments 
                WHERE project_id = ?
            ),
            total_earnings = COALESCE((
                SELECT SUM(wo.pay_amount) 
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ?
            ), 0)
            WHERE id = ?
        """, (project_id, project_id, project_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Work order removed from project'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/auto-create', methods=['POST'])
def auto_create_projects():
    """Automatically create projects based on work order patterns"""
    try:
        data = request.json
        grouping_criteria = data.get('criteria', 'company_and_timeframe')  # company_and_timeframe, technology, location
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        created_projects = []
        
        if grouping_criteria == 'company_and_timeframe':
            # Group by company and 3-month periods
            cursor.execute("""
                SELECT company_name, 
                       strftime('%Y', service_date) as year,
                       (CAST(strftime('%m', service_date) AS INTEGER) - 1) / 3 as quarter,
                       COUNT(*) as work_order_count,
                       MIN(service_date) as start_date,
                       MAX(service_date) as end_date,
                       SUM(pay_amount) as total_earnings,
                       GROUP_CONCAT(DISTINCT work_category) as categories,
                       GROUP_CONCAT(DISTINCT state) as states
                FROM work_orders wo
                LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
                WHERE wopa.work_order_id IS NULL AND service_date IS NOT NULL
                GROUP BY company_name, year, quarter
                HAVING work_order_count >= 3
                ORDER BY company_name, year, quarter
            """)
            
            for row in cursor.fetchall():
                row_dict = dict(row)
                quarter_name = f"Q{row_dict['quarter'] + 1} {row_dict['year']}"
                
                # Create project
                cursor.execute("""
                    INSERT INTO work_order_projects (
                        project_name, project_description, project_type, client_name,
                        client_type, start_date, end_date, project_summary,
                        include_in_resume, priority_level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{row_dict['company_name']} - {quarter_name} Support",
                    f"Comprehensive technical support services for {row_dict['company_name']} during {quarter_name}",
                    "support",
                    row_dict['company_name'],
                    "enterprise",
                    row_dict['start_date'],
                    row_dict['end_date'],
                    f"Provided {row_dict['work_order_count']} technical support services across {row_dict['categories']} with total value of ${row_dict['total_earnings']:.2f}",
                    True,
                    2
                ))
                
                project_id = cursor.lastrowid
                created_projects.append({
                    'id': project_id,
                    'name': f"{row_dict['company_name']} - {quarter_name} Support",
                    'work_order_count': row_dict['work_order_count']
                })
                
                # Assign work orders to project
                cursor.execute("""
                    INSERT INTO work_order_project_assignments (work_order_id, project_id, role_in_project)
                    SELECT wo.id, ?, 'Primary'
                    FROM work_orders wo
                    WHERE wo.company_name = ? 
                    AND strftime('%Y', wo.service_date) = ?
                    AND (CAST(strftime('%m', wo.service_date) AS INTEGER) - 1) / 3 = ?
                    AND wo.id NOT IN (SELECT work_order_id FROM work_order_project_assignments)
                """, (project_id, row_dict['company_name'], row_dict['year'], row_dict['quarter']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Created {len(created_projects)} projects automatically',
            'projects': created_projects
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ENHANCED JOB MATCHING WITH WORK ORDERS AND PROJECTS

@app.route('/api/job-matcher/enhanced', methods=['POST'])
def enhanced_job_matcher():
    """Enhanced job matching that includes work orders and projects"""
    try:
        data = request.json
        job_description = data.get('job_description', '')
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get regular resume components
        cursor.execute("""
            SELECT rc.*, st.name as section_type_name
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
        """)
        components = [dict(row) for row in cursor.fetchall()]
        
        # Get work items (individual work orders and projects)
        cursor.execute("SELECT * FROM resume_ready_work_items")
        work_items = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Extract keywords from job description
        keywords = extract_keywords(job_description)
        
        # Match components
        component_matches = match_items_to_job(job_description, components, 'component')
        
        # Match work items (work orders and projects)
        work_matches = match_items_to_job(job_description, work_items, 'work_item')
        
        return jsonify({
            'keywords': keywords,
            'component_matches': component_matches[:10],
            'work_order_matches': [m for m in work_matches if m['item']['item_type'] == 'work_order'][:10],
            'project_matches': [m for m in work_matches if m['item']['item_type'] == 'project'][:5],
            'total_matches': len(component_matches) + len(work_matches)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def match_items_to_job(job_description, items, item_type):
    """Match items (components or work items) to job description"""
    keywords = extract_keywords(job_description)
    matches = []
    
    for item in items:
        score = 0
        total_keywords = len(keywords)
        
        # Create searchable text based on item type
        if item_type == 'component':
            searchable_text = f"{item['title']} {item['content']} {item.get('keywords', '')}".lower()
        else:  # work_item
            searchable_text = f"{item['title']} {item.get('description', '')} {item.get('technologies_used', '')} {item.get('skills_demonstrated', '')}".lower()
        
        # Count keyword matches
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in searchable_text:
                score += 1
                matched_keywords.append(keyword)
        
        # Bonus scoring for exact phrase matches
        job_lower = job_description.lower()
        if item_type == 'work_item':
            # Bonus for technology matches
            if item.get('technologies_used'):
                technologies = json.loads(item['technologies_used']) if isinstance(item['technologies_used'], str) else item['technologies_used']
                for tech in technologies:
                    if tech.lower() in job_lower:
                        score += 2
            
            # Bonus for skill matches
            if item.get('skills_demonstrated'):
                skills = json.loads(item['skills_demonstrated']) if isinstance(item['skills_demonstrated'], str) else item['skills_demonstrated']
                for skill in skills:
                    if skill.lower() in job_lower:
                        score += 1.5
        
        if score > 0:
            match_percentage = min(100, int((score / max(total_keywords, 1)) * 100))
            matches.append({
                'item': item,
                'score': score,
                'match_percentage': match_percentage,
                'matched_keywords': matched_keywords,
                'item_type': item_type
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches

@app.route('/api/projects/resume-components', methods=['GET'])
def generate_resume_components_from_projects():
    """Generate resume components from projects"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM project_portfolio ORDER BY priority_level, actual_end_date DESC")
        projects = [dict(row) for row in cursor.fetchall()]
        
        components = []
        
        for project in projects:
            # Parse JSON fields
            technologies = json.loads(project['technologies_used']) if project['technologies_used'] else []
            skills = json.loads(project['skills_demonstrated']) if project['skills_demonstrated'] else []
            achievements = json.loads(project['key_achievements']) if project['key_achievements'] else []
            
            # Create project component
            title = f"Project: {project['project_name']}"
            if project['client_name']:
                title += f" - {project['client_name']}"
            
            content = project['project_description'] or project['project_summary'] or ""
            
            # Add project details
            if project['my_role']:
                content += f"\nRole: {project['my_role']}"
            if project['actual_work_orders']:
                content += f"\nCompleted {project['actual_work_orders']} work orders"
            if project['actual_earnings']:
                content += f"\nProject value: ${project['actual_earnings']:,.2f}"
            if achievements:
                content += f"\nKey achievements: {', '.join(achievements)}"
            if project['business_impact']:
                content += f"\nBusiness impact: {project['business_impact']}"
            
            # Keywords from technologies, skills, and project type
            keywords = technologies + skills + [project['project_type'], project['client_type']]
            keywords = [k for k in keywords if k]
            
            component = {
                'title': title,
                'content': content,
                'section_type': 'projects',
                'keywords': keywords,
                'industry_tags': [project['client_type']] if project['client_type'] else [],
                'source': 'fieldnation_project',
                'source_id': project['id']
            }
            
            components.append(component)
        
        conn.close()
        return jsonify(components)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_keywords(text: str) -> list:
    """Extract keywords from text - simplified version"""
    import re
    
    # Remove common words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'will', 'would',
        'should', 'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'our', 'your', 'their', 'his', 'her', 'its'
    }
    
    # Extract words (2+ characters, alphanumeric)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    
    # Filter out stop words and get unique keywords
    keywords = list(set([word for word in words if word not in stop_words]))
    
    # Sort by frequency in text
    keyword_freq = [(word, text.lower().count(word)) for word in keywords]
    keyword_freq.sort(key=lambda x: x[1], reverse=True)
    
    return [word for word, freq in keyword_freq[:50]]  # Return top 50 keywords


# DELETE FUNCTIONALITY ENDPOINTS

@app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component(component_id):
    """Delete a resume component"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if component exists
        cursor.execute("SELECT id FROM resume_components WHERE id = ?", (component_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Component not found'}), 404
        
        # Delete component (cascade deletes will handle related records)
        cursor.execute("DELETE FROM resume_components WHERE id = ?", (component_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Component deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting component: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/work-orders/<int:work_order_id>', methods=['DELETE'])
def delete_work_order(work_order_id):
    """Delete a work order"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if work order exists
        cursor.execute("SELECT id FROM work_orders WHERE id = ?", (work_order_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Work order not found'}), 404
        
        # Delete work order
        cursor.execute("DELETE FROM work_orders WHERE id = ?", (work_order_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Work order deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting work order: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if project exists
        cursor.execute("SELECT id FROM work_order_projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Project not found'}), 404
        
        # Delete project (this will also remove work order associations)
        cursor.execute("DELETE FROM work_order_projects WHERE id = ?", (project_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Project deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({'error': str(e)}), 500


# RESUME UPLOAD AND PARSING ENDPOINTS

@app.route('/api/resumes/upload', methods=['POST'])
def upload_resume():
    """Upload and parse a resume file"""
    try:
        # Check for both 'resume' and 'file' fields for compatibility
        if 'resume' not in request.files and 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files.get('resume') or request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Ensure uploads directory exists
            upload_folder = os.path.join(os.getcwd(), 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            # Extract text based on file type
            content = extract_text_from_file(filepath, file.filename)
            
            if not content or len(content.strip()) < 50:
                # Clean up uploaded file
                try:
                    os.remove(filepath)
                except:
                    pass
                return jsonify({
                    'error': f'Could not extract meaningful text from {file.filename}. Please try converting to .txt format or ensure the file contains readable text.'
                }), 400
            
            # Parse the resume content
            parsed_components = parse_resume_text(content)
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass  # Don't fail if file cleanup fails
            
            return jsonify({
                'message': 'Resume uploaded and parsed successfully',
                'filename': file.filename,
                'components': parsed_components,
                'extracted_text_length': len(content)
            })
        else:
            return jsonify({'error': 'Invalid file type. Please upload TXT, PDF, DOC, or DOCX files.'}), 400
            
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/resumes/parse-text', methods=['POST'])
def parse_resume_text_endpoint():
    """Parse resume text directly without file upload"""
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        resume_text = data['text']
        parsed_components = parse_resume_text(resume_text)
        
        return jsonify({
            'message': 'Resume text parsed successfully',
            'components': parsed_components
        })
        
    except Exception as e:
        logger.error(f"Error parsing resume text: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/resumes/import-components', methods=['POST'])
def import_resume_components():
    """Import parsed components into the database"""
    try:
        data = request.json
        if not data or 'components' not in data:
            return jsonify({'error': 'No components provided'}), 400
        
        components = data['components']
        source_name = data.get('source_name', 'Uploaded Resume')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        
        for section_type, section_components in components.items():
            if not section_components:
                continue
                
            # Get section type ID
            cursor.execute("SELECT id FROM section_types WHERE name = ?", (section_type,))
            section_type_row = cursor.fetchone()
            if not section_type_row:
                continue
                
            section_type_id = section_type_row['id']
            
            for i, content in enumerate(section_components):
                if not content.strip():
                    continue
                    
                title = f"{source_name} - {section_type.replace('_', ' ').title()} {i+1}"
                
                cursor.execute("""
                    INSERT INTO resume_components 
                    (section_type_id, title, content, keywords, industry_tags, skill_level, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    section_type_id,
                    title,
                    content,
                    json.dumps([]),  # Empty keywords for now
                    json.dumps([]),  # Empty industry tags for now
                    'intermediate',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                imported_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Successfully imported {imported_count} components',
            'imported_count': imported_count
        })
        
    except Exception as e:
        logger.error(f"Error importing components: {e}")
        return jsonify({'error': str(e)}), 500


# TEMPLATE MANAGEMENT ENDPOINTS

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all resume templates"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM resume_templates 
            ORDER BY is_default DESC, usage_count DESC, created_at DESC
        """)
        templates = [dict_from_row(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(templates)
        
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates', methods=['POST'])
def create_template():
    """Create a new resume template"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO resume_templates 
            (template_name, description, target_role, target_industry, component_mapping, 
             style_settings, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['template_name'],
            data.get('description', ''),
            data.get('target_role', ''),
            data.get('target_industry', ''),
            json.dumps(data.get('component_mapping', {})),
            json.dumps(data.get('style_settings', {})),
            data.get('is_default', False),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': template_id, 'message': 'Template created successfully'}), 201
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/import-url', methods=['POST'])
def import_template_from_url():
    """Import a resume template from a URL"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
        
        url = data['url']
        template_name = data.get('template_name', f"Template from {urlparse(url).netloc}")
        
        # Download the template
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save the template content
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO resume_templates 
            (template_name, description, target_role, target_industry, component_mapping, 
             style_settings, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template_name,
            f"Imported from {url}",
            data.get('target_role', ''),
            data.get('target_industry', ''),
            json.dumps({'source_url': url, 'content': response.text}),
            json.dumps({'imported': True}),
            False,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': template_id, 
            'message': 'Template imported successfully',
            'template_name': template_name
        }), 201
        
    except requests.RequestException as e:
        logger.error(f"Error downloading template: {e}")
        return jsonify({'error': f'Failed to download template: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error importing template: {e}")
        return jsonify({'error': str(e)}), 500


# AUTO-CREATE PROJECTS FROM WORK ORDERS

@app.route('/api/projects/auto-create-from-workorders', methods=['POST'])
def auto_create_projects_from_work_orders():
    """Auto-create projects by grouping work orders from the same company"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get work orders grouped by company
        cursor.execute("""
            SELECT company_name, COUNT(*) as order_count, 
                   MIN(fn_work_order_id) as first_order_id,
                   GROUP_CONCAT(id) as work_order_ids
            FROM work_orders 
            WHERE company_name IS NOT NULL 
            GROUP BY company_name 
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
        """)
        
        company_groups = cursor.fetchall()
        created_projects = 0
        
        for group in company_groups:
            company_name = group['company_name']
            work_order_ids = [int(id) for id in group['work_order_ids'].split(',')]
            
            # Check if project already exists for this company
            cursor.execute("SELECT id FROM work_order_projects WHERE project_name LIKE ?", (f"%{company_name}%",))
            existing_project = cursor.fetchone()
            
            if not existing_project:
                # Create new project
                cursor.execute("""
                    INSERT INTO work_order_projects (project_name, project_description, client_name, 
                                                   total_work_orders, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{company_name} - Multiple Work Orders",
                    f"Auto-generated project from {group['order_count']} work orders for {company_name}",
                    company_name,
                    group['order_count'],
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                project_id = cursor.lastrowid
                
                # Associate work orders with the project
                for work_order_id in work_order_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO work_order_project_assignments (project_id, work_order_id)
                        VALUES (?, ?)
                    """, (project_id, work_order_id))
                
                created_projects += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Successfully created {created_projects} projects from work orders',
            'created_count': created_projects
        })
        
    except Exception as e:
        logger.error(f"Error auto-creating projects: {e}")
        return jsonify({'error': str(e)}), 500


# Add new endpoint for simple file upload and text extraction
@app.route('/upload_resume_file', methods=['POST'])
def upload_resume_file():
    """Upload resume file and return extracted text for manual component creation"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Save the uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join('uploads', filename)
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        
        file.save(temp_path)
        
        # Extract text from the file
        try:
            extracted_text = extract_text_from_file(temp_path, filename)
            
            if not extracted_text or extracted_text.strip() == '':
                return jsonify({
                    'success': False, 
                    'error': 'Could not extract text from file. The file may be empty or corrupted.'
                })
            
            # Save the full resume to database
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Get file size
                file_size = os.path.getsize(temp_path)
                file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                
                # Generate a title from filename
                resume_title = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                
                # Parse the text into structured data
                parsed_components = parse_resume_text(extracted_text)
                
                cursor.execute("""
                    INSERT INTO uploaded_resumes 
                    (filename, original_filename, file_type, file_size, resume_title, 
                     full_text_content, structured_data, upload_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    filename,
                    file.filename,
                    file_type,
                    file_size,
                    resume_title,
                    extracted_text,
                    json.dumps(parsed_components),
                    'manual_upload'
                ))
                
                resume_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                logger.info(f"Saved uploaded resume with ID {resume_id}")
                
            except Exception as db_error:
                logger.warning(f"Could not save resume to database: {db_error}")
                # Continue anyway - the text extraction worked
            
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except:
                pass  # Don't fail if file cleanup fails
            
            return jsonify({
                'success': True,
                'text': extracted_text,
                'filename': file.filename,
                'message': f'Successfully extracted text from {file.filename}',
                'resume_id': resume_id if 'resume_id' in locals() else None
            })
            
        except Exception as e:
            # Clean up temporary file on error
            try:
                os.remove(temp_path)
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': f'Failed to extract text from file: {str(e)}'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload failed: {str(e)}'})


@app.route('/add_component', methods=['POST'])
def add_component():
    """Add a manually created resume component"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['section_type', 'title', 'content']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get section type ID
        cursor.execute("SELECT id FROM section_types WHERE name = ?", (data['section_type'],))
        section_type_row = cursor.fetchone()
        if not section_type_row:
            return jsonify({'success': False, 'error': 'Invalid section type'}), 400
        
        section_type_id = section_type_row['id']
        
        # Insert component
        cursor.execute("""
            INSERT INTO resume_components 
            (section_type_id, title, content, keywords, industry_tags, skill_level, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            section_type_id,
            data['title'],
            data['content'],
            data.get('keywords', ''),
            data.get('industry_tags', ''),
            data.get('skill_level'),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        component_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'id': component_id, 
            'message': f'Component "{data["title"]}" added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding component: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# UPLOADED RESUMES API ENDPOINTS

@app.route('/api/uploaded-resumes', methods=['GET'])
def get_uploaded_resumes():
    """Get all uploaded resumes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        search_query = request.args.get('q', '')
        limit = request.args.get('limit', 50, type=int)
        
        query = "SELECT * FROM uploaded_resumes WHERE 1=1"
        params = []
        
        if not include_archived:
            query += " AND is_archived = FALSE"
        
        if search_query:
            query += " AND (resume_title LIKE ? OR original_filename LIKE ? OR notes LIKE ?)"
            search_pattern = f'%{search_query}%'
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        resumes = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Parse JSON fields
        for resume in resumes:
            if resume.get('tags'):
                resume['tags'] = json.loads(resume['tags'])
            if resume.get('structured_data'):
                resume['structured_data'] = json.loads(resume['structured_data'])
        
        conn.close()
        return jsonify(resumes)
        
    except Exception as e:
        logger.error(f"Error fetching uploaded resumes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/uploaded-resumes', methods=['POST'])
def save_uploaded_resume():
    """Save an uploaded resume to the database"""
    try:
        data = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO uploaded_resumes 
            (filename, original_filename, file_type, file_size, resume_title, 
             full_text_content, structured_data, upload_source, tags, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('filename', ''),
            data.get('original_filename', ''),
            data.get('file_type', ''),
            data.get('file_size', 0),
            data.get('resume_title', ''),
            data.get('full_text_content', ''),
            json.dumps(data.get('structured_data', {})),
            data.get('upload_source', 'manual'),
            json.dumps(data.get('tags', [])),
            data.get('notes', '')
        ))
        
        resume_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': resume_id,
            'message': 'Resume saved successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error saving uploaded resume: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/uploaded-resumes/<int:resume_id>', methods=['GET'])
def get_uploaded_resume(resume_id):
    """Get a specific uploaded resume"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM uploaded_resumes WHERE id = ?", (resume_id,))
        resume = cursor.fetchone()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        resume_dict = dict_from_row(resume)
        
        # Parse JSON fields
        if resume_dict.get('tags'):
            resume_dict['tags'] = json.loads(resume_dict['tags'])
        if resume_dict.get('structured_data'):
            resume_dict['structured_data'] = json.loads(resume_dict['structured_data'])
        
        # Update last accessed
        cursor.execute("UPDATE uploaded_resumes SET last_accessed = ? WHERE id = ?", 
                      (datetime.now().isoformat(), resume_id))
        conn.commit()
        conn.close()
        
        return jsonify(resume_dict)
        
    except Exception as e:
        logger.error(f"Error fetching uploaded resume: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/uploaded-resumes/<int:resume_id>', methods=['PUT'])
def update_uploaded_resume(resume_id):
    """Update an uploaded resume"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if resume exists
        cursor.execute("SELECT id FROM uploaded_resumes WHERE id = ?", (resume_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Resume not found'}), 404
        
        # Update fields
        update_fields = []
        params = []
        
        for field in ['resume_title', 'notes', 'is_archived']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if 'tags' in data:
            update_fields.append("tags = ?")
            params.append(json.dumps(data['tags']))
        
        if update_fields:
            params.append(datetime.now().isoformat())
            params.append(resume_id)
            
            query = f"UPDATE uploaded_resumes SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return jsonify({'message': 'Resume updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating uploaded resume: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/uploaded-resumes/<int:resume_id>', methods=['DELETE'])
def delete_uploaded_resume(resume_id):
    """Delete an uploaded resume"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if resume exists
        cursor.execute("SELECT id FROM uploaded_resumes WHERE id = ?", (resume_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Resume not found'}), 404
        
        # Delete resume
        cursor.execute("DELETE FROM uploaded_resumes WHERE id = ?", (resume_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Resume deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting uploaded resume: {e}")
        return jsonify({'error': str(e)}), 500


# TEMPLATES API ENDPOINTS

@app.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Get a specific template"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM resume_templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        template_dict = dict_from_row(template)
        
        # Parse JSON fields
        if template_dict.get('component_mapping'):
            template_dict['component_mapping'] = json.loads(template_dict['component_mapping'])
        if template_dict.get('style_settings'):
            template_dict['style_settings'] = json.loads(template_dict['style_settings'])
        
        conn.close()
        return jsonify(template_dict)
        
    except Exception as e:
        logger.error(f"Error fetching template: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """Update a template"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if template exists
        cursor.execute("SELECT id FROM resume_templates WHERE id = ?", (template_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Template not found'}), 404
        
        # Update fields
        update_fields = []
        params = []
        
        for field in ['template_name', 'description', 'target_role', 'target_industry', 'is_default']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        # Handle JSON fields
        if 'component_mapping' in data:
            update_fields.append("component_mapping = ?")
            params.append(json.dumps(data['component_mapping']))
        
        if 'style_settings' in data:
            update_fields.append("style_settings = ?")
            params.append(json.dumps(data['style_settings']))
        
        if update_fields:
            params.append(datetime.now().isoformat())
            params.append(template_id)
            
            query = f"UPDATE resume_templates SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return jsonify({'message': 'Template updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a template"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if template exists
        cursor.execute("SELECT id FROM resume_templates WHERE id = ?", (template_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Template not found'}), 404
        
        # Check if template is marked as default
        cursor.execute("SELECT is_default FROM resume_templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        if template and template['is_default']:
            return jsonify({'error': 'Cannot delete default template'}), 400
        
        # Delete template
        cursor.execute("DELETE FROM resume_templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Template deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Ensure database exists
    if not os.path.exists(DATABASE_PATH):
        logger.warning(f"Database not found at {DATABASE_PATH}. Run resume_extractor.py first.")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5001) 