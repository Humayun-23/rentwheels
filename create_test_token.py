import sys
import os
sys.path.append(os.getcwd())
from app.db.database import SessionLocal
from app.db.models import User, Shop
from app.api.v1.oauth2 import create_access_token

db = SessionLocal()

hashed_pwd = "dummy_password"

# Check if test user exists
user = db.query(User).filter(User.email == "test_owner@gopanda.in").first()
if not user:
    user = User(
        email="test_owner@gopanda.in",
        password=hashed_pwd,
        firstname="Test",
        lastname="Owner",
        phone_number="1234567890",
        user_type="shop_owner",
        is_email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

# Check if shop exists
shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
if not shop:
    shop = Shop(
        owner_id=user.id,
        name="GoPanda Test Shop",
        address="123 Test St",
        phone_number="1234567890",
        city="Test City",
        is_active=True,
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)

# Create token
token = create_access_token(data={"user_id": user.id, "role": "user"})
print("---")
print(f"Token: {token}")
print(f"Shop ID: {shop.id}")
print(f"User ID: {user.id}")
print("---")
