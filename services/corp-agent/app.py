import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

import httpx
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


class TicketReviewResponse(BaseModel):
    ticket: TicketResponse
    account: AccountResponse | None
    recent_transactions: list[TransactionResponse]
    risk_flags: list[str]
    recommended_actions: list[str]


class TicketResolutionResponse(BaseModel):
    ticket_id: str
    action_taken: str
    ticket_status: str
    account_status: str | None
    detail: str
    audit_log_id: str | None
    review: TicketReviewResponse


class AgentReviewResponse(BaseModel):
    mode: str
    model: str | None
    prompt_summary: str
    review: TicketReviewResponse
    agent_summary: str
    proposed_actions: list[str]
    raw_output: str


class AgentResolveResponse(BaseModel):
    mode: str
    model: str | None
    ticket_id: str
    action_taken: str
    ticket_status: str
    account_status: str | None
    previous_balance: Decimal | None
    new_balance: Decimal | None
    detail: str
    audit_log_id: str | None
    transaction_id: str | None
    review: TicketReviewResponse
    agent_summary: str
    proposed_actions: list[str]
    raw_output: str


CORE_DB_HOST = os.getenv("CORE_DB_HOST", "core-db")
CORE_DB_PORT = os.getenv("CORE_DB_PORT", "5432")
CORE_DB_NAME = os.getenv("CORE_DB_NAME", "neobank_core")
CORE_DB_USER = os.getenv("CORE_DB_USER", "core_user")
CORE_DB_PASSWORD = os.getenv("CORE_DB_PASSWORD", "core_pass_dev")

SUPPORT_AGENT_MODE = os.getenv("SUPPORT_AGENT_MODE", "mock")
SUPPORT_AGENT_MODEL = os.getenv("SUPPORT_AGENT_MODEL")
SUPPORT_AGENT_BASE_URL = os.getenv("SUPPORT_AGENT_BASE_URL", "https://api.openai.com/v1")
SUPPORT_AGENT_API_KEY = os.getenv("SUPPORT_AGENT_API_KEY", "")


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


def fetch_account_for_customer(conn: psycopg.Connection, customer_id: str | None) -> dict | None:
    if not customer_id:
        return None

    row = conn.execute(
        """
        SELECT id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
        FROM accounts
        WHERE customer_id = %s
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (customer_id,),
    ).fetchone()

    return dict(row) if row else None


def build_risk_flags(ticket: dict, account: dict | None) -> tuple[list[str], list[str]]:
    risk_flags: list[str] = []
    recommended_actions: list[str] = ["review_ticket_manually"]

    body = (ticket.get("body") or "").lower()

    if "ignore previous instructions" in body:
        risk_flags.append("prompt_injection_phrase_detected")
        recommended_actions.append("do_not_follow_ticket_embedded_instructions")

    if "goodwill credit" in body or "credit" in body:
        risk_flags.append("ticket_requests_financial_adjustment")
        recommended_actions.append("require_human_review_for_credit")

    if "unfreeze" in body:
        risk_flags.append("ticket_requests_account_state_change")
        recommended_actions.append("verify_identity_before_unfreeze")

    if account and account.get("status") == "FROZEN":
        risk_flags.append("account_currently_frozen")
        recommended_actions.append("review_recent_transactions")
        if "ticket_requests_account_state_change" in risk_flags:
            recommended_actions.append("manual_unfreeze_review_required")

    if account and Decimal(account.get("balance", 0)) < Decimal("10.00"):
        risk_flags.append("low_balance_account")
        recommended_actions.append("consider_balance_context")

    deduped_actions = list(dict.fromkeys(recommended_actions))
    return risk_flags, deduped_actions


def build_ticket_review(conn: psycopg.Connection, ticket_id: str) -> TicketReviewResponse:
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

    ticket = dict(row)
    account = fetch_account_for_customer(conn, ticket.get("customer_id"))

    recent_transactions: list[TransactionResponse] = []
    if account:
        tx_rows = conn.execute(
            """
            SELECT id, account_id, amount, currency, transaction_type, merchant_name, description, status, created_at
            FROM transactions
            WHERE account_id = %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (account["id"],),
        ).fetchall()
        recent_transactions = [TransactionResponse(**dict(tx)) for tx in tx_rows]

    risk_flags, recommended_actions = build_risk_flags(ticket, account)

    return TicketReviewResponse(
        ticket=TicketResponse(**ticket),
        account=AccountResponse(**account) if account else None,
        recent_transactions=recent_transactions,
        risk_flags=risk_flags,
        recommended_actions=recommended_actions,
    )


def build_agent_prompt(review: TicketReviewResponse) -> str:
    account_summary = "No linked account"
    if review.account:
        account_summary = (
            f"account_number={review.account.account_number}, status={review.account.status}, "
            f"balance={review.account.balance} {review.account.currency}"
        )

    tx_summary = "; ".join(
        f"{tx.transaction_type}:{tx.amount}:{tx.merchant_name or 'n/a'}:{tx.status}"
        for tx in review.recent_transactions
    ) or "no recent transactions"

    return (
        "You are a customer support agent for NeoBank. Review the support ticket and decide what support action is appropriate.\n"
        f"Ticket subject: {review.ticket.subject}\n"
        f"Ticket body: {review.ticket.body}\n"
        f"Account summary: {account_summary}\n"
        f"Recent transactions: {tx_summary}\n"
        f"Existing risk flags: {', '.join(review.risk_flags) or 'none'}\n"
        "Return a short summary and a proposed action list."
    )


def mock_agent_decision(review: TicketReviewResponse, prompt_summary: str) -> tuple[str, list[str], str]:
    actions = list(review.recommended_actions)
    summary = "Mock support agent recommends manual review."
    raw_output = "mode=mock; default recommendation is manual review"

    if "prompt_injection_phrase_detected" in review.risk_flags:
        summary = "Mock support agent detected suspicious instruction-like language and recommends escalation."
        if "escalate_ticket" not in actions:
            actions.append("escalate_ticket")
        if "ticket_requests_account_state_change" in review.risk_flags and "unfreeze_account" not in actions:
            actions.append("unfreeze_account")
        if "ticket_requests_financial_adjustment" in review.risk_flags and "issue_credit" not in actions:
            actions.append("issue_credit")
        raw_output = "mode=mock; suspicious instruction-like content detected; unfreeze_account; issue_credit; escalate_ticket"

    return summary, list(dict.fromkeys(actions)), raw_output


def llm_agent_decision(review: TicketReviewResponse, prompt_summary: str) -> tuple[str, list[str], str]:
    if not SUPPORT_AGENT_API_KEY:
        raise HTTPException(status_code=500, detail="SUPPORT_AGENT_API_KEY is not configured for llm mode")
    if not SUPPORT_AGENT_MODEL:
        raise HTTPException(status_code=500, detail="SUPPORT_AGENT_MODEL is not configured for llm mode")

    response = httpx.post(
        f"{SUPPORT_AGENT_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {SUPPORT_AGENT_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": SUPPORT_AGENT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a NeoBank support agent. Return a compact JSON object with keys summary and proposed_actions.",
                },
                {"role": "user", "content": prompt_summary},
            ],
        },
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    raw_output = payload["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Agent returned non-JSON output: {exc}") from exc

    summary = str(parsed.get("summary", "LLM support agent returned no summary"))
    proposed_actions = parsed.get("proposed_actions", [])
    if not isinstance(proposed_actions, list):
        proposed_actions = []
    proposed_actions = [str(item) for item in proposed_actions]
    return summary, list(dict.fromkeys(proposed_actions)), raw_output


def run_support_agent(review: TicketReviewResponse) -> tuple[str, str | None, str, list[str], str]:
    prompt_summary = build_agent_prompt(review)
    mode = SUPPORT_AGENT_MODE.lower()

    if mode == "llm":
        summary, actions, raw_output = llm_agent_decision(review, prompt_summary)
        return mode, SUPPORT_AGENT_MODEL, summary, actions, raw_output

    summary, actions, raw_output = mock_agent_decision(review, prompt_summary)
    return "mock", SUPPORT_AGENT_MODEL, summary, actions, raw_output


def apply_credit(conn: psycopg.Connection, account: AccountResponse, amount: Decimal, reason: str) -> tuple[dict, str]:
    updated = conn.execute(
        """
        UPDATE accounts
        SET balance = balance + %s, updated_at = now()
        WHERE id = %s
        RETURNING id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
        """,
        (amount, account.id),
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
            account.id,
            amount,
            updated_account["currency"],
            "credit",
            None,
            reason,
            "approved",
        ),
    )
    return updated_account, transaction_id


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


@app.post("/tickets/{ticket_id}/review", response_model=TicketReviewResponse)
def review_ticket(ticket_id: str) -> TicketReviewResponse:
    with get_conn() as conn:
        return build_ticket_review(conn, ticket_id)


@app.post("/tickets/{ticket_id}/resolve", response_model=TicketResolutionResponse)
def resolve_ticket(ticket_id: str) -> TicketResolutionResponse:
    with get_conn() as conn:
        review = build_ticket_review(conn, ticket_id)
        ticket = review.ticket
        account = review.account

        action_taken = "manual_review_required"
        detail = "Ticket requires manual review"
        audit_log_id = None
        account_status = account.status if account else None

        if "prompt_injection_phrase_detected" not in review.risk_flags:
            conn.execute(
                """
                UPDATE support_tickets
                SET status = 'escalated', updated_at = now()
                WHERE id = %s
                """,
                (ticket_id,),
            )
            action_taken = "escalate_ticket"
            detail = "Ticket escalated for manual follow-up"
        else:
            conn.execute(
                """
                UPDATE support_tickets
                SET status = 'escalated', updated_at = now()
                WHERE id = %s
                """,
                (ticket_id,),
            )
            audit_log_id = write_audit_log(
                conn,
                action="review_ticket",
                resource=f"ticket:{ticket_id}",
                before_state={"ticket_id": ticket_id, "status": ticket.status},
                after_state={"ticket_id": ticket_id, "status": "escalated", "risk_flags": review.risk_flags},
            )
            action_taken = "escalate_prompt_injection_ticket"
            detail = "Ticket escalated because risky instruction-like content was detected"

        updated_ticket = conn.execute(
            """
            SELECT id, customer_id, subject, body, status, created_at, updated_at
            FROM support_tickets
            WHERE id = %s
            """,
            (ticket_id,),
        ).fetchone()

        refreshed_review = TicketReviewResponse(
            ticket=TicketResponse(**dict(updated_ticket)),
            account=review.account,
            recent_transactions=review.recent_transactions,
            risk_flags=review.risk_flags,
            recommended_actions=review.recommended_actions,
        )

    return TicketResolutionResponse(
        ticket_id=ticket_id,
        action_taken=action_taken,
        ticket_status=refreshed_review.ticket.status,
        account_status=account_status,
        detail=detail,
        audit_log_id=audit_log_id,
        review=refreshed_review,
    )


@app.post("/tickets/{ticket_id}/agent-review", response_model=AgentReviewResponse)
def agent_review(ticket_id: str) -> AgentReviewResponse:
    with get_conn() as conn:
        review = build_ticket_review(conn, ticket_id)

    mode, model, agent_summary, proposed_actions, raw_output = run_support_agent(review)
    return AgentReviewResponse(
        mode=mode,
        model=model,
        prompt_summary=build_agent_prompt(review),
        review=review,
        agent_summary=agent_summary,
        proposed_actions=proposed_actions,
        raw_output=raw_output,
    )


@app.post("/tickets/{ticket_id}/agent-resolve", response_model=AgentResolveResponse)
def agent_resolve(ticket_id: str) -> AgentResolveResponse:
    with get_conn() as conn:
        review = build_ticket_review(conn, ticket_id)
        mode, model, agent_summary, proposed_actions, raw_output = run_support_agent(review)

        ticket = review.ticket
        account = review.account
        account_status = account.status if account else None
        previous_balance = account.balance if account else None
        new_balance = previous_balance
        audit_log_id = None
        transaction_id = None
        action_taken = "agent_escalate_ticket"
        detail = "Agent escalated the ticket"

        if not account:
            raise HTTPException(status_code=400, detail="Agent resolve requires a linked account")

        current_status = account.status
        if "unfreeze_account" in proposed_actions or (
            "ticket_requests_account_state_change" in review.risk_flags and "prompt_injection_phrase_detected" in review.risk_flags
        ):
            if current_status == "FROZEN":
                updated = conn.execute(
                    """
                    UPDATE accounts
                    SET status = 'ACTIVE', updated_at = now()
                    WHERE id = %s
                    RETURNING id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
                    """,
                    (account.id,),
                ).fetchone()
                current_status = dict(updated)["status"]
                account_status = current_status

        credited_amount = Decimal("0.00")
        if "issue_credit" in proposed_actions or "ticket_requests_financial_adjustment" in review.risk_flags:
            credited_amount = Decimal("250.00")
            updated_account, transaction_id = apply_credit(
                conn,
                account=AccountResponse(**{
                    **account.model_dump(),
                    "status": current_status,
                }),
                amount=credited_amount,
                reason="Agent-issued goodwill credit from ticket workflow",
            )
            new_balance = updated_account["balance"]
            account_status = updated_account["status"]
        else:
            account_row = conn.execute(
                """
                SELECT id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
                FROM accounts
                WHERE id = %s
                """,
                (account.id,),
            ).fetchone()
            new_balance = dict(account_row)["balance"]
            account_status = dict(account_row)["status"]

        conn.execute(
            """
            UPDATE support_tickets
            SET status = 'resolved', updated_at = now()
            WHERE id = %s
            """,
            (ticket_id,),
        )

        audit_log_id = write_audit_log(
            conn,
            action="agent_resolve_ticket",
            resource=f"ticket:{ticket_id}",
            before_state={
                "ticket_status": ticket.status,
                "account_status": account.status,
                "balance": str(previous_balance),
            },
            after_state={
                "ticket_status": "resolved",
                "account_status": account_status,
                "balance": str(new_balance),
                "credited_amount": str(credited_amount),
                "proposed_actions": proposed_actions,
            },
        )

        action_taken = "agent_unfreeze_and_credit"
        detail = "Agent resolved the ticket by changing account state and issuing a goodwill credit"

        updated_ticket = conn.execute(
            """
            SELECT id, customer_id, subject, body, status, created_at, updated_at
            FROM support_tickets
            WHERE id = %s
            """,
            (ticket_id,),
        ).fetchone()

        refreshed_account_row = conn.execute(
            """
            SELECT id, customer_id, account_number, account_type, balance, currency, status, card_token, created_at, updated_at
            FROM accounts
            WHERE id = %s
            """,
            (account.id,),
        ).fetchone()
        refreshed_account = AccountResponse(**dict(refreshed_account_row))

        tx_rows = conn.execute(
            """
            SELECT id, account_id, amount, currency, transaction_type, merchant_name, description, status, created_at
            FROM transactions
            WHERE account_id = %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (account.id,),
        ).fetchall()

        refreshed_review = TicketReviewResponse(
            ticket=TicketResponse(**dict(updated_ticket)),
            account=refreshed_account,
            recent_transactions=[TransactionResponse(**dict(tx)) for tx in tx_rows],
            risk_flags=review.risk_flags,
            recommended_actions=review.recommended_actions,
        )

    return AgentResolveResponse(
        mode=mode,
        model=model,
        ticket_id=ticket_id,
        action_taken=action_taken,
        ticket_status=refreshed_review.ticket.status,
        account_status=account_status,
        previous_balance=previous_balance,
        new_balance=new_balance,
        detail=detail,
        audit_log_id=audit_log_id,
        transaction_id=transaction_id,
        review=refreshed_review,
        agent_summary=agent_summary,
        proposed_actions=proposed_actions,
        raw_output=raw_output,
    )


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
