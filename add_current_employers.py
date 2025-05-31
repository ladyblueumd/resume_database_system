#!/usr/bin/env python3
"""
Add current/recent employment data from pasted text to database
"""

import sqlite3
import json
from datetime import datetime
import sys

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('resume_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def employer_exists(company_name, position_title, start_date):
    """Check if an employer record already exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM employment_history 
        WHERE company_name = ? AND position_title = ? AND start_date = ?
    """, (company_name, position_title, start_date))
    
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_employment_record(employment_data):
    """Add employment record to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO employment_history 
        (company_name, position_title, start_date, end_date, location, 
         employment_type, industry, responsibilities, achievements, 
         technologies_used, skills_gained, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        employment_data['company_name'],
        employment_data['position_title'],
        employment_data.get('start_date'),
        employment_data.get('end_date'),
        employment_data.get('location', ''),
        employment_data.get('employment_type', 'full-time'),
        employment_data.get('industry', ''),
        json.dumps(employment_data.get('responsibilities', [])),
        json.dumps(employment_data.get('achievements', [])),
        json.dumps(employment_data.get('technologies_used', [])),
        json.dumps(employment_data.get('skills_gained', [])),
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))
    
    employment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return employment_id

# Current/Recent Employment data from pasted text
employment_records = [
    {
        'company_name': 'NERDAPP.COM',
        'position_title': 'Remote Desktop Support',
        'start_date': '2022-12-01',
        'end_date': None,  # Present
        'location': 'Remote',
        'employment_type': 'contract',
        'industry': 'IT Support Services',
        'responsibilities': [
            'B2C, B2B, enterprise and remote technical support',
            'Comprehensive remote desktop support services',
            'Technical troubleshooting and problem resolution',
            'Customer service and technical consultation'
        ],
        'achievements': [
            'Providing ongoing remote support since December 2022',
            'Successfully handling B2C, B2B, and enterprise clients'
        ],
        'technologies_used': [
            'Remote desktop tools',
            'Windows systems',
            'Mac systems',
            'Technical support software',
            'Enterprise support platforms'
        ]
    },
    {
        'company_name': 'Sadie The Tech Lady/ThorntonTech Inc',
        'position_title': 'Desktop Support Specialist/IT Project Manager Lead Technician',
        'start_date': '2012-03-01',
        'end_date': None,  # Present
        'location': 'NY, NJ, PA, CA, HI, WA, VT',
        'employment_type': 'freelance',
        'industry': 'IT Services/Consulting',
        'responsibilities': [
            'Advanced technical support, hardware/software troubleshooting',
            'Project management, testing deployments, asset inventory',
            'Documentation and technical consultation',
            'Multi-state IT support operations',
            'Lead technician responsibilities for various projects'
        ],
        'achievements': [
            'Operating successful IT consulting business since 2012',
            'Serving clients across multiple states',
            'Leading technical projects and deployments',
            'Building comprehensive technical documentation'
        ],
        'technologies_used': [
            'Windows systems',
            'Mac systems',
            'Project management tools',
            'Asset inventory systems',
            'Documentation platforms',
            'Deployment tools'
        ]
    },
    {
        'company_name': 'Enterprise Integration (Covanta Energy)',
        'position_title': 'Field Services Technician',
        'start_date': '2017-05-01',
        'end_date': '2018-01-01',
        'location': 'Morristown, NJ',
        'employment_type': 'contract',
        'industry': 'Energy/Environmental',
        'responsibilities': [
            'Asset management, C-level executive support',
            'Data center duties, reduced provisioning queue from 50+ days to 6 days',
            'Field services technical support',
            'Executive-level technical consultation'
        ],
        'achievements': [
            'Dramatically reduced provisioning queue from 50+ days to 6 days',
            'Provided high-level support to C-level executives',
            'Successfully managed data center operations'
        ],
        'technologies_used': [
            'Asset management systems',
            'Data center infrastructure',
            'Provisioning systems',
            'Executive support tools'
        ]
    },
    {
        'company_name': 'FieldNation.com',
        'position_title': 'IT Contractor/Field Services Tech',
        'start_date': '2011-10-01',
        'end_date': None,  # Present (ongoing contract work)
        'location': 'Nationwide (NY, NJ, PA, CA, HI, WA)',
        'employment_type': 'contract',
        'industry': 'IT Field Services',
        'responsibilities': [
            'Perform desktop support for numerous clients including major banks, retailers, and insurance companies',
            'On-site technical support and troubleshooting',
            'Multi-client field services coordination',
            'Nationwide deployment and support projects'
        ],
        'achievements': [
            'Maintaining active contractor status since 2011',
            'Successfully supporting major enterprise clients',
            'Providing reliable field services across multiple states'
        ],
        'technologies_used': [
            'Desktop support tools',
            'Banking systems',
            'Retail POS systems',
            'Insurance software',
            'Field service management platforms'
        ]
    },
    {
        'company_name': 'SmartSource Inc.',
        'position_title': 'Assistant Lead Technician/Desktop Support Technician',
        'start_date': '2013-11-01',
        'end_date': '2022-01-01',
        'location': 'Horsham, PA/New York',
        'employment_type': 'contract',
        'industry': 'IT Services/Financial',
        'responsibilities': [
            'Windows hardware setup, software setup',
            'Morgan Chase deployments',
            'Desktop support and technical troubleshooting',
            'Lead technician duties for deployment projects'
        ],
        'achievements': [
            'Long-term engagement spanning over 8 years',
            'Successfully completed Morgan Chase deployment projects',
            'Advanced from Assistant to Lead Technician responsibilities'
        ],
        'technologies_used': [
            'Windows hardware and software',
            'Morgan Chase systems',
            'Deployment tools',
            'Desktop support software'
        ]
    },
    {
        'company_name': 'Fusion Marketing',
        'position_title': 'Technical Support Brand Ambassador',
        'start_date': '2016-12-01',
        'end_date': '2017-04-01',
        'location': 'Madison Square Garden, NYC',
        'employment_type': 'contract',
        'industry': 'Event Technology/Marketing',
        'responsibilities': [
            'VR gaming setup and support for Bud Light MSG',
            'Technical brand ambassador duties',
            'Event technology support and troubleshooting',
            'Customer engagement and technical assistance'
        ],
        'achievements': [
            'Successfully supported VR gaming events at Madison Square Garden',
            'Provided technical expertise for major brand activations',
            'Maintained high customer satisfaction during events'
        ],
        'technologies_used': [
            'VR gaming systems',
            'Event technology platforms',
            'Gaming hardware and software',
            'Customer support tools'
        ]
    }
]

def main():
    print("🏢 Adding Current/Recent Employment Records")
    print("=" * 60)
    
    added_count = 0
    skipped_count = 0
    
    for emp_data in employment_records:
        company = emp_data['company_name']
        position = emp_data['position_title']
        start_date = emp_data['start_date']
        
        if employer_exists(company, position, start_date):
            print(f"⏭️  Skipping: {company} - {position} (already exists)")
            skipped_count += 1
        else:
            try:
                emp_id = add_employment_record(emp_data)
                end_status = "Present" if emp_data.get('end_date') is None else emp_data['end_date']
                print(f"✅ Added: {company} - {position} ({emp_data['start_date']} - {end_status}) (ID: {emp_id})")
                added_count += 1
            except Exception as e:
                print(f"❌ Error adding {company}: {e}")
    
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   Added: {added_count} new employers")
    print(f"   Skipped: {skipped_count} existing employers")
    print(f"   Total processed: {len(employment_records)} employers")
    
    # Show updated stats
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM employment_history")
    total_employers = cursor.fetchone()[0]
    
    # Show current employers (no end date)
    cursor.execute("SELECT COUNT(*) FROM employment_history WHERE end_date IS NULL")
    current_employers = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"   Total employers in database: {total_employers}")
    print(f"   Current active employers: {current_employers}")

if __name__ == "__main__":
    main() 