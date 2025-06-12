#!/usr/bin/env python
"""
Enhanced Work Order Endpoints
Additional Flask endpoints for comprehensive work order management and job matching
"""

from flask import jsonify, request
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkOrderMatchingEngine:
    """Advanced job matching engine for work orders"""
    
    def __init__(self, db_path: str = 'resume_database.db', semantic_model=None):
        self.db_path = db_path
        self.semantic_model = semantic_model
        
    def get_db_connection(self):
        """Create and return a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def match_job_to_work_orders(self, job_description: str, limit: int = 20) -> List[Dict]:
        """Match a job description to relevant work orders"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get all work orders
            cursor.execute("""
                SELECT * FROM fieldnation_work_orders 
                WHERE include_in_resume = 1
                ORDER BY service_date DESC
            """)
            
            work_orders = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            # Calculate match scores
            scored_work_orders = []
            
            for wo in work_orders:
                score = self._calculate_match_score(job_description, wo)
                wo['match_score'] = score
                wo['match_reasons'] = self._get_match_reasons(job_description, wo)
                scored_work_orders.append(wo)
            
            # Sort by match score and return top results
            scored_work_orders.sort(key=lambda x: x['match_score'], reverse=True)
            return scored_work_orders[:limit]
            
        except Exception as e:
            logger.error(f"Error matching job to work orders: {e}")
            return []

    def _calculate_match_score(self, job_description: str, work_order: Dict) -> float:
        """Calculate match score between job description and work order"""
        score = 0.0
        
        # Combine work order text for analysis
        wo_text = f"""
        {work_order.get('title', '')} 
        {work_order.get('work_description', '')} 
        {work_order.get('service_description', '')}
        {work_order.get('required_skills', '')}
        {work_order.get('technologies_used', '')}
        {work_order.get('required_tools', '')}
        """
        
        # Semantic similarity (if available)
        if self.semantic_model:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                job_embedding = self.semantic_model.encode([job_description])
                wo_embedding = self.semantic_model.encode([wo_text])
                semantic_score = cosine_similarity(job_embedding, wo_embedding)[0][0]
                score += semantic_score * 0.4  # 40% weight for semantic similarity
            except Exception as e:
                logger.warning(f"Semantic matching failed: {e}")
        
        # Keyword matching
        keyword_score = self._calculate_keyword_score(job_description, wo_text)
        score += keyword_score * 0.3  # 30% weight for keywords
        
        # Industry relevance
        industry_score = self._calculate_industry_score(job_description, work_order)
        score += industry_score * 0.15  # 15% weight for industry
        
        # Technical skills matching
        tech_score = self._calculate_technical_score(job_description, work_order)
        score += tech_score * 0.15  # 15% weight for technical skills
        
        return min(score, 1.0)  # Cap at 1.0

    def _calculate_keyword_score(self, job_description: str, work_order_text: str) -> float:
        """Calculate keyword-based matching score"""
        job_keywords = set(self._extract_keywords(job_description.lower()))
        wo_keywords = set(self._extract_keywords(work_order_text.lower()))
        
        if not job_keywords:
            return 0.0
        
        common_keywords = job_keywords.intersection(wo_keywords)
        return len(common_keywords) / len(job_keywords)

    def _calculate_industry_score(self, job_description: str, work_order: Dict) -> float:
        """Calculate industry relevance score"""
        job_desc_lower = job_description.lower()
        wo_industry = work_order.get('industry_category', '').lower()
        wo_company = work_order.get('buyer_company', '').lower()
        
        # Industry patterns
        industry_keywords = {
            'healthcare': ['healthcare', 'hospital', 'medical', 'clinic', 'patient'],
            'retail': ['retail', 'store', 'pos', 'customer', 'sales'],
            'financial': ['bank', 'financial', 'credit', 'loan', 'investment'],
            'education': ['school', 'university', 'education', 'student', 'campus'],
            'government': ['government', 'federal', 'state', 'municipal'],
            'technology': ['tech', 'software', 'it', 'computer', 'data']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in job_desc_lower for keyword in keywords):
                if industry in wo_industry or any(keyword in wo_company for keyword in keywords):
                    return 1.0
        
        return 0.5  # Default neutral score

    def _calculate_technical_score(self, job_description: str, work_order: Dict) -> float:
        """Calculate technical skills matching score"""
        job_desc_lower = job_description.lower()
        
        # Extract technical requirements from work order
        required_skills = json.loads(work_order.get('required_skills', '[]')) if work_order.get('required_skills') else []
        technologies = json.loads(work_order.get('technologies_used', '[]')) if work_order.get('technologies_used') else []
        tools = json.loads(work_order.get('required_tools', '[]')) if work_order.get('required_tools') else []
        
        all_tech_items = required_skills + technologies + tools
        
        if not all_tech_items:
            return 0.0
        
        matches = 0
        for item in all_tech_items:
            if item.lower() in job_desc_lower:
                matches += 1
        
        return matches / len(all_tech_items)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        import re
        
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must'}
        
        # Extract words (3+ characters, not stop words)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords

    def _get_match_reasons(self, job_description: str, work_order: Dict) -> List[str]:
        """Get specific reasons why this work order matches the job"""
        reasons = []
        
        job_desc_lower = job_description.lower()
        wo_text = f"{work_order.get('work_description', '')} {work_order.get('title', '')}".lower()
        
        # Check for technology matches
        technologies = json.loads(work_order.get('technologies_used', '[]')) if work_order.get('technologies_used') else []
        for tech in technologies:
            if tech.lower() in job_desc_lower:
                reasons.append(f"Experience with {tech}")
        
        # Check for skill matches
        skills = json.loads(work_order.get('required_skills', '[]')) if work_order.get('required_skills') else []
        for skill in skills:
            if skill.lower() in job_desc_lower:
                reasons.append(f"Demonstrated {skill}")
        
        # Check for industry match
        industry = work_order.get('industry_category', '')
        if industry.lower() in job_desc_lower:
            reasons.append(f"{industry} industry experience")
        
        # Check for common keywords
        common_terms = ['installation', 'configuration', 'troubleshooting', 'support', 'maintenance']
        for term in common_terms:
            if term in job_desc_lower and term in wo_text:
                reasons.append(f"{term.title()} experience")
        
        return reasons[:5]  # Limit to top 5 reasons


# Flask endpoint functions to be added to the main app

def add_work_order_endpoints(app, db_path='resume_database.db'):
    """Add work order management endpoints to Flask app"""
    
    matching_engine = WorkOrderMatchingEngine(db_path)
    
    @app.route('/api/work-orders/import-all', methods=['POST'])
    def import_all_work_orders():
        """Import all work orders from markdown and PDF files"""
        try:
            from comprehensive_fieldnation_processor import ComprehensiveFieldNationProcessor
            
            processor = ComprehensiveFieldNationProcessor(db_path)
            results = processor.process_all_files()
            
            return jsonify({
                'success': True,
                'message': 'Work orders imported successfully',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error importing work orders: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/work-orders/fieldnation', methods=['GET'])
    def get_fieldnation_work_orders():
        """Get all FieldNation work orders with filtering and pagination"""
        try:
            # Get query parameters
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            company_filter = request.args.get('company', '')
            industry_filter = request.args.get('industry', '')
            work_type_filter = request.args.get('work_type', '')
            location_filter = request.args.get('location', '')
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query with filters
            where_conditions = []
            params = []
            
            if company_filter:
                where_conditions.append("buyer_company LIKE ?")
                params.append(f"%{company_filter}%")
            
            if industry_filter:
                where_conditions.append("industry_category = ?")
                params.append(industry_filter)
            
            if work_type_filter:
                where_conditions.append("work_type = ?")
                params.append(work_type_filter)
            
            if location_filter:
                where_conditions.append("location LIKE ?")
                params.append(f"%{location_filter}%")
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM fieldnation_work_orders{where_clause}", params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            offset = (page - 1) * per_page
            cursor.execute(f"""
                SELECT * FROM fieldnation_work_orders{where_clause}
                ORDER BY service_date DESC
                LIMIT ? OFFSET ?
            """, params + [per_page, offset])
            
            work_orders = []
            for row in cursor.fetchall():
                wo = dict(row)
                # Parse JSON fields
                for field in ['required_skills', 'technologies_used', 'required_tools', 'achievements']:
                    if wo.get(field):
                        try:
                            wo[field] = json.loads(wo[field])
                        except:
                            wo[field] = []
                work_orders.append(wo)
            
            conn.close()
            
            return jsonify({
                'success': True,
                'work_orders': work_orders,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting work orders: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/work-orders/fieldnation/<int:work_order_id>', methods=['GET'])
    def get_fieldnation_work_order_details(work_order_id):
        """Get detailed information for a specific work order"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM fieldnation_work_orders WHERE id = ?", (work_order_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({
                    'success': False,
                    'error': 'Work order not found'
                }), 404
            
            work_order = dict(row)
            
            # Parse JSON fields
            json_fields = [
                'required_skills', 'technologies_used', 'required_tools', 
                'work_order_qualifications', 'challenges_encountered', 
                'solutions_implemented', 'achievements', 'deliverables',
                'certifications_required', 'resume_bullet_points'
            ]
            
            for field in json_fields:
                if work_order.get(field):
                    try:
                        work_order[field] = json.loads(work_order[field])
                    except:
                        work_order[field] = [] if field.endswith('s') else {}
            
            conn.close()
            
            return jsonify({
                'success': True,
                'work_order': work_order
            })
            
        except Exception as e:
            logger.error(f"Error getting work order details: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/work-orders/job-match', methods=['POST'])
    def match_job_to_work_orders():
        """Match a job description to relevant work orders"""
        try:
            data = request.get_json()
            job_description = data.get('job_description', '')
            limit = data.get('limit', 20)
            
            if not job_description:
                return jsonify({
                    'success': False,
                    'error': 'Job description is required'
                }), 400
            
            # Load semantic model if available
            try:
                from sentence_transformers import SentenceTransformer
                semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
                matching_engine.semantic_model = semantic_model
            except:
                logger.warning("Semantic model not available, using keyword matching only")
            
            matches = matching_engine.match_job_to_work_orders(job_description, limit)
            
            return jsonify({
                'success': True,
                'matches': matches,
                'total_matches': len(matches)
            })
            
        except Exception as e:
            logger.error(f"Error matching job to work orders: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/work-orders/stats', methods=['GET'])
    def get_fieldnation_stats():
        """Get comprehensive statistics about FieldNation work orders"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Basic counts
            cursor.execute("SELECT COUNT(*) as total FROM fieldnation_work_orders")
            total_work_orders = cursor.fetchone()[0]
            
            # Industry breakdown
            cursor.execute("""
                SELECT industry_category, COUNT(*) as count 
                FROM fieldnation_work_orders 
                WHERE industry_category IS NOT NULL 
                GROUP BY industry_category 
                ORDER BY count DESC
            """)
            industry_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # Company breakdown
            cursor.execute("""
                SELECT buyer_company, COUNT(*) as count, AVG(pay_amount) as avg_pay
                FROM fieldnation_work_orders 
                WHERE buyer_company IS NOT NULL 
                GROUP BY buyer_company 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_companies = [dict(row) for row in cursor.fetchall()]
            
            # Financial stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as paid_orders,
                    SUM(pay_amount) as total_earnings,
                    AVG(pay_amount) as avg_pay,
                    MIN(pay_amount) as min_pay,
                    MAX(pay_amount) as max_pay
                FROM fieldnation_work_orders 
                WHERE pay_amount IS NOT NULL AND pay_amount > 0
            """)
            financial_stats = dict(cursor.fetchone())
            
            # Complexity distribution
            cursor.execute("""
                SELECT complexity_level, COUNT(*) as count 
                FROM fieldnation_work_orders 
                WHERE complexity_level IS NOT NULL 
                GROUP BY complexity_level
            """)
            complexity_distribution = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_work_orders': total_work_orders,
                    'industry_breakdown': industry_breakdown,
                    'top_companies': top_companies,
                    'financial_stats': financial_stats,
                    'complexity_distribution': complexity_distribution
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting FieldNation stats: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/work-orders/markdown/<int:work_order_id>', methods=['GET'])
    def get_showcase_markdown_work_order(work_order_id):
        """Get detailed markdown work order data for showcase"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM work_orders_markdown 
                WHERE work_order_id = ?
            """, (work_order_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return jsonify(dict(row))
            else:
                return jsonify({'error': 'Work order not found'}), 404
                
        except Exception as e:
            logger.error(f"Error getting markdown work order {work_order_id}: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/work-orders/pdf/<int:work_order_id>', methods=['GET'])
    def get_showcase_pdf_work_order(work_order_id):
        """Get detailed PDF work order data for showcase"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM work_orders_pdf 
                WHERE work_order_id = ?
            """, (work_order_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return jsonify(dict(row))
            else:
                return jsonify({'error': 'Work order not found'}), 404
                
        except Exception as e:
            logger.error(f"Error getting PDF work order {work_order_id}: {e}")
            return jsonify({'error': str(e)}), 500 