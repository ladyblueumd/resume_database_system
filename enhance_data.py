#!/usr/bin/env python
"""
Data Enhancement Script
Based on Claude Database SOP Step 4
Adapted for SQLite database
"""

import sqlite3
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataEnhancer:
    def __init__(self, db_path: str = 'resume_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
    def enhance_location_data(self):
        """Parse and enhance location information"""
        logging.info("Enhancing location data...")
        
        query = """
        SELECT work_order_id, location_address 
        FROM work_orders_markdown 
        WHERE location_address IS NOT NULL 
        AND (location_city IS NULL OR location_state IS NULL)
        """
        
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        updated = 0
        for row in rows:
            # Try to parse city, state, zip
            patterns = [
                r'(.+?),\s*([A-Z]{2})\s*(\d{5})',  # City, ST 12345
                r'(.+?),\s*([A-Z]{2})',             # City, ST
                r'(.+?)\s+([A-Z]{2})\s*(\d{5})'     # City ST 12345
            ]
            
            for pattern in patterns:
                match = re.search(pattern, row['location_address'])
                if match:
                    city = match.group(1).strip()
                    state = match.group(2)
                    zip_code = match.group(3) if len(match.groups()) > 2 else None
                    
                    update_query = """
                    UPDATE work_orders_markdown 
                    SET location_city = ?, 
                        location_state = ?,
                        location_zip = ?
                    WHERE work_order_id = ?
                    """
                    
                    self.cursor.execute(update_query, (city, state, zip_code, row['work_order_id']))
                    updated += 1
                    break
        
        self.conn.commit()
        logging.info(f"Updated {updated} location records")
    
    def standardize_company_names(self):
        """Standardize company names for consistency"""
        logging.info("Standardizing company names...")
        
        company_mappings = {
            'Dell': ['Dell Inc', 'Dell Technologies', 'Dell Computer', 'DELL'],
            'Spencer Technologies': ['Spencer Tech', 'Spencer Technology', 'SPENCER TECHNOLOGIES'],
            'Worldlink Integration Group': ['Worldlink', 'Worldlink Integration', 'WORLDLINK'],
            'Kiosk Services Group': ['KSG', 'Kiosk Services', 'KIOSK SERVICES'],
            'Victoria\'s Secret': ['Victoria Secret', 'VS', 'VICTORIA\'S SECRET'],
            'CrossCom': ['Cross Com', 'Cross-Com', 'CROSSCOM'],
            'AlliedDigital': ['Allied Digital', 'Allied-Digital', 'ALLIEDDIGITAL'],
            'SAIT Services, Inc': ['SAIT Services', 'SAIT', 'SAIT SERVICES'],
            'SmartSource Inc.': ['SmartSource', 'Smart Source', 'SMARTSOURCE'],
            'Life Station': ['LifeStation', 'LIFE STATION']
        }
        
        updated = 0
        for standard_name, variations in company_mappings.items():
            for variation in variations:
                query = """
                UPDATE work_orders_markdown 
                SET company_name = ? 
                WHERE company_name = ?
                """
                self.cursor.execute(query, (standard_name, variation))
                updated += self.cursor.rowcount
        
        self.conn.commit()
        logging.info(f"Standardized {updated} company names")
    
    def extract_time_data(self):
        """Extract and parse time-related data from tasks"""
        logging.info("Extracting time session data...")
        
        query = """
        SELECT work_order_id, tasks_completed
        FROM work_orders_markdown
        WHERE tasks_completed IS NOT NULL AND tasks_completed != '[]'
        """
        
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        sessions_added = 0
        for row in rows:
            try:
                tasks = json.loads(row['tasks_completed'])
                
                # Look for check in/out tasks
                check_in_time = None
                check_out_time = None
                
                for task in tasks:
                    task_desc = str(task).lower() if isinstance(task, str) else str(task.get('description', '')).lower()
                    
                    if 'check in' in task_desc:
                        # Extract time from task
                        time_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)', 
                                             str(task))
                        if time_match:
                            check_in_time = f"{time_match.group(1)} {time_match.group(2)}"
                    
                    elif 'check out' in task_desc:
                        time_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)', 
                                             str(task))
                        if time_match:
                            check_out_time = f"{time_match.group(1)} {time_match.group(2)}"
                
                # Update main record if we found times
                if check_in_time or check_out_time:
                    # SQLite doesn't have STR_TO_DATE, so we'll store as text
                    update_query = """
                    UPDATE work_orders_markdown
                    SET check_in_datetime = ?,
                        check_out_datetime = ?
                    WHERE work_order_id = ?
                    """
                    
                    self.cursor.execute(update_query, (check_in_time, check_out_time, row['work_order_id']))
                    sessions_added += 1
                    
            except Exception as e:
                logging.error(f"Error processing tasks for {row['work_order_id']}: {str(e)}")
        
        self.conn.commit()
        logging.info(f"Updated {sessions_added} time records")
    
    def calculate_derived_fields(self):
        """Calculate derived fields like hourly rates"""
        logging.info("Calculating derived fields...")
        
        query = """
        UPDATE work_orders_markdown
        SET hourly_rate = CASE 
            WHEN actual_hours_logged > 0 AND total_paid > 0 
            THEN ROUND(total_paid / actual_hours_logged, 2)
            ELSE hourly_rate
        END
        WHERE actual_hours_logged > 0 AND total_paid > 0
        """
        
        self.cursor.execute(query)
        self.conn.commit()
        
        logging.info(f"Updated {self.cursor.rowcount} hourly rate calculations")
    
    def identify_work_categories(self):
        """Categorize work orders based on content"""
        logging.info("Identifying work categories...")
        
        # Define category patterns
        categories = {
            'Hardware Installation': ['install', 'setup', 'deploy', 'mount', 'cable'],
            'Network Services': ['network', 'router', 'switch', 'firewall', 'wifi', 'wireless'],
            'POS Systems': ['pos', 'point of sale', 'register', 'retail', 'payment'],
            'Printer Services': ['printer', 'print', 'toner', 'paper jam'],
            'Desktop Support': ['desktop', 'workstation', 'pc', 'computer', 'monitor'],
            'Server Maintenance': ['server', 'rack', 'datacenter', 'ups'],
            'Telecommunications': ['phone', 'voip', 'pbx', 'telecom'],
            'Software Support': ['software', 'application', 'update', 'patch'],
            'Kiosk Services': ['kiosk', 'terminal', 'self-service'],
            'Healthcare IT': ['medical', 'healthcare', 'hospital', 'clinic', 'patient']
        }
        
        updated = 0
        
        # Get all work orders
        self.cursor.execute("""
            SELECT work_order_id, title, service_description_full, work_type
            FROM work_orders_markdown
            WHERE work_type IS NULL OR work_type = ''
        """)
        
        rows = self.cursor.fetchall()
        
        for row in rows:
            # Combine text for analysis
            text = f"{row['title'] or ''} {row['service_description_full'] or ''}".lower()
            
            # Find matching category
            for category, keywords in categories.items():
                if any(keyword in text for keyword in keywords):
                    self.cursor.execute(
                        "UPDATE work_orders_markdown SET work_type = ? WHERE work_order_id = ?",
                        (category, row['work_order_id'])
                    )
                    updated += 1
                    break
        
        self.conn.commit()
        logging.info(f"Categorized {updated} work orders")
    
    def extract_skills_and_technologies(self):
        """Extract skills and technologies from work order content"""
        logging.info("Extracting skills and technologies...")
        
        # Technology patterns
        tech_patterns = {
            'Operating Systems': ['windows', 'mac', 'linux', 'ubuntu', 'ios', 'android'],
            'Networking': ['tcp/ip', 'dhcp', 'dns', 'vlan', 'vpn', 'subnet'],
            'Hardware': ['dell', 'hp', 'lenovo', 'cisco', 'netgear', 'aruba'],
            'Software': ['microsoft office', 'adobe', 'antivirus', 'backup', 'remote desktop'],
            'Databases': ['sql', 'mysql', 'oracle', 'mongodb', 'database'],
            'Cloud': ['aws', 'azure', 'cloud', 'saas', 'iaas'],
            'Security': ['firewall', 'encryption', 'security', 'authentication', 'ssl']
        }
        
        updated = 0
        
        self.cursor.execute("""
            SELECT work_order_id, service_description_full, closeout_notes
            FROM work_orders_markdown
        """)
        
        rows = self.cursor.fetchall()
        
        for row in rows:
            text = f"{row['service_description_full'] or ''} {row['closeout_notes'] or ''}".lower()
            
            skills = []
            for category, keywords in tech_patterns.items():
                for keyword in keywords:
                    if keyword in text:
                        skills.append(f"{category}: {keyword.title()}")
            
            if skills:
                # Store as JSON array
                self.cursor.execute(
                    "UPDATE work_orders_markdown SET skill_tags = ? WHERE work_order_id = ?",
                    (json.dumps(list(set(skills))), row['work_order_id'])
                )
                updated += 1
        
        self.conn.commit()
        logging.info(f"Updated {updated} records with skills/technologies")
    
    def run_all_enhancements(self):
        """Run all enhancement procedures"""
        logging.info("Starting data enhancement process...")
        
        try:
            self.enhance_location_data()
            self.standardize_company_names()
            self.extract_time_data()
            self.calculate_derived_fields()
            self.identify_work_categories()
            self.extract_skills_and_technologies()
            
            logging.info("Data enhancement complete!")
            
            # Show summary statistics
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT company_name) as companies,
                    COUNT(location_city) as with_city,
                    COUNT(work_type) as categorized,
                    COUNT(skill_tags) as with_skills
                FROM work_orders_markdown
            """)
            
            stats = self.cursor.fetchone()
            
            print("\n📊 ENHANCEMENT RESULTS:")
            print(f"   Total work orders: {stats[0]:,}")
            print(f"   Unique companies: {stats[1]:,}")
            print(f"   With city data: {stats[2]:,} ({stats[2]/stats[0]*100:.1f}%)")
            print(f"   Categorized: {stats[3]:,} ({stats[3]/stats[0]*100:.1f}%)")
            print(f"   With skills: {stats[4]:,} ({stats[4]/stats[0]*100:.1f}%)")
            
        except Exception as e:
            logging.error(f"Enhancement failed: {str(e)}")
            raise
    
    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()

# Main execution
if __name__ == "__main__":
    # Run enhancements
    enhancer = DataEnhancer()
    try:
        enhancer.run_all_enhancements()
    finally:
        enhancer.close() 