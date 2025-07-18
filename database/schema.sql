-- ============================================================================
--  AssessBot2 Clinical Assessment Database Schema
--  Generated from SQLAlchemy models in api/database/models.py
-- ============================================================================

-- Create database
CREATE DATABASE IF NOT EXISTS adl_assessment;
\c adl_assessment;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: assessment_sessions
-- Model: AssessmentSession
CREATE TABLE assessment_sessions (
	session_id VARCHAR(50) NOT NULL, 
	patient_id VARCHAR(100) NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	last_activity TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	current_phase VARCHAR(20) NOT NULL, 
	current_state VARCHAR(20) NOT NULL, 
	current_question_index INTEGER, 
	total_questions INTEGER, 
	questions_completed INTEGER, 
	iadl_questions_completed INTEGER, 
	adl_questions_completed INTEGER, 
	error_count INTEGER, 
	last_error TEXT, 
	metadata_json JSON, 
	PRIMARY KEY (session_id)
);

-- Table: question_responses
-- Model: QuestionResponse
CREATE TABLE question_responses (
	id SERIAL NOT NULL, 
	session_id VARCHAR(50) NOT NULL, 
	question_id VARCHAR(100) NOT NULL, 
	question_text TEXT NOT NULL, 
	question_domain VARCHAR(50) NOT NULL, 
	assessment_type VARCHAR(10) NOT NULL, 
	user_response TEXT NOT NULL, 
	response_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	interpreted_score FLOAT NOT NULL, 
	confidence FLOAT NOT NULL, 
	reasoning TEXT NOT NULL, 
	needs_clarification BOOLEAN, 
	clarification_question TEXT, 
	raw_llm_response JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES assessment_sessions (session_id)
);

-- Table: chat_messages
-- Model: ChatMessage
CREATE TABLE chat_messages (
	id SERIAL NOT NULL, 
	session_id VARCHAR(50) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	message_type VARCHAR(50), 
	question_id VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES assessment_sessions (session_id)
);

-- Table: assessment_scores
-- Model: AssessmentScore
CREATE TABLE assessment_scores (
	id SERIAL NOT NULL, 
	session_id VARCHAR(50) NOT NULL, 
	score_type VARCHAR(20) NOT NULL, 
	domain VARCHAR(50), 
	raw_score FLOAT NOT NULL, 
	max_possible_score FLOAT NOT NULL, 
	percentage_score FLOAT NOT NULL, 
	calculated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	confidence_average FLOAT, 
	responses_count INTEGER, 
	interpretation VARCHAR(50), 
	clinical_notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES assessment_sessions (session_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_question_responses_session_id ON question_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_question_responses_question_id ON question_responses(question_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_assessment_scores_session_id ON assessment_scores(session_id);
CREATE INDEX IF NOT EXISTS idx_assessment_scores_score_type ON assessment_scores(score_type);
CREATE INDEX IF NOT EXISTS idx_assessment_sessions_current_phase ON assessment_sessions(current_phase);

-- Permissions
GRANT ALL PRIVILEGES ON DATABASE adl_assessment TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Health check table
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'healthy'
);

-- Initial health check
INSERT INTO system_health (status) VALUES ('schema_initialized');

-- Schema generation complete
SELECT 'AssessBot2 database schema created successfully' AS status;