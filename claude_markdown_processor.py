#!/usr/bin/env python
"""
Enhanced FieldNation Markdown Processor
Based on Claude Database SOP - SQLite Compatible Version
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any

class FieldNationMarkdownProcessor:
    """Enhanced processor for FieldNation markdown files with comprehensive field extraction"""
    
    def __init__(self, db_path: str = "resume_database.db"):
        self.db_path = db_path
        self.setup_logging()
        self.init_database()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('markdown_processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_database(self):
        """Initialize database with Claude schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create the enhanced work_orders_markdown table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_orders_markdown (
            -- Primary Key
            work_order_id TEXT PRIMARY KEY,
            
            -- Basic Information
            platform TEXT DEFAULT 'Field Nation',
            title TEXT NOT NULL,
            description TEXT,
            status TEXT,
            status_detail TEXT,
            date_created DATE,
            date_completed DATE,
            date_paid DATE,
            priority TEXT,
            work_type TEXT,
            service_type TEXT,
            
            -- Full Service Description (Complete unabridged text)
            service_description_full TEXT,
            scope_of_work TEXT,
            
            -- Company Information
            company_name TEXT,
            company_overall_satisfaction TEXT,
            company_reviews_count INTEGER,
            manager_name TEXT,
            manager_phone TEXT,
            manager_email TEXT,
            
            -- Provider Information
            provider_name TEXT,
            provider_id TEXT,
            provider_phone TEXT,
            provider_email TEXT,
            provider_rating REAL,
            
            -- Financial Information
            total_paid REAL,
            base_pay REAL,
            bonus_pay REAL,
            expense_reimbursement REAL,
            hourly_rate REAL,
            scheduled_hours REAL,
            estimated_hours REAL,
            actual_hours_logged REAL,
            overtime_hours REAL,
            travel_time REAL,
            
            -- Location Information
            location_address TEXT,
            location_city TEXT,
            location_state TEXT,
            location_zip TEXT,
            location_country TEXT DEFAULT 'USA',
            location_coordinates TEXT,
            site_contact_name TEXT,
            site_contact_phone TEXT,
            
            -- Schedule Information
            scheduled_date DATE,
            scheduled_start_time TIME,
            scheduled_end_time TIME,
            actual_start_time TIMESTAMP,
            actual_end_time TIMESTAMP,
            timezone TEXT,
            
            -- Technical Information
            equipment_type TEXT,
            equipment_model TEXT,
            equipment_serial TEXT,
            software_version TEXT,
            network_requirements TEXT,
            special_tools_required TEXT,
            
            -- Work Details
            closeout_notes TEXT,
            customer_signature_required BOOLEAN DEFAULT FALSE,
            photos_required BOOLEAN DEFAULT FALSE,
            parts_used TEXT,
            
            -- JSON Fields (stored as TEXT in SQLite)
            tasks_completed TEXT, -- JSON array
            deliverables TEXT, -- JSON array
            buyer_custom_fields TEXT, -- JSON object
            provider_custom_fields TEXT, -- JSON object
            
            -- Search and Classification
            search_text TEXT, -- Generated from multiple fields
            industry_category TEXT,
            skill_tags TEXT, -- JSON array
            
            -- Metadata
            file_source TEXT,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_quality_score REAL,
            
            -- Indexes for performance
            UNIQUE(work_order_id)
        )
        """)
        
        # Create indexes for search performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON work_orders_markdown(company_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_date ON work_orders_markdown(scheduled_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON work_orders_markdown(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_type ON work_orders_markdown(work_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location_city ON work_orders_markdown(location_city)")
        
        conn.commit()
        conn.close()
        self.logger.info("Database initialized with enhanced schema")
    
    def extract_work_order_id(self, content: str, filename: str) -> Optional[str]:
        """Extract work order ID from content or filename"""
        # Try content patterns first
        patterns = [
            r'# Work Order (\d+)',  # "# Work Order 430895" 
            r'Paid#(\d+)',          # "Paid#430895"
            r'Work Order ID[:\s]*(\d+)',
            r'WO[:\s]*(\d+)',
            r'Order[:\s]*#(\d+)',
            r'\*\*Work Order ID\*\*[:\s]*(\d+)',
            r'#(\d{6,})',           # "#430895" with 6+ digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Try filename patterns
        filename_patterns = [
            r'work_order_(\d+)',
            r'wo_(\d+)',
            r'order_(\d+)',
            r'(\d{6,})'  # 6+ digit numbers
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def parse_datetime(self, date_str: str) -> Optional[date]:
        """Parse various date formats"""
        if not date_str:
            return None
            
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%B %d, %Y',  # January 1, 2024
            '%m/%d/%Y',   # 01/01/2024
            '%Y-%m-%d',   # 2024-01-01
            '%d-%m-%Y',   # 01-01-2024
            '%b %d, %Y',  # Jan 1, 2024
            '%m-%d-%Y',   # 01-01-2024
            '%Y/%m/%d',   # 2024/01/01
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try extracting date from longer strings
        date_patterns = [
            r'(\w+\s+\d+,\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                return self.parse_datetime(match.group(1))
        
        return None
    
    def parse_decimal(self, value_str: str) -> Optional[float]:
        """Parse decimal values from strings"""
        if not value_str:
            return None
            
        # Remove currency symbols and commas
        value_str = re.sub(r'[$,]', '', str(value_str))
        
        try:
            return float(value_str)
        except ValueError:
            return None
    
    def parse_markdown_file(self, filepath: str) -> Dict[str, Any]:
        """Parse a markdown file and extract all fields"""
        self.logger.info(f"Processing file: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = {
            'work_order_id': None,
            'title': None,
            'description': None,
            'status': None,
            'company_name': None,
            'provider_name': None,
            'provider_id': None,
            'provider_phone': None,
            'total_paid': None,
            'scheduled_hours': None,
            'estimated_hours': None,
            'actual_hours_logged': None,
            'location_address': None,
            'location_city': None,
            'location_state': None,
            'location_zip': None,
            'scheduled_date': None,
            'service_description_full': None,
            'closeout_notes': None,
            'work_type': None,
            'service_type': None,
            'equipment_type': None,
            'tasks_completed': [],
            'deliverables': [],
            'buyer_custom_fields': {},
            'provider_custom_fields': {},
            'file_source': os.path.basename(filepath)
        }
        
        # Extract work order ID
        data['work_order_id'] = self.extract_work_order_id(content, os.path.basename(filepath))
        
        # Basic information patterns
        patterns = {
            'title': [
                r'# Work Order (\d+)',  # "# Work Order 430895"
                r'\*\*Title:\*\*\s*(.+?)(?:\n|$)',
                r'##\s*(.+?)(?:\n|$)',
                r'\*\*Service:\*\*\s*(.+?)(?:\n|$)',
                r'# (.+?)(?:\n|$)'
            ],
            'status': [
                r'Pay:\s*(.+?)(?:\n|$)',  # "Pay: Paid"
                r'\*\*Status:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Pay Status:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Work Order Status:\*\*\s*(.+?)(?:\n|$)',
                r'Paid#\d+\s*On\s*[\d/]+\s*(.+?)(?:\n|$)'  # Extract status from "Paid#430895 On 3/15/2013 WC1291 Friday"
            ],
            'company_name': [
                r'Company:\s*(.+?)(?:\n|$)',  # "Company: SAIT Services, Inc"
                r'\*\*Company:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Company Name:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Client:\*\*\s*(.+?)(?:\n|$)'
            ],
            'provider_name': [
                r'Assigned Provider\s*\n\s*(.+?)(?:\n|$)',  # "Assigned Provider\nSadiqa Thornton"
                r'\*\*Assigned Provider:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Provider:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Technician:\*\*\s*(.+?)(?:\n|$)'
            ],
            'provider_id': [
                r'ID:\s*(\d+)',  # "ID: 24217"
                r'\*\*Provider ID:\*\*\s*(\d+)',
                r'\*\*ID:\*\*\s*(\d+)'
            ],
            'provider_phone': [
                r'(\d{3}-\d{3}-\d{4})',  # "862-350-1878"
                r'\*\*Phone:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Contact:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Provider Phone:\*\*\s*(.+?)(?:\n|$)'
            ],
            'location_address': [
                r'Work order site\s*\n\s*(.+?)(?:\n|$)',  # "Work order site\nNEW YORK, NY 10022 US"
                r'\*\*Address:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Location:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Work Order Site:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Site Address:\*\*\s*(.+?)(?:\n|$)'
            ],
            'work_type': [
                r'Type of work:\s*\n\s*(.+?)(?:\n|$)',  # "Type of work:\nGeneral Tasks"
                r'\*\*Work Type:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Type:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Category:\*\*\s*(.+?)(?:\n|$)'
            ],
            'service_type': [
                r'Service Types:\s*(.+?)(?:\n|$)',  # "Service Types:no service type specified"
                r'\*\*Service Type:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Service:\*\*\s*(.+?)(?:\n|$)'
            ],
            'equipment_type': [
                r'\*\*Equipment:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Equipment Type:\*\*\s*(.+?)(?:\n|$)',
                r'\*\*Device:\*\*\s*(.+?)(?:\n|$)'
            ]
        }
        
        # Extract fields using patterns
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, content, re.MULTILINE)
                if match:
                    data[field] = match.group(1).strip()
                    break
        
        # Extract location components from address
        if data['location_address']:
            self.parse_location_components(data)
        
        # Extract financial information
        financial_patterns = [
            (r'Pay:\s*Paid\s*\n?\s*\$?([\d,\.]+)', 'total_paid'),  # "Pay: Paid\n$18.00"
            (r'\$?([\d,\.]+)\s*\n?\s*Pay:', 'total_paid'),  # "$18.00\nPay:"
            (r'\*\*Total Paid\*\*\s*\*\*\$?([\d,\.]+)\*\*', 'total_paid'),
            (r'\*\*Amount:\*\*\s*\$?([\d,\.]+)', 'total_paid'),
            (r'\*\*Total:\*\*\s*\$?([\d,\.]+)', 'total_paid'),
            (r'\*\*Pay:\*\*\s*\$?([\d,\.]+)', 'total_paid'),
            (r'Total\s*\n\s*\$?([\d,\.]+)', 'total_paid'),  # "Total\n$18.00"
            (r'\*\*Base Pay:\*\*\s*\$?([\d,\.]+)', 'base_pay'),
            (r'\*\*Bonus:\*\*\s*\$?([\d,\.]+)', 'bonus_pay'),
            (r'\*\*Hourly Rate:\*\*\s*\$?([\d,\.]+)', 'hourly_rate'),
            (r'Rate\s*\n\s*\$?([\d,\.]+)', 'hourly_rate')  # "Rate\n$20.00"
        ]
        
        for pattern, field in financial_patterns:
            match = re.search(pattern, content)
            if match and not data.get(field):
                data[field] = self.parse_decimal(match.group(1))
        
        # Extract hours
        hours_patterns = [
            (r'Time Logged\s*\n\s*([\d\.]+)\s*hours?', 'actual_hours_logged'),  # "Time Logged\n0 hours"
            (r'\*\*Time Logged:\*\*\s*([\d\.]+)\s*hours?', 'actual_hours_logged'),
            (r'\*\*Total Hours:\*\*\s*([\d\.]+)', 'actual_hours_logged'),
            (r'\*\*Actual Hours:\*\*\s*([\d\.]+)', 'actual_hours_logged'),
            (r'\*\*Scheduled Hours:\*\*\s*([\d\.]+)', 'scheduled_hours'),
            (r'Hours\s*\n\s*([\d\.]+)\s*Max', 'scheduled_hours'),  # "Hours\n8 Max"
            (r'Estimated\s*([\d\.]+)\s*hour', 'estimated_hours')  # "Estimated 1 hour"
        ]
        
        for pattern, field in hours_patterns:
            match = re.search(pattern, content)
            if match and not data.get(field):
                data[field] = self.parse_decimal(match.group(1))
        
        # Extract dates
        date_patterns = [
            (r'On (\d{1,2}/\d{1,2}/\d{4})', 'scheduled_date'),  # "On 3/15/2013"
            (r'(\w{3}, \w{3} \d{1,2}, \d{4})', 'scheduled_date'),  # "Fri, Mar 8, 2013"
            (r'\*\*Date:\*\*\s*(.+?)(?:\n|$)', 'scheduled_date'),
            (r'\*\*Scheduled Date:\*\*\s*(.+?)(?:\n|$)', 'scheduled_date'),
            (r'\*\*Date Completed:\*\*\s*(.+?)(?:\n|$)', 'date_completed'),
            (r'\*\*Date Paid:\*\*\s*(.+?)(?:\n|$)', 'date_paid')
        ]
        
        for pattern, field in date_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                date_value = self.parse_datetime(match.group(1))
                if date_value:
                    data[field] = date_value
        
        # Extract service description - capture large blocks of text
        service_sections = [
            r'Service Description\s*\n(.*?)(?=\n(?:Tasks|Buyer Custom|Provider Custom|Time Log|Deliverables|\Z))',  # Our format
            r'## Service Description\s*\n(.*?)(?=\n##|\n\*\*|\Z)',
            r'### Service Description\s*\n(.*?)(?=\n##|\n###|\n\*\*|\Z)',
            r'## Scope of Work\s*\n(.*?)(?=\n##|\n\*\*|\Z)',
            r'## Full Service Description\s*\n(.*?)(?=\n##|\n\*\*|\Z)',
            r'## Description\s*\n(.*?)(?=\n##|\n\*\*|\Z)'
        ]
        
        for pattern in service_sections:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                data['service_description_full'] = match.group(1).strip()
                break
        
        # Extract closeout notes
        closeout_patterns = [
            r'(?:## Closeout Notes|Notes:|closeout notes)\s*\n(.+?)(?=\n##|\n\*\*|\Z)',
            r'\*\*Notes:\*\*\s*"(.+?)"',
            r'\*\*Closeout Notes:\*\*\s*(.+?)(?=\n|\Z)',
            r'## Notes\s*\n(.*?)(?=\n##|\n\*\*|\Z)'
        ]
        
        for pattern in closeout_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                data['closeout_notes'] = match.group(1).strip()
                break
        
        # Extract tasks completed
        tasks_section = re.search(
            r'## Tasks Completed\s*\n(.*?)(?=\n##|\Z)', 
            content, 
            re.DOTALL
        )
        if tasks_section:
            tasks_text = tasks_section.group(1)
            tasks = re.findall(r'[-*]\s*(.+)', tasks_text)
            data['tasks_completed'] = [task.strip() for task in tasks]
        
        # Generate search text
        data['search_text'] = self.generate_search_text(data)
        
        # Calculate data quality score
        data['data_quality_score'] = self.calculate_quality_score(data)
        
        return data
    
    def parse_location_components(self, data: Dict[str, Any]):
        """Parse location components from address"""
        address = data['location_address']
        if not address:
            return
        
        # Try to extract city, state, zip
        # Pattern: "City, State ZIP"
        location_pattern = r'(.+?),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?'
        match = re.search(location_pattern, address)
        
        if match:
            # Extract from the end of the address
            parts = address.split(',')
            if len(parts) >= 2:
                data['location_city'] = parts[-2].strip()
                
                # Extract state and zip from last part
                last_part = parts[-1].strip()
                state_zip = re.search(r'([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?', last_part)
                if state_zip:
                    data['location_state'] = state_zip.group(1)
                    if state_zip.group(2):
                        data['location_zip'] = state_zip.group(2)
    
    def generate_search_text(self, data: Dict[str, Any]) -> str:
        """Generate searchable text from multiple fields"""
        search_fields = [
            data.get('title', ''),
            data.get('company_name', ''),
            data.get('service_description_full', ''),
            data.get('work_type', ''),
            data.get('service_type', ''),
            data.get('equipment_type', ''),
            data.get('location_city', ''),
            data.get('location_state', ''),
            data.get('closeout_notes', ''),
            ' '.join(data.get('tasks_completed', []))
        ]
        
        return ' '.join(filter(None, search_fields))
    
    def calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score based on field completeness"""
        required_fields = [
            'work_order_id', 'title', 'company_name', 'status',
            'total_paid', 'scheduled_date', 'location_address'
        ]
        
        optional_fields = [
            'service_description_full', 'work_type', 'service_type',
            'equipment_type', 'actual_hours_logged', 'closeout_notes'
        ]
        
        required_score = sum(1 for field in required_fields if data.get(field)) / len(required_fields)
        optional_score = sum(1 for field in optional_fields if data.get(field)) / len(optional_fields)
        
        return (required_score * 0.7) + (optional_score * 0.3)
    
    def save_to_database(self, data: Dict[str, Any]) -> bool:
        """Save parsed data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create a copy to avoid modifying original data
            data_copy = data.copy()
            
            # Convert JSON fields to strings
            json_fields = ['tasks_completed', 'deliverables', 'buyer_custom_fields', 'provider_custom_fields']
            for field in json_fields:
                if field in data_copy and data_copy[field]:
                    data_copy[field] = json.dumps(data_copy[field])
                else:
                    data_copy[field] = None
            
            # Prepare insert statement
            fields = list(data_copy.keys())
            placeholders = ', '.join(['?' for _ in fields])
            field_names = ', '.join(fields)
            
            query = f"""
            INSERT OR REPLACE INTO work_orders_markdown ({field_names})
            VALUES ({placeholders})
            """
            
            values = [data_copy.get(field) for field in fields]
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            self.logger.info(f"Saved work order {data_copy.get('work_order_id')} to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            return False
    
    def process_directory(self, markdown_dir: str) -> Dict[str, int]:
        """Process all markdown files in directory"""
        stats = {
            'total_files': 0,
            'processed': 0,
            'errors': 0,
            'skipped': 0
        }
        
        if not os.path.exists(markdown_dir):
            self.logger.error(f"Directory not found: {markdown_dir}")
            return stats
        
        for filename in os.listdir(markdown_dir):
            if not filename.endswith('.md'):
                continue
                
            stats['total_files'] += 1
            filepath = os.path.join(markdown_dir, filename)
            
            try:
                data = self.parse_markdown_file(filepath)
                
                if not data.get('work_order_id'):
                    self.logger.warning(f"No work order ID found in {filename}")
                    stats['skipped'] += 1
                    continue
                
                if self.save_to_database(data):
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing {filename}: {e}")
                stats['errors'] += 1
        
        self.logger.info(f"Processing complete: {stats}")
        return stats

def main():
    """Main execution function"""
    processor = FieldNationMarkdownProcessor()
    
    # Process the markdown files
    markdown_dir = "downloaded work orders"
    
    if os.path.exists(markdown_dir):
        print(f"Processing markdown files from: {markdown_dir}")
        stats = processor.process_directory(markdown_dir)
        
        print(f"\nProcessing Results:")
        print(f"Total files: {stats['total_files']}")
        print(f"Successfully processed: {stats['processed']}")
        print(f"Errors: {stats['errors']}")
        print(f"Skipped: {stats['skipped']}")
    else:
        print(f"Directory not found: {markdown_dir}")

if __name__ == "__main__":
    main() 