#!/usr/bin/env python3
"""
Quick Start Script for Resume Database System
Helps initialize the system and provides common operations
"""

import sqlite3
import json
import os
from pathlib import Path

def get_database_stats():
    """Get current database statistics"""
    db_path = "resume_database.db"
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get component counts by section
    cursor.execute("""
        SELECT st.name, COUNT(*) as count
        FROM resume_components rc
        JOIN section_types st ON rc.section_type_id = st.id
        GROUP BY st.name
        ORDER BY count DESC
    """)
    
    section_counts = dict(cursor.fetchall())
    
    # Total components
    cursor.execute("SELECT COUNT(*) FROM resume_components")
    total_components = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_components': total_components,
        'sections': section_counts
    }

def search_components(query, section_type=None):
    """Search components by keyword"""
    db_path = "resume_database.db"
    if not os.path.exists(db_path):
        print("Database not found. Run resume_extractor.py first.")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if section_type:
        cursor.execute("""
            SELECT rc.title, rc.content, st.name as section_type, rc.keywords
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            WHERE (rc.title LIKE ? OR rc.content LIKE ? OR rc.keywords LIKE ?)
            AND st.name = ?
            ORDER BY rc.usage_count DESC
            LIMIT 10
        """, (f'%{query}%', f'%{query}%', f'%{query}%', section_type))
    else:
        cursor.execute("""
            SELECT rc.title, rc.content, st.name as section_type, rc.keywords
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
            WHERE rc.title LIKE ? OR rc.content LIKE ? OR rc.keywords LIKE ?
            ORDER BY rc.usage_count DESC
            LIMIT 10
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def add_sample_job_description():
    """Add a sample job description for testing"""
    sample_job = {
        'company': 'TechCorp Solutions',
        'title': 'Senior Desktop Support Specialist',
        'description': '''
        We are seeking an experienced Desktop Support Specialist to join our IT team. 
        
        Responsibilities:
        - Provide Level 2 desktop support for 200+ users
        - Manage Windows 10/11 deployments and migrations
        - Support Active Directory and Office365 environments
        - Troubleshoot hardware and software issues
        - Use ServiceNow for ticket management
        - Support VPN and network connectivity issues
        - Assist with SCCM imaging and deployments
        
        Requirements:
        - 5+ years desktop support experience
        - Strong Windows administration skills
        - Experience with Active Directory, Group Policy
        - ServiceNow experience preferred
        - ITIL Foundation certification a plus
        - Excellent communication skills
        '''
    }
    
    print(f"Sample Job: {sample_job['company']} - {sample_job['title']}")
    print("=" * 50)
    print(sample_job['description'])
    
    return sample_job

def analyze_job_keywords(job_description):
    """Simple keyword extraction from job description"""
    tech_keywords = [
        'windows', 'active directory', 'servicenow', 'office365', 'sccm',
        'desktop support', 'troubleshooting', 'deployment', 'migration',
        'hardware', 'software', 'network', 'vpn', 'itil', 'group policy',
        'level 2', 'tickets', 'imaging', 'azure', 'exchange', 'outlook'
    ]
    
    found_keywords = []
    text_lower = job_description.lower()
    
    for keyword in tech_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    return found_keywords

def main():
    print("🤖 Resume Database System - Quick Start")
    print("=" * 50)
    
    # Check database status
    stats = get_database_stats()
    if stats:
        print(f"✅ Database found with {stats['total_components']} components")
        print("\nSection breakdown:")
        for section, count in stats['sections'].items():
            print(f"  📋 {section}: {count} components")
    else:
        print("❌ Database not found. Run 'python3 resume_extractor.py' first.")
        return
    
    print("\n" + "=" * 50)
    print("🎯 DEMO: Job Description Analysis")
    print("=" * 50)
    
    # Demo job analysis
    sample_job = add_sample_job_description()
    keywords = analyze_job_keywords(sample_job['description'])
    
    print(f"\n🔍 Extracted Keywords ({len(keywords)}):")
    for keyword in keywords:
        print(f"  • {keyword}")
    
    print(f"\n🎯 Searching for matching components...")
    print("=" * 50)
    
    # Search for matching components
    for keyword in keywords[:5]:  # Test with first 5 keywords
        results = search_components(keyword)
        if results:
            print(f"\n📋 Matches for '{keyword}' ({len(results)} found):")
            for title, content, section, kw in results[:2]:  # Show top 2 matches
                print(f"  • {title[:60]}... ({section})")
    
    print("\n" + "=" * 50)
    print("🚀 Next Steps:")
    print("=" * 50)
    print("1. Open 'enhanced_resume_app.html' in your browser")
    print("2. Try the Job Matcher tab with real job descriptions")
    print("3. Build a resume using the Resume Builder")
    print("4. Export your customized resume to PDF")
    
    print(f"\n📁 Files in system:")
    files = [
        "enhanced_resume_app.html (Main Application)",
        "resume_database.db (Component Database)",
        "extracted_components.json (Review File)",
        "README.md (Documentation)"
    ]
    
    for file in files:
        filepath = file.split(' ')[0]
        if os.path.exists(filepath):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")

if __name__ == "__main__":
    main()
