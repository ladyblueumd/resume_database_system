#!/usr/bin/env python
"""
PDF Extraction Engine for FieldNation Work Orders
Comprehensive data extraction from PDF files with no text limits
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pdfplumber

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FieldNationPDFExtractor:
    def __init__(self, db_path: str = 'resume_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_tables()
        
        # Extraction patterns for various data types
        self.patterns = self._init_extraction_patterns()
        
    def init_tables(self):
        """Initialize PDF extraction tables"""
        try:
            with open('pdf_extraction_schema.sql', 'r') as f:
                schema = f.read()
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
            logging.info("PDF extraction tables initialized")
        except Exception as e:
            logging.warning(f"Error initializing PDF tables: {e}")
    
    def _init_extraction_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for data extraction"""
        return {
            'work_order_id': [
                r'Work Order[:\s#]*(\d+)',
                r'WO[:\s#]*(\d+)',
                r'Order[:\s#]*(\d+)',
                r'ID[:\s#]*(\d+)',
                r'Number[:\s#]*(\d+)',
                r'Reference[:\s#]*(\d+)'
            ],
            'title': [
                r'Title[:\s]*(.+?)(?:\n|$)',
                r'Service[:\s]*(.+?)(?:\n|$)',
                r'Job Title[:\s]*(.+?)(?:\n|$)',
                r'Work Description[:\s]*(.+?)(?:\n|$)'
            ],
            'company_name': [
                r'Company[:\s]*(.+?)(?:\n|$)',
                r'Client[:\s]*(.+?)(?:\n|$)',
                r'Organization[:\s]*(.+?)(?:\n|$)',
                r'Business[:\s]*(.+?)(?:\n|$)'
            ],
            'status': [
                r'Status[:\s]*(.+?)(?:\n|$)',
                r'State[:\s]*(.+?)(?:\n|$)',
                r'Condition[:\s]*(.+?)(?:\n|$)'
            ],
            'dates': [
                r'Date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
            ],
            'money': [
                r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|dollars?)',
                r'Amount[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'Pay[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'Total[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            ],
            'phone': [
                r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                r'Phone[:\s]*(.+?)(?:\n|$)',
                r'Tel[:\s]*(.+?)(?:\n|$)',
                r'Contact[:\s]*(.+?)(?:\n|$)'
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'address': [
                r'Address[:\s]*(.+?)(?:\n\n|\n[A-Z])',
                r'Location[:\s]*(.+?)(?:\n\n|\n[A-Z])',
                r'Site[:\s]*(.+?)(?:\n\n|\n[A-Z])',
                r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl).*?)(?:\n|$)'
            ],
            'time': [
                r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',
                r'Time[:\s]*(.+?)(?:\n|$)',
                r'Schedule[:\s]*(.+?)(?:\n|$)',
                r'Hours[:\s]*(.+?)(?:\n|$)'
            ]
        }
    
    def extract_from_pdf_directory(self, pdf_directory: str) -> Dict[str, Any]:
        """Extract data from all PDFs in a directory"""
        pdf_dir = Path(pdf_directory)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory not found: {pdf_directory}")
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        logging.info(f"Found {len(pdf_files)} PDF files to process")
        
        results = {
            'total_files': len(pdf_files),
            'processed': 0,
            'errors': 0,
            'extracted_records': []
        }
        
        for pdf_file in pdf_files:
            try:
                logging.info(f"Processing: {pdf_file.name}")
                extracted_data = self.extract_from_pdf(str(pdf_file))
                
                if extracted_data:
                    self.save_extracted_data(extracted_data)
                    results['extracted_records'].append(extracted_data['work_order_id'])
                    results['processed'] += 1
                else:
                    results['errors'] += 1
                    
            except Exception as e:
                logging.error(f"Error processing {pdf_file.name}: {e}")
                results['errors'] += 1
        
        logging.info(f"PDF extraction complete: {results['processed']} processed, {results['errors']} errors")
        return results
    
    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Extract comprehensive data from a single PDF file"""
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                logging.error(f"PDF file not found: {pdf_path}")
                return None
            
            # Initialize data structure
            data = self._init_data_structure(pdf_file)
            
            # Extract using multiple methods for comprehensive coverage
            text_data = self._extract_with_pdfplumber(pdf_path)
            
            # Set page count
            data['pdf_page_count'] = text_data.get('page_count', 0)
            
            # Combine all extracted text
            full_text = self._combine_text_sources(text_data)
            data['raw_text_full'] = full_text
            
            # Store page-by-page text
            for i, page_text in enumerate(text_data.get('pages', [])[:5]):
                data[f'raw_text_page_{i+1}'] = page_text
            
            # Extract structured information
            self._extract_work_order_details(data, full_text)
            self._extract_company_information(data, full_text)
            self._extract_financial_information(data, full_text)
            self._extract_location_information(data, full_text)
            self._extract_contact_information(data, full_text)
            self._extract_time_information(data, full_text)
            self._extract_requirements_information(data, full_text)
            
            # Store structured data
            data['extracted_tables'] = json.dumps(text_data.get('tables', []))
            
            # Calculate quality scores
            data['extraction_quality_score'] = self._calculate_quality_score(data)
            data['text_extraction_confidence'] = text_data.get('confidence', 0.0)
            data['data_completeness_score'] = self._calculate_completeness_score(data)
            
            # Determine if manual review is needed
            data['needs_manual_review'] = (
                data['extraction_quality_score'] < 0.7 or
                data['text_extraction_confidence'] < 0.8 or
                not data['work_order_id']
            )
            
            return data
            
        except Exception as e:
            logging.error(f"Error extracting from PDF {pdf_path}: {e}")
            return None
    
    def _init_data_structure(self, pdf_file: Path) -> Dict[str, Any]:
        """Initialize the data structure for extracted information"""
        file_stats = pdf_file.stat()
        
        return {
            'pdf_filename': pdf_file.name,
            'pdf_file_path': str(pdf_file),
            'pdf_file_size': file_stats.st_size,
            'pdf_page_count': 0,
            'extraction_date': datetime.now().isoformat(),
            
            # Initialize all fields to None/default values
            'work_order_id': None,
            'work_order_number': None,
            'field_nation_id': None,
            'reference_number': None,
            'title': None,
            'description': None,
            'full_description': None,
            'scope_of_work': None,
            'work_summary': None,
            'service_type': None,
            'work_category': None,
            'priority_level': None,
            'status': None,
            'status_detail': None,
            'date_created': None,
            'date_posted': None,
            'date_scheduled': None,
            'date_started': None,
            'date_completed': None,
            'date_approved': None,
            'date_paid': None,
            'company_name': None,
            'company_id': None,
            'company_address': None,
            'company_phone': None,
            'company_email': None,
            'company_website': None,
            'company_contact_person': None,
            'buyer_name': None,
            'buyer_company': None,
            'buyer_email': None,
            'buyer_phone': None,
            'buyer_address': None,
            'buyer_contact_instructions': None,
            'provider_name': None,
            'provider_id': None,
            'provider_email': None,
            'provider_phone': None,
            'provider_rating': None,
            'provider_reviews_count': None,
            'work_location_name': None,
            'work_location_address': None,
            'work_location_city': None,
            'work_location_state': None,
            'work_location_zip': None,
            'work_location_country': 'USA',
            'work_location_coordinates': None,
            'work_location_instructions': None,
            'parking_instructions': None,
            'access_instructions': None,
            'total_amount': None,
            'base_pay': None,
            'bonus_amount': None,
            'additional_pay': None,
            'expense_allowance': None,
            'mileage_reimbursement': None,
            'hourly_rate': None,
            'overtime_rate': None,
            'currency': 'USD',
            'payment_terms': None,
            'payment_method': None,
            'estimated_duration': None,
            'scheduled_start_time': None,
            'scheduled_end_time': None,
            'actual_start_time': None,
            'actual_end_time': None,
            'total_hours_worked': None,
            'break_time': None,
            'travel_time': None,
            'required_skills': None,
            'required_certifications': None,
            'required_tools': None,
            'required_equipment': None,
            'background_check_required': False,
            'drug_test_required': False,
            'insurance_required': False,
            'equipment_provided': None,
            'equipment_needed': None,
            'technology_requirements': None,
            'software_requirements': None,
            'hardware_specifications': None,
            'network_requirements': None,
            'primary_contact_name': None,
            'primary_contact_phone': None,
            'primary_contact_email': None,
            'secondary_contact_name': None,
            'secondary_contact_phone': None,
            'secondary_contact_email': None,
            'emergency_contact_name': None,
            'emergency_contact_phone': None,
            'check_in_required': False,
            'check_in_contact': None,
            'check_in_phone': None,
            'check_in_instructions': None,
            'check_out_required': False,
            'check_out_contact': None,
            'check_out_phone': None,
            'check_out_instructions': None,
            'work_instructions': None,
            'special_instructions': None,
            'safety_requirements': None,
            'dress_code': None,
            'security_requirements': None,
            'confidentiality_requirements': None,
            'completion_requirements': None,
            'approval_process': None,
            'approval_contact_name': None,
            'approval_contact_phone': None,
            'approval_contact_email': None,
            'deliverables': None,
            'documentation_required': None,
            'photos_required': False,
            'signature_required': False,
            'known_issues': None,
            'troubleshooting_notes': None,
            'previous_work_notes': None,
            'vendor_notes': None,
            'client_notes': None,
            'provider_notes': None,
            'admin_notes': None,
            'custom_field_1_name': None,
            'custom_field_1_value': None,
            'custom_field_2_name': None,
            'custom_field_2_value': None,
            'custom_field_3_name': None,
            'custom_field_3_value': None,
            'custom_field_4_name': None,
            'custom_field_4_value': None,
            'custom_field_5_name': None,
            'custom_field_5_value': None,
            'raw_text_page_1': None,
            'raw_text_page_2': None,
            'raw_text_page_3': None,
            'raw_text_page_4': None,
            'raw_text_page_5': None,
            'raw_text_full': None,
            'extracted_tables': None,
            'extracted_forms': None,
            'extracted_signatures': None,
            'extracted_images': None,
            'text_extraction_confidence': 0.0,
            'data_completeness_score': 0.0,
            'manual_review_required': False,
            'extraction_errors': None,
            'is_processed': False,
            'is_merged_with_markdown': False,
            'needs_manual_review': False
        }
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and structured data using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_text = []
                tables = []
                
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                return {
                    'pages': pages_text,
                    'full_text': '\n\n'.join(pages_text),
                    'tables': tables,
                    'page_count': len(pdf.pages),
                    'confidence': 0.9  # pdfplumber is generally reliable
                }
                
        except Exception as e:
            logging.error(f"Error with pdfplumber extraction: {e}")
            return {'pages': [], 'full_text': '', 'tables': [], 'page_count': 0, 'confidence': 0.0}
    
    def _combine_text_sources(self, text_data: Dict) -> str:
        """Combine text from different extraction methods"""
        # Prefer pdfplumber text, fallback to OCR
        if text_data.get('full_text') and len(text_data['full_text'].strip()) > 100:
            return text_data['full_text']
        else:
            return ""
    
    def _extract_work_order_details(self, data: Dict, text: str):
        """Extract work order identification and basic details"""
        # Work Order ID
        for pattern in self.patterns['work_order_id']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['work_order_id'] = match.group(1)
                break
        
        # Title
        for pattern in self.patterns['title']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['title'] = match.group(1).strip()
                break
        
        # Status
        for pattern in self.patterns['status']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['status'] = match.group(1).strip()
                break
        
        # Extract full description (everything between certain markers)
        desc_patterns = [
            r'Description[:\s]*(.+?)(?=\n\n|\nLocation|\nCompany|\nContact|$)',
            r'Summary[:\s]*(.+?)(?=\n\n|\nLocation|\nCompany|\nContact|$)',
            r'Details[:\s]*(.+?)(?=\n\n|\nLocation|\nCompany|\nContact|$)'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                data['full_description'] = match.group(1).strip()
                break
    
    def _extract_company_information(self, data: Dict, text: str):
        """Extract company and client information"""
        # Company name
        for pattern in self.patterns['company_name']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['company_name'] = match.group(1).strip()
                break
        
        # Company email
        emails = re.findall(self.patterns['email'][0], text)
        if emails:
            data['company_email'] = emails[0]
        
        # Company phone
        phones = re.findall(self.patterns['phone'][0], text)
        if phones:
            if isinstance(phones[0], tuple):
                data['company_phone'] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
            else:
                data['company_phone'] = phones[0]
    
    def _extract_financial_information(self, data: Dict, text: str):
        """Extract payment and financial details"""
        # Extract monetary amounts
        money_matches = []
        for pattern in self.patterns['money']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            money_matches.extend(matches)
        
        if money_matches:
            # Convert to float and find the largest (likely total amount)
            amounts = []
            for match in money_matches:
                try:
                    amount = float(match.replace(',', ''))
                    amounts.append(amount)
                except:
                    continue
            
            if amounts:
                data['total_amount'] = max(amounts)
                data['base_pay'] = min(amounts) if len(amounts) > 1 else amounts[0]
        
        # Extract payment terms
        payment_patterns = [
            r'Payment[:\s]*(.+?)(?:\n|$)',
            r'Terms[:\s]*(.+?)(?:\n|$)',
            r'Method[:\s]*(.+?)(?:\n|$)'
        ]
        
        for pattern in payment_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['payment_terms'] = match.group(1).strip()
                break
    
    def _extract_location_information(self, data: Dict, text: str):
        """Extract location and address information"""
        # Extract addresses
        for pattern in self.patterns['address']:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                data['work_location_address'] = address
                
                # Try to parse city, state, zip
                city_state_zip = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})', address)
                if city_state_zip:
                    data['work_location_city'] = city_state_zip.group(1).strip()
                    data['work_location_state'] = city_state_zip.group(2)
                    data['work_location_zip'] = city_state_zip.group(3)
                break
        
        # Extract parking/access instructions
        parking_patterns = [
            r'Parking[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'Access[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'Entry[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in parking_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if 'parking' in pattern.lower():
                    data['parking_instructions'] = match.group(1).strip()
                else:
                    data['access_instructions'] = match.group(1).strip()
    
    def _extract_contact_information(self, data: Dict, text: str):
        """Extract contact information"""
        # Extract all emails
        emails = re.findall(self.patterns['email'][0], text)
        if emails:
            data['primary_contact_email'] = emails[0]
            if len(emails) > 1:
                data['secondary_contact_email'] = emails[1]
        
        # Extract all phone numbers
        phones = re.findall(self.patterns['phone'][0], text)
        if phones:
            if isinstance(phones[0], tuple):
                data['primary_contact_phone'] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
            else:
                data['primary_contact_phone'] = phones[0]
            
            if len(phones) > 1:
                if isinstance(phones[1], tuple):
                    data['secondary_contact_phone'] = f"({phones[1][0]}) {phones[1][1]}-{phones[1][2]}"
                else:
                    data['secondary_contact_phone'] = phones[1]
        
        # Extract contact names
        contact_patterns = [
            r'Contact[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Manager[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Representative[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in contact_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['primary_contact_name'] = match.group(1).strip()
                break
    
    def _extract_time_information(self, data: Dict, text: str):
        """Extract time and scheduling information"""
        # Extract dates
        dates = []
        for pattern in self.patterns['dates']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        if dates:
            data['date_scheduled'] = dates[0]
            if len(dates) > 1:
                data['date_created'] = dates[1]
        
        # Extract times
        times = re.findall(self.patterns['time'][0], text, re.IGNORECASE)
        if times:
            data['scheduled_start_time'] = times[0]
            if len(times) > 1:
                data['scheduled_end_time'] = times[1]
        
        # Extract duration
        duration_patterns = [
            r'Duration[:\s]*(.+?)(?:\n|$)',
            r'Hours[:\s]*(\d+(?:\.\d+)?)',
            r'Time[:\s]*(\d+(?:\.\d+)?)\s*hours?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['estimated_duration'] = match.group(1).strip()
                break
    
    def _extract_requirements_information(self, data: Dict, text: str):
        """Extract requirements and qualifications"""
        # Extract skills
        skills_patterns = [
            r'Skills[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'Requirements[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'Qualifications[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in skills_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                data['required_skills'] = match.group(1).strip()
                break
        
        # Extract tools/equipment
        tools_patterns = [
            r'Tools[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'Equipment[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'Materials[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in tools_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                data['required_tools'] = match.group(1).strip()
                break
        
        # Check for background check requirements
        if re.search(r'background\s+check', text, re.IGNORECASE):
            data['background_check_required'] = True
        
        # Check for drug test requirements
        if re.search(r'drug\s+test', text, re.IGNORECASE):
            data['drug_test_required'] = True
        
        # Check for insurance requirements
        if re.search(r'insurance', text, re.IGNORECASE):
            data['insurance_required'] = True
    
    def _calculate_quality_score(self, data: Dict) -> float:
        """Calculate extraction quality score based on completeness"""
        key_fields = [
            'work_order_id', 'title', 'company_name', 'status',
            'work_location_address', 'total_amount', 'primary_contact_phone'
        ]
        
        filled_fields = sum(1 for field in key_fields if data.get(field))
        return filled_fields / len(key_fields)
    
    def _calculate_completeness_score(self, data: Dict) -> float:
        """Calculate data completeness score"""
        all_fields = [k for k in data.keys() if not k.startswith('raw_text') and k not in ['id', 'extraction_date']]
        filled_fields = sum(1 for field in all_fields if data.get(field) is not None and data.get(field) != '')
        return filled_fields / len(all_fields)
    
    def save_extracted_data(self, data: Dict[str, Any]):
        """Save extracted data to database"""
        try:
            # Prepare column names and values
            columns = list(data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            column_names = ', '.join(columns)
            
            query = f"""
                INSERT INTO work_orders_pdf ({column_names})
                VALUES ({placeholders})
            """
            
            values = [data[col] for col in columns]
            
            self.cursor.execute(query, values)
            self.conn.commit()
            
            logging.info(f"Saved PDF data for work order: {data.get('work_order_id', 'Unknown')}")
            
        except Exception as e:
            logging.error(f"Error saving PDF data: {e}")
            self.conn.rollback()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_directory>")
        sys.exit(1)
    
    pdf_directory = sys.argv[1]
    
    extractor = FieldNationPDFExtractor()
    
    try:
        results = extractor.extract_from_pdf_directory(pdf_directory)
        
        print("\n" + "="*60)
        print("PDF EXTRACTION COMPLETE")
        print("="*60)
        print(f"Total Files: {results['total_files']}")
        print(f"Successfully Processed: {results['processed']}")
        print(f"Errors: {results['errors']}")
        print(f"Success Rate: {results['processed']/results['total_files']*100:.1f}%")
        
        if results['extracted_records']:
            print(f"\nExtracted Work Orders:")
            for wo_id in results['extracted_records'][:10]:  # Show first 10
                print(f"  - {wo_id}")
            if len(results['extracted_records']) > 10:
                print(f"  ... and {len(results['extracted_records']) - 10} more")
                
    finally:
        extractor.close()


if __name__ == "__main__":
    main() 