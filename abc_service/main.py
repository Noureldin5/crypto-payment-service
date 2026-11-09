"""Mock "ABC" service: owns client personal data.

In real life this would be a CRM / KYC service owned by another team.
Our payment service calls it over HTTP to get client data.
"""
import os

from fastapi import FastAPI, Header, HTTPException

API_KEY = os.getenv("ABC_API_KEY", "abc-secret")

CLIENTS = {
    "1": {"id": "1", "full_name": "Aibek Toktogulov", "email": "aibek@example.com", "status": "ACTIVE"},
    "2": {"id": "2", "full_name": "Aliya Sadykova", "email": "aliya@example.com", "status": "ACTIVE"},
    "3": {"id": "3", "full_name": "Blocked User", "email": "blocked@example.com", "status": "BLOCKED"},
    # client 4 exists in ABC but has NO wallet -> WALLET_NOT_FOUND
    "4": {"id": "4", "full_name": "No Wallet", "email": "nowallet@example.com", "status": "ACTIVE"},
}

app = FastAPI(title="ABC Client Data Service (mock)")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/clients/{client_id}")
def get_client(client_id: str, x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    client = CLIENTS.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
