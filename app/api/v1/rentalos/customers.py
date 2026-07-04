from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import RentalCustomer, RentalCustomerFlag, User
from app.schemas.rentalos import (
    RentalCustomerCreate,
    RentalCustomerFlagCreate,
    RentalCustomerFlagResponse,
    RentalCustomerOut,
    RentalCustomerSearchResponse,
)
from .utils import (
    assert_rentalos_shop_access,
    get_accessible_rental_customer,
    tz,
    _normalize_optional_email,
    _require_non_empty_note,
    _validate_customer_flag,
    _create_customer_flag,
    _customer_search_response,
)


router = APIRouter()

@router.get("/customers/search", response_model=RentalCustomerSearchResponse)
def search_customer_by_phone(
    shop_id: int = Query(...),
    phone: str = Query(..., min_length=3, max_length=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find a RentalOS customer by exact phone number inside one shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    customer = (
        db.query(RentalCustomer)
        .filter(
            RentalCustomer.shop_id == shop_id,
            RentalCustomer.phone_number == phone,
        )
        .first()
    )
    if not customer:
        return RentalCustomerSearchResponse(found=False, phone_number=phone)
    return _customer_search_response(db, customer, phone)


@router.get("/customers", response_model=list[RentalCustomerOut])
def list_rental_customers(
    shop_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List RentalOS customers scoped to one accessible shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    return (
        db.query(RentalCustomer)
        .filter(RentalCustomer.shop_id == shop_id)
        .order_by(RentalCustomer.created_at.desc())
        .all()
    )


@router.post("/customers", response_model=RentalCustomerOut, status_code=status.HTTP_201_CREATED)
def create_rental_customer(
    customer: RentalCustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a RentalOS customer scoped to one shop."""
    assert_rentalos_shop_access(db, customer.shop_id, current_user)
    existing = (
        db.query(RentalCustomer)
        .filter(
            RentalCustomer.shop_id == customer.shop_id,
            RentalCustomer.phone_number == customer.phone_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already exists for this shop.",
        )

    now = tz.now()
    db_customer = RentalCustomer(
        shop_id=customer.shop_id,
        phone_number=customer.phone_number,
        email=_normalize_optional_email(str(customer.email) if customer.email else None),
        firstname=customer.firstname,
        lastname=customer.lastname,
        document_consent=customer.document_consent,
        document_consent_at=now if customer.document_consent else None,
        marketing_consent=customer.marketing_consent,
        marketing_consent_at=now if customer.marketing_consent else None,
        created_by_user_id=current_user.id,
    )
    db.add(db_customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already exists for this shop.",
        )
    db.refresh(db_customer)
    return db_customer


@router.post("/customers/{customer_id}/flags", response_model=RentalCustomerFlagResponse, status_code=status.HTTP_201_CREATED)
def create_rental_customer_flag(
    customer_id: int,
    flag_create: RentalCustomerFlagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a shop-scoped RentalOS customer flag."""
    customer = get_accessible_rental_customer(db, customer_id, current_user)
    note = _require_non_empty_note(flag_create.note, "A note is required for this customer flag.")
    flag_type, severity = _validate_customer_flag(flag_create.flag_type, flag_create.severity, note)
    db_flag = _create_customer_flag(
        db=db,
        customer=customer,
        flag_type=flag_type,
        severity=severity,
        note=note,
        is_active=flag_create.is_active,
        current_user=current_user,
    )
    db.commit()
    db.refresh(db_flag)
    return db_flag


@router.get("/customers/{customer_id}/flags", response_model=list[RentalCustomerFlagResponse])
def list_rental_customer_flags(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List shop-scoped flags for an accessible RentalOS customer."""
    customer = get_accessible_rental_customer(db, customer_id, current_user)
    return (
        db.query(RentalCustomerFlag)
        .filter(
            RentalCustomerFlag.customer_id == customer.id,
            RentalCustomerFlag.shop_id == customer.shop_id,
        )
        .order_by(RentalCustomerFlag.created_at.desc())
        .all()
    )
