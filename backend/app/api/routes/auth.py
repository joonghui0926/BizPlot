from datetime import datetime, timedelta
from urllib.parse import urlencode
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.base import get_db
from app.models.user import OAuthAccount, User
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, UserOut
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        name=data.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/kakao")
def kakao_login():
    if not settings.KAKAO_REST_API_KEY:
        raise HTTPException(status_code=503, detail="Kakao login is not configured")

    params = {
        "response_type": "code",
        "client_id": settings.KAKAO_REST_API_KEY,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "state": _create_oauth_state("kakao"),
    }
    return RedirectResponse(f"{KAKAO_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/kakao/callback")
def kakao_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect(error=error)
    if not code or not _verify_oauth_state(state, "kakao"):
        return _frontend_redirect(error="invalid_oauth_state")

    try:
        token = _exchange_kakao_token(code)
        profile = _fetch_kakao_profile(token)
        user = _find_or_create_oauth_user(db, profile)
        return _frontend_redirect(token=create_access_token(str(user.id)))
    except Exception:
        return _frontend_redirect(error="kakao_login_failed")


@router.get("/google")
def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured")

    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "state": _create_oauth_state("google"),
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect(error=error)
    if not code or not _verify_oauth_state(state, "google"):
        return _frontend_redirect(error="invalid_oauth_state")

    try:
        token = _exchange_google_token(code)
        profile = _fetch_google_profile(token)
        user = _find_or_create_oauth_user(db, profile)
        return _frontend_redirect(token=create_access_token(str(user.id)))
    except Exception:
        return _frontend_redirect(error="google_login_failed")


def _create_oauth_state(provider: str) -> str:
    payload = {
        "provider": provider,
        "nonce": secrets.token_urlsafe(16),
        "exp": datetime.utcnow() + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _verify_oauth_state(state: str | None, provider: str) -> bool:
    if not state:
        return False
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("provider") == provider
    except JWTError:
        return False


def _exchange_kakao_token(code: str) -> str:
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_REST_API_KEY,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "code": code,
    }
    if settings.KAKAO_CLIENT_SECRET:
        data["client_secret"] = settings.KAKAO_CLIENT_SECRET
    with httpx.Client(timeout=15) as client:
        resp = client.post(KAKAO_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()["access_token"]


def _fetch_kakao_profile(access_token: str) -> dict:
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            KAKAO_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"property_keys": '["kakao_account.email","kakao_account.profile"]'},
        )
        resp.raise_for_status()
        data = resp.json()

    kakao_account = data.get("kakao_account") or {}
    profile = kakao_account.get("profile") or {}
    provider_user_id = str(data["id"])
    return {
        "provider": "kakao",
        "provider_user_id": provider_user_id,
        "email": kakao_account.get("email") or f"kakao_{provider_user_id}@kakao.local",
        "name": profile.get("nickname") or "Kakao User",
    }


def _exchange_google_token(code: str) -> str:
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "code": code,
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()["access_token"]


def _fetch_google_profile(access_token: str) -> dict:
    with httpx.Client(timeout=15) as client:
        resp = client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        data = resp.json()

    provider_user_id = str(data["sub"])
    return {
        "provider": "google",
        "provider_user_id": provider_user_id,
        "email": data.get("email") or f"google_{provider_user_id}@google.local",
        "name": data.get("name") or data.get("email") or "Google User",
    }


def _find_or_create_oauth_user(db: Session, profile: dict) -> User:
    account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == profile["provider"],
            OAuthAccount.provider_user_id == profile["provider_user_id"],
        )
        .first()
    )
    if account:
        return account.user

    user = db.query(User).filter(User.email == profile["email"]).first()
    if not user:
        user = User(
            email=profile["email"],
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            name=profile.get("name"),
        )
        db.add(user)
        db.flush()
    elif profile.get("name") and not user.name:
        user.name = profile["name"]

    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=profile["provider"],
            provider_user_id=profile["provider_user_id"],
            email=profile.get("email"),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        account = (
            db.query(OAuthAccount)
            .filter(
                OAuthAccount.provider == profile["provider"],
                OAuthAccount.provider_user_id == profile["provider_user_id"],
            )
            .first()
        )
        if account:
            return account.user
        raise
    db.refresh(user)
    return user


def _frontend_redirect(token: str | None = None, error: str | None = None) -> RedirectResponse:
    query = {"token": token} if token else {"error": error or "oauth_failed"}
    base = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(f"{base}/auth/callback?{urlencode(query)}")
