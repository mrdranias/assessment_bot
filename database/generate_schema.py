#!/usr/bin/env python3
"""
Generate SQL schema from SQLAlchemy models

This script creates a complete SQL schema file from the SQLAlchemy models
in api/database/models.py, giving you the best of both worlds:
- SQLAlchemy convenience for development
- Raw SQL schema for documentation and database management
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.schema import CreateTable

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database.models import Base, AssessmentSession, QuestionResponse, ChatMessage, AssessmentScore

def generate_schema():
    """Generate complete SQL schema from SQLAlchemy models"""
    
    # Create a temporary engine for schema generation
    engine = create_engine('postgresql://user:pass@localhost/temp', echo=False)
    
    # Generate CREATE TABLE statements
    schema_sql = []
    
    # Add header
    schema_sql.append("-- ============================================================================")
    schema_sql.append("--  AssessBot2 Clinical Assessment Database Schema")
    schema_sql.append("--  Generated from SQLAlchemy models in api/database/models.py")
    schema_sql.append("-- ============================================================================")
    schema_sql.append("")
    schema_sql.append("-- Create database")
    schema_sql.append("CREATE DATABASE IF NOT EXISTS adl_assessment;")
    schema_sql.append("\\c adl_assessment;")
    schema_sql.append("")
    schema_sql.append("-- Extensions")
    schema_sql.append("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    schema_sql.append("")
    
    # Generate tables in dependency order
    tables = [AssessmentSession, QuestionResponse, ChatMessage, AssessmentScore]
    
    for table_class in tables:
        table = table_class.__table__
        create_table_sql = str(CreateTable(table).compile(engine)).strip()
        
        # Clean up the SQL formatting
        create_table_sql = create_table_sql.replace('\\n', '\n')
        
        schema_sql.append(f"-- Table: {table.name}")
        schema_sql.append(f"-- Model: {table_class.__name__}")
        schema_sql.append(create_table_sql + ";")
        schema_sql.append("")
    
    # Add indexes
    schema_sql.append("-- Indexes for performance")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_question_responses_session_id ON question_responses(session_id);")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_question_responses_question_id ON question_responses(question_id);")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_assessment_scores_session_id ON assessment_scores(session_id);")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_assessment_scores_score_type ON assessment_scores(score_type);")
    schema_sql.append("CREATE INDEX IF NOT EXISTS idx_assessment_sessions_current_phase ON assessment_sessions(current_phase);")
    schema_sql.append("")
    
    # Add grants
    schema_sql.append("-- Permissions")
    schema_sql.append("GRANT ALL PRIVILEGES ON DATABASE adl_assessment TO postgres;")
    schema_sql.append("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;")
    schema_sql.append("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;")
    schema_sql.append("")
    
    # Add health check
    schema_sql.append("-- Health check table")
    schema_sql.append("CREATE TABLE IF NOT EXISTS system_health (")
    schema_sql.append("    id SERIAL PRIMARY KEY,")
    schema_sql.append("    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
    schema_sql.append("    status VARCHAR(20) DEFAULT 'healthy'")
    schema_sql.append(");")
    schema_sql.append("")
    schema_sql.append("-- Initial health check")
    schema_sql.append("INSERT INTO system_health (status) VALUES ('schema_initialized');")
    schema_sql.append("")
    schema_sql.append("-- Schema generation complete")
    schema_sql.append("SELECT 'AssessBot2 database schema created successfully' AS status;")
    
    return '\n'.join(schema_sql)

if __name__ == "__main__":
    schema = generate_schema()
    
    # Write to file
    output_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(output_path, 'w') as f:
        f.write(schema)
    
    print(f"✅ SQL schema generated: {output_path}")
    print("📋 This schema is generated from SQLAlchemy models and can be used for:")
    print("   - Database documentation")
    print("   - Manual database setup")
    print("   - Schema comparison")
    print("   - Database migrations")
