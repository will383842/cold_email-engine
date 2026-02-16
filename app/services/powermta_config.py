"""Read and write PowerMTA configuration."""

import os
import re
import subprocess
from pathlib import Path

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# Allowed pmta binary paths (whitelist)
_ALLOWED_PMTA_PATHS = {"/usr/sbin/pmta", "/usr/local/sbin/pmta", "/opt/pmta/bin/pmta"}


def _validate_pmta_path(path: str) -> str:
    """Validate that PMTA_BIN_PATH points to a real pmta binary."""
    resolved = str(Path(path).resolve())
    basename = os.path.basename(resolved)
    if basename != "pmta":
        raise ValueError(f"PMTA_BIN_PATH must point to a 'pmta' binary, got: {basename}")
    if resolved not in _ALLOWED_PMTA_PATHS:
        raise ValueError(f"PMTA_BIN_PATH '{resolved}' not in allowed paths: {_ALLOWED_PMTA_PATHS}")
    if not os.path.isfile(resolved):
        raise ValueError(f"PMTA_BIN_PATH '{resolved}' does not exist")
    return resolved


class PowerMTAConfig:
    """Manage /etc/pmta/config reading and writing."""

    def __init__(self, config_path: str | None = None):
        self.config_path = Path(config_path or settings.PMTA_CONFIG_PATH)
        self._pmta_bin = _validate_pmta_path(settings.PMTA_BIN_PATH)

    def read(self) -> str:
        """Return raw config file content."""
        if not self.config_path.exists():
            logger.warning("pmta_config_not_found", path=str(self.config_path))
            return ""
        return self.config_path.read_text()

    def get_vmtas(self) -> list[dict]:
        """Parse VMTA definitions from config."""
        content = self.read()
        vmtas = []
        pattern = re.compile(
            r"<virtual-mta\s+(\S+)>(.*?)</virtual-mta>", re.DOTALL | re.IGNORECASE
        )
        for match in pattern.finditer(content):
            name = match.group(1)
            block = match.group(2)
            ip_match = re.search(r"smtp-source-host\s+(\S+)", block)
            vmtas.append({
                "name": name,
                "ip": ip_match.group(1) if ip_match else None,
            })
        return vmtas

    def get_pools(self) -> list[dict]:
        """Parse VMTA pool definitions from config."""
        content = self.read()
        pools = []
        pattern = re.compile(
            r"<virtual-mta-pool\s+(\S+)>(.*?)</virtual-mta-pool>", re.DOTALL | re.IGNORECASE
        )
        for match in pattern.finditer(content):
            name = match.group(1)
            block = match.group(2)
            members = re.findall(r"virtual-mta\s+(\S+)", block)
            pools.append({"name": name, "vmtas": members})
        return pools

    def add_vmta(self, vmta_name: str, ip_address: str, hostname: str) -> None:
        """Append a new VMTA block to the config file."""
        block = (
            f"\n<virtual-mta {vmta_name}>\n"
            f"    smtp-source-host {ip_address} {hostname}\n"
            f"</virtual-mta>\n"
        )
        with open(self.config_path, "a") as f:
            f.write(block)
        logger.info("pmta_vmta_added", vmta=vmta_name, ip=ip_address)

    def remove_vmta(self, vmta_name: str) -> bool:
        """Remove a VMTA block from config. Returns True if found and removed."""
        content = self.read()
        pattern = re.compile(
            rf"<virtual-mta\s+{re.escape(vmta_name)}>.*?</virtual-mta>\n?",
            re.DOTALL | re.IGNORECASE,
        )
        new_content, count = pattern.subn("", content)
        if count > 0:
            self.config_path.write_text(new_content)
            logger.info("pmta_vmta_removed", vmta=vmta_name)
            return True
        return False

    def reload(self) -> bool:
        """Reload PowerMTA configuration."""
        try:
            result = subprocess.run(
                [self._pmta_bin, "reload"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("pmta_reloaded")
                return True
            logger.error("pmta_reload_failed", stderr=result.stderr)
            return False
        except Exception as exc:
            logger.error("pmta_reload_error", error=str(exc))
            return False

    def is_running(self) -> bool:
        """Check if PowerMTA process is running."""
        try:
            result = subprocess.run(
                [self._pmta_bin, "show", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_queue_size(self) -> int:
        """Get current queue size from PowerMTA."""
        try:
            result = subprocess.run(
                [self._pmta_bin, "show", "topqueues", "--count=999"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return -1
            total = 0
            for line in result.stdout.strip().split("\n")[1:]:  # skip header
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        total += int(parts[1])
                    except ValueError:
                        continue
            return total
        except Exception:
            return -1
