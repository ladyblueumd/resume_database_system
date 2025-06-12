#!/usr/bin/env python3
"""
Test single work order import to debug column mismatch
"""

import os
from comprehensive_fieldnation_processor import ComprehensiveFieldNationProcessor

def test_single_import():
    """Test importing a single work order to debug issues"""
    processor = ComprehensiveFieldNationProcessor()
    
    # Get the first markdown file
    markdown_dir = "downloaded work orders"
    files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')]
    
    if not files:
        print("No markdown files found")
        return
    
    first_file = files[0]
    file_path = os.path.join(markdown_dir, first_file)
    
    print(f"Testing import of: {first_file}")
    
    # Process the file
    work_order = processor.process_markdown_file(file_path)
    
    if work_order:
        print(f"Work order extracted: {work_order.fn_work_order_id}")
        print(f"Title: {work_order.title}")
        print(f"Company: {work_order.buyer_company}")
        
        # Try to save it
        success = processor.save_work_order(work_order)
        if success:
            print("✅ Successfully saved work order")
        else:
            print("❌ Failed to save work order")
    else:
        print("❌ Failed to extract work order")

if __name__ == "__main__":
    test_single_import() 