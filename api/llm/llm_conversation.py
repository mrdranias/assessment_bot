"""
LLM Conversation Management for Clinical Assessments
===================================================
Handles conversational flow for ADL/IADL assessments using LangChain/LangGraph.
Interprets free-form answers and maps them to clinical scores.
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

# Import local neo4j service
from .neo4j_question_service import get_all_questions, get_iadl_questions, get_adl_questions, get_question_service
from .clinical_prompts import ClinicalPromptTemplate


class AssessmentPhase(Enum):
    """Current phase of the assessment"""
    WELCOME = "welcome"
    IADL_ASSESSMENT = "iadl"
    ADL_ASSESSMENT = "adl"
    REVIEW = "review"
    COMPLETE = "complete"


class ConversationState(Enum):
    """Current state of the conversation"""
    INITIALIZING = "initializing"
    WAITING_FOR_INPUT = "waiting"
    PROCESSING = "processing"
    AWAITING_CLARIFICATION = "clarification"
    COMPLETED = "completed"
    ERROR = "error"


class ScoreInterpretation(BaseModel):
    """LLM interpretation of user response to clinical score"""
    interpreted_score: int = Field(description="The clinical score (0-10 for ADL, 0-1 for IADL)")
    confidence: float = Field(description="Confidence level (0.0-1.0)")
    reasoning: str = Field(description="Explanation of scoring rationale")
    needs_clarification: bool = Field(description="Whether response needs clarification")
    clarification_question: Optional[str] = Field(description="Follow-up question if clarification needed")


@dataclass
class ConversationMessage:
    """A single message in the conversation"""
    timestamp: datetime
    speaker: str  # "user", "assistant", "system"
    content: str
    message_type: str  # "question", "answer", "clarification", "transition", "error"
    question_code: Optional[str] = None
    phase: Optional[str] = None


@dataclass
class AssessmentResponse:
    """User response to an assessment question"""
    question_code: str
    user_response: str
    interpreted_score: int
    confidence: float
    reasoning: str = ""
    needs_clarification: bool = False
    clarification_provided: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConversationSession:
    """Complete conversation session state"""
    session_id: str
    patient_id: Optional[str]
    current_phase: AssessmentPhase
    current_state: ConversationState
    current_question_index: int
    responses: List[AssessmentResponse]
    conversation_history: List[ConversationMessage]
    started_at: datetime
    last_activity: datetime
    error_count: int = 0
    
    def __post_init__(self):
        if not hasattr(self, 'session_id') or not self.session_id:
            self.session_id = str(uuid.uuid4())


class AssessmentConversationManager:
    """Manages LLM-powered clinical assessment conversations"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o", temperature: float = 0.1):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=2000  # Increased for complete JSON responses
        )
        self.parser = PydanticOutputParser(pydantic_object=ScoreInterpretation)
        
        # Load clinical questions
        self.all_questions = get_all_questions()
        self.iadl_questions = get_iadl_questions()
        self.adl_questions = get_adl_questions()
    
    def create_new_session(self, patient_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        session = ConversationSession(
            session_id=str(uuid.uuid4()),
            patient_id=patient_id,
            current_phase=AssessmentPhase.WELCOME,
            current_state=ConversationState.INITIALIZING,
            current_question_index=0,
            responses=[],
            conversation_history=[],
            started_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Add system initialization message
        system_msg = ConversationMessage(
            timestamp=datetime.now(),
            speaker="system",
            content="Assessment session initialized",
            message_type="system",
            phase=session.current_phase.value
        )
        session.conversation_history.append(system_msg)
        
        return session
    
    async def generate_welcome_message(self, session: ConversationSession) -> str:
        """Generate personalized welcome message"""
        try:
            system_prompt = ClinicalPromptTemplate.get_system_prompt("welcome")
            welcome_prompt = ClinicalPromptTemplate.get_welcome_prompt()
            
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(welcome_prompt)
            ])
            
            context = {
                "session_id": session.session_id,
                "patient_id": session.patient_id or "valued patient",
                "total_questions": len(self.all_questions)
            }
            
            messages = prompt_template.format_messages(**context)
            response = await self.llm.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            return ClinicalPromptTemplate.get_fallback_response("welcome_error", str(e))
    
    def get_current_question(self, session: ConversationSession) -> Optional[Dict[str, Any]]:
        """Get the current question based on session state"""
        if session.current_phase == AssessmentPhase.IADL_ASSESSMENT:
            questions = self.iadl_questions
            index = session.current_question_index
        elif session.current_phase == AssessmentPhase.ADL_ASSESSMENT:
            # Adjust index for ADL phase (after IADL questions)
            questions = self.adl_questions
            index = session.current_question_index - len(self.iadl_questions)
        else:
            return None
        
        if 0 <= index < len(questions):
            return questions[index]
        return None
    
    async def generate_question_message(self, session: ConversationSession) -> str:
        """Generate the next question message"""
        try:
            current_question = self.get_current_question(session)
            if not current_question:
                return "Assessment completed. Thank you for your responses."
            
            # Determine question context
            context = {
                "current_phase": session.current_phase.value,
                "question_number": session.current_question_index + 1,
                "total_questions": len(self.all_questions),
                "is_sensitive": current_question.get("sensitive", False)
            }
            
            # Get appropriate system prompt
            system_prompt = ClinicalPromptTemplate.get_system_prompt(
                "iadl_assessment" if session.current_phase == AssessmentPhase.IADL_ASSESSMENT 
                else "adl_assessment"
            )
            
            question_prompt = ClinicalPromptTemplate.get_question_prompt(current_question, context)
            
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(question_prompt)
            ])
            
            messages = prompt_template.format_messages()
            response = await self.llm.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            return ClinicalPromptTemplate.get_fallback_response("question_error", str(e))
    
    async def interpret_user_response(self, session: ConversationSession, user_response: str) -> ScoreInterpretation:
        """Interpret user response into clinical score using the working shared approach"""
        try:
            current_question = self.get_current_question(session)
            if not current_question:
                raise ValueError("No current question found")
            
            # Format the answer options for the LLM
            answer_options = "\n".join([
                f"Score {ans['clinical_score']}: {ans['text']}"
                for ans in current_question['answers']
            ])
            
            # Use the working system template from shared version
            system_template = """You are a clinical assessment expert. Your task is to interpret a patient's free-form answer to a standardized assessment question and map it to the appropriate clinical score.

Question: {question_text}
Description: {question_description}

Available Answer Options and Scores:
{answer_options}

Guidelines:
1. Match the patient's response to the most appropriate clinical score
2. Consider the functional level described, not just specific words
3. If the response is ambiguous, indicate that clarification is needed
4. Provide your confidence level (0.0 to 1.0)
5. Explain your reasoning briefly

Patient's Response: {user_answer}

IMPORTANT: You must respond with valid JSON using these EXACT field names:
{{
  "interpreted_score": <integer>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<brief explanation>",
  "needs_clarification": <true/false>,
  "clarification_question": "<question if clarification needed, null otherwise>"
}}

Do NOT use field names like "score" - use "interpreted_score". Do NOT wrap in ```json blocks."""

            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template("Please interpret this response and provide the clinical score.")
            ])
            
            # Use partials like the working shared version
            formatted_prompt = prompt.partial(
                question_text=current_question['text'],
                question_description=current_question['description'],
                answer_options=answer_options,
                user_answer=user_response
            )
            
            # Format with parser instructions
            messages = formatted_prompt.format_messages()
            
            print(f"\n🤖 DEBUG interpret_user_response:")
            print(f"   Question: {current_question.get('code', 'Unknown')}")
            print(f"   User answer: '{user_response}'")
            print(f"   Prompt messages: {len(messages)}")
            
            # Get LLM response
            print(f"   ⏳ Calling LLM with max_tokens={self.llm.max_tokens}...")
            response = await self.llm.ainvoke(messages)
            
            print(f"   📝 Raw LLM response:")
            print(f"      Length: {len(response.content)} chars")
            print(f"      Content: '{response.content}'")
            
            # Parse structured response
            print(f"   🔍 Attempting to parse JSON...")
            interpretation = self.parser.parse(response.content)
            print(f"   ✅ Parsing successful!")
            
            return interpretation
            
        except Exception as e:
            print(f"   ❌ Parsing failed: {str(e)}")
            print(f"   🔄 Using fallback interpretation")
            # Fallback interpretation with low confidence
            return ScoreInterpretation(
                interpreted_score=0,
                confidence=0.1,
                reasoning=f"Error interpreting response: {str(e)}",
                needs_clarification=True,
                clarification_question="I'm having trouble understanding your response. Could you please clarify?"
            )
    
    async def generate_clarification_message(self, session: ConversationSession, 
                                           interpretation: ScoreInterpretation) -> str:
        """Generate clarification question for ambiguous responses"""
        try:
            current_question = self.get_current_question(session)
            if not current_question:
                return "Could you please clarify your previous response?"
            
            context = {
                "question": current_question,
                "interpretation": interpretation,
                "suggested_clarification": interpretation.clarification_question
            }
            
            system_prompt = ClinicalPromptTemplate.get_system_prompt("base")
            clarification_prompt = ClinicalPromptTemplate.get_clarification_prompt(context)
            
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(clarification_prompt)
            ])
            
            messages = prompt_template.format_messages()
            response = await self.llm.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            return interpretation.clarification_question or "Could you please provide more details about your response?"
    
    async def generate_transition_message(self, session: ConversationSession) -> str:
        """Generate transition message between assessment phases"""
        try:
            context = {
                "current_phase": session.current_phase.value,
                "completed_responses": len(session.responses),
                "next_phase": self._get_next_phase(session.current_phase).value if self._get_next_phase(session.current_phase) else "completion"
            }
            
            system_prompt = ClinicalPromptTemplate.get_system_prompt("base")
            transition_prompt = ClinicalPromptTemplate.get_transition_prompt(context)
            
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(transition_prompt)
            ])
            
            messages = prompt_template.format_messages()
            response = await self.llm.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            return ClinicalPromptTemplate.get_fallback_response("transition_error", str(e))
    
    async def generate_completion_message(self, session: ConversationSession) -> str:
        """Generate final completion message with summary"""
        try:
            # Calculate scores
            iadl_responses = [r for r in session.responses if r.question_code.startswith("LAWTON_")]
            adl_responses = [r for r in session.responses if r.question_code.startswith("BARTHEL_")]
            
            iadl_score = sum(r.interpreted_score for r in iadl_responses)
            adl_score = sum(r.interpreted_score for r in adl_responses)
            
            context = {
                "total_responses": len(session.responses),
                "iadl_score": iadl_score,
                "iadl_max": len(self.iadl_questions),
                "adl_score": adl_score,
                "adl_max": 100,
                "session_duration": (datetime.now() - session.started_at).total_seconds() / 60
            }
            
            system_prompt = ClinicalPromptTemplate.get_system_prompt("base")
            completion_prompt = ClinicalPromptTemplate.get_completion_prompt(context)
            
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(completion_prompt)
            ])
            
            messages = prompt_template.format_messages()
            response = await self.llm.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            return ClinicalPromptTemplate.get_fallback_response("completion_error", str(e))
    
    def add_response(self, session: ConversationSession, response: AssessmentResponse):
        """Add a user response to the session"""
        session.responses.append(response)
        session.last_activity = datetime.now()
    
    def add_message(self, session: ConversationSession, message: ConversationMessage):
        """Add a message to conversation history"""
        session.conversation_history.append(message)
        session.last_activity = datetime.now()
    
    def advance_question(self, session: ConversationSession) -> bool:
        """Advance to next question, returns True if more questions available"""
        session.current_question_index += 1
        
        # Check if we need to transition phases
        if session.current_phase == AssessmentPhase.IADL_ASSESSMENT:
            if session.current_question_index >= len(self.iadl_questions):
                session.current_phase = AssessmentPhase.ADL_ASSESSMENT
        elif session.current_phase == AssessmentPhase.ADL_ASSESSMENT:
            if session.current_question_index >= len(self.all_questions):
                session.current_phase = AssessmentPhase.COMPLETE
                return False
        
        return session.current_phase != AssessmentPhase.COMPLETE
    
    def _get_next_phase(self, current_phase: AssessmentPhase) -> Optional[AssessmentPhase]:
        """Get the next assessment phase"""
        phase_order = [
            AssessmentPhase.WELCOME,
            AssessmentPhase.IADL_ASSESSMENT,
            AssessmentPhase.ADL_ASSESSMENT,
            AssessmentPhase.REVIEW,
            AssessmentPhase.COMPLETE
        ]
        
        try:
            current_index = phase_order.index(current_phase)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    def get_session_summary(self, session: ConversationSession) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        # Calculate scores
        iadl_responses = [r for r in session.responses if r.question_code.startswith("LAWTON_")]
        adl_responses = [r for r in session.responses if r.question_code.startswith("BARTHEL_")]
        
        iadl_score = sum(r.interpreted_score for r in iadl_responses)
        adl_score = sum(r.interpreted_score for r in adl_responses)
        
        # Calculate confidence metrics
        confidences = [r.confidence for r in session.responses]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "session_id": session.session_id,
            "patient_id": session.patient_id,
            "status": session.current_state.value,
            "phase": session.current_phase.value,
            "progress": f"{len(session.responses)}/{len(self.all_questions)}",
            "scores": {
                "iadl_score": iadl_score,
                "iadl_max": len(self.iadl_questions),
                "adl_score": adl_score,
                "adl_max": 100,
                "total_responses": len(session.responses)
            },
            "confidence_metrics": {
                "average_confidence": round(avg_confidence, 2),
                "low_confidence_responses": len([r for r in session.responses if r.confidence < 0.7]),
                "clarifications_needed": len([r for r in session.responses if r.needs_clarification])
            },
            "session_metadata": {
                "started_at": session.started_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "duration_minutes": round((session.last_activity - session.started_at).total_seconds() / 60, 1),
                "conversation_turns": len(session.conversation_history),
                "error_count": session.error_count
            }
        }
