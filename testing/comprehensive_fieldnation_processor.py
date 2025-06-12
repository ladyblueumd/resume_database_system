#!/usr/bin/env python3
"""
Comprehensive FieldNation Work Order Processor
Processes both markdown and PDF work order files with advanced extraction and database integration
"""

import sqlite3
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import PyPDF2
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WorkOrderData:
    """Comprehensive work order data structure"""
    fn_work_order_id: str
    title: str
    work_order_date: Optional[str] = None
    service_date: Optional[str] = None
    completion_date: Optional[str] = None
    
    # Location Information
    location: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    site_address: str = ""
    site_type: str = ""
    
    # Client/Company Information
    buyer_company: str = ""
    client_name: str = ""
    manager_name: str = ""
    manager_contact: str = ""
    site_contact: str = ""
    contact_phone: str = ""
    client_email: str = ""
    
    # Financial Information
    pay_amount: Optional[float] = None
    hourly_rate: Optional[float] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    travel_reimbursement: Optional[float] = None
    
    # Work Classification
    work_type: str = ""
    service_type: str = ""
    industry_category: str = ""
    complexity_level: str = ""
    
    # Work Details
    work_description: str = ""
    scope_of_work: str = ""
    service_description: str = ""
    special_instructions: str = ""
    dress_code: str = ""
    
    # Technical Requirements
    required_skills: List[str] = None
    required_tools: List[str] = None
    required_software: List[str] = None
    technologies_used: List[str] = None
    hardware_involved: List[str] = None
    
    # Qualifications
    work_order_qualifications: Dict[str, Any] = None
    certifications_required: List[str] = None
    experience_required: str = ""
    security_clearance_required: str = ""
    
    # Status and Performance
    status: str = ""
    completion_status: str = ""
    quality_rating: Optional[float] = None
    client_satisfaction: Optional[float] = None
    
    # Problem Solving
    challenges_encountered: List[str] = None
    solutions_implemented: List[str] = None
    lessons_learned: str = ""
    
    # Deliverables and Documentation
    deliverables: List[str] = None
    photos_required: bool = False
    documentation_provided: List[str] = None
    
    # Schedule Information
    scheduled_start_time: Optional[str] = None
    scheduled_end_time: Optional[str] = None
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    time_zone: str = ""
    
    # Resume Integration
    include_in_resume: bool = True
    highlight_project: bool = False
    resume_bullet_points: List[str] = None
    achievements: List[str] = None
    
    # Source and Metadata
    data_source: str = ""
    source_file_path: str = ""
    extraction_quality: Optional[float] = None
    needs_review: bool = False

    def __post_init__(self):
        """Initialize empty lists and dicts for None values"""
        if self.required_skills is None:
            self.required_skills = []
        if self.required_tools is None:
            self.required_tools = []
        if self.required_software is None:
            self.required_software = []
        if self.technologies_used is None:
            self.technologies_used = []
        if self.hardware_involved is None:
            self.hardware_involved = []
        if self.work_order_qualifications is None:
            self.work_order_qualifications = {}
        if self.certifications_required is None:
            self.certifications_required = []
        if self.challenges_encountered is None:
            self.challenges_encountered = []
        if self.solutions_implemented is None:
            self.solutions_implemented = []
        if self.deliverables is None:
            self.deliverables = []
        if self.documentation_provided is None:
            self.documentation_provided = []
        if self.resume_bullet_points is None:
            self.resume_bullet_points = []
        if self.achievements is None:
            self.achievements = []


class ComprehensiveFieldNationProcessor:
    """Main processor for comprehensive FieldNation work order analysis"""
    
    def __init__(self, db_path: str = 'resume_database.db'):
        self.db_path = db_path
        self.setup_database()
        
        # Skill categories for classification
        self.skill_categories = {
            'technical': ['troubleshooting', 'installation', 'configuration', 'programming', 'networking', 'security'],
            'software': ['windows', 'linux', 'office', 'adobe', 'autocad', 'sql', 'python', 'java'],
            'hardware': ['servers', 'routers', 'switches', 'printers', 'pos', 'terminals', 'cabling'],
            'soft_skills': ['communication', 'leadership', 'teamwork', 'problem-solving', 'customer service'],
            'industry_specific': ['healthcare', 'retail', 'banking', 'education', 'government', 'manufacturing']
        }
        
        # Industry classification patterns
        self.industry_patterns = {
            'Healthcare': ['hospital', 'clinic', 'medical', 'healthcare', 'patient', 'doctor', 'nurse'],
            'Retail': ['store', 'retail', 'pos', 'register', 'customer', 'sales', 'inventory'],
            'Financial': ['bank', 'credit union', 'financial', 'atm', 'teller', 'loan', 'investment'],
            'Education': ['school', 'university', 'college', 'classroom', 'student', 'teacher', 'campus'],
            'Government': ['government', 'federal', 'state', 'municipal', 'courthouse', 'dmv', 'irs'],
            'Manufacturing': ['factory', 'plant', 'manufacturing', 'production', 'assembly', 'warehouse']
        }

    def get_db_connection(self):
        """Create and return a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def setup_database(self):
        """Create database tables using the enhanced schema"""
        conn = self.get_db_connection()
        
        # Create the main fieldnation_work_orders table with all necessary fields
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fieldnation_work_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fn_work_order_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    work_order_date DATE,
                    service_date DATE,
                    completion_date DATE,
                    
                    -- Location Information  
                    location TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    site_address TEXT,
                    site_type TEXT,
                    
                    -- Client/Company Information
                    buyer_company TEXT NOT NULL,
                    client_name TEXT,
                    manager_name TEXT,
                    manager_contact TEXT,
                    site_contact TEXT,
                    contact_phone TEXT,
                    client_email TEXT,
                    
                    -- Financial Information
                    pay_amount DECIMAL(10,2),
                    hourly_rate DECIMAL(10,2),
                    estimated_hours DECIMAL(4,2),
                    actual_hours DECIMAL(4,2),
                    travel_reimbursement DECIMAL(10,2),
                    
                    -- Work Classification
                    work_type TEXT,
                    service_type TEXT,
                    industry_category TEXT,
                    complexity_level TEXT,
                    
                    -- Work Details
                    work_description TEXT,
                    scope_of_work TEXT,
                    service_description TEXT,
                    special_instructions TEXT,
                    dress_code TEXT,
                    
                    -- Technical Requirements (JSON arrays)
                    required_skills TEXT,
                    required_tools TEXT,
                    required_software TEXT,
                    technologies_used TEXT,
                    hardware_involved TEXT,
                    
                    -- Qualifications
                    work_order_qualifications TEXT,
                    certifications_required TEXT,
                    experience_required TEXT,
                    security_clearance_required TEXT,
                    
                    -- Status and Performance
                    status TEXT,
                    completion_status TEXT,
                    quality_rating DECIMAL(3,2),
                    client_satisfaction DECIMAL(3,2),
                    
                    -- Problem Solving
                    challenges_encountered TEXT,
                    solutions_implemented TEXT,
                    lessons_learned TEXT,
                    
                    -- Deliverables and Documentation
                    deliverables TEXT,
                    photos_required BOOLEAN DEFAULT FALSE,
                    documentation_provided TEXT,
                    
                    -- Schedule Information
                    scheduled_start_time TIME,
                    scheduled_end_time TIME,
                    actual_start_time TIME,
                    actual_end_time TIME,
                    time_zone TEXT,
                    
                    -- Resume Integration
                    include_in_resume BOOLEAN DEFAULT TRUE,
                    highlight_project BOOLEAN DEFAULT FALSE,
                    resume_bullet_points TEXT,
                    achievements TEXT,
                    
                    -- Source and Metadata
                    data_source TEXT,
                    source_file_path TEXT,
                    extraction_quality DECIMAL(3,2),
                    needs_review BOOLEAN DEFAULT FALSE,
                    
                    -- Timestamps
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    extracted_at DATETIME
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_fn_id ON fieldnation_work_orders(fn_work_order_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_company ON fieldnation_work_orders(buyer_company)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_date ON fieldnation_work_orders(service_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_location ON fieldnation_work_orders(city, state)")
            
            conn.commit()
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
        finally:
            conn.close()

    def process_markdown_file(self, file_path: str) -> Optional[WorkOrderData]:
        """Process a markdown work order file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            work_order = self._extract_markdown_data(content)
            work_order.data_source = 'markdown'
            work_order.source_file_path = file_path
            
            return work_order
            
        except Exception as e:
            logger.error(f"Error processing markdown file {file_path}: {e}")
            return None

    def process_pdf_file(self, file_path: str) -> Optional[WorkOrderData]:
        """Process a PDF work order file"""
        try:
            text_content = self._extract_pdf_text(file_path)
            if not text_content:
                logger.warning(f"No text extracted from PDF: {file_path}")
                return None
            
            work_order = self._extract_pdf_data(text_content)
            work_order.data_source = 'pdf'
            work_order.source_file_path = file_path
            
            return work_order
            
        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {e}")
            return None

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF using available libraries"""
        if pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    return text
            except Exception as e:
                logger.warning(f"pdfplumber failed for {file_path}: {e}")
        
        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"PDF text extraction failed for {file_path}: {e}")
            return ""

    def _extract_markdown_data(self, content: str) -> WorkOrderData:
        """Extract data from markdown content"""
        work_order = WorkOrderData(
            fn_work_order_id=self._extract_work_order_id(content),
            title=self._extract_title(content) or "Unknown Title"
        )
        
        # Basic information
        work_order.buyer_company = self._extract_company(content)
        work_order.service_date = self._extract_service_date(content)
        work_order.location = self._extract_location(content)
        work_order.pay_amount = self._extract_pay_amount(content)
        work_order.status = self._extract_status(content)
        work_order.work_type = self._extract_work_type(content)
        work_order.service_type = self._extract_service_type(content)
        work_order.work_description = self._extract_work_description(content)
        
        # Contact information
        work_order.manager_contact = self._extract_manager_contact(content)
        work_order.site_contact = self._extract_site_contact(content)
        
        # Technical details
        work_order.technologies_used = self._extract_technologies(content)
        work_order.required_skills = self._extract_skills(content)
        work_order.required_tools = self._extract_tools_required(content)
        
        # Time tracking
        work_order.actual_hours = self._extract_time_logged(content)
        
        # Analysis
        work_order.industry_category = self._categorize_industry(work_order.buyer_company, work_order.work_description, work_order.location)
        work_order.complexity_level = self._assess_complexity(work_order.work_description, work_order.technologies_used)
        
        # Challenges and solutions
        work_order.challenges_encountered = self._extract_challenges(content)
        work_order.solutions_implemented = self._extract_solutions(content)
        
        # Qualifications
        work_order.work_order_qualifications = self._extract_qualifications(content)
        
        return work_order

    def _extract_pdf_data(self, content: str) -> WorkOrderData:
        """Extract data from PDF text content"""
        # PDF processing uses same extraction methods as markdown
        return self._extract_markdown_data(content)

    def _extract_work_order_id(self, content: str) -> str:
        """Extract work order ID from content"""
        patterns = [
            r'#(\d+)',
            r'Work Order (\d+)',
            r'WO[#\s]*(\d+)',
            r'work_order_(\d+)',
            r'workorders/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "unknown"

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract work order title"""
        patterns = [
            r'# Work Order \d+\n\n([^\n]+)',
            r'Title: ([^\n]+)',
            r'Job Title: ([^\n]+)',
            r'Work Order: ([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if len(title) > 5 and not title.isdigit():
                    return title
        
        return None

    def _extract_company(self, content: str) -> str:
        """Extract company name"""
        patterns = [
            r'Company: ([^\n]+)',
            r'Client: ([^\n]+)', 
            r'Buyer: ([^\n]+)',
            r'Company:\s*([^\n\r]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                company = re.sub(r'\s*\(.*?\)\s*$', '', company)
                return company
        
        return "Unknown Company"

    def _extract_service_date(self, content: str) -> Optional[str]:
        """Extract service date"""
        patterns = [
            r'On (\d{1,2}/\d{1,2}/\d{4})',
            r'Date: (\d{1,2}/\d{1,2}/\d{4})',
            r'Service Date: ([^\n]+)',
            r'(\w+, \w+ \d+, \d{4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def _extract_location(self, content: str) -> str:
        """Extract location information"""
        patterns = [
            r'Location[:\s]+([^\n]+)',
            r'Address[:\s]+([^\n]+)',
            r'Site[:\s]+([^\n]+)',
            r'([A-Z][A-Z], [A-Z]{2} \d{5})',
            r'([A-Z][^,]+, [A-Z]{2})',
            r'Work order site\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 3:
                    return location
        
        return "Unknown Location"

    def _extract_pay_amount(self, content: str) -> Optional[float]:
        """Extract pay amount"""
        patterns = [
            r'Pay: .*?\$(\d+\.?\d*)',
            r'Total.*?\$(\d+\.?\d*)',
            r'Rate.*?\$(\d+\.?\d*)',
            r'\$(\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match)
                    if 5 <= amount <= 10000:
                        return amount
                except ValueError:
                    continue
        
        return None

    def _extract_status(self, content: str) -> str:
        """Extract work order status"""
        status_patterns = [
            r'Status: ([^\n]+)',
            r'Pay: (Paid|Pending|Unpaid)',
            r'(Completed|In Progress|Pending|Cancelled)'
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        if 'completed' in content.lower() or 'paid' in content.lower():
            return 'Completed'
        
        return 'Unknown'

    def _extract_work_type(self, content: str) -> str:
        """Extract type of work"""
        patterns = [
            r'Type of work:\s*([^\n]+)',
            r'Service Type:\s*([^\n]+)',
            r'Work Type:\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        if any(term in content.lower() for term in ['install', 'installation']):
            return 'Installation'
        elif any(term in content.lower() for term in ['repair', 'fix', 'troubleshoot']):
            return 'Repair'
        elif any(term in content.lower() for term in ['maintenance', 'service']):
            return 'Maintenance'
        
        return 'General Tasks'

    def _extract_service_type(self, content: str) -> str:
        """Extract service type"""
        patterns = [
            r'Service Type:\s*([^\n]+)',
            r'Installation Type:\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                service_type = match.group(1).strip()
                if service_type.lower() != 'no service type specified':
                    return service_type
        
        return 'General Service'

    def _extract_work_description(self, content: str) -> str:
        """Extract work description"""
        patterns = [
            r'Service Description\s*(.+?)(?=\n[A-Z]|\nView Less|\nTasks|\n\n|\Z)',
            r'Description\s*(.+?)(?=\n[A-Z]|\nView Less|\nTasks|\n\n|\Z)',
            r'Scope[:\s]+(.+?)(?=\n[A-Z]|\nView Less|\nTasks|\n\n|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                description = re.sub(r'\n+', ' ', description)
                description = re.sub(r'\s+', ' ', description)
                if len(description) > 50:
                    return description
        
        return ""

    def _extract_technologies(self, content: str) -> List[str]:
        """Extract technologies mentioned in the work order"""
        tech_patterns = [
            r'\b(?:server|router|switch|firewall|printer|scanner|desktop|laptop|tablet|phone|monitor|keyboard|mouse|ups|cable|ethernet|fiber)\b',
            r'\b(?:windows|linux|ubuntu|centos|office|outlook|excel|word|adobe|autocad|sql|oracle|mysql|vmware|citrix)\b',
            r'\b(?:pos|point of sale|terminal|register|aloha|micros|ncr|diebold|epson|zebra|hp|dell|cisco|microsoft)\b',
            r'\b(?:wifi|wireless|lan|wan|vpn|tcp/ip|dhcp|dns|active directory|domain)\b'
        ]
        
        technologies = []
        content_lower = content.lower()
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            technologies.extend(matches)
        
        unique_technologies = list(set(tech.strip().title() for tech in technologies if len(tech.strip()) > 2))
        return unique_technologies

    def _extract_skills(self, content: str) -> List[str]:
        """Extract skills demonstrated in the work order"""
        skill_keywords = [
            'troubleshooting', 'installation', 'configuration', 'setup', 'repair', 'maintenance',
            'networking', 'cabling', 'programming', 'scripting', 'testing', 'documentation',
            'customer service', 'communication', 'leadership', 'teamwork', 'problem solving',
            'project management', 'time management', 'technical support', 'training'
        ]
        
        content_lower = content.lower()
        found_skills = []
        
        for skill in skill_keywords:
            if skill in content_lower:
                found_skills.append(skill.title())
        
        return found_skills

    def _extract_tools_required(self, content: str) -> List[str]:
        """Extract tools required for the work order"""
        tool_patterns = [
            r'bring\s+(?:a\s+)?([^.\n]+?)(?:\.|,|\n)',
            r'tools?\s*(?:required|needed):\s*([^.\n]+)',
            r'equipment:\s*([^.\n]+)'
        ]
        
        tools = []
        content_lower = content.lower()
        
        for pattern in tool_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str):
                    tool_list = re.split(r'[,;]', match)
                    tools.extend([tool.strip().title() for tool in tool_list if len(tool.strip()) > 2])
        
        common_tools = ['screwdriver', 'drill', 'cable tester', 'multimeter', 'crimper', 'ladder', 'toolkit', 'wire cutters', 'box cutters']
        for tool in common_tools:
            if tool in content_lower and tool.title() not in tools:
                tools.append(tool.title())
        
        return list(set(tools))

    def _extract_time_logged(self, content: str) -> Optional[float]:
        """Extract time logged/worked"""
        patterns = [
            r'Time Logged\s*(\d+\.?\d*)\s*hours?',
            r'Logged by.*?(\d+\.?\d*)\s*hours?',
            r'worked\s+(\d+\.?\d*)\s*hours?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None

    def _extract_manager_contact(self, content: str) -> Optional[str]:
        """Extract manager contact information"""
        patterns = [
            r'Manager/Site contact\s*([^\n]+)',
            r'Manager:\s*([^\n]+)',
            r'Site Manager:\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def _extract_site_contact(self, content: str) -> Optional[str]:
        """Extract site contact information"""
        patterns = [
            r'Site contact\s*([^\n]+)',
            r'On-site contact:\s*([^\n]+)',
            r'Contact:\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def _categorize_industry(self, company_name: str, work_description: str, location: str) -> str:
        """Categorize the industry based on company name and work description"""
        combined_text = f"{company_name} {work_description} {location}".lower()
        
        for industry, keywords in self.industry_patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                return industry
        
        return 'Technology Services'

    def _assess_complexity(self, work_description: str, technologies: List[str]) -> str:
        """Assess the complexity level of the work order"""
        description_lower = work_description.lower()
        
        high_complexity_indicators = ['programming', 'scripting', 'server', 'network configuration', 'security', 'multiple systems']
        medium_complexity_indicators = ['installation', 'configuration', 'troubleshooting', 'repair']
        
        complexity_score = 0
        
        for indicator in high_complexity_indicators:
            if indicator in description_lower:
                complexity_score += 3
        
        for indicator in medium_complexity_indicators:
            if indicator in description_lower:
                complexity_score += 1
        
        if len(technologies) > 5:
            complexity_score += 2
        elif len(technologies) > 2:
            complexity_score += 1
        
        if complexity_score >= 6:
            return 'Expert'
        elif complexity_score >= 4:
            return 'High'
        elif complexity_score >= 2:
            return 'Medium'
        else:
            return 'Low'

    def _extract_challenges(self, content: str) -> List[str]:
        """Extract challenges mentioned in the work order"""
        challenge_patterns = [
            r'challenge[s]?[:\s]+([^.\n]+)',
            r'problem[s]?[:\s]+([^.\n]+)',
            r'issue[s]?[:\s]+([^.\n]+)',
            r'difficult[y]?[:\s]+([^.\n]+)'
        ]
        
        challenges = []
        for pattern in challenge_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            challenges.extend([match.strip() for match in matches if len(match.strip()) > 10])
        
        return challenges

    def _extract_solutions(self, content: str) -> List[str]:
        """Extract solutions mentioned in the work order"""
        solution_patterns = [
            r'solution[s]?[:\s]+([^.\n]+)',
            r'resolved[:\s]+([^.\n]+)',
            r'fixed[:\s]+([^.\n]+)',
            r'implemented[:\s]+([^.\n]+)'
        ]
        
        solutions = []
        for pattern in solution_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            solutions.extend([match.strip() for match in matches if len(match.strip()) > 10])
        
        return solutions

    def _extract_qualifications(self, content: str) -> Dict[str, Any]:
        """Extract work order qualifications"""
        qualifications = {}
        
        qual_section_match = re.search(r'Work Order Qualifications\s*(.+?)(?=\n[A-Z]|\nService Description|\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        
        if qual_section_match:
            qual_text = qual_section_match.group(1)
            
            qual_patterns = [
                (r'Type\s+Qualification\s+Type of work\s+([^\n]+)', 'work_type'),
                (r'Hardware\s+([^\n]+)', 'hardware_requirements'),
                (r'Software\s+([^\n]+)', 'software_requirements'),
                (r'Experience\s+([^\n]+)', 'experience_requirements'),
                (r'Certification\s+([^\n]+)', 'certification_requirements')
            ]
            
            for pattern, key in qual_patterns:
                match = re.search(pattern, qual_text, re.IGNORECASE)
                if match:
                    qualifications[key] = match.group(1).strip()
        
        return qualifications

    def save_work_order(self, work_order: WorkOrderData) -> bool:
        """Save work order to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Convert lists and dicts to JSON strings
            work_order_dict = asdict(work_order)
            for key, value in work_order_dict.items():
                if isinstance(value, (list, dict)):
                    work_order_dict[key] = json.dumps(value)
            
            # Insert work order
            cursor.execute("""
                INSERT OR REPLACE INTO fieldnation_work_orders (
                    fn_work_order_id, title, work_order_date, service_date, completion_date,
                    location, city, state, zip_code, site_address, site_type,
                    buyer_company, client_name, manager_name, manager_contact, site_contact, contact_phone, client_email,
                    pay_amount, hourly_rate, estimated_hours, actual_hours, travel_reimbursement,
                    work_type, service_type, industry_category, complexity_level,
                    work_description, scope_of_work, service_description, special_instructions, dress_code,
                    required_skills, required_tools, required_software, technologies_used, hardware_involved,
                    work_order_qualifications, certifications_required, experience_required, security_clearance_required,
                    status, completion_status, quality_rating, client_satisfaction,
                    challenges_encountered, solutions_implemented, lessons_learned,
                    deliverables, photos_required, documentation_provided,
                    scheduled_start_time, scheduled_end_time, actual_start_time, actual_end_time, time_zone,
                    include_in_resume, highlight_project, resume_bullet_points, achievements,
                    data_source, source_file_path, extraction_quality, needs_review,
                    created_at, updated_at, extracted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work_order_dict['fn_work_order_id'], work_order_dict['title'], work_order_dict['work_order_date'],
                work_order_dict['service_date'], work_order_dict['completion_date'],
                work_order_dict['location'], work_order_dict['city'], work_order_dict['state'], 
                work_order_dict['zip_code'], work_order_dict['site_address'], work_order_dict['site_type'],
                work_order_dict['buyer_company'], work_order_dict['client_name'], work_order_dict['manager_name'],
                work_order_dict['manager_contact'], work_order_dict['site_contact'], work_order_dict['contact_phone'],
                work_order_dict['client_email'], work_order_dict['pay_amount'], work_order_dict['hourly_rate'],
                work_order_dict['estimated_hours'], work_order_dict['actual_hours'], work_order_dict['travel_reimbursement'],
                work_order_dict['work_type'], work_order_dict['service_type'], work_order_dict['industry_category'],
                work_order_dict['complexity_level'], work_order_dict['work_description'], work_order_dict['scope_of_work'],
                work_order_dict['service_description'], work_order_dict['special_instructions'], work_order_dict['dress_code'],
                work_order_dict['required_skills'], work_order_dict['required_tools'], work_order_dict['required_software'],
                work_order_dict['technologies_used'], work_order_dict['hardware_involved'], work_order_dict['work_order_qualifications'],
                work_order_dict['certifications_required'], work_order_dict['experience_required'], work_order_dict['security_clearance_required'],
                work_order_dict['status'], work_order_dict['completion_status'], work_order_dict['quality_rating'],
                work_order_dict['client_satisfaction'], work_order_dict['challenges_encountered'], work_order_dict['solutions_implemented'],
                work_order_dict['lessons_learned'], work_order_dict['deliverables'], work_order_dict['photos_required'],
                work_order_dict['documentation_provided'], work_order_dict['scheduled_start_time'], work_order_dict['scheduled_end_time'],
                work_order_dict['actual_start_time'], work_order_dict['actual_end_time'], work_order_dict['time_zone'],
                work_order_dict['include_in_resume'], work_order_dict['highlight_project'], work_order_dict['resume_bullet_points'],
                work_order_dict['achievements'], work_order_dict['data_source'], work_order_dict['source_file_path'],
                work_order_dict['extraction_quality'], work_order_dict['needs_review'], 
                datetime.now(), datetime.now(), datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully saved work order {work_order.fn_work_order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving work order {work_order.fn_work_order_id}: {e}")
            return False

    def work_order_exists(self, fn_work_order_id: str) -> bool:
        """Check if work order already exists in database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM fieldnation_work_orders WHERE fn_work_order_id = ?", (fn_work_order_id,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if work order exists: {e}")
            return False

    def store_work_order(self, work_order: WorkOrderData) -> bool:
        """Store work order in database (alias for save_work_order for compatibility)"""
        return self.save_work_order(work_order)

    def process_all_files(self, markdown_dir: str = "downloaded work orders", pdf_dir: str = "fieldnation_pdfs") -> Dict[str, int]:
        """Process all markdown and PDF files"""
        results = {
            'markdown_processed': 0,
            'markdown_failed': 0,
            'pdf_processed': 0,
            'pdf_failed': 0,
            'total_processed': 0,
            'total_failed': 0
        }
        
        # Process markdown files
        if os.path.exists(markdown_dir):
            markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')]
            logger.info(f"Processing {len(markdown_files)} markdown files...")
            
            for filename in markdown_files:
                file_path = os.path.join(markdown_dir, filename)
                work_order = self.process_markdown_file(file_path)
                
                if work_order and self.save_work_order(work_order):
                    results['markdown_processed'] += 1
                    results['total_processed'] += 1
                else:
                    results['markdown_failed'] += 1
                    results['total_failed'] += 1
                    logger.warning(f"Failed to process markdown file: {filename}")
        
        # Process PDF files
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
            logger.info(f"Processing {len(pdf_files)} PDF files...")
            
            for filename in pdf_files:
                file_path = os.path.join(pdf_dir, filename)
                work_order = self.process_pdf_file(file_path)
                
                if work_order and self.save_work_order(work_order):
                    results['pdf_processed'] += 1
                    results['total_processed'] += 1
                else:
                    results['pdf_failed'] += 1
                    results['total_failed'] += 1
                    logger.warning(f"Failed to process PDF file: {filename}")
        
        logger.info(f"Processing complete. Total processed: {results['total_processed']}, Total failed: {results['total_failed']}")
        return results


if __name__ == "__main__":
    processor = ComprehensiveFieldNationProcessor()
    results = processor.process_all_files()
    print(f"Processing Results: {results}") 