"""Single registration point for the active Mizan API surface.

Only domains used by the routed Flutter application belong here.  Future
domains add one feature router here when their backend implementation starts.

API versioning strategy
-----------------------
- All public endpoints live under /api/v1 (set via api_router prefix).
- Individual feature routers use their own domain prefix (e.g. /users, /auth).
- When v2 is introduced, create a new api_router_v2 with prefix="/api/v2"
  and register only the changed routers there, reusing services/repositories.
- Existing v1 clients continue functioning until explicitly deprecated.
"""

from fastapi import APIRouter

from app.core.config import API_V1_PREFIX

from app.api.adhkar import router as adhkar_router
from app.api.badges import router as badges_router
from app.api.charities import router as charities_router
from app.api.dashboard import router as dashboard_router
from app.family.router import router as family_router
from app.api.friday import router as friday_router
from app.books.router import router as books_router
from app.books.bookmark_router import router as book_bookmarks_router
from app.goals.router import router as goals_router
from app.api.leaderboard import router as leaderboard_router
from app.notifications.router import router as notifications_router
from app.quran.router import router as quran_router
from app.api.sadaqah import router as sadaqah_router
from app.sadaqah.router import router as activities_router
from app.api.streak import router as streak_router
from app.api.websocket import router as websocket_router
from app.api.admin_analytics import router as admin_analytics_router
from app.api.admin_books import router as admin_books_router
from app.api.admin_charities import router as admin_charities_router
from app.api.admin_evidence import router as admin_evidence_router
from app.api.admin_leaderboard_seasons import router as admin_leaderboard_seasons_router
from app.journey.router import router as journey_router
from app.users.router import auth_router, router as users_router

api_router = APIRouter(prefix=API_V1_PREFIX)

for router in (
    # Auth & Users
    auth_router,
    users_router,
    # Core features
    adhkar_router,
    badges_router,
    charities_router,
    dashboard_router,
    family_router,
    friday_router,
    books_router,
    book_bookmarks_router,
    leaderboard_router,
    notifications_router,
    quran_router,
    sadaqah_router,
    activities_router,
    streak_router,
    # WebSocket
    websocket_router,
    # Admin
    admin_analytics_router,
    admin_books_router,
    admin_charities_router,
    admin_evidence_router,
    admin_leaderboard_seasons_router,
    journey_router,
    goals_router,
):
    api_router.include_router(router)
