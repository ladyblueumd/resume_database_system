#!/usr/bin/env python3
"""
Clear Resume Database Script
Removes all resume components, generated resumes, uploaded resumes, job descriptions, and templates
"""

import sqlite3
import os

def clear_database():
    """Clear all resume-related data from the database"""
    db_path = 'resume_database.db'
    
    if not os.path.exists(db_path):
        print('❌ Database file not found.')
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear resume components
        cursor.execute('DELETE FROM resume_components')
        components_deleted = cursor.rowcount
        
        # Clear generated resumes
        cursor.execute('DELETE FROM generated_resumes')
        resumes_deleted = cursor.rowcount
        
        # Clear uploaded resumes
        cursor.execute('DELETE FROM uploaded_resumes')
        uploaded_deleted = cursor.rowcount
        
        # Clear job descriptions
        cursor.execute('DELETE FROM job_descriptions')
        jobs_deleted = cursor.rowcount
        
        # Clear templates
        cursor.execute('DELETE FROM resume_templates')
        templates_deleted = cursor.rowcount
        
        # Reset auto-increment counters
        cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("resume_components", "generated_resumes", "uploaded_resumes", "job_descriptions", "resume_templates")')
        
        conn.commit()
        conn.close()
        
        print('✅ Database cleared successfully:')
        print(f'   - Resume components: {components_deleted} deleted')
        print(f'   - Generated resumes: {resumes_deleted} deleted')
        print(f'   - Uploaded resumes: {uploaded_deleted} deleted')
        print(f'   - Job descriptions: {jobs_deleted} deleted')
        print(f'   - Templates: {templates_deleted} deleted')
        print('\n🔄 Database is now reset and ready for fresh data.')
        
    except Exception as e:
        print(f'❌ Error clearing database: {e}')

if __name__ == '__main__':
    clear_database() 