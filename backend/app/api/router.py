from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.exercises import router as exercises_router
from app.api.routers.workout_templates import router as workout_templates_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(exercises_router)
api_router.include_router(workout_templates_router)
