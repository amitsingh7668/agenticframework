import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("POSTGRES_DB_URL", "postgresql://agentuser:secret123@localhost:15432/agents_db")

def get_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def get_total_sessions():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(DISTINCT session_id) FROM messages")
        return cur.fetchone()["count"]

def get_total_queries():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'")
        return cur.fetchone()["count"]

def get_guardrail_blocks():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM messages WHERE role = 'error' AND content LIKE '%Guardrail%'")
        return cur.fetchone()["count"]

def get_session_stats():
    with get_connection() as conn, conn.cursor() as cur:
        # Step 1: Basic summary stats
        cur.execute("""
            SELECT session_id,
                   COUNT(*) AS total_messages,
                   SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) AS total_queries,
                   SUM(CASE WHEN role = 'error' AND content LIKE '%Guardrail%' THEN 1 ELSE 0 END) AS guardrail_blocks
            FROM messages
            GROUP BY session_id
        """)
        summary = cur.fetchall()

        # Step 2: Fetch user messages per session
        cur.execute("""
            SELECT session_id, ARRAY_AGG(content) AS questions
            FROM messages
            WHERE role = 'user'
            GROUP BY session_id
        """)
        questions = {row["session_id"]: row["questions"] for row in cur.fetchall()}

        # Merge the two
        for row in summary:
            row["questions"] = questions.get(row["session_id"], [])

        return summary

