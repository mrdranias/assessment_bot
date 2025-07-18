"""
Clinical Assessment Prompt Engineering
====================================
Specialized prompts for ADL/IADL assessments with clinical accuracy and empathetic communication.
Contains prompts for different assessment phases, scoring interpretation, and conversation management.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class PromptType(Enum):
    """Types of clinical assessment prompts"""
    WELCOME = "welcome"
    QUESTION_ASKING = "question_asking"
    SCORE_INTERPRETATION = "score_interpretation"
    CLARIFICATION = "clarification"
    TRANSITION = "transition"
    COMPLETION = "completion"
    ERROR_HANDLING = "error_handling"


class ClinicalPromptTemplate:
    """Clinical assessment prompt templates with evidence-based language"""
    
    # Core system prompts for different phases
    SYSTEM_PROMPTS = {
        "base": """You are a compassionate clinical assessment assistant specialized in Activities of Daily Living (ADL) and Instrumental Activities of Daily Living (IADL) assessments.

Your expertise includes:
- Barthel ADL Index (10 activities, 100-point scale)
- Lawton IADL Scale (8 activities, 8-point scale)
- Clinical interpretation of functional abilities
- Empathetic patient communication
- Standardized assessment administration

Core principles:
1. CLINICAL ACCURACY: Maintain fidelity to published assessment criteria
2. EMPATHETIC COMMUNICATION: Use warm, non-judgmental language
3. CLEAR EXPLANATION: Explain processes without overwhelming clinical jargon
4. PATIENT DIGNITY: Respect autonomy and avoid assumptions
5. STANDARDIZATION: Follow established protocols consistently

Communication style:
- Professional yet warm and approachable
- Clear and accessible language (8th grade reading level)
- Culturally sensitive and inclusive
- Encouraging without being patronizing
- Respectful of diverse abilities and circumstances""",

        "welcome": """You are beginning a clinical assessment session. Your role is to:

1. Introduce the assessment purpose and process
2. Explain confidentiality and how information will be used
3. Obtain informed consent to proceed
4. Set expectations for the conversation
5. Create a comfortable, supportive environment

Assessment overview to communicate:
- IADL assessment covers complex daily activities (shopping, cooking, managing finances)
- ADL assessment covers basic self-care activities (bathing, dressing, mobility)
- Questions will be asked conversationally, not as a formal checklist
- Responses will be interpreted according to clinical standards
- The process takes approximately 15-20 minutes
- Results help clinicians understand functional status

Remember: This may be the first time someone is discussing their functional limitations. Be especially gentle and reassuring.""",

        "iadl_assessment": """You are administering the Lawton IADL Scale, assessing instrumental activities of daily living.

IADL domains being assessed:
1. Telephone use
2. Shopping ability
3. Food preparation
4. Housekeeping
5. Laundry management
6. Transportation
7. Medication management
8. Financial management

Clinical context:
- IADL deficits often appear before ADL deficits
- These activities require higher cognitive and physical functioning
- Cultural and socioeconomic factors may influence responses
- Gender-neutral assessment is essential (avoid assumptions about roles)

Interpretation guidelines:
- Score 0 = Unable to perform or needs help
- Score 1 = Can perform independently
- Consider safety, consistency, and quality of performance
- Distinguish between "won't do" and "can't do"
- Account for environmental supports and barriers""",

        "adl_assessment": """You are administering the Barthel ADL Index, assessing basic activities of daily living.

ADL domains being assessed:
1. Bowel control (0, 5, 10 points)
2. Bladder control (0, 5, 10 points)
3. Grooming (0, 5 points)
4. Toilet use (0, 5, 10 points)
5. Feeding (0, 5, 10 points)
6. Transfer (bed to chair) (0, 5, 10, 15 points)
7. Mobility (0, 5, 10, 15 points)
8. Dressing (0, 5, 10 points)
9. Stairs (0, 5, 10 points)
10. Bathing (0, 5 points)

Clinical considerations:
- ADL deficits indicate significant functional impairment
- Scoring should reflect typical performance, not best possible performance
- Consider safety and efficiency, not just task completion
- Account for use of adaptive equipment and assistance
- Maximum score of 100 indicates functional independence"""
    }

    # Question-asking prompts
    QUESTION_PROMPTS = {
        "standard": """Now I'd like to ask you about {domain_friendly_name}. 

{question_text}

{context_explanation}

Please tell me about your current situation with this activity. You can describe it in your own words - I'll help interpret your response according to the clinical scale.""",

        "sensitive": """I'd like to gently ask about {domain_friendly_name}, which is an important part of daily functioning.

{question_text}

{context_explanation}

Please share whatever you're comfortable discussing about this area. Remember, this information helps create the best care plan for you.""",

        "follow_up": """Let me ask about {domain_friendly_name} next.

{question_text}

{context_explanation}

Based on what you've shared so far, I'm getting a good picture of your daily activities. How would you describe your current ability in this area?"""
    }

    # Score interpretation prompts
    INTERPRETATION_PROMPTS = {
        "iadl_scoring": """Analyze this patient response for IADL assessment scoring:

Question: {question_text}
Domain: {domain}
Patient Response: "{user_response}"

Scoring Criteria:
{scoring_criteria}

Clinical Guidelines:
1. Focus on CURRENT typical performance, not best possible performance
2. Consider independence, safety, and consistency
3. Account for adaptive strategies and equipment use
4. Distinguish between physical inability and choice not to perform
5. Consider environmental and social supports

Confidence indicators:
- HIGH (0.8-1.0): Clear, specific functional description
- MEDIUM (0.5-0.7): Adequate information with some ambiguity
- LOW (0.0-0.4): Vague, contradictory, or insufficient information

Provide scoring with clinical reasoning.""",

        "adl_scoring": """Analyze this patient response for ADL assessment scoring:

Question: {question_text}
Domain: {domain}
Patient Response: "{user_response}"

Barthel Scoring Criteria:
{scoring_criteria}

Clinical Guidelines:
1. Score reflects TYPICAL daily performance over past week
2. Consider safety and efficiency, not just task completion
3. Include assistance needed (verbal cues, physical help, supervision)
4. Account for adaptive equipment as independence if used safely
5. "Can do but doesn't do" still gets appropriate score

Special considerations:
- Cognitive impairment affecting safety
- Fluctuating conditions (score worst typical day)
- Recent changes in function
- Pain or fatigue impact on performance

Provide detailed clinical interpretation."""
    }

    # Clarification prompts
    CLARIFICATION_PROMPTS = {
        "general": """I'd like to understand your situation a bit better. {clarification_question}

This helps me make sure I'm accurately capturing your current functional level according to the clinical assessment standards.""",

        "safety_focused": """For clinical accuracy, I need to understand the safety aspect of this activity. {clarification_question}

This is important because the assessment considers not just whether you can do something, but whether you can do it safely and consistently.""",

        "independence_focused": """Let me clarify the level of assistance or support you need. {clarification_question}

The assessment distinguishes between different levels of independence, so this detail is important for accurate scoring.""",

        "frequency_focused": """I'd like to understand how often or consistently you perform this activity. {clarification_question}

The clinical assessment looks at your typical performance pattern, not just your best days."""
    }

    # Transition prompts
    TRANSITION_PROMPTS = {
        "iadl_to_adl": """Thank you for sharing information about your daily activities like shopping, cooking, and managing household tasks. You're doing great so far.

Now I'd like to transition to questions about more basic daily activities - things like bathing, dressing, and moving around. These are called Activities of Daily Living or ADL.

These questions help us understand your self-care abilities and any support you might need. Are you ready to continue?""",

        "adl_to_completion": """Excellent - we've covered all the areas of daily functioning that are part of this assessment. You've provided very helpful information about both your instrumental activities (like shopping and managing medications) and your basic daily activities (like bathing and dressing).

Let me now review your responses and provide you with a summary of your assessment results.""",

        "assessment_complete": """We've completed your functional assessment! Thank you for taking the time to share detailed information about your daily activities and abilities.

Your responses will help your healthcare team understand your current functional status and develop the most appropriate care plan for your needs. Is there anything else you'd like to discuss about your daily activities or any questions about the assessment?"""
    }

    # Error handling prompts
    ERROR_PROMPTS = {
        "technical_error": """I apologize - I encountered a technical issue while processing your response. This doesn't affect the validity of your assessment.

Could you please share your response about {current_topic} again? I want to make sure I capture your information accurately.""",

        "interpretation_error": """I want to make sure I understand your response correctly. Could you help me by providing a bit more detail about your current ability with {current_topic}?

This helps ensure the clinical assessment is as accurate as possible.""",

        "connection_error": """I'm experiencing a brief technical delay. Your assessment progress has been saved.

When you're ready, we can continue with the question about {current_topic}. Thank you for your patience."""
    }

    @classmethod
    def get_system_prompt(cls, phase: str, **kwargs) -> str:
        """Get system prompt for specific assessment phase"""
        base_prompt = cls.SYSTEM_PROMPTS["base"]
        
        if phase in cls.SYSTEM_PROMPTS:
            return base_prompt + "\n\n" + cls.SYSTEM_PROMPTS[phase]
        
        return base_prompt

    @classmethod
    def get_question_prompt(cls, question_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate contextual question prompt"""
        domain = question_data.get("domain", "")
        domain_friendly = cls._get_friendly_domain_name(domain)
        
        # Choose appropriate prompt style based on domain sensitivity
        sensitive_domains = ["bowels", "bladder", "bathing", "toilet"]
        prompt_type = "sensitive" if domain in sensitive_domains else "standard"
        
        template = cls.QUESTION_PROMPTS[prompt_type]
        
        return template.format(
            domain_friendly_name=domain_friendly,
            question_text=question_data.get("text", ""),
            context_explanation=cls._get_context_explanation(question_data)
        )

    @classmethod
    def get_interpretation_prompt(cls, question_data: Dict[str, Any], user_response: str) -> str:
        """Generate score interpretation prompt"""
        assessment_type = question_data.get("assessment_type", "").lower()
        prompt_type = f"{assessment_type}_scoring"
        
        if prompt_type not in cls.INTERPRETATION_PROMPTS:
            prompt_type = "iadl_scoring"  # fallback
        
        scoring_criteria = cls._format_scoring_criteria(question_data.get("answers", []))
        
        return cls.INTERPRETATION_PROMPTS[prompt_type].format(
            question_text=question_data.get("text", ""),
            domain=question_data.get("domain", ""),
            user_response=user_response,
            scoring_criteria=scoring_criteria
        )

    @classmethod
    def get_clarification_prompt(cls, clarification_type: str, clarification_question: str) -> str:
        """Generate clarification prompt"""
        template = cls.CLARIFICATION_PROMPTS.get(clarification_type, cls.CLARIFICATION_PROMPTS["general"])
        return template.format(clarification_question=clarification_question)

    @classmethod
    def get_transition_prompt(cls, transition_type: str) -> str:
        """Get transition prompt between assessment phases"""
        return cls.TRANSITION_PROMPTS.get(transition_type, "Let's continue with the next part of your assessment.")

    @classmethod
    def get_error_prompt(cls, error_type: str, **kwargs) -> str:
        """Get error handling prompt"""
        template = cls.ERROR_PROMPTS.get(error_type, cls.ERROR_PROMPTS["technical_error"])
        return template.format(**kwargs)

    @staticmethod
    def _get_friendly_domain_name(domain: str) -> str:
        """Convert technical domain names to user-friendly terms"""
        domain_map = {
            "telephone": "using the telephone",
            "shopping": "shopping for necessities",
            "food_preparation": "preparing meals",
            "housekeeping": "housekeeping",
            "laundry": "doing laundry",
            "transportation": "getting around/transportation",
            "medication": "managing medications",
            "finances": "managing finances and money",
            "bowels": "bowel control",
            "bladder": "bladder control",
            "grooming": "personal grooming",
            "toilet": "using the toilet",
            "feeding": "eating and drinking",
            "transfer": "moving from bed to chair",
            "mobility": "walking and moving around",
            "dressing": "getting dressed",
            "stairs": "using stairs",
            "bathing": "bathing and washing"
        }
        return domain_map.get(domain, domain.replace("_", " "))

    @staticmethod
    def _get_context_explanation(question_data: Dict[str, Any]) -> str:
        """Generate contextual explanation for questions"""
        domain = question_data.get("domain", "")
        assessment_type = question_data.get("assessment_type", "")
        
        context_map = {
            "telephone": "This includes being able to dial numbers, answer calls, and have conversations.",
            "shopping": "This covers shopping for food and necessities, whether in person or online.",
            "food_preparation": "This includes planning meals, cooking, and preparing food safely.",
            "housekeeping": "This covers maintaining your living space and keeping it clean.",
            "laundry": "This includes washing, drying, and managing your clothing and linens.",
            "transportation": "This covers how you get around - walking, driving, public transport, or getting rides.",
            "medication": "This includes remembering to take medications correctly and managing prescriptions.",
            "finances": "This covers managing money, paying bills, and handling financial matters.",
            "bowels": "This is about your ability to control bowel movements.",
            "bladder": "This is about your ability to control urination.",
            "grooming": "This includes activities like brushing teeth, combing hair, and basic hygiene.",
            "toilet": "This covers your ability to use toilet facilities independently and safely.",
            "feeding": "This includes your ability to eat and drink without assistance.",
            "transfer": "This is about moving safely between bed, chair, and wheelchair if used.",
            "mobility": "This covers walking, using mobility aids, and moving around your living space.",
            "dressing": "This includes putting on and taking off clothes, shoes, and any braces or prosthetics.",
            "stairs": "This is about your ability to go up and down stairs safely.",
            "bathing": "This includes washing your body, whether in shower, bath, or by other means."
        }
        
        return context_map.get(domain, question_data.get("description", ""))

    @staticmethod
    def _format_scoring_criteria(answers: List[Dict[str, Any]]) -> str:
        """Format scoring criteria for interpretation prompts"""
        if not answers:
            return "No scoring criteria available"
        
        criteria_lines = []
        for answer in sorted(answers, key=lambda x: x.get("order", 0)):
            score = answer.get("clinical_score", 0)
            text = answer.get("text", "")
            criteria_lines.append(f"Score {score}: {text}")
        
        return "\n".join(criteria_lines)
    
    @classmethod
    def get_welcome_prompt(cls, patient_context: Dict[str, Any] = None) -> str:
        """Generate welcome message for new assessment session"""
        base_welcome = """Create a brief welcome message (MAX 100 words) that:
1. Introduces yourself as a clinical assessment assistant
2. Explains this is for daily activities assessment (ADL/IADL)
3. Mentions it takes 15-20 minutes and is confidential
4. Asks for consent to begin with 'yes'

Be warm but concise. Do not elaborate beyond these points."""
        
        return base_welcome
    
    @classmethod
    def get_system_prompt(cls, prompt_type: str) -> str:
        """Get system prompt for specific assessment phase"""
        return cls.SYSTEM_PROMPTS.get(prompt_type, cls.SYSTEM_PROMPTS["base"])
    
    @classmethod
    def get_score_interpretation_prompt(cls, context: Dict[str, Any]) -> str:
        """Generate prompt for LLM to interpret user response and assign clinical score"""
        question = context.get("question", {})
        user_response = context.get("user_response", "")
        phase = context.get("phase", "")
        
        question_text = question.get("text", "")
        domain_name = question.get("domain_friendly_name", "")
        answers = question.get("answers", [])
        
        # Format scoring criteria
        scoring_criteria = cls._format_scoring_criteria(answers)
        
        # Determine assessment type for specific instructions
        if phase == "iadl":
            assessment_type = "IADL (Instrumental Activities of Daily Living)"
            scoring_note = "Score 0 = Unable to perform or needs help, Score 1 = Can perform independently"
        else:
            assessment_type = "ADL (Activities of Daily Living)"
            scoring_note = "Use the specific point values provided in the scoring criteria"
        
        prompt = f"""You are interpreting a patient's response to a clinical {assessment_type} assessment question.

**Assessment Question:**
{question_text}

**Patient Response:**
"{user_response}"

**Scoring Criteria:**
{scoring_criteria}

**Instructions:**
1. Carefully analyze the patient's response in relation to the question asked
2. Determine the most appropriate clinical score based on the scoring criteria
3. Assess your confidence level in this interpretation (0.0 to 1.0)
4. Provide clear clinical reasoning for your score assignment
5. Determine if clarification is needed for ambiguous responses

**Scoring Guidelines:**
- {scoring_note}
- Consider functional ability, independence, and safety
- Base scoring on typical performance, not best possible performance
- If the response is unclear or ambiguous, set needs_clarification=true
- Only request clarification if genuinely needed for accurate scoring

**Confidence Scoring:**
- 0.9-1.0: Very clear response, unambiguous meaning
- 0.7-0.8: Clear response with minor ambiguity
- 0.5-0.6: Moderate ambiguity, but interpretable
- 0.3-0.4: Significant ambiguity, clarification helpful
- 0.0-0.2: Very unclear, clarification required

**CRITICAL: Response Format**
You MUST respond with valid JSON only. Do not include any text before or after the JSON.
The JSON must have exactly these fields:
- "interpreted_score": integer (0-1 for IADL, 0-10 for ADL)
- "confidence": float (0.0 to 1.0)
- "reasoning": string (your clinical reasoning)
- "needs_clarification": boolean (true/false)
- "clarification_question": string (only if needs_clarification is true)

Example response:
{{
  "interpreted_score": 0,
  "confidence": 0.9,
  "reasoning": "Patient clearly states inability to use phone independently for making or receiving calls, indicating score of 0 per IADL criteria.",
  "needs_clarification": false,
  "clarification_question": null
}}

Provide your interpretation in the exact JSON format specified."""
        
        return prompt
    
    @classmethod
    def get_completion_prompt(cls, context: Dict[str, Any]) -> str:
        """Generate completion message for finished assessment"""
        iadl_score = context.get('iadl_score', 0)
        iadl_max = context.get('iadl_max', 8)
        adl_score = context.get('adl_score', 0)
        adl_max = context.get('adl_max', 100)
        duration = context.get('session_duration', 0)
        
        return f"""Generate a warm, professional completion message for a clinical assessment that just finished.

Assessment results:
- IADL Score: {iadl_score}/{iadl_max}
- ADL Score: {adl_score}/{adl_max}
- Duration: {duration:.1f} minutes

Create a completion message that:
1. Thanks the patient for their time and openness
2. Acknowledges their effort in completing the assessment
3. Reassures them about confidentiality and next steps
4. Maintains a warm, encouraging tone
5. Keeps the message concise (2-3 sentences)

Do not include specific scores in the message - just provide encouragement and next steps information."""
    
    @classmethod
    def get_fallback_response(cls, error_type: str, error_details: str = "") -> str:
        """Generate fallback responses for error handling."""
        fallback_responses = {
            "welcome_error": "I apologize for the technical issue. Let me introduce myself - I'm here to help you with a clinical assessment of your daily activities. We'll go through questions about things like shopping, cooking, bathing, and dressing to understand how you're managing with daily tasks. This helps your healthcare team provide the best care for you.",
            "question_error": "I encountered a brief technical issue while asking that question. Let me continue with our assessment. Please tell me about your current abilities with daily activities, and I'll help interpret your responses.",
            "transition_error": "I had a small technical hiccup while transitioning between sections of the assessment. We're making good progress through your daily activity questions. Let me continue where we left off.",
            "completion_error": "I experienced a technical issue while completing your assessment, but your responses have been saved. Thank you for providing detailed information about your daily activities. Your healthcare team will have the information they need.",
            "general_error": "I apologize for the technical interruption. Let's continue with your assessment - your responses are important for understanding your daily functioning."
        }
        
        response = fallback_responses.get(error_type, fallback_responses["general_error"])
        if error_details:
            response += f" (Technical details: {error_details[:100]}...)"
        
        return response


class PromptValidator:
    """Validates and tests clinical assessment prompts"""
    
    @staticmethod
    def validate_system_prompt(prompt: str) -> Dict[str, Any]:
        """Validate system prompt completeness and clinical appropriateness"""
        validation_results = {
            "is_valid": True,
            "issues": [],
            "recommendations": []
        }
        
        required_elements = [
            "clinical assessment",
            "ADL",
            "IADL",
            "empathetic",
            "professional"
        ]
        
        for element in required_elements:
            if element.lower() not in prompt.lower():
                validation_results["issues"].append(f"Missing key element: {element}")
                validation_results["is_valid"] = False
        
        # Check length (should be comprehensive but not overwhelming)
        if len(prompt) < 200:
            validation_results["issues"].append("Prompt may be too brief for clinical context")
        elif len(prompt) > 2000:
            validation_results["recommendations"].append("Consider breaking into smaller, focused prompts")
        
        return validation_results

    @staticmethod
    def test_prompt_generation(question_data: Dict[str, Any], test_responses: List[str]) -> Dict[str, Any]:
        """Test prompt generation with sample data"""
        test_results = {
            "question_prompt": None,
            "interpretation_prompts": [],
            "errors": []
        }
        
        try:
            # Test question prompt generation
            context = {"current_phase": "iadl", "question_number": 1}
            test_results["question_prompt"] = ClinicalPromptTemplate.get_question_prompt(question_data, context)
            
            # Test interpretation prompt generation
            for response in test_responses:
                interp_prompt = ClinicalPromptTemplate.get_interpretation_prompt(question_data, response)
                test_results["interpretation_prompts"].append({
                    "user_response": response,
                    "interpretation_prompt": interp_prompt
                })
                
        except Exception as e:
            test_results["errors"].append(str(e))
        
        return test_results
