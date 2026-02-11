"""DNS record validation: SPF, DKIM, DMARC, PTR, MX."""

from datetime import datetime

import dns.resolver
import structlog
from sqlalchemy.orm import Session

from app.models import Domain, IP

logger = structlog.get_logger(__name__)


class DNSValidator:
    """Validate DNS records for domains and IPs."""

    def __init__(self, db: Session):
        self.db = db
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 10
        self.resolver.lifetime = 10

    def check_spf(self, domain_name: str, expected_ip: str | None = None) -> bool:
        """Check if domain has valid SPF record, optionally including an IP."""
        try:
            answers = self.resolver.resolve(domain_name, "TXT")
            for rdata in answers:
                txt = rdata.to_text().strip('"')
                if txt.startswith("v=spf1"):
                    if expected_ip and f"ip4:{expected_ip}" not in txt and "+all" not in txt:
                        logger.warning("spf_missing_ip", domain=domain_name, ip=expected_ip)
                        return False
                    return True
            return False
        except Exception as exc:
            logger.debug("spf_check_failed", domain=domain_name, error=str(exc))
            return False

    def check_dkim(self, domain_name: str, selector: str = "default") -> bool:
        """Check if DKIM record exists for selector._domainkey.domain."""
        try:
            qname = f"{selector}._domainkey.{domain_name}"
            answers = self.resolver.resolve(qname, "TXT")
            for rdata in answers:
                txt = rdata.to_text().strip('"')
                if "v=DKIM1" in txt or "p=" in txt:
                    return True
            return False
        except Exception as exc:
            logger.debug("dkim_check_failed", domain=domain_name, selector=selector, error=str(exc))
            return False

    def check_dmarc(self, domain_name: str) -> bool:
        """Check if domain has a DMARC record."""
        try:
            qname = f"_dmarc.{domain_name}"
            answers = self.resolver.resolve(qname, "TXT")
            for rdata in answers:
                txt = rdata.to_text().strip('"')
                if txt.startswith("v=DMARC1"):
                    return True
            return False
        except Exception as exc:
            logger.debug("dmarc_check_failed", domain=domain_name, error=str(exc))
            return False

    def check_ptr(self, ip_address: str, expected_hostname: str | None = None) -> bool:
        """Check reverse DNS (PTR) for an IP address."""
        try:
            octets = ip_address.split(".")
            arpa = ".".join(reversed(octets)) + ".in-addr.arpa"
            answers = self.resolver.resolve(arpa, "PTR")
            for rdata in answers:
                ptr = str(rdata).rstrip(".")
                if expected_hostname and ptr != expected_hostname:
                    logger.warning(
                        "ptr_mismatch", ip=ip_address, got=ptr, expected=expected_hostname
                    )
                    return False
                return True
            return False
        except Exception as exc:
            logger.debug("ptr_check_failed", ip=ip_address, error=str(exc))
            return False

    def check_mx(self, domain_name: str) -> bool:
        """Check if domain has MX records."""
        try:
            answers = self.resolver.resolve(domain_name, "MX")
            return len(answers) > 0
        except Exception as exc:
            logger.debug("mx_check_failed", domain=domain_name, error=str(exc))
            return False

    def validate_domain(self, domain: Domain) -> dict[str, bool]:
        """Run all DNS checks for a domain and update the DB."""
        ip_address = None
        hostname = None
        if domain.ip:
            ip_address = domain.ip.address
            hostname = domain.ip.hostname

        results = {
            "spf": self.check_spf(domain.name, ip_address),
            "dkim": self.check_dkim(domain.name, domain.dkim_selector or "default"),
            "dmarc": self.check_dmarc(domain.name),
            "ptr": self.check_ptr(ip_address, hostname) if ip_address else False,
            "mx": self.check_mx(domain.name),
        }

        domain.spf_valid = results["spf"]
        domain.dkim_valid = results["dkim"]
        domain.dmarc_valid = results["dmarc"]
        domain.ptr_valid = results["ptr"]
        domain.last_dns_check = datetime.utcnow()
        self.db.commit()

        logger.info("dns_validation_complete", domain=domain.name, results=results)
        return results

    def validate_all(self) -> dict[str, dict[str, bool]]:
        """Validate DNS for all domains."""
        domains = self.db.query(Domain).all()
        all_results = {}
        for domain in domains:
            all_results[domain.name] = self.validate_domain(domain)
        return all_results
