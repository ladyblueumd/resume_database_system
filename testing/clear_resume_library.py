#!/usr/bin/env python3
"""
Clear Resume Library Script
Clears only the uploaded resumes from the database
"""

import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'resume_database.db'

def clear_resume_library():
    """Clear only uploaded resumes from the database"""
    try:
        if not os.path.exists(DATABASE_PATH):
            logger.warning(f"Database not found at {DATABASE_PATH}")
            return False
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get initial resume count
        try:
            cursor.execute("SELECT COUNT(*) FROM uploaded_resumes")
            initial_resumes = cursor.fetchone()[0]
            logger.info(f"Found {initial_resumes} uploaded resumes")
        except sqlite3.OperationalError:
            logger.info("Uploaded resumes table not found")
            return True
        
        # Clear uploaded resumes
        logger.info("Clearing uploaded resumes...")
        cursor.execute("DELETE FROM uploaded_resumes")
        cleared_resumes = cursor.rowcount
        
        # Clear resume templates if they exist
        try:
            cursor.execute("SELECT COUNT(*) FROM resume_templates")
            initial_templates = cursor.fetchone()[0]
            logger.info(f"Found {initial_templates} resume templates")
            
            cursor.execute("DELETE FROM resume_templates")
            cleared_templates = cursor.rowcount
            logger.info(f"Cleared {cleared_templates} resume templates")
        except sqlite3.OperationalError:
            logger.info("Resume templates table not found - skipping")
            cleared_templates = 0
        
        # Reset auto-increment counters for resume library
        logger.info("Resetting resume library auto-increment counters...")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('uploaded_resumes', 'resume_templates')")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info("Resume library cleared successfully!")
        logger.info(f"Cleared: {cleared_resumes} uploaded resumes, {cleared_templates} templates")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing resume library: {e}")
        return False

def verify_resume_library_empty():
    """Verify that resume library is cleared"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check uploaded_resumes table
        try:
            cursor.execute("SELECT COUNT(*) FROM uploaded_resumes")
            count = cursor.fetchone()[0]
            logger.info(f"uploaded_resumes: {count} records")
        except sqlite3.OperationalError:
            logger.info("uploaded_resumes: table not found")
        
        # Check resume_templates table
        try:
            cursor.execute("SELECT COUNT(*) FROM resume_templates")
            count = cursor.fetchone()[0]
            logger.info(f"resume_templates: {count} records")
        except sqlite3.OperationalError:
            logger.info("resume_templates: table not found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error verifying resume library: {e}")

if __name__ == '__main__':
    logger.info("Starting resume library cleanup...")
    
    if clear_resume_library():
        logger.info("Verifying resume library is empty...")
        verify_resume_library_empty()
        logger.info("Resume library cleanup completed successfully!")
    else:
        logger.error("Resume library cleanup failed!") 