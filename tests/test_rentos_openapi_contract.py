from app.main import app


def test_rentalos_openapi_route_contract():
    paths = app.openapi()["paths"]
    expected_routes = {
        "/api/v1/rentalos/me": {"get"},
        "/api/v1/rentalos/staff": {"get", "post"},
        "/api/v1/rentalos/staff/{staff_id}": {"patch"},
        "/api/v1/rentalos/bookings": {"get", "post"},
        "/api/v1/rentalos/bookings/{booking_id}": {"get"},
        "/api/v1/rentalos/bookings/{booking_id}/cancel": {"post"},
        "/api/v1/rentalos/bookings/{booking_id}/documents": {"get", "post"},
        "/api/v1/rentalos/bookings/{booking_id}/handover-photo": {"post"},
        "/api/v1/rentalos/bookings/{booking_id}/handover-photos": {"get"},
        "/api/v1/rentalos/bookings/{booking_id}/payments": {"get", "post"},
        "/api/v1/rentalos/bookings/{booking_id}/complete": {"post"},
    }

    for path, methods in expected_routes.items():
        assert path in paths
        assert methods.issubset(paths[path].keys())

    assert not any(path.startswith("/api/v1/rentalos/rentalos") for path in paths)
