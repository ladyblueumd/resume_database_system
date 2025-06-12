-- FieldNation Work Orders Table
-- Store individual work orders for detailed project tracking

CREATE TABLE work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fn_work_order_id TEXT UNIQUE NOT NULL, -- FieldNation WO ID
    title TEXT NOT NULL,
    work_type TEXT, -- General Tasks, Windows Device, Printer, Point of Sale, etc.
    company_name TEXT NOT NULL,
    service_date DATE,
    location TEXT,
    pay_amount DECIMAL(10,2),
    status TEXT CHECK(status IN ('Paid', 'Approved', 'Completed', 'In Progress', 'Cancelled')),
    state TEXT,
    city TEXT,
    zip_code TEXT,
    distance_miles INTEGER,
    estimated_total DECIMAL(10,2),
    buyer_rating INTEGER,
    wo_rating INTEGER,
    
    -- Categorization
    work_category TEXT, -- desktop, retail, networking, printers, telephony, medical, etc.
    client_type TEXT, -- enterprise, retail, healthcare, financial, etc.
    
    -- Technical details
    technologies_used TEXT, -- JSON array of tech/tools used
    skills_demonstrated TEXT, -- JSON array of skills used
    complexity_level TEXT CHECK(complexity_level IN ('basic', 'intermediate', 'advanced', 'expert')),
    
    -- Time tracking
    estimated_hours DECIMAL(4,2),
    actual_hours DECIMAL(4,2),
    
    -- Notes and outcomes
    work_description TEXT,
    challenges_faced TEXT,
    solutions_implemented TEXT,
    client_feedback TEXT,
    lessons_learned TEXT,
    
    -- Resume usage
    include_in_resume BOOLEAN DEFAULT TRUE,
    highlight_project BOOLEAN DEFAULT FALSE,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Work Order Projects Table
-- Group related work orders into projects for resume presentation
CREATE TABLE work_order_projects (
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
CREATE TABLE work_order_project_assignments (
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

-- Create indexes for efficient querying
CREATE INDEX idx_work_orders_company ON work_orders(company_name);
CREATE INDEX idx_work_orders_type ON work_orders(work_type);
CREATE INDEX idx_work_orders_category ON work_orders(work_category);
CREATE INDEX idx_work_orders_date ON work_orders(service_date);
CREATE INDEX idx_work_orders_location ON work_orders(state, city);
CREATE INDEX idx_work_orders_resume ON work_orders(include_in_resume);

CREATE INDEX idx_projects_client ON work_order_projects(client_name);
CREATE INDEX idx_projects_type ON work_order_projects(project_type);
CREATE INDEX idx_projects_resume ON work_order_projects(include_in_resume);
CREATE INDEX idx_projects_priority ON work_order_projects(priority_level);

CREATE INDEX idx_assignments_project ON work_order_project_assignments(project_id);
CREATE INDEX idx_assignments_work_order ON work_order_project_assignments(work_order_id);

-- Create view for work order summary statistics
CREATE VIEW work_orders_summary AS
SELECT 
    work_category,
    work_type,
    COUNT(*) as total_orders,
    SUM(pay_amount) as total_earnings,
    AVG(pay_amount) as avg_pay,
    MIN(service_date) as first_order,
    MAX(service_date) as last_order,
    COUNT(DISTINCT company_name) as unique_companies,
    COUNT(DISTINCT state) as states_worked,
    AVG(wo_rating) as avg_rating
FROM work_orders
WHERE status = 'Paid'
GROUP BY work_category, work_type
ORDER BY total_orders DESC;

-- Create view for resume-worthy projects
CREATE VIEW featured_work_orders AS
SELECT 
    wo.*,
    CASE 
        WHEN pay_amount > 500 THEN 'high-value'
        WHEN pay_amount > 200 THEN 'medium-value' 
        ELSE 'standard'
    END as value_tier,
    CASE
        WHEN wo_rating >= 4 THEN 'excellent'
        WHEN wo_rating >= 3 THEN 'good'
        ELSE 'satisfactory'
    END as performance_tier
FROM work_orders wo
WHERE include_in_resume = TRUE
ORDER BY service_date DESC, pay_amount DESC;

-- Project summary view with aggregated work order data
CREATE VIEW project_portfolio AS
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
CREATE VIEW resume_ready_work_items AS
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