"""Tests for MailWizz API client."""

import pytest

from app.services.mailwizz_api_client import MailWizzAPIClient


@pytest.mark.asyncio
async def test_mailwizz_client_not_configured():
    """Test client when API not configured."""
    client = MailWizzAPIClient()
    # Override config to simulate not configured
    client.base_url = None

    assert not client._is_configured()

    result = await client.get_delivery_server(1)
    assert result is None

    result = await client.update_delivery_server_quota(1, daily_quota=1000)
    assert result is False


@pytest.mark.asyncio
async def test_mailwizz_client_configured():
    """Test client when API is configured."""
    client = MailWizzAPIClient()
    # Override config to simulate configured
    client.base_url = "http://mailwizz.local/api"
    client.public_key = "test-public-key"
    client.private_key = "test-private-key"

    assert client._is_configured()

    # Note: Actual API calls will fail in tests without mock
    # In production tests, you'd use httpx_mock or responses library


def test_mailwizz_client_build_headers():
    """Test that headers are properly built."""
    client = MailWizzAPIClient()
    client.base_url = "http://mailwizz.local/api"
    client.public_key = "test-public-key"
    client.private_key = "test-private-key"

    headers = client._build_headers()

    assert "X-MW-PUBLIC-KEY" in headers
    assert headers["X-MW-PUBLIC-KEY"] == "test-public-key"
    assert "X-MW-TIMESTAMP" in headers
    assert "X-MW-SIGNATURE" in headers
    assert headers["Content-Type"] == "application/json"
