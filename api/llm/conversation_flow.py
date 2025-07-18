"""
Conversation Flow Orchestrator for Clinical Assessments
======================================================
LangGraph-based conversation flow management for ADL/IADL assessments.
Handles state transitions, conversation history, and error recovery.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import Annotated, TypedDict

from .llm_conversation import (
    AssessmentConversationManager, 
    ConversationSession, 
    AssessmentPhase, 
    ConversationState,
    ConversationMessage,
    AssessmentResponse
)
# Import local neo4j service
from .neo4j_question_service import get_all_questions, get_iadl_questions, get_adl_questions, get_question_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationFlowState(TypedDict):
    """State for the conversation flow graph"""
    session: ConversationSession
    messages: Annotated[List[AnyMessage], add_messages]
    current_user_input: str
    current_assistant_response: str
    needs_clarification: bool
    clarification_context: Optional[Dict[str, Any]]
    error_message: Optional[str]
    should_continue: bool
    next_action: str


class ConversationFlowOrchestrator:
    """Orchestrates conversation flow using LangGraph"""
    
    def __init__(self, conversation_manager: AssessmentConversationManager):
        self.conversation_manager = conversation_manager
        self.checkpointer = MemorySaver()
        self.graph = self._build_conversation_graph()
        self.app = self.graph.compile(checkpointer=self.checkpointer)
    
    def _build_conversation_graph(self) -> StateGraph:
        """Build the conversation flow graph"""
        
        # Define workflow nodes
        workflow = StateGraph(ConversationFlowState)
        
        # Add nodes
        workflow.add_node("welcome", self._welcome_node)
        workflow.add_node("consent", self._consent_node)
        workflow.add_node("ask_question", self._ask_question_node)
        workflow.add_node("process_response", self._process_response_node)
        workflow.add_node("clarify_response", self._clarify_response_node)
        workflow.add_node("advance_question", self._advance_question_node)
        workflow.add_node("transition_phase", self._transition_phase_node)
        workflow.add_node("complete_assessment", self._complete_assessment_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Define edges and conditional routing
        workflow.add_edge(START, "welcome")
        
        workflow.add_conditional_edges(
            "welcome",
            self._route_after_welcome,
            {
                "consent": "consent",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "consent",
            self._route_after_consent,
            {
                "ask_question": "ask_question",
                "wait_for_response": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "ask_question",
            self._route_after_question,
            {
                "wait_for_response": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "process_response",
            self._route_after_processing,
            {
                "clarify": "clarify_response",
                "advance": "advance_question",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "clarify_response",
            self._route_after_clarification,
            {
                "wait_for_response": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "advance_question",
            self._route_after_advance,
            {
                "ask_question": "ask_question",
                "transition": "transition_phase",
                "complete": "complete_assessment",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "transition_phase",
            self._route_after_transition,
            {
                "ask_question": "ask_question",
                "complete": "complete_assessment",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("complete_assessment", END)
        workflow.add_edge("handle_error", END)
        
        return workflow
    
    async def _welcome_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Generate welcome message and initialize session"""
        try:
            session = state["session"]
            
            # Generate welcome message
            welcome_msg = await self.conversation_manager.generate_welcome_message(session)
            
            # Keep session in welcome phase, don't start assessment yet
            session.current_phase = AssessmentPhase.WELCOME
            session.current_state = ConversationState.WAITING_FOR_INPUT
            
            # Add to conversation history
            msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="assistant",
                content=welcome_msg,
                message_type="welcome",
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, msg)
            
            state["current_assistant_response"] = welcome_msg
            state["next_action"] = "consent"
            state["should_continue"] = True
            
            logger.info(f"Session {session.session_id}: Welcome message generated, waiting for consent")
            
        except Exception as e:
            logger.error(f"Error in welcome node: {str(e)}")
            state["error_message"] = f"Welcome error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _consent_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Handle consent for starting assessment"""
        try:
            session = state["session"]
            user_input = state.get("current_user_input", "").lower().strip()
            
            # Check if this is the first time (no user input yet)
            if not user_input:
                # Just return and wait for user response
                state["next_action"] = "wait_for_response"
                state["should_continue"] = False
                logger.info(f"Session {session.session_id}: Waiting for consent response")
                return state
            
            # Process consent response
            if any(word in user_input for word in ["yes", "y", "ok", "okay", "sure", "ready", "begin", "start"]):
                # User gave consent, start assessment
                session.current_phase = AssessmentPhase.IADL_ASSESSMENT
                session.current_state = ConversationState.WAITING_FOR_INPUT
                
                # Add user consent to history
                user_msg = ConversationMessage(
                    timestamp=datetime.now(),
                    speaker="user",
                    content=state["current_user_input"],
                    message_type="consent",
                    phase=session.current_phase.value
                )
                self.conversation_manager.add_message(session, user_msg)
                
                state["next_action"] = "ask_question"
                state["should_continue"] = True
                logger.info(f"Session {session.session_id}: Consent received, starting assessment")
            else:
                # User didn't give clear consent, ask again
                clarification_msg = "I understand you may need a moment to decide. When you're ready to begin the assessment, please let me know by saying 'yes' or 'I'm ready'."
                
                msg = ConversationMessage(
                    timestamp=datetime.now(),
                    speaker="assistant",
                    content=clarification_msg,
                    message_type="clarification",
                    phase=session.current_phase.value
                )
                self.conversation_manager.add_message(session, msg)
                
                state["current_assistant_response"] = clarification_msg
                state["next_action"] = "wait_for_response"
                state["should_continue"] = False
                logger.info(f"Session {session.session_id}: Consent not clear, asking for clarification")
                
        except Exception as e:
            logger.error(f"Error in consent node: {str(e)}")
            state["error_message"] = f"Consent error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _ask_question_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Ask the current assessment question"""
        try:
            session = state["session"]
            
            # Generate question message
            question_msg = await self.conversation_manager.generate_question_message(session)
            
            # Update session state
            session.current_state = ConversationState.WAITING_FOR_INPUT
            
            # Add to conversation history
            current_question = self.conversation_manager.get_current_question(session)
            msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="assistant",
                content=question_msg,
                message_type="question",
                question_code=current_question["code"] if current_question else None,
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, msg)
            
            state["current_assistant_response"] = question_msg
            state["next_action"] = "wait_for_response"
            
            logger.info(f"Session {session.session_id}: Question {session.current_question_index + 1} asked")
            
        except Exception as e:
            logger.error(f"Error in ask question node: {str(e)}")
            state["error_message"] = f"Question error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _process_response_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Process user response and interpret score"""
        try:
            session = state["session"]
            user_input = state["current_user_input"]
            
            # Update session state
            session.current_state = ConversationState.PROCESSING
            
            # Add user message to history
            user_msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="user",
                content=user_input,
                message_type="answer",
                question_code=self.conversation_manager.get_current_question(session)["code"],
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, user_msg)
            
            # Interpret response
            interpretation = await self.conversation_manager.interpret_user_response(session, user_input)
            
            # Log detailed interpretation results
            logger.info(f"Session {session.session_id}: LLM Interpretation Results:")
            logger.info(f"  - User Input: '{user_input}'")
            logger.info(f"  - Interpreted Score: {interpretation.interpreted_score}")
            logger.info(f"  - Confidence: {interpretation.confidence}")
            logger.info(f"  - Reasoning: {interpretation.reasoning}")
            logger.info(f"  - Needs Clarification: {interpretation.needs_clarification}")
            if hasattr(interpretation, 'clarification_question') and interpretation.clarification_question:
                logger.info(f"  - Clarification Question: {interpretation.clarification_question}")
            
            if interpretation.needs_clarification:
                # Store clarification context
                state["needs_clarification"] = True
                state["clarification_context"] = {
                    "interpretation": interpretation,
                    "original_response": user_input
                }
                state["next_action"] = "clarify"
                logger.info(f"Session {session.session_id}: Clarification requested due to low confidence")
            else:
                # Create assessment response
                current_question = self.conversation_manager.get_current_question(session)
                response = AssessmentResponse(
                    question_code=current_question["code"],
                    user_response=user_input,
                    interpreted_score=interpretation.interpreted_score,
                    confidence=interpretation.confidence,
                    reasoning=interpretation.reasoning,
                    needs_clarification=False
                )
                
                # Add to session
                self.conversation_manager.add_response(session, response)
                state["needs_clarification"] = False
                state["next_action"] = "advance"
                logger.info(f"Session {session.session_id}: Response accepted, advancing to next question")
            
            logger.info(f"Session {session.session_id}: Response processed, confidence: {interpretation.confidence}")
            
        except Exception as e:
            logger.error(f"Error in process response node: {str(e)}")
            state["error_message"] = f"Processing error: {str(e)}"
            state["next_action"] = "error"
            session.error_count += 1
        
        return state
    
    async def _clarify_response_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Generate clarification request"""
        try:
            session = state["session"]
            clarification_context = state["clarification_context"]
            
            # Generate clarification message
            clarification_msg = await self.conversation_manager.generate_clarification_message(
                session, clarification_context["interpretation"]
            )
            
            # Update session state
            session.current_state = ConversationState.AWAITING_CLARIFICATION
            
            # Add to conversation history
            msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="assistant",
                content=clarification_msg,
                message_type="clarification",
                question_code=self.conversation_manager.get_current_question(session)["code"],
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, msg)
            
            state["current_assistant_response"] = clarification_msg
            state["next_action"] = "wait_for_response"
            
            logger.info(f"Session {session.session_id}: Clarification requested")
            
        except Exception as e:
            logger.error(f"Error in clarify response node: {str(e)}")
            state["error_message"] = f"Clarification error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _advance_question_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Advance to next question or phase"""
        try:
            session = state["session"]
            
            # Check if we need to transition phases
            if session.current_phase == AssessmentPhase.IADL_ASSESSMENT:
                if session.current_question_index >= len(get_iadl_questions()) - 1:
                    # Transition to ADL phase
                    state["next_action"] = "transition"
                    return state
            elif session.current_phase == AssessmentPhase.ADL_ASSESSMENT:
                if session.current_question_index >= len(get_all_questions()) - 1:
                    # Assessment complete
                    state["next_action"] = "complete"
                    return state
            
            # Advance to next question
            has_more = self.conversation_manager.advance_question(session)
            
            if has_more:
                state["next_action"] = "ask_question"
            else:
                state["next_action"] = "complete"
            
            logger.info(f"Session {session.session_id}: Advanced to question {session.current_question_index + 1}")
            
        except Exception as e:
            logger.error(f"Error in advance question node: {str(e)}")
            state["error_message"] = f"Advance error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _transition_phase_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Handle phase transitions (IADL → ADL → Complete)"""
        try:
            session = state["session"]
            
            # Generate transition message
            transition_msg = await self.conversation_manager.generate_transition_message(session)
            
            # Update phase
            if session.current_phase == AssessmentPhase.IADL_ASSESSMENT:
                session.current_phase = AssessmentPhase.ADL_ASSESSMENT
                session.current_question_index = len(get_iadl_questions())  # Start ADL questions
            elif session.current_phase == AssessmentPhase.ADL_ASSESSMENT:
                session.current_phase = AssessmentPhase.COMPLETE
            
            # Add to conversation history
            msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="assistant",
                content=transition_msg,
                message_type="transition",
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, msg)
            
            state["current_assistant_response"] = transition_msg
            
            # Determine next action
            if session.current_phase == AssessmentPhase.COMPLETE:
                state["next_action"] = "complete"
            else:
                state["next_action"] = "ask_question"
            
            logger.info(f"Session {session.session_id}: Transitioned to {session.current_phase.value}")
            
        except Exception as e:
            logger.error(f"Error in transition phase node: {str(e)}")
            state["error_message"] = f"Transition error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _complete_assessment_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Complete the assessment and generate summary"""
        try:
            session = state["session"]
            
            # Generate completion message
            completion_msg = await self.conversation_manager.generate_completion_message(session)
            
            # Update session state
            session.current_phase = AssessmentPhase.COMPLETE
            session.current_state = ConversationState.COMPLETED
            
            # Add to conversation history
            msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="assistant",
                content=completion_msg,
                message_type="completion",
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, msg)
            
            state["current_assistant_response"] = completion_msg
            state["should_continue"] = False
            state["next_action"] = "end"
            
            logger.info(f"Session {session.session_id}: Assessment completed")
            
        except Exception as e:
            logger.error(f"Error in complete assessment node: {str(e)}")
            state["error_message"] = f"Completion error: {str(e)}"
            state["next_action"] = "error"
        
        return state
    
    async def _handle_error_node(self, state: ConversationFlowState) -> ConversationFlowState:
        """Handle errors and provide recovery options"""
        try:
            session = state["session"]
            error_msg = state.get("error_message", "Unknown error occurred")
            
            # Update session state
            session.current_state = ConversationState.ERROR
            session.error_count += 1
            
            # Generate error response
            error_response = f"I apologize, but I encountered an issue: {error_msg}. Let me try to continue with the assessment."
            
            # Add to conversation history
            msg = ConversationMessage(
                timestamp=datetime.now(),
                speaker="assistant",
                content=error_response,
                message_type="error",
                phase=session.current_phase.value
            )
            self.conversation_manager.add_message(session, msg)
            
            state["current_assistant_response"] = error_response
            state["should_continue"] = session.error_count < 3  # Max 3 errors
            
            logger.error(f"Session {session.session_id}: Error handled - {error_msg}")
            
        except Exception as e:
            logger.critical(f"Critical error in error handler: {str(e)}")
            state["should_continue"] = False
        
        return state
    
    # Routing functions
    def _route_after_welcome(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    def _route_after_consent(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    def _route_after_question(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    def _route_after_processing(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    def _route_after_clarification(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    def _route_after_advance(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    def _route_after_transition(self, state: ConversationFlowState) -> str:
        return state.get("next_action", "error")
    
    # Public interface methods
    async def start_conversation(self, session: ConversationSession) -> Dict[str, Any]:
        """Start a new conversation flow"""
        initial_state = ConversationFlowState(
            session=session,
            messages=[],
            current_user_input="",
            current_assistant_response="",
            needs_clarification=False,
            clarification_context=None,
            error_message=None,
            should_continue=True,
            next_action="welcome"
        )
        
        thread_config = {"configurable": {"thread_id": session.session_id}}
        
        try:
            # Run the welcome flow
            result = await self.app.ainvoke(initial_state, config=thread_config)
            
            return {
                "session_id": session.session_id,
                "message": result["current_assistant_response"],
                "status": "active",
                "phase": session.current_phase.value,
                "progress": f"0/{len(get_all_questions())}",
                "should_continue": result.get("should_continue", True)
            }
            
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return {
                "session_id": session.session_id,
                "message": "I apologize, but I'm having trouble starting the assessment. Please try again.",
                "status": "error",
                "error": str(e)
            }
    
    async def process_user_input(self, session: ConversationSession, user_input: str) -> Dict[str, Any]:
        """Process user input and advance conversation"""
        logger.info(f"Session {session.session_id}: Processing user input: '{user_input}'")
        logger.info(f"Session {session.session_id}: Current state: {session.current_state}, Phase: {session.current_phase}")
        
        thread_config = {"configurable": {"thread_id": session.session_id}}
        
        try:
            # Get current state from checkpointer
            current_state = await self.app.aget_state(config=thread_config)
            
            # Update with user input
            updated_state = current_state.values.copy()
            updated_state["current_user_input"] = user_input
            updated_state["session"] = session
            
            # Process the input
            if session.current_state == ConversationState.AWAITING_CLARIFICATION:
                # Handle clarification response - process it as a normal response
                session.current_state = ConversationState.PROCESSING  # Reset state
                result = await self._process_response_node(updated_state)
                
                # Continue with next step based on result
                if result["next_action"] == "clarify":
                    result = await self._clarify_response_node(result)
                elif result["next_action"] == "advance":
                    result = await self._advance_question_node(result)
                    if result["next_action"] == "ask_question":
                        result = await self._ask_question_node(result)
                    elif result["next_action"] == "transition":
                        result = await self._transition_phase_node(result)
                        if result["next_action"] == "ask_question":
                            result = await self._ask_question_node(result)
                    elif result["next_action"] == "complete":
                        result = await self._complete_assessment_node(result)
            elif session.current_phase == AssessmentPhase.WELCOME:
                # Handle consent response
                result = await self._consent_node(updated_state)
                if result["next_action"] == "ask_question":
                    result = await self._ask_question_node(result)
            else:
                # Process normal response
                result = await self._process_response_node(updated_state)
                
                # Continue with next step based on result
                if result["next_action"] == "clarify":
                    result = await self._clarify_response_node(result)
                elif result["next_action"] == "advance":
                    result = await self._advance_question_node(result)
                    if result["next_action"] == "ask_question":
                        result = await self._ask_question_node(result)
                    elif result["next_action"] == "transition":
                        result = await self._transition_phase_node(result)
                        if result["next_action"] == "ask_question":
                            result = await self._ask_question_node(result)
                    elif result["next_action"] == "complete":
                        result = await self._complete_assessment_node(result)
            
            return {
                "session_id": session.session_id,
                "message": result["current_assistant_response"],
                "status": session.current_state.value,
                "phase": session.current_phase.value,
                "progress": f"{len(session.responses)}/{len(get_all_questions())}",
                "should_continue": result.get("should_continue", True),
                "needs_clarification": result.get("needs_clarification", False)
            }
            
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            session.error_count += 1
            session.current_state = ConversationState.ERROR
            return {
                "session_id": session.session_id,
                "message": "I apologize, but I'm having trouble processing your response. Could you please try again?",
                "status": session.current_state.value,
                "phase": session.current_phase.value,
                "progress": f"{len(session.responses)}/{len(get_all_questions())}",
                "should_continue": False,
                "error": str(e)
            }
    
    async def get_conversation_summary(self, session: ConversationSession) -> Dict[str, Any]:
        """Get comprehensive conversation summary"""
        return self.conversation_manager.get_session_summary(session)
