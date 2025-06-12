#!/usr/bin/env python3
"""
Refresh Work Orders Database with Location Data
Clears old data and imports fresh FieldNation data with full location information
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
import os
import re
from typing import Dict, List, Optional

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('resume_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def clear_old_data():
    """Clear old work orders and related data"""
    print("🗑️  Clearing old work orders and projects...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear related tables first (foreign key constraints)
    cursor.execute("DELETE FROM work_order_project_assignments")
    cursor.execute("DELETE FROM work_order_projects")
    cursor.execute("DELETE FROM work_orders")
    
    conn.commit()
    conn.close()
    
    print("✅ Old data cleared successfully")

def update_database_schema():
    """Update database schema to include location fields"""
    print("🔧 Updating database schema for location data...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if location columns exist and add them if they don't
    cursor.execute("PRAGMA table_info(work_orders)")
    columns = [col[1] for col in cursor.fetchall()]
    
    location_columns = ['city', 'state', 'zip_code', 'location_address']
    
    for col in location_columns:
        if col not in columns:
            cursor.execute(f"ALTER TABLE work_orders ADD COLUMN {col} TEXT")
            print(f"   ✅ Added column: {col}")
    
    conn.commit()
    conn.close()
    
    print("✅ Database schema updated")

def import_fieldnation_data():
    """Import fresh FieldNation data with location information"""
    print("📥 Importing FieldNation data with locations...")
    
    # Use the comprehensive CSV with location data
    csv_file = "spreadsheets/fn-full-52025.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: {csv_file} not found")
        return
    
    # Read CSV with proper parsing
    df = pd.read_csv(csv_file, low_memory=False)
    
    print(f"📊 Found {len(df)} work orders in CSV")
    print(f"📍 Columns available: {list(df.columns)}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    skipped_count = 0
    
    for index, row in df.iterrows():
        try:
            # Extract and clean data
            fn_work_order_id = str(row.get('Id', '')).strip()
            if not fn_work_order_id or fn_work_order_id == 'nan':
                skipped_count += 1
                continue
            
            # Basic work order data
            title = str(row.get('Title', '')).strip()
            work_type = str(row.get('Type of Work', '')).strip()
            company_name = str(row.get('Company', '')).strip()
            status = str(row.get('Status', '')).strip()
            
            # Location data
            city = str(row.get('City', '')).strip()
            state = str(row.get('State', '')).strip()
            zip_code = str(row.get('Zip', '')).strip()
            location_address = str(row.get('Location', '')).strip()
            
            # Clean up 'nan' values
            if city == 'nan': city = None
            if state == 'nan': state = None
            if zip_code == 'nan': zip_code = None
            if location_address == 'nan': location_address = None
            
            # Parse pay amount
            pay_str = str(row.get('Pay', '0')).strip()
            pay_amount = 0.0
            if pay_str and pay_str != 'nan':
                # Remove currency symbols and commas
                pay_clean = re.sub(r'[$,]', '', pay_str)
                try:
                    pay_amount = float(pay_clean)
                except ValueError:
                    pay_amount = 0.0
            
            # Parse service date
            service_date_str = str(row.get('Service Date', '')).strip()
            service_date = None
            if service_date_str and service_date_str != 'nan':
                try:
                    # Parse date like "05-14-2025 17:00 EDT"
                    date_part = service_date_str.split(' ')[0]
                    service_date = datetime.strptime(date_part, '%m-%d-%Y').date()
                except:
                    service_date = None
            
            # Determine work category based on work type
            work_category = categorize_work_type(work_type)
            
            # Insert work order with location data
            cursor.execute("""
                INSERT INTO work_orders (
                    fn_work_order_id, title, work_type, work_category, 
                    company_name, status, pay_amount, service_date,
                    city, state, zip_code, location_address,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fn_work_order_id, title, work_type, work_category,
                company_name, status, pay_amount, service_date,
                city, state, zip_code, location_address,
                datetime.now()
            ))
            
            imported_count += 1
            
            if imported_count % 100 == 0:
                print(f"   📥 Imported {imported_count} work orders...")
                
        except Exception as e:
            print(f"   ⚠️  Error processing row {index}: {e}")
            skipped_count += 1
            continue
    
    conn.commit()
    conn.close()
    
    print(f"✅ Import completed!")
    print(f"   📊 Total imported: {imported_count}")
    print(f"   ⚠️  Skipped: {skipped_count}")
    
    return imported_count

def categorize_work_type(work_type: str) -> str:
    """Categorize work type into broader categories"""
    if not work_type:
        return "other"
    
    work_type_lower = work_type.lower()
    
    if any(keyword in work_type_lower for keyword in ['desktop', 'windows', 'pc', 'computer', 'laptop']):
        return "desktop"
    elif any(keyword in work_type_lower for keyword in ['printer', 'print']):
        return "printer"
    elif any(keyword in work_type_lower for keyword in ['server', 'storage']):
        return "server"
    elif any(keyword in work_type_lower for keyword in ['network', 'switch', 'router']):
        return "networking"
    elif any(keyword in work_type_lower for keyword in ['pos', 'point of sale', 'register']):
        return "pos"
    elif any(keyword in work_type_lower for keyword in ['phone', 'voip', 'pots']):
        return "telephony"
    elif any(keyword in work_type_lower for keyword in ['kiosk']):
        return "kiosk"
    elif any(keyword in work_type_lower for keyword in ['audio', 'visual', 'av']):
        return "av"
    else:
        return "general"

def print_location_stats():
    """Print statistics about location data"""
    print("\n📍 Location Statistics:")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # States
    cursor.execute("SELECT state, COUNT(*) as count FROM work_orders WHERE state IS NOT NULL GROUP BY state ORDER BY count DESC")
    states = cursor.fetchall()
    print(f"   🗺️  States: {len(states)} unique states")
    for state in states[:10]:  # Top 10
        print(f"      {state['state']}: {state['count']} work orders")
    
    # Cities
    cursor.execute("SELECT city, state, COUNT(*) as count FROM work_orders WHERE city IS NOT NULL GROUP BY city, state ORDER BY count DESC LIMIT 10")
    cities = cursor.fetchall()
    print(f"   🏙️  Top 10 Cities:")
    for city in cities:
        print(f"      {city['city']}, {city['state']}: {city['count']} work orders")
    
    # Location data completeness
    cursor.execute("SELECT COUNT(*) as total FROM work_orders")
    total = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as with_city FROM work_orders WHERE city IS NOT NULL")
    with_city = cursor.fetchone()['with_city']
    
    cursor.execute("SELECT COUNT(*) as with_state FROM work_orders WHERE state IS NOT NULL")
    with_state = cursor.fetchone()['with_state']
    
    cursor.execute("SELECT COUNT(*) as with_zip FROM work_orders WHERE zip_code IS NOT NULL")
    with_zip = cursor.fetchone()['with_zip']
    
    print(f"   📊 Location Data Completeness:")
    print(f"      Total work orders: {total}")
    if total > 0:
        print(f"      With city: {with_city} ({with_city/total*100:.1f}%)")
        print(f"      With state: {with_state} ({with_state/total*100:.1f}%)")
        print(f"      With zip code: {with_zip} ({with_zip/total*100:.1f}%)")
    else:
        print(f"      No work orders found in database")
    
    conn.close()

def main():
    """Main function to refresh work orders with location data"""
    print("🔄 Starting Work Orders Database Refresh with Location Data")
    print("=" * 60)
    
    # Step 1: Clear old data
    clear_old_data()
    
    # Step 2: Update schema
    update_database_schema()
    
    # Step 3: Import new data
    imported_count = import_fieldnation_data()
    
    # Step 4: Show location statistics
    print_location_stats()
    
    print("\n🎉 Database refresh completed successfully!")
    print(f"   📊 Total work orders: {imported_count}")
    print("   📍 Location data included: city, state, zip code, address")

if __name__ == "__main__":
    main() 