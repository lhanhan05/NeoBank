import os

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row

app = FastAPI(title="NeoBank Corporate Support Service")

CORE_DB_HOST = os.getenv("CORE_DB_HOST", "core-db")
CORE_DB_PORT = os.getenv("CORE_DB_PORT", "5432")
CORE_DB_NAME = os.getenv("CORE_DB_NAME", "neobank_core")
CORE_DB_USER = os.getenv("CORE_DB_USER", "core_user")
CORE_DB_PASSWORD = os.getenv("CORE_DB_PASSWORD", "core_pass_dev")


def get_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=CORE_DB_HOST,
        port=CORE_DB_PORT,
        dbname=CORE_DB_NAME,
        user=CORE_DB_USER,
        password=CORE_DB_PASSWORD,
        row_factory=dict_row,
    )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    with get_conn() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/tickets")
def list_tickets() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, customer_id, subject, body, status, created_at, updated_at
            FROM support_tickets
            ORDER BY created_at DESC
            """
        ).fetchall()
    return list(rows)


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, customer_id, subject, body, status, created_at, updated_at
            FROM support_tickets
            WHERE id = %s
            """,
            (ticket_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return dict(row)
