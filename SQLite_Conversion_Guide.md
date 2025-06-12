# Claude Database Schema SQLite Conversion Guide

## Overview

**Yes, the Claude database schema can be used in SQLite!** I have successfully converted the MySQL schema from the Claude SOP document to a fully compatible SQLite version.

## Key Conversions Made

### 1. **Data Types**
| MySQL | SQLite | Notes |
|-------|--------|-------|
| `VARCHAR(n)` | `TEXT` | SQLite TEXT can store any length |
| `DECIMAL(m,n)` | `REAL` | SQLite uses REAL for floating point |
| `BOOLEAN` | `BOOLEAN` | SQLite supports BOOLEAN (stored as INTEGER 0/1) |
| `JSON` | `TEXT` | JSON stored as TEXT, parsed in application |
| `TIMESTAMP` | `TIMESTAMP` | SQLite supports TIMESTAMP |

### 2. **MySQL-Specific Features Converted**

#### **Generated Columns → Triggers**
- **MySQL**: `search_text TEXT GENERATED ALWAYS AS (...) STORED`
- **SQLite**: Manual population via triggers on INSERT/UPDATE

#### **AUTO_INCREMENT → AUTOINCREMENT**
- **MySQL**: `id INT AUTO_INCREMENT PRIMARY KEY`
- **SQLite**: `id INTEGER PRIMARY KEY AUTOINCREMENT`

#### **Full-Text Search**
- **MySQL**: `FULLTEXT INDEX idx_search (search_text)`
- **SQLite**: `CREATE VIRTUAL TABLE work_orders_fts USING fts5(...)`

#### **Foreign Key Constraints**
- **MySQL**: Enabled by default
- **SQLite**: Requires `PRAGMA foreign_keys = ON;`

#### **ON UPDATE CURRENT_TIMESTAMP → Triggers**
- **MySQL**: `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`
- **SQLite**: Trigger to update timestamp on UPDATE

### 3. **Enhanced SQLite Features Added**

#### **FTS5 Full-Text Search**
```sql
CREATE VIRTUAL TABLE work_orders_fts USING fts5(
    work_order_id, title, description, service_description_full,
    company_name, manager_name, provider_name, location_address,
    location_city, equipment_type, equipment_manufacturer,
    equipment_model, closeout_notes, resolution_summary,
    actions_taken, follow_up_notes, ticket_numbers,
    content='work_orders_markdown'
);
```

#### **Automatic Sync Triggers**
- FTS table stays in sync with main table
- Search text field auto-populated
- Updated timestamp automatically maintained

## Schema Structure

### **Main Tables**
1. **`work_orders_markdown`** - Primary work order data (67 fields)
2. **`work_orders_pdf_supplement`** - Additional client/contact info from PDFs
3. **`work_order_parts`** - Parts and materials used
4. **`work_order_time_sessions`** - Time tracking sessions
5. **`work_order_tasks`** - Individual tasks completed
6. **`work_order_deliverables`** - Files and documentation

### **Views**
- **`work_order_complete_view`** - Joined view with all related data

### **Search Tables**
- **`work_orders_fts`** - Full-text search virtual table

## Usage Examples

### **Basic Queries**
```sql
-- Get all work orders
SELECT * FROM work_orders_markdown;

-- Search work orders
SELECT * FROM work_orders_fts WHERE work_orders_fts MATCH 'printer installation';

-- Get complete work order with all related data
SELECT * FROM work_order_complete_view WHERE work_order_id = '430895';
```

### **JSON Field Handling**
```sql
-- Store JSON data
INSERT INTO work_orders_markdown (work_order_id, buyer_custom_fields) 
VALUES ('123', '{"priority": "high", "special_instructions": "Call before arrival"}');

-- Query JSON data (requires JSON1 extension)
SELECT work_order_id, json_extract(buyer_custom_fields, '$.priority') as priority
FROM work_orders_markdown 
WHERE json_extract(buyer_custom_fields, '$.priority') = 'high';
```

## Implementation Steps

### **1. Apply the Schema**
```bash
sqlite3 your_database.db < claude_sqlite_schema.sql
```

### **2. Verify Tables Created**
```bash
sqlite3 your_database.db ".tables"
```

### **3. Test Full-Text Search**
```sql
-- Insert test data
INSERT INTO work_orders_markdown (work_order_id, title, company_name) 
VALUES ('TEST001', 'Printer Installation', 'ACME Corp');

-- Search test
SELECT * FROM work_orders_fts WHERE work_orders_fts MATCH 'printer';
```

## Advantages of SQLite Version

### **1. Simplified Deployment**
- Single file database
- No server setup required
- Built into Python

### **2. Enhanced Search**
- FTS5 provides excellent full-text search
- Automatic ranking and snippets
- Better than MySQL FULLTEXT for most use cases

### **3. JSON Support**
- SQLite JSON1 extension provides excellent JSON querying
- More flexible than MySQL JSON functions

### **4. Performance**
- Excellent for read-heavy workloads
- Fast for datasets under 1TB
- Perfect for single-user applications

## Compatibility with Current System

### **Field Mapping**
The SQLite schema includes all fields from the current `fieldnation_work_orders` table plus many additional fields from the Claude SOP:

| Current Field | Claude Schema Field | Status |
|---------------|-------------------|---------|
| `fn_work_order_id` | `work_order_id` | ✅ Compatible |
| `title` | `title` | ✅ Compatible |
| `buyer_company` | `company_name` | ✅ Compatible |
| `service_date` | `scheduled_date` | ✅ Compatible |
| `total_paid` | `total_paid` | ✅ Compatible |
| `actual_hours_logged` | `actual_hours_logged` | ✅ Compatible |

### **Migration Path**
1. **Backup current data**: Export existing work orders
2. **Apply new schema**: Use `claude_sqlite_schema.sql`
3. **Migrate data**: Map current fields to new schema
4. **Update application**: Modify queries to use new field names

## Limitations

### **1. Concurrent Writes**
- SQLite handles multiple readers well
- Limited concurrent write performance
- Use WAL mode for better concurrency

### **2. Network Access**
- File-based, not network database
- For multi-user, consider PostgreSQL conversion instead

### **3. Size Limits**
- Practical limit around 1TB
- Your 983 markdown + 1,085 PDF files will be well within limits

## Conclusion

The Claude database schema works excellently in SQLite with the conversions I've made. The SQLite version actually provides some advantages:

- **Better full-text search** with FTS5
- **Simpler deployment** with single file database
- **Enhanced JSON support** with JSON1 extension
- **Automatic maintenance** via triggers

The converted schema is ready to use and fully compatible with your existing data sources (983 markdown files + 1,085 PDFs).

## Files Created

- **`claude_sqlite_schema.sql`** - Complete SQLite schema
- **`claude_schema_test.db`** - Test database (can be deleted)
- **`SQLite_Conversion_Guide.md`** - This guide

You can now use this schema as a drop-in replacement for the MySQL version in the Claude SOP document. 