"""In-house email validation: syntax, DNS MX, blacklist prefixes, disposable domains."""

import asyncio
import re
from functools import lru_cache

import dns.resolver
import structlog

logger = structlog.get_logger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

BLACKLISTED_PREFIXES = frozenset({
    "noreply", "no-reply", "no_reply", "donotreply", "do-not-reply",
    "admin", "webmaster", "postmaster", "hostmaster", "abuse",
    "spam", "test", "mailer-daemon", "root", "nobody", "www",
    "info@", "support@", "contact@",
})

DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "trashmail.com",
    "10minutemail.com", "temp-mail.org", "fakeinbox.com", "dispostable.com",
    "mailnesia.com", "maildrop.cc", "getairmail.com", "mohmal.com",
    "burnermail.io", "tempail.com", "getnada.com", "emailondeck.com",
    "guerrillamail.info", "mailcatch.com", "mytemp.email", "tmpmail.net",
    "tmpmail.org", "bupmail.com", "mailtemp.net",
})


@lru_cache(maxsize=4096)
def _check_mx_cached(domain: str) -> bool:
    """Check if domain has MX records (cached to avoid repeated lookups)."""
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5.0)
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return False
    except (dns.resolver.NoAnswer, dns.resolver.Timeout, dns.exception.DNSException):
        # On timeout/transient error, assume valid to avoid false rejections
        return True


def validate_single(email: str) -> tuple[bool, str | None]:
    """
    Validate a single email address.

    Returns:
        (valid, reason) — reason is None if valid, else a short description.
    """
    email = email.strip().lower()

    if not email:
        return False, "empty"

    if not EMAIL_RE.match(email):
        return False, "invalid_syntax"

    local, domain = email.rsplit("@", 1)

    # Check blacklisted prefixes
    if local in BLACKLISTED_PREFIXES:
        return False, "blacklisted_prefix"

    # Check disposable domains
    if domain in DISPOSABLE_DOMAINS:
        return False, "disposable_domain"

    # DNS MX check
    if not _check_mx_cached(domain):
        return False, "no_mx_records"

    return True, None


async def validate_batch(emails: list[str]) -> list[dict]:
    """
    Validate a batch of emails concurrently.

    DNS lookups are done in a thread pool to not block the event loop.
    Returns list of {"email": str, "valid": bool, "reason": str|None}.
    """
    loop = asyncio.get_event_loop()

    async def _validate_one(email: str) -> dict:
        valid, reason = await loop.run_in_executor(None, validate_single, email)
        return {"email": email.strip().lower(), "valid": valid, "reason": reason}

    tasks = [_validate_one(e) for e in emails]
    return await asyncio.gather(*tasks)
