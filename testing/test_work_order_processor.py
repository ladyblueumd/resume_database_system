#!/usr/bin/env python3
"""
Test Runner for FieldNation Work Order Processing System
Validates the enhanced database system and processing capabilities
"""

import os
import sqlite3
import json
from comprehensive_fieldnation_processor import ComprehensiveFieldNationProcessor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_setup():
    """Test database setup and table creation"""
    logger.info("Testing database setup...")
    
    processor = ComprehensiveFieldNationProcessor('test_resume_database.db')
    
    # Check if tables were created
    conn = processor.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='fieldnation_work_orders'
    """)
    
    table_exists = cursor.fetchone() is not None
    conn.close()
    
    if table_exists:
        logger.info("✅ Database setup successful - fieldnation_work_orders table created")
        return True
    else:
        logger.error("❌ Database setup failed - table not created")
        return False

def test_markdown_processing():
    """Test processing of markdown files"""
    logger.info("Testing markdown file processing...")
    
    # Check if markdown files exist
    markdown_dir = "downloaded work orders"
    if not os.path.exists(markdown_dir):
        logger.warning(f"⚠️ Markdown directory not found: {markdown_dir}")
        return False
    
    markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')]
    if not markdown_files:
        logger.warning("⚠️ No markdown files found to process")
        return False
    
    logger.info(f"Found {len(markdown_files)} markdown files")
    
    # Process a sample file
    processor = ComprehensiveFieldNationProcessor('test_resume_database.db')
    sample_file = os.path.join(markdown_dir, markdown_files[0])
    
    work_order = processor.process_markdown_file(sample_file)
    
    if work_order:
        logger.info("✅ Markdown processing successful")
        logger.info(f"Sample work order: {work_order.title} - {work_order.buyer_company}")
        return True
    else:
        logger.error("❌ Markdown processing failed")
        return False

def test_pdf_processing():
    """Test processing of PDF files"""
    logger.info("Testing PDF file processing...")
    
    # Check if PDF files exist
    pdf_dir = "fieldnation_pdfs"
    if not os.path.exists(pdf_dir):
        logger.warning(f"⚠️ PDF directory not found: {pdf_dir}")
        return False
    
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    if not pdf_files:
        logger.warning("⚠️ No PDF files found to process")
        return False
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    # Process a sample file
    processor = ComprehensiveFieldNationProcessor('test_resume_database.db')
    sample_file = os.path.join(pdf_dir, pdf_files[0])
    
    work_order = processor.process_pdf_file(sample_file)
    
    if work_order:
        logger.info("✅ PDF processing successful")
        logger.info(f"Sample work order: {work_order.title} - {work_order.buyer_company}")
        return True
    else:
        logger.error("❌ PDF processing failed")
        return False

def test_database_storage():
    """Test storing work orders in database"""
    logger.info("Testing database storage...")
    
    processor = ComprehensiveFieldNationProcessor('test_resume_database.db')
    
    # Create a test work order
    from comprehensive_fieldnation_processor import WorkOrderData
    
    test_work_order = WorkOrderData(
        fn_work_order_id="TEST123",
        title="Test Installation Work Order",
        buyer_company="Test Company Inc.",
        service_date="2024-01-15",
        location="San Francisco, CA",
        pay_amount=150.00,
        work_type="Installation",
        industry_category="Technology Services",
        complexity_level="Medium",
        work_description="Test work order for system validation",
        required_skills=["Installation", "Troubleshooting", "Customer Service"],
        technologies_used=["Windows 10", "Network Setup", "POS System"],
        required_tools=["Screwdriver", "Cable Tester", "Laptop"],
        status="Completed",
        data_source="test"
    )
    
    success = processor.save_work_order(test_work_order)
    
    if success:
        logger.info("✅ Database storage successful")
        return True
    else:
        logger.error("❌ Database storage failed")
        return False

def test_job_matching():
    """Test job matching functionality"""
    logger.info("Testing job matching functionality...")
    
    # First ensure we have some data
    processor = ComprehensiveFieldNationProcessor('test_resume_database.db')
    
    # Check if we have work orders in database
    conn = processor.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM fieldnation_work_orders")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        logger.warning("⚠️ No work orders in database for matching test")
        return False
    
    # Test job matching
    from enhanced_work_order_endpoints import WorkOrderMatchingEngine
    
    matching_engine = WorkOrderMatchingEngine('test_resume_database.db')
    
    test_job_description = """
    We are seeking a skilled IT Technician to join our team. The ideal candidate will have:
    - Experience with Windows 10 installation and configuration
    - Strong troubleshooting skills
    - Customer service experience
    - Knowledge of POS systems and network setup
    - Ability to work independently at client sites
    """
    
    matches = matching_engine.match_job_to_work_orders(test_job_description, limit=5)
    
    if matches:
        logger.info(f"✅ Job matching successful - found {len(matches)} matches")
        for match in matches[:2]:
            logger.info(f"Match: {match.get('title', 'N/A')} - Score: {match.get('match_score', 0):.2f}")
        return True
    else:
        logger.error("❌ Job matching failed")
        return False

def test_full_processing():
    """Test processing a small batch of files"""
    logger.info("Testing full file processing...")
    
    processor = ComprehensiveFieldNationProcessor('test_resume_database.db')
    
    # Process first 5 markdown files if available
    markdown_dir = "downloaded work orders"
    if os.path.exists(markdown_dir):
        markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')][:5]
        
        processed_count = 0
        for filename in markdown_files:
            file_path = os.path.join(markdown_dir, filename)
            work_order = processor.process_markdown_file(file_path)
            if work_order and processor.save_work_order(work_order):
                processed_count += 1
        
        logger.info(f"✅ Processed {processed_count}/{len(markdown_files)} markdown files")
    
    # Process first 2 PDF files if available
    pdf_dir = "fieldnation_pdfs"
    if os.path.exists(pdf_dir):
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')][:2]
        
        processed_count = 0
        for filename in pdf_files:
            file_path = os.path.join(pdf_dir, filename)
            work_order = processor.process_pdf_file(file_path)
            if work_order and processor.save_work_order(work_order):
                processed_count += 1
        
        logger.info(f"✅ Processed {processed_count}/{len(pdf_files)} PDF files")
    
    return True

def test_data_extraction():
    """Test data extraction quality"""
    logger.info("Testing data extraction quality...")
    
    # Check database for extracted data quality
    conn = sqlite3.connect('test_resume_database.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN title IS NOT NULL AND title != '' THEN 1 END) as has_title,
            COUNT(CASE WHEN buyer_company IS NOT NULL AND buyer_company != '' THEN 1 END) as has_company,
            COUNT(CASE WHEN pay_amount IS NOT NULL AND pay_amount > 0 THEN 1 END) as has_pay,
            COUNT(CASE WHEN work_description IS NOT NULL AND work_description != '' THEN 1 END) as has_description,
            COUNT(CASE WHEN technologies_used IS NOT NULL AND technologies_used != '[]' THEN 1 END) as has_tech
        FROM fieldnation_work_orders
    """)
    
    stats = cursor.fetchone()
    conn.close()
    
    if stats[0] > 0:  # total > 0
        total = stats[0]
        logger.info(f"✅ Data extraction analysis for {total} work orders:")
        logger.info(f"  - Has Title: {stats[1]}/{total} ({stats[1]/total*100:.1f}%)")
        logger.info(f"  - Has Company: {stats[2]}/{total} ({stats[2]/total*100:.1f}%)")
        logger.info(f"  - Has Pay: {stats[3]}/{total} ({stats[3]/total*100:.1f}%)")
        logger.info(f"  - Has Description: {stats[4]}/{total} ({stats[4]/total*100:.1f}%)")
        logger.info(f"  - Has Technologies: {stats[5]}/{total} ({stats[5]/total*100:.1f}%)")
        return True
    else:
        logger.warning("⚠️ No data found for extraction analysis")
        return False

def cleanup_test_database():
    """Clean up test database"""
    if os.path.exists('test_resume_database.db'):
        os.remove('test_resume_database.db')
        logger.info("🧹 Test database cleaned up")

def main():
    """Run all tests"""
    logger.info("🚀 Starting FieldNation Work Order System Tests")
    logger.info("=" * 50)
    
    test_results = {}
    
    # Run tests
    test_results['database_setup'] = test_database_setup()
    test_results['markdown_processing'] = test_markdown_processing()
    test_results['pdf_processing'] = test_pdf_processing()
    test_results['database_storage'] = test_database_storage()
    test_results['full_processing'] = test_full_processing()
    test_results['data_extraction'] = test_data_extraction()
    test_results['job_matching'] = test_job_matching()
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = 0
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
        total += 1
    
    logger.info("=" * 50)
    logger.info(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready for production use.")
    else:
        logger.warning("⚠️ Some tests failed. Please review and fix issues before using.")
    
    # Optional: Keep test database for inspection
    keep_db = input("\nKeep test database for inspection? (y/N): ").lower().strip() == 'y'
    if not keep_db:
        cleanup_test_database()

if __name__ == "__main__":
    main() 