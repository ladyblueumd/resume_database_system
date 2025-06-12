-- Contact Management Schema for Resume Database System
-- Tracks all people, companies, and relationships from work orders

-- Companies table (enhanced from work orders)
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    company_type TEXT, -- 'client', 'employer', 'partner', 'vendor'
    industry TEXT,
    website TEXT,
    main_phone TEXT,
    main_email TEXT,
    headquarters_address TEXT,
    headquarters_city TEXT,
    headquarters_state TEXT,
    headquarters_zip TEXT,
    company_size TEXT, -- 'small', 'medium', 'large', 'enterprise'
    annual_revenue TEXT,
    description TEXT,
    notes TEXT,
    first_engagement_date DATE,
    last_engagement_date DATE,
    total_work_orders INTEGER DEFAULT 0,
    total_earnings REAL DEFAULT 0,
    relationship_status TEXT DEFAULT 'active', -- 'active', 'inactive', 'prospect'
    is_reference_available BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contacts table (all people interacted with)
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    mobile_phone TEXT,
    company_id INTEGER,
    title TEXT,
    department TEXT,
    role_type TEXT, -- 'client_contact', 'help_desk', 'admin', 'manager', 'technical_contact', 'billing'
    linkedin_url TEXT,
    twitter_handle TEXT,
    preferred_contact_method TEXT, -- 'email', 'phone', 'text', 'linkedin'
    timezone TEXT,
    location_city TEXT,
    location_state TEXT,
    location_country TEXT DEFAULT 'USA',
    first_interaction_date DATE,
    last_interaction_date DATE,
    interaction_count INTEGER DEFAULT 1,
    relationship_strength TEXT DEFAULT 'professional', -- 'new', 'professional', 'strong', 'champion'
    is_reference BOOLEAN DEFAULT FALSE,
    reference_quality INTEGER, -- 1-5 rating
    notes TEXT,
    tags TEXT, -- comma-separated tags
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Contact interactions (track all touchpoints)
CREATE TABLE IF NOT EXISTS contact_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    work_order_id TEXT,
    interaction_date DATE,
    interaction_type TEXT, -- 'work_order', 'email', 'phone', 'meeting', 'reference_request'
    interaction_subject TEXT,
    interaction_notes TEXT,
    sentiment TEXT DEFAULT 'neutral', -- 'positive', 'neutral', 'negative'
    outcome TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

-- Communication channels (store all ways to reach contacts)
CREATE TABLE IF NOT EXISTS communication_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    channel_type TEXT NOT NULL, -- 'email', 'phone', 'mobile', 'slack', 'teams', 'skype', 'whatsapp'
    channel_value TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_used_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

-- Reference tracking (renamed from 'references' to avoid SQL keyword conflict)
CREATE TABLE IF NOT EXISTS contact_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    company_id INTEGER,
    reference_type TEXT, -- 'professional', 'character', 'technical'
    relationship_context TEXT,
    years_known INTEGER,
    reference_strength INTEGER, -- 1-5 rating
    willing_to_recommend BOOLEAN DEFAULT TRUE,
    last_recommendation_date DATE,
    recommendation_count INTEGER DEFAULT 0,
    areas_of_expertise TEXT, -- comma-separated
    sample_recommendation TEXT,
    linkedin_recommendation BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Industry connections (for showcasing)
CREATE TABLE IF NOT EXISTS industry_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    industry_category TEXT NOT NULL, -- 'Healthcare', 'Finance', 'Retail', 'Technology', etc.
    company_tier TEXT, -- 'Fortune 500', 'Enterprise', 'Mid-Market', 'SMB'
    showcase_priority INTEGER DEFAULT 5, -- 1-10, higher = more prominent
    showcase_description TEXT,
    key_projects TEXT,
    technologies_used TEXT,
    impact_statement TEXT,
    logo_url TEXT,
    case_study_available BOOLEAN DEFAULT FALSE,
    public_reference BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Relationship network (track who knows who)
CREATE TABLE IF NOT EXISTS contact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id_1 INTEGER NOT NULL,
    contact_id_2 INTEGER NOT NULL,
    relationship_type TEXT, -- 'colleague', 'reports_to', 'vendor', 'client'
    relationship_strength TEXT DEFAULT 'known', -- 'known', 'worked_together', 'strong'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id_1) REFERENCES contacts(id),
    FOREIGN KEY (contact_id_2) REFERENCES contacts(id)
);

-- Views for easy querying
CREATE VIEW IF NOT EXISTS contact_summary AS
SELECT 
    c.id,
    c.full_name,
    c.email,
    c.phone,
    c.title,
    c.role_type,
    comp.company_name,
    comp.company_type,
    c.relationship_strength,
    c.is_reference,
    c.interaction_count,
    c.last_interaction_date,
    COUNT(DISTINCT ci.id) as total_interactions,
    COUNT(DISTINCT ci.work_order_id) as work_orders_together
FROM contacts c
LEFT JOIN companies comp ON c.company_id = comp.id
LEFT JOIN contact_interactions ci ON c.id = ci.contact_id
GROUP BY c.id;

CREATE VIEW IF NOT EXISTS company_summary AS
SELECT 
    comp.id,
    comp.company_name,
    comp.company_type,
    comp.industry,
    comp.total_work_orders,
    comp.total_earnings,
    comp.relationship_status,
    COUNT(DISTINCT c.id) as total_contacts,
    COUNT(DISTINCT c.id) FILTER (WHERE c.is_reference = TRUE) as reference_contacts,
    GROUP_CONCAT(DISTINCT c.role_type) as contact_roles
FROM companies comp
LEFT JOIN contacts c ON comp.id = c.company_id
GROUP BY comp.id;

CREATE VIEW IF NOT EXISTS reference_ready_contacts AS
SELECT 
    c.*,
    comp.company_name,
    comp.industry,
    r.reference_strength,
    r.areas_of_expertise,
    r.sample_recommendation
FROM contacts c
JOIN companies comp ON c.company_id = comp.id
LEFT JOIN contact_references r ON c.id = r.contact_id
WHERE c.is_reference = TRUE
ORDER BY r.reference_strength DESC, c.interaction_count DESC;

-- Indexes for performance
CREATE INDEX idx_contacts_company ON contacts(company_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_role ON contacts(role_type);
CREATE INDEX idx_interactions_contact ON contact_interactions(contact_id);
CREATE INDEX idx_interactions_date ON contact_interactions(interaction_date);
CREATE INDEX idx_companies_name ON companies(company_name);
CREATE INDEX idx_companies_type ON companies(company_type);
CREATE INDEX idx_references_contact ON contact_references(contact_id); 