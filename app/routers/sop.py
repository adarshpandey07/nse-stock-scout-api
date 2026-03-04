from fastapi import APIRouter, HTTPException

from app.dependencies import DB, CurrentUser, EditorUser
from app.schemas.sop import SopCreate, SopOut, SopUpdate

router = APIRouter(prefix="/sop", tags=["sop"])


@router.get("", response_model=list[SopOut])
def list_sops(db: DB, _user: CurrentUser):
    return db.table("sop_docs").select("*").order("updated_at", desc=True).execute().data


@router.get("/{slug}", response_model=SopOut)
def get_sop(slug: str, db: DB, _user: CurrentUser):
    result = db.table("sop_docs").select("*").eq("slug", slug).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="SOP not found")
    return result.data[0]


@router.post("", response_model=SopOut, status_code=201)
def create_sop(body: SopCreate, db: DB, user: EditorUser):
    existing = db.table("sop_docs").select("id").eq("slug", body.slug).limit(1).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Slug already exists")
    result = db.table("sop_docs").insert({
        "slug": body.slug,
        "title": body.title,
        "content_md": body.content_md,
        "updated_by": user["id"],
    }).execute()
    return result.data[0] if result.data else {}


@router.put("/{slug}", response_model=SopOut)
def update_sop(slug: str, body: SopUpdate, db: DB, user: EditorUser):
    existing = db.table("sop_docs").select("id").eq("slug", slug).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="SOP not found")
    updates = {"updated_by": user["id"]}
    if body.title is not None:
        updates["title"] = body.title
    if body.content_md is not None:
        updates["content_md"] = body.content_md
    result = db.table("sop_docs").update(updates).eq("slug", slug).execute()
    return result.data[0] if result.data else {}


@router.delete("/{slug}")
def delete_sop(slug: str, db: DB, _user: EditorUser):
    existing = db.table("sop_docs").select("id").eq("slug", slug).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="SOP not found")
    db.table("sop_docs").delete().eq("slug", slug).execute()
    return {"message": "SOP deleted"}
