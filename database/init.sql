-- Database initialization script for Clinical Assessment System
-- This script is run when the PostgreSQL container starts
-- The database 'adl_assessment' is already created by Docker environment variables

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The actual tables will be created by SQLAlchemy when the API starts
-- This script just ensures the database exists and any required extensions are installed

-- Create a simple health check table
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'healthy'
);

-- Insert initial health check record
INSERT INTO system_health (status) VALUES ('initialized');

-- Grant permissions to the postgres user
GRANT ALL PRIVILEGES ON DATABASE adl_assessment TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Log completion
SELECT 'Database initialization completed successfully' AS status;
