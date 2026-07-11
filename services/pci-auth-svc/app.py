import os
import uuid
from decimal import Decimal
import psycopg
from fastapi import FastAPI
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

app = FastAPI(title="NeoBank PCI Auth Service")


class AuthorizeRequest(BaseModel):
    token: str = Field(..., min_length=1)
    merchant: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)


class AuthorizeResponse(BaseModel):
    approved: bool
    reason: str
    card_status: str | None


DB_HOST = os.getenv("PCI_DB_HOST", "pci-db")
DB_PORT = os.getenv("PCI_DB_PORT", "5432")
DB_NAME = os.getenv("PCI_DB_NAME", "neobank_pci")
DB_USER = os.getenv("PCI_DB_USER", "pci_user")
DB_PASSWORD = os.getenv("PCI_DB_PASSWORD", "pci_pass_dev")


def get_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )


def decision_for_status(status: str) -> tuple[bool, str]:
    if status == "ACTIVE":
        return True, "Approved"
    if status == "EXPIRED":
        return False, "Declined because card is expired"
    if status == "FROZEN":
        return False, "Declined because card is frozen"
    if status == "LOST":
        return False, "Declined because card is reported lost"
    return False, f"Declined because card status {status} is not supported"


@app.get("/health")
def healthcheck() -> dict[str, str]:
    with get_conn() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/authorize", response_model=AuthorizeResponse)
def authorize(req: AuthorizeRequest) -> AuthorizeResponse:
    with get_conn() as conn:
        card = conn.execute(
            """
            SELECT id, token, status
            FROM cards
            WHERE token = %s
            """,
            (req.token,),
        ).fetchone()

        if not card:
            approved = False
            reason = "Declined because token was not found"
            card_status = None
        else:
            approved, reason = decision_for_status(card["status"])
            card_status = card["status"]

            conn.execute(
                """
                INSERT INTO authorization_log (id, card_id, merchant, amount, approved, reason)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), card["id"], req.merchant, req.amount, approved, reason),
            )

    return AuthorizeResponse(
        approved=approved,
        reason=reason,
        card_status=card_status,
    )
