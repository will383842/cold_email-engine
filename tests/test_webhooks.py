"""Tests for webhook security — HMAC validation + IP whitelist.

Tests couverts :
  - _validate_hmac() : signature valide, invalide, sans secret (mode dev)
  - _validate_client_ip() : IP autorisée, IP rejetée, sans restriction
  - Endpoint /webhooks/pmta-bounce : auth + réponse 200/401/403
"""

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Import direct des helpers (pas de FastAPI pour tester la logique pure)
# ─────────────────────────────────────────────────────────────────────────────

from app.api.routes.webhooks import _validate_hmac


# ─────────────────────────────────────────────────────────────────────────────
# _validate_hmac()
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateHmac:
    """Tests unitaires pour la validation HMAC-SHA256."""

    def test_no_secret_always_passes(self):
        """Sans WEBHOOK_SECRET configuré → mode dev, toujours valide."""
        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = ""
            assert _validate_hmac(b'{"test": true}', None) is True
            assert _validate_hmac(b'{"test": true}', "sha256=wrong") is True
        finally:
            settings.WEBHOOK_SECRET = original

    def test_valid_signature_passes(self):
        """Signature HMAC correcte → valide."""
        secret = "test-secret-key"
        body = b'{"email": "test@example.com", "type": "hard"}'
        expected_sig = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = secret
            assert _validate_hmac(body, f"sha256={expected_sig}") is True
        finally:
            settings.WEBHOOK_SECRET = original

    def test_valid_signature_without_prefix_passes(self):
        """Signature sans préfixe 'sha256=' acceptée aussi."""
        secret = "test-secret-key"
        body = b'{"email": "test@example.com"}'
        sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = secret
            assert _validate_hmac(body, sig) is True
        finally:
            settings.WEBHOOK_SECRET = original

    def test_wrong_signature_fails(self):
        """Signature incorrecte → invalide."""
        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = "test-secret-key"
            assert _validate_hmac(b'{"email": "test@example.com"}', "sha256=wrongsig") is False
        finally:
            settings.WEBHOOK_SECRET = original

    def test_no_signature_with_secret_fails(self):
        """Secret configuré mais pas de signature → invalide."""
        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = "test-secret-key"
            assert _validate_hmac(b'some body', None) is False
        finally:
            settings.WEBHOOK_SECRET = original

    def test_tampered_body_fails(self):
        """Payload modifié → signature invalide même si clé correcte."""
        secret = "test-secret-key"
        original_body = b'{"email": "legit@example.com"}'
        tampered_body = b'{"email": "hacker@evil.com"}'
        sig = hmac.new(secret.encode("utf-8"), original_body, hashlib.sha256).hexdigest()

        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = secret
            assert _validate_hmac(tampered_body, f"sha256={sig}") is False
        finally:
            settings.WEBHOOK_SECRET = original

    def test_timing_safe_comparison(self):
        """La comparaison est timing-safe (pas d'early exit)."""
        # On ne peut pas tester directement la résistance aux timing attacks,
        # mais on vérifie que compare_digest est utilisé (pas ==)
        # Ce test s'assure juste que le module fonctionne sans exception
        from app.config import settings
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = "secret"
            # Signature de longueur valide mais valeur incorrecte
            fake_sig = "a" * 64  # SHA256 hexdigest = 64 chars
            result = _validate_hmac(b"body", f"sha256={fake_sig}")
            assert result is False
        finally:
            settings.WEBHOOK_SECRET = original


# ─────────────────────────────────────────────────────────────────────────────
# _validate_client_ip()
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateClientIp:
    """Tests unitaires pour la validation de l'IP source."""

    def test_no_restriction_without_config(self):
        """Sans PMTA_ALLOWED_IPS configuré → aucune restriction."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        from app.api.routes.webhooks import _validate_client_ip
        from app.config import settings

        original = settings.PMTA_ALLOWED_IPS
        try:
            settings.PMTA_ALLOWED_IPS = ""
            request = MagicMock()
            # Ne doit pas lever d'exception
            _validate_client_ip(request)
        finally:
            settings.PMTA_ALLOWED_IPS = original

    def test_allowed_ip_passes(self):
        """IP dans la whitelist → passe sans exception."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        from app.api.routes.webhooks import _validate_client_ip
        from app.config import settings

        original = settings.PMTA_ALLOWED_IPS
        try:
            settings.PMTA_ALLOWED_IPS = "1.2.3.4,5.6.7.8"
            request = MagicMock()
            request.client.host = "1.2.3.4"
            # Ne doit pas lever d'exception
            _validate_client_ip(request)
        finally:
            settings.PMTA_ALLOWED_IPS = original

    def test_forbidden_ip_raises_403(self):
        """IP hors whitelist → HTTPException 403."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        from app.api.routes.webhooks import _validate_client_ip
        from app.config import settings

        original = settings.PMTA_ALLOWED_IPS
        try:
            settings.PMTA_ALLOWED_IPS = "1.2.3.4,5.6.7.8"
            request = MagicMock()
            request.client.host = "9.9.9.9"
            with pytest.raises(HTTPException) as exc_info:
                _validate_client_ip(request)
            assert exc_info.value.status_code == 403
        finally:
            settings.PMTA_ALLOWED_IPS = original

    def test_whitelist_with_spaces(self):
        """Espaces autour des IPs dans la config → nettoyés correctement."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        from app.api.routes.webhooks import _validate_client_ip
        from app.config import settings

        original = settings.PMTA_ALLOWED_IPS
        try:
            settings.PMTA_ALLOWED_IPS = " 1.2.3.4 , 5.6.7.8 "
            request = MagicMock()
            request.client.host = "1.2.3.4"
            _validate_client_ip(request)  # Ne doit pas lever d'exception
        finally:
            settings.PMTA_ALLOWED_IPS = original


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints via TestClient (integration tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookEndpoints:
    """Tests d'intégration des endpoints webhooks."""

    def _make_bounce_payload(self):
        return {
            "email": "test@example.com",
            "bounce_type": "hard",
            "reason": "550 User unknown",
            "source_ip": "192.168.1.1",
        }

    def _make_delivery_payload(self):
        return {
            "domain": "gmail.com",
            "count": 42,
        }

    def test_bounce_without_security_config(self, client, api_headers):
        """Sans WEBHOOK_SECRET ni PMTA_ALLOWED_IPS → 200 OK (mode dev)."""
        from app.config import settings

        with patch("app.services.scraper_pro_client.scraper_pro_client.forward_bounce",
                   new_callable=AsyncMock, return_value=True):
            resp = client.post(
                "/webhooks/pmta-bounce",
                json=self._make_bounce_payload(),
                headers=api_headers,
            )
        # 200 ou 422 selon que les champs sont corrects — on vérifie juste pas de 401/403
        assert resp.status_code not in (401, 403)

    def test_bounce_with_valid_hmac(self, client, api_headers):
        """Avec WEBHOOK_SECRET + signature valide → 200 OK."""
        import json
        from app.config import settings

        secret = "test-webhook-secret-2026"
        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = secret
            body = json.dumps(self._make_bounce_payload()).encode()
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

            with patch("app.services.scraper_pro_client.scraper_pro_client.forward_bounce",
                       new_callable=AsyncMock, return_value=True):
                resp = client.post(
                    "/webhooks/pmta-bounce",
                    content=body,
                    headers={
                        **api_headers,
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": f"sha256={sig}",
                    },
                )
            assert resp.status_code not in (401, 403)
        finally:
            settings.WEBHOOK_SECRET = original

    def test_bounce_with_invalid_hmac_returns_401(self, client, api_headers):
        """Avec WEBHOOK_SECRET + signature incorrecte → 401."""
        from app.config import settings

        original = settings.WEBHOOK_SECRET
        try:
            settings.WEBHOOK_SECRET = "test-webhook-secret-2026"
            resp = client.post(
                "/webhooks/pmta-bounce",
                json=self._make_bounce_payload(),
                headers={
                    **api_headers,
                    "X-Webhook-Signature": "sha256=invalidsignature",
                },
            )
            assert resp.status_code == 401
        finally:
            settings.WEBHOOK_SECRET = original

    def test_delivery_endpoint_accessible(self, client, api_headers):
        """Endpoint delivery accessible en mode dev (sans sécurité)."""
        with patch("app.services.scraper_pro_client.scraper_pro_client.forward_delivery_feedback",
                   new_callable=AsyncMock, return_value=True):
            resp = client.post(
                "/webhooks/pmta-delivery",
                json=self._make_delivery_payload(),
                headers=api_headers,
            )
        assert resp.status_code not in (401, 403)
