"""Tests for IP API routes."""


def test_create_ip(client, api_headers):
    resp = client.post(
        "/api/v1/ips",
        json={"address": "1.2.3.4", "hostname": "mail.test.com"},
        headers=api_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["address"] == "1.2.3.4"
    assert data["status"] == "standby"


def test_create_duplicate_ip(client, api_headers):
    client.post(
        "/api/v1/ips",
        json={"address": "1.2.3.4", "hostname": "mail.test.com"},
        headers=api_headers,
    )
    resp = client.post(
        "/api/v1/ips",
        json={"address": "1.2.3.4", "hostname": "mail2.test.com"},
        headers=api_headers,
    )
    assert resp.status_code == 409


def test_list_ips(client, api_headers):
    client.post(
        "/api/v1/ips",
        json={"address": "1.1.1.1", "hostname": "m1.test.com"},
        headers=api_headers,
    )
    client.post(
        "/api/v1/ips",
        json={"address": "2.2.2.2", "hostname": "m2.test.com"},
        headers=api_headers,
    )
    resp = client.get("/api/v1/ips", headers=api_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_ip(client, api_headers):
    create = client.post(
        "/api/v1/ips",
        json={"address": "1.2.3.4", "hostname": "mail.test.com"},
        headers=api_headers,
    )
    ip_id = create.json()["id"]
    resp = client.get(f"/api/v1/ips/{ip_id}", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["address"] == "1.2.3.4"


def test_delete_ip(client, api_headers):
    create = client.post(
        "/api/v1/ips",
        json={"address": "1.2.3.4", "hostname": "mail.test.com"},
        headers=api_headers,
    )
    ip_id = create.json()["id"]
    resp = client.delete(f"/api/v1/ips/{ip_id}", headers=api_headers)
    assert resp.status_code == 204


def test_unauthorized_without_api_key(client):
    resp = client.get("/api/v1/ips")
    assert resp.status_code == 401


def test_health_no_auth_required(client):
    resp = client.get("/health")
    # May return unknown status (no health checks yet) but should not 401
    assert resp.status_code == 200
