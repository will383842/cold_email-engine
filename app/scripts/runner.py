"""Subprocess wrapper for existing bash scripts."""

import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def run_script(name: str, args: list[str] | None = None, timeout: int = 120) -> dict:
    """Run a bash script from the scripts/ directory.

    Returns dict with returncode, stdout, stderr.
    """
    script_path = SCRIPTS_DIR / name
    if not script_path.exists():
        return {"returncode": -1, "stdout": "", "stderr": f"Script not found: {name}"}

    cmd = ["bash", str(script_path)] + (args or [])
    logger.info("running_script", script=name, args=args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        logger.info(
            "script_complete",
            script=name,
            returncode=result.returncode,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        logger.error("script_timeout", script=name, timeout=timeout)
        return {"returncode": -2, "stdout": "", "stderr": f"Timeout after {timeout}s"}
    except Exception as exc:
        logger.error("script_error", script=name, error=str(exc))
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}
