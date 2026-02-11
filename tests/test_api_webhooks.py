"""Tests for webhook routes."""

from unittest.mock import AsyncMock, patch


@patch("app.api.routes.webhooks.scraper_pro_client")
def test_pmta_bounce(mock_client, client, api_headers):
    mock_client.forward_bounce = AsyncMock(return_value=True)
    resp = client.post(
        "/api/v1/webhooks/pmta-bounce",
        json={
            "email": "bounce@example.com",
            "bounce_type": "hard",
            "reason": "user unknown",
            "source_ip": "1.2.3.4",
        },
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True
    assert data["email"] == "bounce@example.com"


@patch("app.api.routes.webhooks.scraper_pro_client")
def test_pmta_bounce_forward_fail(mock_client, client, api_headers):
    mock_client.forward_bounce = AsyncMock(return_value=False)
    resp = client.post(
        "/api/v1/webhooks/pmta-bounce",
        json={"email": "bounce@example.com", "bounce_type": "soft"},
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["forwarded_to_scraper_pro"] is False
