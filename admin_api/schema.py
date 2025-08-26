import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("POSTGRES_DB_URL", "postgresql://agentuser:secret123@localhost:15432/agents_db")

def get_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def get_schema_details(schema: str = "public"):
    """
    Get all tables and their columns (name + type) for the given schema.
    """
    query = """
    SELECT 
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = %s
    ORDER BY table_name, ordinal_position;
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, (schema,))
        rows = cur.fetchall()

    schema_details = {}
    for row in rows:
        table = row["table_name"]
        if table not in schema_details:
            schema_details[table] = []
        schema_details[table].append({
            "column_name": row["column_name"],
            "data_type": row["data_type"],
            "nullable": row["is_nullable"],
            "default": row["column_default"],
        })
    return schema_details


def delete_all_messages():
    query = "DELETE FROM messages;"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(query)
        conn.commit()
    print("✅ All rows deleted from messages table.")

if __name__ == "__main__":
    schema = get_schema_details()
    for table, cols in schema.items():
        print(f"\n📂 Table: {table}")
        for col in cols:
            print(f"   - {col['column_name']} ({col['data_type']}) "
                  f"NULLABLE={col['nullable']} DEFAULT={col['default']}")
    #delete_all_messages()
