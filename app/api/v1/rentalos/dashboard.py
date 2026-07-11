from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import RentalBooking, RentalPayment, User, RentalCustomer
from app.schemas.rentalos import RentalDashboardDetailsResponse, RentalDashboardSummaryResponse
from app.utils import tz
from .utils import (
    assert_rentalos_shop_access,
    OPEN_BOOKING_STATUSES,
    CLOSED_BOOKING_STATUSES,
    _dashboard_day_windows,
    _count_rental_bookings,
    _sum_positive_rental_booking_field,
    _sum_rental_collection_for_window,
)


router = APIRouter()

@router.get("/dashboard/summary", response_model=RentalDashboardSummaryResponse)
def get_dashboard_summary(
    shop_id: int = Query(...),
    timezone_offset_minutes: int = Query(0, ge=-14 * 60, le=14 * 60),
    as_of: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return lightweight RentalOS dashboard KPI totals for one accessible shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    as_of_utc, yesterday_start, today_start, tomorrow_start = _dashboard_day_windows(
        as_of,
        timezone_offset_minutes,
    )

    client_tz = timezone(timedelta(minutes=-timezone_offset_minutes))
    local_now = as_of_utc.astimezone(client_tz)
    this_month_start_local = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if this_month_start_local.month == 1:
        prev_month_start_local = this_month_start_local.replace(year=this_month_start_local.year - 1, month=12)
    else:
        prev_month_start_local = this_month_start_local.replace(month=this_month_start_local.month - 1)

    this_month_start = this_month_start_local.astimezone(timezone.utc)
    prev_month_start = prev_month_start_local.astimezone(timezone.utc)

    shop_filter = RentalBooking.shop_id == shop_id
    active_filter = RentalBooking.status.in_(OPEN_BOOKING_STATUSES)
    not_closed_filter = ~RentalBooking.status.in_(CLOSED_BOOKING_STATUSES)
    not_cancelled_filter = RentalBooking.status != "cancelled"

    active_count = _count_rental_bookings(db, shop_filter, active_filter)
    active_yesterday = _count_rental_bookings(
        db,
        shop_filter,
        active_filter,
        RentalBooking.start_time >= yesterday_start,
        RentalBooking.start_time < today_start,
    )
    due_today_count = _count_rental_bookings(
        db,
        shop_filter,
        not_closed_filter,
        RentalBooking.end_time >= today_start,
        RentalBooking.end_time < tomorrow_start,
    )
    due_yesterday = _count_rental_bookings(
        db,
        shop_filter,
        not_closed_filter,
        RentalBooking.end_time >= yesterday_start,
        RentalBooking.end_time < today_start,
    )
    overdue_count = _count_rental_bookings(
        db,
        shop_filter,
        active_filter,
        RentalBooking.end_time < as_of_utc,
    )
    overdue_before_today = _count_rental_bookings(
        db,
        shop_filter,
        active_filter,
        RentalBooking.end_time < today_start,
    )
    outstanding = _sum_positive_rental_booking_field(
        db,
        RentalBooking.balance_due,
        shop_filter,
        not_cancelled_filter,
    )
    outstanding_yesterday = _sum_positive_rental_booking_field(
        db,
        RentalBooking.balance_due,
        shop_filter,
        not_cancelled_filter,
        RentalBooking.start_time >= yesterday_start,
        RentalBooking.start_time < today_start,
    )
    today_revenue = _sum_rental_collection_for_window(db, shop_id, today_start, tomorrow_start)
    yesterday_revenue = _sum_rental_collection_for_window(db, shop_id, yesterday_start, today_start)

    monthly_booking_count = _count_rental_bookings(
        db,
        shop_filter,
        not_cancelled_filter,
        RentalBooking.created_at >= this_month_start,
        RentalBooking.created_at < tomorrow_start,
    )
    last_month_booking_count = _count_rental_bookings(
        db,
        shop_filter,
        not_cancelled_filter,
        RentalBooking.created_at >= prev_month_start,
        RentalBooking.created_at < this_month_start,
    )

    return RentalDashboardSummaryResponse(
        generated_at=as_of_utc,
        active_count=active_count,
        active_delta=active_count - active_yesterday,
        due_today_count=due_today_count,
        due_today_delta=due_today_count - due_yesterday,
        overdue_count=overdue_count,
        overdue_delta=overdue_count - overdue_before_today,
        outstanding=outstanding,
        outstanding_delta=outstanding - outstanding_yesterday,
        today_revenue=today_revenue,
        revenue_delta=today_revenue - yesterday_revenue,
        monthly_booking_count=monthly_booking_count,
        monthly_booking_delta=monthly_booking_count - last_month_booking_count,
    )


@router.get("/dashboard/details", response_model=RentalDashboardDetailsResponse)
def get_dashboard_details(
    shop_id: int = Query(...),
    timezone_offset_minutes: int = Query(0, ge=-14 * 60, le=14 * 60),
    as_of: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return heavier RentalOS dashboard section lists for one accessible shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    as_of_utc, _, today_start, tomorrow_start = _dashboard_day_windows(
        as_of,
        timezone_offset_minutes,
    )

    shop_filter = RentalBooking.shop_id == shop_id
    active_filter = RentalBooking.status.in_(OPEN_BOOKING_STATUSES)
    not_closed_filter = ~RentalBooking.status.in_(CLOSED_BOOKING_STATUSES)
    not_cancelled_filter = RentalBooking.status != "cancelled"

    active_trips_due_today = (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(shop_filter, active_filter, RentalBooking.end_time < tomorrow_start)
        .all()
    )

    all_active_or_confirmed = (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(shop_filter, RentalBooking.status.in_(["active", "confirmed"]))
        .all()
    )

    timeline_events = []
    for booking in all_active_or_confirmed:
        pickup_time = tz.ensure_aware(booking.start_time) if booking.start_time else None
        drop_time = tz.ensure_aware(booking.end_time) if booking.end_time else None

        # Check if pickup is today
        if pickup_time and pickup_time >= today_start and pickup_time < tomorrow_start:
            timeline_events.append({
                "id": f"{booking.id}-pickup",
                "booking": booking,
                "type": "pickup",
                "time": pickup_time,
                "overdue": False
            })

        # Check if dropoff is today or earlier (overdue)
        # Note: If it's overdue, the dashboard wants it in the timeline too
        if drop_time and drop_time < tomorrow_start:
            is_overdue = drop_time < as_of_utc
            if drop_time >= today_start or is_overdue:
                timeline_events.append({
                    "id": f"{booking.id}-return",
                    "booking": booking,
                    "type": "return",
                    "time": drop_time,
                    "overdue": is_overdue
                })

    # Sort timeline: overdue first, then by time
    timeline_events.sort(key=lambda x: (not x["overdue"], x["time"]))

    flagged_bookings = (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .join(RentalCustomer, RentalBooking.customer_id == RentalCustomer.id)
        .filter(shop_filter, not_closed_filter, RentalCustomer.current_flag_status.isnot(None))
        .all()
    )

    unpaid_bookings = (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(shop_filter, not_cancelled_filter, RentalBooking.balance_due > 0)
        .all()
    )

    return RentalDashboardDetailsResponse(
        active_trips_due_today=active_trips_due_today,
        timeline_events=timeline_events,
        flagged_bookings=flagged_bookings,
        unpaid_bookings=unpaid_bookings,
    )
