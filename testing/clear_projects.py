#!/usr/bin/env python3
"""
Clear Projects Script
Clears only the projects table from the database
"""

import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'resume_database.db'

def clear_projects():
    """Clear only projects from the database"""
    try:
        if not os.path.exists(DATABASE_PATH):
            logger.warning(f"Database not found at {DATABASE_PATH}")
            return False
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Clear work_order_projects table
        try:
            cursor.execute("SELECT COUNT(*) FROM work_order_projects")
            initial_work_order_projects = cursor.fetchone()[0]
            logger.info(f"Found {initial_work_order_projects} work order projects")
            
            cursor.execute("DELETE FROM work_order_projects")
            cleared_work_order_projects = cursor.rowcount
            logger.info(f"Cleared {cleared_work_order_projects} work order projects")
        except sqlite3.OperationalError:
            logger.info("work_order_projects table not found - skipping")
            cleared_work_order_projects = 0
        
        # Clear project_portfolio table
        try:
            cursor.execute("SELECT COUNT(*) FROM project_portfolio")
            initial_project_portfolio = cursor.fetchone()[0]
            logger.info(f"Found {initial_project_portfolio} project portfolio entries")
            
            cursor.execute("DELETE FROM project_portfolio")
            cleared_project_portfolio = cursor.rowcount
            logger.info(f"Cleared {cleared_project_portfolio} project portfolio entries")
        except sqlite3.OperationalError:
            logger.info("project_portfolio table not found - skipping")
            cleared_project_portfolio = 0
        
        # Clear work_order_project_assignments table
        try:
            cursor.execute("SELECT COUNT(*) FROM work_order_project_assignments")
            initial_assignments = cursor.fetchone()[0]
            logger.info(f"Found {initial_assignments} work order project assignments")
            
            cursor.execute("DELETE FROM work_order_project_assignments")
            cleared_assignments = cursor.rowcount
            logger.info(f"Cleared {cleared_assignments} work order project assignments")
        except sqlite3.OperationalError:
            logger.info("work_order_project_assignments table not found - skipping")
            cleared_assignments = 0
        
        # Clear traditional projects table if it exists
        try:
            cursor.execute("SELECT COUNT(*) FROM projects")
            initial_projects = cursor.fetchone()[0]
            logger.info(f"Found {initial_projects} traditional projects")
            
            cursor.execute("DELETE FROM projects")
            cleared_projects = cursor.rowcount
            logger.info(f"Cleared {cleared_projects} traditional projects")
        except sqlite3.OperationalError:
            logger.info("projects table not found - skipping")
            cleared_projects = 0
        
        # Reset auto-increment counters for all project tables
        logger.info("Resetting project auto-increment counters...")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('projects', 'work_order_projects', 'project_portfolio', 'work_order_project_assignments')")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info("Projects cleared successfully!")
        logger.info(f"Total cleared: {cleared_projects} projects, {cleared_work_order_projects} work order projects, {cleared_project_portfolio} portfolio entries, {cleared_assignments} assignments")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing projects: {e}")
        return False

def verify_projects_empty():
    """Verify that projects are cleared"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check all project-related tables
        project_tables = ['projects', 'work_order_projects', 'project_portfolio', 'work_order_project_assignments']
        
        for table in project_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"{table}: {count} records")
            except sqlite3.OperationalError:
                logger.info(f"{table}: table not found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error verifying projects: {e}")

if __name__ == '__main__':
    logger.info("Starting projects cleanup...")
    
    if clear_projects():
        logger.info("Verifying projects are empty...")
        verify_projects_empty()
        logger.info("Projects cleanup completed successfully!")
    else:
        logger.error("Projects cleanup failed!") 