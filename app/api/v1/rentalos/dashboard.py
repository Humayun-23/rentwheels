from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status, Response
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import *
from app.schemas.rentalos import *
from .utils import *

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


