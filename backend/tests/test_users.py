from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_inventory import role_headers

from app.db.models import User

pytestmark = pytest.mark.integration


def add_user(
    client, headers, email="new@example.com", role="STAFF", password="initial-password-123"
):
    response = client.post(
        "/api/v1/users", headers=headers, json={"email": email, "role": role, "password": password}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("role", ["STAFF", "VIEWER"])
def test_only_admin_can_manage_accounts(catalog_client, role):
    headers = role_headers(catalog_client, role)
    assert catalog_client.get("/api/v1/users", headers=headers).status_code == 403
    assert (
        catalog_client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "another@example.com",
                "password": "initial-password-123",
                "role": "VIEWER",
            },
        ).status_code
        == 403
    )
    assert catalog_client.get("/api/v1/audit", headers=headers).status_code == 403


def test_create_account_and_safe_response(catalog_client, admin_headers):
    account = add_user(catalog_client, admin_headers, email="New@Example.COM")
    assert account["email"] == "new@example.com"
    assert account["role"] == "STAFF"
    assert not {"password", "password_hash", "auth_version"}.intersection(account)
    duplicate = catalog_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "new@example.com",
            "password": "initial-password-123",
            "role": "VIEWER",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    result = catalog_client.get(
        "/api/v1/users?search=new&page_size=1", headers=admin_headers
    ).json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == account["id"]


def test_password_reset_and_disable_revoke_existing_tokens(catalog_client, admin_headers):
    account = add_user(catalog_client, admin_headers)
    first = catalog_client.post(
        "/api/v1/auth/login",
        json={
            "email": account["email"],
            "password": "initial-password-123",
        },
    ).json()
    old_headers = {"Authorization": "Bearer " + first["access_token"]}
    response = catalog_client.patch(
        f"/api/v1/users/{account['id']}",
        headers=admin_headers,
        json={"password": "replacement-password-123"},
    )
    assert response.status_code == 200
    assert catalog_client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    assert (
        catalog_client.post(
            "/api/v1/auth/login",
            json={
                "email": account["email"],
                "password": "initial-password-123",
            },
        ).status_code
        == 401
    )
    login = catalog_client.post(
        "/api/v1/auth/login",
        json={
            "email": account["email"],
            "password": "replacement-password-123",
        },
    )
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert (
        catalog_client.patch(
            f"/api/v1/users/{account['id']}", headers=admin_headers, json={"is_active": False}
        ).status_code
        == 200
    )
    assert catalog_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        catalog_client.patch(
            f"/api/v1/users/{account['id']}", headers=admin_headers, json={"is_active": True}
        ).status_code
        == 200
    )
    assert catalog_client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_role_change_revokes_old_privileges(catalog_client, admin_headers):
    staff_headers = role_headers(catalog_client, "STAFF")
    staff = catalog_client.get("/api/v1/auth/me", headers=staff_headers).json()
    assert (
        catalog_client.patch(
            f"/api/v1/users/{staff['id']}", headers=admin_headers, json={"role": "VIEWER"}
        ).status_code
        == 200
    )
    assert catalog_client.get("/api/v1/auth/me", headers=staff_headers).status_code == 401
    new_headers = role_headers(catalog_client, "STAFF")
    assert catalog_client.get("/api/v1/auth/me", headers=new_headers).json()["role"] == "VIEWER"


def test_last_admin_cannot_be_removed(catalog_client, admin_headers):
    current = catalog_client.get("/api/v1/auth/me", headers=admin_headers).json()
    for payload in ({"is_active": False}, {"role": "STAFF"}):
        result = catalog_client.patch(
            f"/api/v1/users/{current['id']}", headers=admin_headers, json=payload
        )
        assert result.status_code == 409
        assert result.json()["error"]["code"] == "LAST_ADMIN"


def test_concurrent_admin_changes_keep_one_active_admin(catalog_client, admin_headers, catalog_db):
    second = add_user(catalog_client, admin_headers, email="second-admin@example.com", role="ADMIN")
    second_login = catalog_client.post(
        "/api/v1/auth/login",
        json={
            "email": second["email"],
            "password": "initial-password-123",
        },
    ).json()
    second_headers = {"Authorization": "Bearer " + second_login["access_token"]}
    first = catalog_client.get("/api/v1/auth/me", headers=admin_headers).json()

    def disable(args):
        headers, target = args
        return catalog_client.patch(
            f"/api/v1/users/{target}", headers=headers, json={"is_active": False}
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(disable, [(admin_headers, second["id"]), (second_headers, first["id"])])
        )
    assert sum(result.status_code == 200 for result in results) == 1
    assert all(result.status_code in {200, 401, 403, 409} for result in results)
    with Session(catalog_db) as session:
        remaining = session.scalars(
            select(User).where(User.role == "ADMIN", User.is_active.is_(True))
        ).all()
        assert len(remaining) == 1


def test_user_cannot_escalate_by_changing_own_password(catalog_client):
    headers = role_headers(catalog_client, "VIEWER")
    result = catalog_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "test-password-123",
            "new_password": "new-personal-password-123",
        },
    )
    assert result.status_code == 200
    assert catalog_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    new_login = catalog_client.post(
        "/api/v1/auth/login",
        json={
            "email": "viewer@example.com",
            "password": "new-personal-password-123",
        },
    )
    new_headers = {"Authorization": "Bearer " + new_login.json()["access_token"]}
    assert catalog_client.get("/api/v1/auth/me", headers=new_headers).json()["role"] == "VIEWER"
    assert catalog_client.get("/api/v1/users", headers=new_headers).status_code == 403


def test_change_password_requires_current_and_new_password(catalog_client, admin_headers):
    for current, new, status in [
        ("wrong-password", "replacement-password-123", 400),
        ("test-password-123", "test-password-123", 422),
        ("test-password-123", "short", 422),
    ]:
        response = catalog_client.post(
            "/api/v1/auth/change-password",
            headers=admin_headers,
            json={
                "current_password": current,
                "new_password": new,
            },
        )
        assert response.status_code == status
    assert catalog_client.get("/api/v1/auth/me", headers=admin_headers).status_code == 200


def test_no_public_registration_and_patch_validation(catalog_client, admin_headers):
    current = catalog_client.get("/api/v1/auth/me", headers=admin_headers).json()
    assert catalog_client.post("/api/v1/auth/register").status_code == 404
    assert catalog_client.get("/api/v1/users").status_code == 401
    for payload in (
        {"role": None},
        {"is_active": None},
        {"password": None},
        {"role": "OWNER"},
        {"is_active": "false"},
        {"email": "new@example.com"},
    ):
        response = catalog_client.patch(
            f"/api/v1/users/{current['id']}", headers=admin_headers, json=payload
        )
        assert response.status_code == 422
    assert UUID(current["id"])
