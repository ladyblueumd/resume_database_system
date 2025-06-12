#!/usr/bin/env python3
"""
Demo: Work Order Projects and Job Description Matching
Shows how to group work orders into projects and match them to job descriptions
"""

import sqlite3
import json
from datetime import datetime, timedelta
import random

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('resume_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_sample_projects():
    """Create sample projects from existing work orders"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔄 Creating sample projects from work orders...")
    
    # Sample project configurations
    sample_projects = [
        {
            'project_name': 'PIVITAL Enterprise Desktop Deployment Q2 2024',
            'project_description': 'Large-scale desktop deployment and configuration project for PIVITAL across multiple locations',
            'project_type': 'deployment',
            'client_name': 'PIVITAL',
            'client_type': 'enterprise',
            'my_role': 'Lead Desktop Support Technician',
            'key_achievements': [
                'Successfully deployed 150+ workstations',
                'Reduced average deployment time by 35%',
                'Achieved 98% client satisfaction rating',
                'Implemented standardized imaging process'
            ],
            'technologies_used': ['Windows 10', 'Active Directory', 'Group Policy', 'Imaging Software'],
            'skills_demonstrated': ['Project Management', 'Technical Leadership', 'System Deployment', 'Client Communication'],
            'priority_level': 1,
            'project_summary': 'Led enterprise desktop deployment serving 150+ workstations with 98% satisfaction rating',
            'business_impact': 'Improved productivity through standardized deployment process and reduced setup time'
        },
        {
            'project_name': 'AVT Technology Multi-Site Support Initiative',
            'project_description': 'Comprehensive technical support services across multiple retail locations for AVT Technology',
            'project_type': 'support',
            'client_name': 'AVT Technology Solutions LLC',
            'client_type': 'retail',
            'my_role': 'Field Support Specialist',
            'key_achievements': [
                'Completed 100+ support tickets across 50+ locations',
                'Maintained 95% first-call resolution rate',
                'Reduced average response time by 40%'
            ],
            'technologies_used': ['POS Systems', 'Network Hardware', 'Windows', 'Printers'],
            'skills_demonstrated': ['Field Support', 'Troubleshooting', 'Customer Service', 'Hardware Maintenance'],
            'priority_level': 2,
            'project_summary': 'Provided field support across 50+ retail locations with 95% first-call resolution',
            'business_impact': 'Minimized downtime and improved customer experience through rapid issue resolution'
        },
        {
            'project_name': 'Healthcare Technology Modernization - Multiple Providers',
            'project_description': 'Medical device setup and IT infrastructure support for healthcare providers',
            'project_type': 'infrastructure',
            'client_name': 'Various Healthcare Providers',
            'client_type': 'healthcare',
            'my_role': 'Healthcare IT Specialist',
            'key_achievements': [
                'Configured 25+ medical workstations',
                'Implemented HIPAA-compliant security measures',
                'Zero data security incidents'
            ],
            'technologies_used': ['Medical Carts', 'HIPAA Compliance', 'Healthcare Software', 'Network Security'],
            'skills_demonstrated': ['Healthcare IT', 'Security Implementation', 'Compliance Management', 'Medical Equipment'],
            'priority_level': 1,
            'project_summary': 'Healthcare IT modernization with HIPAA compliance and zero security incidents',
            'business_impact': 'Enhanced patient care through reliable technology infrastructure'
        }
    ]
    
    created_projects = []
    
    for project_data in sample_projects:
        try:
            # Insert project
            cursor.execute("""
                INSERT INTO work_order_projects (
                    project_name, project_description, project_type, client_name, client_type,
                    my_role, key_achievements, technologies_used, skills_demonstrated,
                    include_in_resume, priority_level, project_summary, business_impact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_data['project_name'],
                project_data['project_description'],
                project_data['project_type'],
                project_data['client_name'],
                project_data['client_type'],
                project_data['my_role'],
                json.dumps(project_data['key_achievements']),
                json.dumps(project_data['technologies_used']),
                json.dumps(project_data['skills_demonstrated']),
                True,  # include_in_resume
                project_data['priority_level'],
                project_data['project_summary'],
                project_data['business_impact']
            ))
            
            project_id = cursor.lastrowid
            created_projects.append({
                'id': project_id,
                'name': project_data['project_name'],
                'client': project_data['client_name']
            })
            
            print(f"   ✅ Created project: {project_data['project_name']}")
            
        except Exception as e:
            print(f"   ❌ Error creating project {project_data['project_name']}: {e}")
    
    conn.commit()
    conn.close()
    
    return created_projects

def assign_work_orders_to_projects():
    """Automatically assign work orders to projects based on company matching"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔗 Assigning work orders to projects...")
    
    # Get all projects
    cursor.execute("SELECT id, project_name, client_name FROM work_order_projects")
    projects = [dict(row) for row in cursor.fetchall()]
    
    assignments_made = 0
    
    for project in projects:
        # Find work orders that match this project's client
        if project['client_name']:
            cursor.execute("""
                SELECT id, title, company_name, pay_amount
                FROM work_orders 
                WHERE company_name LIKE ? 
                AND id NOT IN (SELECT work_order_id FROM work_order_project_assignments)
                LIMIT 20
            """, (f"%{project['client_name']}%",))
            
            matching_work_orders = cursor.fetchall()
            
            for wo in matching_work_orders:
                try:
                    cursor.execute("""
                        INSERT INTO work_order_project_assignments 
                        (work_order_id, project_id, role_in_project)
                        VALUES (?, ?, ?)
                    """, (wo['id'], project['id'], 'Primary'))
                    assignments_made += 1
                except Exception as e:
                    print(f"   ⚠️  Could not assign WO {wo['id']}: {e}")
            
            print(f"   ✅ Assigned {len(matching_work_orders)} work orders to '{project['project_name']}'")
    
    # Update project metrics
    for project in projects:
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
            ), 0),
            start_date = (
                SELECT MIN(wo.service_date)
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ?
            ),
            end_date = (
                SELECT MAX(wo.service_date)
                FROM work_order_project_assignments wopa
                JOIN work_orders wo ON wopa.work_order_id = wo.id
                WHERE wopa.project_id = ?
            )
            WHERE id = ?
        """, (project['id'], project['id'], project['id'], project['id'], project['id'], project['id']))
    
    conn.commit()
    conn.close()
    
    print(f"   📊 Total assignments made: {assignments_made}")
    return assignments_made

def test_job_matching():
    """Test job description matching with sample job postings"""
    print("\n🎯 Testing Job Description Matching")
    print("=" * 60)
    
    # Sample job descriptions for testing
    sample_jobs = [
        {
            'title': 'Desktop Support Technician',
            'company': 'TechCorp Solutions',
            'description': """
            We are seeking a Desktop Support Technician to provide technical support for Windows 10 
            workstations, deploy new systems, and manage Active Directory user accounts. Experience 
            with imaging software, Group Policy, and project management is preferred. The role involves 
            working with enterprise clients and managing large-scale deployments.
            
            Requirements:
            - 3+ years Windows 10 support experience
            - Active Directory and Group Policy knowledge
            - Experience with system imaging and deployment
            - Strong project management skills
            - Enterprise environment experience
            - Excellent client communication skills
            """
        },
        {
            'title': 'Field Service Technician',
            'company': 'Retail Solutions Inc',
            'description': """
            Field Service Technician needed to support POS systems, printers, and network equipment 
            across multiple retail locations. Must have experience with troubleshooting hardware 
            issues, maintaining high customer satisfaction, and working independently in the field.
            
            Requirements:
            - POS system experience
            - Printer and network hardware troubleshooting
            - Field support experience
            - Strong customer service skills
            - Ability to travel to multiple locations
            - Hardware maintenance expertise
            """
        },
        {
            'title': 'Healthcare IT Specialist',
            'company': 'MedTech Healthcare',
            'description': """
            Healthcare IT Specialist to support medical workstations, implement HIPAA compliance 
            measures, and manage healthcare technology infrastructure. Experience with medical 
            equipment and healthcare software required.
            
            Requirements:
            - Healthcare IT experience
            - HIPAA compliance knowledge
            - Medical equipment configuration
            - Healthcare software support
            - Security implementation experience
            - Medical environment familiarity
            """
        }
    ]
    
    conn = get_db_connection()
    
    for i, job in enumerate(sample_jobs, 1):
        print(f"\n{i}. Testing Job: {job['title']} at {job['company']}")
        print("-" * 50)
        
        # Get matching data
        matches = match_job_to_work_items(job['description'], conn)
        
        print(f"📝 Components found: {len(matches['components'])}")
        print(f"🔧 Work orders found: {len(matches['work_orders'])}")
        print(f"📁 Projects found: {len(matches['projects'])}")
        
        # Show top matches
        if matches['projects']:
            print("\n🏆 Top Project Matches:")
            for match in matches['projects'][:2]:
                print(f"   • {match['title']} (Match: {match['match_percentage']}%)")
                print(f"     {match['value_metric']}")
        
        if matches['work_orders']:
            print("\n🔧 Top Work Order Matches:")
            for match in matches['work_orders'][:3]:
                print(f"   • {match['title']} (Match: {match['match_percentage']}%)")
                print(f"     {match['client_name']} - {match['value_metric']}")
    
    conn.close()

def match_job_to_work_items(job_description, conn):
    """Match job description to work items (components, work orders, projects)"""
    cursor = conn.cursor()
    
    # Extract simple keywords
    keywords = extract_simple_keywords(job_description)
    
    # Get resume components
    cursor.execute("""
        SELECT rc.*, st.name as section_type_name
        FROM resume_components rc
        JOIN section_types st ON rc.section_type_id = st.id
    """)
    components = [dict(row) for row in cursor.fetchall()]
    
    # Get work items from the view
    cursor.execute("SELECT * FROM resume_ready_work_items")
    work_items = [dict(row) for row in cursor.fetchall()]
    
    # Match each type
    component_matches = match_items_to_keywords(components, keywords, 'component')
    work_item_matches = match_items_to_keywords(work_items, keywords, 'work_item')
    
    # Separate work orders and projects
    work_order_matches = [m for m in work_item_matches if m['item_type'] == 'work_order']
    project_matches = [m for m in work_item_matches if m['item_type'] == 'project']
    
    return {
        'components': component_matches,
        'work_orders': work_order_matches,
        'projects': project_matches,
        'keywords': keywords
    }

def match_items_to_keywords(items, keywords, item_type):
    """Match items to keywords and return scored results"""
    matches = []
    
    for item in items:
        score = 0
        matched_keywords = []
        
        # Create searchable text based on item type
        if item_type == 'component':
            searchable_text = f"{item['title']} {item['content']} {item.get('keywords', '')}".lower()
        else:  # work_item
            # Parse JSON fields if they're strings
            technologies = item.get('technologies_used', '')
            skills = item.get('skills_demonstrated', '')
            
            if isinstance(technologies, str) and technologies.startswith('['):
                try:
                    technologies = ' '.join(json.loads(technologies))
                except:
                    pass
            
            if isinstance(skills, str) and skills.startswith('['):
                try:
                    skills = ' '.join(json.loads(skills))
                except:
                    pass
            
            searchable_text = f"{item['title']} {item.get('description', '')} {technologies} {skills}".lower()
        
        # Count keyword matches
        for keyword in keywords:
            if keyword.lower() in searchable_text:
                score += 1
                matched_keywords.append(keyword)
        
        if score > 0:
            match_percentage = min(100, int((score / len(keywords)) * 100))
            match = {
                'score': score,
                'match_percentage': match_percentage,
                'matched_keywords': matched_keywords
            }
            
            # Add item-specific fields
            if item_type == 'component':
                match.update({
                    'title': item['title'],
                    'content': item['content'][:150] + '...',
                    'section': item['section_type_name']
                })
            else:
                match.update({
                    'title': item['title'],
                    'client_name': item['client_name'],
                    'category': item['category'],
                    'value_metric': item['value_metric'],
                    'item_type': item['item_type']
                })
            
            matches.append(match)
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches

def extract_simple_keywords(text):
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
    
    return [word for word, freq in keyword_freq[:30]]  # Return top 30 keywords

def show_project_statistics():
    """Display project and work order statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n📊 Project & Work Order Statistics")
    print("=" * 60)
    
    # Project stats
    cursor.execute("SELECT COUNT(*) FROM work_order_projects")
    total_projects = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM work_order_projects WHERE include_in_resume = TRUE")
    resume_projects = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_earnings) FROM work_order_projects")
    total_project_value = cursor.fetchone()[0] or 0
    
    # Work order assignment stats
    cursor.execute("SELECT COUNT(*) FROM work_order_project_assignments")
    assigned_work_orders = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM work_orders wo
        LEFT JOIN work_order_project_assignments wopa ON wo.id = wopa.work_order_id
        WHERE wopa.work_order_id IS NULL
    """)
    unassigned_work_orders = cursor.fetchone()[0]
    
    print(f"📁 Total Projects: {total_projects}")
    print(f"📝 Resume-Ready Projects: {resume_projects}")
    print(f"💰 Total Project Value: ${total_project_value:,.2f}")
    print(f"🔗 Assigned Work Orders: {assigned_work_orders}")
    print(f"❓ Unassigned Work Orders: {unassigned_work_orders}")
    
    # Top projects by value
    cursor.execute("""
        SELECT project_name, client_name, total_earnings, total_work_orders
        FROM work_order_projects 
        WHERE total_earnings > 0
        ORDER BY total_earnings DESC 
        LIMIT 5
    """)
    
    top_projects = cursor.fetchall()
    if top_projects:
        print(f"\n🏆 Top Projects by Value:")
        for project in top_projects:
            print(f"   • {project['project_name']}")
            print(f"     {project['client_name']} - ${project['total_earnings']:,.2f} ({project['total_work_orders']} orders)")
    
    conn.close()

def main():
    """Run the complete demo"""
    print("🚀 Work Order Projects & Job Matching Demo")
    print("=" * 80)
    
    # Step 1: Create sample projects
    created_projects = create_sample_projects()
    print(f"\n✅ Created {len(created_projects)} sample projects")
    
    # Step 2: Assign work orders to projects
    assignments = assign_work_orders_to_projects()
    print(f"\n✅ Made {assignments} work order assignments")
    
    # Step 3: Show statistics
    show_project_statistics()
    
    # Step 4: Test job matching
    test_job_matching()
    
    print("\n🎉 Demo completed!")
    print("\nNext steps:")
    print("1. 📱 Open your resume app and go to the 'Projects' tab")
    print("2. 🎯 Try the 'Enhanced Job Matcher' with real job descriptions")
    print("3. 📄 Generate targeted resumes using matched projects and work orders")
    print("4. 🤖 Use auto-create projects to organize your remaining work orders")

if __name__ == "__main__":
    main() 