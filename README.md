# 🚀 Project Kickoff: Knowledge Graph-Driven Assessment Bot (ADL/IADL) 

## Vision
Build a production-ready, containerized chatbot platform that guides users (patients or clinicians) through structured clinical assessments (ADL & IADL) using a **knowledge graph** for flow control, full-stack modern Python/LLM techniques, and interactive dashboards.

---

## Key Features & Tech Stack

- **Knowledge Graph**: Neo4j graph database represents assessment domains, questions, answer options, and sequential flow (IADL → ADL).
- **Conversational AI**: LLM-powered chatbot (OpenAI API or local Ollama/Deepseek LLM) interprets free-form answers and maps to clinical scores.
- **FastAPI Backend**: Provides API endpoints for session management, assessment scoring, and audit.
- **Gradio UI**: Clean, responsive chat interface and dashboard visualizing progress and results.
- **PostgreSQL DB**: Stores patients, sessions, responses, scores, and chat logs for audit and analytics.
- **Containerized**: Docker Compose for reproducible local and cloud deployments.
- **Shared Python Module**: Single source of truth for clinical data (question text, scoring, etc.)—used to seed both Neo4j and Postgres.

---

## Problem to Solve
How can we use **knowledge graphs** to drive dynamic, auditable, and customizable clinical assessments—with full conversational logging, scoring, and UI—all in an open, reproducible stack?

---

## What’s Done / What’s Needed
- Initial clinical data module and schema defined
- Base Docker Compose and service structure in place
- Need help with:
    - Graph database best practices for assessments
    - LLM prompt engineering and NLU pipeline
    - FastAPI and UI/UX polish
    - CI/CD for deployment

---

## Why This is Cool
- Mixes graph reasoning, NLP, and conversational UI
- HIPAA-aware, extensible to other assessments
- Great for research, clinics, and demoing modern Python/AI

---

## How to Get Started
- Clone the repo, check out `/shared/clinical_assessment_data.py`, and run the seed scripts!
- Propose ideas for improvement, submit PRs, or request issues to claim

**Let’s build a state-of-the-art, knowledge-graph-powered assessment bot—together!**




# 🌀 ADL/IADL Knowledge Graph Chatbot

## 🎯 **Project Overview**

This project aims to **combine knowledge graphs and large language models (LLMs) for intelligent administration of standardized assessments**—specifically, the Activities of Daily Living (ADL) and Instrumental Activities of Daily Living (IADL) scales. The chatbot will initially use the OpenAI API (GPT-4o), but the architecture is designed for **easy migration to local LLMs** (e.g., via Ollama/Deepseek/LM Studio), leveraging the flexibility of [LangChain](https://python.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/).

**Key innovation:** A knowledge graph encodes assessment flow and scoring rubrics, enabling the LLM chatbot to conduct adaptive, accurate, and explainable evaluations in natural conversation.

---

### **Project Goals**
1. **Inject knowledge graph context into LLM prompts** to guide assessment flow.
2. **Use LLMs for NLU:** Convert free-text user answers into structured assessment scores.
3. **Dashboarding:** Visualize assessment results for users and clinicians.
4. **Patient Data Tracking:** Persist all results securely and accessibly.
5. **Measure response similarity and latency** across multiple LLM runs.

---

## 🏗️ **Architecture**

### **Core Concept**
- **LLM-Driven Test Administration:** An LLM (OpenAI or local) conducts assessments in natural language, guided by graph-derived prompts.
- **Knowledge Graph Backbone:** Assessment items (questions, scoring, logic) are nodes and relationships in a Neo4j graph.
- **Intelligent Navigation:** The LLM follows the graph’s flow to ensure all required domains are covered.
- **Full-Stack Integration:** User interaction, scoring, and data storage are modular, containerized, and reproducible.

---

### **Tech Stack**
| Component      | Tool/Service                  | Purpose                                   |
|----------------|------------------------------|-------------------------------------------|
| LLM            | OpenAI API, Ollama, Deepseek | Language understanding, scoring, chat     |
| Frontend       | Gradio  (also Jupyter)       | Chat interface & dashboard  (analytics)   |
| Backend        | FastAPI                      | Orchestrate flows, serve API              |
| Knowledge Graph| Neo4j                        | Assessment logic and flow                 |
| Database       | PostgreSQL                   | Patient records, assessment data          |
| Language       | Python 3.11                  | Implementation language                   |
| Deployment     | Docker Compose               | Portable, multi-service stack             |

---

## 📋 **Scope Definition**

### **What's Included** ✅
- **Complete ADL/IADL Administration:** All domains, with flexible question order via the KG.
- **Knowledge Graph Navigation:** Neo4j structure enforces assessment logic and scoring.
- **Conversational Interface:** Natural language chat, structured result extraction.
- **Data Persistence:** Store raw responses and scores in Postgres.
- **Progress Tracking:** Live progress/status indicator.
- **Result Dashboard:** Summary of scores, data export.
- **LLM Abstraction:** Easily swap cloud and local LLMs via LangChain.

### **What's Not Included** ❌
- Clinical hazard/risk analysis
- Automated service/intervention recommendations
- Medical device integration
- Multi-user management (MVP: single user at a time)

---

## 🌐 **Knowledge Graph Design**

### **Node Types**
Question Nodes:
- id: "adl_feeding"
- text: "How is your ability to feed yourself?"
- domain: "feeding"
- type: "question"

Answer Nodes:
- id: "feeding_0", "feeding_1", "feeding_2", "feeding_3"
- text: "Independent", "Needs help", "Unable", etc.
- value: 0, 1, 2, 3
- type: "answer"

Flow Nodes:
- id: "start", "completion"
- type: "flow_control"

### **Edge Types**
NEXT_QUESTION:  Question → Question (sequential flow)  
HAS_OPTION:     Question → Answer (available responses)

---

## 🎮 **User Experience Flow**

1. **Start Assessment:** User begins the chat—"Let's start your ADL assessment!"
2. **Graph Navigation:** The bot queries Neo4j for the next relevant question node.
3. **Conversational Input:** User replies naturally; bot follows up as needed.
4. **Answer Extraction:** LLM parses response and assigns a structured score using criteria from the graph.
5. **Progress Tracking:** Visual progress bar, status messages, and ability to resume.
6. **Results Summary:** Final dashboard with total scores, per-domain breakdown, and export options (CSV/JSON).

---

## 🚀 **Future Directions**
- Add multi-hop reasoning or intervention suggestions from the KG
- Support more assessments (MMSE, MoCA, custom flows)
- Enable secure, multi-user support and audit trails
- Research bidirectional KG-LLM updates (e.g., KG enrichment from new responses)

---

## 📝 **Project Principles**
- **Open Source, Reproducible:** All code and data structures in version control.
- **Privacy First:** No PHI in test deployments; all patient data is for demo/dev only.
- **Migration Ready:** Easy transition from cloud to local LLMs.

---

## 👨‍💻 **Contributing**

Pull requests and collaboration are welcome!  
For setup instructions, see `README_setup.md`.

## License
Citation If you use this software in academic research, publications, or commercial projects, please cite: Mark Dranias. (2025). ADL/IADL Assessment Chatbot and database. GitHub. [https://github.com/mrdranias/assessment_bot] For BibTeX: bibtex@software{assessment_bot_2025, author = {Mark Dranias}, title = {ADL/IADL Assessment Chatbot and database}, url = {https://github.com/mrdranias/assessment_bot}, year = {2025} }

License MIT License Copyright (c) 2025 Mark Dranias Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. Note on Citations: While not legally required by the MIT License, we strongly encourage citation in academic and research contexts to support continued development of open-source rural healthcare tools. Commercial Use This software is open source under the MIT License. For commercial deployment, support, customization, or implementation services, please contact [your email/website]. Disclaimer This software is for care coordination purposes only and does not provide medical advice, diagnosis, or treatment. Always consult qualified healthcare professionals for medical decisions.
---
