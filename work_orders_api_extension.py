#!/usr/bin/env python3
"""
Work Orders API Extension for Resume Database System
Add these routes to your main app.py file
"""

from flask import jsonify, request
import sqlite3
import json
from datetime import datetime

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('resume_database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Work Orders API Routes
# Add these to your main app.py file

@app.route('/api/work-orders', methods=['GET'])
def get_work_orders():
    """Get all work orders with optional filtering"""
    try:
        conn = get_db_connection()
        
        # Parse query parameters
        category = request.args.get('category')
        company = request.args.get('company')
        work_type = request.args.get('work_type')
        client_type = request.args.get('client_type')
        state = request.args.get('state')
        title = request.args.get('title')
        project_id = request.args.get('project_id')
        unassigned = request.args.get('unassigned', 'false').lower() == 'true'
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        if unassigned:
            query = """
                SELECT wo.* FROM work_orders wo
                LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
                WHERE wopa.work_order_id IS NULL
            """
            params = []
        else:
            query = "SELECT * FROM work_orders WHERE 1=1"
            params = []
        
        if category:
            query += " AND work_category = ?"
            params.append(category)
        if company:
            query += " AND company_name LIKE ?"
            params.append(f"%{company}%")
        if work_type:
            query += " AND work_type LIKE ?"
            params.append(f"%{work_type}%")
        if client_type:
            query += " AND client_type = ?"
            params.append(client_type)
        if state:
            query += " AND state = ?"
            params.append(state)
        if title:
            query += " AND title = ?"
            params.append(title)
        if project_id:
            query = """
                SELECT wo.* FROM work_orders wo
                JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
                WHERE wopa.project_id = ?
            """
            params = [project_id]
        
        # Get total count first (without LIMIT/OFFSET)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        count_query = count_query.replace("SELECT wo.*", "SELECT COUNT(*)")
        cursor = conn.cursor()
        
        # For count query, we need to use params without limit and offset
        count_params = params[:-2] if len(params) >= 2 else params
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        # Now get the paginated results
        query += " ORDER BY service_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        work_orders = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields
        for wo in work_orders:
            if wo['technologies_used']:
                wo['technologies_used'] = json.loads(wo['technologies_used'])
            if wo['skills_demonstrated']:
                wo['skills_demonstrated'] = json.loads(wo['skills_demonstrated'])
        
        conn.close()
        return jsonify({
            'work_orders': work_orders,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/stats', methods=['GET'])
def get_work_order_stats():
    """Get work order statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("SELECT COUNT(*) FROM work_orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT company_name) FROM work_orders")
        unique_companies = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(pay_amount) FROM work_orders WHERE pay_amount IS NOT NULL")
        total_earnings = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(pay_amount) FROM work_orders WHERE pay_amount IS NOT NULL")
        avg_pay = cursor.fetchone()[0] or 0
        
        # Unassigned work orders
        cursor.execute("""
            SELECT COUNT(*) FROM work_orders wo
            LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
            WHERE wopa.work_order_id IS NULL
        """)
        unassigned_orders = cursor.fetchone()[0]
        
        # By category
        cursor.execute("""
            SELECT work_category, COUNT(*) as count, 
                   COALESCE(SUM(pay_amount), 0) as total_pay
            FROM work_orders 
            GROUP BY work_category 
            ORDER BY count DESC
        """)
        by_category = [dict(row) for row in cursor.fetchall()]
        
        # By year
        cursor.execute("""
            SELECT strftime('%Y', service_date) as year, 
                   COUNT(*) as count,
                   COALESCE(SUM(pay_amount), 0) as total_pay
            FROM work_orders 
            WHERE service_date IS NOT NULL
            GROUP BY strftime('%Y', service_date)
            ORDER BY year DESC
        """)
        by_year = [dict(row) for row in cursor.fetchall()]
        
        # Top companies
        cursor.execute("""
            SELECT company_name, COUNT(*) as count,
                   COALESCE(SUM(pay_amount), 0) as total_pay
            FROM work_orders 
            GROUP BY company_name 
            ORDER BY count DESC
            LIMIT 10
        """)
        top_companies = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_orders': total_orders,
            'unique_companies': unique_companies,
            'total_earnings': round(total_earnings, 2),
            'average_pay': round(avg_pay, 2),
            'unassigned_orders': unassigned_orders,
            'by_category': by_category,
            'by_year': by_year,
            'top_companies': top_companies
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/categories', methods=['GET'])
def get_work_order_categories():
    """Get unique work order categories"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT work_category FROM work_orders ORDER BY work_category")
        categories = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT work_type FROM work_orders WHERE work_type IS NOT NULL ORDER BY work_type")
        work_types = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT client_type FROM work_orders WHERE client_type IS NOT NULL ORDER BY client_type")
        client_types = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT state FROM work_orders WHERE state IS NOT NULL ORDER BY state")
        states = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'categories': categories,
            'work_types': work_types,
            'client_types': client_types,
            'states': states
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/<int:work_order_id>', methods=['GET'])
def get_work_order(work_order_id):
    """Get a specific work order"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,))
        work_order = cursor.fetchone()
        
        if not work_order:
            return jsonify({'error': 'Work order not found'}), 404
        
        wo_dict = dict(work_order)
        
        # Parse JSON fields
        if wo_dict['technologies_used']:
            wo_dict['technologies_used'] = json.loads(wo_dict['technologies_used'])
        if wo_dict['skills_demonstrated']:
            wo_dict['skills_demonstrated'] = json.loads(wo_dict['skills_demonstrated'])
        
        conn.close()
        return jsonify(wo_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/<int:work_order_id>', methods=['PUT'])
def update_work_order(work_order_id):
    """Update a work order"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if work order exists
        cursor.execute("SELECT id FROM work_orders WHERE id = ?", (work_order_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Work order not found'}), 404
        
        # Update fields
        update_fields = []
        params = []
        
        for field in ['work_description', 'challenges_faced', 'solutions_implemented', 
                     'client_feedback', 'lessons_learned', 'complexity_level',
                     'include_in_resume', 'highlight_project']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if update_fields:
            params.append(datetime.now().isoformat())
            params.append(work_order_id)
            
            query = f"UPDATE work_orders SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return jsonify({'message': 'Work order updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/resume-components', methods=['GET'])
def generate_resume_components_from_work_orders():
    """Generate resume components from work orders"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get highlighted work orders
        cursor.execute("""
            SELECT * FROM work_orders 
            WHERE include_in_resume = TRUE 
            ORDER BY highlight_project DESC, pay_amount DESC, service_date DESC
            LIMIT 20
        """)
        
        work_orders = [dict(row) for row in cursor.fetchall()]
        
        components = []
        
        for wo in work_orders:
            # Parse JSON fields
            technologies = json.loads(wo['technologies_used']) if wo['technologies_used'] else []
            skills = json.loads(wo['skills_demonstrated']) if wo['skills_demonstrated'] else []
            
            # Create work experience component
            title = f"{wo['work_type']} - {wo['company_name']}"
            if wo['service_date']:
                service_date = datetime.strptime(wo['service_date'], '%Y-%m-%d').strftime('%B %Y')
                title += f" ({service_date})"
            
            content = wo['title']
            if wo['work_description']:
                content += f"\n{wo['work_description']}"
            if wo['location']:
                content += f"\nLocation: {wo['location']}"
            
            # Add technologies and skills as keywords
            keywords = technologies + skills + [wo['work_category'], wo['client_type']]
            keywords = [k for k in keywords if k]  # Remove empty strings
            
            component = {
                'title': title,
                'content': content,
                'section_type': 'work_experience',
                'keywords': keywords,
                'industry_tags': [wo['client_type']] if wo['client_type'] else [],
                'source': 'fieldnation_work_order',
                'source_id': wo['id']
            }
            
            components.append(component)
        
        conn.close()
        return jsonify(components)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/import', methods=['POST'])
def import_work_orders():
    """Trigger work order import from CSV files"""
    try:
        # This would call your import script
        import subprocess
        result = subprocess.run(['python', 'import_field_nation_data.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                'message': 'Import completed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'error': 'Import failed',
                'details': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PROJECT MANAGEMENT API ROUTES

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all work order projects"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        include_resume_only = request.args.get('resume_only', 'false').lower() == 'true'
        
        if include_resume_only:
            cursor.execute("SELECT * FROM project_portfolio")
        else:
            cursor.execute("""
                SELECT * FROM work_order_projects
                ORDER BY total_work_orders DESC, created_at DESC
            """)
        
        projects = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(projects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new work order project"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert project
        cursor.execute("""
            INSERT INTO work_order_projects (
                project_name, project_description, project_type, client_name, client_type,
                start_date, end_date, duration_weeks, scope_description, team_size, my_role,
                key_achievements, technologies_used, skills_demonstrated, include_in_resume,
                priority_level, target_job_types, project_summary, challenges_overcome,
                business_impact, lessons_learned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['project_name'], data.get('project_description', ''),
            data.get('project_type', 'support'), data.get('client_name', ''),
            data.get('client_type', 'enterprise'), data.get('start_date'),
            data.get('end_date'), data.get('duration_weeks'),
            data.get('scope_description', ''), data.get('team_size', 1),
            data.get('my_role', 'Technical Specialist'),
            json.dumps(data.get('key_achievements', [])),
            json.dumps(data.get('technologies_used', [])),
            json.dumps(data.get('skills_demonstrated', [])),
            data.get('include_in_resume', True), data.get('priority_level', 3),
            json.dumps(data.get('target_job_types', [])),
            data.get('project_summary', ''), data.get('challenges_overcome', ''),
            data.get('business_impact', ''), data.get('lessons_learned', '')
        ))
        
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': project_id, 'message': 'Project created successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a work order project"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update project
        update_fields = []
        params = []
        
        for field in ['project_name', 'project_description', 'project_type', 'client_name', 
                     'client_type', 'start_date', 'end_date', 'duration_weeks', 
                     'scope_description', 'team_size', 'my_role', 'include_in_resume',
                     'priority_level', 'project_summary', 'challenges_overcome',
                     'business_impact', 'lessons_learned']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        # Handle JSON fields
        for field in ['key_achievements', 'technologies_used', 'skills_demonstrated', 
                     'locations_served', 'target_job_types']:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(json.dumps(data[field]))
        
        if update_fields:
            params.append(datetime.now().isoformat())
            params.append(project_id)
            
            query = f"UPDATE work_order_projects SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return jsonify({'message': 'Project updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/work-orders', methods=['POST'])
def assign_work_orders_to_project(project_id):
    """Assign work orders to a project"""
    try:
        data = request.json
        work_order_ids = data.get('work_order_ids', [])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if project exists
        cursor.execute("SELECT id FROM work_order_projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Project not found'}), 404
        
        # Assign work orders
        assigned = 0
        for wo_id in work_order_ids:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO work_order_project_assignments 
                    (work_order_id, project_id, role_in_project)
                    VALUES (?, ?, ?)
                """, (wo_id, project_id, data.get('role_in_project', 'Primary')))
                assigned += 1
            except Exception as e:
                print(f"Error assigning work order {wo_id}: {e}")
        
        # Update project metrics
        cursor.execute("""
            UPDATE work_order_projects 
            SET total_work_orders = (
                SELECT COUNT(*) FROM work_order_project_assignments 
                WHERE project_id = ?
            ),
            total_earnings = COALESCE((
                SELECT SUM(wo.pay_amount) 
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ?
            ), 0),
            avg_rating = COALESCE((
                SELECT AVG(wo.wo_rating) 
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ? AND wo.wo_rating IS NOT NULL
            ), 0)
            WHERE id = ?
        """, (project_id, project_id, project_id, project_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Assigned {assigned} work orders to project',
            'assigned_count': assigned
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/work-orders/<int:work_order_id>', methods=['DELETE'])
def remove_work_order_from_project(project_id, work_order_id):
    """Remove a work order from a project"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM work_order_project_assignments 
            WHERE project_id = ? AND work_order_id = ?
        """, (project_id, work_order_id))
        
        # Update project metrics
        cursor.execute("""
            UPDATE work_order_projects 
            SET total_work_orders = (
                SELECT COUNT(*) FROM work_order_project_assignments 
                WHERE project_id = ?
            ),
            total_earnings = COALESCE((
                SELECT SUM(wo.pay_amount) 
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ?
            ), 0)
            WHERE id = ?
        """, (project_id, project_id, project_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Work order removed from project'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/auto-create', methods=['POST'])
def auto_create_projects():
    """Automatically create projects based on work order patterns"""
    try:
        data = request.json
        grouping_criteria = data.get('criteria', 'company_and_timeframe')  # company_and_timeframe, technology, location
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        created_projects = []
        
        if grouping_criteria == 'company_and_timeframe':
            # Group by company and 3-month periods
            cursor.execute("""
                SELECT company_name, 
                       strftime('%Y', service_date) as year,
                       (CAST(strftime('%m', service_date) AS INTEGER) - 1) / 3 as quarter,
                       COUNT(*) as work_order_count,
                       MIN(service_date) as start_date,
                       MAX(service_date) as end_date,
                       SUM(pay_amount) as total_earnings,
                       GROUP_CONCAT(DISTINCT work_category) as categories,
                       GROUP_CONCAT(DISTINCT state) as states
                FROM work_orders wo
                LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
                WHERE wopa.work_order_id IS NULL AND service_date IS NOT NULL
                GROUP BY company_name, year, quarter
                HAVING work_order_count >= 3
                ORDER BY company_name, year, quarter
            """)
            
            for row in cursor.fetchall():
                row_dict = dict(row)
                quarter_name = f"Q{row_dict['quarter'] + 1} {row_dict['year']}"
                
                # Create project
                cursor.execute("""
                    INSERT INTO work_order_projects (
                        title, company_name, work_type, client_type, total_work_orders
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    f"{row_dict['company_name']} - {quarter_name} Support",
                    row_dict['company_name'],
                    "support",
                    "enterprise",
                    row_dict['work_order_count']
                ))
                
                project_id = cursor.lastrowid
                created_projects.append({
                    'id': project_id,
                    'name': f"{row_dict['company_name']} - {quarter_name} Support",
                    'work_order_count': row_dict['work_order_count']
                })
                
                # Assign work orders to project
                cursor.execute("""
                    INSERT INTO work_order_project_assignments (work_order_id, project_id, role_in_project)
                    SELECT wo.id, ?, 'Primary'
                    FROM work_orders wo
                    WHERE wo.company_name = ? 
                    AND strftime('%Y', wo.service_date) = ?
                    AND (CAST(strftime('%m', wo.service_date) AS INTEGER) - 1) / 3 = ?
                    AND wo.id NOT IN (SELECT work_order_id FROM work_order_project_assignments)
                """, (project_id, row_dict['company_name'], row_dict['year'], row_dict['quarter']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Created {len(created_projects)} projects automatically',
            'projects': created_projects
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/auto-create-by-title', methods=['POST'])
def auto_create_projects_by_title():
    """Auto-create projects by grouping work orders with the same title"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get work orders grouped by title
        cursor.execute("""
            SELECT title, COUNT(*) as order_count, 
                   MIN(id) as first_order_id,
                   GROUP_CONCAT(id) as work_order_ids,
                   company_name,
                   work_category,
                   work_type
            FROM work_orders 
            WHERE title IS NOT NULL AND title != ''
            GROUP BY title 
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
        """)
        
        title_groups = cursor.fetchall()
        created_projects = 0
        
        for group in title_groups:
            title = group['title']
            work_order_ids = [int(id) for id in group['work_order_ids'].split(',')]
            company_name = group['company_name']
            work_category = group['work_category']
            work_type = group['work_type']
            
            # Check if project already exists for this title
            cursor.execute("SELECT id FROM work_order_projects WHERE title = ?", (title,))
            existing_project = cursor.fetchone()
            
            if not existing_project:
                # Create project description based on work orders
                project_description = f"Project encompassing {group['order_count']} similar work orders: {title}"
                if work_category:
                    project_description += f" (Category: {work_category})"
                
                # Create new project
                cursor.execute("""
                    INSERT INTO work_order_projects (title, company_name, work_category, 
                                                   work_type, client_type, total_work_orders)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    title,
                    company_name,
                    work_category,
                    work_type,
                    None,  # client_type not available in this query
                    group['order_count']
                ))
                
                project_id = cursor.lastrowid
                
                # Associate work orders with the project
                for work_order_id in work_order_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO work_order_project_assignments (project_id, work_order_id)
                        VALUES (?, ?)
                    """, (project_id, work_order_id))
                
                created_projects += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Successfully created {created_projects} projects by grouping work orders with the same title',
            'created_count': created_projects,
            'grouped_titles': len(title_groups)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ENHANCED JOB MATCHING WITH WORK ORDERS AND PROJECTS

@app.route('/api/job-matcher/enhanced', methods=['POST'])
def enhanced_job_matcher():
    """Enhanced job matching that includes work orders and projects"""
    try:
        data = request.json
        job_description = data.get('job_description', '')
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get regular resume components
        cursor.execute("""
            SELECT rc.*, st.name as section_type_name
            FROM resume_components rc
            JOIN section_types st ON rc.section_type_id = st.id
        """)
        components = [dict(row) for row in cursor.fetchall()]
        
        # Get work items (individual work orders and projects)
        cursor.execute("SELECT * FROM resume_ready_work_items")
        work_items = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Extract keywords from job description
        keywords = extract_keywords(job_description)
        
        # Match components
        component_matches = match_items_to_job(job_description, components, 'component')
        
        # Match work items (work orders and projects)
        work_matches = match_items_to_job(job_description, work_items, 'work_item')
        
        return jsonify({
            'keywords': keywords,
            'component_matches': component_matches[:10],
            'work_order_matches': [m for m in work_matches if m['item']['item_type'] == 'work_order'][:10],
            'project_matches': [m for m in work_matches if m['item']['item_type'] == 'project'][:5],
            'total_matches': len(component_matches) + len(work_matches)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def match_items_to_job(job_description, items, item_type):
    """Match items (components or work items) to job description"""
    keywords = extract_keywords(job_description)
    matches = []
    
    for item in items:
        score = 0
        total_keywords = len(keywords)
        
        # Create searchable text based on item type
        if item_type == 'component':
            searchable_text = f"{item['title']} {item['content']} {item.get('keywords', '')}".lower()
        else:  # work_item
            searchable_text = f"{item['title']} {item.get('description', '')} {item.get('technologies_used', '')} {item.get('skills_demonstrated', '')}".lower()
        
        # Count keyword matches
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in searchable_text:
                score += 1
                matched_keywords.append(keyword)
        
        # Bonus scoring for exact phrase matches
        job_lower = job_description.lower()
        if item_type == 'work_item':
            # Bonus for technology matches
            if item.get('technologies_used'):
                technologies = json.loads(item['technologies_used']) if isinstance(item['technologies_used'], str) else item['technologies_used']
                for tech in technologies:
                    if tech.lower() in job_lower:
                        score += 2
            
            # Bonus for skill matches
            if item.get('skills_demonstrated'):
                skills = json.loads(item['skills_demonstrated']) if isinstance(item['skills_demonstrated'], str) else item['skills_demonstrated']
                for skill in skills:
                    if skill.lower() in job_lower:
                        score += 1.5
        
        if score > 0:
            match_percentage = min(100, int((score / max(total_keywords, 1)) * 100))
            matches.append({
                'item': item,
                'score': score,
                'match_percentage': match_percentage,
                'matched_keywords': matched_keywords,
                'item_type': item_type
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches

@app.route('/api/projects/resume-components', methods=['GET'])
def generate_resume_components_from_projects():
    """Generate resume components from projects"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM project_portfolio ORDER BY priority_level, actual_end_date DESC")
        projects = [dict(row) for row in cursor.fetchall()]
        
        components = []
        
        for project in projects:
            # Parse JSON fields
            technologies = json.loads(project['technologies_used']) if project['technologies_used'] else []
            skills = json.loads(project['skills_demonstrated']) if project['skills_demonstrated'] else []
            achievements = json.loads(project['key_achievements']) if project['key_achievements'] else []
            
            # Create project component
            title = f"Project: {project['title']}"
            if project['company_name']:
                title += f" - {project['company_name']}"
            
            content = f"Project with {project['total_work_orders']} work orders in {project['work_category'] or 'various'} category"
            
            # Add project details
            if project['my_role']:
                content += f"\nRole: {project['my_role']}"
            if project['actual_work_orders']:
                content += f"\nCompleted {project['actual_work_orders']} work orders"
            if project['actual_earnings']:
                content += f"\nProject value: ${project['actual_earnings']:,.2f}"
            if achievements:
                content += f"\nKey achievements: {', '.join(achievements)}"
            if project['business_impact']:
                content += f"\nBusiness impact: {project['business_impact']}"
            
            # Keywords from technologies, skills, and project type
            keywords = technologies + skills + [project['project_type'], project['client_type']]
            keywords = [k for k in keywords if k]
            
            component = {
                'title': title,
                'content': content,
                'section_type': 'projects',
                'keywords': keywords,
                'industry_tags': [project['client_type']] if project['client_type'] else [],
                'source': 'fieldnation_project',
                'source_id': project['id']
            }
            
            components.append(component)
        
        conn.close()
        return jsonify(components)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_keywords(text: str) -> list:
    """Extract keywords from text - simplified version"""
    import re
    
    # Remove common words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'will', 'would',
        'should', 'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'our', 'your', 'their', 'his', 'her', 'its'
    }
    
    # Extract words (2+ characters, alphanumeric)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    
    # Filter out stop words and get unique keywords
    keywords = list(set([word for word in words if word not in stop_words]))
    
    # Sort by frequency in text
    keyword_freq = [(word, text.lower().count(word)) for word in keywords]
    keyword_freq.sort(key=lambda x: x[1], reverse=True)
    
    return [word for word, freq in keyword_freq[:50]]  # Return top 50 keywords 