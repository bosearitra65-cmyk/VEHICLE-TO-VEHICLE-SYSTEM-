from app.api.routes.sync import router as sync_router
from app.api.routes import realtime
from app.api.routes import convoy_intelligence
from app.api.routes import map
from app.api.routes import operational_intelligence
from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.convoys import router as convoys_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.journeys import router as journeys_router
from app.api.routes.routes import router as routes_router
from app.api.routes.route_stops import router as route_stops_router
from app.api.routes.users import router as users_router
from app.api.routes.vehicles import router as vehicle_router
from app.api.routes.vehicle_management import router as vehicle_management_router
from app.api.routes.location import router as location_router
from app.api.routes.route_progress import router as route_progress_router


from app.api.routes.research import router as research_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(sync_router)
api_router.include_router(users_router)
api_router.include_router(vehicle_router)
api_router.include_router(vehicle_management_router)
api_router.include_router(convoys_router)
api_router.include_router(journeys_router)
api_router.include_router(routes_router)
api_router.include_router(route_stops_router)
api_router.include_router(events_router)
api_router.include_router(alerts_router)
api_router.include_router(location_router)
api_router.include_router(route_progress_router)
api_router.include_router(map.router)
api_router.include_router(convoy_intelligence.router)
api_router.include_router(operational_intelligence.router)


api_router.include_router(realtime.router)
api_router.include_router(research_router)
