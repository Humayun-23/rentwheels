from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import RentalStaff, Shop, User
from app.schemas.rentalos import (
    RentalOSAccessShop,
    RentalOSMeResponse,
    RentalStaffCreate,
    RentalStaffResponse,
    RentalStaffUpdate,
)
from app.utils.utils import hash_password
from .utils import (
    assert_rentalos_owner_access,
    assert_rentalos_shop_access,
    tz,
    func,
    _validate_staff_role,
    _staff_response,
)


router = APIRouter()

@router.get("/me", response_model=RentalOSMeResponse)
def get_rentalos_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's RentalOS owner/staff access."""
    owned_shops = db.query(Shop).filter(Shop.owner_id == current_user.id).all()
    owned_shop_ids = {shop.id for shop in owned_shops}
    active_staff_memberships = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.shop))
        .filter(
            RentalStaff.user_id == current_user.id,
            RentalStaff.is_active == True,
        )
        .all()
    )

    owned_access = [
        RentalOSAccessShop(
            shop_id=shop.id,
            shop_name=shop.name,
            role="owner",
            staff_id=None,
            is_active=True,
        )
        for shop in owned_shops
    ]
    staff_access = [
        RentalOSAccessShop(
            shop_id=staff.shop_id,
            shop_name=staff.shop.name,
            role=staff.role,
            staff_id=staff.id,
            is_active=staff.is_active,
        )
        for staff in active_staff_memberships
        if staff.shop_id not in owned_shop_ids
    ]

    return RentalOSMeResponse(
        has_rentalos_access=bool(owned_access or staff_access),
        user_id=current_user.id,
        email=current_user.email,
        user_type=current_user.user_type,
        owned_shops=owned_access,
        staff_shops=staff_access,
    )


@router.post("/staff", response_model=RentalStaffResponse, status_code=status.HTTP_201_CREATED)
def create_rental_staff(
    staff_create: RentalStaffCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a staff user or attach an existing user to an owned shop."""
    shop = assert_rentalos_owner_access(db, staff_create.shop_id, current_user)
    role = _validate_staff_role(staff_create.role)
    email = str(staff_create.email).strip().lower()

    staff_user = (
        db.query(User)
        .filter(func.lower(func.trim(User.email)) == email)
        .first()
    )
    if staff_user:
        if staff_user.id == shop.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop owner does not need a staff membership.",
            )
        existing_staff = (
            db.query(RentalStaff)
            .filter(
                RentalStaff.shop_id == shop.id,
                RentalStaff.user_id == staff_user.id,
            )
            .first()
        )
        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already staff for this shop.",
            )
    else:
        if not staff_create.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for new staff user.",
            )
        if len(staff_create.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long.",
            )
        staff_user = User(
            email=email,
            password=hash_password(staff_create.password),
            firstname=staff_create.firstname,
            lastname=staff_create.lastname,
            phone_number=staff_create.phone_number,
            user_type="shop_staff",
            is_email_verified=True,
        )
        db.add(staff_user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email/user conflict.",
            )

    db_staff = RentalStaff(
        shop_id=shop.id,
        user_id=staff_user.id,
        role=role,
        is_active=True,
    )
    db.add(db_staff)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already staff for this shop.",
        )

    db_staff = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.user))
        .filter(RentalStaff.id == db_staff.id)
        .first()
    )
    return _staff_response(db_staff)


@router.get("/staff", response_model=list[RentalStaffResponse])
def list_rental_staff(
    shop_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active and inactive staff for an owned shop."""
    assert_rentalos_owner_access(db, shop_id, current_user)
    staff_rows = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.user))
        .filter(RentalStaff.shop_id == shop_id)
        .order_by(RentalStaff.created_at.desc())
        .all()
    )
    return [_staff_response(staff) for staff in staff_rows]


@router.patch("/staff/{staff_id}", response_model=RentalStaffResponse)
def update_rental_staff(
    staff_id: int,
    staff_update: RentalStaffUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update staff profile details or activate/deactivate a staff membership."""
    staff = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.user))
        .filter(RentalStaff.id == staff_id)
        .first()
    )
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff not found.",
        )

    assert_rentalos_owner_access(db, staff.shop_id, current_user)

    if staff_update.role is not None:
        staff.role = _validate_staff_role(staff_update.role)
    if staff_update.firstname is not None:
        staff.user.firstname = staff_update.firstname
    if staff_update.lastname is not None:
        staff.user.lastname = staff_update.lastname
    if staff_update.phone_number is not None:
        staff.user.phone_number = staff_update.phone_number
    if staff_update.is_active is not None:
        staff.is_active = staff_update.is_active

    staff.updated_at = tz.now()
    staff.user.updated_at = tz.now()
    db.commit()
    db.refresh(staff)
    db.refresh(staff.user)
    return _staff_response(staff)


