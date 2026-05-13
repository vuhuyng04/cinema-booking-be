"""Auth dependencies — verify Clerk JWT and check admin allowlist."""
import os
from typing import Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "")
CLERK_ISSUER = os.environ.get("CLERK_ISSUER", "")
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
}

_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not CLERK_JWKS_URL:
            raise RuntimeError("CLERK_JWKS_URL not configured")
        _jwks_client = PyJWKClient(CLERK_JWKS_URL)
    return _jwks_client


class CurrentUser:
    def __init__(self, user_id: str, email: Optional[str], raw: dict):
        self.user_id = user_id
        self.email = email
        self.raw = raw

    @property
    def is_admin(self) -> bool:
        return bool(self.email) and self.email.lower() in ADMIN_EMAILS


async def get_current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()

    try:
        jwks = _get_jwks_client()
        signing_key = jwks.get_signing_key_from_jwt(token).key
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER if CLERK_ISSUER else None,
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub")

    # Email may be in 'email' claim, or fetch from Clerk API
    email = decoded.get("email") or decoded.get("primary_email_address")
    if not email:
        # Fallback: fetch from Clerk Users API
        secret = os.environ.get("CLERK_SECRET_KEY", "")
        if secret:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(
                        f"https://api.clerk.com/v1/users/{user_id}",
                        headers={"Authorization": f"Bearer {secret}"},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        primary_id = data.get("primary_email_address_id")
                        for ea in data.get("email_addresses", []):
                            if ea.get("id") == primary_id:
                                email = ea.get("email_address")
                                break
            except Exception:
                pass

    return CurrentUser(user_id=user_id, email=email, raw=decoded)


async def get_admin_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
