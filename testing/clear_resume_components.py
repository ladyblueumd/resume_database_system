#!/usr/bin/env python3
"""
Clear Resume Components Script
Clears all resume components and optionally other data for a fresh start
"""

import sqlite3
import os
import sys
from datetime import datetime

DATABASE_PATH = 'resume_database.db'

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def display_current_data():
    """Display what data currently exists"""
    print("📊 CURRENT DATABASE CONTENTS:")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Count components by section
        cursor.execute("""
            SELECT st.name, COUNT(*) as count 
            FROM resume_components rc 
            JOIN section_types st ON rc.section_type_id = st.id 
            GROUP BY st.name
            ORDER BY count DESC
        """)
        components_by_section = cursor.fetchall()
        
        if components_by_section:
            print("📚 Resume Components:")
            total_components = 0
            for row in components_by_section:
                print(f"  • {row['name']}: {row['count']} components")
                total_components += row['count']
            print(f"  TOTAL: {total_components} components")
        else:
            print("📚 Resume Components: None")
        
        # Count employment records
        cursor.execute("SELECT COUNT(*) as count FROM employment_history")
        employment_count = cursor.fetchone()['count']
        print(f"💼 Employment Records: {employment_count}")
        
        # Count job descriptions
        cursor.execute("SELECT COUNT(*) as count FROM job_descriptions")
        job_count = cursor.fetchone()['count']
        print(f"🎯 Job Descriptions: {job_count}")
        
        # Count work orders
        cursor.execute("SELECT COUNT(*) as count FROM work_orders")
        work_order_count = cursor.fetchone()['count']
        print(f"🔧 Work Orders: {work_order_count}")
        
        # Count projects
        cursor.execute("SELECT COUNT(*) as count FROM work_order_projects")
        project_count = cursor.fetchone()['count']
        print(f"📁 Projects: {project_count}")
        
    except Exception as e:
        print(f"Error reading database: {e}")
    finally:
        conn.close()
    
    print("=" * 50)

def clear_resume_components():
    """Clear all resume components"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM resume_components")
        count_before = cursor.fetchone()[0]
        
        # Delete all resume components
        cursor.execute("DELETE FROM resume_components")
        
        # Reset the auto-increment counter
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='resume_components'")
        
        conn.commit()
        print(f"✅ Deleted {count_before} resume components")
        
    except Exception as e:
        print(f"❌ Error clearing resume components: {e}")
        conn.rollback()
    finally:
        conn.close()

def clear_employment_history():
    """Clear all employment history"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM employment_history")
        count_before = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM employment_history")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='employment_history'")
        
        conn.commit()
        print(f"✅ Deleted {count_before} employment records")
        
    except Exception as e:
        print(f"❌ Error clearing employment history: {e}")
        conn.rollback()
    finally:
        conn.close()

def clear_job_descriptions():
    """Clear all job descriptions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM job_descriptions")
        count_before = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM job_descriptions")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='job_descriptions'")
        
        conn.commit()
        print(f"✅ Deleted {count_before} job descriptions")
        
    except Exception as e:
        print(f"❌ Error clearing job descriptions: {e}")
        conn.rollback()
    finally:
        conn.close()

def clear_all_data():
    """Clear all data for a complete fresh start"""
    print("🧹 CLEARING ALL DATA...")
    print("-" * 30)
    
    clear_resume_components()
    clear_employment_history() 
    clear_job_descriptions()
    
    print("-" * 30)
    print("✨ Database cleared! Ready for fresh start.")

def main():
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found: {DATABASE_PATH}")
        sys.exit(1)
    
    print("🗑️  RESUME DATABASE CLEANER")
    print("=" * 50)
    
    # Show current data
    display_current_data()
    
    print("\nWhat would you like to clear?")
    print("1. Resume Components only")
    print("2. Employment History only") 
    print("3. Job Descriptions only")
    print("4. Everything (Complete reset)")
    print("5. Show data again")
    print("6. Exit without changes")
    
    while True:
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            print("\n🗑️  Clearing resume components...")
            clear_resume_components()
            break
        elif choice == '2':
            print("\n🗑️  Clearing employment history...")
            clear_employment_history()
            break
        elif choice == '3':
            print("\n🗑️  Clearing job descriptions...")
            clear_job_descriptions()
            break
        elif choice == '4':
            confirm = input("\n⚠️  This will delete ALL data. Are you sure? (type 'YES' to confirm): ")
            if confirm == 'YES':
                clear_all_data()
            else:
                print("❌ Cancelled")
            break
        elif choice == '5':
            print()
            display_current_data()
        elif choice == '6':
            print("👋 Exiting without changes")
            break
        else:
            print("❌ Invalid choice. Please enter 1-6.")
    
    print("\n📊 FINAL DATABASE STATE:")
    print("-" * 30)
    display_current_data()

if __name__ == "__main__":
    main() 