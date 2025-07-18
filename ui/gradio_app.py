"""
Clinical Assessment Dashboard - Gradio UI
========================================
Interactive dashboard connecting to the Neo4j-powered clinical assessment API.
Features chat interface with live progress tracking and scoring visualization.
"""

import gradio as gr
import requests
import json
import os
from typing import Dict, Any, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration - Use environment variable for container communication
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class AssessmentDashboard:
    def __init__(self):
        self.session_id = None
        self.current_progress = {"iadl": [], "adl": []}
        self.current_scores = {"iadl": 0, "adl": 0, "total_iadl": 8, "total_adl": 100}
        
    def create_session(self, patient_id: str = "dashboard_patient") -> Tuple[List[Dict], Dict]:
        """Create a new assessment session"""
        logger.info(f"Creating new session for patient: {patient_id}")
        
        try:
            url = f"{API_BASE_URL}/assessment/sessions"
            payload = {"patient_id": patient_id, "metadata": {"ui": "gradio_dashboard"}}
            
            logger.info(f"Sending POST to {url} with payload: {payload}")
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            self.session_id = data["session_id"]
            logger.info(f"Session created successfully: {self.session_id}")
            
            return self.load_conversation_history(), self.create_progress_display()
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            error_msg = [{"role": "assistant", "content": f"❌ Failed to start session: {str(e)}"}]
            return error_msg, {}
    
    def load_conversation_history(self) -> List[Dict]:
        """Load conversation history from API session"""
        if not self.session_id:
            return []
            
        try:
            response = requests.get(f"{API_BASE_URL}/assessment/sessions/{self.session_id}/summary")
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Loaded session summary data: {data.keys()}")
            conversation_history = data.get("conversation_history", [])
            logger.info(f"Conversation history length: {len(conversation_history)}")
            
            # Convert conversation history to Gradio messages format
            messages = []
            for turn in conversation_history:
                logger.info(f"Processing turn: {turn}")
                if turn["role"] == "assistant" or turn["role"] == "system":
                    messages.append({
                        "role": "assistant", 
                        "content": turn["content"]
                    })
                elif turn["role"] == "user":
                    messages.append({
                        "role": "user", 
                        "content": turn["content"]
                    })
            
            logger.info(f"Processed {len(messages)} messages for UI")
            
            # Update progress from session data
            self.update_progress_from_session(data)
            
            return messages
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return [{"role": "assistant", "content": "Session started, but couldn't load conversation history."}]
    
    def send_response(self, user_message: str, chat_history: List) -> Tuple[List, str, Dict]:
        """Send user response to API and get next question"""
        logger.info(f"Sending response: {user_message}")
        
        if not self.session_id:
            logger.warning("No session ID available")
            chat_history.append({"role": "assistant", "content": "Please start a new session first."})
            return chat_history, "", {}
            
        try:
            # Add user message to chat
            chat_history.append({"role": "user", "content": user_message})
            
            # Prepare API request
            url = f"{API_BASE_URL}/assessment/sessions/{self.session_id}/respond"
            payload = {
                "user_input": user_message,
                "session_id": self.session_id
            }
            
            logger.info(f"Sending POST to {url} with payload: {payload}")
            
            # Send to API
            response = requests.post(url, json=payload)
            
            logger.info(f"API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API error response: {response.text}")
                
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"API response data: {data}")
            
            # Add bot response to chat
            chat_history.append({"role": "assistant", "content": data["message"]})
            
            # Update progress tracking
            self.update_progress_from_session(data)
            
            return chat_history, "", self.create_progress_display()
            
        except Exception as e:
            logger.error(f"Error in send_response: {str(e)}")
            error_msg = f"❌ Error: {str(e)}"
            chat_history.append({"role": "assistant", "content": error_msg})
            return chat_history, "", {}
    
    def update_progress_from_session(self, session_data: Dict):
        """Update progress tracking from session data"""
        try:
            # Use the update_progress method which handles the correct API response format
            self.update_progress(session_data)
            logger.info(f"Updated progress from session data: {self.current_progress}")
        except Exception as e:
            logger.error(f"Error updating progress from session: {e}")
    
    def update_progress(self, api_response: Dict):
        """Update progress tracking from API response"""
        try:
            progress_str = api_response.get("progress", "0/18")
            current, total = map(int, progress_str.split("/"))
            phase = api_response.get("phase", "welcome")
            
            logger.info(f"Updating progress: {progress_str}, phase: {phase}")
            
            # Update phase-specific progress
            if phase == "iadl":
                # IADL questions are 1-8
                iadl_completed = min(current, 8)
                self.current_progress["iadl"] = list(range(1, iadl_completed + 1))
                logger.info(f"IADL progress: {self.current_progress['iadl']}")
            elif phase == "adl":
                # ADL questions are 9-18 (so ADL progress is current - 8)
                adl_completed = max(0, current - 8)
                self.current_progress["iadl"] = list(range(1, 9))  # All IADL done
                self.current_progress["adl"] = list(range(1, adl_completed + 1))
                logger.info(f"ADL progress: {self.current_progress['adl']}")
            elif phase == "complete" or current >= 18:
                # Assessment completed
                self.current_progress["iadl"] = list(range(1, 9))  # All IADL done
                self.current_progress["adl"] = list(range(1, 11))  # All ADL done
                logger.info("Assessment completed - all questions done")
            
            # Try to fetch current scores from summary API whenever we have progress
            # This ensures scores update throughout the assessment, not just at the end
            if self.session_id and current > 0:
                logger.info(f"Fetching scores after {current} questions completed")
                self.fetch_current_scores()
                
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def fetch_current_scores(self):
        """Fetch current scores from session summary API"""
        try:
            if not self.session_id:
                return
                
            url = f"{API_BASE_URL}/assessment/sessions/{self.session_id}/summary"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                scores = data.get("scores", {})
                
                logger.info(f"API returned scores data: {scores}")
                
                # Update scores if available - using the correct field names
                if "iadl_total" in scores:
                    self.current_scores["iadl"] = scores["iadl_total"]["raw_score"]
                    logger.info(f"Updated IADL score: {self.current_scores['iadl']}")
                if "adl_total" in scores:
                    self.current_scores["adl"] = scores["adl_total"]["raw_score"]
                    logger.info(f"Updated ADL score: {self.current_scores['adl']}")
                    
                logger.info(f"Final scores: IADL={self.current_scores['iadl']}, ADL={self.current_scores['adl']}")
            else:
                logger.warning(f"Could not fetch scores, API returned {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.warning(f"Could not fetch current scores: {e}")
    
    def create_progress_display(self) -> Dict:
        """Create progress visualization data"""
        return {
            "iadl_progress": self.current_progress["iadl"],
            "adl_progress": self.current_progress["adl"],
            "iadl_score": self.current_scores["iadl"],
            "adl_score": self.current_scores["adl"],
            "iadl_total": self.current_scores["total_iadl"],
            "adl_total": self.current_scores["total_adl"]
        }
    
    def create_subway_map(self, progress_data: Dict) -> go.Figure:
        """Create subway map style progress indicators"""
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("IADL Progress (8 Questions)", "ADL Progress (10 Questions)"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # IADL Subway Map (Left Column)
        iadl_labels = [
            "Telephone", "Shopping", "Food Prep", "Housekeeping",
            "Laundry", "Transport", "Medication", "Finances"
        ]
        iadl_colors = ["#28a745" if i+1 in progress_data.get("iadl_progress", []) else "#e9ecef" for i in range(8)]
        
        fig.add_trace(
            go.Scatter(
                x=[0] * 8,
                y=list(range(8)),
                mode='markers+text',
                marker=dict(size=30, color=iadl_colors, line=dict(width=2, color="#000")),
                text=iadl_labels,
                textposition="middle right",
                textfont=dict(size=10),
                name="IADL",
                showlegend=False
            ),
            row=1, col=1
        )
        
        # ADL Subway Map (Right Column)
        adl_labels = [
            "Bowel", "Bladder", "Grooming", "Toilet", "Feeding",
            "Transfer", "Mobility", "Dressing", "Stairs", "Bathing"
        ]
        adl_colors = ["#007bff" if i+1 in progress_data.get("adl_progress", []) else "#e9ecef" for i in range(10)]
        
        fig.add_trace(
            go.Scatter(
                x=[1] * 10,
                y=list(range(10)),
                mode='markers+text',
                marker=dict(size=30, color=adl_colors, line=dict(width=2, color="#000")),
                text=adl_labels,
                textposition="middle right",
                textfont=dict(size=10),
                name="ADL",
                showlegend=False
            ),
            row=1, col=2
        )
        
        # Style the subway maps
        fig.update_xaxes(visible=False, row=1, col=1)
        fig.update_xaxes(visible=False, row=1, col=2)
        fig.update_yaxes(visible=False, row=1, col=1)
        fig.update_yaxes(visible=False, row=1, col=2)
        
        fig.update_layout(
            height=500,
            title_text="Assessment Progress Tracking",
            title_x=0.5,
            showlegend=False
        )
        
        return fig
    
    def create_score_meters(self, progress_data: Dict) -> go.Figure:
        """Create score meter visualizations"""
        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "indicator"}, {"type": "indicator"}]],
            subplot_titles=("IADL Score", "ADL Score")
        )
        
        # IADL Score Meter (0-8 scale)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=progress_data.get("iadl_score", 0),
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "IADL Score"},
                delta={'reference': progress_data.get("iadl_total", 8)},
                gauge={
                    'axis': {'range': [None, 8]},
                    'bar': {'color': "#28a745"},
                    'steps': [
                        {'range': [0, 4], 'color': "#ffe6e6"},
                        {'range': [4, 6], 'color': "#fff2e6"},
                        {'range': [6, 8], 'color': "#e6ffe6"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 6
                    }
                }
            ),
            row=1, col=1
        )
        
        # ADL Score Meter (0-100 scale)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=progress_data.get("adl_score", 0),
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "ADL Score"},
                delta={'reference': progress_data.get("adl_total", 100)},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#007bff"},
                    'steps': [
                        {'range': [0, 40], 'color': "#ffe6e6"},
                        {'range': [40, 70], 'color': "#fff2e6"},
                        {'range': [70, 100], 'color': "#e6ffe6"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ),
            row=1, col=2
        )
        
        fig.update_layout(height=400, title_text="Clinical Scores", title_x=0.5)
        return fig

# Initialize dashboard
dashboard = AssessmentDashboard()

def start_new_session():
    """Start a new assessment session"""
    messages, progress = dashboard.create_session()
    subway_map = dashboard.create_subway_map(progress)
    score_meters = dashboard.create_score_meters(progress)
    return messages, "", subway_map, score_meters

def respond_to_assessment(user_message, chat_history):
    """Handle user responses in the assessment"""
    chat_history, cleared_input, progress = dashboard.send_response(user_message, chat_history)
    subway_map = dashboard.create_subway_map(progress)
    score_meters = dashboard.create_score_meters(progress)
    return chat_history, cleared_input, subway_map, score_meters

# Create Gradio Interface
with gr.Blocks(title="Clinical Assessment Dashboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🏥 Clinical Assessment Dashboard
        **ADL/IADL Assessment with Live Progress Tracking**
        
        This dashboard provides an interactive clinical assessment experience with real-time progress visualization.
        Connected to API at: `{}`
        """.format(API_BASE_URL)
    )
    
    with gr.Row():
        # Left Column - Chat Interface
        with gr.Column(scale=1):
            gr.Markdown("## 💬 Assessment Conversation")
            
            chatbot = gr.Chatbot(
                height=500,
                placeholder="Click 'Start New Assessment' to begin...",
                avatar_images=(None, "🏥"),
                type="messages"
            )
            
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="Type your response here...",
                    container=False,
                    scale=4
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)
            
            start_btn = gr.Button("🚀 Start New Assessment", variant="secondary", size="lg")
        
        # Right Column - Progress Dashboard
        with gr.Column(scale=1):
            gr.Markdown("## 📊 Progress Dashboard")
            
            # Subway Map Progress
            progress_plot = gr.Plot(label="Question Progress")
            
            # Score Meters
            scores_plot = gr.Plot(label="Clinical Scores")
            
            # Assessment Info
            with gr.Accordion("Assessment Information", open=False):
                gr.Markdown(
                    """
                    **IADL (Instrumental Activities of Daily Living)**
                    - 8 questions about complex daily activities
                    - Scale: 0-8 points (8 = fully independent)
                    - Covers: telephone, shopping, cooking, housekeeping, etc.
                    
                    **ADL (Activities of Daily Living)**  
                    - 10 questions about basic self-care activities
                    - Scale: 0-100 points (100 = fully independent)
                    - Covers: bathing, dressing, mobility, feeding, etc.
                    """
                )
    
    # Event Handlers
    start_btn.click(
        start_new_session,
        outputs=[chatbot, msg_input, progress_plot, scores_plot]
    )
    
    send_btn.click(
        respond_to_assessment,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input, progress_plot, scores_plot]
    )
    
    msg_input.submit(
        respond_to_assessment,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input, progress_plot, scores_plot]
    )

if __name__ == "__main__":
    print("🚀 Starting Clinical Assessment Dashboard...")
    print(f"🔗 Connecting to API at: {API_BASE_URL}")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
