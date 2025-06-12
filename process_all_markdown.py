#!/usr/bin/env python
"""
Process all FieldNation markdown files
Based on Claude Database SOP Step 2
"""

import os
import sys
import time
from claude_markdown_processor import FieldNationMarkdownProcessor

def main():
    """Process all markdown files in the downloaded work orders directory"""
    print("🚀 Starting Full Markdown Processing")
    print("=" * 60)
    
    # Configuration
    markdown_dir = "downloaded work orders/"
    db_path = "resume_database.db"
    
    # Initialize processor
    print(f"📊 Database: {db_path}")
    print(f"📁 Directory: {markdown_dir}")
    
    try:
        processor = FieldNationMarkdownProcessor(db_path)
        print("✅ Processor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        return 1
    
    # Start processing
    start_time = time.time()
    print(f"\n🔄 Processing markdown files...")
    
    try:
        results = processor.process_directory(markdown_dir)
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        total_files = results.get('total_files', 0)
        processed = results.get('processed', 0)
        errors = results.get('errors', 0)
        skipped = results.get('skipped', 0)
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 PROCESSING COMPLETE")
        print("=" * 60)
        print(f"✅ Successfully processed: {processed} files")
        print(f"❌ Errors encountered: {errors} files")
        print(f"⏭️  Skipped (duplicates): {skipped} files")
        print(f"📁 Total files found: {total_files}")
        print(f"⏱️  Time elapsed: {elapsed_time:.2f} seconds")
        print(f"⚡ Processing speed: {processed/elapsed_time:.2f} files/second")
        
        # Quality check
        if processed > 0:
            print(f"\n📈 Success rate: {(processed/total_files)*100:.1f}%")
            
            # Show sample of processed data
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT company_name) as companies,
                       AVG(total_paid) as avg_pay,
                       SUM(total_paid) as total_earnings,
                       AVG(data_quality_score) as avg_quality
                FROM work_orders_markdown
            """)
            
            stats = cursor.fetchone()
            
            print("\n📊 DATABASE STATISTICS:")
            print(f"   Total work orders: {stats[0]:,}")
            print(f"   Unique companies: {stats[1]:,}")
            print(f"   Average payment: ${stats[2]:.2f}" if stats[2] else "   Average payment: N/A")
            print(f"   Total earnings: ${stats[3]:,.2f}" if stats[3] else "   Total earnings: N/A")
            print(f"   Average quality score: {stats[4]:.3f}" if stats[4] else "   Average quality score: N/A")
            
            # Show top companies
            cursor.execute("""
                SELECT company_name, COUNT(*) as count, SUM(total_paid) as total
                FROM work_orders_markdown
                WHERE company_name IS NOT NULL
                GROUP BY company_name
                ORDER BY count DESC
                LIMIT 5
            """)
            
            print("\n🏢 TOP COMPANIES BY WORK ORDERS:")
            for row in cursor.fetchall():
                print(f"   {row[0]}: {row[1]} orders (${row[2]:,.2f})" if row[2] else f"   {row[0]}: {row[1]} orders")
            
            conn.close()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 