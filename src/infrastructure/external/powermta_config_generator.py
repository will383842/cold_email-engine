"""PowerMTA Configuration Generator."""

from typing import List


class PowerMTAConfigGenerator:
    """
    Generates PowerMTA configuration files.

    Creates VirtualMTA pools for multi-tenant IP rotation.
    """

    def generate_vmta_pool(
        self,
        pool_name: str,
        ips: List[dict],
        rotation_mode: str = "weighted",
    ) -> str:
        """
        Generate VirtualMTA pool configuration.

        Args:
            pool_name: Pool name (e.g., "hub-travelers-pool")
            ips: List of IP dicts with keys: address, hostname, vmta_name, weight
            rotation_mode: Rotation mode (weighted, round-robin, least-used)

        Returns:
            PowerMTA config string

        Example:
            config = generator.generate_vmta_pool(
                pool_name="hub-travelers-pool",
                ips=[
                    {"address": "45.123.10.1", "hostname": "mail.hub-travelers.com", "vmta_name": "vmta-hub-travelers", "weight": 100},
                    {"address": "45.123.10.2", "hostname": "mail.emilia-mullerd.com", "vmta_name": "vmta-emilia-mullerd", "weight": 100},
                ],
                rotation_mode="weighted",
            )
        """
        lines = []

        # Pool header
        lines.append(f"# ================================================================")
        lines.append(f"# VirtualMTA Pool: {pool_name}")
        lines.append(f"# Rotation: {rotation_mode}")
        lines.append(f"# Total IPs: {len(ips)}")
        lines.append(f"# ================================================================")
        lines.append("")

        # Create VirtualMTA for each IP
        for ip_data in ips:
            vmta_name = ip_data["vmta_name"]
            address = ip_data["address"]
            hostname = ip_data["hostname"]
            weight = ip_data.get("weight", 100)

            lines.append(f"<VirtualMTA {vmta_name}>")
            lines.append(f"    smtp-source-host {hostname} {address}")
            lines.append(f"    # Weight: {weight}")
            lines.append(f"</VirtualMTA>")
            lines.append("")

        # Create pool
        lines.append(f"<VirtualMTA-Pool {pool_name}>")

        if rotation_mode == "weighted":
            # Weighted rotation
            for ip_data in ips:
                vmta_name = ip_data["vmta_name"]
                weight = ip_data.get("weight", 100)
                if weight > 0:  # Only include active IPs (weight > 0)
                    lines.append(f"    virtual-mta {vmta_name} {weight}")
        elif rotation_mode == "round-robin":
            # Round-robin (equal weight)
            for ip_data in ips:
                vmta_name = ip_data["vmta_name"]
                weight = ip_data.get("weight", 100)
                if weight > 0:
                    lines.append(f"    virtual-mta {vmta_name}")
        else:
            # Default to weighted
            for ip_data in ips:
                vmta_name = ip_data["vmta_name"]
                weight = ip_data.get("weight", 100)
                if weight > 0:
                    lines.append(f"    virtual-mta {vmta_name} {weight}")

        lines.append(f"</VirtualMTA-Pool>")
        lines.append("")

        return "\n".join(lines)

    def generate_full_config(
        self,
        sos_expat_ips: List[dict],
        ulixai_ips: List[dict],
    ) -> str:
        """
        Generate full PowerMTA config for both tenants.

        Args:
            sos_expat_ips: List of SOS-Expat IP dicts
            ulixai_ips: List of Ulixai IP dicts

        Returns:
            Complete PowerMTA config
        """
        lines = []

        # Header
        lines.append("# ================================================================")
        lines.append("# PowerMTA Configuration - Email Engine")
        lines.append("# Multi-Tenant: SOS-Expat + Ulixai")
        lines.append("# Generated automatically")
        lines.append("# ================================================================")
        lines.append("")

        # Global settings
        lines.append("# Global settings")
        lines.append("max-smtp-out 100")
        lines.append("max-msg-rate 1000/h")
        lines.append("bounce-upon-no-mx true")
        lines.append("")

        # Tenant 1 pool
        tenant1_config = self.generate_vmta_pool(
            pool_name="tenant1-pool",
            ips=tenant1_ips,
            rotation_mode="weighted",
        )
        lines.append(tenant1_config)

        # Tenant 2 pool
        tenant2_config = self.generate_vmta_pool(
            pool_name="tenant2-pool",
            ips=tenant2_ips,
            rotation_mode="weighted",
        )
        lines.append(tenant2_config)

        # Domain routing (example)
        lines.append("# ================================================================")
        lines.append("# Domain Routing")
        lines.append("# ================================================================")
        lines.append("")
        lines.append("<domain *>")
        lines.append("    # Default pool: Tenant 1")
        lines.append("    virtual-mta-pool tenant1-pool")
        lines.append("</domain>")
        lines.append("")

        return "\n".join(lines)

    def generate_dkim_config(self, domain: str, selector: str, private_key_path: str) -> str:
        """
        Generate DKIM configuration for a domain.

        Args:
            domain: Domain name (e.g., mail1.sos-mail.com)
            selector: DKIM selector (e.g., "default")
            private_key_path: Path to DKIM private key

        Returns:
            DKIM config string
        """
        lines = []
        lines.append(f"<domain {domain}>")
        lines.append(f"    dkim-sign yes")
        lines.append(f"    dkim-selector {selector}")
        lines.append(f"    dkim-key {private_key_path}")
        lines.append(f"    dkim-identity @{domain}")
        lines.append(f"</domain>")
        return "\n".join(lines)
