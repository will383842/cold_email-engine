"""Email validation endpoint for pre-send list cleaning."""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import verify_api_key
from app.api.schemas import EmailValidationRequest, EmailValidationResponse
from app.services.email_validator import validate_batch

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/validation", tags=["Validation"], dependencies=[Depends(verify_api_key)])


@router.post("/emails", response_model=EmailValidationResponse)
@limiter.limit("10/minute")
async def validate_emails(request: Request, payload: EmailValidationRequest):
    """
    Validate a batch of email addresses before importing to MailWizz.

    Checks: syntax, DNS MX records, blacklisted prefixes, disposable domains.
    Max 10,000 emails per request, rate limited to 10 requests/minute.
    """
    from app.api.routes.metrics import emails_validated

    results = await validate_batch(payload.emails)

    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = len(results) - valid_count

    emails_validated.labels(result="valid").inc(valid_count)
    emails_validated.labels(result="invalid").inc(invalid_count)

    return EmailValidationResponse(
        total=len(results),
        valid=valid_count,
        invalid=invalid_count,
        results=results,
    )
