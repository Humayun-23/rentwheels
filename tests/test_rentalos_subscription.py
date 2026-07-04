from fastapi.testclient import TestClient
import pytest
from app.db.models import Shop

def test_rentalos_subscription_paywall(client: TestClient, db_session, verified_owner, auth_headers):
    # Create a shop with an inactive subscription
    inactive_shop = Shop(
        name="Inactive Shop",
        owner_id=verified_owner.id,
        phone_number="3333333333",
        address="123 Inactive St",
        city="City",
        rentalos_subscription_status="inactive"
    )
    db_session.add(inactive_shop)
    db_session.commit()
    db_session.refresh(inactive_shop)

    # Owner accesses their own shop catalog -> 402 Payment Required
    headers = auth_headers(verified_owner)
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={inactive_shop.id}", headers=headers)
    assert response.status_code == 402
    assert response.json()["detail"] == "rentalos_subscription_required"

    # Now make the shop active
    inactive_shop.rentalos_subscription_status = "active"
    db_session.commit()

    # Owner accesses their own shop catalog -> 200 OK
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={inactive_shop.id}", headers=headers)
    assert response.status_code == 200

def test_rentalos_me_includes_subscription_status(client: TestClient, db_session, verified_owner, auth_headers):
    # Create an inactive shop
    inactive_shop = Shop(
        name="Inactive Shop",
        owner_id=verified_owner.id,
        phone_number="3333333333",
        address="123 Inactive St",
        city="City",
        rentalos_subscription_status="inactive"
    )
    db_session.add(inactive_shop)
    db_session.commit()

    headers = auth_headers(verified_owner)
    response = client.get("/api/v1/rentalos/me", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["has_rentalos_access"] is True
    
    shop_info = next((s for s in data["owned_shops"] if s["shop_id"] == inactive_shop.id), None)
    assert shop_info is not None
    assert shop_info["subscription_status"] == "inactive"
