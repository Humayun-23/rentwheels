from datetime import timedelta

from fastapi.testclient import TestClient

from app.db.models import RentalCustomer, RentalPayment
from app.services import rentalos_invoice_email
from app.utils import tz


def configure_smtp(monkeypatch, sent_messages):
    monkeypatch.setattr(rentalos_invoice_email.settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(rentalos_invoice_email.settings, "smtp_port", 587)
    monkeypatch.setattr(rentalos_invoice_email.settings, "smtp_user", "sender@example.com")
    monkeypatch.setattr(rentalos_invoice_email.settings, "smtp_password", "password")
    monkeypatch.setattr(rentalos_invoice_email.settings, "smtp_sender", "billing@gopanda.in")

    def capture_send(host, port, user, password, msg):
        sent_messages.append(
            {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "msg": msg,
            }
        )

    monkeypatch.setattr("app.services.rentalos_invoice_email.send_email_background", capture_send)


def plain_text(msg) -> str:
    if not msg.is_multipart():
        return msg.get_content()
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            return part.get_content()
    return ""


def html_text(msg) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            return part.get_content()
    return ""


def related_image_parts(msg):
    return [part for part in msg.walk() if part.get_content_maintype() == "image"]


def test_create_booking_sends_booking_invoice_email(
    client: TestClient,
    owner_shop,
    owner_bike,
    verified_owner,
    auth_headers,
    db_session,
    monkeypatch,
):
    sent_messages = []
    configure_smtp(monkeypatch, sent_messages)
    now = tz.now()

    response = client.post(
        "/api/v1/rentalos/bookings",
        headers=auth_headers(verified_owner),
        json={
            "shop_id": owner_shop.id,
            "bike_id": owner_bike.id,
            "phone_number": "9000000001",
            "email": "CUSTOMER@EXAMPLE.COM",
            "firstname": "Invoice",
            "lastname": "Customer",
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=2)).isoformat(),
            "total_amount": 2000,
            "advance_paid": 500,
            "balance_due": 1500,
            "security_deposit": 1000,
        },
    )

    assert response.status_code == 201
    customer = db_session.query(RentalCustomer).filter(RentalCustomer.phone_number == "9000000001").one()
    assert customer.email == "customer@example.com"
    assert len(sent_messages) == 1
    msg = sent_messages[0]["msg"]
    assert msg["To"] == "customer@example.com"
    assert "Booking Invoice" in msg["Subject"]
    body = plain_text(msg)
    assert "Advance At Booking" in body
    assert "Balance due: Rs. 1,500" in body
    assert "cid:gopanda-wordmark" in html_text(msg)
    assert related_image_parts(msg)


def test_complete_booking_sends_final_invoice_email_with_payment_ledger(
    client: TestClient,
    rental_booking,
    rental_customer,
    verified_owner,
    auth_headers,
    db_session,
    monkeypatch,
):
    sent_messages = []
    configure_smtp(monkeypatch, sent_messages)
    rental_customer.email = "final@example.com"
    db_session.add(
        RentalPayment(
            booking_id=rental_booking.id,
            payment_type="balance",
            amount=300,
            status="paid",
            method="cash",
            paid_at=tz.now(),
            created_at=tz.now(),
            received_by_user_id=verified_owner.id,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/complete",
        headers=auth_headers(verified_owner),
        json={"note": "Returned safely", "completed_at": tz.now().isoformat()},
    )

    assert response.status_code == 200
    assert len(sent_messages) == 1
    msg = sent_messages[0]["msg"]
    assert msg["To"] == "final@example.com"
    assert "Final Trip Invoice" in msg["Subject"]
    body = plain_text(msg)
    assert "Balance: Rs. 300" in body
    assert "Completed:" in body


def test_invoice_email_skips_when_customer_email_missing(
    client: TestClient,
    owner_shop,
    owner_bike,
    verified_owner,
    auth_headers,
    monkeypatch,
):
    sent_messages = []
    configure_smtp(monkeypatch, sent_messages)
    now = tz.now()

    response = client.post(
        "/api/v1/rentalos/bookings",
        headers=auth_headers(verified_owner),
        json={
            "shop_id": owner_shop.id,
            "bike_id": owner_bike.id,
            "phone_number": "9000000002",
            "start_time": (now + timedelta(days=3)).isoformat(),
            "end_time": (now + timedelta(days=4)).isoformat(),
        },
    )

    assert response.status_code == 201
    assert sent_messages == []


def test_invoice_email_uses_settings_smtp_without_environment(
    rental_booking,
    rental_customer,
    monkeypatch,
):
    sent_messages = []
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    configure_smtp(monkeypatch, sent_messages)
    rental_customer.email = "settings@example.com"

    class FakeBackgroundTasks:
        def add_task(self, func, *args):
            func(*args)

    enqueued = rentalos_invoice_email.enqueue_rentalos_invoice_email(
        FakeBackgroundTasks(),
        rental_booking,
        [],
        "booking_created",
    )

    assert enqueued is True
    assert len(sent_messages) == 1
    assert sent_messages[0]["host"] == "smtp.example.com"
    assert sent_messages[0]["msg"]["To"] == "settings@example.com"
