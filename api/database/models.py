"""
Database Models for Clinical Assessment System
============================================
SQLAlchemy models for persisting session data, scores, and conversation history.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

Base = declarative_base()


class AssessmentSession(Base):
    """Main assessment session record"""
    __tablename__ = "assessment_sessions"
    
    # Primary key
    session_id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Session metadata
    patient_id = Column(String(100), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Session state
    current_phase = Column(String(20), nullable=False, default="welcome")  # welcome, iadl, adl, review, complete
    current_state = Column(String(20), nullable=False, default="processing")  # processing, awaiting_clarification, completed, error
    current_question_index = Column(Integer, default=0)
    
    # Progress tracking
    total_questions = Column(Integer, default=18)
    questions_completed = Column(Integer, default=0)
    iadl_questions_completed = Column(Integer, default=0)
    adl_questions_completed = Column(Integer, default=0)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    metadata_json = Column(JSON, nullable=True)
    
    # Relationships
    responses = relationship("QuestionResponse", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan") 
    scores = relationship("AssessmentScore", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "current_phase": self.current_phase,
            "current_state": self.current_state,
            "current_question_index": self.current_question_index,
            "total_questions": self.total_questions,
            "questions_completed": self.questions_completed,
            "iadl_questions_completed": self.iadl_questions_completed,
            "adl_questions_completed": self.adl_questions_completed,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "metadata": self.metadata_json
        }


class QuestionResponse(Base):
    """Individual question responses with clinical interpretation"""
    __tablename__ = "question_responses"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    session_id = Column(String(50), ForeignKey("assessment_sessions.session_id"), nullable=False)
    
    # Question details
    question_id = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    question_domain = Column(String(50), nullable=False)
    assessment_type = Column(String(10), nullable=False)  # IADL or ADL
    
    # User response
    user_response = Column(Text, nullable=False)
    response_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Clinical interpretation
    interpreted_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    needs_clarification = Column(Boolean, default=False)
    clarification_question = Column(Text, nullable=True)
    
    # Additional data
    raw_llm_response = Column(JSON, nullable=True)
    
    # Relationships
    session = relationship("AssessmentSession", back_populates="responses")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "question_domain": self.question_domain,
            "assessment_type": self.assessment_type,
            "user_response": self.user_response,
            "response_timestamp": self.response_timestamp.isoformat() if self.response_timestamp else None,
            "interpreted_score": self.interpreted_score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "raw_llm_response": self.raw_llm_response
        }


class ChatMessage(Base):
    """Chat conversation history"""
    __tablename__ = "chat_messages"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    session_id = Column(String(50), ForeignKey("assessment_sessions.session_id"), nullable=False)
    
    # Message details
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Message metadata
    message_type = Column(String(50), nullable=True)  # question, response, clarification, completion, error
    question_id = Column(String(100), nullable=True)  # Associated question if applicable
    
    # Relationships
    session = relationship("AssessmentSession", back_populates="chat_messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "message_type": self.message_type,
            "question_id": self.question_id
        }


class AssessmentScore(Base):
    """Calculated assessment scores and metrics"""
    __tablename__ = "assessment_scores"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    session_id = Column(String(50), ForeignKey("assessment_sessions.session_id"), nullable=False)
    
    # Score details
    score_type = Column(String(20), nullable=False)  # iadl_total, adl_total, iadl_individual, adl_individual
    domain = Column(String(50), nullable=True)  # For individual domain scores
    
    # Score values
    raw_score = Column(Float, nullable=False)
    max_possible_score = Column(Float, nullable=False)
    percentage_score = Column(Float, nullable=False)
    
    # Score metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence_average = Column(Float, nullable=True)
    responses_count = Column(Integer, nullable=True)
    
    # Additional metrics
    interpretation = Column(String(50), nullable=True)  # independent, mild_impairment, moderate_impairment, severe_impairment
    clinical_notes = Column(Text, nullable=True)
    
    # Relationships
    session = relationship("AssessmentSession", back_populates="scores")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert score to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "score_type": self.score_type,
            "domain": self.domain,
            "raw_score": self.raw_score,
            "max_possible_score": self.max_possible_score,
            "percentage_score": self.percentage_score,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "confidence_average": self.confidence_average,
            "responses_count": self.responses_count,
            "interpretation": self.interpretation,
            "clinical_notes": self.clinical_notes
        }


# Create indexes for better query performance
from sqlalchemy import Index

# Session indexes
Index('idx_sessions_patient_id', AssessmentSession.patient_id)
Index('idx_sessions_phase_state', AssessmentSession.current_phase, AssessmentSession.current_state)
Index('idx_sessions_started_at', AssessmentSession.started_at)

# Response indexes  
Index('idx_responses_session_question', QuestionResponse.session_id, QuestionResponse.question_id)
Index('idx_responses_timestamp', QuestionResponse.response_timestamp)
Index('idx_responses_assessment_type', QuestionResponse.assessment_type)

# Chat message indexes
Index('idx_chat_session_timestamp', ChatMessage.session_id, ChatMessage.timestamp)
Index('idx_chat_role_type', ChatMessage.role, ChatMessage.message_type)

# Score indexes
Index('idx_scores_session_type', AssessmentScore.session_id, AssessmentScore.score_type)
Index('idx_scores_calculated_at', AssessmentScore.calculated_at)
