#!/usr/bin/env python3
"""
Integration Script for Existing Resume Template App
Migrates data from the HTML template app to the database system
"""

import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeAppIntegrator:
    def __init__(self, database_path: str = "resume_database.db"):
        self.database_path = database_path
        self.conn = sqlite3.connect(database_path)
        self.conn.row_factory = sqlite3.Row
        
    def extract_from_template_app(self, html_path: str):
        """Extract resume data from the existing HTML template app"""
        logger.info(f"Extracting data from {html_path}")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Extract personal info
        personal_info = {
            'full_name': self._get_input_value(soup, 'full-name'),
            'location': self._get_input_value(soup, 'location'),
            'email': self._get_input_value(soup, 'email'),
            'phone': self._get_input_value(soup, 'phone'),
            'linkedin': self._get_input_value(soup, 'linkedin')
        }
        
        # Extract professional summary
        prof_summary = self._get_textarea_value(soup, 'professional-summary')
        career_objective = self._get_textarea_value(soup, 'career-objective')
        
        # Extract skills by category
        skills = {
            'server_management': self._extract_skills(soup, 'server-management-skills'),
            'windows_tools': self._extract_skills(soup, 'windows-tools-skills'),
            'mobile': self._extract_skills(soup, 'mobile-skills'),
            'vpn': self._extract_skills(soup, 'vpn-skills'),
            'office365': self._extract_skills(soup, 'office365-skills'),
            'security': self._extract_skills(soup, 'security-skills'),
            'blockchain': self._extract_skills(soup, 'blockchain-skills'),
            'tech_support': self._extract_skills(soup, 'tech-support-skills'),
            'itil': self._extract_skills(soup, 'itil-skills'),
            'deployment': self._extract_skills(soup, 'deployment-skills'),
            'maintenance': self._extract_skills(soup, 'maintenance-skills'),
            'documentation': self._extract_skills(soup, 'documentation-skills'),
            'work_environment': self._extract_skills(soup, 'work-environment-skills')
        }
        
        # Extract certifications
        certifications = self._extract_skills(soup, 'certification-items')
        
        return {
            'personal_info': personal_info,
            'professional_summary': prof_summary,
            'career_objective': career_objective,
            'skills': skills,
            'certifications': certifications
        }
    
    def _get_input_value(self, soup, input_id):
        """Get value from input field"""
        element = soup.find('input', {'id': input_id})
        return element.get('value', '') if element else ''
    
    def _get_textarea_value(self, soup, textarea_id):
        """Get value from textarea"""
        element = soup.find('textarea', {'id': textarea_id})
        return element.text.strip() if element else ''
    
    def _extract_skills(self, soup, container_id):
        """Extract skills from a container div"""
        container = soup.find('div', {'id': container_id})
        if not container:
            return []
        
        skills = []
        skill_items = container.find_all('div', class_='skill-item')
        for item in skill_items:
            input_elem = item.find('input')
            if input_elem and input_elem.get('value'):
                skills.append(input_elem.get('value'))
        
        return skills
    
    def import_to_database(self, extracted_data):
        """Import extracted data into the database"""
        cursor = self.conn.cursor()
        components_created = 0
        
        # Import personal info
        personal = extracted_data['personal_info']
        cursor.execute("""
            INSERT OR REPLACE INTO personal_info 
            (id, full_name, email, phone, location, linkedin_url, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (
            personal['full_name'],
            personal['email'],
            personal['phone'],
            personal['location'],
            personal['linkedin'],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # Import professional summary
        if extracted_data['professional_summary']:
            components_created += self._create_component(
                'professional_summary',
                'Professional Summary',
                extracted_data['professional_summary'],
                'expert'
            )
        
        # Import career objective
        if extracted_data['career_objective']:
            components_created += self._create_component(
                'professional_summary',
                'Career Objective',
                extracted_data['career_objective'],
                'expert'
            )
        
        # Import technical skills
        skill_mappings = {
            'server_management': ('technical_skills', 'Server Management'),
            'windows_tools': ('technical_skills', 'Windows/Windows Tools'),
            'mobile': ('technical_skills', 'Mobile Technologies'),
            'vpn': ('technical_skills', 'VPN Technologies'),
            'office365': ('technical_skills', 'Office365/Microsoft365'),
            'security': ('technical_skills', 'Security'),
            'blockchain': ('technical_skills', 'Blockchain'),
            'tech_support': ('professional_skills', 'Technical Support'),
            'itil': ('professional_skills', 'ITIL & Service Management'),
            'deployment': ('professional_skills', 'Deployment and Configuration'),
            'maintenance': ('professional_skills', 'Maintenance and Optimization'),
            'documentation': ('professional_skills', 'Documentation and Training'),
            'work_environment': ('professional_skills', 'Work Environment Experience')
        }
        
        for skill_key, (section_type, title) in skill_mappings.items():
            skills = extracted_data['skills'].get(skill_key, [])
            for skill in skills:
                if skill:
                    components_created += self._create_component(
                        section_type,
                        f"{title}: {skill[:50]}..." if len(skill) > 50 else f"{title}: {skill}",
                        skill,
                        'advanced'
                    )
        
        # Import certifications
        for cert in extracted_data['certifications']:
            if cert:
                components_created += self._create_component(
                    'certifications',
                    cert[:100],
                    cert,
                    'expert'
                )
        
        self.conn.commit()
        logger.info(f"Created {components_created} components from template app")
        return components_created
    
    def _create_component(self, section_type, title, content, skill_level='intermediate'):
        """Create a component in the database"""
        cursor = self.conn.cursor()
        
        # Get section type ID
        cursor.execute("SELECT id FROM section_types WHERE name = ?", (section_type,))
        section_row = cursor.fetchone()
        if not section_row:
            logger.warning(f"Unknown section type: {section_type}")
            return 0
        
        section_type_id = section_row['id']
        
        # Extract keywords
        keywords = self._extract_keywords(content)
        
        # Check if component already exists
        cursor.execute("""
            SELECT id FROM resume_components 
            WHERE title = ? AND section_type_id = ?
        """, (title, section_type_id))
        
        if cursor.fetchone():
            logger.info(f"Component already exists: {title}")
            return 0
        
        # Insert component
        cursor.execute("""
            INSERT INTO resume_components 
            (section_type_id, title, content, keywords, skill_level, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            section_type_id,
            title,
            content,
            keywords,
            skill_level,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        return 1
    
    def _extract_keywords(self, text):
        """Extract keywords from text"""
        tech_keywords = [
            'windows', 'linux', 'macos', 'server', 'active directory', 'azure',
            'office365', 'microsoft', 'exchange', 'sharepoint', 'teams',
            'servicenow', 'itil', 'vpn', 'cisco', 'firewall', 'security',
            'bitlocker', 'antivirus', 'vmware', 'citrix', 'aws', 'cloud',
            'powershell', 'scripting', 'automation', 'deployment', 'sccm',
            'jamf', 'intune', 'autopilot', 'imaging', 'troubleshooting',
            'support', 'desktop', 'hardware', 'software', 'network'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return ', '.join(found_keywords)
    
    def create_sample_employment(self):
        """Create sample employment records based on known history"""
        cursor = self.conn.cursor()
        
        sample_employment = [
            {
                'company_name': 'Field Services Nationwide',
                'position_title': 'Senior Desktop Support Technician',
                'start_date': '2020-01-01',
                'end_date': None,
                'location': 'Vermont, USA',
                'employment_type': 'contract',
                'industry': 'IT Services',
                'responsibilities': [
                    'Provide Level 2 desktop support for enterprise clients',
                    'Lead Windows 10 to Windows 11 migration projects',
                    'Support financial sector clients with trading floor systems',
                    'Manage Active Directory and Group Policy configurations',
                    'Utilize ServiceNow for incident management'
                ],
                'achievements': [
                    'Completed 960+ work orders with 99% customer satisfaction',
                    'Successfully migrated 500+ workstations to Windows 11',
                    'Reduced ticket resolution time by 30%'
                ],
                'technologies_used': [
                    'Windows 10/11', 'Active Directory', 'ServiceNow', 
                    'Office365', 'SCCM', 'BitLocker', 'PowerShell'
                ]
            },
            {
                'company_name': 'Various Financial Institutions',
                'position_title': 'Desktop Support Specialist',
                'start_date': '2012-03-01',
                'end_date': '2019-12-31',
                'location': 'New York, NY',
                'employment_type': 'contract',
                'industry': 'Finance',
                'responsibilities': [
                    'Provided desktop support for trading floors',
                    'Managed hardware deployments and migrations',
                    'Supported Bloomberg terminals and financial applications',
                    'Performed break/fix repairs and troubleshooting'
                ],
                'achievements': [
                    'Supported 20+ major financial institutions',
                    'Completed multiple large-scale deployment projects',
                    'Maintained high client satisfaction ratings'
                ],
                'technologies_used': [
                    'Windows', 'Bloomberg Terminal', 'Citrix', 
                    'VMware', 'Active Directory', 'VPN'
                ]
            }
        ]
        
        for emp in sample_employment:
            cursor.execute("""
                INSERT INTO employment_history 
                (company_name, position_title, start_date, end_date, location, 
                 employment_type, industry, responsibilities, achievements, 
                 technologies_used, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                emp['company_name'],
                emp['position_title'],
                emp['start_date'],
                emp['end_date'],
                emp['location'],
                emp['employment_type'],
                emp['industry'],
                json.dumps(emp['responsibilities']),
                json.dumps(emp['achievements']),
                json.dumps(emp['technologies_used']),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        self.conn.commit()
        logger.info("Created sample employment records")


def main():
    """Main integration process"""
    print("🔄 Resume App Integration Tool")
    print("=" * 50)
    
    integrator = ResumeAppIntegrator()
    
    # Path to your existing resume template app
    template_app_path = "/Volumes/LLM-Drive/development_files/AI-dashboard/resume_app/resume-template-app.html"
    
    if not Path(template_app_path).exists():
        print(f"❌ Template app not found at: {template_app_path}")
        return
    
    print(f"📄 Found template app at: {template_app_path}")
    print("🔍 Extracting data from template app...")
    
    # Extract data
    extracted_data = integrator.extract_from_template_app(template_app_path)
    
    print(f"✅ Extracted:")
    print(f"   - Personal info for: {extracted_data['personal_info']['full_name']}")
    print(f"   - Professional summary: {len(extracted_data['professional_summary'])} chars")
    print(f"   - Career objective: {len(extracted_data['career_objective'])} chars")
    print(f"   - Skills categories: {len(extracted_data['skills'])} categories")
    print(f"   - Certifications: {len(extracted_data['certifications'])} items")
    
    # Import to database
    print("\n💾 Importing to database...")
    components_created = integrator.import_to_database(extracted_data)
    
    print(f"✅ Created {components_created} new components")
    
    # Create sample employment records
    print("\n📋 Creating sample employment records...")
    integrator.create_sample_employment()
    
    print("\n🎉 Integration complete!")
    print("\nNext steps:")
    print("1. Start the Flask backend: python app.py")
    print("2. Open the connected app: http://localhost:5000")
    print("3. Or open the HTML file directly: enhanced_resume_app_connected.html")


if __name__ == "__main__":
    main() 