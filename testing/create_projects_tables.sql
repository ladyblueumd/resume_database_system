-- Work Order Projects Table
-- Group related work orders into projects for resume presentation
CREATE TABLE IF NOT EXISTS work_order_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    project_description TEXT,
    project_type TEXT, -- deployment, migration, support, infrastructure, etc.
    client_name TEXT, -- Primary client/company for this project
    client_type TEXT, -- enterprise, retail, healthcare, financial, etc.
    
    -- Project timeline
    start_date DATE,
    end_date DATE,
    duration_weeks INTEGER,
    
    -- Project scope and impact
    scope_description TEXT,
    team_size INTEGER,
    my_role TEXT, -- Lead Technician, Support Specialist, etc.
    key_achievements TEXT, -- JSON array of achievements
    technologies_used TEXT, -- JSON array of technologies
    skills_demonstrated TEXT, -- JSON array of skills
    
    -- Project metrics
    total_work_orders INTEGER DEFAULT 0,
    total_earnings DECIMAL(10,2) DEFAULT 0,
    avg_rating DECIMAL(3,2),
    locations_served TEXT, -- JSON array of locations
    
    -- Resume integration
    include_in_resume BOOLEAN DEFAULT TRUE,
    priority_level INTEGER DEFAULT 1, -- 1=highest, 5=lowest
    target_job_types TEXT, -- JSON array of job types this project is relevant for
    
    -- Documentation
    project_summary TEXT, -- Formatted summary for resume
    challenges_overcome TEXT,
    business_impact TEXT,
    lessons_learned TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Junction table for work orders in projects
CREATE TABLE IF NOT EXISTS work_order_project_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    assignment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    role_in_project TEXT, -- Primary, Supporting, Documentation, etc.
    contribution_notes TEXT,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES work_order_projects(id) ON DELETE CASCADE,
    UNIQUE(work_order_id, project_id)
);

-- Create indexes for project tables
CREATE INDEX IF NOT EXISTS idx_projects_client ON work_order_projects(client_name);
CREATE INDEX IF NOT EXISTS idx_projects_type ON work_order_projects(project_type);
CREATE INDEX IF NOT EXISTS idx_projects_resume ON work_order_projects(include_in_resume);
CREATE INDEX IF NOT EXISTS idx_projects_priority ON work_order_projects(priority_level);

CREATE INDEX IF NOT EXISTS idx_assignments_project ON work_order_project_assignments(project_id);
CREATE INDEX IF NOT EXISTS idx_assignments_work_order ON work_order_project_assignments(work_order_id);

-- Project summary view with aggregated work order data
CREATE VIEW IF NOT EXISTS project_portfolio AS
SELECT 
    p.*,
    COUNT(wopa.work_order_id) as actual_work_orders,
    SUM(wo.pay_amount) as actual_earnings,
    AVG(wo.wo_rating) as actual_avg_rating,
    GROUP_CONCAT(DISTINCT wo.company_name) as companies_worked,
    GROUP_CONCAT(DISTINCT wo.state) as states_served,
    MIN(wo.service_date) as actual_start_date,
    MAX(wo.service_date) as actual_end_date
FROM work_order_projects p
LEFT JOIN work_order_project_assignments wopa ON p.id = wopa.project_id
LEFT JOIN work_orders wo ON wopa.work_order_id = wo.id
WHERE p.include_in_resume = TRUE
GROUP BY p.id
ORDER BY p.priority_level, p.end_date DESC;

-- View for job matching - combines individual work orders and projects
CREATE VIEW IF NOT EXISTS resume_ready_work_items AS
SELECT 
    'work_order' as item_type,
    wo.id as item_id,
    wo.title,
    wo.company_name as client_name,
    wo.work_category as category,
    wo.client_type,
    wo.technologies_used,
    wo.skills_demonstrated,
    wo.service_date as start_date,
    wo.service_date as end_date,
    wo.work_description as description,
    CAST(wo.pay_amount AS TEXT) as value_metric,
    wo.include_in_resume
FROM work_orders wo
WHERE wo.include_in_resume = TRUE

UNION ALL

SELECT 
    'project' as item_type,
    p.id as item_id,
    p.project_name as title,
    p.client_name,
    p.project_type as category,
    p.client_type,
    p.technologies_used,
    p.skills_demonstrated,
    p.start_date,
    p.end_date,
    p.project_description as description,
    CAST(p.total_earnings AS TEXT) || ' (' || CAST(p.total_work_orders AS TEXT) || ' orders)' as value_metric,
    p.include_in_resume
FROM work_order_projects p
WHERE p.include_in_resume = TRUE
ORDER BY start_date DESC; 