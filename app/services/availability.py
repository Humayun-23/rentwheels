from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Bike, BikeInventory, Booking, RentalBooking
from app.utils import tz


ONLINE_CONFLICT_STATUSES = {"pending", "paid", "confirmed"}
RENTALOS_CONFLICT_STATUSES = {"draft", "confirmed", "active"}
MAINTENANCE_STATUSES = {"maintenance", "repair", "cleaning"}


@dataclass(frozen=True)
class AvailabilityResult:
    is_available: bool
    reason: str | None = None
    available_count: int = 0
    total_count: int = 0


def overlap_filter(model, start_time: datetime, end_time: datetime):
    return and_(model.start_time < end_time, model.end_time > start_time)


def normalize_time_range(start_time: datetime, end_time: datetime) -> tuple[datetime, datetime]:
    return tz.ensure_aware(start_time), tz.ensure_aware(end_time)


def validate_bike_status(bike: Bike) -> tuple[bool, str | None]:
    if not bike.is_available:
        return False, "Bike is unavailable."
    if bike.maintenance_status in MAINTENANCE_STATUSES:
        return False, "Bike is under maintenance."
    return True, None


def get_bike_for_availability(db: Session, bike_id: int, *, lock: bool = False) -> Bike | None:
    query = db.query(Bike).filter(Bike.id == bike_id)
    if lock:
        query = query.with_for_update()
    return query.first()


def get_inventory_for_availability(db: Session, bike_id: int, *, lock: bool = False) -> BikeInventory | None:
    query = db.query(BikeInventory).filter(BikeInventory.bike_id == bike_id)
    if lock:
        query = query.with_for_update()
    return query.first()


def count_online_conflicts(
    db: Session,
    bike_id: int,
    start_time: datetime,
    end_time: datetime,
    *,
    exclude_booking_id: int | None = None,
) -> int:
    query = db.query(Booking.id).filter(
        Booking.bike_id == bike_id,
        Booking.status.in_(ONLINE_CONFLICT_STATUSES),
        overlap_filter(Booking, start_time, end_time),
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.count()


def count_rentalos_conflicts(
    db: Session,
    bike_id: int,
    start_time: datetime,
    end_time: datetime,
    *,
    exclude_rental_booking_id: int | None = None,
) -> int:
    query = db.query(RentalBooking.id).filter(
        RentalBooking.bike_id == bike_id,
        RentalBooking.status.in_(RENTALOS_CONFLICT_STATUSES),
        overlap_filter(RentalBooking, start_time, end_time),
    )
    if exclude_rental_booking_id is not None:
        query = query.filter(RentalBooking.id != exclude_rental_booking_id)
    return query.count()


def check_bike_availability(
    db: Session,
    bike: Bike,
    start_time: datetime,
    end_time: datetime,
    *,
    inventory: BikeInventory | None = None,
    require_inventory: bool = False,
    exclude_online_booking_id: int | None = None,
    exclude_rental_booking_id: int | None = None,
) -> AvailabilityResult:
    start_time, end_time = normalize_time_range(start_time, end_time)
    status_ok, reason = validate_bike_status(bike)
    total_count = inventory.total_quantity if inventory else 1

    if not status_ok:
        return AvailabilityResult(False, reason, 0, total_count)
    if require_inventory and not inventory:
        return AvailabilityResult(False, "Bike is not available for booking.", 0, 0)
    if total_count <= 0:
        return AvailabilityResult(False, "Bike is not available for booking.", 0, total_count)

    conflict_count = count_online_conflicts(
        db,
        bike.id,
        start_time,
        end_time,
        exclude_booking_id=exclude_online_booking_id,
    ) + count_rentalos_conflicts(
        db,
        bike.id,
        start_time,
        end_time,
        exclude_rental_booking_id=exclude_rental_booking_id,
    )
    available_count = max(total_count - conflict_count, 0)

    if available_count <= 0:
        return AvailabilityResult(
            False,
            "Bike is fully booked for the requested time range.",
            available_count,
            total_count,
        )

    return AvailabilityResult(True, None, available_count, total_count)


def check_bike_availability_by_id(
    db: Session,
    bike_id: int,
    start_time: datetime,
    end_time: datetime,
    *,
    lock: bool = False,
    require_inventory: bool = False,
    exclude_online_booking_id: int | None = None,
    exclude_rental_booking_id: int | None = None,
) -> tuple[Bike | None, BikeInventory | None, AvailabilityResult]:
    bike = get_bike_for_availability(db, bike_id, lock=lock)
    if not bike:
        return None, None, AvailabilityResult(False, "Bike not found.", 0, 0)

    inventory = get_inventory_for_availability(db, bike_id, lock=lock)
    result = check_bike_availability(
        db,
        bike,
        start_time,
        end_time,
        inventory=inventory,
        require_inventory=require_inventory,
        exclude_online_booking_id=exclude_online_booking_id,
        exclude_rental_booking_id=exclude_rental_booking_id,
    )
    return bike, inventory, result
