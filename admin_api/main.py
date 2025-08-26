from fastapi import FastAPI
from session_db import get_total_sessions, get_total_queries, get_guardrail_blocks, get_session_stats
import uvicorn

app = FastAPI(title="Agent Admin API")

@app.get("/metrics/summary")
def summary():
    return {
        "total_sessions": get_total_sessions(),
        "total_queries": get_total_queries(),
        "guardrail_blocks": get_guardrail_blocks(),
    }

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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9001, reload=True)
