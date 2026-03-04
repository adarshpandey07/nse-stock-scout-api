from fastapi import APIRouter

from app.dependencies import CurrentUser, DB
from app.services.astro_service import get_commodity_signals, get_planet_positions, get_prediction_accuracy

router = APIRouter(prefix="/astro", tags=["astro"])


@router.get("/signals")
def commodity_signals(db: DB, _user: CurrentUser):
    return get_commodity_signals(db)


@router.get("/planets")
def planet_positions(db: DB, _user: CurrentUser):
    return get_planet_positions(db)


@router.get("/accuracy")
def prediction_accuracy(db: DB, _user: CurrentUser):
    return get_prediction_accuracy(db)
