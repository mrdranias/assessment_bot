"""
Clinical Assessment API - Main FastAPI Application
=================================================
REST API backend for the Knowledge Graph-Driven Assessment Bot.
Provides endpoints for clinical ADL/IADL assessments using LLM conversation system.
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add the project root to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .routes.assessment_routes import router as assessment_router
from .database import initialize_database, database_health_check


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Clinical Assessment API starting up...")
    
    # Validate environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set OPENAI_API_KEY environment variable")
    else:
        print("✅ Environment variables validated")
    
    # Initialize database
    try:
        print("🗄️ Initializing PostgreSQL database...")
        db_info = initialize_database()
        print(f"✅ Database initialized: {db_info['database_name']}")
        print(f"🔗 Active connections: {db_info['active_connections']}")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("⚠️ API will continue but database features may not work")
    
    print("🏥 Clinical Assessment API ready for patient assessments")
    print("📋 Supporting ADL/IADL assessments with LLM conversation system")
    
    yield
    
    # Shutdown
    print("🔄 Clinical Assessment API shutting down...")
    print("👋 Goodbye!")


# Create FastAPI application
app = FastAPI(
    title="Clinical Assessment API",
    description="""
    **Clinical Assessment API for ADL/IADL Evaluations**
    
    This API provides a conversational interface for administering standardized clinical assessments:
    
    - **Barthel ADL Index**: Activities of Daily Living (10 questions, 0-100 points)
    - **Lawton IADL Scale**: Instrumental Activities of Daily Living (8 questions, 0-8 points)
    
    ## Assessment Flow
    
    1. **Create Session**: Initialize a new assessment session
    2. **IADL Phase**: Start with less intrusive community functioning questions  
    3. **ADL Phase**: Continue with more personal self-care questions
    4. **Completion**: Receive scores and clinical interpretation
    
    ## Key Features
    
    - **LLM-Powered**: Uses GPT-4o for natural conversation and response interpretation
    - **Clinical Accuracy**: Maintains fidelity to published assessment criteria
    - **Empathetic Communication**: Warm, non-judgmental interaction style
    - **Structured Scoring**: Converts free-form responses to standardized clinical scores
    - **Session Management**: Complete conversation history and audit trails
    - **Error Recovery**: Handles ambiguous responses with clarification requests
    
    ## Clinical Considerations
    
    - Questions are ordered IADL → ADL to build rapport before more sensitive topics
    - All responses are interpreted using established clinical scoring criteria
    - Confidence metrics help identify responses that may need human review
    - Complete conversation logs support clinical documentation requirements
    
    **Environment Setup**: Requires `OPENAI_API_KEY` environment variable.
    """,
    version="1.0.0",
    contact={
        "name": "Clinical Assessment Team",
        "email": "clinical-team@assessbot.com"
    },
    license_info={
        "name": "Clinical Use License",
        "identifier": "Clinical"
    },
    lifespan=lifespan
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assessment_router)


@app.get("/", tags=["System"])
async def root() -> Dict[str, Any]:
    """
    API Health Check and Information
    
    Returns basic API information and health status.
    """
    return {
        "service": "Clinical Assessment API",
        "version": "1.0.0",
        "status": "healthy",
        "description": "REST API for clinical ADL/IADL assessments using LLM conversation system",
        "features": [
            "Barthel ADL Index assessment",
            "Lawton IADL Scale assessment", 
            "LLM-powered natural conversation",
            "Clinical score interpretation",
            "Session management",
            "Conversation history tracking"
        ],
        "assessment_order": "IADL (less intrusive) → ADL (more intrusive)",
        "endpoints": {
            "create_session": "POST /assessment/sessions",
            "respond": "POST /assessment/sessions/{session_id}/respond",
            "status": "GET /assessment/sessions/{session_id}/status",
            "summary": "GET /assessment/sessions/{session_id}/summary",
            "info": "GET /assessment/info"
        }
    }


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """
    Detailed Health Check
    
    Validates system dependencies and environment configuration.
    """
    from datetime import datetime
    
    health_status = {
        "api": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    
    # Check environment variables
    if os.getenv("OPENAI_API_KEY"):
        health_status["openai_api"] = "configured"
    else:
        health_status["openai_api"] = "missing_key"
    
    # Check database connection
    try:
        db_health = database_health_check()
        health_status["database"] = db_health["status"]
        if db_health["status"] == "healthy":
            health_status["database_name"] = db_health["database"]
            health_status["database_connections"] = str(db_health["connections"])
        else:
            health_status["database_error"] = db_health.get("error", "unknown")
    except Exception as e:
        health_status["database"] = "error"
        health_status["database_error"] = str(e)
    
    # Check if we can import core modules
    try:
        from .llm.llm_conversation import AssessmentConversationManager
        from .llm.conversation_flow import ConversationFlowOrchestrator
        # Import from local neo4j service
        from .llm.neo4j_question_service import get_all_questions
        health_status["core_modules"] = "loaded"
    except ImportError as e:
        health_status["core_modules"] = f"import_error: {str(e)}"
    
    return health_status


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    # Development server configuration
    print("🏥 Starting Clinical Assessment API in development mode...")
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Run the development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
