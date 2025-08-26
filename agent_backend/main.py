from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from uuid import uuid4
from datetime import datetime
from session_db import get_total_sessions, get_total_queries, get_guardrail_blocks, get_session_stats ,clear_expired_sessions
from fastapi_utils.tasks import repeat_every
from src.agents.orchestrator import SalesOrchestrator
from src.sessions.manager import session_manager
from src.models.config import get_available_models
from agents.exceptions import InputGuardrailTripwireTriggered
import asyncio

app = FastAPI(title="Sales Assistant API")

# Enable CORS for frontends
app.add_middleware(                                    
    CORSMiddleware,
    allow_origins=["*"],  # Customize for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------#
# Session & State Cache
# ----------------------#
orchestrator_cache: Dict[str, SalesOrchestrator] = {}
user_sessions: Dict[str, Dict] = {}


# ----------------------#
# Request Models
# ----------------------#

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    prompt: str
    session_type: str = "persistent"
    model_name: str
    user_context: Optional[Dict] = {
        "name": "Sales Representative",
        "territory": "Northeast",
        "role": "Sales Rep"
    }

class ChatResponse(BaseModel):
    success: bool
    response: str
    metadata: Optional[Dict] = None


# ----------------------#
# API Endpoints
# ----------------------#

@app.get("/models", summary="List available models")
def list_models():
    available = get_available_models()
    return {name: model.display_name for name, model in available.items()}


def sanitize_session_messages(session) -> List[Dict[str, str]]:
    print("🔍 Type of session:", type(session))
    print("🔍 Attributes:", dir(session))

    if not session:
        print("⚠️ No session provided.")
        return []

    if hasattr(session, "messages"):
        print("📜 Raw messages:")
        print(session.messages)

        clean = []
        for m in session.messages:
            if isinstance(m, dict) and "role" in m and "content" in m:
                clean.append(m)
            else:
                print(f"⚠️ Skipping malformed message: {m}")

        print("✅ Sanitized messages:")
        print(clean)
        return clean

    else:
        print("⚠️ Session object has no 'messages' attribute.")
        return []




@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())[:8]
    session = session_manager.get_session(session_id, req.session_type)


    if req.model_name not in orchestrator_cache:
        try:
            orchestrator_cache[req.model_name] = SalesOrchestrator(
                model_name=req.model_name,
                enable_guardrails=True,
                enable_tracing=False
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to init orchestrator: {str(e)}")

    orchestrator = orchestrator_cache[req.model_name]

    try:
        result = asyncio.run(
            orchestrator.process_query(
                req.prompt,
                user_context=req.user_context,
                session=session
            )
        )

        if result["success"]:
            return ChatResponse(
                success=True,
                response=result["response"],
                metadata={
                    "execution_time": result["execution_time"],
                    "tools_used": result.get("tools_used", []),
                    "model": result.get("model", req.model_name),
                    "session_type": req.session_type,
                    "session_id": session_id
                }
            )
        else:
            print(f"❌ Orchestrator failed: {str(result)}")
            return ChatResponse(success=False, response=result["response"], metadata=None)

    except InputGuardrailTripwireTriggered as e:
        return ChatResponse(success=False, response=f"🛡️ Guardrail triggered: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



@app.post("/session/clear", summary="Clear user chat session")
def clear_session(session_id: str, session_type: str = "persistent"):
    try:
        session_manager.clear_session(session_id, session_type)
        return {"status": "success", "message": "Session cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")


@app.get("/health", summary="System health check")
def health_check():
    from src.knowledge.bedrock_kb import knowledge_base
    return {
        "knowledge_base": knowledge_base.health_check(),
        "active_sessions": len(session_manager.list_active_sessions()),
        "models": list(orchestrator_cache.keys())
    }

@app.get("/metrics/summary")
def summary():
    return {
        "total_sessions": get_total_sessions(),
        "total_queries": get_total_queries(),
        "guardrail_blocks": get_guardrail_blocks(),
    }

@app.get("/sessions/active")
def list_active():
    return session_manager.list_active_sessions()


@app.get("/metrics/sessions")
def sessions():
    stats = get_session_stats()
    return [
        {
            "session_id": row["session_id"],
            "total_messages": row["total_messages"],
            "total_queries": row["total_queries"],
            "guardrail_blocks": row["guardrail_blocks"],
            "questions": row["questions"]  # ✅ added here
        }
        for row in stats
    ]   

@app.on_event("startup")
@repeat_every(seconds=600)  # Run every 10 minutes
def cleanup_sessions_task():
    clear_expired_sessions(timeout_minutes=30)

