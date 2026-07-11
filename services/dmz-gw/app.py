import os
from decimal import Decimal

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="NeoBank DMZ Gateway")

CORE_BASE_URL = os.getenv("CORE_BASE_URL", "http://core-svc:8000")


class PublicAuthRequest(BaseModel):
    account_number: str = Field(..., min_length=1)
    merchant: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)


class PublicAuthResponse(BaseModel):
    approved: bool
    reason: str
    account_status: str | None
    card_status: str | None


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth-payment", response_model=PublicAuthResponse)
def auth_payment(req: PublicAuthRequest) -> PublicAuthResponse:
    core_response = httpx.post(
        f"{CORE_BASE_URL}/api/v1/auth-payment",
        json={
            "account_number": req.account_number,
            "merchant": req.merchant,
            "amount": float(req.amount),
        },
        timeout=5.0,
    )
    core_response.raise_for_status()
    return PublicAuthResponse(**core_response.json())
