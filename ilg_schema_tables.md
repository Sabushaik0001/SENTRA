# PostgreSQL Schema for AI Purchase Order System

## Enable Extensions

``` sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
```

## documents

``` sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id VARCHAR(50),
    builder_id VARCHAR(50),
    document_type VARCHAR(50),
    file_name TEXT,
    s3_path TEXT,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## document_classifications

``` sql
CREATE TABLE document_classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    document_type VARCHAR(50),
    builder_id VARCHAR(50),
    format VARCHAR(50),
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## prompt_templates

``` sql
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    builder_id VARCHAR(50),
    document_type VARCHAR(50),
    version INT,
    prompt_text TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## selections

``` sql
CREATE TABLE selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id VARCHAR(50),
    option_code VARCHAR(50),
    description TEXT,
    category VARCHAR(10),
    quantity INT,
    color VARCHAR(100),
    location_number VARCHAR(50),
    change_order_status BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## takeoff_data

``` sql
CREATE TABLE takeoff_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id VARCHAR(50),
    room_name VARCHAR(100),
    std_material VARCHAR(100),
    option_code VARCHAR(50),
    subfloor VARCHAR(100),
    material_width FLOAT,
    cut_length FLOAT,
    sq_yards FLOAT,
    pad_sq_yards FLOAT,
    wood_tile_sqft FLOAT,
    shoe_base_lf FLOAT,
    cabinet_sides_lf FLOAT,
    toe_kick_lf FLOAT,
    nosing_lf FLOAT,
    threshold_lf FLOAT,
    t_molding_lf FLOAT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## takeoff_mapped

``` sql
CREATE TABLE takeoff_mapped (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id VARCHAR(50),
    option_code VARCHAR(50),
    room_name VARCHAR(100),
    material_type VARCHAR(100),
    quantity FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## material_substitution_matrix

``` sql
CREATE TABLE material_substitution_matrix (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    when_option_selected VARCHAR(50),
    replaces_material_type VARCHAR(100),
    room VARCHAR(100),
    with_material_type VARCHAR(100),
    builder_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## sap_materials

``` sql
CREATE TABLE sap_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sap_code VARCHAR(50) UNIQUE,
    description TEXT,
    material_category VARCHAR(100),
    trade_type VARCHAR(100),
    uom VARCHAR(20),
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## confirmed_mappings

``` sql
CREATE TABLE confirmed_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_name VARCHAR(255),
    sap_code VARCHAR(50),
    confidence_score FLOAT,
    approved_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## sundry_rules

``` sql
CREATE TABLE sundry_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_category VARCHAR(100),
    sundry_item VARCHAR(255),
    quantity_ratio FLOAT,
    uom VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## labor_rules

``` sql
CREATE TABLE labor_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_category VARCHAR(100),
    sap_labor_code VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## order_drafts

``` sql
CREATE TABLE order_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id VARCHAR(50),
    builder_id VARCHAR(50),
    order_status VARCHAR(50),
    total_amount FLOAT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## order_lines

``` sql
CREATE TABLE order_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES order_drafts(id) ON DELETE CASCADE,
    sap_material_code VARCHAR(50),
    description TEXT,
    quantity FLOAT,
    uom VARCHAR(20),
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## corrections

``` sql
CREATE TABLE corrections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID,
    field_name VARCHAR(100),
    original_value TEXT,
    corrected_value TEXT,
    corrected_by VARCHAR(100),
    corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## audit_events

``` sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID,
    event_type VARCHAR(100),
    user_id VARCHAR(100),
    duration_ms INT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## builder_configs

``` sql
CREATE TABLE builder_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    builder_id VARCHAR(50),
    builder_name VARCHAR(100),
    plan VARCHAR(100),
    selection_sheet_format VARCHAR(50),
    takeoff_sheet_format VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Indexes

``` sql
CREATE INDEX idx_documents_lot_id ON documents(lot_id);
CREATE INDEX idx_selections_lot_id ON selections(lot_id);
CREATE INDEX idx_takeoff_lot_id ON takeoff_data(lot_id);
CREATE INDEX idx_sap_code ON sap_materials(sap_code);
CREATE INDEX idx_confirmed_material ON confirmed_mappings(material_name);
```
