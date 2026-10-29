from fastapi import APIRouter

from app.api.v1 import audit, auth, health, users, visits

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(visits.router)
api_router.include_router(audit.router)
