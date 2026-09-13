from httpx import AsyncClient


async def test_trip_search(client: AsyncClient, world):
    origin = world["origin"].id
    dest = world["dest"].id
    day = world["trip"].departure_datetime.date().isoformat()
    response = await client.get(
        "/api/v1/trips",
        params={
            "origin_city_id": str(origin),
            "destination_city_id": str(dest),
            "travel_date": day,
        },
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["available_seats"] == 8


async def test_admin_login_and_dashboard(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@example.com", "password": "secret"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    dash = await client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash.status_code == 200
    assert "trips_today" in dash.json()
