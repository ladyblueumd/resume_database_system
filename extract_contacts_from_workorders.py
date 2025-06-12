#!/usr/bin/env python
"""
Extract contacts, companies, and relationships from work orders
Builds a comprehensive contact management database
"""

import sqlite3
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ContactExtractor:
    def __init__(self, db_path: str = 'resume_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.companies = {}
        self.contacts = {}
        self.init_tables()
        
    def init_tables(self):
        """Initialize contact management tables"""
        try:
            with open('contact_management_schema.sql', 'r') as f:
                schema = f.read()
                # SQLite doesn't support IF NOT EXISTS for indexes, so we'll handle errors
                statements = schema.split(';')
                for statement in statements:
                    if statement.strip():
                        try:
                            self.cursor.execute(statement)
                        except sqlite3.OperationalError as e:
                            if "already exists" in str(e):
                                continue
                            else:
                                raise
            self.conn.commit()
        except Exception as e:
            logging.warning(f"Error initializing tables: {e}")
            # Tables might already exist, continue anyway
        
    def extract_all_contacts(self):
        """Main method to extract all contacts from work orders"""
        logging.info("Starting contact extraction from work orders...")
        
        # First, extract companies
        self.extract_companies()
        
        # Then, extract contacts from various fields
        self.extract_contacts_from_work_orders()
        
        # Extract relationships
        self.extract_relationships()
        
        # Calculate statistics
        self.update_statistics()
        
        logging.info("Contact extraction complete!")
        
    def extract_companies(self):
        """Extract unique companies from work orders"""
        logging.info("Extracting companies...")
        
        query = """
        SELECT DISTINCT 
            company_name,
            COUNT(*) as work_order_count,
            SUM(total_paid) as total_earnings,
            MIN(scheduled_date) as first_date,
            MAX(scheduled_date) as last_date,
            GROUP_CONCAT(DISTINCT location_city) as cities,
            GROUP_CONCAT(DISTINCT location_state) as states,
            GROUP_CONCAT(DISTINCT work_type) as categories
        FROM work_orders_markdown
        WHERE company_name IS NOT NULL
        GROUP BY company_name
        """
        
        companies = self.cursor.execute(query).fetchall()
        
        for company in companies:
            # Determine industry from work categories
            industry = self.determine_industry(company['categories'])
            company_type = self.determine_company_type(company['company_name'])
            
            # Insert or update company
            self.cursor.execute("""
                INSERT OR REPLACE INTO companies (
                    company_name, company_type, industry,
                    first_engagement_date, last_engagement_date,
                    total_work_orders, total_earnings,
                    relationship_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company['company_name'],
                company_type,
                industry,
                company['first_date'],
                company['last_date'],
                company['work_order_count'],
                company['total_earnings'] or 0,
                'active' if company['last_date'] and company['last_date'] > '2023-01-01' else 'inactive'
            ))
            
            company_id = self.cursor.lastrowid
            self.companies[company['company_name']] = company_id
            
        self.conn.commit()
        logging.info(f"Extracted {len(self.companies)} companies")
        
    def extract_contacts_from_work_orders(self):
        """Extract contacts from work order fields"""
        logging.info("Extracting contacts from work orders...")
        
        query = """
        SELECT 
            work_order_id, work_order_id as id, company_name, provider_name, provider_id,
            provider_phone, scheduled_date, location_city, location_state,
            site_contact_name, site_contact_phone,
            manager_name, manager_email, manager_phone,
            service_description_full, closeout_notes,
            buyer_custom_fields, provider_custom_fields
        FROM work_orders_markdown
        """
        
        work_orders = self.cursor.execute(query).fetchall()
        contact_count = 0
        
        for wo in work_orders:
            company_id = self.companies.get(wo['company_name'])
            
            # Extract provider as contact
            if wo['provider_name']:
                contact_id = self.create_or_update_contact({
                    'full_name': wo['provider_name'],
                    'company_id': company_id,
                    'role_type': 'technical_contact',
                    'phone': wo['provider_phone'],
                    'location_city': wo['location_city'],
                    'location_state': wo['location_state']
                })
                
                # Record interaction
                self.record_interaction(contact_id, wo['work_order_id'], wo['scheduled_date'], 'work_order')
                contact_count += 1
            
            # Extract buyer contact
            if wo['site_contact_name']:
                contact_id = self.create_or_update_contact({
                    'full_name': wo['site_contact_name'],
                    'phone': wo['site_contact_phone'],
                    'company_id': company_id,
                    'role_type': 'client_contact'
                })
                self.record_interaction(contact_id, wo['work_order_id'], wo['scheduled_date'], 'work_order')
                contact_count += 1
            
            # Extract manager contact
            if wo['manager_name']:
                contact_id = self.create_or_update_contact({
                    'full_name': wo['manager_name'],
                    'email': wo['manager_email'],
                    'phone': wo['manager_phone'],
                    'company_id': company_id,
                    'role_type': 'manager'
                })
                self.record_interaction(contact_id, wo['work_order_id'], wo['scheduled_date'], 'work_order')
                contact_count += 1
            
            # Extract contacts from description and notes
            self.extract_contacts_from_text(wo['service_description_full'], company_id, wo['work_order_id'], wo['scheduled_date'])
            self.extract_contacts_from_text(wo['closeout_notes'], company_id, wo['work_order_id'], wo['scheduled_date'])
            
            # Extract from custom fields
            if wo['buyer_custom_fields']:
                self.extract_contacts_from_json(wo['buyer_custom_fields'], company_id, wo['work_order_id'], wo['scheduled_date'])
            if wo['provider_custom_fields']:
                self.extract_contacts_from_json(wo['provider_custom_fields'], company_id, wo['work_order_id'], wo['scheduled_date'])
        
        self.conn.commit()
        logging.info(f"Extracted {contact_count} contacts")
        
    def create_or_update_contact(self, contact_info: Dict) -> int:
        """Create or update a contact record"""
        # Check if contact exists
        existing = None
        if contact_info.get('email'):
            existing = self.cursor.execute(
                "SELECT id FROM contacts WHERE email = ?", 
                (contact_info['email'],)
            ).fetchone()
        elif contact_info.get('full_name') and contact_info.get('company_id'):
            existing = self.cursor.execute(
                "SELECT id FROM contacts WHERE full_name = ? AND company_id = ?", 
                (contact_info['full_name'], contact_info['company_id'])
            ).fetchone()
        
        if existing:
            # Update existing contact
            contact_id = existing['id']
            self.cursor.execute("""
                UPDATE contacts 
                SET interaction_count = interaction_count + 1,
                    last_interaction_date = CURRENT_DATE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (contact_id,))
        else:
            # Parse name if needed
            first_name, last_name = self.parse_name(contact_info.get('full_name', ''))
            
            # Insert new contact
            self.cursor.execute("""
                INSERT INTO contacts (
                    first_name, last_name, full_name, email, phone,
                    company_id, title, role_type, location_city, location_state,
                    first_interaction_date, last_interaction_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_DATE, CURRENT_DATE)
            """, (
                first_name,
                last_name,
                contact_info.get('full_name', ''),
                contact_info.get('email'),
                contact_info.get('phone'),
                contact_info.get('company_id'),
                contact_info.get('title'),
                contact_info.get('role_type', 'client_contact'),
                contact_info.get('location_city'),
                contact_info.get('location_state')
            ))
            contact_id = self.cursor.lastrowid
            
        return contact_id
        
    def record_interaction(self, contact_id: int, work_order_id: str, date: str, interaction_type: str = 'work_order'):
        """Record an interaction with a contact"""
        self.cursor.execute("""
            INSERT INTO contact_interactions (
                contact_id, work_order_id, interaction_date, 
                interaction_type, sentiment
            ) VALUES (?, ?, ?, ?, ?)
        """, (contact_id, work_order_id, date, interaction_type, 'positive'))
        
    def extract_contacts_from_text(self, text: str, company_id: int, work_order_id: int, date: str):
        """Extract contact information from free text"""
        if not text:
            return
            
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Phone pattern
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, text)
        
        # Name patterns (before email or phone)
        name_patterns = [
            r'(?:contact|Contact|CONTACT):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:ask for|Ask for|ASK FOR):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:manager|Manager|MANAGER):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:@|at)\s*[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        ]
        
        # Extract names associated with emails
        for email in emails:
            # Look for name before email
            for pattern in name_patterns:
                match = re.search(pattern + r'.*?' + re.escape(email), text, re.IGNORECASE)
                if match:
                    contact_info = {
                        'full_name': match.group(1),
                        'email': email,
                        'company_id': company_id,
                        'role_type': 'client_contact'
                    }
                    contact_id = self.create_or_update_contact(contact_info)
                    self.record_interaction(contact_id, work_order_id, date, 'work_order')
                    break
                    
    def extract_contacts_from_json(self, json_str: str, company_id: int, work_order_id: int, date: str):
        """Extract contacts from JSON custom fields"""
        try:
            data = json.loads(json_str) if json_str else {}
            
            # Look for contact-related fields
            contact_fields = ['contact', 'manager', 'admin', 'helpdesk', 'support', 'email', 'phone']
            
            for key, value in data.items():
                if any(field in key.lower() for field in contact_fields) and value:
                    # Determine if it's an email, phone, or name
                    if '@' in str(value):
                        # Email found
                        contact_info = {'email': value, 'company_id': company_id}
                    elif re.match(r'[\d\s\-\(\)]+', str(value)):
                        # Phone found
                        contact_info = {'phone': value, 'company_id': company_id}
                    else:
                        # Assume it's a name
                        contact_info = {'full_name': value, 'company_id': company_id}
                    
                    contact_id = self.create_or_update_contact(contact_info)
                    self.record_interaction(contact_id, work_order_id, date, 'work_order')
                    
        except json.JSONDecodeError:
            pass
            
    def extract_relationships(self):
        """Extract relationships between contacts"""
        logging.info("Extracting contact relationships...")
        
        # Find contacts who worked on the same work orders
        query = """
        SELECT DISTINCT ci1.contact_id as contact1, ci2.contact_id as contact2,
               COUNT(DISTINCT ci1.work_order_id) as shared_work_orders
        FROM contact_interactions ci1
        JOIN contact_interactions ci2 ON ci1.work_order_id = ci2.work_order_id
        WHERE ci1.contact_id < ci2.contact_id
        GROUP BY ci1.contact_id, ci2.contact_id
        HAVING shared_work_orders > 1
        """
        
        relationships = self.cursor.execute(query).fetchall()
        
        for rel in relationships:
            strength = 'known'
            if rel['shared_work_orders'] > 5:
                strength = 'strong'
            elif rel['shared_work_orders'] > 2:
                strength = 'worked_together'
                
            self.cursor.execute("""
                INSERT OR IGNORE INTO contact_relationships (
                    contact_id_1, contact_id_2, relationship_type, relationship_strength
                ) VALUES (?, ?, ?, ?)
            """, (rel['contact1'], rel['contact2'], 'colleague', strength))
            
        self.conn.commit()
        logging.info(f"Extracted {len(relationships)} contact relationships")
        
    def update_statistics(self):
        """Update statistics and identify key contacts"""
        logging.info("Updating statistics and identifying key contacts...")
        
        # Update relationship strength based on interactions
        self.cursor.execute("""
            UPDATE contacts
            SET relationship_strength = CASE
                WHEN interaction_count > 10 THEN 'champion'
                WHEN interaction_count > 5 THEN 'strong'
                WHEN interaction_count > 2 THEN 'professional'
                ELSE 'new'
            END
        """)
        
        # Identify potential references
        self.cursor.execute("""
            UPDATE contacts
            SET is_reference = TRUE,
                reference_quality = CASE
                    WHEN interaction_count > 10 AND role_type IN ('manager', 'client_contact') THEN 5
                    WHEN interaction_count > 5 AND role_type IN ('manager', 'client_contact') THEN 4
                    WHEN interaction_count > 3 THEN 3
                    ELSE 2
                END
            WHERE interaction_count > 3
            AND role_type IN ('manager', 'client_contact', 'admin')
        """)
        
        # Update company tiers
        self.cursor.execute("""
            UPDATE companies
            SET company_size = CASE
                WHEN total_earnings > 10000 THEN 'enterprise'
                WHEN total_earnings > 5000 THEN 'large'
                WHEN total_earnings > 1000 THEN 'medium'
                ELSE 'small'
            END
        """)
        
        self.conn.commit()
        
    def determine_industry(self, categories: str) -> str:
        """Determine industry from work categories"""
        if not categories:
            return 'General'
            
        categories_lower = categories.lower()
        
        industry_keywords = {
            'Healthcare': ['healthcare', 'medical', 'hospital', 'clinic', 'health'],
            'Finance': ['finance', 'banking', 'financial', 'insurance', 'investment'],
            'Retail': ['retail', 'store', 'shop', 'commerce', 'pos'],
            'Technology': ['software', 'tech', 'it', 'computer', 'network'],
            'Education': ['education', 'school', 'university', 'training'],
            'Manufacturing': ['manufacturing', 'factory', 'production', 'industrial'],
            'Hospitality': ['hotel', 'restaurant', 'hospitality', 'food service'],
            'Government': ['government', 'federal', 'state', 'municipal', 'public']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in categories_lower for keyword in keywords):
                return industry
                
        return 'General'
        
    def determine_company_type(self, company_name: str) -> str:
        """Determine company type from name"""
        name_lower = company_name.lower()
        
        if any(term in name_lower for term in ['llc', 'inc', 'corp', 'company']):
            return 'client'
        elif any(term in name_lower for term in ['staffing', 'solutions', 'services']):
            return 'partner'
        else:
            return 'client'
            
    def parse_name(self, full_name: str) -> Tuple[str, str]:
        """Parse full name into first and last name"""
        if not full_name:
            return '', ''
            
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return parts[0], ' '.join(parts[1:])
        else:
            return full_name, ''
            
    def generate_report(self):
        """Generate a summary report of extracted contacts"""
        stats = {}
        
        # Total companies
        stats['total_companies'] = self.cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        
        # Total contacts
        stats['total_contacts'] = self.cursor.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        
        # Contacts by role
        role_counts = self.cursor.execute("""
            SELECT role_type, COUNT(*) as count 
            FROM contacts 
            GROUP BY role_type
        """).fetchall()
        stats['contacts_by_role'] = {row['role_type']: row['count'] for row in role_counts}
        
        # Reference contacts
        stats['reference_contacts'] = self.cursor.execute(
            "SELECT COUNT(*) FROM contacts WHERE is_reference = TRUE"
        ).fetchone()[0]
        
        # Top companies by contacts
        top_companies = self.cursor.execute("""
            SELECT c.company_name, COUNT(ct.id) as contact_count
            FROM companies c
            JOIN contacts ct ON c.id = ct.company_id
            GROUP BY c.id
            ORDER BY contact_count DESC
            LIMIT 10
        """).fetchall()
        stats['top_companies'] = [(row['company_name'], row['contact_count']) for row in top_companies]
        
        # Industries
        industries = self.cursor.execute("""
            SELECT industry, COUNT(*) as count
            FROM companies
            GROUP BY industry
        """).fetchall()
        stats['industries'] = {row['industry']: row['count'] for row in industries}
        
        return stats
        
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main execution function"""
    extractor = ContactExtractor()
    
    try:
        # Extract all contacts
        extractor.extract_all_contacts()
        
        # Generate report
        report = extractor.generate_report()
        
        print("\n" + "="*60)
        print("CONTACT EXTRACTION COMPLETE")
        print("="*60)
        print(f"Total Companies: {report['total_companies']}")
        print(f"Total Contacts: {report['total_contacts']}")
        print(f"Reference Contacts: {report['reference_contacts']}")
        
        print("\nContacts by Role:")
        for role, count in report['contacts_by_role'].items():
            print(f"  {role or 'Unknown'}: {count}")
            
        print("\nTop Companies by Contacts:")
        for company, count in report['top_companies']:
            print(f"  {company}: {count} contacts")
            
        print("\nIndustries:")
        for industry, count in report['industries'].items():
            print(f"  {industry}: {count} companies")
            
    finally:
        extractor.close()


if __name__ == "__main__":
    main() 