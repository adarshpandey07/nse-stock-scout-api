import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import AdminUser, DB
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(db: DB, _user: AdminUser):
    return db.table("profiles").select("*").order("created_at", desc=True).execute().data


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: DB, _user: AdminUser):
    result = db.table("profiles").select("*").eq("id", str(user_id)).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data[0]


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, db: DB, _user: AdminUser):
    existing = db.table("profiles").select("id").eq("id", str(user_id)).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    if updates:
        result = db.table("profiles").update(updates).eq("id", str(user_id)).execute()
        return result.data[0] if result.data else {}
    return existing.data[0]


@router.delete("/users/{user_id}")
def delete_user(user_id: uuid.UUID, db: DB, admin: AdminUser):
    if str(user_id) == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    existing = db.table("profiles").select("id").eq("id", str(user_id)).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")
    db.table("profiles").delete().eq("id", str(user_id)).execute()
    return {"message": "User deleted"}
