from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from urllib.parse import urlencode
import secrets
import hmac
import hashlib
import time

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.memory import DomainBlocklist
from app.api.v1.schemas import UserResponse, DEFAULT_BLOCKED_DOMAINS

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Stateless HMAC-signed state — no cookies, no sessions, no DB needed.
#
# Format:  <nonce>.<timestamp>.<hmac-sha256>
#
# The HMAC is computed over "nonce.timestamp" using JWT_SECRET as the key.
# The callback verifies the signature and checks the timestamp is within
# STATE_MAX_AGE_SECONDS (10 min) to prevent replay attacks.
# ---------------------------------------------------------------------------

STATE_MAX_AGE_SECONDS = 600  # 10 minutes


def _state_sig(nonce: str, ts: int) -> str:
    msg = f"{nonce}.{ts}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def _create_state() -> str:
    nonce = secrets.token_urlsafe(16)
    ts = int(time.time())
    sig = _state_sig(nonce, ts)
    return f"{nonce}.{ts}.{sig}"


def _verify_state(state: str) -> bool:
    try:
        parts = state.split(".")
        if len(parts) != 3:
            return False
        nonce, ts_str, provided_sig = parts
        ts = int(ts_str)
        if abs(time.time() - ts) > STATE_MAX_AGE_SECONDS:
            return False
        return hmac.compare_digest(_state_sig(nonce, ts), provided_sig)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/google")
async def google_login():
    """Redirect the browser to Google's OAuth consent screen."""
    state = _create_state()
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=select_account"
    )
    return Response(headers={"Location": auth_url}, status_code=302)


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google's redirect back, exchange code, upsert user, issue JWT."""
    if not _verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    # Exchange authorization code for tokens
    from httpx import AsyncClient

    async with AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")

    access_token_val = token_resp.json().get("access_token")

    # Fetch user info from Google
    async with AsyncClient() as client:
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token_val}"},
        )
    if userinfo_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")

    user_info = userinfo_resp.json()
    google_id = user_info["sub"]
    email = user_info["email"]
    display_name = user_info.get("name")
    avatar_url = user_info.get("picture")

    # Upsert user in DB
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            google_id=google_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.flush()
        for domain in DEFAULT_BLOCKED_DOMAINS:
            db.add(DomainBlocklist(user_id=user.id, domain=domain))
        await db.commit()
        await db.refresh(user)
    else:
        user.display_name = display_name
        user.avatar_url = avatar_url
        user.updated_at = datetime.now(timezone.utc)
        await db.commit()

    # Issue our JWT and redirect to frontend
    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    frontend_url = settings.FRONTEND_URL
    params = urlencode(
        {
            "access_token": jwt_token,
            "user_id": str(user.id),
            "email": email,
            "display_name": display_name or "",
        }
    )
    return Response(
        headers={"Location": f"{frontend_url}/api/auth/callback?{params}"},
        status_code=302,
    )


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        memory_count=user.memory_count,
    )
