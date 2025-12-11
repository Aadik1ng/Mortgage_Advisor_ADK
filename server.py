"""
FastAPI Server for UAE Mortgage Assistant.

This server wraps the Google ADK agent with a REST API and provides:
- REST API for chat interactions
- Server-Sent Events (SSE) for streaming responses
- Conversation history management
- Lead capture endpoints
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, AsyncGenerator
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the ADK agent and tools
from mortgage_agent.agent import root_agent, load_system_prompt
from mortgage_agent.tools import (
    tool_calculate_mortgage,
    tool_assess_affordability,
    tool_compare_buy_vs_rent,
    tool_check_eligibility,
    tool_get_uae_mortgage_rules,
)

# Google ADK imports
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings:
    """Application settings loaded from environment."""
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    # Support both Google and Groq/LiteLLM keys
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "groq/llama-3.3-70b-versatile")

    @property
    def is_api_key_configured(self) -> bool:
        return bool(self.GOOGLE_API_KEY or self.GROQ_API_KEY)


settings = Settings()


# ============================================================================
# ADK SESSION MANAGEMENT
# ============================================================================

# Create session service for conversation management
session_service = InMemorySessionService()

# Create the ADK runner
runner = Runner(
    agent=root_agent,
    app_name="uae_mortgage_assistant",
    session_service=session_service,
)


# ============================================================================
# LEAD STORAGE
# ============================================================================

class LeadStore:
    """Simple in-memory lead storage."""
    
    def __init__(self):
        self.leads: list[dict] = []
    
    def add_lead(self, conv_id: str, email: str, phone: str = "", name: str = ""):
        """Capture a lead."""
        self.leads.append({
            "conversation_id": conv_id,
            "email": email,
            "phone": phone,
            "name": name,
            "timestamp": datetime.now().isoformat(),
        })


lead_store = LeadStore()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "default_user"


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    conversation_id: str


class LeadCaptureRequest(BaseModel):
    """Request model for lead capture."""
    conversation_id: str
    email: str
    phone: Optional[str] = ""
    name: Optional[str] = ""


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🏠 UAE Mortgage Assistant (Google ADK) starting up...")
    print(f"   Model: {settings.MODEL_NAME}")
    print(f"   API Key configured: {'Yes' if settings.is_api_key_configured else 'No'}")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="UAE Mortgage Assistant",
    description="AI-powered conversational mortgage advisor for UAE expats - Built with Google ADK",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="""
    <html>
        <head><title>UAE Mortgage Assistant</title></head>
        <body>
            <h1>🏠 UAE Mortgage Assistant</h1>
            <p>API is running. Frontend not found at /static/index.html</p>
            <p>Try the API at <a href="/docs">/docs</a></p>
        </body>
    </html>
    """)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a response using Google ADK.
    """
    if not settings.is_api_key_configured:
        raise HTTPException(status_code=500, detail="API Key (GOOGLE_API_KEY or GROQ_API_KEY) not configured")
    
    # Get or create session
    user_id = request.user_id or "default_user"
    session_id = request.conversation_id or str(uuid.uuid4())
    
    # Get or create session in ADK
    session = session_service.get_session(
        app_name="uae_mortgage_assistant",
        user_id=user_id,
        session_id=session_id,
    )
    
    if session is None:
        session = session_service.create_session(
            app_name="uae_mortgage_assistant",
            user_id=user_id,
            session_id=session_id,
        )
    
    # Create the user message content
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=request.message)]
    )
    
    # Run the agent
    full_response = ""
    
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_content,
    ):
        # Collect agent response text
        if hasattr(event, 'content') and event.content:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    full_response += part.text
    
    return ChatResponse(response=full_response, conversation_id=session_id)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a message and stream the response using Server-Sent Events (SSE).
    """
    if not settings.is_api_key_configured:
        raise HTTPException(status_code=500, detail="API Key (GOOGLE_API_KEY or GROQ_API_KEY) not configured")
    
    user_id = request.user_id or "default_user"
    session_id = request.conversation_id or str(uuid.uuid4())
    
    # Get or create session
    session = session_service.get_session(
        app_name="uae_mortgage_assistant",
        user_id=user_id,
        session_id=session_id,
    )
    
    if session is None:
        session = session_service.create_session(
            app_name="uae_mortgage_assistant",
            user_id=user_id,
            session_id=session_id,
        )
    
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=request.message)]
    )
    
    async def generate():
        # Send conversation ID first
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': session_id})}\n\n"
        
        full_response = ""
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        chunk = part.text
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        yield f"data: {json.dumps({'type': 'end', 'conversation_id': session_id})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str, user_id: str = "default_user"):
    """Get conversation history from ADK session."""
    session = session_service.get_session(
        app_name="uae_mortgage_assistant",
        user_id=user_id,
        session_id=session_id,
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Extract messages from session events
    messages = []
    for event in session.events:
        if hasattr(event, 'content') and event.content:
            role = event.content.role if hasattr(event.content, 'role') else 'assistant'
            text = ""
            for part in event.content.parts:
                if hasattr(part, 'text'):
                    text += part.text
            if text:
                messages.append({"role": role, "content": text})
    
    return {"conversation_id": session_id, "messages": messages}


@app.post("/api/lead")
async def capture_lead(request: LeadCaptureRequest):
    """Capture user contact details for follow-up."""
    lead_store.add_lead(
        conv_id=request.conversation_id,
        email=request.email,
        phone=request.phone or "",
        name=request.name or ""
    )
    return {"status": "success", "message": "Thank you! We'll be in touch soon."}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": "Google ADK",
        "model": settings.MODEL_NAME,
        "api_key_configured": bool(settings.GOOGLE_API_KEY),
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
