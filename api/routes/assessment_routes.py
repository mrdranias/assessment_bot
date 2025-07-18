"""
Assessment API Routes
====================
FastAPI endpoints for clinical ADL/IADL assessment conversations.
Provides REST API interface for the LLM conversation system.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..llm.llm_conversation import (
    AssessmentConversationManager,
    ConversationSession,
    AssessmentPhase,
    ConversationState
)
from ..llm.conversation_flow import ConversationFlowOrchestrator
# Import local neo4j service
from ..llm.neo4j_question_service import get_all_questions, get_assessment_order
# Import database services
from ..database import DatabaseService, SessionManager, get_db, database_health_check

# Logger instance
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class SessionCreateRequest(BaseModel):
    """Request to create a new assessment session"""
    patient_id: Optional[str] = Field(None, description="Optional patient identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional session metadata")


class SessionCreateResponse(BaseModel):
    """Response for session creation"""
    session_id: str = Field(description="Unique session identifier")
    message: str = Field(description="Welcome message from assistant")
    status: str = Field(description="Session status")
    phase: str = Field(description="Current assessment phase")
    progress: str = Field(description="Progress indicator (e.g., '0/18')")
    assessment_info: Dict[str, Any] = Field(description="Information about the assessment structure")


class UserInputRequest(BaseModel):
    """Request to process user input"""
    user_input: str = Field(description="User's response to the current question")
    session_id: str = Field(description="Session identifier")


class ConversationResponse(BaseModel):
    """Response from conversation processing"""
    session_id: str = Field(description="Session identifier")
    message: str = Field(description="Assistant's response")
    status: str = Field(description="Current session status")
    phase: str = Field(description="Current assessment phase")
    progress: str = Field(description="Progress indicator")
    should_continue: bool = Field(description="Whether conversation should continue")
    needs_clarification: Optional[bool] = Field(None, description="Whether response needs clarification")
    error: Optional[str] = Field(None, description="Error message if any")


class SessionSummaryResponse(BaseModel):
    """Complete session summary"""
    session_info: Dict[str, Any] = Field(description="Session metadata")
    scores: Dict[str, Any] = Field(description="Assessment scores")
    confidence_metrics: Dict[str, Any] = Field(description="Response confidence analysis")
    conversation_history: List[Dict[str, Any]] = Field(description="Complete conversation log")


# Global session storage (now backed by database)
active_sessions: Dict[str, ConversationSession] = {}

def validate_session_active(session_id: str) -> None:
    """Validate that session exists in active memory"""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": "session_not_active",
                "message": "Assessment session not found in active memory. This may happen if the server was restarted.",
                "action": "Please start a new assessment session.",
                "session_id": session_id
            }
        )

# Initialize conversation manager and orchestrator
conversation_manager = None
flow_orchestrator = None


def get_conversation_components():
    """Dependency to get conversation manager and orchestrator"""
    global conversation_manager, flow_orchestrator
    
    if conversation_manager is None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPENAI_API_KEY environment variable not set"
            )
        
        conversation_manager = AssessmentConversationManager(
            openai_api_key=openai_api_key,
            model_name="gpt-4o",
            temperature=0.1
        )
        flow_orchestrator = ConversationFlowOrchestrator(conversation_manager)
    
    return conversation_manager, flow_orchestrator


# Create router
router = APIRouter(prefix="/assessment", tags=["Clinical Assessment"])


@router.post("/sessions", response_model=SessionCreateResponse)
async def create_assessment_session(
    request: SessionCreateRequest,
    components: tuple = Depends(get_conversation_components)
) -> SessionCreateResponse:
    """
    Create a new clinical assessment session.
    
    This endpoint initializes a new ADL/IADL assessment conversation session.
    The system will start with IADL questions (less intrusive) followed by ADL questions.
    """
    try:
        conversation_manager, flow_orchestrator = components
        
        # Create new session
        session = conversation_manager.create_new_session(patient_id=request.patient_id)
        
        # Save session to database
        db_session = DatabaseService.create_session(
            patient_id=request.patient_id or f"patient_{session.session_id[:8]}",
            metadata=request.metadata
        )
        
        # Update session ID to match database
        session.session_id = db_session.session_id
        
        # Create database session manager
        session_manager = SessionManager(session.session_id)
        
        # Store session in memory (for LLM conversation state)
        active_sessions[session.session_id] = session
        
        # Start conversation flow
        result = await flow_orchestrator.start_conversation(session)
        
        # Save initial system message to database
        session_manager.add_message(
            role="system",
            content=result["message"],
            message_type="welcome"
        )
        
        # Update database session progress
        session_manager.update_progress(
            phase=result["phase"],
            state=result["status"],
            question_index=0,
            questions_completed=0
        )
        
        # Get assessment structure info
        assessment_info = get_assessment_order()
        
        return SessionCreateResponse(
            session_id=session.session_id,
            message=result["message"],
            status=result["status"],
            phase=result["phase"],
            progress=result["progress"],
            assessment_info=assessment_info
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assessment session: {str(e)}"
        )


@router.post("/sessions/{session_id}/respond", response_model=ConversationResponse)
async def process_user_response(
    session_id: str,
    request: UserInputRequest,
    components: tuple = Depends(get_conversation_components)
) -> ConversationResponse:
    """
    Process user response and advance the conversation.
    
    This endpoint processes the user's response to the current assessment question,
    interprets the clinical score, and returns the next question or completion message.
    """
    try:
        # Validate session is active in memory
        validate_session_active(session_id)
        
        session = active_sessions[session_id]
        conversation_manager, flow_orchestrator = components
        session_manager = SessionManager(session_id)
        
        # Validate session is still active
        if session.current_state == ConversationState.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment session has already been completed"
            )
        
        if session.current_state == ConversationState.ERROR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment session is in error state"
            )
        
        # Capture the question that is being asked BEFORE processing advances the session
        # This prevents the question-response mismatch bug
        asked_question = conversation_manager.get_current_question(session)
        
        # Save user input to database
        session_manager.add_message(
            role="user",
            content=request.user_input,
            message_type="response"
        )
        
        # Process user input
        result = await flow_orchestrator.process_user_input(session, request.user_input)
        
        # Save assistant response to database
        session_manager.add_message(
            role="assistant",
            content=result["message"],
            message_type="question" if result.get("should_continue", True) else "completion"
        )
        
        # Update session progress in database
        progress_parts = result["progress"].split("/")
        questions_completed = int(progress_parts[0]) if len(progress_parts) > 0 else 0
        
        session_manager.update_progress(
            phase=result["phase"],
            state=result["status"],
            question_index=len(session.responses),
            questions_completed=questions_completed
        )
        
        # Save question response if this was a scored response
        # Use the question that was ASKED, not the current question after processing
        if len(session.responses) > 0 and asked_question:
            latest_response = session.responses[-1]
            
            logger.info(f"Saving response for question {asked_question['code']}: '{request.user_input}'")
            session_manager.save_response(
                question_id=asked_question["code"],
                question_text=asked_question["text"],
                question_domain=asked_question["domain"],
                assessment_type=asked_question["assessment_type"],
                user_response=request.user_input,
                interpreted_score=latest_response.interpreted_score,
                confidence=latest_response.confidence,
                reasoning=latest_response.reasoning,
                needs_clarification=latest_response.needs_clarification,
                clarification_question=getattr(latest_response, 'clarification_question', None),
                raw_llm_response=getattr(latest_response, 'raw_llm_response', None)
            )
        
        # Calculate and save scores if assessment is complete
        if result["phase"] == "complete":
            session_manager.calculate_scores()
        
        return ConversationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process user response: {str(e)}"
        )


@router.get("/sessions/{session_id}/status", response_model=ConversationResponse)
async def get_session_status(
    session_id: str,
    components: tuple = Depends(get_conversation_components)
) -> ConversationResponse:
    """
    Get current status of an assessment session.
    
    Returns the current state, progress, and last assistant message.
    """
    try:
        # Validate session is active in memory
        validate_session_active(session_id)
        
        session = active_sessions[session_id]
        
        # Get last assistant message
        last_assistant_msg = ""
        for msg in reversed(session.conversation_history):
            if msg.role == "assistant":
                last_assistant_msg = msg.content
                break
        
        return ConversationResponse(
            session_id=session.session_id,
            message=last_assistant_msg,
            status=session.current_state.value,
            phase=session.current_phase.value,
            progress=f"{len(session.responses)}/{len(get_all_questions())}",
            should_continue=session.current_state not in [ConversationState.COMPLETED, ConversationState.ERROR]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )


@router.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    components: tuple = Depends(get_conversation_components)
) -> SessionSummaryResponse:
    """
    Get comprehensive summary of completed assessment session.
    
    Returns scores, confidence metrics, and complete conversation history.
    Best used after session completion.
    """
    try:
        # Get session summary from database
        summary = DatabaseService.get_session_summary(session_id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment session {session_id} not found"
            )
        
        return SessionSummaryResponse(
            session_info=summary["session_info"],
            scores=summary["scores"],
            confidence_metrics=summary["confidence_metrics"],
            conversation_history=summary["conversation_history"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session summary: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> JSONResponse:
    """
    Delete an assessment session and clean up resources.
    
    Removes session from database and memory.
    """
    try:
        # Delete from database
        deleted = DatabaseService.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment session {session_id} not found"
            )
        
        # Remove from memory if present
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Session {session_id} deleted successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/info")
async def get_assessment_info() -> Dict[str, Any]:
    """
    Get information about the clinical assessment structure.
    
    Returns details about the ADL/IADL assessment including question counts,
    scoring, and proper ordering.
    """
    try:
        assessment_order = get_assessment_order()
        all_questions = get_all_questions()
        
        return {
            "assessment_structure": assessment_order,
            "total_questions": len(all_questions),
            "phases": [
                {
                    "name": "IADL Assessment",
                    "description": "Instrumental Activities of Daily Living - less intrusive questions about community functioning",
                    "question_count": assessment_order["phase_1"]["count"],
                    "order": 1
                },
                {
                    "name": "ADL Assessment", 
                    "description": "Activities of Daily Living - more personal questions about basic self-care",
                    "question_count": assessment_order["phase_2"]["count"],
                    "order": 2
                }
            ],
            "clinical_rationale": assessment_order["rationale"],
            "scoring": {
                "iadl": {
                    "range": "0-8 points",
                    "description": "Higher scores indicate greater independence"
                },
                "adl": {
                    "range": "0-100 points", 
                    "description": "Higher scores indicate greater independence"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment info: {str(e)}"
        )


@router.get("/sessions")
async def list_active_sessions() -> Dict[str, Any]:
    """
    List all currently active assessment sessions.
    
    Returns basic information about active sessions for monitoring purposes.
    """
    try:
        # Get active sessions from database
        session_list = DatabaseService.get_active_sessions()
        
        return {
            "active_sessions": session_list,
            "total_count": len(session_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )
