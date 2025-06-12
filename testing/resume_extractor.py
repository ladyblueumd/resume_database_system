#!/usr/bin/env python3
"""
Resume Data Extraction Tool
Extracts components from existing resume files to populate the database
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import docx
import PyPDF2
import pandas as pd
from typing import List, Dict, Any
import re

class ResumeExtractor:
    def __init__(self, database_path: str = "resume_database.db"):
        self.database_path = database_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.database_path)
        
        # Check if database already has tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='personal_info'")
        if cursor.fetchone():
            # Database already initialized
            conn.close()
            return
        
        # Read schema file
        schema_path = Path(__file__).parent / "database_schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = f.read()
                conn.executescript(schema)
        
        conn.close()
        
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        file_path = Path(file_path)
        
        try:
            if file_path.suffix.lower() == '.pdf':
                return self.extract_from_pdf(file_path)
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                return self.extract_from_docx(file_path)
            elif file_path.suffix.lower() == '.txt':
                return self.extract_from_txt(file_path)
            else:
                print(f"Unsupported file format: {file_path.suffix}")
                return ""
        except Exception as e:
            print(f"Error extracting from {file_path}: {e}")
            return ""
    
    def extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF files"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return ""
    
    def extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX files"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""
    
    def extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading TXT {file_path}: {e}")
            return ""
    
    def identify_sections(self, text: str) -> Dict[str, str]:
        """Identify different sections in resume text"""
        sections = {}
        
        # Define section patterns
        section_patterns = {
            'professional_summary': [
                r'professional summary',
                r'summary',
                r'profile',
                r'objective',
                r'career objective'
            ],
            'technical_skills': [
                r'technical skills',
                r'technical competencies',
                r'technology skills',
                r'systems? & infrastructure',
                r'server management',
                r'windows.*tools?'
            ],
            'professional_skills': [
                r'professional skills',
                r'core competencies',
                r'key skills',
                r'areas of expertise',
                r'service management'
            ],
            'work_experience': [
                r'work experience',
                r'professional experience',
                r'employment history',
                r'experience',
                r'career history'
            ],
            'projects': [
                r'key projects',
                r'notable projects',
                r'major projects',
                r'project experience',
                r'achievements'
            ],
            'certifications': [
                r'certifications?',
                r'professional certifications?',
                r'training',
                r'credentials'
            ],
            'education': [
                r'education',
                r'educational background',
                r'academic background'
            ]
        }
        
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line is a section header
            found_section = None
            for section_type, patterns in section_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line.lower()):
                        found_section = section_type
                        break
                if found_section:
                    break
            
            if found_section:
                # Save previous section
                if current_section and section_content:
                    sections[current_section] = '\n'.join(section_content)
                
                # Start new section
                current_section = found_section
                section_content = []
            elif current_section:
                section_content.append(line)
        
        # Save last section
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content)
        
        return sections
    
    def extract_components_from_section(self, section_type: str, content: str) -> List[Dict[str, Any]]:
        """Extract individual components from a section"""
        components = []
        
        if section_type == 'technical_skills':
            components.extend(self.extract_skill_components(content, 'technical_skills'))
        elif section_type == 'professional_skills':
            components.extend(self.extract_skill_components(content, 'professional_skills'))
        elif section_type == 'work_experience':
            components.extend(self.extract_experience_components(content))
        elif section_type == 'projects':
            components.extend(self.extract_project_components(content))
        elif section_type == 'certifications':
            components.extend(self.extract_certification_components(content))
        else:
            # For other sections, treat as single component
            if content.strip():
                components.append({
                    'section_type': section_type,
                    'title': f"{section_type.replace('_', ' ').title()} Section",
                    'content': content.strip(),
                    'keywords': self.extract_keywords(content),
                    'skill_level': 'intermediate'
                })
        
        return components
    
    def extract_skill_components(self, content: str, section_type: str) -> List[Dict[str, Any]]:
        """Extract skill components from skills sections"""
        components = []
        
        # Split by categories or bullet points
        lines = content.split('\n')
        current_category = None
        category_skills = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if it's a category header (often in bold or ending with colon)
            if ':' in line and len(line.split(':')[0].split()) <= 4:
                # Save previous category
                if current_category and category_skills:
                    components.append({
                        'section_type': section_type,
                        'title': current_category,
                        'content': ', '.join(category_skills),
                        'keywords': ', '.join(category_skills).lower(),
                        'skill_level': 'advanced'
                    })
                
                # Start new category
                current_category = line.split(':')[0].strip()
                skills_part = ':'.join(line.split(':')[1:]).strip()
                category_skills = [skills_part] if skills_part else []
            elif current_category:
                category_skills.append(line)
            else:
                # No category, treat as individual skill group
                components.append({
                    'section_type': section_type,
                    'title': f"{section_type.replace('_', ' ').title()}: {line[:30]}...",
                    'content': line,
                    'keywords': self.extract_keywords(line),
                    'skill_level': 'intermediate'
                })
        
        # Save last category
        if current_category and category_skills:
            components.append({
                'section_type': section_type,
                'title': current_category,
                'content': ', '.join(category_skills),
                'keywords': ', '.join(category_skills).lower(),
                'skill_level': 'advanced'
            })
        
        return components
    
    def extract_experience_components(self, content: str) -> List[Dict[str, Any]]:
        """Extract work experience components"""
        components = []
        
        # Split by company/position entries
        entries = re.split(r'\n(?=[A-Z][^:]*(?::|$))', content)
        
        for entry in entries:
            entry = entry.strip()
            if len(entry) > 50:  # Filter out short entries
                # Extract company/position from first line
                lines = entry.split('\n')
                title = lines[0] if lines else "Work Experience"
                
                components.append({
                    'section_type': 'work_experience',
                    'title': title[:100],
                    'content': entry,
                    'keywords': self.extract_keywords(entry),
                    'skill_level': 'advanced'
                })
        
        return components
    
    def extract_project_components(self, content: str) -> List[Dict[str, Any]]:
        """Extract project components"""
        components = []
        
        # Split by bullet points or project names
        projects = re.split(r'\n(?=•|\*|-|\d+\.)', content)
        
        for project in projects:
            project = project.strip()
            if len(project) > 30:
                # Extract project name/company
                first_line = project.split('\n')[0].strip('•*- \t')
                title = first_line[:50] + "..." if len(first_line) > 50 else first_line
                
                components.append({
                    'section_type': 'projects',
                    'title': title,
                    'content': project,
                    'keywords': self.extract_keywords(project),
                    'skill_level': 'advanced'
                })
        
        return components
    
    def extract_certification_components(self, content: str) -> List[Dict[str, Any]]:
        """Extract certification components"""
        components = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip('•*- \t')
            if line and len(line) > 10:
                components.append({
                    'section_type': 'certifications',
                    'title': line[:50],
                    'content': line,
                    'keywords': self.extract_keywords(line),
                    'skill_level': 'expert'
                })
        
        return components
    
    def extract_keywords(self, text: str) -> str:
        """Extract relevant keywords from text"""
        # Common technical keywords
        tech_keywords = [
            'windows', 'linux', 'macos', 'active directory', 'servicenow',
            'office365', 'azure', 'aws', 'vmware', 'citrix', 'cisco',
            'dell', 'hp', 'server', 'desktop', 'support', 'troubleshooting',
            'deployment', 'migration', 'backup', 'security', 'network',
            'hardware', 'software', 'imaging', 'sccm', 'jamf', 'bitlocker',
            'exchange', 'sharepoint', 'teams', 'outlook', 'powershell',
            'python', 'sql', 'database', 'scripting', 'automation'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return ', '.join(found_keywords)
    
    def save_component_to_db(self, component: Dict[str, Any]):
        """Save component to database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Get section type ID
        cursor.execute("SELECT id FROM section_types WHERE name = ?", (component['section_type'],))
        section_type_row = cursor.fetchone()
        if not section_type_row:
            print(f"Unknown section type: {component['section_type']}")
            conn.close()
            return
        
        section_type_id = section_type_row[0]
        
        # Insert component
        cursor.execute("""
            INSERT INTO resume_components 
            (section_type_id, title, content, keywords, skill_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            section_type_id,
            component['title'],
            component['content'],
            component['keywords'],
            component.get('skill_level', 'intermediate'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def process_resume_file(self, file_path: str) -> int:
        """Process a single resume file and extract components"""
        print(f"Processing: {file_path}")
        
        # Extract text
        text = self.extract_text_from_file(file_path)
        if not text:
            print(f"No text extracted from {file_path}")
            return 0
        
        # Identify sections
        sections = self.identify_sections(text)
        print(f"Found sections: {list(sections.keys())}")
        
        # Extract components from each section
        total_components = 0
        for section_type, content in sections.items():
            components = self.extract_components_from_section(section_type, content)
            for component in components:
                self.save_component_to_db(component)
                total_components += 1
        
        print(f"Extracted {total_components} components from {file_path}")
        return total_components
    
    def process_directory(self, directory_path: str) -> Dict[str, int]:
        """Process all resume files in a directory"""
        directory = Path(directory_path)
        results = {'files_processed': 0, 'total_components': 0, 'errors': 0}
        
        # Supported file extensions
        supported_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        
        for file_path in directory.rglob('*'):
            if file_path.suffix.lower() in supported_extensions:
                try:
                    components_count = self.process_resume_file(str(file_path))
                    results['files_processed'] += 1
                    results['total_components'] += components_count
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    results['errors'] += 1
        
        return results
    
    def export_components_to_json(self, output_path: str = "extracted_components.json"):
        """Export all components to JSON for review"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rc.*, st.name as section_type_name
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            ORDER BY rc.created_at DESC
        """)
        
        components = []
        for row in cursor.fetchall():
            components.append({
                'id': row[0],
                'title': row[2],
                'content': row[3],
                'keywords': row[4],
                'skill_level': row[6],
                'section_type': row[11],
                'created_at': row[9]
            })
        
        with open(output_path, 'w') as f:
            json.dump(components, f, indent=2)
        
        conn.close()
        print(f"Exported {len(components)} components to {output_path}")
        
        return components
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get summary of extracted data"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Count components by section
        cursor.execute("""
            SELECT st.name, COUNT(*) as count
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            GROUP BY st.name
            ORDER BY count DESC
        """)
        
        section_counts = dict(cursor.fetchall())
        
        # Total components
        cursor.execute("SELECT COUNT(*) FROM resume_components")
        total_components = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_components': total_components,
            'section_breakdown': section_counts,
            'database_path': self.database_path
        }

def main():
    """Main extraction process"""
    print("🤖 Resume Component Extraction Tool")
    print("=" * 50)
    
    # Initialize extractor
    extractor = ResumeExtractor()
    
    # Process resumes directory
    resumes_dir = "/Volumes/LLM-Drive/development_files/AI-dashboard/resumes_2024/resumes_for_database"
    
    if not os.path.exists(resumes_dir):
        print(f"Directory not found: {resumes_dir}")
        return
    
    print(f"Processing resumes from: {resumes_dir}")
    results = extractor.process_directory(resumes_dir)
    
    print("\n" + "=" * 50)
    print("📊 EXTRACTION RESULTS")
    print("=" * 50)
    print(f"Files processed: {results['files_processed']}")
    print(f"Total components extracted: {results['total_components']}")
    print(f"Errors encountered: {results['errors']}")
    
    # Get summary
    summary = extractor.get_extraction_summary()
    print(f"\nDatabase summary:")
    print(f"Total components in database: {summary['total_components']}")
    print(f"Components by section:")
    for section, count in summary['section_breakdown'].items():
        print(f"  {section}: {count}")
    
    # Export for review
    components = extractor.export_components_to_json()
    print(f"\nComponents exported to: extracted_components.json")
    print(f"Database saved to: {summary['database_path']}")
    
    print("\n✅ Extraction complete! Components are ready for use in the resume builder.")

if __name__ == "__main__":
    main()
