#!/usr/bin/env python3
"""
Refresh Work Orders Database
Clears old data and imports fresh 5/31/2025 FieldNation report
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
    
    # Reset auto-increment counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='work_orders'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='work_order_projects'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='work_order_project_assignments'")
    
    conn.commit()
    
    # Verify clearing
    cursor.execute("SELECT COUNT(*) FROM work_orders")
    work_orders_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM work_order_projects")
    projects_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"✅ Cleared {work_orders_count} work orders and {projects_count} projects")
    return True

def categorize_work_type(work_type: str, buyer: str = "") -> Dict[str, str]:
    """Categorize work order based on type and buyer"""
    work_type_lower = work_type.lower() if work_type else ""
    buyer_lower = buyer.lower() if buyer else ""
    
    # Map work types to categories
    category_map = {
        'networking': 'networking',
        'printer': 'printers', 
        'windows device': 'desktop',
        'point of sale': 'retail',
        'pots': 'telephony',
        'voip-sip': 'telephony',
        'general tasks': 'general',
        'other trades': 'general',
        'low voltage testing': 'networking',
        'low voltage runs': 'networking',
        'kiosk': 'retail',
        'merchandising': 'retail',
        'general alarm': 'security',
        'server/storage': 'server'
    }
    
    category = category_map.get(work_type_lower, 'general')
    
    # Determine client type from buyer
    client_type = 'enterprise'
    if any(word in buyer_lower for word in ['retail', 'restaurant', 'store']):
        client_type = 'retail'
    elif any(word in buyer_lower for word in ['caption', 'medical', 'healthcare']):
        client_type = 'healthcare'
    elif any(word in buyer_lower for word in ['bank', 'financial']):
        client_type = 'financial'
    
    return {
        'work_category': category,
        'client_type': client_type
    }

def extract_technologies_and_skills(work_type: str, buyer: str = "") -> Dict[str, List[str]]:
    """Extract technologies and skills from work type and buyer"""
    work_type_lower = work_type.lower() if work_type else ""
    buyer_lower = buyer.lower() if buyer else ""
    
    # Technology mapping
    technologies = []
    if 'windows' in work_type_lower:
        technologies.extend(['Windows', 'Desktop Support'])
    if 'networking' in work_type_lower:
        technologies.extend(['Network Equipment', 'Cisco', 'LAN/WAN'])
    if 'printer' in work_type_lower:
        technologies.extend(['Printers', 'Print Servers'])
    if 'point of sale' in work_type_lower or 'pos' in work_type_lower:
        technologies.extend(['POS Systems', 'Retail Technology'])
    if 'pots' in work_type_lower or 'voip' in work_type_lower:
        technologies.extend(['VoIP', 'Telephony', 'PBX'])
    if 'server' in work_type_lower:
        technologies.extend(['Server Hardware', 'Storage Systems'])
    
    # Add buyer-specific technologies
    if 'zones' in buyer_lower:
        technologies.append('Zones Equipment')
    if 'unisys' in buyer_lower:
        technologies.append('Unisys Systems')
    
    # Skills mapping
    skills = []
    skill_map = {
        'Hardware Installation': ['windows device', 'server', 'printer'],
        'Network Configuration': ['networking', 'voip'],
        'Troubleshooting': ['device', 'system', 'equipment'],
        'Customer Service': ['onsite', 'field'],
        'Technical Support': ['support', 'maintenance'],
        'System Deployment': ['installation', 'setup']
    }
    
    for skill, keywords in skill_map.items():
        if any(keyword in work_type_lower for keyword in keywords):
            skills.append(skill)
    
    # Always include basic skills
    skills.extend(['Technical Support', 'Customer Service'])
    
    return {
        'technologies_used': list(set(technologies)),  # Remove duplicates
        'skills_demonstrated': list(set(skills))
    }

def parse_pay_amount(pay_str: str) -> Optional[float]:
    """Parse pay amount from string"""
    if not pay_str or pd.isna(pay_str):
        return None
    
    try:
        # Remove currency symbols and convert to float
        pay_clean = re.sub(r'[$,]', '', str(pay_str))
        return float(pay_clean)
    except (ValueError, TypeError):
        return None

def parse_date(date_str: str) -> Optional[str]:
    """Parse service date from string (format: M/D/YYYY)"""
    if not date_str or pd.isna(date_str):
        return None
    
    try:
        # Expected format: "5/28/2025"
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def import_new_fieldnation_csv(file_path: str) -> int:
    """Import the new 5/31 FieldNation CSV"""
    print(f"📊 Importing new FieldNation data from: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return 0
    
    # Read CSV
    df = pd.read_csv(file_path)
    print(f"📋 Found {len(df)} work orders in CSV")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Extract data from the new CSV format
            fn_work_order_id = str(row['Work Order Id']).strip()
            work_type = str(row['Type of Work']).strip()
            paid_date = row['Paid']
            total_pay = parse_pay_amount(row['Total Pay'])
            hours_logged = row.get('Hours Logged', 0)
            buyer = str(row['Buyer']).strip()
            
            # Categorize the work
            categories = categorize_work_type(work_type, buyer)
            tech_skills = extract_technologies_and_skills(work_type, buyer)
            
            # Create a descriptive title
            title = f"{work_type} - {buyer}"
            
            # Parse service date (using Paid date as service date)
            service_date = parse_date(paid_date)
            
            # Determine status - all records in this report are completed/paid
            status = 'Paid'
            
            # Insert work order
            cursor.execute("""
                INSERT INTO work_orders (
                    fn_work_order_id, title, work_type, company_name, service_date,
                    pay_amount, status, work_category, client_type,
                    technologies_used, skills_demonstrated, 
                    estimated_hours, include_in_resume, highlight_project,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fn_work_order_id,
                title,
                work_type,
                buyer,  # Using buyer as company name
                service_date,
                total_pay,
                status,
                categories['work_category'],
                categories['client_type'],
                json.dumps(tech_skills['technologies_used']),
                json.dumps(tech_skills['skills_demonstrated']),
                float(hours_logged) if hours_logged and not pd.isna(hours_logged) else None,
                True,  # Include in resume by default
                total_pay and total_pay > 300,  # Highlight high-value projects
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            imported_count += 1
            
        except Exception as e:
            error_msg = f"Row {idx + 1}: {str(e)}"
            errors.append(error_msg)
            print(f"⚠️  {error_msg}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully imported {imported_count} work orders")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred during import")
    
    return imported_count

def main():
    """Main execution function"""
    print("🔄 Refreshing FieldNation Work Orders Database")
    print("=" * 50)
    
    # Step 1: Clear old data
    if clear_old_data():
        print()
        
        # Step 2: Import new data
        csv_file = "spreadsheets/Work Order Report 2025-05-31.csv"
        imported_count = import_new_fieldnation_csv(csv_file)
        
        if imported_count > 0:
            print()
            print("📈 Generating statistics...")
            
            # Step 3: Show statistics
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM work_orders")
            total_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT company_name) FROM work_orders")
            unique_companies = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(pay_amount) FROM work_orders WHERE pay_amount IS NOT NULL")
            total_earnings = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM work_orders WHERE pay_amount > 300")
            high_value_orders = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"📊 Final Statistics:")
            print(f"   • Total Work Orders: {total_orders}")
            print(f"   • Unique Companies: {unique_companies}")
            print(f"   • Total Earnings: ${total_earnings:,.2f}")
            print(f"   • High-Value Orders (>$300): {high_value_orders}")
            print()
            print("✅ Database refresh complete!")
            print("💡 You can now run the auto-create projects feature to group these work orders.")
        else:
            print("❌ No work orders were imported.")
    else:
        print("❌ Failed to clear old data.")

if __name__ == "__main__":
    main() 