import json
import os
from datetime import datetime
from decimal import Decimal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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


class AccountNoteResponse(BaseModel):
    id: str
    account_id: str
    author: str
    note: str
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
    account_notes: list[AccountNoteResponse]
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


CORE_SERVICE_BASE_URL = os.getenv("CORE_SERVICE_BASE_URL", "http://core-svc:8000")
SUPPORT_AGENT_MODE = os.getenv("SUPPORT_AGENT_MODE", "mock")
SUPPORT_AGENT_MODEL = os.getenv("SUPPORT_AGENT_MODEL")
SUPPORT_AGENT_BASE_URL = os.getenv("SUPPORT_AGENT_BASE_URL", "https://api.openai.com/v1")
SUPPORT_AGENT_API_KEY = os.getenv("SUPPORT_AGENT_API_KEY", "")


def core_get(path: str):
    response = httpx.get(f"{CORE_SERVICE_BASE_URL}{path}", timeout=10.0)
    if response.status_code >= 400:
        detail = response.json().get("detail", response.text)
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


def core_post(path: str, payload: dict | None = None):
    response = httpx.post(f"{CORE_SERVICE_BASE_URL}{path}", json=payload, timeout=15.0)
    if response.status_code >= 400:
        detail = response.json().get("detail", response.text)
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


def build_agent_prompt(review: TicketReviewResponse) -> str:
    account_summary = "No linked account"
    if review.account:
        account_summary = (
            f"account_number={review.account.account_number}, status={review.account.status}, "
            f"balance={review.account.balance} {review.account.currency}"
        )

    note_summary = "; ".join(
        f"{note.author}:{note.note}" for note in review.account_notes
    ) or "no account notes"

    tx_summary = "; ".join(
        f"{tx.transaction_type}:{tx.amount}:{tx.merchant_name or 'n/a'}:{tx.status}"
        for tx in review.recent_transactions
    ) or "no recent transactions"

    return (
        "You are a customer support agent for NeoBank. Review the support ticket and decide what support action is appropriate.\n"
        f"Ticket subject: {review.ticket.subject}\n"
        f"Ticket body: {review.ticket.body}\n"
        f"Account summary: {account_summary}\n"
        f"Account notes: {note_summary}\n"
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


@app.get("/health")
def healthcheck() -> dict[str, str]:
    core_get("/health")
    return {"status": "ok"}


@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets() -> list[TicketResponse]:
    data = core_get("/internal/tickets")
    return [TicketResponse(**row) for row in data]


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str) -> TicketResponse:
    data = core_get(f"/internal/tickets/{ticket_id}")
    return TicketResponse(**data)


@app.post("/tickets/{ticket_id}/review", response_model=TicketReviewResponse)
def review_ticket(ticket_id: str) -> TicketReviewResponse:
    data = core_post(f"/internal/tickets/{ticket_id}/review")
    return TicketReviewResponse(**data)


@app.post("/tickets/{ticket_id}/resolve", response_model=TicketResolutionResponse)
def resolve_ticket(ticket_id: str) -> TicketResolutionResponse:
    data = core_post(f"/internal/tickets/{ticket_id}/resolve")
    return TicketResolutionResponse(**data)


@app.post("/tickets/{ticket_id}/agent-review", response_model=AgentReviewResponse)
def agent_review(ticket_id: str) -> AgentReviewResponse:
    review = TicketReviewResponse(**core_post(f"/internal/tickets/{ticket_id}/review"))
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
    review = TicketReviewResponse(**core_post(f"/internal/tickets/{ticket_id}/review"))
    mode, model, agent_summary, proposed_actions, raw_output = run_support_agent(review)

    if not review.account:
        raise HTTPException(status_code=400, detail="Agent resolve requires a linked account")

    account_status = review.account.status
    previous_balance = review.account.balance
    new_balance = previous_balance
    transaction_id = None

    if "unfreeze_account" in proposed_actions or (
        "ticket_requests_account_state_change" in review.risk_flags and "prompt_injection_phrase_detected" in review.risk_flags
    ):
        if review.account.status == "FROZEN":
            unfreeze_result = core_post(f"/internal/accounts/{review.account.account_number}/unfreeze")
            account_status = unfreeze_result["new_status"]
        else:
            account_status = review.account.status

    if "issue_credit" in proposed_actions or "ticket_requests_financial_adjustment" in review.risk_flags:
        credit_result = core_post(
            f"/internal/accounts/{review.account.account_number}/credit",
            {"amount": "250.00", "reason": "Agent-issued goodwill credit from ticket workflow"},
        )
        new_balance = Decimal(credit_result["new_balance"])
        transaction_id = credit_result["transaction_id"]

    resolved = TicketResolutionResponse(**core_post(f"/internal/tickets/{ticket_id}/agent-resolve"))
    refreshed_review = TicketReviewResponse(**core_post(f"/internal/tickets/{ticket_id}/review"))

    return AgentResolveResponse(
        mode=mode,
        model=model,
        ticket_id=ticket_id,
        action_taken="agent_unfreeze_and_credit",
        ticket_status=resolved.ticket_status,
        account_status=account_status,
        previous_balance=previous_balance,
        new_balance=new_balance,
        detail="Agent resolved the ticket by changing account state and issuing a goodwill credit",
        audit_log_id=resolved.audit_log_id,
        transaction_id=transaction_id,
        review=refreshed_review,
        agent_summary=agent_summary,
        proposed_actions=proposed_actions,
        raw_output=raw_output,
    )


@app.get("/accounts/{account_number}", response_model=AccountResponse)
def get_account(account_number: str) -> AccountResponse:
    data = core_get(f"/internal/accounts/{account_number}")
    return AccountResponse(**data)


@app.get("/accounts/{account_number}/transactions", response_model=list[TransactionResponse])
def get_account_transactions(account_number: str) -> list[TransactionResponse]:
    data = core_get(f"/internal/accounts/{account_number}/transactions")
    return [TransactionResponse(**row) for row in data]


@app.get("/accounts/{account_number}/notes", response_model=list[AccountNoteResponse])
def get_account_notes(account_number: str) -> list[AccountNoteResponse]:
    data = core_get(f"/internal/accounts/{account_number}/notes")
    return [AccountNoteResponse(**row) for row in data]


@app.post("/accounts/{account_number}/freeze", response_model=AccountActionResponse)
def freeze_account(account_number: str) -> AccountActionResponse:
    data = core_post(f"/internal/accounts/{account_number}/freeze")
    return AccountActionResponse(**data)


@app.post("/accounts/{account_number}/unfreeze", response_model=AccountActionResponse)
def unfreeze_account(account_number: str) -> AccountActionResponse:
    data = core_post(f"/internal/accounts/{account_number}/unfreeze")
    return AccountActionResponse(**data)


@app.post("/accounts/{account_number}/credit", response_model=CreditResponse)
def credit_account(account_number: str, req: CreditRequest) -> CreditResponse:
    data = core_post(
        f"/internal/accounts/{account_number}/credit",
        {"amount": str(req.amount), "reason": req.reason},
    )
    return CreditResponse(**data)
