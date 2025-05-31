#!/usr/bin/env python3
"""
Import FieldNation Work Order Data
Processes CSV files and imports work orders into the resume database
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
import os
import glob
import re
from typing import Dict, List, Optional

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('resume_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_work_orders_table():
    """Create the work_orders table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Read and execute the table creation script
    if os.path.exists('create_work_orders_table.sql'):
        with open('create_work_orders_table.sql', 'r') as f:
            sql_script = f.read()
            cursor.executescript(sql_script)
    else:
        # Fallback table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fn_work_order_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                work_type TEXT,
                company_name TEXT NOT NULL,
                service_date DATE,
                location TEXT,
                pay_amount DECIMAL(10,2),
                status TEXT,
                state TEXT,
                city TEXT,
                zip_code TEXT,
                work_category TEXT,
                client_type TEXT,
                technologies_used TEXT,
                skills_demonstrated TEXT,
                complexity_level TEXT,
                work_description TEXT,
                include_in_resume BOOLEAN DEFAULT TRUE,
                highlight_project BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

def categorize_work_type(title: str, work_type: str = None) -> Dict[str, str]:
    """Categorize work order based on title and type"""
    title_lower = title.lower()
    
    # Define category mappings
    categories = {
        'desktop': ['desktop', 'pc', 'workstation', 'laptop', 'computer', 'windows', 'mac', 'imac'],
        'retail': ['pos', 'register', 'kiosk', 'retail', 'pin pad', 'payment', 'cash drawer'],
        'networking': ['network', 'router', 'switch', 'voip', 'phone', 'cable', 'wifi'],
        'printers': ['printer', 'print', 'scanning', 'copier', 'xerox', 'hp printer'],
        'telephony': ['phone', 'voip', 'telecom', 'pbx', 'caption phone'],
        'medical': ['medical', 'healthcare', 'cart', 'capsa', 'hospital'],
        'security': ['security', 'access control', 'camera', 'surveillance'],
        'server': ['server', 'rack', 'data center', 'storage'],
        'general': ['install', 'setup', 'configuration', 'maintenance']
    }
    
    # Determine category
    category = 'general'
    for cat, keywords in categories.items():
        if any(keyword in title_lower for keyword in keywords):
            category = cat
            break
    
    # Determine client type based on company names and work
    client_type = 'enterprise'
    if any(word in title_lower for word in ['retail', 'store', 'mall', 'shop']):
        client_type = 'retail'
    elif any(word in title_lower for word in ['hospital', 'medical', 'healthcare']):
        client_type = 'healthcare'
    elif any(word in title_lower for word in ['bank', 'financial', 'credit']):
        client_type = 'financial'
    
    return {
        'work_category': category,
        'client_type': client_type
    }

def extract_technologies_and_skills(title: str, work_type: str = None) -> Dict[str, List[str]]:
    """Extract technologies and skills from work order title"""
    title_lower = title.lower()
    
    # Technology keywords
    technologies = []
    tech_keywords = {
        'Windows': ['windows', 'win 7', 'win 10', 'windows 7', 'windows 10'],
        'Mac/Apple': ['mac', 'imac', 'apple', 'macbook'],
        'HP': ['hp', 'hewlett packard'],
        'Dell': ['dell'],
        'Xerox': ['xerox', 'fuji xerox'],
        'POS Systems': ['pos', 'point of sale', 'register'],
        'VoIP': ['voip', 'voice over ip'],
        'Network Equipment': ['router', 'switch', 'network'],
        'Printers': ['printer', 'print', 'scanning'],
        'Medical Equipment': ['medical cart', 'healthcare cart'],
        'Security Systems': ['access control', 'security camera']
    }
    
    for tech, keywords in tech_keywords.items():
        if any(keyword in title_lower for keyword in keywords):
            technologies.append(tech)
    
    # Skills demonstrated
    skills = []
    skill_keywords = {
        'Hardware Installation': ['install', 'setup', 'deployment', 'replacement'],
        'Troubleshooting': ['troubleshoot', 'diagnose', 'repair', 'fix'],
        'System Configuration': ['configuration', 'config', 'setup'],
        'Network Support': ['network', 'connectivity', 'cable'],
        'Customer Service': ['onsite', 'client', 'customer'],
        'Project Management': ['project', 'lead', 'coordination'],
        'Technical Support': ['support', 'maintenance', 'service']
    }
    
    for skill, keywords in skill_keywords.items():
        if any(keyword in title_lower for keyword in keywords):
            skills.append(skill)
    
    return {
        'technologies_used': technologies,
        'skills_demonstrated': skills
    }

def parse_pay_amount(pay_str: str) -> Optional[float]:
    """Parse pay amount from string"""
    if not pay_str or pd.isna(pay_str):
        return None
    
    # Remove currency symbols and commas
    pay_clean = re.sub(r'[$,]', '', str(pay_str))
    
    try:
        return float(pay_clean)
    except ValueError:
        return None

def parse_date(date_str: str) -> Optional[str]:
    """Parse service date from string"""
    if not date_str or pd.isna(date_str):
        return None
    
    try:
        # Try different date formats
        for fmt in ['%m-%d-%Y %H:%M %Z', '%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
            try:
                dt = datetime.strptime(date_str.split()[0], fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If no format works, try pandas
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def import_csv_file(file_path: str, work_category: str = None) -> int:
    """Import a single CSV file"""
    print(f"Processing: {file_path}")
    
    try:
        # Try different column name variations
        df = pd.read_csv(file_path)
        
        # Standardize column names
        column_mapping = {
            'Id': 'fn_work_order_id',
            'ID': 'fn_work_order_id',
            'Title': 'title',
            'Company': 'company_name',
            'Service Date': 'service_date',
            'Type of Work': 'work_type',
            'Location': 'location',
            'Pay': 'pay_amount',
            'Status': 'status',
            'State': 'state',
            'City': 'city',
            'Zip': 'zip_code'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Ensure required columns exist
        required_columns = ['fn_work_order_id', 'title', 'company_name']
        for col in required_columns:
            if col not in df.columns:
                if col == 'fn_work_order_id' and 'Id' in df.columns:
                    df['fn_work_order_id'] = df['Id']
                elif col == 'title' and 'Title' in df.columns:
                    df['title'] = df['Title']
                elif col == 'company_name' and 'Company' in df.columns:
                    df['company_name'] = df['Company']
                else:
                    print(f"Missing required column: {col}")
                    return 0
        
        # Auto-detect work category from filename if not provided
        if not work_category:
            filename = os.path.basename(file_path).lower()
            if 'desktop' in filename:
                work_category = 'desktop'
            elif 'retail' in filename:
                work_category = 'retail'
            elif 'network' in filename:
                work_category = 'networking'
            elif 'printer' in filename:
                work_category = 'printers'
            elif 'telephony' in filename:
                work_category = 'telephony'
            elif 'medical' in filename:
                work_category = 'medical'
            else:
                work_category = 'general'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                fn_id = str(row['fn_work_order_id'])
                title = str(row['title'])
                company = str(row['company_name'])
                
                # Check if work order already exists
                cursor.execute("SELECT id FROM work_orders WHERE fn_work_order_id = ?", (fn_id,))
                if cursor.fetchone():
                    skipped_count += 1
                    continue
                
                # Parse optional fields
                service_date = parse_date(row.get('service_date', ''))
                pay_amount = parse_pay_amount(row.get('pay_amount', ''))
                
                # Categorize work
                categories = categorize_work_type(title, row.get('work_type', ''))
                tech_skills = extract_technologies_and_skills(title, row.get('work_type', ''))
                
                # Insert work order
                cursor.execute("""
                    INSERT INTO work_orders (
                        fn_work_order_id, title, work_type, company_name,
                        service_date, location, pay_amount, status,
                        state, city, zip_code, work_category, client_type,
                        technologies_used, skills_demonstrated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fn_id, title, row.get('work_type', ''), company,
                    service_date, row.get('location', ''), pay_amount,
                    row.get('status', 'Paid'), row.get('state', ''),
                    row.get('city', ''), row.get('zip_code', ''),
                    categories['work_category'], categories['client_type'],
                    json.dumps(tech_skills['technologies_used']),
                    json.dumps(tech_skills['skills_demonstrated'])
                ))
                
                imported_count += 1
                
            except Exception as e:
                print(f"Error processing row {fn_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"  Imported: {imported_count}, Skipped: {skipped_count}")
        return imported_count
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return 0

def import_all_csv_files(spreadsheets_dir: str = "spreadsheets") -> Dict[str, int]:
    """Import all CSV files from the spreadsheets directory"""
    print("🔄 Starting FieldNation Work Order Import")
    print("=" * 60)
    
    # Create table first
    create_work_orders_table()
    
    results = {}
    total_imported = 0
    
    # Get all CSV files
    csv_files = glob.glob(os.path.join(spreadsheets_dir, "*.csv"))
    
    # Sort files - process full reports last
    csv_files.sort(key=lambda x: ('fn-full' in x, 'field-nation-report' in x, x))
    
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        imported = import_csv_file(csv_file)
        results[filename] = imported
        total_imported += imported
    
    print("=" * 60)
    print(f"📊 Import Summary:")
    for filename, count in results.items():
        if count > 0:
            print(f"   {filename}: {count} work orders")
    
    print(f"   Total imported: {total_imported} work orders")
    
    # Show summary statistics
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM work_orders")
    total_wo = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT company_name) FROM work_orders")
    unique_companies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT work_category) FROM work_orders")
    unique_categories = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(pay_amount) FROM work_orders WHERE pay_amount IS NOT NULL")
    total_earnings = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"   Total work orders in DB: {total_wo}")
    print(f"   Unique companies: {unique_companies}")
    print(f"   Work categories: {unique_categories}")
    print(f"   Total earnings: ${total_earnings:,.2f}")
    
    return results

def generate_work_order_statistics():
    """Generate and display work order statistics"""
    conn = get_db_connection()
    
    print("\n📈 Work Order Statistics")
    print("=" * 40)
    
    # By category
    df_cat = pd.read_sql_query("""
        SELECT work_category, COUNT(*) as count, 
               COALESCE(SUM(pay_amount), 0) as total_pay,
               COALESCE(AVG(pay_amount), 0) as avg_pay
        FROM work_orders 
        GROUP BY work_category 
        ORDER BY count DESC
    """, conn)
    
    print("By Work Category:")
    for _, row in df_cat.iterrows():
        print(f"  {row['work_category']}: {row['count']} orders, ${row['total_pay']:,.2f} total, ${row['avg_pay']:.2f} avg")
    
    # By company (top 10)
    df_company = pd.read_sql_query("""
        SELECT company_name, COUNT(*) as count,
               COALESCE(SUM(pay_amount), 0) as total_pay
        FROM work_orders 
        GROUP BY company_name 
        ORDER BY count DESC
        LIMIT 10
    """, conn)
    
    print("\nTop 10 Companies:")
    for _, row in df_company.iterrows():
        print(f"  {row['company_name']}: {row['count']} orders, ${row['total_pay']:,.2f}")
    
    conn.close()

if __name__ == "__main__":
    import_all_csv_files()
    generate_work_order_statistics() 