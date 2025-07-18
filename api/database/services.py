"""
Database Services Layer
======================
High-level database operations for clinical assessment sessions, scores, and chat history.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from .models import AssessmentSession, QuestionResponse, ChatMessage, AssessmentScore
from .connection import get_db_session

logger = logging.getLogger(__name__)


class DatabaseService:
    """Main database service for clinical assessments"""
    
    @staticmethod
    def create_session(patient_id: str, metadata: Optional[Dict] = None) -> AssessmentSession:
        """Create a new assessment session"""
        try:
            with get_db_session() as db:
                session = AssessmentSession(
                    patient_id=patient_id,
                    metadata_json=metadata or {}
                )
                db.add(session)
                db.flush()  # Get the session_id
                
                # Add initial chat message
                welcome_msg = ChatMessage(
                    session_id=session.session_id,
                    role="system",
                    content="Assessment session started",
                    message_type="system"
                )
                db.add(welcome_msg)
                
                # Refresh to ensure all attributes are loaded
                db.refresh(session)
                
                # Expunge the session from the database session to avoid binding issues
                db.expunge(session)
                
                logger.info(f"Created new assessment session: {session.session_id}")
                return session
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    @staticmethod
    def get_session(session_id: str) -> Optional[AssessmentSession]:
        """Get session by ID"""
        try:
            with get_db_session() as db:
                session = db.query(AssessmentSession).filter(
                    AssessmentSession.session_id == session_id
                ).first()
                
                if session:
                    # Update last activity
                    session.last_activity = datetime.utcnow()
                
                return session
                
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    @staticmethod
    def update_session_progress(
        session_id: str, 
        phase: str, 
        state: str, 
        question_index: int,
        questions_completed: int
    ) -> bool:
        """Update session progress"""
        try:
            with get_db_session() as db:
                session = db.query(AssessmentSession).filter(
                    AssessmentSession.session_id == session_id
                ).first()
                
                if not session:
                    logger.warning(f"Session {session_id} not found for progress update")
                    return False
                
                session.current_phase = phase
                session.current_state = state
                session.current_question_index = question_index
                session.questions_completed = questions_completed
                session.last_activity = datetime.utcnow()
                
                # Update phase-specific counters
                if phase == "iadl" and questions_completed <= 8:
                    session.iadl_questions_completed = questions_completed
                elif phase == "adl":
                    session.iadl_questions_completed = 8  # All IADL done
                    session.adl_questions_completed = max(0, questions_completed - 8)
                elif phase == "complete":
                    session.iadl_questions_completed = 8
                    session.adl_questions_completed = 10
                    session.completed_at = datetime.utcnow()
                
                logger.info(f"Updated progress for session {session_id}: {phase}/{state}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update session progress: {e}")
            return False
    
    @staticmethod
    def save_question_response(
        session_id: str,
        question_id: str,
        question_text: str,
        question_domain: str,
        assessment_type: str,
        user_response: str,
        interpreted_score: float,
        confidence: float,
        reasoning: str,
        needs_clarification: bool = False,
        clarification_question: Optional[str] = None,
        raw_llm_response: Optional[Dict] = None
    ) -> QuestionResponse:
        """Save a question response with clinical interpretation"""
        try:
            with get_db_session() as db:
                response = QuestionResponse(
                    session_id=session_id,
                    question_id=question_id,
                    question_text=question_text,
                    question_domain=question_domain,
                    assessment_type=assessment_type,
                    user_response=user_response,
                    interpreted_score=interpreted_score,
                    confidence=confidence,
                    reasoning=reasoning,
                    needs_clarification=needs_clarification,
                    clarification_question=clarification_question,
                    raw_llm_response=raw_llm_response
                )
                db.add(response)
                
                logger.info(f"Saved response for {question_id} in session {session_id}")
                return response
                
        except Exception as e:
            logger.error(f"Failed to save question response: {e}")
            raise
    
    @staticmethod
    def add_chat_message(
        session_id: str,
        role: str,
        content: str,
        message_type: Optional[str] = None,
        question_id: Optional[str] = None
    ) -> ChatMessage:
        """Add a chat message to the conversation history"""
        try:
            with get_db_session() as db:
                message = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    message_type=message_type,
                    question_id=question_id
                )
                db.add(message)
                
                logger.debug(f"Added {role} message to session {session_id}")
                return message
                
        except Exception as e:
            logger.error(f"Failed to add chat message: {e}")
            raise
    
    @staticmethod
    def calculate_and_save_scores(session_id: str) -> Dict[str, Any]:
        """Calculate and save assessment scores"""
        try:
            with get_db_session() as db:
                # Get all responses for this session
                responses = db.query(QuestionResponse).filter(
                    QuestionResponse.session_id == session_id
                ).all()
                
                if not responses:
                    logger.warning(f"No responses found for session {session_id}")
                    return {}
                
                # Calculate IADL scores
                iadl_responses = [r for r in responses if r.assessment_type == "IADL"]
                iadl_score = sum(r.interpreted_score for r in iadl_responses)
                iadl_confidence = sum(r.confidence for r in iadl_responses) / len(iadl_responses) if iadl_responses else 0
                
                # Calculate ADL scores  
                adl_responses = [r for r in responses if r.assessment_type == "ADL"]
                adl_score = sum(r.interpreted_score for r in adl_responses)
                adl_confidence = sum(r.confidence for r in adl_responses) / len(adl_responses) if adl_responses else 0
                
                # Save IADL total score
                if iadl_responses:
                    iadl_score_record = AssessmentScore(
                        session_id=session_id,
                        score_type="iadl_total",
                        raw_score=iadl_score,
                        max_possible_score=8.0,
                        percentage_score=(iadl_score / 8.0) * 100,
                        confidence_average=iadl_confidence,
                        responses_count=len(iadl_responses),
                        interpretation=DatabaseService._interpret_iadl_score(iadl_score)
                    )
                    db.add(iadl_score_record)
                
                # Save ADL total score
                if adl_responses:
                    adl_score_record = AssessmentScore(
                        session_id=session_id,
                        score_type="adl_total", 
                        raw_score=adl_score,
                        max_possible_score=100.0,
                        percentage_score=adl_score,  # ADL is already percentage
                        confidence_average=adl_confidence,
                        responses_count=len(adl_responses),
                        interpretation=DatabaseService._interpret_adl_score(adl_score)
                    )
                    db.add(adl_score_record)
                
                scores_summary = {
                    "iadl_score": iadl_score,
                    "iadl_max": 8,
                    "iadl_percentage": (iadl_score / 8.0) * 100,
                    "iadl_confidence": iadl_confidence,
                    "adl_score": adl_score,
                    "adl_max": 100,
                    "adl_percentage": adl_score,
                    "adl_confidence": adl_confidence,
                    "total_responses": len(responses)
                }
                
                logger.info(f"Calculated scores for session {session_id}: {scores_summary}")
                return scores_summary
                
        except Exception as e:
            logger.error(f"Failed to calculate scores for session {session_id}: {e}")
            return {}
    
    @staticmethod
    def get_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete session summary with scores and history"""
        try:
            with get_db_session() as db:
                # Get session
                session = db.query(AssessmentSession).filter(
                    AssessmentSession.session_id == session_id
                ).first()
                
                if not session:
                    return None
                
                # Get responses
                responses = db.query(QuestionResponse).filter(
                    QuestionResponse.session_id == session_id
                ).order_by(QuestionResponse.response_timestamp).all()
                
                # Get chat history
                chat_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(ChatMessage.timestamp).all()
                
                # Get scores
                scores = db.query(AssessmentScore).filter(
                    AssessmentScore.session_id == session_id
                ).all()
                
                # Build summary
                summary = {
                    "session_info": session.to_dict(),
                    "scores": {
                        score.score_type: {
                            "raw_score": score.raw_score,
                            "max_possible_score": score.max_possible_score,
                            "percentage_score": score.percentage_score,
                            "confidence_average": score.confidence_average,
                            "interpretation": score.interpretation,
                            "responses_count": score.responses_count
                        }
                        for score in scores
                    },
                    "confidence_metrics": {
                        "overall_confidence": sum(r.confidence for r in responses) / len(responses) if responses else 0,
                        "low_confidence_count": len([r for r in responses if r.confidence < 0.7]),
                        "clarification_requests": len([r for r in responses if r.needs_clarification])
                    },
                    "conversation_history": [msg.to_dict() for msg in chat_messages],
                    "responses": [resp.to_dict() for resp in responses]
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            return None
    
    @staticmethod
    def get_active_sessions(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of active sessions"""
        try:
            with get_db_session() as db:
                query = db.query(AssessmentSession).filter(
                    AssessmentSession.current_state != "completed"
                )
                
                if patient_id:
                    query = query.filter(AssessmentSession.patient_id == patient_id)
                
                sessions = query.order_by(desc(AssessmentSession.last_activity)).all()
                
                return [session.to_dict() for session in sessions]
                
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete a session and all related data"""
        try:
            with get_db_session() as db:
                session = db.query(AssessmentSession).filter(
                    AssessmentSession.session_id == session_id
                ).first()
                
                if not session:
                    return False
                
                db.delete(session)  # Cascade will delete related records
                logger.info(f"Deleted session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    @staticmethod
    def _interpret_iadl_score(score: float) -> str:
        """Interpret IADL score (0-8 scale)"""
        if score >= 7:
            return "independent"
        elif score >= 5:
            return "mild_impairment"
        elif score >= 3:
            return "moderate_impairment"
        else:
            return "severe_impairment"
    
    @staticmethod
    def _interpret_adl_score(score: float) -> str:
        """Interpret ADL score (0-100 scale)"""
        if score >= 90:
            return "independent"
        elif score >= 70:
            return "mild_impairment"
        elif score >= 40:
            return "moderate_impairment"
        else:
            return "severe_impairment"


class SessionManager:
    """Session-specific database operations"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    def get_session(self) -> Optional[AssessmentSession]:
        """Get the current session"""
        return DatabaseService.get_session(self.session_id)
    
    def update_progress(self, phase: str, state: str, question_index: int, questions_completed: int):
        """Update session progress"""
        return DatabaseService.update_session_progress(
            self.session_id, phase, state, question_index, questions_completed
        )
    
    def save_response(self, **kwargs):
        """Save a question response"""
        return DatabaseService.save_question_response(self.session_id, **kwargs)
    
    def add_message(self, role: str, content: str, **kwargs):
        """Add a chat message"""
        return DatabaseService.add_chat_message(self.session_id, role, content, **kwargs)
    
    def calculate_scores(self):
        """Calculate and save scores"""
        return DatabaseService.calculate_and_save_scores(self.session_id)
    
    def get_summary(self):
        """Get session summary"""
        return DatabaseService.get_session_summary(self.session_id)
