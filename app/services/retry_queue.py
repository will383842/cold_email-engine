"""File-based retry queue for failed scraper-pro API calls.

When scraper-pro is unreachable, payloads are saved to a JSONL file.
APScheduler retries them every 2 minutes until successful or max_retries reached.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

QUEUE_DIR = Path(os.getenv("RETRY_QUEUE_DIR", "/opt/email-engine/data"))
QUEUE_FILE = QUEUE_DIR / "retry_queue.jsonl"
MAX_RETRIES = 10


def enqueue(url: str, payload: dict, action: str) -> None:
    """Append a failed payload to the retry queue (atomic write)."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "url": url,
        "payload": payload,
        "action": action,
        "retries": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    line = json.dumps(entry, separators=(",", ":")) + "\n"
    # Append is atomic on Linux for lines < PIPE_BUF (4096 bytes)
    with open(QUEUE_FILE, "a") as f:
        f.write(line)
    logger.info("retry_enqueued", action=action, url=url)


async def process_queue() -> dict:
    """Retry all queued payloads. Returns stats dict."""
    if not QUEUE_FILE.exists():
        return {"processed": 0, "succeeded": 0, "failed": 0, "dropped": 0}

    # Read all entries
    entries = []
    try:
        with open(QUEUE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        return {"processed": 0, "succeeded": 0, "failed": 0, "dropped": 0}

    if not entries:
        return {"processed": 0, "succeeded": 0, "failed": 0, "dropped": 0}

    # Import here to avoid circular imports
    from app.services.scraper_pro_client import ScraperProClient, _build_headers

    client = ScraperProClient()
    import httpx

    remaining = []
    succeeded = 0
    dropped = 0

    for entry in entries:
        url = entry["url"]
        payload = entry["payload"]
        action = entry["action"]
        retries = entry.get("retries", 0)

        if retries >= MAX_RETRIES:
            logger.warning("retry_max_exceeded", action=action, retries=retries)
            dropped += 1
            continue

        body = json.dumps(payload, sort_keys=True)
        headers = _build_headers(client.secret, body)

        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.post(url, content=body, headers=headers)
                if resp.status_code == 200:
                    succeeded += 1
                    logger.info("retry_succeeded", action=action)
                    continue
        except Exception as exc:
            logger.debug("retry_still_failing", action=action, error=str(exc))

        # Still failed — re-enqueue with incremented retry count
        entry["retries"] = retries + 1
        remaining.append(entry)

    # Atomic rewrite: write to temp file then rename
    if remaining:
        fd, tmp_path = tempfile.mkstemp(dir=str(QUEUE_DIR), suffix=".jsonl")
        try:
            with os.fdopen(fd, "w") as f:
                for entry in remaining:
                    f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            os.replace(tmp_path, str(QUEUE_FILE))
        except Exception:
            os.unlink(tmp_path)
            raise
    else:
        # All succeeded or dropped — remove queue file
        try:
            QUEUE_FILE.unlink()
        except FileNotFoundError:
            pass

    stats = {
        "processed": len(entries),
        "succeeded": succeeded,
        "failed": len(remaining),
        "dropped": dropped,
    }
    if succeeded or dropped:
        logger.info("retry_queue_processed", **stats)
    return stats
