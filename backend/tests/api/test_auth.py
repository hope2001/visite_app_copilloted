from fastapi.testclient import TestClient

from app.models import User
from tests.conftest import TEST_PASSWORD, AuthHeaders

LOGIN_URL = "/api/v1/auth/login"


def login(client: TestClient, email: str, password: str = TEST_PASSWORD):  # type: ignore[no-untyped-def]
    return client.post(LOGIN_URL, data={"username": email, "password": password})


def test_login_returns_token_usable_on_me(client: TestClient, users: dict[str, User]) -> None:
    response = login(client, "ALICE@acme-corp.com")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {
        "id": str(users["employee"].id),
        "full_name": "Alice Employee",
        "email": "alice@acme-corp.com",
        "role": "EMPLOYEE",
    }


def test_wrong_password_and_unknown_email_are_indistinguishable(
    client: TestClient, users: dict[str, User]
) -> None:
    wrong_password = login(client, "alice@acme-corp.com", "nope")
    unknown_email = login(client, "nobody@acme-corp.com")

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


def test_inactive_user_cannot_login(client: TestClient, users: dict[str, User]) -> None:
    assert login(client, "ivan@acme-corp.com").status_code == 401


def test_inactive_user_token_is_rejected(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers(users["inactive"]))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_INVALID"


def test_repeated_failures_are_rate_limited(client: TestClient, users: dict[str, User]) -> None:
    for _ in range(3):
        assert login(client, "alice@acme-corp.com", "nope").status_code == 401

    blocked = login(client, "alice@acme-corp.com")

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) > 0


def test_missing_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_INVALID"


def test_missing_form_fields_return_validation_error(client: TestClient) -> None:
    response = client.post(LOGIN_URL, data={"username": "a@b.com"})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "password"
