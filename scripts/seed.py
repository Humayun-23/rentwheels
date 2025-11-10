"""Seed script for RentWheels - inserts sample data into all tables.

Run with:
    /path/to/venv/bin/python scripts/seed.py

The script is idempotent for known sample emails and will not duplicate entries.
"""
from datetime import timedelta
from app.utils import tz
from sqlalchemy.exc import IntegrityError

from app.db.database import SessionLocal
from app.db import models
from app.utils.utils import hash_password


def create_sample_data():
    db = SessionLocal()
    try:
        # Users
        admin_email = "admin@example.com"
        owner_email = "owner@example.com"
        customer_email = "customer@example.com"

        admin = db.query(models.User).filter(models.User.email == admin_email).first()
        if not admin:
            admin = models.User(
                email=admin_email,
                password=hash_password("adminpass"),
                phone_number="+10000000000",
                user_type="shop_owner",
            )
            # set is_admin if model has attribute
            if hasattr(admin, "is_admin"):
                setattr(admin, "is_admin", True)
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Created admin user id={admin.id}")
        else:
            print(f"Admin user already exists id={admin.id}")

        owner = db.query(models.User).filter(models.User.email == owner_email).first()
        if not owner:
            owner = models.User(
                email=owner_email,
                password=hash_password("ownerpass"),
                phone_number="+19999999999",
                user_type="shop_owner",
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)
            print(f"Created owner user id={owner.id}")
        else:
            print(f"Owner user already exists id={owner.id}")

        customer = db.query(models.User).filter(models.User.email == customer_email).first()
        if not customer:
            customer = models.User(
                email=customer_email,
                password=hash_password("customerpass"),
                phone_number="+12222222222",
                user_type="customer",
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            print(f"Created customer user id={customer.id}")
        else:
            print(f"Customer user already exists id={customer.id}")

        # Shop (owned by owner)
        shop = db.query(models.Shop).filter(models.Shop.owner_id == owner.id).first()
        if not shop:
            shop = models.Shop(
                name="Downtown Rentals",
                description="City center bike and scooty rentals",
                owner_id=owner.id,
                phone_number="+19990001111",
                address="123 Main St",
                city="Metropolis",
                state="State",
                zip_code="12345",
                is_active=True,
            )
            db.add(shop)
            db.commit()
            db.refresh(shop)
            print(f"Created shop id={shop.id}")
        else:
            print(f"Shop already exists id={shop.id}")

        # Bikes / Vehicles
        # Create a few vehicles: scooty 150cc, bike 250cc, car 1200cc
        def get_or_create_bike(name, model, bike_type, engine_cc, price_day):
            b = db.query(models.Bike).filter(models.Bike.name == name, models.Bike.shop_id == shop.id).first()
            if not b:
                b = models.Bike(
                    shop_id=shop.id,
                    name=name,
                    model=model,
                    bike_type=bike_type,
                    engine_cc=engine_cc,
                    description=f"{name} - {model}",
                    price_per_hour=price_day * 10,  # arbitrary
                    price_per_day=price_day,
                    condition="good",
                    is_available=True,
                )
                db.add(b)
                db.commit()
                db.refresh(b)
                print(f"Created vehicle id={b.id} name={b.name} type={b.bike_type} cc={b.engine_cc}")
            else:
                print(f"Vehicle already exists id={b.id} name={b.name}")
            return b

        scooty = get_or_create_bike("Scooty One", "S150", "scooty", 150, 1500)
        bike = get_or_create_bike("Roadster", "R250", "bike", 250, 2500)
        car = get_or_create_bike("CityCar", "C1200", "car", 1200, 8000)

        # Inventory
        def get_or_create_inventory(bike_obj, total_qty):
            inv = db.query(models.BikeInventory).filter(models.BikeInventory.bike_id == bike_obj.id).first()
            if not inv:
                inv = models.BikeInventory(
                    bike_id=bike_obj.id,
                    shop_id=bike_obj.shop_id,
                    total_quantity=total_qty,
                    available_quantity=total_qty,
                    rented_quantity=0,
                )
                db.add(inv)
                db.commit()
                db.refresh(inv)
                print(f"Created inventory id={inv.id} bike_id={inv.bike_id} total={inv.total_quantity}")
            else:
                print(f"Inventory already exists id={inv.id} bike_id={inv.bike_id}")
            return inv

        inv1 = get_or_create_inventory(scooty, 5)
        inv2 = get_or_create_inventory(bike, 3)
        inv3 = get_or_create_inventory(car, 2)

        # Booking by customer for one bike
        # Create a booking with start now, end tomorrow
        existing_booking = db.query(models.Booking).filter(models.Booking.customer_id == customer.id, models.Booking.bike_id == bike.id).first()
        if not existing_booking:
            start = tz.now()
            end = start + timedelta(days=1)
            total_price = bike.price_per_day
            booking = models.Booking(
                customer_id=customer.id,
                bike_id=bike.id,
                start_time=start,
                end_time=end,
                status="confirmed",
                total_price=total_price,
            )
            db.add(booking)
            # decrement inventory available_quantity and increment rented_quantity if inventory exists
            if inv2 and inv2.available_quantity > 0:
                inv2.available_quantity -= 1
                inv2.rented_quantity += 1
                db.add(inv2)
            db.commit()
            db.refresh(booking)
            print(f"Created booking id={booking.id} customer_id={booking.customer_id} bike_id={booking.bike_id}")
        else:
            print(f"Booking already exists id={existing_booking.id}")

        # Summary counts
        users_count = db.query(models.User).count()
        shops_count = db.query(models.Shop).count()
        bikes_count = db.query(models.Bike).count()
        inv_count = db.query(models.BikeInventory).count()
        bookings_count = db.query(models.Booking).count()
        print("Summary:")
        print(f" Users: {users_count}")
        print(f" Shops: {shops_count}")
        print(f" Bikes: {bikes_count}")
        print(f" Inventories: {inv_count}")
        print(f" Bookings: {bookings_count}")

    except IntegrityError as e:
        db.rollback()
        print(f"IntegrityError: {e}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()
