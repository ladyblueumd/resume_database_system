-- Enhanced Document Management Schema for Resume Database System
-- Handles both Markdown and PDF work order documents

-- 1. Document Files Registry
CREATE TABLE document_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- File Identification
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_type TEXT CHECK(file_type IN ('markdown', 'pdf')) NOT NULL,
    file_size INTEGER,
    file_hash TEXT, -- SHA256 hash for duplicate detection
    
    -- Work Order Identification  
    work_order_id TEXT NOT NULL, -- Extracted from filename
    work_order_url TEXT,
    
    -- File Metadata
    extraction_timestamp DATETIME,
    processor_version TEXT,
    extraction_method TEXT, -- 'automated', 'manual', 'batch'
    
    -- Content Status
    processing_status TEXT CHECK(processing_status IN ('pending', 'processing', 'completed', 'error', 'skipped')) DEFAULT 'pending',
    content_extracted BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    quality_score DECIMAL(3,2), -- 0.00 to 1.00
    
    -- Duplicate Management
    is_duplicate BOOLEAN DEFAULT FALSE,
    master_document_id INTEGER REFERENCES document_files(id),
    duplicate_reason TEXT,
    
    -- Source Folder Classification
    source_folder TEXT CHECK(source_folder IN ('downloaded_work_orders', 'fieldnation_pdfs', 'not_used_md_files')) NOT NULL,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_processed DATETIME
);

-- 2. Extracted Content Storage
CREATE TABLE document_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_file_id INTEGER NOT NULL REFERENCES document_files(id) ON DELETE CASCADE,
    
    -- Raw Content
    raw_text TEXT, -- Full extracted text
    structured_data TEXT, -- JSON of parsed sections
    
    -- Work Order Details (extracted from document)
    work_order_title TEXT,
    company_name TEXT,
    service_date DATE,
    completion_date DATE,
    
    -- Financial Information
    pay_amount TEXT, -- Keep as text initially for parsing
    hourly_rate TEXT,
    hours_logged TEXT,
    
    -- Location Data
    work_location TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    
    -- Personnel
    assigned_provider TEXT,
    provider_id TEXT,
    manager_contact TEXT,
    site_contact TEXT,
    
    -- Service Information
    service_description TEXT,
    work_type TEXT,
    tasks_completed TEXT,
    closeout_notes TEXT,
    
    -- Technical Details
    equipment_used TEXT,
    software_mentioned TEXT,
    tools_required TEXT,
    technologies TEXT,
    
    -- Quality Metrics
    client_rating TEXT,
    satisfaction_score TEXT,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Document Processing Log
CREATE TABLE document_processing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_file_id INTEGER NOT NULL REFERENCES document_files(id),
    
    -- Processing Details
    processing_stage TEXT NOT NULL, -- 'file_scan', 'content_extraction', 'data_parsing', 'validation'
    status TEXT CHECK(status IN ('started', 'completed', 'failed', 'skipped')) NOT NULL,
    
    -- Results
    records_extracted INTEGER DEFAULT 0,
    errors_encountered INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    
    -- Error Information
    error_message TEXT,
    error_details TEXT, -- JSON of detailed error info
    
    -- Performance Metrics
    processing_time_ms INTEGER,
    memory_used_mb DECIMAL(8,2),
    
    -- Processing Context
    processor_version TEXT,
    processing_mode TEXT, -- 'batch', 'individual', 'retry'
    
    -- Timestamps
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- 4. Work Order Relationships (connects documents to main work orders table)
CREATE TABLE document_work_order_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_file_id INTEGER NOT NULL REFERENCES document_files(id),
    work_order_id INTEGER REFERENCES fieldnation_work_orders(id),
    
    -- Mapping Quality
    match_confidence DECIMAL(3,2), -- 0.00 to 1.00
    match_method TEXT, -- 'exact_id', 'fuzzy_match', 'manual'
    verified BOOLEAN DEFAULT FALSE,
    
    -- Conflict Resolution
    data_conflicts TEXT, -- JSON of conflicting fields
    resolution_notes TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system'
);

-- 5. Document Tags and Categories
CREATE TABLE document_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_file_id INTEGER NOT NULL REFERENCES document_files(id),
    
    -- Classification
    tag_type TEXT CHECK(tag_type IN ('industry', 'technology', 'skill', 'location', 'client', 'custom')) NOT NULL,
    tag_value TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.00,
    
    -- Source
    created_by TEXT DEFAULT 'system', -- 'system', 'user', 'ai'
    extraction_method TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. Batch Processing Jobs
CREATE TABLE batch_processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Job Details
    job_name TEXT NOT NULL,
    job_type TEXT CHECK(job_type IN ('import', 'reprocess', 'cleanup', 'validation')) NOT NULL,
    source_folder TEXT,
    
    -- Scope
    total_files INTEGER,
    files_processed INTEGER DEFAULT 0,
    files_successful INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    files_skipped INTEGER DEFAULT 0,
    
    -- Status
    status TEXT CHECK(status IN ('queued', 'running', 'completed', 'failed', 'cancelled')) DEFAULT 'queued',
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    
    -- Performance
    estimated_duration_minutes INTEGER,
    actual_duration_minutes INTEGER,
    
    -- Results
    summary_report TEXT, -- JSON summary
    error_summary TEXT,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    
    -- Job Parameters
    processing_options TEXT -- JSON of job configuration
);

-- Indexes for Performance
CREATE INDEX idx_doc_files_work_order_id ON document_files(work_order_id);
CREATE INDEX idx_doc_files_type ON document_files(file_type);
CREATE INDEX idx_doc_files_status ON document_files(processing_status);
CREATE INDEX idx_doc_files_source ON document_files(source_folder);
CREATE INDEX idx_doc_files_hash ON document_files(file_hash);

CREATE INDEX idx_doc_content_work_order ON document_content(document_file_id);
CREATE INDEX idx_doc_content_company ON document_content(company_name);
CREATE INDEX idx_doc_content_date ON document_content(service_date);

CREATE INDEX idx_doc_mapping_doc_id ON document_work_order_mapping(document_file_id);
CREATE INDEX idx_doc_mapping_wo_id ON document_work_order_mapping(work_order_id);

CREATE INDEX idx_doc_tags_file_id ON document_tags(document_file_id);
CREATE INDEX idx_doc_tags_type_value ON document_tags(tag_type, tag_value);

CREATE INDEX idx_batch_jobs_status ON batch_processing_jobs(status);
CREATE INDEX idx_batch_jobs_created ON batch_processing_jobs(created_at);

-- Views for Common Queries
CREATE VIEW document_summary AS
SELECT 
    df.id,
    df.file_name,
    df.work_order_id,
    df.file_type,
    df.source_folder,
    df.processing_status,
    dc.company_name,
    dc.service_date,
    dc.work_order_title,
    CASE 
        WHEN dwom.work_order_id IS NOT NULL THEN 'mapped'
        ELSE 'unmapped'
    END as mapping_status,
    df.created_at
FROM document_files df
LEFT JOIN document_content dc ON df.id = dc.document_file_id
LEFT JOIN document_work_order_mapping dwom ON df.id = dwom.document_file_id;

CREATE VIEW processing_statistics AS
SELECT 
    source_folder,
    file_type,
    processing_status,
    COUNT(*) as file_count,
    COUNT(CASE WHEN content_extracted THEN 1 END) as extracted_count,
    COUNT(CASE WHEN is_duplicate THEN 1 END) as duplicate_count
FROM document_files
GROUP BY source_folder, file_type, processing_status;

-- Triggers for Auto-updating timestamps
CREATE TRIGGER update_document_files_timestamp 
    AFTER UPDATE ON document_files
BEGIN
    UPDATE document_files SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_document_content_timestamp 
    AFTER UPDATE ON document_content
BEGIN
    UPDATE document_content SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END; 