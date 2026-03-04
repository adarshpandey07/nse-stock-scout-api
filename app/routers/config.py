from fastapi import APIRouter

from app.dependencies import DB, EditorUser
from app.schemas.config import ConfigOut, ConfigUpdate
from app.services.config_service import get_active_config, update_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config(db: DB, _user: EditorUser):
    return get_active_config(db)


@router.put("", response_model=ConfigOut)
def put_config(body: ConfigUpdate, db: DB, user: EditorUser):
    return update_config(db, body.config_data, user["id"])
