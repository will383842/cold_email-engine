"""PowerMTA API v2 - Generate PowerMTA configuration."""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IP, Tenant
from src.infrastructure.external import PowerMTAConfigGenerator
from src.domain.services import VMTASelector
from .auth import no_auth

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class VMTAConfigResponse(BaseModel):
    """VirtualMTA configuration for a tenant."""

    tenant_id: int
    tenant_name: str
    pool_name: str
    total_ips: int
    active_ips: int
    warming_ips: int
    ips: list[dict]
    delivery_server_host: str
    delivery_server_port: int


class MailWizzDeliveryServerResponse(BaseModel):
    """MailWizz delivery server configuration."""

    name: str
    type: str
    host: str
    port: int
    protocol: str
    from_email: str
    from_name: str
    notes: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/config/download", response_class=PlainTextResponse, dependencies=[Depends(no_auth)])
def download_powermta_config(
    db: Session = Depends(get_db),
):
    """
    Download complete PowerMTA configuration file.

    Generates VirtualMTA pools for all tenants and returns a ready-to-use
    PowerMTA configuration file.

    Usage:
        curl http://localhost:8000/api/v2/powermta/config/download > /tmp/pmta-config.txt
        sudo cp /tmp/pmta-config.txt /etc/pmta/config
        sudo pmta reload
    """
    try:
        generator = PowerMTAConfigGenerator()

        # Get SOS-Expat IPs
        sos_ips = db.query(IP).filter_by(tenant_id=1).all()
        sos_ip_configs = [
            {
                "address": ip.address,
                "hostname": ip.domain.domain if ip.domain else f"mail{ip.id}.sos-mail.com",
                "vmta_name": f"vmta-sos-expat-{ip.id}",
                "weight": ip.weight,
            }
            for ip in sos_ips
        ]

        # Get Ulixai IPs
        ulixai_ips = db.query(IP).filter_by(tenant_id=2).all()
        ulixai_ip_configs = [
            {
                "address": ip.address,
                "hostname": ip.domain.domain if ip.domain else f"mail{ip.id}.ulixai-mail.com",
                "vmta_name": f"vmta-ulixai-{ip.id}",
                "weight": ip.weight,
            }
            for ip in ulixai_ips
        ]

        # Generate full config
        config = generator.generate_full_config(
            sos_expat_ips=sos_ip_configs,
            ulixai_ips=ulixai_ip_configs,
        )

        return config

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate config: {str(e)}")


@router.get("/config/{tenant_id}", response_class=PlainTextResponse, dependencies=[Depends(no_auth)])
def get_tenant_powermta_config(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """
    Get PowerMTA configuration for a specific tenant.

    Returns VirtualMTA pool configuration for one tenant only.
    """
    try:
        tenant = db.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Get IPs for this tenant
        ips = db.query(IP).filter_by(tenant_id=tenant_id).all()

        if not ips:
            raise HTTPException(status_code=404, detail=f"No IPs found for tenant {tenant_id}")

        ip_configs = [
            {
                "address": ip.address,
                "hostname": ip.domain.domain if ip.domain else f"mail{ip.id}.{tenant.sending_domain_base}",
                "vmta_name": f"vmta-{tenant.slug}-{ip.id}",
                "weight": ip.weight,
            }
            for ip in ips
        ]

        generator = PowerMTAConfigGenerator()
        config = generator.generate_vmta_pool(
            pool_name=f"{tenant.slug}-pool",
            ips=ip_configs,
            rotation_mode="weighted",
        )

        return config

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate config: {str(e)}")


@router.get("/vmta/{tenant_id}", response_model=VMTAConfigResponse, dependencies=[Depends(no_auth)])
def get_vmta_config(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """
    Get VirtualMTA configuration details for a tenant.

    Returns JSON with pool name, IPs, and delivery server settings.
    """
    try:
        selector = VMTASelector(db)
        config = selector.get_vmta_config_for_tenant(tenant_id)

        return VMTAConfigResponse(**config)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get VMTA config: {str(e)}")


@router.get("/mailwizz-delivery-server/{tenant_id}", response_model=MailWizzDeliveryServerResponse, dependencies=[Depends(no_auth)])
def get_mailwizz_delivery_server_config(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """
    Get MailWizz delivery server configuration for a tenant.

    Use this to configure MailWizz to send via PowerMTA.

    Steps to configure MailWizz:
    1. Call this endpoint to get configuration
    2. Login to MailWizz admin
    3. Go to Settings > Delivery Servers
    4. Click "Create new server" > "SMTP Server"
    5. Fill in the values from this response
    6. Save and test
    """
    try:
        selector = VMTASelector(db)
        config = selector.get_mailwizz_delivery_server_config(tenant_id)

        return MailWizzDeliveryServerResponse(**config)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get delivery server config: {str(e)}")


@router.get("/dkim/{domain}", response_class=PlainTextResponse, dependencies=[Depends(no_auth)])
def generate_dkim_config(
    domain: str,
    selector: str = "default",
    key_path: str = "/etc/pmta/dkim/private.key",
    db: Session = Depends(get_db),
):
    """
    Generate DKIM configuration for a domain.

    Args:
        domain: Domain name (e.g., mail1.sos-mail.com)
        selector: DKIM selector (default: "default")
        key_path: Path to DKIM private key (default: /etc/pmta/dkim/private.key)

    Returns:
        DKIM configuration block to add to PowerMTA config

    Example:
        curl "http://localhost:8000/api/v2/powermta/dkim/mail1.sos-mail.com"
    """
    try:
        generator = PowerMTAConfigGenerator()
        config = generator.generate_dkim_config(
            domain=domain,
            selector=selector,
            private_key_path=key_path,
        )

        return config

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DKIM config: {str(e)}")
