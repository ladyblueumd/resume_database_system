#!/usr/bin/env python3
"""
Clear Database Script
Clears all components and work orders from the database to start fresh
"""

import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'resume_database.db'

def clear_database():
    """Clear all components and work orders from the database"""
    try:
        if not os.path.exists(DATABASE_PATH):
            logger.warning(f"Database not found at {DATABASE_PATH}")
            return False
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get initial counts
        cursor.execute("SELECT COUNT(*) FROM resume_components")
        initial_components = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM work_orders")
        initial_work_orders = cursor.fetchone()[0]
        
        logger.info(f"Found {initial_components} components and {initial_work_orders} work orders")
        
        # Clear work orders first (due to foreign key relationships)
        logger.info("Clearing work orders...")
        cursor.execute("DELETE FROM work_orders")
        cleared_work_orders = cursor.rowcount
        
        # Clear resume components
        logger.info("Clearing resume components...")
        cursor.execute("DELETE FROM resume_components")
        cleared_components = cursor.rowcount
        
        # Clear component usage tracking
        logger.info("Clearing component usage...")
        cursor.execute("DELETE FROM component_usage")
        cleared_usage = cursor.rowcount
        
        # Clear employment history
        logger.info("Clearing employment history...")
        cursor.execute("DELETE FROM employment_history")
        cleared_employment = cursor.rowcount
        
        # Clear job descriptions
        logger.info("Clearing job descriptions...")
        cursor.execute("DELETE FROM job_descriptions")
        cleared_jobs = cursor.rowcount
        
        # Clear projects if table exists
        try:
            cursor.execute("DELETE FROM projects")
            cleared_projects = cursor.rowcount
            logger.info(f"Cleared {cleared_projects} projects")
        except sqlite3.OperationalError:
            logger.info("Projects table not found - skipping")
        
        # Clear project work order assignments if table exists
        try:
            cursor.execute("DELETE FROM project_work_orders")
            cleared_assignments = cursor.rowcount
            logger.info(f"Cleared {cleared_assignments} project assignments")
        except sqlite3.OperationalError:
            logger.info("Project work orders table not found - skipping")
        
        # Reset auto-increment counters
        logger.info("Resetting auto-increment counters...")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('resume_components', 'work_orders', 'component_usage', 'employment_history', 'job_descriptions', 'projects', 'project_work_orders')")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info("Database cleared successfully!")
        logger.info(f"Cleared: {cleared_components} components, {cleared_work_orders} work orders, {cleared_usage} usage records, {cleared_employment} employment records, {cleared_jobs} job descriptions")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return False

def verify_database_empty():
    """Verify that the database is empty"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check all main tables
        tables = ['resume_components', 'work_orders', 'component_usage', 'employment_history', 'job_descriptions']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"{table}: {count} records")
            except sqlite3.OperationalError:
                logger.info(f"{table}: table not found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error verifying database: {e}")

if __name__ == '__main__':
    logger.info("Starting database cleanup...")
    
    if clear_database():
        logger.info("Verifying database is empty...")
        verify_database_empty()
        logger.info("Database cleanup completed successfully!")
    else:
        logger.error("Database cleanup failed!") 