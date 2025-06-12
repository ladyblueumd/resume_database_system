#!/usr/bin/env python3
"""
Test script for markdown processor integration
"""

import os
import sys
from claude_markdown_processor import FieldNationMarkdownProcessor

def test_processor():
    """Test the markdown processor functionality"""
    print("Testing Claude Markdown Processor...")
    
    # Initialize processor
    try:
        processor = FieldNationMarkdownProcessor("test_resume_database.db")
        print("✓ Processor initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize processor: {e}")
        return False
    
    # Test with sample file
    test_file = "downloaded work orders/work_order_430895_2025_06_10_21_29_56.md"
    if os.path.exists(test_file):
        print(f"Testing with file: {test_file}")
        
        try:
            # Parse file
            data = processor.parse_markdown_file(test_file)
            print(f"✓ File parsed successfully")
            print(f"  Work Order ID: {data.get('work_order_id')}")
            print(f"  Title: {data.get('title')}")
            print(f"  Company: {data.get('company_name')}")
            print(f"  Total Paid: {data.get('total_paid')}")
            print(f"  Quality Score: {data.get('data_quality_score')}")
            
            # Save to database
            success = processor.save_to_database(data)
            if success:
                print("✓ Data saved to database successfully")
            else:
                print("✗ Failed to save to database")
                return False
                
        except Exception as e:
            print(f"✗ Error processing file: {e}")
            return False
    else:
        print(f"✗ Test file not found: {test_file}")
        return False
    
    return True

def test_directory_processing():
    """Test processing a small batch of files"""
    print("\nTesting directory processing...")
    
    try:
        processor = FieldNationMarkdownProcessor("test_resume_database.db")
        
        # Get list of markdown files
        md_dir = "downloaded work orders/"
        if os.path.exists(md_dir):
            md_files = [f for f in os.listdir(md_dir) if f.endswith('.md')]
            print(f"Found {len(md_files)} markdown files")
            
            if len(md_files) > 0:
                # Process first 5 files as test
                test_files = md_files[:5]
                processed_count = 0
                
                for filename in test_files:
                    filepath = os.path.join(md_dir, filename)
                    try:
                        data = processor.parse_markdown_file(filepath)
                        if processor.save_to_database(data):
                            processed_count += 1
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
                
                print(f"✓ Successfully processed {processed_count}/{len(test_files)} files")
                return True
            else:
                print("No markdown files found to test")
                return False
        else:
            print(f"Directory not found: {md_dir}")
            return False
            
    except Exception as e:
        print(f"✗ Error in directory processing: {e}")
        return False

def check_database():
    """Check the database contents"""
    print("\nChecking database contents...")
    
    try:
        import sqlite3
        conn = sqlite3.connect("test_resume_database.db")
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='work_orders_markdown'
        """)
        
        if cursor.fetchone():
            print("✓ work_orders_markdown table exists")
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM work_orders_markdown")
            count = cursor.fetchone()[0]
            print(f"✓ Database contains {count} work orders")
            
            if count > 0:
                # Show sample data
                cursor.execute("""
                    SELECT work_order_id, title, company_name, total_paid, data_quality_score 
                    FROM work_orders_markdown 
                    LIMIT 3
                """)
                
                print("\nSample records:")
                for row in cursor.fetchall():
                    print(f"  WO: {row[0]} | {row[1]} | {row[2]} | ${row[3]} | Quality: {row[4]}")
            
        else:
            print("✗ work_orders_markdown table not found")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Markdown Processor Integration Test\n")
    
    # Clean up any existing test database
    if os.path.exists("test_resume_database.db"):
        os.remove("test_resume_database.db")
        print("Removed existing test database")
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_processor():
        tests_passed += 1
    
    if test_directory_processing():
        tests_passed += 1
        
    if check_database():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Markdown processor integration is working.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    # Clean up test database
    if os.path.exists("test_resume_database.db"):
        os.remove("test_resume_database.db")
        print("Cleaned up test database") 