"""
Neo4j Question Service - Dynamic Clinical Assessment Questions
============================================================
Replaces static clinical_assessment_data.py with dynamic Neo4j graph queries.
Maintains the same API interface while enabling flexible question management.
"""

import os
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

class Neo4jQuestionService:
    """Service for managing clinical assessment questions via Neo4j."""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """Initialize Neo4j connection."""
        self.uri = uri or os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j") 
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            self.driver.verify_connectivity()
            logger.info("✅ Neo4j connection established")
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def get_iadl_questions(self) -> List[Dict[str, Any]]:
        """Get IADL questions in sequence order."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (q:Question)
                WHERE q.assessment_type = 'IADL'
                OPTIONAL MATCH (q)-[:HAS_OPTION]->(a:Answer)
                WITH q, collect({
                    text: a.text,
                    clinical_score: a.clinical_score,
                    order: a.answer_order
                }) as answers
                RETURN q.code as code,
                       q.domain as domain,
                       q.sequence as sequence,
                       q.text as text,
                       q.description as description,
                       q.assessment_type as assessment_type,
                       answers
                ORDER BY q.sequence
            """)
            
            questions = []
            for record in result:
                questions.append({
                    "code": record["code"],
                    "domain": record["domain"],
                    "sequence": record["sequence"],
                    "text": record["text"],
                    "description": record["description"],
                    "assessment_type": record["assessment_type"],
                    "answers": sorted(record["answers"], key=lambda x: x["order"])
                })
            
            logger.debug(f"Retrieved {len(questions)} IADL questions")
            return questions
    
    def get_adl_questions(self) -> List[Dict[str, Any]]:
        """Get ADL questions in sequence order.""" 
        with self.driver.session() as session:
            result = session.run("""
                MATCH (q:Question)
                WHERE q.assessment_type = 'ADL'
                OPTIONAL MATCH (q)-[:HAS_OPTION]->(a:Answer)
                WITH q, collect({
                    text: a.text,
                    clinical_score: a.clinical_score,
                    order: a.answer_order
                }) as answers
                RETURN q.code as code,
                       q.domain as domain,
                       q.sequence as sequence,
                       q.text as text,
                       q.description as description,
                       q.assessment_type as assessment_type,
                       answers
                ORDER BY q.sequence
            """)
            
            questions = []
            for record in result:
                questions.append({
                    "code": record["code"],
                    "domain": record["domain"],
                    "sequence": record["sequence"],
                    "text": record["text"],
                    "description": record["description"],
                    "assessment_type": record["assessment_type"],
                    "answers": sorted(record["answers"], key=lambda x: x["order"])
                })
            
            logger.debug(f"Retrieved {len(questions)} ADL questions")
            return questions
    
    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all questions: IADL first (sequence), then ADL (sequence)."""
        iadl_questions = self.get_iadl_questions()
        adl_questions = self.get_adl_questions()
        return iadl_questions + adl_questions
    
    def get_question_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by its code."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (q:Question {code: $code})
                OPTIONAL MATCH (q)-[:HAS_OPTION]->(a:Answer)
                WITH q, collect({
                    text: a.text,
                    clinical_score: a.clinical_score,
                    order: a.answer_order
                }) as answers
                RETURN q.code as code,
                       q.domain as domain,
                       q.sequence as sequence,
                       q.text as text,
                       q.description as description,
                       q.assessment_type as assessment_type,
                       answers
            """, code=code)
            
            record = result.single()
            if not record:
                return None
                
            return {
                "code": record["code"],
                "domain": record["domain"],
                "sequence": record["sequence"],
                "text": record["text"],
                "description": record["description"],
                "assessment_type": record["assessment_type"],
                "answers": sorted(record["answers"], key=lambda x: x["order"])
            }
    
    def get_next_question_code(self, current_code: str) -> Optional[str]:
        """Get the next question code in the flow using graph relationships."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (q:Question {code: $code})-[:NEXT_QUESTION]->(next:Question)
                RETURN next.code as next_code
            """, code=current_code)
            
            record = result.single()
            return record["next_code"] if record else None
    
    def get_first_question_code(self) -> Optional[str]:
        """Get the first question in the assessment flow."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (start:AssessmentFlow {type: 'introduction'})-[:STARTS_WITH]->(q:Question)
                RETURN q.code as first_code
                UNION
                MATCH (q:Question)
                WHERE q.assessment_type = 'IADL' AND q.sequence = 1
                RETURN q.code as first_code
                LIMIT 1
            """)
            
            record = result.single()
            return record["first_code"] if record else None

# Global service instance (lazy initialization)
_question_service: Optional[Neo4jQuestionService] = None

def get_question_service() -> Neo4jQuestionService:
    """Get or create the global question service instance."""
    global _question_service
    if _question_service is None:
        _question_service = Neo4jQuestionService()
    return _question_service

# Compatibility functions to maintain existing API
def get_iadl_questions() -> List[Dict[str, Any]]:
    """Get IADL questions - maintains compatibility with clinical_assessment_data."""
    return get_question_service().get_iadl_questions()

def get_adl_questions() -> List[Dict[str, Any]]:
    """Get ADL questions - maintains compatibility with clinical_assessment_data."""
    return get_question_service().get_adl_questions()

def get_all_questions() -> List[Dict[str, Any]]:
    """Get all questions - maintains compatibility with clinical_assessment_data."""
    return get_question_service().get_all_questions()

def get_assessment_order() -> Dict[str, Any]:
    """Get assessment order info - returns dict for API compatibility."""
    questions = get_all_questions()
    iadl_count = len([q for q in questions if q["assessment_type"] == "IADL"])
    adl_count = len([q for q in questions if q["assessment_type"] == "ADL"])
    
    return {
        "total_questions": len(questions),
        "phase_1": {
            "name": "IADL",
            "count": iadl_count,
            "description": "Instrumental Activities of Daily Living"
        },
        "phase_2": {
            "name": "ADL", 
            "count": adl_count,
            "description": "Activities of Daily Living"
        },
        "rationale": "IADL questions are asked first as they are less intrusive and assess community functioning. ADL questions follow as they are more personal and assess basic self-care abilities.",
        "order": ["IADL", "ADL"]
    }

# Cleanup function for application shutdown
def cleanup_question_service():
    """Clean up global question service connection."""
    global _question_service
    if _question_service:
        _question_service.close()
