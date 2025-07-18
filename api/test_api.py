"""
Clinical Assessment API Test Script
==================================
Simple test script to validate API endpoints and conversation flow.
"""

import asyncio
import os
import sys
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from fastapi.testclient import TestClient

# Test client
client = TestClient(app)


def test_health_check():
    """Test basic health check endpoint"""
    print("Testing health check endpoint...")
    response = client.get("/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_api_info():
    """Test API info endpoint"""
    print("\nTesting API info endpoint...")
    response = client.get("/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_assessment_info():
    """Test assessment structure info"""
    print("\nTesting assessment info endpoint...")
    response = client.get("/assessment/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_session_creation():
    """Test session creation (requires OPENAI_API_KEY)"""
    print("\nTesting session creation...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping session creation test - OPENAI_API_KEY not set")
        return True
    
    try:
        payload = {
            "patient_id": "test_patient_001",
            "metadata": {"test": True}
        }
        
        response = client.post("/assessment/sessions", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Session ID: {data['session_id']}")
            print(f"Phase: {data['phase']}")
            print(f"Progress: {data['progress']}")
            print(f"Message: {data['message'][:100]}...")
            return True, data['session_id']
        else:
            print(f"Error: {response.json()}")
            return False, None
            
    except Exception as e:
        print(f"Exception during session creation: {str(e)}")
        return False, None


def test_session_status(session_id: str):
    """Test session status endpoint"""
    print(f"\nTesting session status for {session_id}...")
    
    try:
        response = client.get(f"/assessment/sessions/{session_id}/status")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Phase: {data['phase']}")
            print(f"Progress: {data['progress']}")
            return True
        else:
            print(f"Error: {response.json()}")
            return False
            
    except Exception as e:
        print(f"Exception during status check: {str(e)}")
        return False


def test_conversation_response(session_id: str):
    """Test conversation response processing"""
    print(f"\nTesting conversation response for {session_id}...")
    
    try:
        payload = {
            "user_input": "I can use the phone just fine, no problems at all.",
            "session_id": session_id
        }
        
        response = client.post(f"/assessment/sessions/{session_id}/respond", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Phase: {data['phase']}")
            print(f"Progress: {data['progress']}")
            print(f"Should Continue: {data['should_continue']}")
            print(f"Message: {data['message'][:100]}...")
            return True
        else:
            print(f"Error: {response.json()}")
            return False
            
    except Exception as e:
        print(f"Exception during response processing: {str(e)}")
        return False


def test_active_sessions():
    """Test listing active sessions"""
    print("\nTesting active sessions endpoint...")
    
    try:
        response = client.get("/assessment/sessions")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Exception during sessions list: {str(e)}")
        return False


def main():
    """Run all API tests"""
    print("🧪 Clinical Assessment API Test Suite")
    print("=" * 50)
    
    results = []
    
    # Basic endpoint tests
    results.append(("Health Check", test_health_check()))
    results.append(("API Info", test_api_info()))
    results.append(("Assessment Info", test_assessment_info()))
    results.append(("Active Sessions", test_active_sessions()))
    
    # Session-based tests (require OpenAI API key)
    session_id = None
    if os.getenv("OPENAI_API_KEY"):
        print("\n🔑 OPENAI_API_KEY found - testing full conversation flow...")
        session_result, session_id = test_session_creation()
        results.append(("Session Creation", session_result))
        
        if session_result and session_id:
            results.append(("Session Status", test_session_status(session_id)))
            results.append(("Conversation Response", test_conversation_response(session_id)))
    else:
        print("\n⚠️  OPENAI_API_KEY not set - skipping conversation tests")
        print("   To test full functionality, set: export OPENAI_API_KEY='your-key'")
    
    # Print results summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("-" * 25)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if session_id:
        print(f"\n🗑️  Test session created: {session_id}")
        print("   You can manually test further or clean up via DELETE endpoint")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
