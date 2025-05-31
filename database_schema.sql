-- Resume Database Schema
-- SQLite database for storing resume components, employment history, and job matching

-- Personal Information Table
CREATE TABLE personal_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    location TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    portfolio_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Resume Section Types
CREATE TABLE section_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    display_order INTEGER
);

-- Insert default section types
INSERT INTO section_types (name, description, display_order) VALUES
('professional_summary', 'Professional Summary/Objective statements', 1),
('technical_skills', 'Technical skills and tools', 2),
('professional_skills', 'Soft skills and professional capabilities', 3),
('work_experience', 'Employment history and job descriptions', 4),
('projects', 'Key projects and achievements', 5),
('certifications', 'Professional certifications and training', 6),
('education', 'Educational background', 7),
('accomplishments', 'Awards and recognitions', 8);

-- Resume Components/Snippets
CREATE TABLE resume_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_type_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT, -- JSON array of relevant keywords
    industry_tags TEXT, -- JSON array of industry tags
    skill_level TEXT CHECK(skill_level IN ('entry', 'intermediate', 'advanced', 'expert')),
    usage_count INTEGER DEFAULT 0,
    effectiveness_score REAL DEFAULT 0.0, -- Based on success rate when used
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_type_id) REFERENCES section_types(id)
);

-- Historical Employment
CREATE TABLE employment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    position_title TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    location TEXT,
    employment_type TEXT CHECK(employment_type IN ('full-time', 'part-time', 'contract', 'freelance', 'internship')),
    industry TEXT,
    company_size TEXT,
    manager_name TEXT,
    manager_contact TEXT,
    hr_contact TEXT,
    salary_range TEXT,
    responsibilities TEXT, -- JSON array of responsibilities
    achievements TEXT, -- JSON array of achievements
    technologies_used TEXT, -- JSON array of technologies
    skills_gained TEXT, -- JSON array of skills gained
    reason_for_leaving TEXT,
    reference_available BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Job Descriptions for Matching
CREATE TABLE job_descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    position_title TEXT NOT NULL,
    job_description TEXT NOT NULL,
    requirements TEXT, -- Extracted requirements
    preferred_qualifications TEXT,
    keywords TEXT, -- JSON array of extracted keywords
    salary_range TEXT,
    location TEXT,
    employment_type TEXT,
    application_deadline DATE,
    application_url TEXT,
    status TEXT CHECK(status IN ('saved', 'applied', 'interviewing', 'rejected', 'offered', 'archived')),
    priority INTEGER DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Resume Templates
CREATE TABLE resume_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name TEXT UNIQUE NOT NULL,
    description TEXT,
    target_role TEXT,
    target_industry TEXT,
    component_mapping TEXT, -- JSON mapping of sections to components
    style_settings TEXT, -- JSON for styling preferences
    is_default BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Generated Resumes
CREATE TABLE generated_resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_description_id INTEGER,
    template_id INTEGER,
    resume_title TEXT NOT NULL,
    full_content TEXT NOT NULL, -- Complete resume HTML/content
    components_used TEXT, -- JSON array of component IDs used
    customizations TEXT, -- JSON of any manual customizations
    keywords_matched TEXT, -- JSON array of matched keywords
    match_score REAL,
    status TEXT CHECK(status IN ('draft', 'final', 'submitted', 'archived')),
    exported_formats TEXT, -- JSON array of exported formats (pdf, docx, etc.)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id),
    FOREIGN KEY (template_id) REFERENCES resume_templates(id)
);

-- Skill Categories for Organization
CREATE TABLE skill_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL,
    parent_category_id INTEGER,
    description TEXT,
    display_order INTEGER,
    FOREIGN KEY (parent_category_id) REFERENCES skill_categories(id)
);

-- Individual Skills Database
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT UNIQUE NOT NULL,
    category_id INTEGER,
    proficiency_level TEXT CHECK(proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    years_experience INTEGER,
    last_used_date DATE,
    certifications TEXT, -- JSON array of related certifications
    projects_used TEXT, -- JSON array of project IDs where used
    keywords TEXT, -- JSON array of related keywords/synonyms
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES skill_categories(id)
);

-- Component Usage Tracking
CREATE TABLE component_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id INTEGER,
    component_id INTEGER,
    position_in_resume INTEGER,
    was_customized BOOLEAN DEFAULT FALSE,
    customization_notes TEXT,
    result_feedback TEXT, -- Success/failure feedback
    used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES generated_resumes(id),
    FOREIGN KEY (component_id) REFERENCES resume_components(id)
);

-- Keyword Matching for Job Descriptions
CREATE TABLE keyword_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_description_id INTEGER,
    component_id INTEGER,
    keyword TEXT,
    match_strength REAL, -- 0.0 to 1.0
    match_type TEXT CHECK(match_type IN ('exact', 'semantic', 'synonym')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id),
    FOREIGN KEY (component_id) REFERENCES resume_components(id)
);

-- Application Tracking
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_description_id INTEGER,
    resume_id INTEGER,
    application_date DATE,
    application_method TEXT,
    status TEXT CHECK(status IN ('submitted', 'acknowledged', 'screening', 'interviewing', 'offer', 'rejected', 'withdrawn')),
    next_action TEXT,
    next_action_date DATE,
    contact_person TEXT,
    interview_notes TEXT,
    feedback_received TEXT,
    lessons_learned TEXT,
    follow_up_dates TEXT, -- JSON array of follow-up dates
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id),
    FOREIGN KEY (resume_id) REFERENCES generated_resumes(id)
);

-- Create indexes for better performance
CREATE INDEX idx_components_section_type ON resume_components(section_type_id);
CREATE INDEX idx_components_keywords ON resume_components(keywords);
CREATE INDEX idx_employment_company ON employment_history(company_name);
CREATE INDEX idx_employment_dates ON employment_history(start_date, end_date);
CREATE INDEX idx_jobs_status ON job_descriptions(status);
CREATE INDEX idx_jobs_keywords ON job_descriptions(keywords);
CREATE INDEX idx_resumes_job ON generated_resumes(job_description_id);
CREATE INDEX idx_skills_category ON skills(category_id);
CREATE INDEX idx_usage_component ON component_usage(component_id);
CREATE INDEX idx_matches_job ON keyword_matches(job_description_id);

-- Create views for common queries
CREATE VIEW resume_component_summary AS
SELECT 
    rc.id,
    rc.title,
    rc.content,
    st.name as section_type,
    rc.keywords,
    rc.industry_tags,
    rc.skill_level,
    rc.usage_count,
    rc.effectiveness_score
FROM resume_components rc
JOIN section_types st ON rc.section_type_id = st.id;

CREATE VIEW active_employment AS
SELECT 
    eh.*,
    CASE 
        WHEN eh.end_date IS NULL THEN 'Current'
        ELSE 'Previous'
    END as employment_status
FROM employment_history eh
ORDER BY eh.start_date DESC;

CREATE VIEW job_matching_summary AS
SELECT 
    jd.id as job_id,
    jd.company_name,
    jd.position_title,
    COUNT(km.id) as total_matches,
    AVG(km.match_strength) as avg_match_strength,
    jd.status
FROM job_descriptions jd
LEFT JOIN keyword_matches km ON jd.id = km.job_description_id
GROUP BY jd.id, jd.company_name, jd.position_title, jd.status;
