-- Enhanced FieldNation Work Order Database Schema
-- Comprehensive database for organizing work order data by skills, software, tools, client information, and matching capabilities

-- Main work orders table with comprehensive fields
CREATE TABLE IF NOT EXISTS fieldnation_work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fn_work_order_id TEXT UNIQUE NOT NULL,
    
    -- Basic Work Order Information
    title TEXT NOT NULL,
    work_order_date DATE,
    service_date DATE,
    completion_date DATE,
    
    -- Location Information  
    location TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    site_address TEXT,
    site_type TEXT, -- commercial, residential, datacenter, etc.
    
    -- Client/Company Information
    buyer_company TEXT NOT NULL,
    client_name TEXT,
    manager_name TEXT,
    manager_contact TEXT,
    site_contact TEXT,
    contact_phone TEXT,
    client_email TEXT,
    
    -- Financial Information
    pay_amount DECIMAL(10,2),
    hourly_rate DECIMAL(10,2),
    estimated_hours DECIMAL(4,2),
    actual_hours DECIMAL(4,2),
    travel_reimbursement DECIMAL(10,2),
    
    -- Work Classification
    work_type TEXT, -- from labels on work order
    service_type TEXT, -- installation, repair, maintenance, etc.
    industry_category TEXT,
    complexity_level TEXT CHECK(complexity_level IN ('Low', 'Medium', 'High', 'Expert')),
    
    -- Work Details
    work_description TEXT,
    scope_of_work TEXT,
    service_description TEXT,
    special_instructions TEXT,
    dress_code TEXT,
    
    -- Technical Requirements
    required_skills TEXT, -- JSON array
    required_tools TEXT, -- JSON array
    required_software TEXT, -- JSON array
    technologies_used TEXT, -- JSON array
    hardware_involved TEXT, -- JSON array
    
    -- Qualifications
    work_order_qualifications TEXT, -- JSON object with all qualification fields
    certifications_required TEXT, -- JSON array
    experience_required TEXT,
    security_clearance_required TEXT,
    
    -- Status and Performance
    status TEXT,
    completion_status TEXT,
    quality_rating DECIMAL(3,2),
    client_satisfaction DECIMAL(3,2),
    
    -- Problem Solving
    challenges_encountered TEXT, -- JSON array
    solutions_implemented TEXT, -- JSON array
    lessons_learned TEXT,
    
    -- Deliverables and Documentation
    deliverables TEXT, -- JSON array
    photos_required BOOLEAN DEFAULT FALSE,
    documentation_provided TEXT, -- JSON array
    
    -- Schedule Information
    scheduled_start_time TIME,
    scheduled_end_time TIME,
    actual_start_time TIME,
    actual_end_time TIME,
    time_zone TEXT,
    
    -- Resume Integration
    include_in_resume BOOLEAN DEFAULT TRUE,
    highlight_project BOOLEAN DEFAULT FALSE,
    resume_bullet_points TEXT, -- JSON array of formatted bullet points
    achievements TEXT, -- JSON array of specific achievements
    
    -- Source and Metadata
    data_source TEXT, -- 'markdown' or 'pdf'
    source_file_path TEXT,
    extraction_quality DECIMAL(3,2),
    needs_review BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    extracted_at DATETIME
);

-- Skills taxonomy and categorization
CREATE TABLE IF NOT EXISTS work_order_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    skill_category TEXT,
    skill_type TEXT, -- technical, soft, industry-specific
    proficiency_level TEXT,
    years_experience INTEGER,
    is_primary_skill BOOLEAN DEFAULT FALSE,
    skill_context TEXT, -- how skill was used in this work order
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES fieldnation_work_orders(id) ON DELETE CASCADE
);

-- Tools and equipment used
CREATE TABLE IF NOT EXISTS work_order_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    tool_category TEXT, -- hardware, software, diagnostic, safety
    manufacturer TEXT,
    model_number TEXT,
    required_vs_used TEXT, -- 'required' or 'used'
    proficiency_level TEXT,
    usage_context TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES fieldnation_work_orders(id) ON DELETE CASCADE
);

-- Software and applications
CREATE TABLE IF NOT EXISTS work_order_software (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    software_name TEXT NOT NULL,
    software_category TEXT, -- OS, application, utility, diagnostic
    vendor TEXT,
    version TEXT,
    license_type TEXT,
    usage_context TEXT,
    proficiency_level TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES fieldnation_work_orders(id) ON DELETE CASCADE
);

-- Client intelligence and relationship management
CREATE TABLE IF NOT EXISTS client_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT UNIQUE NOT NULL,
    industry TEXT,
    company_size TEXT,
    headquarters_location TEXT,
    business_type TEXT, -- public, private, government, non-profit
    
    -- Contact Information
    primary_contact TEXT,
    primary_email TEXT,
    primary_phone TEXT,
    billing_contact TEXT,
    
    -- Service History
    first_service_date DATE,
    last_service_date DATE,
    total_work_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(12,2) DEFAULT 0,
    average_pay_rate DECIMAL(10,2),
    
    -- Relationship Quality
    client_rating DECIMAL(3,2),
    payment_reliability TEXT,
    communication_quality TEXT,
    
    -- Service Patterns
    preferred_service_types TEXT, -- JSON array
    common_locations TEXT, -- JSON array
    typical_technologies TEXT, -- JSON array
    seasonal_patterns TEXT,
    
    -- Notes and Intelligence
    client_notes TEXT,
    special_requirements TEXT,
    preferred_vendors TEXT, -- JSON array
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Job matching intelligence for resume building
CREATE TABLE IF NOT EXISTS job_matching_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    
    -- Matching Keywords
    primary_keywords TEXT, -- JSON array
    secondary_keywords TEXT, -- JSON array
    industry_keywords TEXT, -- JSON array
    
    -- Experience Indicators
    experience_level TEXT,
    leadership_indicators TEXT, -- JSON array
    collaboration_indicators TEXT, -- JSON array
    
    -- Achievement Metrics
    quantifiable_results TEXT, -- JSON array
    cost_savings TEXT,
    efficiency_improvements TEXT,
    quality_improvements TEXT,
    
    -- Transferable Skills
    transferable_skills TEXT, -- JSON array
    cross_industry_applications TEXT, -- JSON array
    
    -- Resume Optimization
    bullet_point_templates TEXT, -- JSON array
    achievement_statements TEXT, -- JSON array
    relevant_for_roles TEXT, -- JSON array
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES fieldnation_work_orders(id) ON DELETE CASCADE
);

-- Geographic service areas and market intelligence
CREATE TABLE IF NOT EXISTS service_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_identifier TEXT UNIQUE NOT NULL, -- city_state_zip format
    city TEXT,
    state TEXT,
    zip_code TEXT,
    county TEXT,
    region TEXT,
    metro_area TEXT,
    
    -- Market Data
    total_work_orders INTEGER DEFAULT 0,
    average_pay_rate DECIMAL(10,2),
    travel_distance_miles INTEGER,
    typical_travel_time INTEGER, -- minutes
    
    -- Industry Presence
    dominant_industries TEXT, -- JSON array
    major_clients TEXT, -- JSON array
    
    -- Service Patterns
    peak_service_months TEXT, -- JSON array
    common_service_types TEXT, -- JSON array
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Technology and platform expertise tracking
CREATE TABLE IF NOT EXISTS technology_expertise (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technology_name TEXT UNIQUE NOT NULL,
    category TEXT, -- hardware, software, platform, protocol
    subcategory TEXT,
    vendor TEXT,
    
    -- Usage Statistics
    times_used INTEGER DEFAULT 0,
    first_used_date DATE,
    last_used_date DATE,
    proficiency_progression TEXT, -- JSON array tracking skill growth
    
    -- Market Relevance
    market_demand TEXT, -- high, medium, low
    industry_adoption TEXT, -- JSON array
    replacement_technologies TEXT, -- JSON array
    
    -- Learning Resources
    certification_paths TEXT, -- JSON array
    training_resources TEXT, -- JSON array
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Performance analytics and KPIs
CREATE TABLE IF NOT EXISTS work_order_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    
    -- Performance Metrics
    time_efficiency DECIMAL(3,2), -- actual vs estimated hours
    quality_score DECIMAL(3,2),
    client_satisfaction DECIMAL(3,2),
    complexity_handled DECIMAL(3,2),
    
    -- Skill Development
    new_skills_acquired TEXT, -- JSON array
    skills_improved TEXT, -- JSON array
    certifications_earned TEXT, -- JSON array
    
    -- Business Impact
    cost_savings_achieved DECIMAL(10,2),
    efficiency_improvements TEXT,
    customer_retention_impact TEXT,
    
    -- Learning Outcomes
    lessons_learned TEXT, -- JSON array
    best_practices_developed TEXT, -- JSON array
    process_improvements TEXT, -- JSON array
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES fieldnation_work_orders(id) ON DELETE CASCADE
);

-- Indexes for optimal query performance
CREATE INDEX idx_work_orders_fn_id ON fieldnation_work_orders(fn_work_order_id);
CREATE INDEX idx_work_orders_company ON fieldnation_work_orders(buyer_company);
CREATE INDEX idx_work_orders_date ON fieldnation_work_orders(service_date);
CREATE INDEX idx_work_orders_location ON fieldnation_work_orders(city, state);
CREATE INDEX idx_work_orders_work_type ON fieldnation_work_orders(work_type);
CREATE INDEX idx_work_orders_status ON fieldnation_work_orders(status);
CREATE INDEX idx_work_orders_pay ON fieldnation_work_orders(pay_amount);

CREATE INDEX idx_skills_work_order ON work_order_skills(work_order_id);
CREATE INDEX idx_skills_name ON work_order_skills(skill_name);
CREATE INDEX idx_skills_category ON work_order_skills(skill_category);

CREATE INDEX idx_tools_work_order ON work_order_tools(work_order_id);
CREATE INDEX idx_tools_name ON work_order_tools(tool_name);
CREATE INDEX idx_tools_category ON work_order_tools(tool_category);

CREATE INDEX idx_software_work_order ON work_order_software(work_order_id);
CREATE INDEX idx_software_name ON work_order_software(software_name);

CREATE INDEX idx_clients_company ON client_companies(company_name);
CREATE INDEX idx_clients_industry ON client_companies(industry);

CREATE INDEX idx_locations_city_state ON service_locations(city, state);
CREATE INDEX idx_locations_region ON service_locations(region);

-- Views for common queries
CREATE VIEW work_order_summary AS
SELECT 
    wo.id,
    wo.fn_work_order_id,
    wo.title,
    wo.buyer_company,
    wo.service_date,
    wo.location,
    wo.pay_amount,
    wo.work_type,
    wo.status,
    COUNT(DISTINCT ws.id) as skills_count,
    COUNT(DISTINCT wt.id) as tools_count,
    COUNT(DISTINCT wsw.id) as software_count
FROM fieldnation_work_orders wo
LEFT JOIN work_order_skills ws ON wo.id = ws.work_order_id
LEFT JOIN work_order_tools wt ON wo.id = wt.work_order_id  
LEFT JOIN work_order_software wsw ON wo.id = wsw.work_order_id
GROUP BY wo.id;

CREATE VIEW client_performance_summary AS
SELECT 
    cc.company_name,
    cc.industry,
    cc.total_work_orders,
    cc.total_revenue,
    cc.average_pay_rate,
    cc.client_rating,
    COUNT(DISTINCT wo.work_type) as service_variety,
    MAX(wo.service_date) as last_service_date
FROM client_companies cc
LEFT JOIN fieldnation_work_orders wo ON cc.company_name = wo.buyer_company
GROUP BY cc.id;

CREATE VIEW technology_usage_summary AS
SELECT 
    te.technology_name,
    te.category,
    te.times_used,
    te.market_demand,
    COUNT(DISTINCT ws.work_order_id) as work_orders_used,
    AVG(wo.pay_amount) as avg_pay_for_technology
FROM technology_expertise te
LEFT JOIN work_order_software ws ON te.technology_name = ws.software_name
LEFT JOIN fieldnation_work_orders wo ON ws.work_order_id = wo.id
GROUP BY te.id; 