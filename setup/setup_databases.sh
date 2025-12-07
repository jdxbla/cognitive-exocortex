#!/bin/bash
# Cognitive Exocortex - Database Setup
# Run this after install_all.sh

set -e

echo "============================================"
echo "  Setting up Databases"
echo "============================================"

# Create PostgreSQL user and database
echo "[1/3] Creating PostgreSQL database..."
sudo -u postgres psql << 'EOF'
-- Create user
CREATE USER exocortex WITH PASSWORD 'exocortex_secure_2025';

-- Create database
CREATE DATABASE cognitive_exocortex OWNER exocortex;

-- Connect to database
\c cognitive_exocortex

-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE cognitive_exocortex TO exocortex;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO exocortex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO exocortex;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO exocortex;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO exocortex;
EOF

echo "[2/3] Creating database schemas..."
sudo -u postgres psql -d cognitive_exocortex << 'EOF'

-- ===========================================
-- PREDICTIVE INTELLIGENCE TABLES
-- ===========================================

-- File operations tracking
CREATE TABLE IF NOT EXISTS file_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    operation_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_extension VARCHAR(50),
    file_size BIGINT,
    directory_path TEXT NOT NULL,
    context JSONB,
    session_id UUID,
    device_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('file_operations', 'timestamp', if_not_exists => TRUE);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_file_ops_path ON file_operations(file_path);
CREATE INDEX IF NOT EXISTS idx_file_ops_type ON file_operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_file_ops_extension ON file_operations(file_extension);
CREATE INDEX IF NOT EXISTS idx_file_ops_directory ON file_operations(directory_path);

-- Prediction patterns (learned from operations)
CREATE TABLE IF NOT EXISTS prediction_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_type VARCHAR(50) NOT NULL,
    pattern_data JSONB NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    hit_count INTEGER DEFAULT 0,
    miss_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Current predictions cache
CREATE TABLE IF NOT EXISTS active_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    predicted_file TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    context JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- INFINITE UNDO TABLES
-- ===========================================

-- File versions (for infinite undo)
CREATE TABLE IF NOT EXISTS file_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    operation VARCHAR(50) NOT NULL,
    content_hash VARCHAR(64),
    storage_location TEXT,
    file_size BIGINT,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('file_versions', 'timestamp', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_versions_path ON file_versions(file_path);
CREATE INDEX IF NOT EXISTS idx_versions_hash ON file_versions(content_hash);

-- ===========================================
-- KNOWLEDGE GRAPH TABLES
-- ===========================================

-- File nodes
CREATE TABLE IF NOT EXISTS file_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT UNIQUE NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    embedding_id VARCHAR(100),
    metadata JSONB,
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- File relationships
CREATE TABLE IF NOT EXISTS file_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file_id UUID REFERENCES file_nodes(id) ON DELETE CASCADE,
    target_file_id UUID REFERENCES file_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_file_id, target_file_id, relationship_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_relationships_source ON file_relationships(source_file_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON file_relationships(target_file_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON file_relationships(relationship_type);

-- ===========================================
-- FOCUS MODE / COGNITIVE LOAD TABLES
-- ===========================================

-- User sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(100),
    session_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_end TIMESTAMPTZ,
    focus_score FLOAT,
    context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cognitive events
CREATE TABLE IF NOT EXISTS cognitive_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES user_sessions(id),
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_data JSONB,
    cognitive_load_estimate FLOAT
);

SELECT create_hypertable('cognitive_events', 'timestamp', if_not_exists => TRUE);

-- ===========================================
-- CRISIS PREVENTION TABLES
-- ===========================================

-- Protected files
CREATE TABLE IF NOT EXISTS protected_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT UNIQUE NOT NULL,
    protection_level VARCHAR(20) DEFAULT 'standard',
    reason TEXT,
    protected_at TIMESTAMPTZ DEFAULT NOW(),
    protected_by VARCHAR(100)
);

-- Dangerous operation log
CREATE TABLE IF NOT EXISTS dangerous_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_type VARCHAR(50) NOT NULL,
    target_path TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    was_prevented BOOLEAN DEFAULT FALSE,
    user_confirmed BOOLEAN DEFAULT FALSE,
    risk_score FLOAT,
    context JSONB
);

SELECT create_hypertable('dangerous_operations', 'timestamp', if_not_exists => TRUE);

-- ===========================================
-- NATURAL LANGUAGE COMMAND LOG
-- ===========================================

CREATE TABLE IF NOT EXISTS nl_commands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_input TEXT NOT NULL,
    parsed_intent VARCHAR(100),
    parsed_entities JSONB,
    executed_action TEXT,
    success BOOLEAN,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_time_ms INTEGER
);

SELECT create_hypertable('nl_commands', 'timestamp', if_not_exists => TRUE);

-- Grant all permissions to exocortex user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO exocortex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO exocortex;

EOF

echo "[3/3] Verifying Qdrant connection..."
curl -s http://localhost:6333/collections | head -20 || echo "Qdrant not ready yet - check docker logs"

echo ""
echo "============================================"
echo "  Database Setup Complete!"
echo "============================================"
echo ""
echo "PostgreSQL credentials:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: cognitive_exocortex"
echo "  User: exocortex"
echo "  Password: exocortex_secure_2025"
echo ""
echo "Tables created:"
echo "  - file_operations (TimescaleDB hypertable)"
echo "  - prediction_patterns"
echo "  - active_predictions"
echo "  - file_versions (TimescaleDB hypertable)"
echo "  - file_nodes"
echo "  - file_relationships"
echo "  - user_sessions"
echo "  - cognitive_events (TimescaleDB hypertable)"
echo "  - protected_files"
echo "  - dangerous_operations (TimescaleDB hypertable)"
echo "  - nl_commands (TimescaleDB hypertable)"
echo ""
