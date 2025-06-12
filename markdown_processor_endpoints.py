#!/usr/bin/env python3
"""
Markdown Processor API Endpoints
Flask endpoints for processing FieldNation markdown files
"""

from flask import jsonify, request
import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from claude_markdown_processor import FieldNationMarkdownProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_markdown_processor_endpoints(app, db_path='resume_database.db'):
    """Add markdown processor endpoints to the Flask app"""
    
    # Initialize processor
    try:
        processor = FieldNationMarkdownProcessor(db_path)
        logger.info("Markdown processor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize markdown processor: {e}")
        processor = None

    @app.route('/api/markdown-processor/status', methods=['GET'])
    def get_processor_status():
        """Get the status of the markdown processor"""
        if processor is None:
            return jsonify({
                'status': 'error',
                'message': 'Markdown processor not initialized'
            }), 500
        
        return jsonify({
            'status': 'ready',
            'database_path': processor.db_path,
            'processor_type': 'FieldNationMarkdownProcessor'
        })

    @app.route('/api/markdown-processor/process-single', methods=['POST'])
    def process_single_file():
        """Process a single markdown file"""
        if processor is None:
            return jsonify({'error': 'Markdown processor not initialized'}), 500
        
        try:
            data = request.get_json()
            file_path = data.get('file_path')
            
            if not file_path:
                return jsonify({'error': 'file_path is required'}), 400
            
            if not os.path.exists(file_path):
                return jsonify({'error': f'File not found: {file_path}'}), 404
            
            # Parse the file
            logger.info(f"Processing file: {file_path}")
            extracted_data = processor.parse_markdown_file(file_path)
            
            if not extracted_data.get('work_order_id'):
                return jsonify({
                    'error': 'Could not extract work order ID from file',
                    'file_path': file_path
                }), 400
            
            # Save to database
            success = processor.save_to_database(extracted_data)
            
            if success:
                return jsonify({
                    'success': True,
                    'work_order_id': extracted_data.get('work_order_id'),
                    'title': extracted_data.get('title'),
                    'company_name': extracted_data.get('company_name'),
                    'total_paid': extracted_data.get('total_paid'),
                    'quality_score': extracted_data.get('data_quality_score'),
                    'file_path': file_path
                })
            else:
                return jsonify({
                    'error': 'Failed to save to database',
                    'extracted_data': extracted_data
                }), 500
        
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/markdown-processor/process-directory', methods=['POST'])
    def process_directory():
        """Process all markdown files in a directory"""
        if processor is None:
            return jsonify({'error': 'Markdown processor not initialized'}), 500
        
        try:
            data = request.get_json()
            directory_path = data.get('directory_path', 'downloaded work orders/')
            
            if not os.path.exists(directory_path):
                return jsonify({'error': f'Directory not found: {directory_path}'}), 404
            
            # Process directory
            logger.info(f"Processing directory: {directory_path}")
            results = processor.process_directory(directory_path)
            
            return jsonify({
                'success': True,
                'results': results,
                'directory_path': directory_path
            })
        
        except Exception as e:
            logger.error(f"Error processing directory: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/markdown-processor/work-orders', methods=['GET'])
    def get_markdown_work_orders():
        """Get work orders from markdown processing"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get query parameters
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            search = request.args.get('search', '')
            company_filter = request.args.get('company', '')
            date_from = request.args.get('date_from', '')
            date_to = request.args.get('date_to', '')
            
            # Build query
            base_query = "SELECT * FROM work_orders_markdown"
            where_conditions = []
            params = []
            
            if search:
                where_conditions.append("search_text LIKE ?")
                params.append(f"%{search}%")
            
            if company_filter:
                where_conditions.append("company_name LIKE ?")
                params.append(f"%{company_filter}%")
            
            if date_from:
                where_conditions.append("scheduled_date >= ?")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("scheduled_date <= ?")
                params.append(date_to)
            
            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)
            
            # Add ordering and pagination
            query = f"{base_query} ORDER BY scheduled_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            work_orders = [dict(row) for row in cursor.fetchall()]
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM work_orders_markdown"
            if where_conditions:
                count_query += " WHERE " + " AND ".join(where_conditions[:-2])  # Remove limit/offset params
            
            cursor.execute(count_query, params[:-2])
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            return jsonify({
                'work_orders': work_orders,
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            })
        
        except Exception as e:
            logger.error(f"Error getting markdown work orders: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/markdown-processor/work-orders/<work_order_id>', methods=['GET'])
    def get_markdown_work_order(work_order_id):
        """Get a specific work order from markdown processing"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM work_orders_markdown WHERE work_order_id = ?", (work_order_id,))
            work_order = cursor.fetchone()
            
            if not work_order:
                return jsonify({'error': 'Work order not found'}), 404
            
            work_order_dict = dict(work_order)
            
            # Parse JSON fields
            json_fields = ['tasks_completed', 'deliverables', 'buyer_custom_fields', 'provider_custom_fields']
            for field in json_fields:
                if work_order_dict.get(field):
                    try:
                        work_order_dict[field] = json.loads(work_order_dict[field])
                    except (json.JSONDecodeError, TypeError):
                        work_order_dict[field] = []
            
            conn.close()
            return jsonify(work_order_dict)
        
        except Exception as e:
            logger.error(f"Error getting markdown work order: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/markdown-processor/stats', methods=['GET'])
    def get_markdown_processor_stats():
        """Get statistics about processed markdown files"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("SELECT COUNT(*) FROM work_orders_markdown")
            total_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT company_name) FROM work_orders_markdown")
            unique_companies = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(total_paid) FROM work_orders_markdown WHERE total_paid IS NOT NULL")
            total_earnings = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT AVG(total_paid) FROM work_orders_markdown WHERE total_paid IS NOT NULL")
            avg_pay = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT AVG(data_quality_score) FROM work_orders_markdown WHERE data_quality_score IS NOT NULL")
            avg_quality = cursor.fetchone()[0] or 0
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM work_orders_markdown 
                GROUP BY status 
                ORDER BY count DESC
            """)
            by_status = [{'status': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            # By company
            cursor.execute("""
                SELECT company_name, COUNT(*) as count,
                       COALESCE(SUM(total_paid), 0) as total_pay
                FROM work_orders_markdown 
                GROUP BY company_name 
                ORDER BY count DESC
                LIMIT 10
            """)
            top_companies = [{'company': row[0], 'count': row[1], 'total_pay': row[2]} for row in cursor.fetchall()]
            
            # Processing quality distribution
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN data_quality_score >= 0.8 THEN 'High'
                        WHEN data_quality_score >= 0.6 THEN 'Medium'
                        WHEN data_quality_score >= 0.4 THEN 'Low'
                        ELSE 'Very Low'
                    END as quality_level,
                    COUNT(*) as count
                FROM work_orders_markdown 
                WHERE data_quality_score IS NOT NULL
                GROUP BY quality_level
                ORDER BY count DESC
            """)
            quality_distribution = [{'quality': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            conn.close()
            
            return jsonify({
                'total_orders': total_orders,
                'unique_companies': unique_companies,
                'total_earnings': round(total_earnings, 2),
                'average_pay': round(avg_pay, 2),
                'average_quality_score': round(avg_quality, 3),
                'by_status': by_status,
                'top_companies': top_companies,
                'quality_distribution': quality_distribution
            })
        
        except Exception as e:
            logger.error(f"Error getting markdown processor stats: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/markdown-processor/migrate-to-fieldnation', methods=['POST'])
    def migrate_to_fieldnation_table():
        """Migrate processed markdown data to the main fieldnation_work_orders table"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if fieldnation_work_orders table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='fieldnation_work_orders'
            """)
            
            if not cursor.fetchone():
                return jsonify({'error': 'fieldnation_work_orders table does not exist'}), 400
            
            # Get data from work_orders_markdown
            cursor.execute("SELECT * FROM work_orders_markdown")
            markdown_orders = cursor.fetchall()
            markdown_columns = [desc[0] for desc in cursor.description]
            
            if not markdown_orders:
                return jsonify({'message': 'No markdown orders to migrate'})
            
            # Map markdown fields to fieldnation fields
            migrated_count = 0
            errors = []
            
            for order in markdown_orders:
                order_dict = dict(zip(markdown_columns, order))
                
                try:
                    # Map fields from markdown to fieldnation format
                    fieldnation_data = {
                        'fn_work_order_id': order_dict.get('work_order_id'),
                        'title': order_dict.get('title'),
                        'work_order_date': order_dict.get('date_created'),
                        'service_date': order_dict.get('scheduled_date'),
                        'completion_date': order_dict.get('date_completed'),
                        'location': order_dict.get('location_address'),
                        'city': order_dict.get('location_city'),
                        'state': order_dict.get('location_state'),
                        'zip_code': order_dict.get('location_zip'),
                        'buyer_company': order_dict.get('company_name'),
                        'pay_amount': order_dict.get('total_paid'),
                        'status': order_dict.get('status'),
                        'work_description': order_dict.get('service_description_full'),
                        'work_type': order_dict.get('work_type'),
                        'service_type': order_dict.get('service_type'),
                        'equipment_type': order_dict.get('equipment_type'),
                        'closeout_notes': order_dict.get('closeout_notes'),
                        'data_source': 'markdown',
                        'source_file_path': order_dict.get('file_source'),
                        'extraction_quality': order_dict.get('data_quality_score')
                    }
                    
                    # Insert or update in fieldnation_work_orders
                    cursor.execute("""
                        INSERT OR REPLACE INTO fieldnation_work_orders 
                        (fn_work_order_id, title, work_order_date, service_date, completion_date,
                         location, city, state, zip_code, buyer_company, pay_amount, status,
                         work_description, work_type, service_type, equipment_type, closeout_notes,
                         data_source, source_file_path, extraction_quality, extracted_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        fieldnation_data.get('fn_work_order_id'),
                        fieldnation_data.get('title'),
                        fieldnation_data.get('work_order_date'),
                        fieldnation_data.get('service_date'),
                        fieldnation_data.get('completion_date'),
                        fieldnation_data.get('location'),
                        fieldnation_data.get('city'),
                        fieldnation_data.get('state'),
                        fieldnation_data.get('zip_code'),
                        fieldnation_data.get('buyer_company'),
                        fieldnation_data.get('pay_amount'),
                        fieldnation_data.get('status'),
                        fieldnation_data.get('work_description'),
                        fieldnation_data.get('work_type'),
                        fieldnation_data.get('service_type'),
                        fieldnation_data.get('equipment_type'),
                        fieldnation_data.get('closeout_notes'),
                        fieldnation_data.get('data_source'),
                        fieldnation_data.get('source_file_path'),
                        fieldnation_data.get('extraction_quality'),
                        datetime.now()
                    ))
                    
                    migrated_count += 1
                    
                except Exception as e:
                    errors.append({
                        'work_order_id': order_dict.get('work_order_id'),
                        'error': str(e)
                    })
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'migrated_count': migrated_count,
                'total_processed': len(markdown_orders),
                'errors': errors
            })
        
        except Exception as e:
            logger.error(f"Error migrating to fieldnation table: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("Markdown processor endpoints added successfully") 