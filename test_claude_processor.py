#!/usr/bin/env python3
"""Test script for Claude markdown processor"""

from claude_markdown_processor import FieldNationMarkdownProcessor
import os

def test_single_file():
    """Test processing a single file"""
    processor = FieldNationMarkdownProcessor()
    
    # Test with a single file
    test_file = 'downloaded work orders/work_order_430895_2025_06_10_21_29_56.md'
    if os.path.exists(test_file):
        print(f"Testing file: {test_file}")
        data = processor.parse_markdown_file(test_file)
        
        print('\nExtracted data:')
        print(f'Work Order ID: {data.get("work_order_id")}')
        print(f'Title: {data.get("title")}')
        print(f'Company: {data.get("company_name")}')
        print(f'Total Paid: {data.get("total_paid")}')
        print(f'Location: {data.get("location_address")}')
        print(f'City: {data.get("location_city")}')
        print(f'State: {data.get("location_state")}')
        print(f'Work Type: {data.get("work_type")}')
        print(f'Service Type: {data.get("service_type")}')
        print(f'Equipment: {data.get("equipment_type")}')
        print(f'Quality Score: {data.get("data_quality_score")}')
        print(f'Tasks: {data.get("tasks_completed")}')
        
        # Try to save
        success = processor.save_to_database(data)
        print(f'\nSave successful: {success}')
        
        if success:
            # Verify it was saved
            import sqlite3
            conn = sqlite3.connect("resume_database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT work_order_id, title, company_name FROM work_orders_markdown WHERE work_order_id = ?", (data.get("work_order_id"),))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"Verified in database: {result}")
            else:
                print("Not found in database!")
        
    else:
        print(f'Test file not found: {test_file}')

if __name__ == "__main__":
    test_single_file() 