from fastapi.testclient import TestClient

from app.db.models import RentalCustomer


def create_customer(db_session, shop_id: int, phone: str) -> RentalCustomer:
    customer = RentalCustomer(
        shop_id=shop_id,
        phone_number=phone,
        firstname="Directory",
        lastname="Customer",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def test_list_rental_customers_returns_shop_customers(
    client: TestClient,
    db_session,
    owner_shop,
    rental_customer,
    verified_owner,
    auth_headers,
):
    second_customer = create_customer(db_session, owner_shop.id, "5555550101")

    response = client.get(
        f"/api/v1/rentalos/customers?shop_id={owner_shop.id}",
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    customer_ids = {customer["id"] for customer in response.json()}
    assert {rental_customer.id, second_customer.id}.issubset(customer_ids)


def test_list_rental_customers_does_not_leak_other_shop_customers(
    client: TestClient,
    db_session,
    owner_shop,
    other_shop,
    verified_owner,
    auth_headers,
):
    own_customer = create_customer(db_session, owner_shop.id, "5555550102")
    other_customer = create_customer(db_session, other_shop.id, "5555550103")

    response = client.get(
        f"/api/v1/rentalos/customers?shop_id={owner_shop.id}",
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    customer_ids = {customer["id"] for customer in response.json()}
    assert own_customer.id in customer_ids
    assert other_customer.id not in customer_ids
