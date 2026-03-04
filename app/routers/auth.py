import traceback
import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DB
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: DB):
    try:
        existing = db.table("profiles").select("id").eq("email", body.email).limit(1).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(uuid.uuid4())
        result = db.table("profiles").insert({
            "user_id": user_id,
            "name": body.name or body.email.split("@")[0],
            "email": body.email,
            "password_hash": hash_password(body.password),
            "is_active": True,
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create user")

        user = result.data[0]
        return TokenResponse(
            access_token=create_access_token({"sub": str(user["id"])}),
            refresh_token=create_refresh_token({"sub": str(user["id"])}),
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Register error: {str(e)}")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DB):
    result = db.table("profiles").select("*").eq("email", body.email).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = result.data[0]
    if not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    return TokenResponse(
        access_token=create_access_token({"sub": str(user["id"])}),
        refresh_token=create_refresh_token({"sub": str(user["id"])}),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: DB):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = db.table("profiles").select("*").eq("id", payload["sub"]).limit(1).execute()
    if not result.data or not result.data[0].get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive")

    user = result.data[0]
    return TokenResponse(
        access_token=create_access_token({"sub": str(user["id"])}),
        refresh_token=create_refresh_token({"sub": str(user["id"])}),
    )


@router.post("/logout")
def logout():
    return {"message": "Logged out"}
