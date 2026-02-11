"""Tests for health monitor."""

from unittest.mock import patch

import pytest

from app.models import HealthCheck
from app.services.health_monitor import HealthMonitor


@pytest.mark.asyncio
@patch.object(HealthMonitor, "check_pmta", return_value=True)
@patch.object(HealthMonitor, "check_disk", return_value=42.5)
@patch.object(HealthMonitor, "check_ram", return_value=55.0)
@patch.object(HealthMonitor, "check_queue", return_value=100)
async def test_run_health_check(mock_q, mock_ram, mock_disk, mock_pmta, db):
    monitor = HealthMonitor(db)
    check = await monitor.run_health_check()
    assert check.pmta_running is True
    assert check.disk_usage_pct == 42.5
    assert check.ram_usage_pct == 55.0
    assert check.pmta_queue_size == 100


def test_get_status_summary_no_checks(db):
    monitor = HealthMonitor(db)
    summary = monitor.get_status_summary()
    assert summary["status"] == "unknown"


@pytest.mark.asyncio
@patch.object(HealthMonitor, "check_pmta", return_value=True)
@patch.object(HealthMonitor, "check_disk", return_value=42.0)
@patch.object(HealthMonitor, "check_ram", return_value=50.0)
@patch.object(HealthMonitor, "check_queue", return_value=10)
async def test_status_summary_healthy(mock_q, mock_ram, mock_disk, mock_pmta, db):
    monitor = HealthMonitor(db)
    await monitor.run_health_check()
    summary = monitor.get_status_summary()
    assert summary["status"] == "healthy"
    assert summary["issues"] == []


@pytest.mark.asyncio
@patch.object(HealthMonitor, "check_pmta", return_value=False)
@patch.object(HealthMonitor, "check_disk", return_value=90.0)
@patch.object(HealthMonitor, "check_ram", return_value=50.0)
@patch.object(HealthMonitor, "check_queue", return_value=10)
async def test_status_summary_degraded(mock_q, mock_ram, mock_disk, mock_pmta, db):
    monitor = HealthMonitor(db)
    await monitor.run_health_check()
    summary = monitor.get_status_summary()
    assert summary["status"] == "degraded"
    assert "PowerMTA down" in summary["issues"]
