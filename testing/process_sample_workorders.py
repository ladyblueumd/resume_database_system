#!/usr/bin/env python3
"""
Process Sample Work Orders
Test script to process a sample of markdown and PDF work orders
"""

from comprehensive_fieldnation_processor import ComprehensiveFieldNationProcessor
import os

def main():
    print("🚀 Processing Sample Work Orders")
    print("=" * 50)
    
    # Initialize processor with main database
    processor = ComprehensiveFieldNationProcessor('resume_database.db')
    
    # Process first 10 markdown files
    markdown_dir = 'downloaded work orders'
    if os.path.exists(markdown_dir):
        markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')][:10]
        print(f"📄 Processing {len(markdown_files)} markdown files...")
        
        success_count = 0
        for i, filename in enumerate(markdown_files):
            file_path = os.path.join(markdown_dir, filename)
            work_order = processor.process_markdown_file(file_path)
            if work_order and processor.save_work_order(work_order):
                success_count += 1
                title = work_order.title[:50] + "..." if len(work_order.title) > 50 else work_order.title
                print(f"  {i+1}. ✅ WO#{work_order.fn_work_order_id}: {title} - {work_order.buyer_company}")
            else:
                print(f"  {i+1}. ❌ Failed to process {filename}")
        
        print(f"📄 Markdown: Successfully processed {success_count}/{len(markdown_files)} work orders")
    
    # Process first 3 PDF files
    pdf_dir = 'fieldnation_pdfs'
    if os.path.exists(pdf_dir):
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')][:3]
        print(f"\n📋 Processing {len(pdf_files)} PDF files...")
        
        success_count = 0
        for i, filename in enumerate(pdf_files):
            file_path = os.path.join(pdf_dir, filename)
            work_order = processor.process_pdf_file(file_path)
            if work_order and processor.save_work_order(work_order):
                success_count += 1
                title = work_order.title[:50] + "..." if len(work_order.title) > 50 else work_order.title
                print(f"  {i+1}. ✅ WO#{work_order.fn_work_order_id}: {title} - {work_order.buyer_company}")
            else:
                print(f"  {i+1}. ❌ Failed to process {filename}")
        
        print(f"📋 PDF: Successfully processed {success_count}/{len(pdf_files)} work orders")
    
    # Check database contents
    print(f"\n📊 Database Summary:")
    conn = processor.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM fieldnation_work_orders")
    total_count = cursor.fetchone()[0]
    print(f"  Total work orders in database: {total_count}")
    
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN title IS NOT NULL AND title != '' THEN 1 END) as with_title,
            COUNT(CASE WHEN buyer_company IS NOT NULL AND buyer_company != '' THEN 1 END) as with_company,
            COUNT(CASE WHEN pay_amount IS NOT NULL AND pay_amount > 0 THEN 1 END) as with_pay,
            COUNT(CASE WHEN work_description IS NOT NULL AND work_description != '' THEN 1 END) as with_description
        FROM fieldnation_work_orders
    """)
    
    stats = cursor.fetchone()
    if total_count > 0:
        print(f"  - With titles: {stats[0]} ({stats[0]/total_count*100:.1f}%)")
        print(f"  - With company: {stats[1]} ({stats[1]/total_count*100:.1f}%)")
        print(f"  - With pay amount: {stats[2]} ({stats[2]/total_count*100:.1f}%)")
        print(f"  - With description: {stats[3]} ({stats[3]/total_count*100:.1f}%)")
    
    # Show sample work orders
    cursor.execute("""
        SELECT fn_work_order_id, title, buyer_company, pay_amount, work_type, industry_category 
        FROM fieldnation_work_orders 
        LIMIT 5
    """)
    
    print(f"\n📋 Sample Work Orders:")
    for row in cursor.fetchall():
        wo_id, title, company, pay, work_type, industry = row
        title_display = (title[:40] + "...") if title and len(title) > 40 else (title or "No Title")
        print(f"  • WO#{wo_id}: {title_display}")
        print(f"    Company: {company or 'Unknown'} | Pay: ${pay or 0} | Type: {work_type or 'N/A'} | Industry: {industry or 'N/A'}")
    
    conn.close()
    
    print(f"\n✅ Sample processing complete!")
    print(f"🌐 Access the web interface at: http://localhost:8000")
    print(f"📊 Use the 'Import All Work Orders' button to process all {len(os.listdir('downloaded work orders'))} markdown files")

if __name__ == "__main__":
    main() 