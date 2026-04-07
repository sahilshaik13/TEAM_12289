from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authlib.integrations.starlette_client import OAuth
from datetime import datetime, timezone
from urllib.parse import urlencode
import secrets

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.memory import DomainBlocklist
from app.api.v1.schemas import TokenResponse, UserResponse, DEFAULT_BLOCKED_DOMAINS

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_login(request: Request):
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
        f"&nonce={nonce}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    response = Response(headers={"Location": auth_url}, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid or missing state parameter")

    token_url = "https://oauth2.googleapis.com/token"
    from httpx import AsyncClient
    async with AsyncClient() as client:
        token_resp = await client.post(
            token_url,
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

    tokens = token_resp.json()
    access_token_val = tokens.get("access_token")
    id_token_val = tokens.get("id_token")

    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    async with AsyncClient() as client:
        userinfo_resp = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token_val}"},
        )

    if userinfo_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")

    user_info = userinfo_resp.json()
    google_id = user_info["sub"]
    email = user_info["email"]
    display_name = user_info.get("name")
    avatar_url = user_info.get("picture")

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

    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    frontend_url = "https://echomemory-frontend-161866545382.asia-south1.run.app"
    params = urlencode({
        "access_token": jwt_token,
        "user_id": str(user.id),
        "email": email,
        "display_name": display_name or "",
    })
    response = Response(
        headers={"Location": f"{frontend_url}/api/auth/callback?{params}"},
        status_code=302,
    )
    response.delete_cookie("oauth_state", path="/")
    return response


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
