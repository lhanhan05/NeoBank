import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

app = FastAPI(title="NeoBank Corporate Support Service")


class TicketResponse(BaseModel):
    id: str
    customer_id: str | None
    subject: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime


class AccountResponse(BaseModel):
    id: str
    customer_id: str
    account_number: str
    account_type: str
    balance: Decimal
    currency: str
    status: str
    card_token: str
    created_at: datetime
    updated_at: datetime


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    amount: Decimal
    currency: str
    transaction_type: str
    merchant_name: str | None
    description: str | None
    status: str
    created_at: datetime


class CreditRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=1)


class AccountActionResponse(BaseModel):
    account_number: str
    previous_status: str
    new_status: str
    balance: Decimal
    detail: str
    audit_log_id: str


class CreditResponse(BaseModel):
    account_number: str
    credited_amount: Decimal
    previous_balance: Decimal
    new_balance: Decimal
    transaction_id: str
    audit_log_id: str
    detail: str


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


def fetch_account_by_number(conn: psycopg.Connection, account_number: str) -> dict:
    row = conn.execute(
        """
        SELECT id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
        FROM accounts
        WHERE account_number = %s
        """,
        (account_number,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Account not found")

    return dict(row)


def write_audit_log(
    conn: psycopg.Connection,
    *,
    action: str,
    resource: str,
    before_state: dict,
    after_state: dict,
) -> str:
    audit_log_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO audit_log (id, actor, action, resource, before_state, after_state)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            audit_log_id,
            "corp-agent",
            action,
            resource,
            json.dumps(before_state),
            json.dumps(after_state),
        ),
    )
    return audit_log_id


@app.get("/health")
def healthcheck() -> dict[str, str]:
    with get_conn() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets() -> list[TicketResponse]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, customer_id, subject, body, status, created_at, updated_at
            FROM support_tickets
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [TicketResponse(**dict(row)) for row in rows]


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str) -> TicketResponse:
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

    return TicketResponse(**dict(row))


@app.get("/accounts/{account_number}", response_model=AccountResponse)
def get_account(account_number: str) -> AccountResponse:
    with get_conn() as conn:
        row = fetch_account_by_number(conn, account_number)
    return AccountResponse(**row)


@app.get("/accounts/{account_number}/transactions", response_model=list[TransactionResponse])
def get_account_transactions(account_number: str) -> list[TransactionResponse]:
    with get_conn() as conn:
        account = fetch_account_by_number(conn, account_number)
        rows = conn.execute(
            """
            SELECT id, account_id, amount, currency, transaction_type, merchant_name, description, status, created_at
            FROM transactions
            WHERE account_id = %s
            ORDER BY created_at DESC
            """,
            (account["id"],),
        ).fetchall()

    return [TransactionResponse(**dict(row)) for row in rows]


@app.post("/accounts/{account_number}/freeze", response_model=AccountActionResponse)
def freeze_account(account_number: str) -> AccountActionResponse:
    with get_conn() as conn:
        account = fetch_account_by_number(conn, account_number)
        previous_status = account["status"]

        if previous_status == "FROZEN":
            raise HTTPException(status_code=400, detail="Account is already frozen")
        if previous_status == "CLOSED":
            raise HTTPException(status_code=400, detail="Closed account cannot be frozen")

        updated = conn.execute(
            """
            UPDATE accounts
            SET status = 'FROZEN', updated_at = now()
            WHERE id = %s
            RETURNING id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
            """,
            (account["id"],),
        ).fetchone()

        updated_account = dict(updated)
        audit_log_id = write_audit_log(
            conn,
            action="freeze_account",
            resource=f"account:{account_number}",
            before_state={"account_number": account_number, "status": previous_status},
            after_state={"account_number": account_number, "status": updated_account["status"]},
        )

    return AccountActionResponse(
        account_number=account_number,
        previous_status=previous_status,
        new_status=updated_account["status"],
        balance=updated_account["balance"],
        detail="Account frozen",
        audit_log_id=audit_log_id,
    )


@app.post("/accounts/{account_number}/unfreeze", response_model=AccountActionResponse)
def unfreeze_account(account_number: str) -> AccountActionResponse:
    with get_conn() as conn:
        account = fetch_account_by_number(conn, account_number)
        previous_status = account["status"]

        if previous_status == "ACTIVE":
            raise HTTPException(status_code=400, detail="Account is already active")
        if previous_status == "CLOSED":
            raise HTTPException(status_code=400, detail="Closed account cannot be unfrozen")
        if previous_status != "FROZEN":
            raise HTTPException(status_code=400, detail=f"Account status {previous_status} cannot be unfrozen")

        updated = conn.execute(
            """
            UPDATE accounts
            SET status = 'ACTIVE', updated_at = now()
            WHERE id = %s
            RETURNING id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
            """,
            (account["id"],),
        ).fetchone()

        updated_account = dict(updated)
        audit_log_id = write_audit_log(
            conn,
            action="unfreeze_account",
            resource=f"account:{account_number}",
            before_state={"account_number": account_number, "status": previous_status},
            after_state={"account_number": account_number, "status": updated_account["status"]},
        )

    return AccountActionResponse(
        account_number=account_number,
        previous_status=previous_status,
        new_status=updated_account["status"],
        balance=updated_account["balance"],
        detail="Account unfrozen",
        audit_log_id=audit_log_id,
    )


@app.post("/accounts/{account_number}/credit", response_model=CreditResponse)
def credit_account(account_number: str, req: CreditRequest) -> CreditResponse:
    with get_conn() as conn:
        account = fetch_account_by_number(conn, account_number)
        if account["status"] == "CLOSED":
            raise HTTPException(status_code=400, detail="Closed account cannot be credited")

        previous_balance = account["balance"]
        updated = conn.execute(
            """
            UPDATE accounts
            SET balance = balance + %s, updated_at = now()
            WHERE id = %s
            RETURNING id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
            """,
            (req.amount, account["id"]),
        ).fetchone()

        updated_account = dict(updated)
        transaction_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO transactions (id, account_id, amount, currency, transaction_type, merchant_name, description, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                transaction_id,
                account["id"],
                req.amount,
                updated_account["currency"],
                "credit",
                None,
                req.reason,
                "approved",
            ),
        )

        audit_log_id = write_audit_log(
            conn,
            action="credit_account",
            resource=f"account:{account_number}",
            before_state={"account_number": account_number, "balance": str(previous_balance)},
            after_state={"account_number": account_number, "balance": str(updated_account["balance"]), "credited_amount": str(req.amount)},
        )

    return CreditResponse(
        account_number=account_number,
        credited_amount=req.amount,
        previous_balance=previous_balance,
        new_balance=updated_account["balance"],
        transaction_id=transaction_id,
        audit_log_id=audit_log_id,
        detail="Account credited",
    )
