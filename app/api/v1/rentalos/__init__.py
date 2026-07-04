from fastapi import APIRouter
from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .catalog import router as catalog_router
from .customers import router as customers_router
from .bookings import router as bookings_router
from .documents import router as documents_router
from .payments import router as payments_router
from .notes import router as notes_router

router = APIRouter(prefix="/rentalos", tags=["rentalos"])
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(catalog_router)
router.include_router(customers_router)
router.include_router(bookings_router)
router.include_router(documents_router)
router.include_router(payments_router)
router.include_router(notes_router)
