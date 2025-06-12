#!/usr/bin/env python3
"""
FieldNation Data Processor
Comprehensive extraction and organization of work order data from markdown and PDF files
Organizes data by skills, software, tools, client information, locations, and contacts
"""

import sqlite3
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import PyPDF2
from dataclasses import dataclass, asdict

@dataclass
class WorkOrderData:
    """Structured work order data"""
    fn_work_order_id: str
    title: str
    company_name: str
    service_date: Optional[str]
    location: str
    pay_amount: Optional[float]
    status: str
    work_type: str
    service_type: str
    work_description: str
    technologies_used: List[str]
    skills_demonstrated: List[str]
    tools_required: List[str]
    client_type: str
    industry: str
    manager_contact: Optional[str]
    site_contact: Optional[str]
    time_logged: Optional[float]
    complexity_level: str
    challenges_faced: List[str]
    solutions_implemented: List[str]

class FieldNationDataProcessor:
    """Main processor for FieldNation work order data"""
    
    def __init__(self, db_path: str = 'resume_database.db'):
        self.db_path = db_path
        self.setup_enhanced_tables()
        
    def get_db_connection(self):
        """Create and return a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def setup_enhanced_tables(self):
        """Create enhanced tables for comprehensive work order data"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Enhanced work orders table with additional fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_orders_enhanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fn_work_order_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company_name TEXT NOT NULL,
                service_date DATE,
                location TEXT,
                pay_amount DECIMAL(10,2),
                status TEXT,
                work_type TEXT,
                service_type TEXT,
                work_description TEXT,
                
                -- Technical Details
                technologies_used TEXT, -- JSON array
                skills_demonstrated TEXT, -- JSON array
                tools_required TEXT, -- JSON array
                complexity_level TEXT,
                
                -- Client & Industry Information
                client_type TEXT,
                industry TEXT,
                business_impact TEXT,
                
                -- Contact Information
                manager_contact TEXT,
                site_contact TEXT,
                contact_phone TEXT,
                
                -- Time & Performance
                time_logged DECIMAL(4,2),
                estimated_hours DECIMAL(4,2),
                efficiency_rating DECIMAL(3,2),
                
                -- Problem Solving
                challenges_faced TEXT, -- JSON array
                solutions_implemented TEXT, -- JSON array
                lessons_learned TEXT,
                
                -- Resume Usage
                include_in_resume BOOLEAN DEFAULT TRUE,
                highlight_project BOOLEAN DEFAULT FALSE,
                resume_categories TEXT, -- JSON array of relevant resume categories
                
                -- Metadata
                extracted_from TEXT, -- file source
                extraction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Skills taxonomy table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_taxonomy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE NOT NULL,
                skill_category TEXT,
                skill_subcategory TEXT,
                related_tools TEXT, -- JSON array
                proficiency_indicators TEXT, -- JSON array
                industry_relevance TEXT, -- JSON array
                job_titles TEXT, -- JSON array of relevant job titles
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Technologies and tools table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technologies_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                technology_name TEXT UNIQUE NOT NULL,
                category TEXT, -- hardware, software, platform, etc.
                vendor TEXT,
                versions TEXT, -- JSON array
                skill_requirements TEXT, -- JSON array
                industry_usage TEXT, -- JSON array
                related_technologies TEXT, -- JSON array
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Client intelligence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE NOT NULL,
                industry TEXT,
                client_type TEXT,
                locations_served TEXT, -- JSON array
                technologies_used TEXT, -- JSON array
                service_patterns TEXT, -- JSON array
                contact_info TEXT, -- JSON object
                work_order_count INTEGER DEFAULT 0,
                total_value DECIMAL(10,2) DEFAULT 0,
                avg_rating DECIMAL(3,2),
                last_service_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Geographic service areas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_name TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                region TEXT,
                service_count INTEGER DEFAULT 0,
                industries_served TEXT, -- JSON array
                avg_pay_rate DECIMAL(10,2),
                travel_time_estimate INTEGER, -- minutes
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Job matching intelligence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_matching_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER,
                job_keywords TEXT, -- JSON array
                industry_tags TEXT, -- JSON array
                skill_matches TEXT, -- JSON array
                experience_level TEXT,
                relevant_achievements TEXT, -- JSON array
                match_strength DECIMAL(3,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id) REFERENCES work_orders_enhanced(id)
            )
        """)
        
        conn.commit()
        conn.close()

    def extract_from_markdown(self, file_path: str) -> Optional[WorkOrderData]:
        """Extract structured data from FieldNation markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract basic information
            fn_work_order_id = self._extract_work_order_id(content)
            title = self._extract_title(content)
            company_name = self._extract_company(content)
            service_date = self._extract_service_date(content)
            location = self._extract_location(content)
            pay_amount = self._extract_pay_amount(content)
            status = self._extract_status(content)
            work_type = self._extract_work_type(content)
            service_type = self._extract_service_type(content)
            work_description = self._extract_work_description(content)
            time_logged = self._extract_time_logged(content)
            
            # Extract contacts
            manager_contact = self._extract_manager_contact(content)
            site_contact = self._extract_site_contact(content)
            
            # Analyze and categorize
            technologies_used = self._extract_technologies(content)
            skills_demonstrated = self._extract_skills(content)
            tools_required = self._extract_tools_required(content)
            client_type = self._categorize_client_type(company_name, work_description)
            industry = self._categorize_industry(company_name, work_description, location)
            complexity_level = self._assess_complexity(work_description, technologies_used)
            challenges_faced = self._extract_challenges(content)
            solutions_implemented = self._extract_solutions(content)
            
            return WorkOrderData(
                fn_work_order_id=fn_work_order_id or "unknown",
                title=title or "Unknown Work Order",
                company_name=company_name or "Unknown Company",
                service_date=service_date,
                location=location or "",
                pay_amount=pay_amount,
                status=status or "Unknown",
                work_type=work_type or "",
                service_type=service_type or "",
                work_description=work_description or "",
                technologies_used=technologies_used,
                skills_demonstrated=skills_demonstrated,
                tools_required=tools_required,
                client_type=client_type,
                industry=industry,
                manager_contact=manager_contact,
                site_contact=site_contact,
                time_logged=time_logged,
                complexity_level=complexity_level,
                challenges_faced=challenges_faced,
                solutions_implemented=solutions_implemented
            )
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def _extract_work_order_id(self, content: str) -> Optional[str]:
        """Extract work order ID from markdown content"""
        patterns = [
            r'# Work Order (\d+)',
            r'#(\d+)',
            r'Work Order #(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        return None

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract work order title"""
        patterns = [
            r'Title: (.+?)(?:\n|Company:)',
            r'On \d+/\d+/\d+\n(.+?)\nCompany:'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _extract_company(self, content: str) -> Optional[str]:
        """Extract company name"""
        patterns = [
            r'Company: (.+?)(?:\n|\t)',
            r'Company:\s*(.+?)(?:\n|\r)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        return None

    def _extract_service_date(self, content: str) -> Optional[str]:
        """Extract service date"""
        patterns = [
            r'On (\d+/\d+/\d+)',
            r'Service Date[:\s]+(\d+[-/]\d+[-/]\d+)',
            r'(\d+/\d+/\d+) at \d+:\d+'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                date_str = match.group(1)
                try:
                    # Convert to standard format
                    if '/' in date_str:
                        month, day, year = date_str.split('/')
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    pass
        return None

    def _extract_location(self, content: str) -> str:
        """Extract location information"""
        locations = []
        
        # Look for various location patterns
        patterns = [
            r'Location[:\s]+(.+?)(?:\n|Work)',
            r'(\w+, \w{2} \d{5})',
            r'(\w+, \w{2})',
            r'Work order site\s*(.+?)(?:\n|Commercial)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            locations.extend(matches)
        
        # Remove duplicates and clean
        unique_locations = list(set([loc.strip() for loc in locations if loc.strip()]))
        return '; '.join(unique_locations[:3])  # Limit to top 3 locations

    def _extract_pay_amount(self, content: str) -> Optional[float]:
        """Extract pay amount"""
        patterns = [
            r'Pay: Paid\s*\$([0-9,]+\.?\d*)',
            r'\$([0-9,]+\.?\d*)',
            r'Total\s*\$([0-9,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None

    def _extract_status(self, content: str) -> str:
        """Extract work order status"""
        if 'Paid' in content:
            return 'Paid'
        elif 'Completed' in content:
            return 'Completed'
        elif 'Approved' in content:
            return 'Approved'
        elif 'In Progress' in content:
            return 'In Progress'
        else:
            return 'Unknown'

    def _extract_work_type(self, content: str) -> str:
        """Extract type of work"""
        patterns = [
            r'Type of work:\s*(.+?)(?:\n|Additional)',
            r'Work Experience\s*Type of work:\s*(.+?)(?:\n|Additional)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_service_type(self, content: str) -> str:
        """Extract service type"""
        patterns = [
            r'Service Type:\s*(.+?)(?:\n|Work)',
            r'Service Types:\s*(.+?)(?:\n|Work)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_work_description(self, content: str) -> str:
        """Extract work description from service description section"""
        patterns = [
            r'Service Description\s*(.+?)(?=Tasks|Prep|WORK ORDERS|-----)',
            r'Justification for Tech:\s*(.+?)(?=Tech to|WORK ORDERS|-----)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                description = match.group(1).strip()
                # Clean up the description
                description = re.sub(r'\n+', ' ', description)
                description = re.sub(r'\s+', ' ', description)
                return description[:1000]  # Limit length
        return ""

    def _extract_time_logged(self, content: str) -> Optional[float]:
        """Extract time logged"""
        patterns = [
            r'Time Logged\s*([0-9.]+)\s*hours',
            r'(\d+\.?\d*)\s*Total hours'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _extract_manager_contact(self, content: str) -> Optional[str]:
        """Extract manager/site contact information"""
        patterns = [
            r'Manager/Site contact\s*(.+?)(?:\n|Print)',
            r'Work Order Manager[:\s]+(.+?)(?:\n|via)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        return None

    def _extract_site_contact(self, content: str) -> Optional[str]:
        """Extract site contact information"""
        patterns = [
            r'store Manager[:\s]+(.+?)(?:\n|,)',
            r'site contact[:\s]+(.+?)(?:\n|,)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_technologies(self, content: str) -> List[str]:
        """Extract technologies used from work order content"""
        technologies = set()
        content_lower = content.lower()
        
        # Technology mappings
        tech_keywords = {
            'Windows': ['windows', 'win 7', 'win 10', 'win 11', 'microsoft'],
            'Mac/Apple': ['mac', 'imac', 'apple', 'macbook', 'ios'],
            'Linux': ['linux', 'ubuntu', 'centos', 'redhat'],
            'HP': ['hp', 'hewlett packard', 'hp printer'],
            'Dell': ['dell', 'dell computer', 'dell laptop'],
            'Xerox': ['xerox', 'fuji xerox'],
            'POS Systems': ['pos', 'point of sale', 'register', 'kiosk'],
            'VoIP': ['voip', 'voice over ip', 'phone system'],
            'Network Equipment': ['router', 'switch', 'network', 'meraki', 'd-link'],
            'Printers': ['printer', 'print', 'scanning', 'copier'],
            'Medical Equipment': ['medical cart', 'healthcare cart', 'capsa'],
            'Security Systems': ['access control', 'security camera', 'surveillance'],
            'RDP/Remote Access': ['rdp', 'remote desktop', 'teamviewer', 'vnc'],
            'Active Directory': ['active directory', 'ad', 'domain controller'],
            'Office 365': ['office 365', 'o365', 'sharepoint', 'teams'],
            'Networking Protocols': ['tcp/ip', 'dhcp', 'dns', 'wifi'],
            'Database Systems': ['sql server', 'mysql', 'oracle', 'database'],
            'Virtualization': ['vmware', 'hyper-v', 'virtual machine', 'vm']
        }
        
        for tech, keywords in tech_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                technologies.add(tech)
        
        return list(technologies)

    def _extract_skills(self, content: str) -> List[str]:
        """Extract demonstrated skills from work order content"""
        skills = set()
        content_lower = content.lower()
        
        # Skills mappings
        skill_keywords = {
            'Hardware Installation': ['install', 'setup', 'deployment', 'replacement', 'mounting'],
            'Troubleshooting': ['troubleshoot', 'diagnose', 'repair', 'fix', 'resolve'],
            'System Configuration': ['configuration', 'config', 'setup', 'configure'],
            'Network Administration': ['network', 'connectivity', 'cable', 'routing'],
            'Customer Service': ['onsite', 'client', 'customer', 'site contact'],
            'Project Management': ['project', 'lead', 'coordination', 'manage'],
            'Technical Support': ['support', 'maintenance', 'service', 'help'],
            'Documentation': ['document', 'notes', 'report', 'deliverable'],
            'Testing & Validation': ['test', 'validate', 'verify', 'check'],
            'Training': ['train', 'teach', 'instruct', 'demo'],
            'Problem Solving': ['problem', 'issue', 'challenge', 'solution'],
            'Time Management': ['schedule', 'deadline', 'efficient', 'timely'],
            'Quality Assurance': ['quality', 'standard', 'compliance', 'audit'],
            'Security Implementation': ['security', 'access', 'authentication', 'encryption']
        }
        
        for skill, keywords in skill_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                skills.add(skill)
        
        return list(skills)

    def _extract_tools_required(self, content: str) -> List[str]:
        """Extract tools and equipment required"""
        tools = set()
        content_lower = content.lower()
        
        # Look for materials/equipment section
        materials_match = re.search(r'MATERIAL/EQUIPMENT REQUIRED:(.+?)(?=DELIVERABLES|Tasks|$)', content, re.DOTALL)
        if materials_match:
            materials_section = materials_match.group(1).lower()
            
            tool_keywords = {
                'Allen Wrenches': ['allen wrench', 'hex key'],
                'Screwdrivers': ['screwdriver', 'phillips', 'flathead'],
                'Network Tools': ['crimper', 'cable tester', 'toner', 'fish tape'],
                'Power Tools': ['drill', 'cordless drill', 'bit set'],
                'Measuring Tools': ['measuring tape', 'level', 'torpedo level'],
                'Hand Tools': ['hammer', 'hack saw', 'box cutter', 'nut driver'],
                'Computer Tools': ['laptop', 'tablet', 'usb keyboard', 'mouse'],
                'Network Cables': ['cat6', 'cat5e', 'ethernet', 'rj45'],
                'Electrical Supplies': ['electrical tape', 'zip ties', 'keystones'],
                'Test Equipment': ['network tester', 'multimeter', 'hdmi cable'],
                'Connectivity': ['hotspot', 'cell phone', 'wifi'],
                'Documentation': ['label maker', 'camera', 'measuring tape']
            }
            
            for tool, keywords in tool_keywords.items():
                if any(keyword in materials_section for keyword in keywords):
                    tools.add(tool)
        
        return list(tools)

    def _categorize_client_type(self, company_name: str, work_description: str) -> str:
        """Categorize client type based on company and work description"""
        company_lower = company_name.lower() if company_name else ""
        desc_lower = work_description.lower() if work_description else ""
        
        # Client type indicators
        if any(word in company_lower + desc_lower for word in ['hospital', 'medical', 'healthcare', 'clinic']):
            return 'Healthcare'
        elif any(word in company_lower + desc_lower for word in ['bank', 'financial', 'credit', 'investment']):
            return 'Financial'
        elif any(word in company_lower + desc_lower for word in ['retail', 'store', 'mall', 'shop', 'restaurant']):
            return 'Retail'
        elif any(word in company_lower + desc_lower for word in ['government', 'federal', 'state', 'municipal']):
            return 'Government'
        elif any(word in company_lower + desc_lower for word in ['school', 'university', 'education', 'college']):
            return 'Education'
        elif any(word in company_lower + desc_lower for word in ['warehouse', 'logistics', 'distribution']):
            return 'Logistics'
        else:
            return 'Enterprise'

    def _categorize_industry(self, company_name: str, work_description: str, location: str) -> str:
        """Categorize industry based on available information"""
        combined_text = f"{company_name} {work_description} {location}".lower()
        
        industry_keywords = {
            'Healthcare': ['medical', 'hospital', 'healthcare', 'clinic', 'pharmacy'],
            'Financial Services': ['bank', 'financial', 'credit', 'investment', 'insurance'],
            'Retail': ['retail', 'store', 'mall', 'shop', 'restaurant', 'pos', 'kiosk'],
            'Technology': ['tech', 'software', 'it services', 'computer'],
            'Education': ['school', 'university', 'education', 'college', 'learning'],
            'Government': ['government', 'federal', 'state', 'municipal', 'public'],
            'Manufacturing': ['manufacturing', 'factory', 'production', 'industrial'],
            'Logistics': ['warehouse', 'logistics', 'distribution', 'shipping'],
            'Telecommunications': ['telecom', 'phone', 'voip', 'communication'],
            'Real Estate': ['real estate', 'property', 'building', 'facility']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                return industry
        
        return 'General Services'

    def _assess_complexity(self, work_description: str, technologies: List[str]) -> str:
        """Assess complexity level based on work description and technologies"""
        desc_lower = work_description.lower() if work_description else ""
        
        # Basic indicators
        basic_indicators = ['basic', 'simple', 'routine', 'standard', 'replace']
        
        # Advanced indicators  
        advanced_indicators = ['complex', 'advanced', 'integration', 'custom', 'troubleshoot', 'diagnose']
        
        # Expert indicators
        expert_indicators = ['architect', 'design', 'implement', 'migrate', 'optimization']
        
        if any(indicator in desc_lower for indicator in expert_indicators) or len(technologies) >= 5:
            return 'Expert'
        elif any(indicator in desc_lower for indicator in advanced_indicators) or len(technologies) >= 3:
            return 'Advanced'
        elif any(indicator in desc_lower for indicator in basic_indicators) or len(technologies) <= 1:
            return 'Basic'
        else:
            return 'Intermediate'

    def _extract_challenges(self, content: str) -> List[str]:
        """Extract challenges faced from work order content"""
        challenges = []
        
        # Look for common challenge indicators
        challenge_patterns = [
            r'(?:challenge|problem|issue|difficulty)[:\s]+(.+?)(?:\n|\.)',
            r'(?:stuck|broken|failed|not working)[:\s]+(.+?)(?:\n|\.)',
            r'delay in (.+?)(?:\n|\.)'
        ]
        
        for pattern in challenge_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            challenges.extend([match.strip() for match in matches if match.strip()])
        
        return challenges[:5]  # Limit to top 5 challenges

    def _extract_solutions(self, content: str) -> List[str]:
        """Extract solutions implemented"""
        solutions = []
        
        # Look for solution indicators
        solution_patterns = [
            r'(?:solution|resolved|fixed|completed)[:\s]+(.+?)(?:\n|\.)',
            r'(?:implemented|installed|configured)[:\s]+(.+?)(?:\n|\.)',
            r'was able to (.+?)(?:\n|\.)'
        ]
        
        for pattern in solution_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            solutions.extend([match.strip() for match in matches if match.strip()])
        
        return solutions[:5]  # Limit to top 5 solutions

    def save_work_order(self, work_order: WorkOrderData, source_file: str):
        """Save work order data to enhanced database"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO work_orders_enhanced (
                    fn_work_order_id, title, company_name, service_date, location,
                    pay_amount, status, work_type, service_type, work_description,
                    technologies_used, skills_demonstrated, tools_required,
                    client_type, industry, manager_contact, site_contact,
                    time_logged, complexity_level, challenges_faced,
                    solutions_implemented, extracted_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work_order.fn_work_order_id,
                work_order.title,
                work_order.company_name,
                work_order.service_date,
                work_order.location,
                work_order.pay_amount,
                work_order.status,
                work_order.work_type,
                work_order.service_type,
                work_order.work_description,
                json.dumps(work_order.technologies_used),
                json.dumps(work_order.skills_demonstrated),
                json.dumps(work_order.tools_required),
                work_order.client_type,
                work_order.industry,
                work_order.manager_contact,
                work_order.site_contact,
                work_order.time_logged,
                work_order.complexity_level,
                json.dumps(work_order.challenges_faced),
                json.dumps(work_order.solutions_implemented),
                source_file
            ))
            
            work_order_id = cursor.lastrowid
            
            # Update related intelligence tables
            self._update_skills_taxonomy(work_order.skills_demonstrated)
            self._update_technologies_catalog(work_order.technologies_used)
            self._update_client_intelligence(work_order)
            self._update_service_locations(work_order.location)
            
            conn.commit()
            return work_order_id
            
        except Exception as e:
            print(f"Error saving work order {work_order.fn_work_order_id}: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def _update_skills_taxonomy(self, skills: List[str]):
        """Update skills taxonomy table"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        for skill in skills:
            cursor.execute("""
                INSERT OR IGNORE INTO skills_taxonomy (skill_name, skill_category)
                VALUES (?, ?)
            """, (skill, self._categorize_skill(skill)))
        
        conn.commit()
        conn.close()

    def _update_technologies_catalog(self, technologies: List[str]):
        """Update technologies catalog"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        for tech in technologies:
            cursor.execute("""
                INSERT OR IGNORE INTO technologies_catalog (technology_name, category)
                VALUES (?, ?)
            """, (tech, self._categorize_technology(tech)))
        
        conn.commit()
        conn.close()

    def _update_client_intelligence(self, work_order: WorkOrderData):
        """Update client intelligence table"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Check if client exists
        cursor.execute("SELECT id, work_order_count, total_value FROM client_intelligence WHERE company_name = ?", 
                      (work_order.company_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing client
            new_count = existing['work_order_count'] + 1
            new_value = existing['total_value'] + (work_order.pay_amount or 0)
            
            cursor.execute("""
                UPDATE client_intelligence 
                SET work_order_count = ?, total_value = ?, last_service_date = ?, updated_at = ?
                WHERE company_name = ?
            """, (new_count, new_value, work_order.service_date, datetime.now(), work_order.company_name))
        else:
            # Insert new client
            cursor.execute("""
                INSERT INTO client_intelligence (
                    company_name, industry, client_type, work_order_count, 
                    total_value, last_service_date
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                work_order.company_name,
                work_order.industry,
                work_order.client_type,
                1,
                work_order.pay_amount or 0,
                work_order.service_date
            ))
        
        conn.commit()
        conn.close()

    def _update_service_locations(self, location: str):
        """Update service locations table"""
        if not location:
            return
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Simple location parsing
        parts = location.split(',')
        if len(parts) >= 2:
            city = parts[0].strip()
            state = parts[1].strip()
            
            cursor.execute("""
                INSERT OR IGNORE INTO service_locations (city, state, service_count)
                VALUES (?, ?, 1)
            """, (city, state))
            
            cursor.execute("""
                UPDATE service_locations 
                SET service_count = service_count + 1 
                WHERE city = ? AND state = ?
            """, (city, state))
        
        conn.commit()
        conn.close()

    def _categorize_skill(self, skill: str) -> str:
        """Categorize skill into broader categories"""
        skill_lower = skill.lower()
        
        if any(word in skill_lower for word in ['hardware', 'install', 'setup', 'mount']):
            return 'Hardware'
        elif any(word in skill_lower for word in ['network', 'connectivity', 'routing']):
            return 'Networking'
        elif any(word in skill_lower for word in ['software', 'config', 'system']):
            return 'Software'
        elif any(word in skill_lower for word in ['customer', 'client', 'service']):
            return 'Customer Service'
        elif any(word in skill_lower for word in ['project', 'manage', 'lead']):
            return 'Management'
        elif any(word in skill_lower for word in ['troubleshoot', 'diagnose', 'problem']):
            return 'Problem Solving'
        else:
            return 'Technical'

    def _categorize_technology(self, technology: str) -> str:
        """Categorize technology into broader categories"""
        tech_lower = technology.lower()
        
        if any(word in tech_lower for word in ['windows', 'mac', 'linux', 'operating']):
            return 'Operating Systems'
        elif any(word in tech_lower for word in ['router', 'switch', 'network', 'voip']):
            return 'Networking'
        elif any(word in tech_lower for word in ['hp', 'dell', 'xerox', 'printer']):
            return 'Hardware'
        elif any(word in tech_lower for word in ['pos', 'kiosk', 'register']):
            return 'Point of Sale'
        elif any(word in tech_lower for word in ['office', 'software', 'application']):
            return 'Software'
        elif any(word in tech_lower for word in ['security', 'access', 'camera']):
            return 'Security'
        else:
            return 'General'

    def process_all_markdown_files(self, directory: str = "downloaded work orders") -> Dict[str, int]:
        """Process all markdown files in the directory"""
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'duplicates': 0
        }
        
        markdown_files = list(Path(directory).glob("*.md"))
        print(f"🔄 Processing {len(markdown_files)} markdown files...")
        
        for file_path in markdown_files:
            results['processed'] += 1
            
            try:
                work_order = self.extract_from_markdown(str(file_path))
                if work_order:
                    work_order_id = self.save_work_order(work_order, str(file_path))
                    if work_order_id:
                        results['successful'] += 1
                        if results['successful'] % 10 == 0:
                            print(f"   ✅ Processed {results['successful']} work orders...")
                    else:
                        results['duplicates'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                print(f"   ❌ Error processing {file_path}: {e}")
                results['failed'] += 1
        
        return results

# Example usage
if __name__ == "__main__":
    processor = FieldNationDataProcessor()
    results = processor.process_all_markdown_files()
    
    print(f"""
🎉 Processing Complete!
   📁 Files processed: {results['processed']}
   ✅ Successfully imported: {results['successful']}
   ❌ Failed: {results['failed']}
   🔄 Duplicates skipped: {results['duplicates']}
    """)