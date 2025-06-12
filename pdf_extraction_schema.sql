-- PDF Extraction Schema for FieldNation Work Orders
-- Comprehensive data extraction from PDF files with no text limits

CREATE TABLE IF NOT EXISTS work_orders_pdf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- File Information
    pdf_filename TEXT NOT NULL,
    pdf_file_path TEXT,
    pdf_file_size INTEGER,
    pdf_page_count INTEGER,
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extraction_quality_score REAL DEFAULT 0.0,
    
    -- Work Order Identification
    work_order_id TEXT,
    work_order_number TEXT,
    field_nation_id TEXT,
    reference_number TEXT,
    
    -- Basic Information (No text limits)
    title TEXT,
    description TEXT,
    full_description TEXT,
    scope_of_work TEXT,
    work_summary TEXT,
    service_type TEXT,
    work_category TEXT,
    priority_level TEXT,
    
    -- Status and Dates
    status TEXT,
    status_detail TEXT,
    date_created TEXT,
    date_posted TEXT,
    date_scheduled TEXT,
    date_started TEXT,
    date_completed TEXT,
    date_approved TEXT,
    date_paid TEXT,
    
    -- Company Information
    company_name TEXT,
    company_id TEXT,
    company_address TEXT,
    company_phone TEXT,
    company_email TEXT,
    company_website TEXT,
    company_contact_person TEXT,
    
    -- Client/Buyer Information
    buyer_name TEXT,
    buyer_company TEXT,
    buyer_email TEXT,
    buyer_phone TEXT,
    buyer_address TEXT,
    buyer_contact_instructions TEXT,
    
    -- Provider Information
    provider_name TEXT,
    provider_id TEXT,
    provider_email TEXT,
    provider_phone TEXT,
    provider_rating REAL,
    provider_reviews_count INTEGER,
    
    -- Location Details
    work_location_name TEXT,
    work_location_address TEXT,
    work_location_city TEXT,
    work_location_state TEXT,
    work_location_zip TEXT,
    work_location_country TEXT DEFAULT 'USA',
    work_location_coordinates TEXT,
    work_location_instructions TEXT,
    parking_instructions TEXT,
    access_instructions TEXT,
    
    -- Financial Information
    total_amount REAL,
    base_pay REAL,
    bonus_amount REAL,
    additional_pay REAL,
    expense_allowance REAL,
    mileage_reimbursement REAL,
    hourly_rate REAL,
    overtime_rate REAL,
    currency TEXT DEFAULT 'USD',
    payment_terms TEXT,
    payment_method TEXT,
    
    -- Time Information
    estimated_duration TEXT,
    scheduled_start_time TEXT,
    scheduled_end_time TEXT,
    actual_start_time TEXT,
    actual_end_time TEXT,
    total_hours_worked REAL,
    break_time REAL,
    travel_time REAL,
    
    -- Requirements and Qualifications
    required_skills TEXT,
    required_certifications TEXT,
    required_tools TEXT,
    required_equipment TEXT,
    background_check_required BOOLEAN DEFAULT FALSE,
    drug_test_required BOOLEAN DEFAULT FALSE,
    insurance_required BOOLEAN DEFAULT FALSE,
    
    -- Equipment and Technology
    equipment_provided TEXT,
    equipment_needed TEXT,
    technology_requirements TEXT,
    software_requirements TEXT,
    hardware_specifications TEXT,
    network_requirements TEXT,
    
    -- Contact Information
    primary_contact_name TEXT,
    primary_contact_phone TEXT,
    primary_contact_email TEXT,
    secondary_contact_name TEXT,
    secondary_contact_phone TEXT,
    secondary_contact_email TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    
    -- Check-in/Check-out
    check_in_required BOOLEAN DEFAULT FALSE,
    check_in_contact TEXT,
    check_in_phone TEXT,
    check_in_instructions TEXT,
    check_out_required BOOLEAN DEFAULT FALSE,
    check_out_contact TEXT,
    check_out_phone TEXT,
    check_out_instructions TEXT,
    
    -- Work Details
    work_instructions TEXT,
    special_instructions TEXT,
    safety_requirements TEXT,
    dress_code TEXT,
    security_requirements TEXT,
    confidentiality_requirements TEXT,
    
    -- Completion and Approval
    completion_requirements TEXT,
    approval_process TEXT,
    approval_contact_name TEXT,
    approval_contact_phone TEXT,
    approval_contact_email TEXT,
    deliverables TEXT,
    documentation_required TEXT,
    photos_required BOOLEAN DEFAULT FALSE,
    signature_required BOOLEAN DEFAULT FALSE,
    
    -- Issues and Notes
    known_issues TEXT,
    troubleshooting_notes TEXT,
    previous_work_notes TEXT,
    vendor_notes TEXT,
    client_notes TEXT,
    provider_notes TEXT,
    admin_notes TEXT,
    
    -- Custom Fields and Metadata
    custom_field_1_name TEXT,
    custom_field_1_value TEXT,
    custom_field_2_name TEXT,
    custom_field_2_value TEXT,
    custom_field_3_name TEXT,
    custom_field_3_value TEXT,
    custom_field_4_name TEXT,
    custom_field_4_value TEXT,
    custom_field_5_name TEXT,
    custom_field_5_value TEXT,
    
    -- Raw Extracted Text
    raw_text_page_1 TEXT,
    raw_text_page_2 TEXT,
    raw_text_page_3 TEXT,
    raw_text_page_4 TEXT,
    raw_text_page_5 TEXT,
    raw_text_full TEXT,
    
    -- Structured Data (JSON)
    extracted_tables TEXT, -- JSON array of tables found
    extracted_forms TEXT,  -- JSON object of form fields
    extracted_signatures TEXT, -- JSON array of signature locations
    extracted_images TEXT, -- JSON array of image descriptions
    
    -- Quality and Confidence
    text_extraction_confidence REAL DEFAULT 0.0,
    data_completeness_score REAL DEFAULT 0.0,
    manual_review_required BOOLEAN DEFAULT FALSE,
    extraction_errors TEXT,
    
    -- Processing Flags
    is_processed BOOLEAN DEFAULT FALSE,
    is_merged_with_markdown BOOLEAN DEFAULT FALSE,
    needs_manual_review BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pdf_work_order_id ON work_orders_pdf(work_order_id);
CREATE INDEX IF NOT EXISTS idx_pdf_filename ON work_orders_pdf(pdf_filename);
CREATE INDEX IF NOT EXISTS idx_pdf_company_name ON work_orders_pdf(company_name);
CREATE INDEX IF NOT EXISTS idx_pdf_status ON work_orders_pdf(status);
CREATE INDEX IF NOT EXISTS idx_pdf_date_created ON work_orders_pdf(date_created);
CREATE INDEX IF NOT EXISTS idx_pdf_extraction_date ON work_orders_pdf(extraction_date);
CREATE INDEX IF NOT EXISTS idx_pdf_is_processed ON work_orders_pdf(is_processed);

-- View for merged work order data (will be used later)
CREATE VIEW IF NOT EXISTS work_orders_complete AS
SELECT 
    COALESCE(pdf.work_order_id, md.work_order_id) as work_order_id,
    COALESCE(pdf.title, md.title) as title,
    COALESCE(pdf.company_name, md.company_name) as company_name,
    COALESCE(pdf.status, md.status) as status,
    COALESCE(pdf.total_amount, md.total_paid) as total_amount,
    
    -- Prefer PDF data for detailed fields, fallback to markdown
    COALESCE(pdf.full_description, pdf.description, md.service_description_full, md.description) as description,
    COALESCE(pdf.work_location_address, md.location_address) as location_address,
    COALESCE(pdf.work_location_city, md.location_city) as location_city,
    COALESCE(pdf.work_location_state, md.location_state) as location_state,
    
    -- Source indicators
    CASE WHEN pdf.id IS NOT NULL THEN TRUE ELSE FALSE END as has_pdf_data,
    CASE WHEN md.work_order_id IS NOT NULL THEN TRUE ELSE FALSE END as has_markdown_data,
    
    -- Quality scores
    pdf.extraction_quality_score as pdf_quality,
    md.data_quality_score as markdown_quality,
    
    -- Timestamps
    pdf.extraction_date as pdf_extracted_at,
    md.created_at as markdown_created_at
    
FROM work_orders_pdf pdf
FULL OUTER JOIN work_orders_markdown md ON pdf.work_order_id = md.work_order_id; 