"""Prometheus metrics endpoint."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)

router = APIRouter(tags=["Metrics"])

# Custom registry to avoid default Python metrics clutter
REGISTRY = CollectorRegistry()

# Gauges
ips_active = Gauge("email_engine_ips_active", "Number of active IPs", registry=REGISTRY)
ips_warming = Gauge("email_engine_ips_warming", "Number of IPs in warmup", registry=REGISTRY)
ips_blacklisted = Gauge(
    "email_engine_ips_blacklisted", "Number of blacklisted IPs", registry=REGISTRY
)
pmta_running = Gauge("email_engine_pmta_running", "PowerMTA running (1/0)", registry=REGISTRY)
pmta_queue_size = Gauge("email_engine_pmta_queue_size", "PowerMTA queue size", registry=REGISTRY)
disk_usage = Gauge("email_engine_disk_usage_pct", "Disk usage percentage", registry=REGISTRY)
ram_usage = Gauge("email_engine_ram_usage_pct", "RAM usage percentage", registry=REGISTRY)

# Counters
bounces_received = Counter(
    "email_engine_bounces_received_total", "Total bounces received", registry=REGISTRY
)
bounces_forwarded = Counter(
    "email_engine_bounces_forwarded_total", "Total bounces forwarded to scraper-pro",
    registry=REGISTRY,
)
blacklist_checks = Counter(
    "email_engine_blacklist_checks_total", "Total blacklist check runs", registry=REGISTRY
)
alerts_sent = Counter(
    "email_engine_alerts_sent_total", "Total Telegram alerts sent",
    ["severity"],
    registry=REGISTRY,
)


def update_metrics_from_db(db) -> None:
    """Update Prometheus gauges from database state."""
    from app.models import IP, HealthCheck

    ips_active.set(db.query(IP).filter(IP.status == "active").count())
    ips_warming.set(db.query(IP).filter(IP.status == "warming").count())
    ips_blacklisted.set(db.query(IP).filter(IP.status == "blacklisted").count())

    latest_health = db.query(HealthCheck).order_by(HealthCheck.timestamp.desc()).first()
    if latest_health:
        pmta_running.set(1 if latest_health.pmta_running else 0)
        pmta_queue_size.set(latest_health.pmta_queue_size)
        disk_usage.set(latest_health.disk_usage_pct)
        ram_usage.set(latest_health.ram_usage_pct)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus-compatible metrics endpoint."""
    return generate_latest(REGISTRY).decode("utf-8")
