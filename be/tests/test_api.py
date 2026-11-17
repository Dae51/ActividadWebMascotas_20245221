PASSWORD = "supersecret123"


def register(client, username: str):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "full_name": username.title(),
        },
    )


def headers_for(client, username: str) -> dict:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_pet(client, headers: dict, name: str = "Luna") -> int:
    response = client.post(
        "/pets/",
        json={
            "name": name,
            "species": "dog",
            "breed": "Mestiza",
            "age_years": 3.5,
            "description": "Tranquila",
            "is_for_adoption": True,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def request_adoption(client, headers: dict, pet_id: int) -> int:
    response = client.post(
        "/adoptions/request",
        json={"pet_id": pet_id, "message": "Tengo jardín y experiencia."},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login(client):
    assert register(client, "alex").status_code == 201

    response = client.post(
        "/auth/login",
        json={"username": "alex", "password": PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_duplicate_username_is_rejected(client):
    assert register(client, "alex").status_code == 201

    response = register(client, "alex")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "username_conflict"


def test_short_password_is_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "weak",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_pets_require_authentication(client):
    assert client.get("/pets/mine").status_code == 401
    assert client.get("/pets/1").status_code == 401
    assert (
        client.post("/pets/", json={"name": "Luna", "species": "dog"}).status_code
        == 401
    )


def test_invalid_species_is_rejected(client):
    register(client, "owner")
    owner = headers_for(client, "owner")

    response = client.post(
        "/pets/",
        json={"name": "Luna", "species": "dragon"},
        headers=owner,
    )
    assert response.status_code == 422


def test_update_can_clear_optional_fields(client):
    register(client, "owner")
    owner = headers_for(client, "owner")
    pet_id = create_pet(client, owner)

    cleared = client.patch(
        f"/pets/{pet_id}",
        json={"description": None, "breed": None},
        headers=owner,
    )
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["breed"] is None


def test_update_other_users_pet_is_forbidden(client):
    register(client, "owner")
    register(client, "intruder")
    owner = headers_for(client, "owner")
    intruder = headers_for(client, "intruder")
    pet_id = create_pet(client, owner)

    response = client.patch(
        f"/pets/{pet_id}",
        json={"name": "Robada"},
        headers=intruder,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_pet_owner"


def test_delete_pet(client):
    register(client, "owner")
    owner = headers_for(client, "owner")
    pet_id = create_pet(client, owner)

    assert client.delete(f"/pets/{pet_id}", headers=owner).status_code == 204
    assert client.get(f"/pets/{pet_id}", headers=owner).status_code == 404


def test_cannot_adopt_own_pet(client):
    register(client, "owner")
    owner = headers_for(client, "owner")
    pet_id = create_pet(client, owner)

    response = client.post(
        "/adoptions/request",
        json={"pet_id": pet_id},
        headers=owner,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cannot_adopt_own_pet"


def test_full_adoption_flow(client):
    register(client, "owner")
    register(client, "adopter")
    owner = headers_for(client, "owner")
    adopter = headers_for(client, "adopter")

    pet_id = create_pet(client, owner)

    catalog = client.get("/pets/catalog")
    assert any(pet["id"] == pet_id for pet in catalog.json())

    adoption_id = request_adoption(client, adopter, pet_id)

    received = client.get("/adoptions/received", headers=owner).json()
    assert len(received) == 1
    assert received[0]["status"] == "pending"
    assert received[0]["pet"]["name"] == "Luna"
    assert received[0]["adopter"]["username"] == "adopter"

    approved = client.post(f"/adoptions/{adoption_id}/approve", headers=owner)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    # An approved pet leaves the public catalog.
    assert client.get("/pets/catalog").json() == []

    forbidden = client.post(f"/adoptions/{adoption_id}/complete", headers=adopter)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "not_pet_owner"

    completed = client.post(f"/adoptions/{adoption_id}/complete", headers=owner)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    assert client.get("/pets/mine", headers=owner).json() == []
    adopter_pets = client.get("/pets/mine", headers=adopter).json()
    assert [pet["name"] for pet in adopter_pets] == ["Luna"]

    notifications = client.get("/notifications", headers=adopter).json()
    types = {item["type"] for item in notifications}
    assert {"adoption_approved", "adoption_completed"} <= types


def test_reject_restores_pet_availability(client):
    register(client, "owner")
    register(client, "adopter")
    owner = headers_for(client, "owner")
    adopter = headers_for(client, "adopter")

    pet_id = create_pet(client, owner)
    adoption_id = request_adoption(client, adopter, pet_id)

    assert (
        client.post(f"/adoptions/{adoption_id}/approve", headers=owner).status_code
        == 200
    )
    rejected = client.post(f"/adoptions/{adoption_id}/reject", headers=owner)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    catalog = client.get("/pets/catalog").json()
    assert [pet["id"] for pet in catalog] == [pet_id]

    duplicates = client.post(
        "/adoptions/request",
        json={"pet_id": pet_id},
        headers=adopter,
    )
    assert duplicates.status_code == 201


def test_cannot_complete_pending_adoption(client):
    register(client, "owner")
    register(client, "adopter")
    owner = headers_for(client, "owner")
    adopter = headers_for(client, "adopter")

    pet_id = create_pet(client, owner)
    adoption_id = request_adoption(client, adopter, pet_id)

    response = client.post(f"/adoptions/{adoption_id}/complete", headers=owner)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "adoption_not_approved"


def test_duplicate_adoption_request_is_rejected(client):
    register(client, "owner")
    register(client, "adopter")
    owner = headers_for(client, "owner")
    adopter = headers_for(client, "adopter")

    pet_id = create_pet(client, owner)
    request_adoption(client, adopter, pet_id)

    response = client.post(
        "/adoptions/request",
        json={"pet_id": pet_id},
        headers=adopter,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "adoption_request_exists"


def test_notifications_read_flow(client):
    register(client, "owner")
    register(client, "adopter")
    owner = headers_for(client, "owner")
    adopter = headers_for(client, "adopter")

    pet_id = create_pet(client, owner)
    request_adoption(client, adopter, pet_id)

    owner_notifications = client.get("/notifications", headers=owner).json()
    assert len(owner_notifications) == 1
    assert owner_notifications[0]["is_read"] is False
    assert client.get("/notifications/unread-count", headers=owner).json() == {
        "unread": 1
    }

    notification_id = owner_notifications[0]["id"]
    marked = client.post(f"/notifications/{notification_id}/read", headers=owner)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert client.get("/notifications/unread-count", headers=owner).json() == {
        "unread": 0
    }

    assert (
        client.post(f"/notifications/{notification_id}/read", headers=adopter).status_code
        == 404
    )


def test_ws_ticket_is_not_an_access_token(client):
    register(client, "owner")
    owner = headers_for(client, "owner")

    ticket_response = client.post("/auth/ws-ticket", headers=owner)
    assert ticket_response.status_code == 200
    ticket = ticket_response.json()["ticket"]

    response = client.get(
        "/pets/mine",
        headers={"Authorization": f"Bearer {ticket}"},
    )
    assert response.status_code == 401
