#!/usr/bin/env python3
"""
Comprehensive Work Order Enhancement Script
Extracts complete information from markdown files to enhance database records
"""

import sqlite3
import os
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class MarkdownWorkOrderEnhancer:
    def __init__(self, db_path='resume_database.db'):
        self.db_path = db_path
        self.markdown_dir = 'downloaded work orders'
        self.enhanced_count = 0
        self.processed_count = 0
        
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def clean_text(self, text: str) -> str:
        """Clean markdown formatting and unwanted characters"""
        if not text or not isinstance(text, str):
            return text
        
        # Remove markdown formatting
        text = text.replace('**', '').replace('***', '').replace('*', '')
        text = text.replace('##', '').replace('#', '')
        
        # Clean up colons and formatting
        text = text.replace('**:**', '').replace(': ', ' ').strip()
        if text.startswith(':'):
            text = text[1:].strip()
            
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text

    def extract_work_order_id(self, filename: str) -> Optional[str]:
        """Extract work order ID from filename"""
        match = re.search(r'work_order_(\d+)_', filename)
        return match.group(1) if match else None
    
    def extract_contact_info(self, content: str) -> Dict[str, str]:
        """Extract contact information from markdown content"""
        contacts = {}
        
        # Extract manager/site contact
        manager_pattern = r'Manager/Site contact\s*\n([^\n]+)'
        manager_match = re.search(manager_pattern, content, re.IGNORECASE)
        if manager_match:
            contacts['site_contact'] = self.clean_text(manager_match.group(1))
            contacts['manager_name'] = self.clean_text(manager_match.group(1))
        
        # Extract phone numbers from contact section
        phone_pattern = r'(\d{3}-\d{3}-\d{4}|\(\d{3}\)\s*\d{3}-\d{4})'
        phone_matches = re.findall(phone_pattern, content)
        if phone_matches:
            contacts['contact_phone'] = phone_matches[0]
        
        return contacts
    
    def extract_location_info(self, content: str) -> Dict[str, str]:
        """Extract detailed location information"""
        location = {}
        
        # Extract work order site location
        location_pattern = r'Work order site\s*\n([^\n]+)'
        location_match = re.search(location_pattern, content)
        if location_match:
            full_address = self.clean_text(location_match.group(1))
            location['site_address'] = full_address
            location['location'] = full_address
            
            # Parse city, state, zip
            address_parts = full_address.split(',')
            if len(address_parts) >= 2:
                location['city'] = address_parts[-2].strip()
                state_zip = address_parts[-1].strip().split()
                if len(state_zip) >= 2:
                    location['state'] = state_zip[0]
                    location['zip_code'] = state_zip[1]
        
        # Extract commercial/residential type
        if 'Commercial' in content:
            location['site_type'] = 'Commercial'
        elif 'Residential' in content:
            location['site_type'] = 'Residential'
            
        return location
    
    def extract_service_description(self, content: str) -> str:
        """Extract complete service description"""
        # Look for service description section
        service_patterns = [
            r'Service Description\s*\n\n\n(.*?)(?=\n\n[A-Z]|\nWORK ORDERS WILL)',
            r'Justification for Tech:\s*\n\n(.*?)(?=\n\nWORK ORDERS WILL|\nTech to contact)',
            r'Brief description of the issue:\s*([^\n]+)',
            r'Work to be performed:\s*\n(.*?)(?=\n\n|\nPay:)',
            r'Description:\s*\n(.*?)(?=\n\n|\nWork order site)'
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                description = self.clean_text(match.group(1))
                if len(description) > 50:  # Only use substantial descriptions
                    return description
        
        return ""
    
    def extract_closeout_notes(self, content: str) -> str:
        """Extract detailed closeout notes"""
        # Look for closeout notes section
        closeout_patterns = [
            r'Enter closeout notes\s*\n(.*?)(?=\nCompleted by you|\nCheck out)',
            r'Provide detailed closeout notes.*?\n(.*?)(?=\nCompleted by you)',
            r'closeout notes[:\s]*\n(.*?)(?=\n\w+:|$)',
            r'Closeout Summary:\s*\n(.*?)(?=\n\n|\nTime Logged)',
            r'Work Summary:\s*\n(.*?)(?=\n\n|\nCompleted)'
        ]
        
        for pattern in closeout_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                notes = self.clean_text(match.group(1))
                if len(notes) > 20:  # Only use substantial notes
                    return notes
        
        return ""
    
    def extract_equipment_requirements(self, content: str) -> List[str]:
        """Extract equipment/material requirements"""
        equipment = []
        
        # Look for material/equipment section
        equipment_patterns = [
            r'MATERIAL/EQUIPMENT REQUIRED:(.*?)(?=\n\nDELIVERABLES:|\n\n[A-Z]+:)',
            r'Required Tools:\s*\n(.*?)(?=\n\n|\nService)',
            r'Equipment needed:\s*\n(.*?)(?=\n\n)',
            r'Materials:\s*\n(.*?)(?=\n\n)'
        ]
        
        for pattern in equipment_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                equipment_text = match.group(1)
                # Split by lines and clean
                for line in equipment_text.split('\n'):
                    line = self.clean_text(line).strip()
                    if line and len(line) > 3 and not line.isdigit():
                        equipment.append(line)
                break
        
        return equipment[:15]  # Limit to reasonable number
    
    def extract_payment_info(self, content: str) -> Dict[str, float]:
        """Extract payment information"""
        payment = {}
        
        # Extract pay amount
        pay_patterns = [
            r'Pay:\s*\$([0-9,.]+)',
            r'Pay Amount\s*\n\$([0-9,.]+)',
            r'\$([0-9,.]+)\s*\nAssigned Provider',
            r'Total Pay:\s*\$([0-9,.]+)'
        ]
        
        for pattern in pay_patterns:
            match = re.search(pattern, content)
            if match:
                pay_text = match.group(1).replace(',', '')
                try:
                    payment['pay_amount'] = float(pay_text)
                    break
                except ValueError:
                    continue
        
        # Extract time logged
        time_patterns = [
            r'Time Logged\s*\n([0-9.]+)\s*hours',
            r'Actual time:\s*([0-9.]+)\s*hours',
            r'Total hours:\s*([0-9.]+)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    payment['actual_hours'] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        return payment
    
    def extract_work_details(self, content: str) -> Dict[str, str]:
        """Extract work type and category details"""
        details = {}
        
        # Extract work type
        work_type_patterns = [
            r'Type of work:\s*\n([^\n]+)',
            r'Work Type:\s*\n([^\n]+)',
            r'Service Category:\s*([^\n]+)'
        ]
        
        for pattern in work_type_patterns:
            match = re.search(pattern, content)
            if match:
                details['work_type'] = self.clean_text(match.group(1))
                break
        
        # Extract service type
        service_type_patterns = [
            r'Service Type:\s*\n([^\n]+)',
            r'Category:\s*([^\n]+)'
        ]
        
        for pattern in service_type_patterns:
            match = re.search(pattern, content)
            if match:
                details['service_type'] = self.clean_text(match.group(1))
                break
        
        # Extract company
        company_patterns = [
            r'Company:\s*([^\n]+)',
            r'Client:\s*([^\n]+)',
            r'Buyer:\s*([^\n]+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, content)
            if match:
                details['buyer_company'] = self.clean_text(match.group(1))
                break
        
        return details
    
    def extract_schedule_info(self, content: str) -> Dict[str, str]:
        """Extract scheduling information"""
        schedule = {}
        
        # Extract service date
        date_patterns = [
            r'On (\d{1,2}/\d{1,2}/\d{4})',
            r'Service Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'Completed by you on (\d{1,2}/\d{1,2}/\d{4})',
            r'(\w{3}, \w{3} \d{1,2}, \d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                schedule['service_date'] = match.group(1)
                break
        
        # Extract estimated time
        time_patterns = [
            r'Estimated (\d+) hours? to complete',
            r'Expected duration:\s*(\d+)\s*hours?',
            r'Time estimate:\s*(\d+)\s*hours?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    schedule['estimated_hours'] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        return schedule

    def extract_technologies_and_skills(self, content: str) -> Dict[str, List[str]]:
        """Extract technologies and skills from content"""
        result = {'technologies': [], 'skills': []}
        
        # Look for technology mentions
        tech_keywords = ['Windows', 'Linux', 'Mac', 'Android', 'iOS', 'router', 'switch', 'firewall', 
                        'WiFi', 'network', 'server', 'desktop', 'laptop', 'tablet', 'smartphone',
                        'cable', 'ethernet', 'fiber', 'troubleshoot', 'diagnostic', 'repair']
        
        content_lower = content.lower()
        for keyword in tech_keywords:
            if keyword.lower() in content_lower:
                result['technologies'].append(keyword)
        
        # Look for skills mentions
        skill_keywords = ['troubleshooting', 'installation', 'configuration', 'maintenance', 
                         'repair', 'testing', 'documentation', 'customer service', 'problem solving']
        
        for keyword in skill_keywords:
            if keyword.lower() in content_lower:
                result['skills'].append(keyword)
        
        return result

    def process_markdown_file(self, filepath: str) -> Optional[Dict]:
        """Process a single markdown file and extract all information"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filename = os.path.basename(filepath)
            work_order_id = self.extract_work_order_id(filename)
            
            if not work_order_id:
                print(f"Could not extract work order ID from {filename}")
                return None
            
            # Extract all information
            extracted_data = {
                'fn_work_order_id': work_order_id,
                'contacts': self.extract_contact_info(content),
                'location': self.extract_location_info(content),
                'service_description': self.extract_service_description(content),
                'closeout_notes': self.extract_closeout_notes(content),
                'equipment': self.extract_equipment_requirements(content),
                'payment': self.extract_payment_info(content),
                'work_details': self.extract_work_details(content),
                'schedule': self.extract_schedule_info(content),
                'tech_skills': self.extract_technologies_and_skills(content)
            }
            
            return extracted_data
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return None
    
    def update_database_record(self, conn: sqlite3.Connection, extracted_data: Dict) -> bool:
        """Update database record with extracted information"""
        try:
            cursor = conn.cursor()
            
            # Build update query dynamically based on available data
            update_fields = []
            update_values = []
            
            # Contact information (using existing columns)
            contacts = extracted_data.get('contacts', {})
            if contacts.get('site_contact'):
                update_fields.append('site_contact = ?')
                update_values.append(contacts['site_contact'])
            
            if contacts.get('manager_name'):
                update_fields.append('manager_name = ?')
                update_values.append(contacts['manager_name'])
            
            if contacts.get('contact_phone'):
                update_fields.append('contact_phone = ?')
                update_values.append(contacts['contact_phone'])
            
            # Location information (using existing columns)
            location = extracted_data.get('location', {})
            if location.get('site_address'):
                update_fields.append('site_address = ?')
                update_values.append(location['site_address'])
            
            if location.get('location'):
                update_fields.append('location = ?')
                update_values.append(location['location'])
            
            if location.get('city'):
                update_fields.append('city = ?')
                update_values.append(location['city'])
            
            if location.get('state'):
                update_fields.append('state = ?')
                update_values.append(location['state'])
            
            if location.get('zip_code'):
                update_fields.append('zip_code = ?')
                update_values.append(location['zip_code'])
            
            if location.get('site_type'):
                update_fields.append('site_type = ?')
                update_values.append(location['site_type'])
            
            # Service information (using existing columns)
            service_desc = extracted_data.get('service_description')
            if service_desc:
                update_fields.append('service_description = ?')
                update_values.append(service_desc)
                # Also update work_description if it's currently empty/basic
                update_fields.append('work_description = ?')
                update_values.append(service_desc)
            
            closeout_notes = extracted_data.get('closeout_notes')
            if closeout_notes:
                update_fields.append('documentation_provided = ?')
                update_values.append(closeout_notes)
            
            # Equipment requirements (using existing columns)
            equipment = extracted_data.get('equipment', [])
            if equipment:
                update_fields.append('required_tools = ?')
                update_values.append(json.dumps(equipment))
            
            # Payment information (using existing columns)
            payment = extracted_data.get('payment', {})
            if payment.get('pay_amount'):
                update_fields.append('pay_amount = ?')
                update_values.append(payment['pay_amount'])
            
            if payment.get('actual_hours'):
                update_fields.append('actual_hours = ?')
                update_values.append(payment['actual_hours'])
            
            # Work details (using existing columns)
            work_details = extracted_data.get('work_details', {})
            if work_details.get('work_type'):
                update_fields.append('work_type = ?')
                update_values.append(work_details['work_type'])
            
            if work_details.get('service_type'):
                update_fields.append('service_type = ?')
                update_values.append(work_details['service_type'])
            
            if work_details.get('buyer_company'):
                update_fields.append('buyer_company = ?')
                update_values.append(work_details['buyer_company'])
            
            # Schedule information (using existing columns)
            schedule = extracted_data.get('schedule', {})
            if schedule.get('service_date'):
                update_fields.append('service_date = ?')
                update_values.append(schedule['service_date'])
            
            if schedule.get('estimated_hours'):
                update_fields.append('estimated_hours = ?')
                update_values.append(schedule['estimated_hours'])
            
            # Technologies and skills (using existing columns)
            tech_skills = extracted_data.get('tech_skills', {})
            if tech_skills.get('technologies'):
                update_fields.append('technologies_used = ?')
                update_values.append(json.dumps(tech_skills['technologies']))
            
            if tech_skills.get('skills'):
                update_fields.append('required_skills = ?')
                update_values.append(json.dumps(tech_skills['skills']))
            
            # Add last updated timestamp
            update_fields.append('updated_at = ?')
            update_values.append(datetime.now().isoformat())
            
            if not update_fields:
                print(f"No data to update for work order {extracted_data['fn_work_order_id']}")
                return False
            
            # Build and execute update query
            update_query = f"""
                UPDATE fieldnation_work_orders 
                SET {', '.join(update_fields)}
                WHERE fn_work_order_id = ?
            """
            update_values.append(extracted_data['fn_work_order_id'])
            
            cursor.execute(update_query, update_values)
            
            if cursor.rowcount > 0:
                print(f"✅ Enhanced work order {extracted_data['fn_work_order_id']} with {len(update_fields)} fields")
                return True
            else:
                print(f"❌ No existing record found for work order {extracted_data['fn_work_order_id']}")
                return False
                
        except Exception as e:
            print(f"Error updating database for work order {extracted_data['fn_work_order_id']}: {e}")
            return False

    def enhance_all_records(self):
        """Process all markdown files and enhance database records"""
        print("🚀 Starting Work Order Enhancement from Markdown Files")
        print("=" * 60)
        
        if not os.path.exists(self.markdown_dir):
            print(f"❌ Markdown directory not found: {self.markdown_dir}")
            return
        
        # Get all markdown files
        markdown_files = [f for f in os.listdir(self.markdown_dir) if f.endswith('.md')]
        print(f"📁 Found {len(markdown_files)} markdown files to process")
        
        conn = self.get_db_connection()
        
        try:
            for filename in sorted(markdown_files):
                filepath = os.path.join(self.markdown_dir, filename)
                self.processed_count += 1
                
                print(f"\n📄 Processing {filename} ({self.processed_count}/{len(markdown_files)})")
                
                # Extract data from markdown
                extracted_data = self.process_markdown_file(filepath)
                if not extracted_data:
                    continue
                
                # Update database record
                if self.update_database_record(conn, extracted_data):
                    self.enhanced_count += 1
                
                # Commit after each record for safety
                conn.commit()
            
        finally:
            conn.close()
        
        print("\n" + "=" * 60)
        print(f"🎉 Enhancement Complete!")
        print(f"📊 Processed: {self.processed_count} files")
        print(f"✅ Enhanced: {self.enhanced_count} work orders")
        print(f"📈 Success Rate: {(self.enhanced_count/max(self.processed_count,1)*100):.1f}%")

def main():
    enhancer = MarkdownWorkOrderEnhancer()
    enhancer.enhance_all_records()

if __name__ == "__main__":
    main() 