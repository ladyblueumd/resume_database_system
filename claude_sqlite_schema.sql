-- SQLite Compatible Version of Claude Database Schema
-- Converted from MySQL to SQLite syntax

-- Primary Table: work_orders_markdown
CREATE TABLE work_orders_markdown (
    -- Primary Key
    work_order_id TEXT PRIMARY KEY,
    
    -- Basic Information
    platform TEXT DEFAULT 'Field Nation',
    title TEXT NOT NULL,
    description TEXT,
    status TEXT,
    status_detail TEXT,
    date_created DATE,
    date_completed DATE,
    date_paid DATE,
    priority TEXT,
    work_type TEXT,
    service_type TEXT,
    
    -- Full Service Description (Complete unabridged text)
    service_description_full TEXT,
    scope_of_work TEXT,
    
    -- Company Information
    company_name TEXT,
    company_overall_satisfaction TEXT,
    company_reviews_count INTEGER,
    manager_name TEXT,
    manager_contact TEXT,
    
    -- Provider/Technician Information
    provider_name TEXT,
    provider_id TEXT,
    provider_phone TEXT,
    provider_email TEXT,
    
    -- Location Information
    location_address TEXT,
    location_city TEXT,
    location_state TEXT,
    location_zip TEXT,
    location_country TEXT DEFAULT 'US',
    location_type TEXT,
    gps_required BOOLEAN DEFAULT 0,
    
    -- Schedule Information
    scheduled_date DATE,
    arrival_time TIME,
    arrival_time_timezone TEXT,
    arrival_window_start TIME,
    arrival_window_end TIME,
    hard_start BOOLEAN DEFAULT 0,
    estimated_duration_hours REAL,
    
    -- Time and Hours
    estimated_hours REAL,
    actual_hours_logged REAL,
    max_hours_allowed REAL,
    check_in_datetime TIMESTAMP,
    check_out_datetime TIMESTAMP,
    check_in_distance TEXT,
    check_out_distance TEXT,
    
    -- Equipment Information
    equipment_type TEXT,
    equipment_manufacturer TEXT,
    equipment_model TEXT,
    equipment_serial_number TEXT,
    equipment_asset_tag TEXT,
    kiosk_id TEXT,
    
    -- Financial Information
    labor_rate REAL,
    first_hours_rate REAL,
    first_hours INTEGER,
    additional_hours_rate REAL,
    max_additional_hours INTEGER,
    labor_cost REAL,
    parts_cost REAL,
    penalties REAL,
    service_charges REAL,
    taxes REAL,
    total_cost REAL,
    total_paid REAL,
    payment_terms TEXT,
    payment_terms_days INTEGER,
    estimated_approval_days INTEGER,
    
    -- Work Details
    type_of_work TEXT,
    additional_types_of_work TEXT,
    qualifications_required TEXT,
    tools_required TEXT,
    experience_required TEXT,
    dress_code TEXT,
    physical_requirements TEXT,
    
    -- Closeout Information
    closeout_notes TEXT,
    resolution_summary TEXT,
    root_cause TEXT,
    actions_taken TEXT,
    follow_up_required BOOLEAN DEFAULT 0,
    follow_up_notes TEXT,
    ticket_numbers TEXT,
    
    -- Custom Fields JSON (stored as TEXT in SQLite)
    buyer_custom_fields TEXT,
    provider_custom_fields TEXT,
    
    -- Tasks JSON (stored as TEXT in SQLite)
    tasks_completed TEXT,
    
    -- Deliverables JSON (stored as TEXT in SQLite)
    deliverables TEXT,
    
    -- Compliance
    background_check_required BOOLEAN DEFAULT 0,
    drug_test_required BOOLEAN DEFAULT 0,
    safety_checks_completed BOOLEAN DEFAULT 0,
    quality_assurance_completed BOOLEAN DEFAULT 0,
    customer_signoff_received BOOLEAN DEFAULT 0,
    warranty_info TEXT,
    on_time_arrival BOOLEAN DEFAULT 1,
    
    -- Platform Metadata
    messages_count INTEGER DEFAULT 0,
    deliverables_count INTEGER DEFAULT 0,
    shipments_count INTEGER DEFAULT 0,
    work_order_url TEXT,
    
    -- Full Text Search Column (SQLite doesn't support generated columns, so we'll populate this manually)
    search_text TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Supplementary Table: work_orders_pdf_supplement
CREATE TABLE work_orders_pdf_supplement (
    -- Primary Key
    work_order_id TEXT PRIMARY KEY,
    
    -- Client Information
    client_name TEXT,
    client_brand TEXT,
    client_parent_company TEXT,
    store_number TEXT,
    store_manager_name TEXT,
    
    -- On-site Contacts
    onsite_contact_primary_name TEXT,
    onsite_contact_primary_phone TEXT,
    onsite_contact_primary_email TEXT,
    onsite_contact_secondary_name TEXT,
    onsite_contact_secondary_phone TEXT,
    onsite_contact_secondary_email TEXT,
    
    -- Additional Contact Information
    escalation_contact_name TEXT,
    escalation_contact_phone TEXT,
    escalation_contact_email TEXT,
    noc_contact_info TEXT,
    support_hotline TEXT,
    
    -- Additional Location Details
    floor_number TEXT,
    suite_number TEXT,
    building_name TEXT,
    mall_name TEXT,
    cross_streets TEXT,
    parking_instructions TEXT,
    site_access_instructions TEXT,
    
    -- Equipment/Asset Details
    equipment_location_detail TEXT,
    equipment_ip_address TEXT,
    equipment_mac_address TEXT,
    network_vlan TEXT,
    
    -- Signatures and Approvals
    customer_signature_name TEXT,
    customer_signature_datetime TIMESTAMP,
    technician_signature_datetime TIMESTAMP,
    approval_notes TEXT,
    
    -- Additional Documentation
    attached_documents TEXT, -- JSON stored as TEXT
    photo_urls TEXT, -- JSON stored as TEXT
    diagram_references TEXT,
    
    -- PDF Metadata
    pdf_filename TEXT,
    pdf_page_count INTEGER,
    pdf_file_size_kb INTEGER,
    pdf_extracted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extraction_confidence_score REAL,
    
    -- Foreign Key (SQLite supports foreign keys but they need to be enabled)
    FOREIGN KEY (work_order_id) REFERENCES work_orders_markdown(work_order_id) ON DELETE CASCADE
);

-- Supporting Tables
CREATE TABLE work_order_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id TEXT,
    part_number TEXT,
    part_description TEXT,
    quantity INTEGER DEFAULT 1,
    unit_cost REAL,
    total_cost REAL,
    supplier TEXT,
    return_required BOOLEAN DEFAULT 0,
    return_waybill TEXT,
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders_markdown(work_order_id) ON DELETE CASCADE
);

CREATE TABLE work_order_time_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id TEXT,
    session_number INTEGER,
    start_datetime TIMESTAMP,
    end_datetime TIMESTAMP,
    duration_hours REAL,
    start_distance_from_site TEXT,
    end_distance_from_site TEXT,
    logged_by TEXT,
    logged_datetime TIMESTAMP,
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders_markdown(work_order_id) ON DELETE CASCADE
);

CREATE TABLE work_order_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id TEXT,
    task_category TEXT,
    task_description TEXT,
    completed BOOLEAN DEFAULT 0,
    completed_date DATE,
    completed_time TIME,
    completed_by TEXT,
    time_spent_hours REAL,
    notes TEXT,
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders_markdown(work_order_id) ON DELETE CASCADE
);

CREATE TABLE work_order_deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id TEXT,
    deliverable_type TEXT,
    deliverable_category TEXT,
    filename TEXT,
    file_size_kb REAL,
    upload_datetime TIMESTAMP,
    status TEXT,
    approved_datetime TIMESTAMP,
    approved_by TEXT,
    description TEXT,
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders_markdown(work_order_id) ON DELETE CASCADE
);

-- Views (SQLite supports views)
CREATE VIEW work_order_complete_view AS
SELECT 
    m.*,
    p.client_name,
    p.client_brand,
    p.store_number,
    p.onsite_contact_primary_name,
    p.onsite_contact_primary_phone,
    p.site_access_instructions,
    COUNT(DISTINCT parts.id) as parts_count,
    COUNT(DISTINCT tasks.id) as tasks_count,
    COUNT(DISTINCT deliverables.id) as deliverables_count,
    COUNT(DISTINCT sessions.id) as time_sessions_count
FROM work_orders_markdown m
LEFT JOIN work_orders_pdf_supplement p ON m.work_order_id = p.work_order_id
LEFT JOIN work_order_parts parts ON m.work_order_id = parts.work_order_id
LEFT JOIN work_order_tasks tasks ON m.work_order_id = tasks.work_order_id
LEFT JOIN work_order_deliverables deliverables ON m.work_order_id = deliverables.work_order_id
LEFT JOIN work_order_time_sessions sessions ON m.work_order_id = sessions.work_order_id
GROUP BY m.work_order_id;

-- Indexes for performance (SQLite syntax)
CREATE INDEX idx_status ON work_orders_markdown(status);
CREATE INDEX idx_company ON work_orders_markdown(company_name);
CREATE INDEX idx_provider ON work_orders_markdown(provider_name, provider_id);
CREATE INDEX idx_location ON work_orders_markdown(location_city, location_state);
CREATE INDEX idx_scheduled_date ON work_orders_markdown(scheduled_date);
CREATE INDEX idx_date_completed ON work_orders_markdown(date_completed);
CREATE INDEX idx_date_range ON work_orders_markdown(scheduled_date, date_completed);
CREATE INDEX idx_financial ON work_orders_markdown(total_paid, status);
CREATE INDEX idx_equipment ON work_orders_markdown(equipment_type, equipment_manufacturer);
CREATE INDEX idx_work_type ON work_orders_markdown(work_type, service_type);
CREATE INDEX idx_company_date ON work_orders_markdown(company_name, scheduled_date);
CREATE INDEX idx_location_status ON work_orders_markdown(location_city, location_state, status);

-- Supporting table indexes
CREATE INDEX idx_parts_work_order ON work_order_parts(work_order_id);
CREATE INDEX idx_sessions_work_order ON work_order_time_sessions(work_order_id);
CREATE INDEX idx_sessions_datetime ON work_order_time_sessions(start_datetime, end_datetime);
CREATE INDEX idx_tasks_work_order ON work_order_tasks(work_order_id);
CREATE INDEX idx_tasks_category ON work_order_tasks(task_category);
CREATE INDEX idx_deliverables_work_order ON work_order_deliverables(work_order_id);
CREATE INDEX idx_deliverables_type ON work_order_deliverables(deliverable_type);
CREATE INDEX idx_pdf_work_order ON work_orders_pdf_supplement(work_order_id);
CREATE INDEX idx_pdf_client ON work_orders_pdf_supplement(client_name, client_brand);
CREATE INDEX idx_pdf_store ON work_orders_pdf_supplement(store_number);
CREATE INDEX idx_pdf_contacts ON work_orders_pdf_supplement(onsite_contact_primary_name);

-- Enable foreign key constraints (SQLite specific)
PRAGMA foreign_keys = ON;

-- Create FTS (Full-Text Search) virtual table for search functionality
CREATE VIRTUAL TABLE work_orders_fts USING fts5(
    work_order_id,
    title,
    description,
    service_description_full,
    company_name,
    manager_name,
    provider_name,
    location_address,
    location_city,
    equipment_type,
    equipment_manufacturer,
    equipment_model,
    closeout_notes,
    resolution_summary,
    actions_taken,
    follow_up_notes,
    ticket_numbers,
    content='work_orders_markdown'
);

-- Trigger to keep FTS table in sync with main table
CREATE TRIGGER work_orders_fts_insert AFTER INSERT ON work_orders_markdown BEGIN
    INSERT INTO work_orders_fts(
        work_order_id, title, description, service_description_full,
        company_name, manager_name, provider_name, location_address,
        location_city, equipment_type, equipment_manufacturer,
        equipment_model, closeout_notes, resolution_summary,
        actions_taken, follow_up_notes, ticket_numbers
    ) VALUES (
        NEW.work_order_id, NEW.title, NEW.description, NEW.service_description_full,
        NEW.company_name, NEW.manager_name, NEW.provider_name, NEW.location_address,
        NEW.location_city, NEW.equipment_type, NEW.equipment_manufacturer,
        NEW.equipment_model, NEW.closeout_notes, NEW.resolution_summary,
        NEW.actions_taken, NEW.follow_up_notes, NEW.ticket_numbers
    );
END;

CREATE TRIGGER work_orders_fts_delete AFTER DELETE ON work_orders_markdown BEGIN
    DELETE FROM work_orders_fts WHERE work_order_id = OLD.work_order_id;
END;

CREATE TRIGGER work_orders_fts_update AFTER UPDATE ON work_orders_markdown BEGIN
    DELETE FROM work_orders_fts WHERE work_order_id = OLD.work_order_id;
    INSERT INTO work_orders_fts(
        work_order_id, title, description, service_description_full,
        company_name, manager_name, provider_name, location_address,
        location_city, equipment_type, equipment_manufacturer,
        equipment_model, closeout_notes, resolution_summary,
        actions_taken, follow_up_notes, ticket_numbers
    ) VALUES (
        NEW.work_order_id, NEW.title, NEW.description, NEW.service_description_full,
        NEW.company_name, NEW.manager_name, NEW.provider_name, NEW.location_address,
        NEW.location_city, NEW.equipment_type, NEW.equipment_manufacturer,
        NEW.equipment_model, NEW.closeout_notes, NEW.resolution_summary,
        NEW.actions_taken, NEW.follow_up_notes, NEW.ticket_numbers
    );
END;

-- Trigger to update the updated_at timestamp
CREATE TRIGGER work_orders_updated_at AFTER UPDATE ON work_orders_markdown BEGIN
    UPDATE work_orders_markdown SET updated_at = CURRENT_TIMESTAMP WHERE work_order_id = NEW.work_order_id;
END;

-- Trigger to populate search_text field
CREATE TRIGGER work_orders_search_text_insert AFTER INSERT ON work_orders_markdown BEGIN
    UPDATE work_orders_markdown SET search_text = (
        COALESCE(NEW.work_order_id, '') || ' ' ||
        COALESCE(NEW.title, '') || ' ' ||
        COALESCE(NEW.description, '') || ' ' ||
        COALESCE(NEW.service_description_full, '') || ' ' ||
        COALESCE(NEW.company_name, '') || ' ' ||
        COALESCE(NEW.manager_name, '') || ' ' ||
        COALESCE(NEW.provider_name, '') || ' ' ||
        COALESCE(NEW.location_address, '') || ' ' ||
        COALESCE(NEW.location_city, '') || ' ' ||
        COALESCE(NEW.equipment_type, '') || ' ' ||
        COALESCE(NEW.equipment_manufacturer, '') || ' ' ||
        COALESCE(NEW.equipment_model, '') || ' ' ||
        COALESCE(NEW.closeout_notes, '') || ' ' ||
        COALESCE(NEW.resolution_summary, '') || ' ' ||
        COALESCE(NEW.actions_taken, '') || ' ' ||
        COALESCE(NEW.follow_up_notes, '') || ' ' ||
        COALESCE(NEW.ticket_numbers, '')
    ) WHERE work_order_id = NEW.work_order_id;
END;

CREATE TRIGGER work_orders_search_text_update AFTER UPDATE ON work_orders_markdown BEGIN
    UPDATE work_orders_markdown SET search_text = (
        COALESCE(NEW.work_order_id, '') || ' ' ||
        COALESCE(NEW.title, '') || ' ' ||
        COALESCE(NEW.description, '') || ' ' ||
        COALESCE(NEW.service_description_full, '') || ' ' ||
        COALESCE(NEW.company_name, '') || ' ' ||
        COALESCE(NEW.manager_name, '') || ' ' ||
        COALESCE(NEW.provider_name, '') || ' ' ||
        COALESCE(NEW.location_address, '') || ' ' ||
        COALESCE(NEW.location_city, '') || ' ' ||
        COALESCE(NEW.equipment_type, '') || ' ' ||
        COALESCE(NEW.equipment_manufacturer, '') || ' ' ||
        COALESCE(NEW.equipment_model, '') || ' ' ||
        COALESCE(NEW.closeout_notes, '') || ' ' ||
        COALESCE(NEW.resolution_summary, '') || ' ' ||
        COALESCE(NEW.actions_taken, '') || ' ' ||
        COALESCE(NEW.follow_up_notes, '') || ' ' ||
        COALESCE(NEW.ticket_numbers, '')
    ) WHERE work_order_id = NEW.work_order_id;
END; 