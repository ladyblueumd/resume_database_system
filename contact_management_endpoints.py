#!/usr/bin/env python
"""
Contact Management API Endpoints
Flask endpoints for managing contacts, companies, and professional relationships
"""

from flask import jsonify, request
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_contact_management_endpoints(app, db_path='resume_database.db'):
    """Add contact management endpoints to the Flask app"""
    
    def get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @app.route('/api/contacts/stats', methods=['GET'])
    def get_contact_stats():
        """Get contact management statistics"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            stats = {}
            
            # Total companies
            stats['total_companies'] = cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
            
            # Total contacts
            stats['total_contacts'] = cursor.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            
            # Reference contacts
            stats['reference_contacts'] = cursor.execute(
                "SELECT COUNT(*) FROM contacts WHERE is_reference = TRUE"
            ).fetchone()[0]
            
            # Industries
            stats['total_industries'] = cursor.execute(
                "SELECT COUNT(DISTINCT industry) FROM companies"
            ).fetchone()[0]
            
            # Active relationships
            stats['active_companies'] = cursor.execute(
                "SELECT COUNT(*) FROM companies WHERE relationship_status = 'active'"
            ).fetchone()[0]
            
            # Contact breakdown by role
            role_counts = cursor.execute("""
                SELECT role_type, COUNT(*) as count 
                FROM contacts 
                GROUP BY role_type
            """).fetchall()
            stats['contacts_by_role'] = {row['role_type']: row['count'] for row in role_counts}
            
            conn.close()
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error getting contact stats: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/companies', methods=['GET'])
    def get_companies():
        """Get all companies with filters"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get query parameters
            search = request.args.get('search', '')
            industry = request.args.get('industry', '')
            size = request.args.get('size', '')
            status = request.args.get('status', '')
            
            # Build query
            query = """
                SELECT c.*, 
                       COUNT(DISTINCT ct.id) as contact_count,
                       COUNT(DISTINCT ct.id) FILTER (WHERE ct.is_reference = TRUE) as reference_count
                FROM companies c
                LEFT JOIN contacts ct ON c.id = ct.company_id
                WHERE 1=1
            """
            params = []
            
            if search:
                query += " AND c.company_name LIKE ?"
                params.append(f"%{search}%")
            
            if industry:
                query += " AND c.industry = ?"
                params.append(industry)
            
            if size:
                query += " AND c.company_size = ?"
                params.append(size)
            
            if status:
                query += " AND c.relationship_status = ?"
                params.append(status)
            
            query += " GROUP BY c.id ORDER BY c.total_earnings DESC"
            
            companies = cursor.execute(query, params).fetchall()
            
            result = []
            for company in companies:
                company_dict = dict(company)
                result.append(company_dict)
            
            conn.close()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/contacts', methods=['GET'])
    def get_contacts():
        """Get all contacts with filters"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get query parameters
            search = request.args.get('search', '')
            role = request.args.get('role', '')
            strength = request.args.get('strength', '')
            reference_only = request.args.get('reference_only', 'false').lower() == 'true'
            company_id = request.args.get('company_id', '')
            
            # Build query
            query = """
                SELECT c.*, comp.company_name, comp.industry,
                       COUNT(DISTINCT ci.id) as total_interactions
                FROM contacts c
                LEFT JOIN companies comp ON c.company_id = comp.id
                LEFT JOIN contact_interactions ci ON c.id = ci.contact_id
                WHERE 1=1
            """
            params = []
            
            if search:
                query += " AND (c.full_name LIKE ? OR c.email LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            if role:
                query += " AND c.role_type = ?"
                params.append(role)
            
            if strength:
                query += " AND c.relationship_strength = ?"
                params.append(strength)
            
            if reference_only:
                query += " AND c.is_reference = TRUE"
            
            if company_id:
                query += " AND c.company_id = ?"
                params.append(company_id)
            
            query += " GROUP BY c.id ORDER BY c.interaction_count DESC"
            
            contacts = cursor.execute(query, params).fetchall()
            
            result = []
            for contact in contacts:
                contact_dict = dict(contact)
                result.append(contact_dict)
            
            conn.close()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/contacts/<int:contact_id>', methods=['GET'])
    def get_contact_detail(contact_id):
        """Get detailed contact information"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get contact details
            contact = cursor.execute("""
                SELECT c.*, comp.company_name, comp.industry
                FROM contacts c
                LEFT JOIN companies comp ON c.company_id = comp.id
                WHERE c.id = ?
            """, (contact_id,)).fetchone()
            
            if not contact:
                return jsonify({'error': 'Contact not found'}), 404
            
            contact_dict = dict(contact)
            
            # Get interaction history
            interactions = cursor.execute("""
                SELECT ci.*, wom.title as work_order_title
                FROM contact_interactions ci
                LEFT JOIN work_orders_markdown wom ON ci.work_order_id = wom.work_order_id
                WHERE ci.contact_id = ?
                ORDER BY ci.interaction_date DESC
                LIMIT 20
            """, (contact_id,)).fetchall()
            
            contact_dict['interactions'] = [dict(i) for i in interactions]
            
            # Get communication channels
            channels = cursor.execute("""
                SELECT * FROM communication_channels
                WHERE contact_id = ?
            """, (contact_id,)).fetchall()
            
            contact_dict['communication_channels'] = [dict(c) for c in channels]
            
            conn.close()
            return jsonify(contact_dict)
            
        except Exception as e:
            logger.error(f"Error getting contact detail: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/contacts/<int:contact_id>/reference', methods=['POST'])
    def update_reference_status(contact_id):
        """Update contact reference status"""
        try:
            data = request.json
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE contacts
                SET is_reference = ?,
                    reference_quality = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('is_reference', False),
                data.get('reference_quality', 3),
                contact_id
            ))
            
            # Add reference details if provided
            if data.get('is_reference') and data.get('reference_details'):
                ref = data['reference_details']
                cursor.execute("""
                    INSERT OR REPLACE INTO contact_references (
                        contact_id, reference_type, relationship_context,
                        years_known, reference_strength, areas_of_expertise,
                        sample_recommendation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    contact_id,
                    ref.get('type', 'professional'),
                    ref.get('context', ''),
                    ref.get('years_known', 1),
                    ref.get('strength', 3),
                    ref.get('expertise', ''),
                    ref.get('recommendation', '')
                ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'message': 'Reference status updated'})
            
        except Exception as e:
            logger.error(f"Error updating reference status: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/industries', methods=['GET'])
    def get_industries():
        """Get industry breakdown"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            industries = cursor.execute("""
                SELECT 
                    industry,
                    COUNT(*) as company_count,
                    SUM(total_work_orders) as total_work_orders,
                    SUM(total_earnings) as total_earnings,
                    COUNT(DISTINCT c.id) as contact_count
                FROM companies comp
                LEFT JOIN contacts c ON comp.id = c.company_id
                GROUP BY industry
                ORDER BY company_count DESC
            """).fetchall()
            
            result = []
            for industry in industries:
                industry_dict = dict(industry)
                
                # Get top companies in this industry
                top_companies = cursor.execute("""
                    SELECT company_name, total_earnings
                    FROM companies
                    WHERE industry = ?
                    ORDER BY total_earnings DESC
                    LIMIT 5
                """, (industry['industry'],)).fetchall()
                
                industry_dict['top_companies'] = [dict(c) for c in top_companies]
                result.append(industry_dict)
            
            conn.close()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error getting industries: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/references', methods=['GET'])
    def get_references():
        """Get all available references"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            references = cursor.execute("""
                SELECT 
                    c.*,
                    comp.company_name,
                    comp.industry,
                    r.reference_type,
                    r.reference_strength,
                    r.years_known,
                    r.areas_of_expertise,
                    r.sample_recommendation
                FROM contacts c
                JOIN companies comp ON c.company_id = comp.id
                LEFT JOIN contact_references r ON c.id = r.contact_id
                WHERE c.is_reference = TRUE
                ORDER BY c.reference_quality DESC, c.interaction_count DESC
            """).fetchall()
            
            result = []
            for ref in references:
                ref_dict = dict(ref)
                result.append(ref_dict)
            
            conn.close()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error getting references: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/contacts/interactions', methods=['GET'])
    def get_recent_interactions():
        """Get recent contact interactions"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            limit = int(request.args.get('limit', 20))
            
            interactions = cursor.execute("""
                SELECT 
                    ci.*,
                    c.full_name as contact_name,
                    c.email as contact_email,
                    comp.company_name,
                    wom.title as work_order_title
                FROM contact_interactions ci
                JOIN contacts c ON ci.contact_id = c.id
                LEFT JOIN companies comp ON c.company_id = comp.id
                LEFT JOIN work_orders_markdown wom ON ci.work_order_id = wom.work_order_id
                ORDER BY ci.interaction_date DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            result = []
            for interaction in interactions:
                interaction_dict = dict(interaction)
                result.append(interaction_dict)
            
            conn.close()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error getting interactions: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/contacts/network-map', methods=['GET'])
    def get_network_map():
        """Get contact relationship network data"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get all contacts with company info
            contacts = cursor.execute("""
                SELECT c.id, c.full_name, c.company_id, comp.company_name
                FROM contacts c
                LEFT JOIN companies comp ON c.company_id = comp.id
                WHERE c.interaction_count > 2
            """).fetchall()
            
            # Get relationships
            relationships = cursor.execute("""
                SELECT * FROM contact_relationships
            """).fetchall()
            
            # Format for network visualization
            nodes = []
            for contact in contacts:
                nodes.append({
                    'id': contact['id'],
                    'name': contact['full_name'],
                    'company': contact['company_name'],
                    'group': contact['company_id'] or 0
                })
            
            links = []
            for rel in relationships:
                links.append({
                    'source': rel['contact_id_1'],
                    'target': rel['contact_id_2'],
                    'strength': rel['relationship_strength']
                })
            
            conn.close()
            return jsonify({
                'nodes': nodes,
                'links': links
            })
            
        except Exception as e:
            logger.error(f"Error getting network map: {e}")
            return jsonify({'error': str(e)}), 500
    
    logger.info("Contact management endpoints added successfully") 