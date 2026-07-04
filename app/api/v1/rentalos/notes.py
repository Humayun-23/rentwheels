from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status, Response
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import *
from app.schemas.rentalos import *
from .utils import *

router = APIRouter()

@router.post("/bookings/{booking_id}/notes", response_model=RentalBookingNoteResponse, status_code=status.HTTP_201_CREATED)
def create_rental_booking_note(
    booking_id: int,
    note_create: RentalBookingNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add an operational note to an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    note = _require_non_empty_note(note_create.note)
    db_note = RentalBookingNote(
        booking_id=booking.id,
        note=note,
        created_by_user_id=current_user.id,
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


@router.get("/bookings/{booking_id}/notes", response_model=list[RentalBookingNoteResponse])
def list_rental_booking_notes(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notes for an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    return (
        db.query(RentalBookingNote)
        .filter(RentalBookingNote.booking_id == booking.id)
        .order_by(RentalBookingNote.created_at.desc())
        .all()
    )


