#!/usr/bin/env python3
"""
Comprehensive Work Order Import Script
Processes markdown and PDF work order files, extracts detailed information,
and stores in database with full search capabilities
"""

import os
import re
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from comprehensive_fieldnation_processor import ComprehensiveFieldNationProcessor, WorkOrderData
import PyPDF2
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkOrderBatchImporter:
    def __init__(self, database_path: str = 'resume_database.db'):
        self.database_path = database_path
        self.processor = ComprehensiveFieldNationProcessor(database_path)
        self.markdown_dir = 'downloaded work orders'
        self.pdf_dir = 'fieldnation_pdfs'
        
    def extract_work_order_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract work order ID from filename"""
        # Match patterns like: work_order_430895_2025_06_10_21_29_56.md
        patterns = [
            r'work_order_(\d+)_\d{4}_\d{2}_\d{2}',  # work_order_ID_date format
            r'wo(\d+)',  # wo123456 format
            r'(\d{6,})'  # standalone 6+ digit numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        return None
    
    def find_matching_files(self, limit: int = 25) -> List[Tuple[str, Optional[str]]]:
        """Find matching markdown and PDF files"""
        markdown_files = []
        pdf_files = []
        
        # Get all markdown files
        if os.path.exists(self.markdown_dir):
            markdown_files = [f for f in os.listdir(self.markdown_dir) if f.endswith('.md')]
            markdown_files.sort()  # Sort for consistent processing
        
        # Get all PDF files
        if os.path.exists(self.pdf_dir):
            pdf_files = [f for f in os.listdir(self.pdf_dir) if f.endswith('.pdf')]
        
        # Create a mapping of work order IDs to PDF files
        pdf_map = {}
        for pdf_file in pdf_files:
            wo_id = self.extract_work_order_id_from_filename(pdf_file)
            if wo_id:
                pdf_map[wo_id] = pdf_file
        
        # Match markdown files with PDFs
        matched_files = []
        processed_count = 0
        
        for md_file in markdown_files:
            if processed_count >= limit:
                break
                
            wo_id = self.extract_work_order_id_from_filename(md_file)
            pdf_file = pdf_map.get(wo_id) if wo_id else None
            
            matched_files.append((md_file, pdf_file))
            processed_count += 1
            
        logger.info(f"Found {len(matched_files)} markdown files, {sum(1 for _, pdf in matched_files if pdf)} have matching PDFs")
        return matched_files
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text from {pdf_path}: {e}")
            return ""
    
    def enhance_work_order_with_pdf(self, work_order: WorkOrderData, pdf_path: str) -> WorkOrderData:
        """Enhance work order data with information from PDF"""
        if not pdf_path or not os.path.exists(pdf_path):
            return work_order
        
        try:
            pdf_text = self.extract_pdf_text(pdf_path)
            if not pdf_text:
                return work_order
            
            # Extract additional details from PDF that might not be in markdown
            
            # Look for more detailed payment information
            pay_matches = re.findall(r'\$[\d,]+\.?\d*', pdf_text)
            if pay_matches and not work_order.pay_amount:
                # Take the highest amount found
                amounts = [float(match.replace('$', '').replace(',', '')) for match in pay_matches]
                work_order.pay_amount = max(amounts)
            
            # Look for more detailed location information
            location_patterns = [
                r'Address[:\s]+([^\n]+)',
                r'Location[:\s]+([^\n]+)',
                r'Site[:\s]+([^\n]+)'
            ]
            for pattern in location_patterns:
                match = re.search(pattern, pdf_text, re.IGNORECASE)
                if match and not work_order.location:
                    work_order.location = match.group(1).strip()
                    break
            
            # Look for contact information
            phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', pdf_text)
            if phone_matches:
                work_order.contact_phone = phone_matches[0]
            
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', pdf_text)
            if email_matches:
                work_order.client_email = email_matches[0]
            
            # Look for detailed requirements
            requirement_patterns = [
                r'Requirements?[:\s]+([^\n]+(?:\n[^\n]+)*?)(?:\n\s*\n|\n[A-Z]|\Z)',
                r'Qualifications?[:\s]+([^\n]+(?:\n[^\n]+)*?)(?:\n\s*\n|\n[A-Z]|\Z)',
                r'Must have[:\s]+([^\n]+(?:\n[^\n]+)*?)(?:\n\s*\n|\n[A-Z]|\Z)'
            ]
            for pattern in requirement_patterns:
                match = re.search(pattern, pdf_text, re.IGNORECASE | re.DOTALL)
                if match:
                    requirements = match.group(1).strip()
                    if requirements and len(requirements) > len(work_order.experience_required or ""):
                        work_order.experience_required = requirements
                    break
            
            # Enhanced work order with PDF data
            if hasattr(work_order, 'source_file_path'):
                work_order.source_file_path = f"{work_order.source_file_path}, PDF: {os.path.basename(pdf_path)}"
            else:
                work_order.data_source = f"{getattr(work_order, 'data_source', 'markdown')}, PDF: {os.path.basename(pdf_path)}"
            
        except Exception as e:
            logger.error(f"Error enhancing work order with PDF {pdf_path}: {e}")
        
        return work_order
    
    def import_work_orders(self, limit: int = 25) -> Dict[str, int]:
        """Import work orders from markdown and PDF files"""
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'duplicates': 0
        }
        
        # Find matching files
        matched_files = self.find_matching_files(limit)
        
        if not matched_files:
            logger.warning("No work order files found to process")
            return results
        
        # Process each file pair
        for md_file, pdf_file in matched_files:
            try:
                md_path = os.path.join(self.markdown_dir, md_file)
                pdf_path = os.path.join(self.pdf_dir, pdf_file) if pdf_file else None
                
                logger.info(f"Processing: {md_file} {'+ ' + pdf_file if pdf_file else ''}")
                
                # Process markdown file
                work_order = self.processor.process_markdown_file(md_path)
                if not work_order:
                    logger.error(f"Failed to process markdown file: {md_file}")
                    results['failed'] += 1
                    continue
                
                # Enhance with PDF data if available
                if pdf_path:
                    work_order = self.enhance_work_order_with_pdf(work_order, pdf_path)
                
                # Check for duplicates
                if self.processor.work_order_exists(work_order.fn_work_order_id):
                    logger.warning(f"Work order {work_order.fn_work_order_id} already exists, skipping")
                    results['duplicates'] += 1
                    continue
                
                # Store in database
                if self.processor.store_work_order(work_order):
                    results['successful'] += 1
                    logger.info(f"Successfully imported work order {work_order.fn_work_order_id}: {work_order.title}")
                else:
                    results['failed'] += 1
                    logger.error(f"Failed to store work order {work_order.fn_work_order_id}")
                
                results['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
                results['failed'] += 1
        
        return results
    
    def print_import_summary(self, results: Dict[str, int]):
        """Print import summary"""
        print("\n" + "="*60)
        print("WORK ORDER IMPORT SUMMARY")
        print("="*60)
        print(f"Files Processed: {results['processed']}")
        print(f"Successfully Imported: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Duplicates Skipped: {results['duplicates']}")
        print(f"Success Rate: {(results['successful']/max(results['processed'], 1)*100):.1f}%")
        print("="*60)
        
        if results['successful'] > 0:
            print(f"\n✅ {results['successful']} work orders are now available in your database!")
            print("🌐 View them in your Flask app at http://127.0.0.1:8000")
            print("📁 Check the FieldNation tab for the new work order tiles")

def main():
    """Main execution function"""
    print("🚀 Starting Work Order Batch Import...")
    print("📁 Processing markdown files and matching PDFs...")
    
    importer = WorkOrderBatchImporter()
    
    # Import 25 work orders
    results = importer.import_work_orders(limit=25)
    
    # Print summary
    importer.print_import_summary(results)
    
    if results['successful'] > 0:
        print("\n📊 Database now contains comprehensive work order data with:")
        print("   • Complete work order details")
        print("   • Enhanced information from PDF files")
        print("   • Full-text search capabilities")
        print("   • Categorized skills and technologies")
        print("   • Location and payment information")
        print("   • Client and company details")

if __name__ == '__main__':
    main() 