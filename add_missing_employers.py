#!/usr/bin/env python3
"""
Extract employment data from the Honolulu resume and add missing employers to database
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

# Employment data extracted from the 2014 Honolulu resume
employment_records = [
    {
        'company_name': 'Bartizan Connects LLC',
        'position_title': 'Nationwide Technical Support Representative',
        'start_date': '2012-08-01',
        'end_date': '2014-09-01',
        'location': 'Yonkers, NY',
        'employment_type': 'full-time',
        'industry': 'Event Technology Services',
        'responsibilities': [
            'Direct support to show organizers and exhibitors',
            'Supervise arrival and distribution of lead retrieval hardware',
            'Installation and activation of iLeads software',
            'Provide training to exhibitors',
            'Export local databases and transmit data to Director of Event Services',
            'Hardware support to all devices',
            'Badge printing for on-site registration',
            'Sales to exhibitors for lead retrieval devices and software',
            'Coordinate equipment return and shipments'
        ],
        'achievements': [
            'Supported major conventions including AAMOS, VIVA, IFEBP, USCAP',
            'Managed technical support for multiple high-profile events',
            'Successfully handled lead retrieval systems for large trade shows'
        ],
        'technologies_used': [
            'Motorola handheld devices',
            'iPad',
            'iPod',
            'iLeads software',
            'Desktop scanning devices',
            'Badge printing systems'
        ]
    },
    {
        'company_name': 'Doggie Style Pets',
        'position_title': 'POS/Desktop and Network Support Technician',
        'start_date': '2014-01-01',
        'end_date': '2014-08-01',
        'location': 'Philadelphia, PA',
        'employment_type': 'contract',
        'industry': 'Retail/Pet Services',
        'responsibilities': [
            'Direct support to owners, main office and retail locations',
            'Windows and Mac environment support (90/10 split)',
            'On call support for retail and office IT issues',
            'POS systems installations, backup and recovery',
            'Grooming software administration',
            'VPN software installation between office and retail locations',
            'Security camera system installation and support',
            'Quickbooks POS configuration',
            'Virus removals and anti-virus administration',
            'Router configuration and network administration'
        ],
        'achievements': [
            'Reset and reconfigured Nortel PBX system',
            'Successfully installed VPN between office server and six retail locations',
            'Implemented backup solutions for grooming client data'
        ],
        'technologies_used': [
            'Windows',
            'Mac OS',
            'Nortel PBX',
            'POS systems',
            'VPN software',
            'Security cameras',
            'Quickbooks POS',
            'Anti-virus software',
            'Network routers'
        ]
    },
    {
        'company_name': 'The Peak Organization Inc',
        'position_title': 'Deployment Technician',
        'start_date': '2012-09-01',
        'end_date': '2014-07-01',
        'location': 'New York, NY',
        'employment_type': 'contract',
        'industry': 'IT Services/Financial',
        'responsibilities': [
            'Windows 7 deployment & migration for Wells Fargo, UBS and Kraft Foods',
            'Direct interaction with company executives and hourly employees',
            'Day two desktop support',
            'Deployment of Windows 7 OS on Dell desktops and laptops',
            'Swap CPUs, monitors and peripherals',
            'Re-map network printers and shared drive access',
            'Migration of customer data',
            'Hardware/Software Support for JPMorgan Chase',
            'Image installs for retail Chase locations',
            'Office deployment of Win 7 machines for Citigroup'
        ],
        'achievements': [
            'Successfully deployed Windows 7 for major financial institutions',
            'Handled department relocations between retail locations',
            'Completed validation of machines after install'
        ],
        'technologies_used': [
            'Windows 7',
            'Dell desktops and laptops',
            'Network printers',
            'PXE imaging',
            'Financial software',
            'Data migration tools'
        ]
    },
    {
        'company_name': 'SmartSource Inc',
        'position_title': 'Assistant Lead Technician',
        'start_date': '2013-11-01',
        'end_date': '2013-11-30',
        'location': 'Horsham, PA',
        'employment_type': 'contract',
        'industry': 'IT Services/Insurance',
        'responsibilities': [
            'Windows XP to Windows 7 Deployment for Allstate Insurance',
            'Setup of HP Desktops and Laptops',
            'USMT migration tool used for data transfer',
            'DiskWipe of outgoing Hardware',
            'Day two Desktop Support'
        ],
        'achievements': [
            'Successfully completed Windows XP to 7 migration for Allstate',
            'Managed secure data wiping procedures'
        ],
        'technologies_used': [
            'Windows XP',
            'Windows 7',
            'HP Desktops and Laptops',
            'USMT migration tool',
            'DiskWipe software'
        ]
    },
    {
        'company_name': 'Essential Enterprise Solutions',
        'position_title': 'Software Support Consultant/Desktop Support',
        'start_date': '2012-09-01',
        'end_date': '2013-08-01',
        'location': 'New Brunswick, NJ and New York, NY',
        'employment_type': 'contract',
        'industry': 'Healthcare/Financial',
        'responsibilities': [
            'Software upgrade project for large women and children\'s hospital',
            'Upgrade of 170 "Computers on Wheels" for nursing staff',
            'AVR flash of four circuit boards per unit',
            'Flashing of accompanying bay chargers',
            'Hewlett Packard technician for Morgan Stanley',
            'Desktop support to executives and hourly employees',
            'Motherboard replacements, HDD replacements/re-imaging',
            'Software support, network troubleshooting'
        ],
        'achievements': [
            'Completed upgrade of 170 medical computers for hospital',
            'Provided support to locations with average of 300 employees',
            'Successfully managed parts return logistics'
        ],
        'technologies_used': [
            'Computers on Wheels',
            'AVR flash programming',
            'Bay chargers',
            'Motherboard replacement',
            'HDD imaging',
            'Network troubleshooting tools'
        ]
    },
    {
        'company_name': 'Sullivan & Cogliano',
        'position_title': 'Install Coordinator/Software Support Technician',
        'start_date': '2013-06-01',
        'end_date': '2013-07-01',
        'location': 'Voorhees, NJ',
        'employment_type': 'contract',
        'industry': 'Utilities/Water Management',
        'responsibilities': [
            'Point of contact for team of 6 technicians over 5 state upgrade',
            'Field truck Toughbooks upgrade for American Water',
            'Point of escalation between technicians and system admins',
            'Monitor site arrival and departure times using GPS tracking',
            'Utilize Spiceworks help desk ticketing system',
            'Create accounts in Apptivo project management system',
            'Co-leader of teleconference between project manager and technicians',
            'Weekend and late night on call technician',
            'Work with system administrator for VBS scripts and SCCM'
        ],
        'achievements': [
            'Successfully managed 700 end user Toughbook upgrades',
            'Coordinated technicians across 5 states',
            'Implemented project tracking and management systems'
        ],
        'technologies_used': [
            'Toughbooks',
            'Windows XP',
            'Windows 7',
            'GPS tracking system',
            'Spiceworks ticketing',
            'Apptivo project management',
            'LogMeIn remote access',
            'VBS scripts',
            'SCCM'
        ]
    },
    {
        'company_name': 'SupportSpace.com',
        'position_title': 'Remote Support Technician',
        'start_date': '2010-03-01',
        'end_date': '2013-01-01',
        'location': 'San Francisco, CA (Remote)',
        'employment_type': 'contract',
        'industry': 'Remote Technical Support',
        'responsibilities': [
            'Remote technical support for Geek Squad customers',
            'Home networking setup and troubleshooting',
            'Virus removal and security software installation',
            'Software installation and troubleshooting',
            'Email support configuration',
            'Mac and tablet support',
            'Operating system repair',
            'PC tune-up services',
            'TrendMicro premium installation',
            'Virus and spyware removal service'
        ],
        'achievements': [
            'Provided remote support for major retail technology services',
            'Maintained high customer satisfaction ratings',
            'Achieved SupportSpace University certifications'
        ],
        'technologies_used': [
            'Remote support tools',
            'Windows XP/Vista/7',
            'Mac OSX',
            'iOS',
            'Android',
            'Email clients',
            'Antivirus software',
            'TrendMicro',
            'System optimization tools'
        ]
    },
    {
        'company_name': 'Global Resources Ltd',
        'position_title': 'Desktop Support Technician',
        'start_date': '2009-05-01',
        'end_date': '2011-01-01',
        'location': 'New York, NY and Long Island, NY',
        'employment_type': 'full-time',
        'industry': 'Financial Services',
        'responsibilities': [
            'Deployment & migration technician for JP Morgan Chase/Washington Mutual',
            'Deployment of desktops and laptops for Bank Acquisition',
            'Upgrade CPUs, monitors and peripherals',
            'Backup and restoration of end user data',
            'Installation of bank peripherals at retail locations'
        ],
        'achievements': [
            'Successfully supported major bank acquisition technology transition',
            'Managed deployment across multiple retail banking locations'
        ],
        'technologies_used': [
            'Windows desktops and laptops',
            'Data backup systems',
            'Bank-specific peripherals',
            'Data migration tools'
        ]
    }
]

def main():
    print("🏢 Adding Missing Employers from Honolulu Resume (2014)")
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
                print(f"✅ Added: {company} - {position} (ID: {emp_id})")
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
    conn.close()
    
    print(f"   Total employers in database: {total_employers}")

if __name__ == "__main__":
    main() 