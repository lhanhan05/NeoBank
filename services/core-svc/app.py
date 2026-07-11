import os
import uuid
from decimal import Decimal

import httpx
import psycopg
from fastapi import FastAPI
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

app = FastAPI(title="NeoBank Core Service")


class AuthPaymentRequest(BaseModel):
    account_number: str = Field(..., min_length=1)
    merchant: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)


class AuthPaymentResponse(BaseModel):
    approved: bool
    reason: str
    account_status: str | None
    card_status: str | None


CORE_DB_HOST = os.getenv("CORE_DB_HOST", "core-db")
CORE_DB_PORT = os.getenv("CORE_DB_PORT", "5432")
CORE_DB_NAME = os.getenv("CORE_DB_NAME", "neobank_core")
CORE_DB_USER = os.getenv("CORE_DB_USER", "core_user")
CORE_DB_PASSWORD = os.getenv("CORE_DB_PASSWORD", "core_pass_dev")

PCI_AUTH_BASE_URL = os.getenv("PCI_AUTH_BASE_URL", "http://pci-svc:8000")


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


@app.post("/api/v1/auth-payment", response_model=AuthPaymentResponse)
def auth_payment(req: AuthPaymentRequest) -> AuthPaymentResponse:
    with get_conn() as conn:
        account = conn.execute(
            """
            SELECT id, account_number, status, card_token
            FROM accounts
            WHERE account_number = %s
            """,
            (req.account_number,),
        ).fetchone()

        if not account:
            return AuthPaymentResponse(
                approved=False,
                reason="Declined because account was not found",
                account_status=None,
                card_status=None,
            )

        account_status = account["status"]
        if account_status != "ACTIVE":
            return AuthPaymentResponse(
                approved=False,
                reason=f"Declined because account status is {account_status}",
                account_status=account_status,
                card_status=None,
            )

        pci_response = httpx.post(
            f"{PCI_AUTH_BASE_URL}/authorize",
            json={
                "token": account["card_token"],
                "merchant": req.merchant,
                "amount": float(req.amount),
            },
            timeout=5.0,
        )
        pci_response.raise_for_status()
        pci_result = pci_response.json()

        if pci_result["approved"]:
            conn.execute(
                """
                INSERT INTO transactions (id, account_id, amount, currency, transaction_type, merchant_name, description, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    account["id"],
                    req.amount,
                    "USD",
                    "purchase",
                    req.merchant,
                    f"Authorized purchase at {req.merchant}",
                    "approved",
                ),
            )

        return AuthPaymentResponse(
            approved=pci_result["approved"],
            reason=pci_result["reason"],
            account_status=account_status,
            card_status=pci_result.get("card_status"),
        )
