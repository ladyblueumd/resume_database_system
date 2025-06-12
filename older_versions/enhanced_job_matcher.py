#!/usr/bin/env python3
"""
Enhanced Job Matcher
Uses comprehensive FieldNation work order data to match with job descriptions
Matches skills, technologies, industries, client types, and experience levels
"""

import sqlite3
import json
import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

@dataclass
class JobMatch:
    """Job matching result"""
    work_order_ids: List[int]
    match_score: float
    matched_skills: List[str]
    matched_technologies: List[str]
    industry_match: bool
    client_type_match: bool
    relevant_experience: str
    suggested_achievements: List[str]
    confidence_level: str

class EnhancedJobMatcher:
    """Enhanced job matcher using comprehensive work order data"""
    
    def __init__(self, db_path: str = 'resume_database.db'):
        self.db_path = db_path
        
    def get_db_connection(self):
        """Create and return a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def analyze_job_description(self, job_description: str) -> Dict[str, List[str]]:
        """Analyze job description to extract requirements"""
        analysis = {
            'required_skills': [],
            'required_technologies': [],
            'preferred_industries': [],
            'client_types': [],
            'experience_level': '',
            'job_functions': [],
            'soft_skills': []
        }
        
        job_desc_lower = job_description.lower()
        
        # Extract required skills
        skill_patterns = {
            'Hardware Installation': ['hardware install', 'equipment setup', 'device deployment'],
            'Troubleshooting': ['troubleshoot', 'diagnose', 'problem solving', 'repair'],
            'Network Administration': ['network admin', 'network support', 'networking', 'lan/wan'],
            'System Configuration': ['system config', 'configuration', 'setup systems'],
            'Customer Service': ['customer service', 'client interaction', 'onsite support'],
            'Project Management': ['project management', 'project coordination', 'manage projects'],
            'Technical Support': ['technical support', 'it support', 'help desk', 'field service'],
            'Documentation': ['documentation', 'technical writing', 'create reports'],
            'Testing & Validation': ['testing', 'validation', 'qa', 'quality assurance'],
            'Security Implementation': ['security', 'access control', 'cybersecurity']
        }
        
        for skill, patterns in skill_patterns.items():
            if any(pattern in job_desc_lower for pattern in patterns):
                analysis['required_skills'].append(skill)
        
        # Extract technologies
        tech_patterns = {
            'Windows': ['windows', 'microsoft windows', 'windows server'],
            'Mac/Apple': ['mac', 'apple', 'macbook', 'ios'],
            'Linux': ['linux', 'unix', 'ubuntu', 'centos'],
            'POS Systems': ['pos', 'point of sale', 'retail systems'],
            'Network Equipment': ['cisco', 'router', 'switch', 'firewall'],
            'Printers': ['printer', 'multifunction', 'xerox', 'hp printer'],
            'VoIP': ['voip', 'phone system', 'telecommunications'],
            'Office 365': ['office 365', 'microsoft 365', 'sharepoint'],
            'Active Directory': ['active directory', 'ad', 'domain'],
            'VMware': ['vmware', 'virtualization', 'virtual machine']
        }
        
        for tech, patterns in tech_patterns.items():
            if any(pattern in job_desc_lower for pattern in patterns):
                analysis['required_technologies'].append(tech)
        
        # Extract industry preferences
        industry_patterns = {
            'Healthcare': ['healthcare', 'medical', 'hospital', 'clinic'],
            'Financial Services': ['banking', 'financial', 'finance', 'insurance'],
            'Retail': ['retail', 'store', 'restaurant', 'hospitality'],
            'Education': ['education', 'school', 'university', 'academic'],
            'Government': ['government', 'federal', 'state', 'public sector'],
            'Technology': ['tech company', 'software', 'it services']
        }
        
        for industry, patterns in industry_patterns.items():
            if any(pattern in job_desc_lower for pattern in patterns):
                analysis['preferred_industries'].append(industry)
        
        # Extract client types
        client_patterns = {
            'Enterprise': ['enterprise', 'corporate', 'large organization'],
            'SMB': ['small business', 'medium business', 'smb'],
            'Healthcare': ['healthcare facility', 'medical practice'],
            'Retail': ['retail environment', 'store operations'],
            'Government': ['government agency', 'public sector']
        }
        
        for client_type, patterns in client_patterns.items():
            if any(pattern in job_desc_lower for pattern in patterns):
                analysis['client_types'].append(client_type)
        
        # Determine experience level
        if any(word in job_desc_lower for word in ['senior', 'lead', 'principal', '5+ years', '7+ years']):
            analysis['experience_level'] = 'Senior'
        elif any(word in job_desc_lower for word in ['mid-level', '3+ years', '3-5 years', 'intermediate']):
            analysis['experience_level'] = 'Intermediate'
        elif any(word in job_desc_lower for word in ['junior', 'entry', '1-2 years', 'associate']):
            analysis['experience_level'] = 'Junior'
        else:
            analysis['experience_level'] = 'Mid-Level'
        
        # Extract job functions
        function_patterns = {
            'Field Service': ['field service', 'onsite', 'field technician'],
            'Help Desk': ['help desk', 'support desk', 'service desk'],
            'System Administrator': ['system admin', 'sysadmin', 'infrastructure'],
            'Network Engineer': ['network engineer', 'network architect'],
            'IT Support': ['it support', 'technical support', 'desktop support']
        }
        
        for function, patterns in function_patterns.items():
            if any(pattern in job_desc_lower for pattern in patterns):
                analysis['job_functions'].append(function)
        
        return analysis

    def find_matching_work_orders(self, job_analysis: Dict[str, List[str]]) -> JobMatch:
        """Find work orders that match job requirements"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get all work orders with their details
        cursor.execute("""
            SELECT 
                id, fn_work_order_id, title, company_name, industry, client_type,
                technologies_used, skills_demonstrated, tools_required,
                complexity_level, pay_amount, time_logged, work_description
            FROM work_orders_enhanced
            WHERE include_in_resume = TRUE
        """)
        
        work_orders = cursor.fetchall()
        conn.close()
        
        if not work_orders:
            return JobMatch([], 0.0, [], [], False, False, "", [], "Low")
        
        # Score each work order
        scored_orders = []
        all_matched_skills = set()
        all_matched_technologies = set()
        industry_matches = 0
        client_type_matches = 0
        
        for wo in work_orders:
            score, matched_skills, matched_techs, industry_match, client_match = self._score_work_order(
                wo, job_analysis
            )
            
            if score > 0:
                scored_orders.append((wo['id'], score, matched_skills, matched_techs))
                all_matched_skills.update(matched_skills)
                all_matched_technologies.update(matched_techs)
                
                if industry_match:
                    industry_matches += 1
                if client_match:
                    client_type_matches += 1
        
        # Sort by score and take top matches
        scored_orders.sort(key=lambda x: x[1], reverse=True)
        top_matches = scored_orders[:10]  # Top 10 matches
        
        if not top_matches:
            return JobMatch([], 0.0, [], [], False, False, "", [], "Low")
        
        # Calculate overall match score
        total_score = sum(score for _, score, _, _ in top_matches)
        avg_score = total_score / len(top_matches)
        
        # Determine confidence level
        confidence = self._calculate_confidence(
            avg_score, len(top_matches), industry_matches, client_type_matches
        )
        
        # Generate relevant experience summary
        experience_summary = self._generate_experience_summary(top_matches, work_orders)
        
        # Generate suggested achievements
        achievements = self._generate_suggested_achievements(top_matches, work_orders)
        
        return JobMatch(
            work_order_ids=[wo_id for wo_id, _, _, _ in top_matches],
            match_score=avg_score,
            matched_skills=list(all_matched_skills),
            matched_technologies=list(all_matched_technologies),
            industry_match=industry_matches > 0,
            client_type_match=client_type_matches > 0,
            relevant_experience=experience_summary,
            suggested_achievements=achievements,
            confidence_level=confidence
        )

    def _score_work_order(self, work_order: sqlite3.Row, job_analysis: Dict[str, List[str]]) -> Tuple[float, List[str], List[str], bool, bool]:
        """Score a single work order against job requirements"""
        score = 0.0
        matched_skills = []
        matched_technologies = []
        
        # Parse JSON fields
        try:
            wo_skills = json.loads(work_order['skills_demonstrated'] or '[]')
            wo_technologies = json.loads(work_order['technologies_used'] or '[]')
        except:
            wo_skills = []
            wo_technologies = []
        
        # Skills matching (40% of score)
        skill_score = 0
        for required_skill in job_analysis['required_skills']:
            for wo_skill in wo_skills:
                if self._skills_match(required_skill, wo_skill):
                    matched_skills.append(wo_skill)
                    skill_score += 1
                    break
        
        if job_analysis['required_skills']:
            skill_score = (skill_score / len(job_analysis['required_skills'])) * 40
        
        # Technology matching (30% of score)
        tech_score = 0
        for required_tech in job_analysis['required_technologies']:
            for wo_tech in wo_technologies:
                if self._technologies_match(required_tech, wo_tech):
                    matched_technologies.append(wo_tech)
                    tech_score += 1
                    break
        
        if job_analysis['required_technologies']:
            tech_score = (tech_score / len(job_analysis['required_technologies'])) * 30
        
        # Industry matching (15% of score)
        industry_match = False
        industry_score = 0
        if job_analysis['preferred_industries']:
            for job_industry in job_analysis['preferred_industries']:
                if self._industry_matches(job_industry, work_order['industry']):
                    industry_match = True
                    industry_score = 15
                    break
        
        # Client type matching (10% of score)
        client_match = False
        client_score = 0
        if job_analysis['client_types']:
            for job_client in job_analysis['client_types']:
                if self._client_type_matches(job_client, work_order['client_type']):
                    client_match = True
                    client_score = 10
                    break
        
        # Complexity bonus (5% of score)
        complexity_score = self._get_complexity_score(work_order['complexity_level'], job_analysis['experience_level'])
        
        total_score = skill_score + tech_score + industry_score + client_score + complexity_score
        
        return total_score, matched_skills, matched_technologies, industry_match, client_match

    def _skills_match(self, job_skill: str, wo_skill: str) -> bool:
        """Check if job skill matches work order skill"""
        job_skill_lower = job_skill.lower()
        wo_skill_lower = wo_skill.lower()
        
        # Direct match
        if job_skill_lower == wo_skill_lower:
            return True
        
        # Partial match
        job_words = set(job_skill_lower.split())
        wo_words = set(wo_skill_lower.split())
        
        # If 60% of words match
        if len(job_words & wo_words) >= 0.6 * len(job_words):
            return True
        
        # Semantic matching
        skill_synonyms = {
            'troubleshooting': ['problem solving', 'diagnose', 'repair'],
            'customer service': ['client interaction', 'customer support'],
            'project management': ['project coordination', 'manage projects'],
            'technical support': ['it support', 'help desk', 'field service']
        }
        
        for main_skill, synonyms in skill_synonyms.items():
            if main_skill in job_skill_lower and any(syn in wo_skill_lower for syn in synonyms):
                return True
            if main_skill in wo_skill_lower and any(syn in job_skill_lower for syn in synonyms):
                return True
        
        return False

    def _technologies_match(self, job_tech: str, wo_tech: str) -> bool:
        """Check if job technology matches work order technology"""
        job_tech_lower = job_tech.lower()
        wo_tech_lower = wo_tech.lower()
        
        # Direct match
        if job_tech_lower == wo_tech_lower:
            return True
        
        # Check for partial matches and synonyms
        tech_mappings = {
            'windows': ['microsoft windows', 'win 10', 'win 11'],
            'mac': ['apple', 'macbook', 'imac'],
            'network equipment': ['cisco', 'router', 'switch', 'networking'],
            'pos systems': ['point of sale', 'retail systems'],
            'printers': ['hp printer', 'xerox', 'multifunction']
        }
        
        for base_tech, variations in tech_mappings.items():
            if (base_tech in job_tech_lower and any(var in wo_tech_lower for var in variations)) or \
               (base_tech in wo_tech_lower and any(var in job_tech_lower for var in variations)):
                return True
        
        return False

    def _industry_matches(self, job_industry: str, wo_industry: str) -> bool:
        """Check if industries match"""
        if not wo_industry:
            return False
        
        job_industry_lower = job_industry.lower()
        wo_industry_lower = wo_industry.lower()
        
        # Direct match
        if job_industry_lower == wo_industry_lower:
            return True
        
        # Industry synonyms
        industry_synonyms = {
            'healthcare': ['medical', 'hospital'],
            'financial services': ['banking', 'financial'],
            'retail': ['restaurant', 'hospitality'],
            'technology': ['it services', 'software']
        }
        
        for base_industry, synonyms in industry_synonyms.items():
            if (base_industry in job_industry_lower and any(syn in wo_industry_lower for syn in synonyms)) or \
               (base_industry in wo_industry_lower and any(syn in job_industry_lower for syn in synonyms)):
                return True
        
        return False

    def _client_type_matches(self, job_client: str, wo_client: str) -> bool:
        """Check if client types match"""
        if not wo_client:
            return False
        
        return job_client.lower() in wo_client.lower() or wo_client.lower() in job_client.lower()

    def _get_complexity_score(self, wo_complexity: str, job_experience: str) -> float:
        """Get complexity score based on experience level match"""
        complexity_levels = {'Basic': 1, 'Intermediate': 2, 'Advanced': 3, 'Expert': 4}
        experience_levels = {'Junior': 1, 'Mid-Level': 2, 'Intermediate': 2, 'Senior': 3}
        
        wo_level = complexity_levels.get(wo_complexity, 2)
        job_level = experience_levels.get(job_experience, 2)
        
        # Perfect match gets full points, close matches get partial points
        if wo_level == job_level:
            return 5.0
        elif abs(wo_level - job_level) == 1:
            return 3.0
        else:
            return 1.0

    def _calculate_confidence(self, avg_score: float, num_matches: int, industry_matches: int, client_matches: int) -> str:
        """Calculate confidence level of the match"""
        confidence_score = 0
        
        # Score contribution
        if avg_score >= 70:
            confidence_score += 3
        elif avg_score >= 50:
            confidence_score += 2
        elif avg_score >= 30:
            confidence_score += 1
        
        # Number of matches
        if num_matches >= 5:
            confidence_score += 2
        elif num_matches >= 3:
            confidence_score += 1
        
        # Industry and client matches
        if industry_matches > 0:
            confidence_score += 1
        if client_matches > 0:
            confidence_score += 1
        
        if confidence_score >= 6:
            return "High"
        elif confidence_score >= 4:
            return "Medium"
        else:
            return "Low"

    def _generate_experience_summary(self, top_matches: List[Tuple], work_orders: List[sqlite3.Row]) -> str:
        """Generate relevant experience summary"""
        wo_dict = {wo['id']: wo for wo in work_orders}
        
        # Collect key statistics
        total_projects = len(top_matches)
        companies = set()
        industries = set()
        total_value = 0
        
        for wo_id, score, _, _ in top_matches:
            if wo_id in wo_dict:
                wo = wo_dict[wo_id]
                companies.add(wo['company_name'])
                if wo['industry']:
                    industries.add(wo['industry'])
                if wo['pay_amount']:
                    total_value += wo['pay_amount']
        
        summary_parts = []
        summary_parts.append(f"Successfully completed {total_projects} relevant projects")
        
        if len(companies) > 1:
            summary_parts.append(f"across {len(companies)} different organizations")
        
        if industries:
            industry_list = ', '.join(list(industries)[:3])
            summary_parts.append(f"in {industry_list} industries")
        
        if total_value > 0:
            summary_parts.append(f"with total project value of ${total_value:,.2f}")
        
        return '. '.join(summary_parts) + '.'

    def _generate_suggested_achievements(self, top_matches: List[Tuple], work_orders: List[sqlite3.Row]) -> List[str]:
        """Generate suggested achievements for resume"""
        wo_dict = {wo['id']: wo for wo in work_orders}
        achievements = []
        
        # Analyze top matches for impressive achievements
        high_value_projects = []
        complex_projects = []
        quick_turnarounds = []
        
        for wo_id, score, _, _ in top_matches[:5]:  # Top 5 matches
            if wo_id in wo_dict:
                wo = wo_dict[wo_id]
                
                # High value projects
                if wo['pay_amount'] and wo['pay_amount'] > 300:
                    high_value_projects.append(wo)
                
                # Complex projects
                if wo['complexity_level'] in ['Advanced', 'Expert']:
                    complex_projects.append(wo)
                
                # Quick projects (less than 2 hours)
                if wo['time_logged'] and wo['time_logged'] < 2:
                    quick_turnarounds.append(wo)
        
        # Generate achievement statements
        if high_value_projects:
            highest_value = max(high_value_projects, key=lambda x: x['pay_amount'] or 0)
            achievements.append(
                f"Successfully completed high-value technical project worth ${highest_value['pay_amount']:,.2f} "
                f"for {highest_value['company_name']}"
            )
        
        if complex_projects:
            achievements.append(
                f"Demonstrated expertise in complex {complex_projects[0]['work_type']} projects "
                f"requiring advanced technical skills"
            )
        
        if quick_turnarounds:
            avg_time = sum(wo['time_logged'] for wo in quick_turnarounds) / len(quick_turnarounds)
            achievements.append(
                f"Consistently delivered efficient solutions with average completion time of "
                f"{avg_time:.1f} hours, demonstrating strong problem-solving abilities"
            )
        
        # Industry-specific achievements
        industry_counts = Counter(wo_dict[wo_id]['industry'] for wo_id, _, _, _ in top_matches 
                                if wo_id in wo_dict and wo_dict[wo_id]['industry'])
        
        if industry_counts:
            top_industry = industry_counts.most_common(1)[0]
            achievements.append(
                f"Extensive experience in {top_industry[0]} industry with {top_industry[1]} "
                f"completed projects"
            )
        
        return achievements[:5]  # Return top 5 achievements

    def generate_resume_components(self, job_match: JobMatch, job_title: str = "") -> Dict[str, str]:
        """Generate resume components based on job match"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get detailed work order information
        placeholders = ','.join('?' * len(job_match.work_order_ids))
        cursor.execute(f"""
            SELECT * FROM work_orders_enhanced 
            WHERE id IN ({placeholders})
            ORDER BY pay_amount DESC, complexity_level DESC
        """, job_match.work_order_ids)
        
        matched_orders = cursor.fetchall()
        conn.close()
        
        components = {}
        
        # Professional Summary
        summary_parts = [
            f"Experienced IT professional with proven expertise in {', '.join(job_match.matched_skills[:3])}",
            f"Proficient in {', '.join(job_match.matched_technologies[:3])} technologies",
            job_match.relevant_experience
        ]
        
        if job_match.industry_match:
            industry = matched_orders[0]['industry'] if matched_orders else ""
            summary_parts.append(f"Specialized experience in {industry} industry")
        
        components['Professional Summary'] = '. '.join(summary_parts) + '.'
        
        # Skills Section
        technical_skills = job_match.matched_technologies
        soft_skills = [skill for skill in job_match.matched_skills 
                      if any(word in skill.lower() for word in ['customer', 'project', 'communication'])]
        
        skills_text = "**Technical Skills:** " + ', '.join(technical_skills)
        if soft_skills:
            skills_text += "\n**Professional Skills:** " + ', '.join(soft_skills)
        
        components['Technical Skills'] = skills_text
        
        # Work Experience Highlights
        experience_items = []
        for i, wo in enumerate(matched_orders[:3]):  # Top 3 work orders
            try:
                technologies = json.loads(wo['technologies_used'] or '[]')
                skills = json.loads(wo['skills_demonstrated'] or '[]')
            except:
                technologies = []
                skills = []
            
            item = f"• {wo['title']} - {wo['company_name']}"
            if wo['pay_amount']:
                item += f" (${wo['pay_amount']:,.2f})"
            
            item += f"\n  - {wo['work_description'][:100]}..."
            
            if technologies:
                item += f"\n  - Technologies: {', '.join(technologies[:3])}"
            
            experience_items.append(item)
        
        components['Relevant Project Experience'] = '\n\n'.join(experience_items)
        
        # Key Achievements
        achievements_text = '\n'.join(f"• {achievement}" for achievement in job_match.suggested_achievements)
        components['Key Achievements'] = achievements_text
        
        return components

# Example usage and testing
if __name__ == "__main__":
    matcher = EnhancedJobMatcher()
    
    # Sample job description
    sample_job = """
    We are seeking a Field Service Technician to provide onsite technical support for our retail clients.
    
    Requirements:
    - Experience with POS systems and retail technology
    - Strong troubleshooting and problem-solving skills
    - Customer service experience in retail environments
    - Knowledge of Windows systems and network equipment
    - Ability to work independently in the field
    
    Preferred:
    - Experience in retail industry
    - Network administration skills
    - Hardware installation experience
    """
    
    # Analyze job and find matches
    job_analysis = matcher.analyze_job_description(sample_job)
    print("📋 Job Analysis:")
    for key, value in job_analysis.items():
        print(f"   {key}: {value}")
    
    # Find matching work orders
    match_result = matcher.find_matching_work_orders(job_analysis)
    print(f"\n🎯 Match Results:")
    print(f"   Score: {match_result.match_score:.1f}")
    print(f"   Confidence: {match_result.confidence_level}")
    print(f"   Matching Work Orders: {len(match_result.work_order_ids)}")
    print(f"   Matched Skills: {match_result.matched_skills}")
    print(f"   Matched Technologies: {match_result.matched_technologies}")
    
    # Generate resume components
    if match_result.work_order_ids:
        components = matcher.generate_resume_components(match_result, "Field Service Technician")
        print(f"\n📄 Generated Resume Components:")
        for section, content in components.items():
            print(f"\n{section}:")
            print(content) 