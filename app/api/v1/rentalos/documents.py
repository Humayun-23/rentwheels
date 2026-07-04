from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status, Response
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import *
from app.schemas.rentalos import *
from .utils import *

router = APIRouter()

@router.post(
    "/bookings/{booking_id}/documents",
    response_model=RentalBookingDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_rental_booking_document(
    booking_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload DL/ID proof for a RentalOS booking into private Cloudflare R2 storage."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_type must be driving_license or id_proof.",
        )

    content = validate_rentalos_upload(file, DOCUMENT_CONTENT_TYPES, _max_rentalos_upload_bytes())
    blob_name = build_rentalos_blob_name(booking.shop_id, booking.id, "documents", file.content_type)
    upload = upload_rentalos_blob(blob_name, content, file.content_type)

    db_document = RentalBookingDocument(
        booking_id=booking.id,
        document_type=document_type,
        file_url=upload.blob_url,
        file_name=file.filename,
        content_type=file.content_type,
        uploaded_by_user_id=current_user.id,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    resp = RentalBookingDocumentResponse.model_validate(db_document)
    if resp.file_url:
        resp.file_url = generate_rentalos_presigned_url(resp.file_url)
    return resp


@router.get("/bookings/{booking_id}/documents", response_model=list[RentalBookingDocumentResponse])
def list_rental_booking_documents(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List uploaded DL/ID proof metadata for an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    docs = (
        db.query(RentalBookingDocument)
        .filter(RentalBookingDocument.booking_id == booking.id)
        .order_by(RentalBookingDocument.created_at.desc())
        .all()
    )
    responses = []
    for doc in docs:
        resp = RentalBookingDocumentResponse.model_validate(doc)
        if resp.file_url:
            resp.file_url = generate_rentalos_presigned_url(resp.file_url)
        responses.append(resp)
    return responses


@router.post(
    "/bookings/{booking_id}/handover-photo",
    response_model=RentalHandoverPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_rental_handover_photo(
    booking_id: int,
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy_meters: int | None = Form(None),
    location_address: str | None = Form(None),
    location_permission_granted: bool = Form(False),
    captured_at: datetime | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload customer-with-vehicle handover photo into private Cloudflare R2 storage."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="latitude must be between -90 and 90.",
        )
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="longitude must be between -180 and 180.",
        )

    content = validate_rentalos_upload(file, HANDOVER_PHOTO_CONTENT_TYPES, _max_rentalos_upload_bytes())
    blob_name = build_rentalos_blob_name(booking.shop_id, booking.id, "handover", file.content_type)
    upload = upload_rentalos_blob(blob_name, content, file.content_type)

    db_photo = RentalHandoverPhoto(
        booking_id=booking.id,
        image_url=upload.blob_url,
        latitude=latitude,
        longitude=longitude,
        location_accuracy_meters=location_accuracy_meters,
        location_address=location_address,
        location_permission_granted=location_permission_granted,
        captured_at=captured_at,
        uploaded_by_user_id=current_user.id,
    )
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    
    resp = RentalHandoverPhotoResponse.model_validate(db_photo)
    if resp.image_url:
        resp.image_url = generate_rentalos_presigned_url(resp.image_url)
    return resp


@router.get("/bookings/{booking_id}/handover-photos", response_model=list[RentalHandoverPhotoResponse])
def list_rental_handover_photos(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List handover photo metadata for an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    photos = (
        db.query(RentalHandoverPhoto)
        .filter(RentalHandoverPhoto.booking_id == booking.id)
        .order_by(RentalHandoverPhoto.created_at.desc())
        .all()
    )
    responses = []
    for photo in photos:
        resp = RentalHandoverPhotoResponse.model_validate(photo)
        if resp.image_url:
            resp.image_url = generate_rentalos_presigned_url(resp.image_url)
        responses.append(resp)
    return responses


