"""Simple API Key authentication for internal tool."""

from fastapi import Header, HTTPException, status


def verify_api_key(x_api_key: str = Header(..., description="API Key for internal authentication")):
    """
    Simple API Key authentication for internal tool.

    For internal use only - not production-grade security.
    Production would use JWT, OAuth2, etc.

    Usage:
        Add to endpoint: Depends(verify_api_key)

    Example:
        curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/v2/contacts/1
    """
    # Simple hardcoded API key for internal tool
    # In production, this would be in env vars and hashed in database
    VALID_API_KEYS = [
        "client1-internal-key-2026",
        "client2-internal-key-2026",
        "admin-master-key-2026",
    ]

    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


# Optional: Even simpler version without any auth (for truly internal tools)
def no_auth():
    """No authentication - for internal tools behind firewall."""
    return None
