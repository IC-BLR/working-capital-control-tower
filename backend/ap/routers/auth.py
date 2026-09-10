from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from ap.store import DEMO_USERS, ACTIVE_TOKENS, make_auth_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LogoutRequest(BaseModel):
    token: str | None = None


def public_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password"}


def get_user_from_header(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Login required.")
    token = authorization.split(" ", 1)[1].strip()
    email = ACTIVE_TOKENS.get(token)
    if not email or email not in DEMO_USERS:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return DEMO_USERS[email]


@router.post("/login")
def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    user = DEMO_USERS.get(email)
    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = make_auth_token(email)
    ACTIVE_TOKENS[token] = email
    return {"token": token, "user": public_user(user)}


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    return {"user": public_user(get_user_from_header(authorization))}


@router.post("/logout")
def logout(payload: LogoutRequest | None = None, authorization: str | None = Header(default=None)):
    token = None
    if payload and payload.token:
        token = payload.token
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token:
        ACTIVE_TOKENS.pop(token, None)
    return {"status": "logged_out"}


@router.get("/demo-users")
def demo_users():
    return [public_user(user) for user in DEMO_USERS.values()]
