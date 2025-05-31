#!/usr/bin/env python3
"""
Clear Resume Components Script
Safely removes all resume components while preserving work orders and projects
"""

import sqlite3
from datetime import datetime

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('resume_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def clear_resume_components():
    """Clear all resume components and related data"""
    print("🧹 Clearing resume components for fresh start...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get count before clearing
        cursor.execute("SELECT COUNT(*) FROM resume_components")
        before_count = cursor.fetchone()[0]
        print(f"   📊 Found {before_count} resume components to clear")
        
        # Check if tables exist before clearing
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        # Clear related tables first (only if they exist)
        if 'resume_component_usage' in existing_tables:
            cursor.execute("DELETE FROM resume_component_usage")
            print("   ✅ Cleared component usage records")
        
        if 'component_selections' in existing_tables:
            cursor.execute("DELETE FROM component_selections")
            print("   ✅ Cleared component selections")
        
        # Clear main components table
        cursor.execute("DELETE FROM resume_components")
        print("   ✅ Cleared all resume components")
        
        # Reset any auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='resume_components'")
        print("   ✅ Reset component ID counter")
        
        # Clear job descriptions that might reference components
        if 'job_descriptions' in existing_tables:
            cursor.execute("DELETE FROM job_descriptions")
            print("   ✅ Cleared job descriptions")
        
        if 'generated_resumes' in existing_tables:
            cursor.execute("DELETE FROM generated_resumes")
            print("   ✅ Cleared generated resumes")
        
        conn.commit()
        
        # Verify clearing
        cursor.execute("SELECT COUNT(*) FROM resume_components")
        after_count = cursor.fetchone()[0]
        
        print(f"\n🎉 Successfully cleared {before_count} resume components!")
        print(f"   📊 Current component count: {after_count}")
        
        # Show what remains intact
        cursor.execute("SELECT COUNT(*) FROM work_orders")
        work_orders_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM work_order_projects")
        projects_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM employment_history")
        employment_count = cursor.fetchone()[0]
        
        print(f"\n✅ Data preserved:")
        print(f"   🔧 Work Orders: {work_orders_count}")
        print(f"   📁 Projects: {projects_count}")
        print(f"   💼 Employment History: {employment_count}")
        
    except Exception as e:
        print(f"❌ Error clearing components: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clear_resume_components()
    print("\n🚀 Ready for fresh resume imports!") 