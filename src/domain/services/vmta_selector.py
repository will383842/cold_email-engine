"""VirtualMTA Selector - Select correct VirtualMTA pool for tenant."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models import IP, Tenant


class VMTASelector:
    """
    Select VirtualMTA pool for tenant.

    Each tenant has its own isolated pool of IPs/VMTAs.
    This ensures complete isolation between SOS-Expat and Ulixai.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_pool_name_for_tenant(self, tenant_id: int) -> str:
        """
        Get VirtualMTA pool name for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Pool name derived from tenant slug (e.g., "client-1-pool")

        Example:
            pool = selector.get_pool_name_for_tenant(tenant_id=1)
            # Returns: "{tenant.slug}-pool"
        """
        tenant = self.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Pool name from tenant slug
        return f"{tenant.slug}-pool"

    def get_vmta_config_for_tenant(self, tenant_id: int) -> dict:
        """
        Get complete VirtualMTA configuration for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dict with pool name, IPs, and configuration

        Example:
            config = selector.get_vmta_config_for_tenant(tenant_id=1)
            # {
            #     "pool_name": "client-1-pool",
            #     "total_ips": 5,
            #     "active_ips": 2,
            #     "warming_ips": 3,
            #     "ips": [...],
            #     "delivery_server_host": "localhost",
            #     "delivery_server_port": 25,
            # }
        """
        tenant = self.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Get all IPs for this tenant
        ips = self.db.query(IP).filter_by(tenant_id=tenant_id).all()

        # Count by status
        active_count = sum(1 for ip in ips if ip.status == "active")
        warming_count = sum(1 for ip in ips if ip.status == "warming")

        # Build IP list for config
        ip_configs = []
        for ip in ips:
            ip_configs.append({
                "id": ip.id,
                "address": ip.address,
                "hostname": ip.domain.domain if ip.domain else f"mail{ip.id}.{tenant.sending_domain_base}",
                "vmta_name": f"vmta-{tenant.slug}-{ip.id}",
                "weight": ip.weight,
                "status": ip.status,
            })

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "tenant_slug": tenant.slug,
            "pool_name": f"{tenant.slug}-pool",
            "total_ips": len(ips),
            "active_ips": active_count,
            "warming_ips": warming_count,
            "ips": ip_configs,
            # MailWizz Delivery Server configuration
            "delivery_server_host": "localhost",  # PowerMTA on same server
            "delivery_server_port": 25,
            "delivery_server_protocol": "smtp",
            # Domain configuration
            "brand_domain": tenant.brand_domain,
            "sending_domain_base": tenant.sending_domain_base,
        }

    def get_sending_domain_for_ip(self, ip_id: int) -> Optional[str]:
        """
        Get sending domain for an IP.

        Args:
            ip_id: IP ID

        Returns:
            Domain name or None

        Example:
            domain = selector.get_sending_domain_for_ip(ip_id=1)
            # Returns: "mail1.sos-mail.com"
        """
        ip = self.db.query(IP).filter_by(id=ip_id).first()

        if not ip:
            return None

        if ip.domain:
            return ip.domain.domain

        # Fallback: generate from tenant
        tenant = self.db.query(Tenant).filter_by(id=ip.tenant_id).first()
        if tenant:
            return f"mail{ip.id}.{tenant.sending_domain_base}"

        return None

    def get_mailwizz_delivery_server_config(self, tenant_id: int) -> dict:
        """
        Get MailWizz delivery server configuration.

        This can be used to configure MailWizz to send via PowerMTA.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dict with delivery server configuration for MailWizz

        Example:
            config = selector.get_mailwizz_delivery_server_config(tenant_id=1)

            # Then in MailWizz:
            # 1. Go to Delivery Servers
            # 2. Create "SMTP Server"
            # 3. Use these values:
            #    - Name: config["name"]
            #    - Host: config["host"]
            #    - Port: config["port"]
            #    - Protocol: config["protocol"]
        """
        tenant = self.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        return {
            "name": f"PowerMTA - {tenant.name}",
            "type": "smtp",
            "host": "localhost",  # PowerMTA on same server
            "port": 25,
            "protocol": "smtp",
            "username": "",  # No auth needed for localhost
            "password": "",
            "timeout": 30,
            "from_email": f"no-reply@{tenant.brand_domain}",
            "from_name": tenant.name,
            "force_from": "yes",  # Important: use campaign's from
            "probability": 100,
            "notes": f"Sends via PowerMTA using {tenant.slug}-pool VirtualMTA pool",
        }
