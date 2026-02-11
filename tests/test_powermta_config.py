"""Tests for PowerMTA config parser."""

import tempfile
from pathlib import Path

from app.services.powermta_config import PowerMTAConfig

SAMPLE_CONFIG = """
<virtual-mta vmta-1.2.3.4>
    smtp-source-host 1.2.3.4 mail.example.com
</virtual-mta>

<virtual-mta vmta-5.6.7.8>
    smtp-source-host 5.6.7.8 mail2.example.com
</virtual-mta>

<virtual-mta-pool pool-marketing>
    virtual-mta vmta-1.2.3.4
    virtual-mta vmta-5.6.7.8
</virtual-mta-pool>
"""


def test_get_vmtas():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()
        cfg = PowerMTAConfig(config_path=f.name)
        vmtas = cfg.get_vmtas()
        assert len(vmtas) == 2
        assert vmtas[0]["name"] == "vmta-1.2.3.4"
        assert vmtas[0]["ip"] == "1.2.3.4"
        assert vmtas[1]["name"] == "vmta-5.6.7.8"


def test_get_pools():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()
        cfg = PowerMTAConfig(config_path=f.name)
        pools = cfg.get_pools()
        assert len(pools) == 1
        assert pools[0]["name"] == "pool-marketing"
        assert "vmta-1.2.3.4" in pools[0]["vmtas"]


def test_add_vmta():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()
        cfg = PowerMTAConfig(config_path=f.name)
        cfg.add_vmta("vmta-new", "9.9.9.9", "new.example.com")
        vmtas = cfg.get_vmtas()
        assert len(vmtas) == 3
        names = [v["name"] for v in vmtas]
        assert "vmta-new" in names


def test_remove_vmta():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()
        cfg = PowerMTAConfig(config_path=f.name)
        assert cfg.remove_vmta("vmta-5.6.7.8") is True
        vmtas = cfg.get_vmtas()
        assert len(vmtas) == 1


def test_read_nonexistent():
    cfg = PowerMTAConfig(config_path="/tmp/nonexistent-pmta-config")
    assert cfg.read() == ""
